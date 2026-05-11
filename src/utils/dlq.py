import json
import os
from datetime import datetime
from typing import List
from pathlib import Path
from src.storage.redis_cache import get_redis
from src.utils.logger import get_logger

log = get_logger(__name__)

FAILED_ARTICLES_KEY = "failed_articles"
# LOG_DIR is already defined in logger.py, but we'll use a relative path here or from env
LOG_DIR = Path(os.getenv('LOG_DIR', 'logs'))
LOG_FILE = LOG_DIR / "failed_articles.jsonl"

def add_to_dlq(article_dict: dict, error: str) -> None:
    """Adds a failed article to the Dead Letter Queue (Redis + JSONL log)."""
    entry = {
        **article_dict,
        'error': error,
        'timestamp': datetime.now().isoformat(),
    }

    try:
        # 1. Add to Redis List
        r = get_redis()
        r.lpush(FAILED_ARTICLES_KEY, json.dumps(entry))
    except Exception as e:
        log.error("dlq_redis_failed", error=str(e))

    try:
        # 2. Log to JSONL file
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        log.error("dlq_file_failed", error=str(e))

    log.error("added_to_dlq", url=article_dict.get('url'), error=error)

def get_dlq_items() -> List[dict]:
    """Retrieves all items from the DLQ in Redis."""
    try:
        r = get_redis()
        items = r.lrange(FAILED_ARTICLES_KEY, 0, -1)
        return [json.loads(i) for i in items]
    except Exception as e:
        log.error("dlq_get_failed", error=str(e))
        return []

def clear_dlq() -> None:
    """Clears the DLQ in Redis."""
    try:
        r = get_redis()
        r.delete(FAILED_ARTICLES_KEY)
        log.info("dlq_cleared")
    except Exception as e:
        log.error("dlq_clear_failed", error=str(e))

def retry_dlq() -> int:
    """Moves all items from DLQ back to the extraction queue."""
    items = get_dlq_items()
    if not items:
        return 0

    from src.processors.extractor import process_extract

    for item in items:
        # Remove DLQ metadata before retrying
        item.pop('error', None)
        item.pop('timestamp', None)
        process_extract.delay(item)

    clear_dlq()

    log.info("dlq_retry_completed", count=len(items))
    return len(items)
