import feedparser
from typing import List, Dict
from datetime import datetime

RSS_FEEDS = {
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
}


def fetch_rss_feed(feed_info: Dict) -> List[Dict]:
    """Fetch articles from a single RSS feed."""
    articles = []
    try:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries[:10]:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            if not title or not url:
                continue

            summary = (
                entry.get("summary", "")
                or entry.get("description", "")
            )
            # Strip basic HTML tags from summary
            import re
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

            articles.append({
                "title": title,
                "summary": summary,
                "url": url,
                "source": feed_info["name"],
                "category": feed_info["category"],
                "published_at": entry.get("published", str(datetime.now())),
            })
    except Exception as e:
        print(f"[NewsFetcher] Error fetching {feed_info['name']}: {e}")
    return articles


def fetch_all_news(category_filter: str = "all") -> List[Dict]:
    """Fetch news from all configured RSS feeds."""
    feeds_to_fetch = []
    if category_filter in ("all", "global"):
        feeds_to_fetch.extend(RSS_FEEDS["global"])
    if category_filter in ("all", "india"):
        feeds_to_fetch.extend(RSS_FEEDS["india"])

    all_articles = []
    for feed in feeds_to_fetch:
        articles = fetch_rss_feed(feed)
        all_articles.extend(articles)
        print(f"[NewsFetcher] {feed['name']}: fetched {len(articles)} articles")

    return all_articles
