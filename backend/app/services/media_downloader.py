"""Download and store news article media (images / videos) under backend/media/."""
import hashlib
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

# backend/media — works when uvicorn is started from backend/
MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Max download size (15 MB) — keeps storage and Twitter uploads reasonable
MAX_BYTES = 15 * 1024 * 1024

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}

USER_AGENT = (
    "Mozilla/5.0 (compatible; NewsPostBot/1.0; +http://localhost:8000)"
)


def absolute_media_path(filename: Optional[str]) -> Optional[str]:
    """Resolve a stored media filename to an absolute filesystem path."""
    if not filename:
        return None
    path = MEDIA_DIR / Path(filename).name
    return str(path) if path.is_file() else None


def media_public_url(filename: Optional[str]) -> Optional[str]:
    """Public URL path served by FastAPI StaticFiles mount."""
    if not filename:
        return None
    return f"/media/{Path(filename).name}"


def extract_media_url(entry: Any) -> Optional[str]:
    """Pull the best image/video URL from a feedparser entry."""
    # 1. Enclosures (common for podcasts / media RSS)
    for enc in getattr(entry, "enclosures", None) or entry.get("enclosures", []) or []:
        href = enc.get("href") or enc.get("url")
        mime = (enc.get("type") or "").lower()
        if href and (mime.startswith("image/") or mime.startswith("video/")):
            return href.strip()
        if href and _looks_like_media(href):
            return href.strip()

    # 2. media:content
    for item in getattr(entry, "media_content", None) or entry.get("media_content", []) or []:
        url = (item.get("url") or "").strip()
        if url and (item.get("medium") in ("image", "video") or _looks_like_media(url)):
            return url

    # 3. media:thumbnail
    for item in getattr(entry, "media_thumbnail", None) or entry.get("media_thumbnail", []) or []:
        url = (item.get("url") or "").strip()
        if url:
            return url

    # 4. link rel=enclosure / type image|video
    for link in getattr(entry, "links", None) or entry.get("links", []) or []:
        href = (link.get("href") or "").strip()
        mime = (link.get("type") or "").lower()
        rel = (link.get("rel") or "").lower()
        if not href:
            continue
        if rel == "enclosure" and (mime.startswith("image/") or mime.startswith("video/") or _looks_like_media(href)):
            return href
        if mime.startswith("image/") or mime.startswith("video/"):
            return href

    # 5. First <img src> in HTML summary / content
    html_parts = []
    summary = entry.get("summary") or entry.get("description") or ""
    if summary:
        html_parts.append(summary)
    for block in entry.get("content", []) or []:
        if isinstance(block, dict) and block.get("value"):
            html_parts.append(block["value"])

    for html in html_parts:
        match = re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            html,
            flags=re.IGNORECASE,
        )
        if match:
            src = match.group(1).strip()
            if src.startswith("http") and not src.startswith("data:"):
                return src

    return None


def _looks_like_media(url: str) -> bool:
    path = urlparse(url).path.lower()
    ext = Path(path).suffix
    return ext in IMAGE_EXTS or ext in VIDEO_EXTS


def _guess_ext_and_type(url: str, content_type: Optional[str]) -> tuple[str, str]:
    """Return (file_extension, media_type) where media_type is 'image' or 'video'."""
    mime = (content_type or "").split(";")[0].strip().lower()
    path_ext = Path(urlparse(url).path).suffix.lower()

    if mime.startswith("video/") or path_ext in VIDEO_EXTS:
        if path_ext in VIDEO_EXTS:
            return path_ext, "video"
        ext = mimetypes.guess_extension(mime) or ".mp4"
        return ext, "video"

    if mime.startswith("image/") or path_ext in IMAGE_EXTS:
        if path_ext in IMAGE_EXTS:
            return path_ext, "image"
        ext = mimetypes.guess_extension(mime) or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        return ext, "image"

    # Default to image if unclear but we got bytes
    if path_ext:
        kind = "video" if path_ext in VIDEO_EXTS else "image"
        return path_ext, kind
    return ".jpg", "image"


def download_media(source_url: str, article_id: Optional[int] = None) -> Optional[Dict[str, str]]:
    """
    Download media from source_url into MEDIA_DIR.

    Returns {"filename": "...", "media_type": "image"|"video"} or None on failure.
    """
    if not source_url or not source_url.startswith("http"):
        return None

    try:
        with httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            # Prefer HEAD for content-type, but some feeds block it — fall through to GET
            content_type = None
            try:
                head = client.head(source_url)
                content_type = head.headers.get("content-type")
                content_length = head.headers.get("content-length")
                if content_length and int(content_length) > MAX_BYTES:
                    print(f"[Media] Skip (too large): {source_url[:80]}")
                    return None
            except Exception:
                pass

            response = client.get(source_url)
            response.raise_for_status()
            content_type = content_type or response.headers.get("content-type")
            data = response.content
            if not data:
                return None
            if len(data) > MAX_BYTES:
                print(f"[Media] Skip (too large after download): {source_url[:80]}")
                return None

        ext, media_type = _guess_ext_and_type(source_url, content_type)
        url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
        prefix = f"{article_id}_" if article_id is not None else ""
        filename = f"{prefix}{url_hash}{ext}"
        dest = MEDIA_DIR / filename

        if not dest.exists():
            dest.write_bytes(data)

        print(f"[Media] Saved {media_type}: {filename} ({len(data)} bytes)")
        return {"filename": filename, "media_type": media_type}
    except Exception as e:
        print(f"[Media] Failed to download {source_url[:80]}: {e}")
        return None


def attach_media_to_article(article, source_url: Optional[str]) -> bool:
    """
    Download media for a NewsArticle ORM instance and set its media fields.
    Returns True if media was saved.
    """
    if not source_url:
        return False
    result = download_media(source_url, article_id=getattr(article, "id", None))
    if not result:
        return False
    article.media_path = result["filename"]
    article.media_type = result["media_type"]
    article.media_source_url = source_url
    return True
