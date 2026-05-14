import httpx
import hashlib
import time
import trafilatura
import asyncio
from typing import Optional
from urllib.parse import urlparse
from src.storage.redis_cache import (
    add_to_dlq,
    get_jina_cache,
    get_readme_cache,
    set_jina_cache,
    set_readme_cache,
)
from src.utils.logger import get_logger
from src.storage.sqlite import save_article
from src.models.article import Article
from src.celery_app import app

log = get_logger(__name__)

TIMEOUT = 15.0
JINA_BASE_URL = "https://r.jina.ai/"
GITHUB_API_BASE = "https://api.github.com/repos"

async def extract_with_crawl4ai_async(url: str) -> Optional[str]:
    """Asynchronous extraction using Crawl4AI with stealth mode."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        
        browser_config = BrowserConfig(
            headless=True,
            browser_type="chromium",
        )
        
        run_config = CrawlerRunConfig(
            word_count_threshold=10,
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(),
            ),
            cache_mode=CacheMode.BYPASS, # We handle caching at the orchestrator level
            process_iframes=False,
            remove_overlay_elements=True,
            check_robots_txt=True,
            # Stealth mode features
            magic=True, 
            simulate_user=True,
            override_navigator=True
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            if result.success and result.markdown:
                log.info("crawl4ai_success", url=url, chars=len(result.markdown))
                return result.markdown
            else:
                log.warning("crawl4ai_failed", url=url, error=result.error_message)
                return None
    except ImportError:
        log.error("crawl4ai_not_installed")
        return None
    except Exception as e:
        log.error("crawl4ai_error", url=url, error=str(e))
        return None

def extract_with_crawl4ai(url: str) -> Optional[str]:
    """Sync wrapper for Crawl4AI extraction."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(extract_with_crawl4ai_async(url))

def extract_with_jina(url: str, md5_url: str = None) -> Optional[str]:
    """Extracts content from a URL using Jina AI Reader with Redis caching."""
    if md5_url is None:
        md5_url = hashlib.md5(url.encode()).hexdigest()

    # Caching handled in extract_article now for consistency
    try:
        response = httpx.get(
            f"{JINA_BASE_URL}{url}",
            headers={"Accept": "text/markdown"},
            timeout=TIMEOUT,
        )

        if response.status_code == 429:
            log.warning("jina_rate_limited", url=url)
            time.sleep(2)
            response = httpx.get(
                f"{JINA_BASE_URL}{url}",
                headers={"Accept": "text/markdown"},
                timeout=TIMEOUT,
            )

        response.raise_for_status()
        content = response.text.strip()

        if content:
            log.info("jina_extraction_completed", url=url, chars=len(content))
            return content

        return None

    except httpx.TimeoutException:
        log.error("jina_timeout", url=url)
        return None
    except httpx.HTTPStatusError as e:
        log.error("jina_http_error", url=url, status=e.response.status_code)
        return None
    except Exception as e:
        log.error("jina_error", url=url, error=str(e))
        return None

def extract_with_trafilatura(url: str) -> Optional[str]:
    """Fallback extraction using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
            
        result = trafilatura.extract(downloaded)
        if result:
            log.info("trafilatura_used", url=url, chars=len(result))
            return result.strip()
        return None
    except Exception as e:
        log.error("trafilatura_error", url=url, error=str(e))
        return None


def extract_github_readme(url: str) -> Optional[str]:
    """Fetches README markdown for GitHub repository URLs."""
    repo_key = _github_repo_key(url)
    if not repo_key:
        return None

    cached = get_readme_cache(repo_key)
    if cached:
        log.info("github_readme_cache_hit", repo=repo_key)
        return cached

    try:
        response = httpx.get(
            f"{GITHUB_API_BASE}/{repo_key}/readme",
            headers={
                "Accept": "application/vnd.github.raw",
                "User-Agent": "DailyDigestBot/1.0",
            },
            timeout=TIMEOUT,
        )
        if response.status_code == 404:
            log.warning("github_readme_missing", repo=repo_key)
            return None
        if response.status_code in {403, 429}:
            log.warning("github_readme_rate_limited", repo=repo_key, status=response.status_code)
            return None
        response.raise_for_status()
        content = response.text.strip()
        if content:
            set_readme_cache(repo_key, content)
            log.info("github_readme_extracted", repo=repo_key, chars=len(content))
            return content
    except Exception as e:
        log.warning("github_readme_failed", repo=repo_key, error=str(e))
    return None

def extract_article(article_dict: dict) -> dict:
    """Main extraction logic: Crawl4AI -> Jina AI -> Trafilatura fallback."""
    url = article_dict['url']
    md5_url = article_dict.get('md5_hash', '')

    log.info("extraction_started", url=url)

    existing_content = article_dict.get('clean_text')
    if article_dict.get("source") == "github":
        readme = extract_github_readme(url)
        if readme and len(readme) > 100:
            prefix = existing_content or ""
            article_dict['clean_text'] = f"{prefix}\n\nREADME:\n{readme}".strip()
            article_dict['status'] = 'processed'
            article = Article.from_dict(article_dict)
            save_article(article)
            return article_dict
        if existing_content and len(existing_content) > 100:
            log.info("github_readme_fallback_to_repo_metadata", url=url)
            article_dict['status'] = 'processed'
            article = Article.from_dict(article_dict)
            save_article(article)
            return article_dict

    if existing_content and len(existing_content) > 100 and not _is_source_context(existing_content):
        log.info("extraction_content_supplied", url=url, chars=len(existing_content))
        article_dict['status'] = 'processed'
        article = Article.from_dict(article_dict)
        save_article(article)
        return article_dict

    # 1. Try Cache First
    cached = get_jina_cache(md5_url)
    if cached:
        log.info("extraction_cache_hit", url=url)
        if existing_content and _is_source_context(existing_content):
            cached = f"{existing_content}\n\nCONTENT:\n{cached}"
        article_dict['clean_text'] = cached
        article_dict['status'] = 'processed'
        return article_dict

    # 2. Try Crawl4AI (Best for anti-bot/modern sites)
    content = extract_with_crawl4ai(url)

    # 3. Fallback to Jina
    if not content:
        log.warning("crawl4ai_failed_trying_jina", url=url)
        content = extract_with_jina(url, md5_url)

    # 4. Fallback to Trafilatura
    if not content:
        log.warning("jina_failed_trying_trafilatura", url=url)
        content = extract_with_trafilatura(url)

    if content and len(content) > 100:
        if existing_content and _is_source_context(existing_content):
            content = f"{existing_content}\n\nCONTENT:\n{content}"
        article_dict['clean_text'] = content
        article_dict['status'] = 'processed'
        set_jina_cache(md5_url, content) # Save back to cache
        log.info("extraction_completed", url=url, chars=len(content))
    else:
        article_dict['clean_text'] = None
        article_dict['status'] = 'failed'
        log.warning("extraction_failed", url=url)

    # Save to SQLite (upsert)
    article = Article.from_dict(article_dict)
    save_article(article)

    return article_dict

@app.task(name='src.processors.extractor.process_extract', bind=True, max_retries=3)
def process_extract(self, article_dict: dict):
    """Celery task for the extraction phase."""
    try:
        result = extract_article(article_dict)
        if result['status'] == 'processed':
            # Trigger Analyzer phase
            from src.processors.analyzer import process_analyze
            process_analyze.delay(result)
        else:
            add_to_dlq(result, "extraction_failed")
        return result
    except Exception as e:
        log.error("process_extract_error", url=article_dict.get('url'), error=str(e))
        if self.request.retries >= self.max_retries:
            add_to_dlq(article_dict, str(e))
            return {"status": "failed", "reason": str(e)}
        raise self.retry(exc=e, countdown=60)


def _github_repo_key(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    if domain != "github.com":
        return ""
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return ""
    return f"{parts[0]}/{parts[1]}"


def _is_source_context(content: str) -> bool:
    return str(content or "").startswith("Source: ") and "Inclusion reason:" in str(content or "")
