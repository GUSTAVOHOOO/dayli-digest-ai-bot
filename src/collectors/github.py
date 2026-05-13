import httpx
from datetime import datetime, timedelta
from typing import List
from src.collectors.base import BaseCollector
from src.models.article import Article
from src.storage.sqlite import is_article_processed
from src.utils.circuit import circuit_breaker
from src.utils.logger import get_logger
from src.utils.config_loader import load_config

log = get_logger(__name__)

class GitHubCollector(BaseCollector):
    source = "github"

    def __init__(self):
        super().__init__()
        self.api_url = "https://api.github.com/search/repositories"
        # We search for these topics to find relevant AI projects
        self.topics = ["llm", "generative-ai", "artificial-intelligence", "machine-learning"]

    def get_domain(self) -> str:
        return "github.com"

    @circuit_breaker(source="github")
    def fetch(self) -> List[Article]:
        articles = []
        
        # We look for repos created in the last 3 days
        since_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        for topic in self.topics:
            try:
                # Query: topic:ai created:>YYYY-MM-DD sort:stars
                query = f"topic:{topic} created:>{since_date}"
                log.info("github_searching", topic=topic, query=query)
                
                response = httpx.get(
                    self.api_url,
                    params={
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 5 # Top 5 per topic
                    },
                    headers={"User-Agent": "DailyDigestBot/1.0"},
                    timeout=15.0
                )
                
                if response.status_code == 403:
                    log.warning("github_rate_limited", topic=topic)
                    break
                    
                response.raise_for_status()
                data = response.json()

                for repo in data.get('items', []):
                    title = repo.get('full_name', '')
                    description = repo.get('description', '')
                    url = repo.get('html_url', '')
                    stars = repo.get('stargazers_count', 0)
                    
                    # We combine name and description for the "clean_text" so the analyzer has context
                    full_content = f"Repository: {title}\nStars: {stars}\nDescription: {description}"

                    article = Article(
                        url=url,
                        title=f"{title} (⭐{stars})",
                        source=self.source,
                        date_published=repo.get('created_at', ''),
                        clean_text=full_content,
                    )

                    if not is_article_processed(article.md5_hash):
                        # We'll let the extractor fetch the README for better analysis
                        articles.append(article)

            except Exception as e:
                log.error("github_search_failed", topic=topic, error=str(e))
                continue

        return articles
