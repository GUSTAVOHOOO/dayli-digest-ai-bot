try:
    import feedparser
except ImportError:
    class _FeedparserUnavailable:
        @staticmethod
        def parse(*args, **kwargs):
            raise RuntimeError("feedparser package is not installed")

    feedparser = _FeedparserUnavailable()
try:
    import httpx
except ImportError:
    class _HttpxUnavailable:
        @staticmethod
        def get(*args, **kwargs):
            raise RuntimeError("httpx package is not installed")

    httpx = _HttpxUnavailable()
from typing import List
from urllib.parse import urlparse
from src.collectors.base import BaseCollector
from src.models.article import Article
from src.storage.sqlite import is_article_processed
from src.utils.circuit import circuit_breaker
from src.utils.logger import get_logger
from src.utils.config_loader import load_config

log = get_logger(__name__)

class BlogsCollector(BaseCollector):
    source = "blogs"

    def __init__(self):
        config = load_config('config/feeds.yaml')
        self.SOURCES = _blog_sources(config)
        self.FEEDS = [source["url"] for source in self.SOURCES]
        super().__init__()

    def get_domain(self) -> str:
        if self.FEEDS:
            return urlparse(self.FEEDS[0]).netloc
        return "blogs"

    @circuit_breaker(source="blogs")
    def fetch(self) -> List[Article]:
        articles = []
        for source_config in self.SOURCES:
            feed_url = source_config["url"]
            try:
                response = httpx.get(feed_url, timeout=15.0, follow_redirects=True)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
                if getattr(feed, "bozo", False) and not feed.entries:
                    log.warning("feed_invalid_ignored", source=self.source, url=feed_url, reason=str(getattr(feed, "bozo_exception", "")))
                    continue

                for entry in feed.entries:
                    title = entry.get('title', '')
                    url = entry.get('link', '')
                    date = entry.get('published', '')

                    article = Article(
                        url=url,
                        title=title,
                        source=self.source,
                        date_published=date,
                        clean_text=_source_context(source_config),
                    )

                    if not is_article_processed(article.md5_hash):
                        articles.append(article)

            except Exception as e:
                log.error("fetch_failed", source=self.source, url=feed_url, error=str(e))
                # Don't raise here, allow other blogs to be fetched

        return articles


def _blog_sources(config: dict) -> List[dict]:
    structured = config.get("blog_sources")
    if isinstance(structured, list) and structured:
        sources = []
        for item in structured:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            sources.append({
                "name": str(item.get("name") or item["url"]),
                "url": str(item["url"]),
                "category": str(item.get("category") or "technical_blog"),
                "authority": str(item.get("authority") or "medium"),
                "inclusion_reason": str(item.get("inclusion_reason") or ""),
            })
        return sources
    return [
        {
            "name": feed_url,
            "url": feed_url,
            "category": "technical_blog",
            "authority": "medium",
            "inclusion_reason": "legacy feed configuration",
        }
        for feed_url in config.get("blogs", [])
    ]


def _source_context(source_config: dict) -> str:
    return (
        f"Source: {source_config.get('name')}\n"
        f"Source category: {source_config.get('category')}\n"
        f"Source authority: {source_config.get('authority')}\n"
        f"Inclusion reason: {source_config.get('inclusion_reason')}"
    )
