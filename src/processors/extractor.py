import httpx
import hashlib
import time
import trafilatura
from typing import Optional
from src.storage.redis_cache import get_jina_cache, set_jina_cache, add_to_dlq
from src.utils.logger import get_logger
from src.storage.sqlite import save_article
from src.models.article import Article
from src.celery_app import app

log = get_logger(__name__)

TIMEOUT = 15.0
JINA_BASE_URL = "https://r.jina.ai/http://"

def extract_with_jina(url: str, md5_url: str = None) -> Optional[str]:
    """Extracts content from a URL using Jina AI Reader with Redis caching."""
    if md5_url is None:
        md5_url = hashlib.md5(url.encode()).hexdigest()

    cached = get_jina_cache(md5_url)
    if cached:
        log.info("jina_cache_hit", url=url)
        return cached

    log.info("jina_cache_miss", url=url)

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
            set_jina_cache(md5_url, content)
            log.info("extraction_completed", url=url, chars=len(content))
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

def extract_article(article_dict: dict) -> dict:
    """Main extraction logic: Jina AI -> Trafilatura fallback."""
    url = article_dict['url']
    md5_url = article_dict.get('md5_hash', '')

    log.info("extraction_started", url=url)

    content = extract_with_jina(url, md5_url)

    if not content:
        log.warning("jina_failed_trying_trafilatura", url=url)
        content = extract_with_trafilatura(url)

    if content and len(content) > 100:
        article_dict['clean_text'] = content
        article_dict['status'] = 'processed'
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
            # Trigger Analyzer phase (NEW)
            from src.processors.analyzer import process_analyze
            process_analyze.delay(result)
        else:
            add_to_dlq(result, "extraction_failed")
        return result
    except Exception as e:
        log.error("process_extract_error", url=article_dict.get('url'), error=str(e))
        raise self.retry(exc=e, countdown=60)
