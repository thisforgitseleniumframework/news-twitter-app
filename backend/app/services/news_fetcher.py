import feedparser
from typing import List, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    "sports": [
        {"name": "ESPN", "url": "https://www.espn.com/espn/rss/news", "category": "sports"},
        {"name": "BBC Sport", "url": "http://feeds.bbci.co.uk/sport/rss.xml", "category": "sports"},
        {"name": "Sky Sports", "url": "https://www.skysports.com/rss/12040", "category": "sports"},
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
    """Fetch news from all configured RSS feeds in parallel."""
    feeds_to_fetch = []
    if category_filter == "all":
        for feeds in RSS_FEEDS.values():
            feeds_to_fetch.extend(feeds)
    elif category_filter in RSS_FEEDS:
        feeds_to_fetch.extend(RSS_FEEDS[category_filter])

    all_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_rss_feed, feed): feed for feed in feeds_to_fetch}
        for future in as_completed(futures):
            feed = futures[future]
            try:
                articles = future.result()
                all_articles.extend(articles)
                print(f"[NewsFetcher] {feed['name']}: fetched {len(articles)} articles")
            except Exception as e:
                print(f"[NewsFetcher] {feed['name']}: failed — {e}")

    return all_articles
