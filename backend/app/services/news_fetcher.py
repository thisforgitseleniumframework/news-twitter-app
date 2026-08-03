"""
RSS news fetcher — general topics + sports subcategories.

Categories include india/global, science/tech/space/ocean/facts,
and sports_local / sports_international / sports_laliga / sports_epl /
sports_tennis / sports_cricket.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

import feedparser

from app.services.media_downloader import extract_media_url

# ---------------------------------------------------------------------------
# General news & topic feeds
# ---------------------------------------------------------------------------
GENERAL_FEEDS = {
    "global": [
        {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "category": "global"},
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "global"},
        {"name": "Reuters", "url": "http://feeds.reuters.com/reuters/topNews", "category": "global"},
        {"name": "Guardian World", "url": "https://www.theguardian.com/world/rss", "category": "global"},
    ],
    "india": [
        {"name": "NDTV", "url": "https://feeds.feedburner.com/ndtvnews-top-stories", "category": "india"},
        {"name": "The Hindu", "url": "https://www.thehindu.com/feeder/default.rss", "category": "india"},
        {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "category": "india"},
        {"name": "India Today", "url": "https://www.indiatoday.in/rss/1206578", "category": "india"},
        {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/rssfeedsdefault.cms", "category": "india"},
    ],
    "science": [
        {"name": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml", "category": "science"},
        {"name": "Phys.org", "url": "https://phys.org/rss-feed/", "category": "science"},
        {"name": "New Scientist", "url": "https://www.newscientist.com/feed/home/", "category": "science"},
    ],
    "technology": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "technology"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "technology"},
        {"name": "Ars Technica", "url": "http://feeds.arstechnica.com/arstechnica/index", "category": "technology"},
    ],
    "space": [
        {"name": "NASA", "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss", "category": "space"},
        {"name": "Space.com", "url": "https://www.space.com/feeds/all", "category": "space"},
        {"name": "SpaceNews", "url": "https://spacenews.com/feed/", "category": "space"},
    ],
    "ocean": [
        {"name": "NOAA Ocean", "url": "https://oceanservice.noaa.gov/news/rss/", "category": "ocean"},
        {"name": "Oceana", "url": "https://oceana.org/feed/", "category": "ocean"},
        {"name": "Ocean Conservancy", "url": "https://oceanconservancy.org/feed/", "category": "ocean"},
    ],
    "facts": [
        {"name": "IFLScience", "url": "https://www.iflscience.com/rss.xml", "category": "facts"},
        {"name": "Interesting Engineering", "url": "https://interestingengineering.com/feed", "category": "facts"},
        {"name": "Mental Floss", "url": "https://www.mentalfloss.com/rss.xml", "category": "facts"},
    ],
}

# ---------------------------------------------------------------------------
# Sports — optional "keywords" to keep only matching items
# ---------------------------------------------------------------------------
SPORTS_FEEDS = {
    "sports_local": [
        {
            "name": "NDTV Sports",
            "url": "https://feeds.feedburner.com/ndtvsports-latest",
            "category": "sports_local",
        },
        {
            "name": "TOI Sports",
            "url": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
            "category": "sports_local",
        },
        {
            "name": "The Hindu Sport",
            "url": "https://www.thehindu.com/sport/feeder/default.rss",
            "category": "sports_local",
        },
        {
            "name": "Indian Express Sports",
            "url": "https://indianexpress.com/section/sports/feed/",
            "category": "sports_local",
        },
    ],
    "sports_international": [
        {
            "name": "BBC Sport",
            "url": "http://feeds.bbci.co.uk/sport/rss.xml",
            "category": "sports_international",
        },
        {
            "name": "ESPN",
            "url": "https://www.espn.com/espn/rss/news",
            "category": "sports_international",
        },
        {
            "name": "Guardian Sport",
            "url": "https://www.theguardian.com/uk/sport/rss",
            "category": "sports_international",
        },
        {
            "name": "Sky Sports",
            "url": "https://www.skysports.com/rss/12040",
            "category": "sports_international",
        },
    ],
    "sports_laliga": [
        {
            "name": "BBC Football (La Liga filter)",
            "url": "http://feeds.bbci.co.uk/sport/football/rss.xml",
            "category": "sports_laliga",
            "keywords": [
                "la liga", "laliga", "real madrid", "barcelona", "barça", "barca",
                "atletico", "atlético", "sevilla", "villarreal", "real sociedad",
                "athletic bilbao", "girona", "betis", "valencia", "celta",
                "osasuna", "getafe", "mallorca", "alaves", "alavés", "las palmas",
                "rayo vallecano", "leganes", "leganés", "espanyol", "valladolid",
            ],
        },
        {
            "name": "ESPN Soccer (La Liga filter)",
            "url": "https://www.espn.com/espn/rss/soccer/news",
            "category": "sports_laliga",
            "keywords": [
                "la liga", "laliga", "real madrid", "barcelona", "barça", "barca",
                "atletico madrid", "atlético", "sevilla", "villarreal",
            ],
        },
        {
            "name": "Guardian Football (La Liga filter)",
            "url": "https://www.theguardian.com/football/rss",
            "category": "sports_laliga",
            "keywords": [
                "la liga", "laliga", "real madrid", "barcelona", "barça", "barca",
                "atletico", "atlético", "sevilla", "villarreal",
            ],
        },
    ],
    "sports_epl": [
        {
            "name": "BBC Premier League",
            "url": "http://feeds.bbci.co.uk/sport/football/premier-league/rss.xml",
            "category": "sports_epl",
        },
        {
            "name": "BBC Football (EPL filter)",
            "url": "http://feeds.bbci.co.uk/sport/football/rss.xml",
            "category": "sports_epl",
            "keywords": [
                "premier league", "epl", "manchester united", "man utd", "man united",
                "manchester city", "man city", "liverpool", "arsenal", "chelsea",
                "tottenham", "spurs", "newcastle", "aston villa", "west ham",
                "brighton", "wolves", "crystal palace", "fulham", "brentford",
                "nottingham forest", "everton", "bournemouth", "leicester",
                "ipswich", "southampton",
            ],
        },
        {
            "name": "Guardian Football (EPL filter)",
            "url": "https://www.theguardian.com/football/rss",
            "category": "sports_epl",
            "keywords": [
                "premier league", "epl", "manchester", "liverpool", "arsenal",
                "chelsea", "tottenham", "newcastle", "aston villa",
            ],
        },
        {
            "name": "ESPN Soccer (EPL filter)",
            "url": "https://www.espn.com/espn/rss/soccer/news",
            "category": "sports_epl",
            "keywords": [
                "premier league", "epl", "manchester united", "manchester city",
                "liverpool", "arsenal", "chelsea", "tottenham",
            ],
        },
    ],
    "sports_tennis": [
        {
            "name": "BBC Tennis",
            "url": "http://feeds.bbci.co.uk/sport/tennis/rss.xml",
            "category": "sports_tennis",
        },
        {
            "name": "ESPN Tennis",
            "url": "https://www.espn.com/espn/rss/tennis/news",
            "category": "sports_tennis",
        },
        {
            "name": "Guardian Tennis",
            "url": "https://www.theguardian.com/sport/tennis/rss",
            "category": "sports_tennis",
        },
        {
            "name": "ATP Tour News",
            "url": "https://www.atptour.com/en/media/rss-feed/xml-feed",
            "category": "sports_tennis",
        },
    ],
    "sports_cricket": [
        {
            "name": "BBC Cricket",
            "url": "http://feeds.bbci.co.uk/sport/cricket/rss.xml",
            "category": "sports_cricket",
        },
        {
            "name": "ESPNcricinfo",
            "url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
            "category": "sports_cricket",
        },
        {
            "name": "Cricbuzz",
            "url": "https://www.cricbuzz.com/rss-feed/cricket-news",
            "category": "sports_cricket",
        },
        {
            "name": "TOI Cricket",
            "url": "https://timesofindia.indiatimes.com/rssfeeds/54829575.cms",
            "category": "sports_cricket",
        },
        {
            "name": "The Hindu Cricket",
            "url": "https://www.thehindu.com/sport/cricket/feeder/default.rss",
            "category": "sports_cricket",
        },
    ],
}

# Combined map used by fetchers
RSS_FEEDS: Dict[str, List[Dict]] = {**GENERAL_FEEDS, **SPORTS_FEEDS}

SPORTS_CATEGORY_IDS = list(SPORTS_FEEDS.keys())
TOPIC_CATEGORY_IDS = [
    "india", "global", "science", "technology", "space", "ocean", "facts",
]

CATEGORY_META = {
    "india": {"label": "India", "group": "general"},
    "global": {"label": "Global", "group": "general"},
    "science": {"label": "Science", "group": "topics"},
    "technology": {"label": "Technology", "group": "topics"},
    "space": {"label": "Space", "group": "topics"},
    "ocean": {"label": "Ocean", "group": "topics"},
    "facts": {"label": "Facts", "group": "topics"},
    "sports_local": {"label": "Sports - Local (India)", "group": "sports"},
    "sports_international": {"label": "Sports - International", "group": "sports"},
    "sports_laliga": {"label": "Sports - La Liga", "group": "sports"},
    "sports_epl": {"label": "Sports - EPL", "group": "sports"},
    "sports_tennis": {"label": "Sports - Tennis", "group": "sports"},
    "sports_cricket": {"label": "Sports - Cricket", "group": "sports"},
}


def list_categories() -> List[Dict]:
    """Public category catalog for the API / UI."""
    items = []
    for cat_id, meta in CATEGORY_META.items():
        items.append({
            "id": cat_id,
            "label": meta["label"],
            "group": meta["group"],
            "feed_count": len(RSS_FEEDS.get(cat_id, [])),
        })
    return items


def _matches_keywords(title: str, summary: str, keywords: Optional[List[str]]) -> bool:
    """If keywords set, require at least one match in title/summary."""
    if not keywords:
        return True
    blob = f"{title} {summary}".lower()
    return any(kw.lower() in blob for kw in keywords)


def fetch_rss_feed(feed_info: Dict) -> List[Dict]:
    """Fetch articles from a single RSS feed (optional keyword filter + media URL)."""
    articles = []
    keywords = feed_info.get("keywords")
    try:
        feed = feedparser.parse(feed_info["url"])
        # Pull a few more entries when filtering by keyword
        entry_limit = 25 if keywords else 12
        for entry in feed.entries[:entry_limit]:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            if not title or not url:
                continue

            summary = (
                entry.get("summary", "")
                or entry.get("description", "")
            )
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

            if not _matches_keywords(title, summary, keywords):
                continue

            media_source_url = extract_media_url(entry)

            articles.append({
                "title": title,
                "summary": summary,
                "url": url,
                "source": feed_info["name"],
                "category": feed_info["category"],
                "published_at": entry.get("published", str(datetime.now())),
                "media_source_url": media_source_url,
            })
            # Cap per feed after filtering
            if len(articles) >= 12:
                break
    except Exception as e:
        print(f"[NewsFetcher] Error fetching {feed_info['name']}: {e}")
    return articles


def _feeds_for_filter(category_filter: str) -> List[Dict]:
    """Resolve which feed lists to pull for a filter value."""
    category_filter = (category_filter or "all").lower().strip()

    if category_filter == "all":
        feeds: List[Dict] = []
        for group in RSS_FEEDS.values():
            feeds.extend(group)
        return feeds

    if category_filter == "sports":
        # All sports subcategories
        feeds = []
        for cat_id in SPORTS_CATEGORY_IDS:
            feeds.extend(SPORTS_FEEDS[cat_id])
        return feeds

    if category_filter == "general":
        feeds = []
        for cat_id in ("india", "global"):
            feeds.extend(GENERAL_FEEDS[cat_id])
        return feeds

    if category_filter == "topics":
        feeds = []
        for cat_id in ("science", "technology", "space", "ocean", "facts"):
            feeds.extend(GENERAL_FEEDS[cat_id])
        return feeds

    if category_filter in RSS_FEEDS:
        return list(RSS_FEEDS[category_filter])

    return []


def fetch_all_news(category_filter: str = "all") -> List[Dict]:
    """
    Fetch news from configured RSS feeds in parallel.

    category_filter:
      all | general | topics | india | global | sports |
      science | technology | space | ocean | facts |
      sports_local | sports_international | sports_laliga |
      sports_epl | sports_tennis | sports_cricket
    """
    feeds_to_fetch = _feeds_for_filter(category_filter)
    if not feeds_to_fetch:
        print(f"[NewsFetcher] Unknown category filter: {category_filter}")
        return []

    # De-dupe feeds that appear in multiple categories (same URL)
    seen_urls = set()
    unique_feeds = []
    for feed in feeds_to_fetch:
        key = (feed["url"], feed["category"])
        if key in seen_urls:
            continue
        seen_urls.add(key)
        unique_feeds.append(feed)

    all_articles: List[Dict] = []
    seen_article_urls = set()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_rss_feed, feed): feed for feed in unique_feeds
        }
        for future in as_completed(futures):
            feed = futures[future]
            try:
                articles = future.result()
                for art in articles:
                    if art["url"] in seen_article_urls:
                        continue
                    seen_article_urls.add(art["url"])
                    all_articles.append(art)
                print(
                    f"[NewsFetcher] {feed['name']} [{feed['category']}]: "
                    f"fetched {len(articles)} articles"
                )
            except Exception as e:
                print(f"[NewsFetcher] {feed['name']}: failed — {e}")

    return all_articles
