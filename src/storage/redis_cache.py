import json
import os
from typing import Optional, List
try:
    import redis
except ImportError:
    redis = None
from src.utils.config_loader import load_env

# Ensure env is loaded
load_env()
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Singleton client
_redis_client = None

class _NoRedisError(Exception):
    pass


def _redis_error():
    return redis.RedisError if redis is not None else _NoRedisError


def get_redis():
    """Provides a singleton Redis client."""
    if redis is None:
        raise _NoRedisError("redis package is not installed")
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client

# Jina Cache
def get_jina_cache(md5_url: str) -> Optional[str]:
    """Retrieves cached Jina content."""
    try:
        return get_redis().get(f"jina_cache:{md5_url}")
    except _redis_error():
        return None

def set_jina_cache(md5_url: str, content: str):
    """Caches Jina content with a 24h TTL."""
    try:
        get_redis().setex(f"jina_cache:{md5_url}", 86400, content)
    except _redis_error():
        pass


def get_readme_cache(repo_key: str) -> Optional[str]:
    """Retrieves cached GitHub README content."""
    try:
        return get_redis().get(f"github_readme:{repo_key}")
    except _redis_error():
        return None


def set_readme_cache(repo_key: str, content: str, ttl_seconds: int = 86400 * 7):
    """Caches GitHub README content."""
    try:
        get_redis().setex(f"github_readme:{repo_key}", ttl_seconds, content)
    except _redis_error():
        pass

# Distributed Lock for Digest
def acquire_digest_lock(date: str) -> bool:
    """Attempts to acquire a distributed lock for a specific date digest."""
    try:
        return bool(get_redis().set(f"digest:lock:{date}", "locked", nx=True, ex=3600))
    except _redis_error():
        # Fallback if Redis is down - allow but log? Or safer to fail?
        # Given the requirements, we'll return True to not block, but this is risky.
        return True

def release_digest_lock(date: str):
    """Releases the distributed lock."""
    try:
        get_redis().delete(f"digest:lock:{date}")
    except _redis_error():
        pass

def acquire_dispatch_schedule_lock(date: str, ttl_seconds: int = 120) -> bool:
    """Prevents scheduling many dispatch tasks while summaries finish in a burst."""
    try:
        return bool(get_redis().set(f"dispatch:scheduled:{date}", "scheduled", nx=True, ex=ttl_seconds))
    except _redis_error():
        return True

def release_dispatch_schedule_lock(date: str):
    """Allows a later dispatch schedule after the current dispatch has run."""
    try:
        get_redis().delete(f"dispatch:scheduled:{date}")
    except _redis_error():
        pass


def acquire_realtime_alert_lock(alert_key: str, date: str, ttl_seconds: int = 86400) -> bool:
    """Prevents sending the same realtime alert more than once per day."""
    try:
        return bool(get_redis().set(f"realtime_alert:{date}:{alert_key}", "sent", nx=True, ex=ttl_seconds))
    except _redis_error():
        return True

# DLQ Helpers
def add_to_dlq(article_dict: dict, reason: str):
    """Real DLQ implementation from src.utils.dlq."""
    from src.utils.dlq import add_to_dlq as real_add
    real_add(article_dict, reason)

def get_dlq_items() -> List[dict]:
    """Real DLQ implementation from src.utils.dlq."""
    from src.utils.dlq import get_dlq_items as real_get
    return real_get()

def clear_dlq():
    """Real DLQ implementation from src.utils.dlq."""
    from src.utils.dlq import clear_dlq as real_clear
    real_clear()
