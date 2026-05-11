import time
import abc
from typing import List
import redis
import os
from src.models.article import Article
from src.utils.logger import get_logger

log = get_logger(__name__)

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

class RateLimiter:
    """Token bucket rate limiter using Redis."""
    def __init__(self, domain: str, max_tokens: int = 10, refill_seconds: int = 60):
        self.domain = domain
        self.max_tokens = max_tokens
        self.refill_seconds = refill_seconds
        self._redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self._key = f"rate:{domain}"

    def _refill(self):
        now = time.time()
        try:
            data = self._redis.hgetall(self._key)
            if not data:
                self._redis.hset(self._key, mapping={
                    'tokens': self.max_tokens,
                    'last_refill': now
                })
                return float(self.max_tokens)

            tokens = float(data.get('tokens', self.max_tokens))
            last_refill = float(data.get('last_refill', now))
            elapsed = now - last_refill
            refill_rate = self.max_tokens / self.refill_seconds
            new_tokens = min(float(self.max_tokens), tokens + elapsed * refill_rate)
            self._redis.hset(self._key, mapping={'tokens': new_tokens, 'last_refill': now})
            return new_tokens
        except (redis.RedisError, ValueError, TypeError):
            return float(self.max_tokens)

    def try_acquire(self) -> bool:
        """Tries to acquire a token, returns True if successful."""
        tokens = self._refill()
        if tokens >= 1:
            try:
                self._redis.hincrbyfloat(self._key, 'tokens', -1.0)
                return True
            except redis.RedisError:
                return True # Fallback: allow if redis is down
        return False

    def wait_time(self) -> float:
        """Returns the time in seconds until the next token is available."""
        tokens = self._refill()
        if tokens >= 1:
            return 0.0
        return (1.0 - tokens) / (self.max_tokens / self.refill_seconds)

class BaseCollector(abc.ABC):
    """Abstract base class for all news collectors."""
    source: str = ""

    def __init__(self):
        self.rate_limiter = RateLimiter(self.get_domain())

    @abc.abstractmethod
    def fetch(self) -> List[Article]:
        """Fetches articles from the source. Must be implemented by subclasses."""
        pass

    @abc.abstractmethod
    def get_domain(self) -> str:
        """Returns the domain for rate limiting."""
        pass

    def collect(self) -> List[Article]:
        """Orchestrates the collection process with rate limiting and logging."""
        if not self.rate_limiter.try_acquire():
            wait = self.rate_limiter.wait_time()
            log.warning("rate_limited", domain=self.get_domain(), wait_seconds=wait)
            time.sleep(wait)

        log.info("collect_started", source=self.source)
        try:
            articles = self.fetch()
            log.info("articles_collected", source=self.source, count=len(articles))
            return articles
        except Exception as e:
            log.error("collect_failed", source=self.source, error=str(e))
            raise
