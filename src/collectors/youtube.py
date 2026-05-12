import feedparser
import httpx
import os
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
        self.KEYWORDS = config.get('keywords', ["AI", "LLM"])
        self.rsshub_base = os.getenv('RSSHUB_URL', 'http://rsshub:1200')

    def get_domain(self) -> str:
        return "www.youtube.com"

    @circuit_breaker(source="youtube")
    def fetch(self) -> List[Article]:
        articles = []
        config = load_config('config/feeds.yaml')
        channels = config.get('youtube_channels', [])
        
        for channel_id in channels:
            # RSSHub YouTube Channel: /youtube/channel/:id
            feed_url = f"{self.rsshub_base}/youtube/channel/{channel_id}"
            try:
                log.info("youtube_fetching_channel", channel_id=channel_id)
                response = httpx.get(feed_url, timeout=15.0)
                if response.status_code != 200:
                    log.warning("youtube_channel_failed", channel_id=channel_id, status=response.status_code)
                    continue
                
                feed = feedparser.parse(response.text)
                for entry in feed.entries[:3]: # Top 3 per channel
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
                log.error("fetch_failed", source=self.source, channel_id=channel_id, error=str(e))

        return articles
