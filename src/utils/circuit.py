try:
    import pybreaker
except ImportError:
    pybreaker = None
try:
    import redis
except ImportError:
    redis = None
import os
from functools import wraps
from typing import Callable

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

_breakers = {}

def get_redis():
    """Provides a Redis client for circuit breaker state."""
    if redis is None:
        raise RuntimeError("redis package is not installed")
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)

def get_circuit_breaker(source: str):
    """Returns a singleton circuit breaker for a specific source."""
    if pybreaker is None:
        return _NoopBreaker()
    if source not in _breakers:
        # Use built-in CircuitRedisStorage if possible, or fallback to memory
        try:
            from redis import Redis
            client = redis.Redis.from_url(REDIS_URL)
            storage = pybreaker.CircuitRedisStorage(pybreaker.STATE_CLOSED, client, namespace=f"circuit:{source}")
        except Exception:
            # Fallback to memory storage if Redis fails or isn't available
            storage = pybreaker.CircuitMemoryStorage(pybreaker.STATE_CLOSED)
            
        _breakers[source] = pybreaker.CircuitBreaker(
            fail_max=3,
            reset_timeout=1800,  # 30 min
            state_storage=storage,
        )
    return _breakers[source]


class _NoopBreaker:
    def call(self, func: Callable, *args, **kwargs):
        return func(*args, **kwargs)

def circuit_breaker(source: str):
    """Decorator to apply circuit breaker to a function."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(source)
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
