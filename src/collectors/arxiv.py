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
from src.collectors.base import BaseCollector
from src.models.article import Article
from src.storage.sqlite import is_article_processed
from src.utils.circuit import circuit_breaker
from src.utils.logger import get_logger
from src.utils.config_loader import load_config

log = get_logger(__name__)

class ArxivCollector(BaseCollector):
    source = "papers"

    def __init__(self):
        config = load_config('config/feeds.yaml')
        self.FEEDS = config.get('arxiv', [])
        super().__init__()

    def get_domain(self) -> str:
        return "export.arxiv.org"

    @circuit_breaker(source="papers")
    def fetch(self) -> List[Article]:
        articles = []
        for feed_url in self.FEEDS:
            try:
                response = httpx.get(feed_url, timeout=15.0)
                response.raise_for_status()
                feed = feedparser.parse(response.text)

                for entry in feed.entries:
                    title = entry.get('title', '')
                    url = entry.get('link', '')
                    date = entry.get('published', '')
                    authors = ", ".join(author.get("name", "") for author in entry.get("authors", []) if author.get("name"))
                    abstract = entry.get("summary", "")

                    article = Article(
                        url=url,
                        title=title,
                        source=self.source,
                        date_published=date,
                        clean_text=f"Title: {title}\nAuthors: {authors}\nAbstract: {abstract}".strip(),
                    )

                    if not is_article_processed(article.md5_hash):
                        articles.append(article)

            except Exception as e:
                log.error("fetch_failed", source=self.source, url=feed_url, error=str(e))
                raise

        return articles
