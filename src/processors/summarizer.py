import httpx
import os
from datetime import datetime
from typing import Optional
from src.utils.logger import get_logger
from src.utils.config_loader import load_config
from src.celery_app import app
from src.models.article import Article
from src.storage.sqlite import save_article
from src.storage.redis_cache import add_to_dlq, acquire_dispatch_schedule_lock

log = get_logger(__name__)

OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:3b')
TIMEOUT = 30.0

_prompts_cache = None

def get_prompts() -> dict:
    """Provides a singleton prompts configuration."""
    global _prompts_cache
    if _prompts_cache is None:
        _prompts_cache = load_config('config/prompts.yaml')
    return _prompts_cache

def get_prompt_for_category(category: str, text: str, title: str = "") -> str:
    """Builds the prompt based on category and article content."""
    prompts = get_prompts()
    # Fallback to 'blogs' if category not found
    category_config = prompts.get(category, prompts.get('blogs', {}))
    system = category_config.get('system', '')

    # Limit text to ~4000 characters to stay within context limits
    truncated_text = text[:4000] if len(text) > 4000 else text

    return f"{system}\n\nArtigo: {title}\n\nConteúdo:\n{truncated_text}"

def summarize(article: dict, category: str) -> Optional[str]:
    """Summarizes article content using Ollama."""
    clean_text = article.get('clean_text', '')
    title = article.get('title', '')

    if not clean_text:
        log.error("summarize_no_content", url=article.get('url'))
        return None

    prompt = get_prompt_for_category(category, clean_text, title)

    try:
        log.info("ollama_request_started", url=article.get('url'), category=category)

        response = httpx.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 250,
                    "top_p": 0.9,
                }
            },
            timeout=TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()
        summary = data.get('response', '').strip()

        if summary:
            log.info("ollama_response", tokens=len(summary.split()), duration_ms=data.get('total_duration', 0))
            return summary

        return None

    except httpx.TimeoutException:
        log.error("ollama_timeout", url=article.get('url'))
        return None
    except httpx.HTTPStatusError as e:
        log.error("ollama_http_error", url=article.get('url'), status=e.response.status_code)
        return None
    except Exception as e:
        log.error("ollama_error", url=article.get('url'), error=str(e))
        return None

@app.task(
    name='src.processors.summarizer.process_summarize',
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def process_summarize(self, article_dict: dict):
    """Celery task for the summarization phase."""
    url = article_dict.get('url', '')
    log.info("summarize_started", url=url)

    try:
        clean_text = article_dict.get('clean_text', '')
        if not clean_text:
            log.error("summarize_no_content", url=url)
            add_to_dlq(article_dict, "no_clean_text")
            return {"status": "failed", "reason": "no_content"}

        category = article_dict.get('source', 'blogs')
        summary = summarize(article_dict, category)

        if summary:
            article_dict['summary'] = summary
            # Update SQLite with the summary
            article = Article.from_dict(article_dict)
            save_article(article)

            log.info("summarize_completed", url=url, summary_len=len(summary))

            today = datetime.now().strftime('%Y-%m-%d')
            if acquire_dispatch_schedule_lock(today):
                from src.dispatchers.telegram import process_dispatch
                process_dispatch.apply_async(countdown=60)
                log.info("dispatch_scheduled", date=today, delay_seconds=60)
            else:
                log.info("dispatch_already_scheduled", date=today)
            return {"status": "ok", "summary": summary}
        else:
            raise Exception("summarize_returned_none")

    except Exception as e:
        log.error("summarize_error", url=url, error=str(e))

        if self.request.retries >= self.max_retries:
            log.error("summarize_max_retries", url=url)
            add_to_dlq(article_dict, str(e))
            return {"status": "failed", "reason": str(e)}

        raise self.retry(exc=e, countdown=int(60 * (2 ** self.request.retries)))
