import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from src.utils.logger import get_logger

log = get_logger(__name__)

def retry_on_failure(max_attempts: int = 3, wait_min: int = 2, wait_max: int = 10):
    """Generic retry decorator for network-related failures."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=wait_min, min=wait_min, max=wait_max),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException, ConnectionError)),
        before_sleep=lambda retry_state: log.warning(
            "retrying_after_failure",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()),
        ),
    )

def retry_ollama(max_attempts: int = 2, wait: int = 5):
    """Specific retry decorator for Ollama calls."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=wait, min=wait, max=wait * 2),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=lambda retry_state: log.warning(
            "retrying_ollama",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()),
        ),
    )
