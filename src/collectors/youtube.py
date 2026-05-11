import feedparser
import httpx
from typing import List
from src.collectors.base import BaseCollector
from src.models.article import Article
from src.storage.sqlite import is_article_processed
from src.utils.circuit import circuit_breaker
from src.utils.logger import get_logger
from src.utils.config_loader import load_config

log = get_logger(__name__)

class YouTubeCollector(BaseCollector):
    source = "youtube"

    def __init__(self):
        super().__init__()
        config = load_config('config/feeds.yaml')
        self.FEEDS = config.get('youtube', [])

    def get_domain(self) -> str:
        return "www.youtube.com"

    @circuit_breaker(source="youtube")
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

                    article = Article(
                        url=url,
                        title=title,
                        source=self.source,
                        date_published=date,
                    )

                    if not is_article_processed(article.md5_hash):
                        articles.append(article)

            except Exception as e:
                log.error("fetch_failed", source=self.source, url=feed_url, error=str(e))

        return articles
