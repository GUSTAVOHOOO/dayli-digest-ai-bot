import feedparser
import httpx
import os
import yt_dlp
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
        self.CHANNELS = config.get('youtube_channels', [])
        self.rsshub_base = os.getenv('RSSHUB_URL', 'http://rsshub:1200')

    def get_domain(self) -> str:
        return "www.youtube.com"

    @circuit_breaker(source="youtube")
    def fetch(self) -> List[Article]:
        articles = []
        
        # 1. Authority Channels via Official YouTube RSS
        for channel_id in self.CHANNELS:
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            articles.extend(self._fetch_official_rss(feed_url))

        # 2. Global Discovery via yt-dlp
        for keyword in self.KEYWORDS:
            articles.extend(self._fetch_yt_dlp(keyword))

        return articles

    def _fetch_yt_dlp(self, keyword: str) -> List[Article]:
        """Uses yt-dlp to find trending videos for a keyword."""
        collected = []
        try:
            log.info("youtube_yt_dlp_searching", keyword=keyword)
            ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get top 3 results
                info = ydl.extract_info(f"ytsearch3:{keyword}", download=False)
                for entry in info.get('entries', []):
                    url = f"https://www.youtube.com/watch?v={entry['id']}"
                    article = Article(url=url, title=f"📺 SEARCH:{keyword}: {entry['title']}", 
                                     source=self.source, date_published=None)
                    if not is_article_processed(article.md5_hash):
                        collected.append(article)
        except Exception as e:
            log.error("youtube_yt_dlp_failed", keyword=keyword, error=str(e))
        return collected

    def _fetch_official_rss(self, url: str) -> List[Article]:
        collected = []
        try:
            log.info("youtube_fetching_official_rss", url=url)
            response = httpx.get(url, timeout=20.0, follow_redirects=True)
            if response.status_code != 200:
                log.warning("youtube_official_rss_http_error", url=url, status=response.status_code)
                return collected

            feed = feedparser.parse(response.text)
            channel_title = feed.feed.get('title', 'YouTube')
            for entry in feed.entries[:3]:
                article = Article(url=entry.get('link', ''), title=f"📺 {channel_title}: {entry.get('title', '')}",
                                 source=self.source, date_published=entry.get('published', ''))
                if not is_article_processed(article.md5_hash):
                    collected.append(article)
        except Exception as e:
            log.error("youtube_official_rss_failed", url=url, error=str(e))
        return collected
