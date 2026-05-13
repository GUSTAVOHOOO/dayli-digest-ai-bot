import feedparser
import httpx
import os
import tweepy
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
        self.USERS = config.get('twitter_users', [])
        self.rsshub_base = os.getenv('RSSHUB_URL', 'http://rsshub:1200')
        
        # Initialize Tweepy Client
        try:
            self.twitter_client = tweepy.Client(
                bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
                consumer_key=os.getenv('TWITTER_CONSUMER_KEY'),
                consumer_secret=os.getenv('TWITTER_CONSUMER_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
        except Exception as e:
            log.error("twitter_init_failed", error=str(e))
            self.twitter_client = None

    def get_domain(self) -> str:
        return "twitter.com"

    @circuit_breaker(source="twitter")
    def fetch(self) -> List[Article]:
        articles = []
        
        # 1. Authority Users via RSSHub
        for user in self.USERS:
            feed_url = f"{self.rsshub_base}/twitter/user/{user}"
            articles.extend(self._fetch_rsshub(feed_url, f"@{user}"))

        # 2. Global Discovery via Tweepy
        if self.twitter_client:
            for keyword in self.KEYWORDS:
                articles.extend(self._fetch_tweepy(keyword))

        return articles

    def _fetch_tweepy(self, keyword: str) -> List[Article]:
        collected = []
        try:
            log.info("twitter_tweepy_searching", keyword=keyword)
            # Search recent tweets (last 7 days), excluding retweets
            query = f"{keyword} -is:retweet lang:en"
            response = self.twitter_client.search_recent_tweets(query=query, max_results=10)
            
            if response.data:
                for tweet in response.data:
                    url = f"https://x.com/i/web/status/{tweet.id}"
                    article = Article(url=url, title=f"🐦 TAG:{keyword}: {tweet.text[:100]}...",
                                     source=self.source, date_published=None)
                    if not is_article_processed(article.md5_hash):
                        collected.append(article)
        except Exception as e:
            log.error("twitter_tweepy_failed", keyword=keyword, error=str(e))
        return collected

    def _fetch_rsshub(self, url: str, prefix: str) -> List[Article]:
        collected = []
        try:
            log.info("twitter_fetching_rss", url=url)
            response = httpx.get(url, timeout=20.0)
            if response.status_code != 200:
                log.warning("twitter_rss_http_error", url=url, status=response.status_code)
                return collected

            feed = feedparser.parse(response.text)
            for entry in feed.entries[:5]:
                article = Article(url=entry.get('link', ''), title=f"🐦 {prefix}: {entry.get('title', '')[:100]}...",
                                 source=self.source, date_published=entry.get('published', ''))
                if not is_article_processed(article.md5_hash):
                    collected.append(article)
        except Exception as e:
            log.error("twitter_rss_failed", url=url, error=str(e))
        return collected
