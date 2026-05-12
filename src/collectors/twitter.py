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

class TwitterCollector(BaseCollector):
    source = "twitter"

    def __init__(self):
        super().__init__()
        config = load_config('config/feeds.yaml')
        self.KEYWORDS = config.get('keywords', ["AI", "LLM"])
        self.rsshub_base = os.getenv('RSSHUB_URL', 'http://rsshub:1200')

    def get_domain(self) -> str:
        return "twitter.com"

    @circuit_breaker(source="twitter")
    def fetch(self) -> List[Article]:
        articles = []
        config = load_config('config/feeds.yaml')
        users = config.get('twitter_users', [])
        
        # We try users instead of keyword search because RSSHub needs Twitter API keys for keywords
        for user in users:
            feed_url = f"{self.rsshub_base}/twitter/user/{user}"
            try:
                log.info("twitter_fetching_user", user=user)
                response = httpx.get(feed_url, timeout=15.0)
                if response.status_code != 200:
                    log.warning("twitter_user_failed", user=user, status=response.status_code)
                    continue

                feed = feedparser.parse(response.text)
                for entry in feed.entries[:5]: # Top 5 tweets per user
                    title = entry.get('title', '')
                    url = entry.get('link', '')
                    date = entry.get('published', '')

                    article = Article(
                        url=url,
                        title=f"@{user}: {title[:100]}...",
                        source=self.source,
                        date_published=date,
                    )

                    if not is_article_processed(article.md5_hash):
                        articles.append(article)

            except Exception as e:
                log.error("fetch_failed", source=self.source, user=user, error=str(e))

        return articles
