from src.utils.logger import get_logger

def metric_articles_collected(count: int, source: str):
    """Logs metrics for collected articles."""
    log = get_logger('metrics')
    log.info("metric", metric="articles_collected", count=count, source=source)

def metric_articles_processed(count: int):
    """Logs metrics for successfully processed articles."""
    log = get_logger('metrics')
    log.info("metric", metric="articles_processed", count=count)

def metric_articles_failed(count: int, reason: str):
    """Logs metrics for failed article processing."""
    log = get_logger('metrics')
    log.error("metric", metric="articles_failed", count=count, reason=reason)

def metric_dispatch_sent(count: int, chat_id: int):
    """Logs metrics for sent digest messages."""
    log = get_logger('metrics')
    log.info("metric", metric="dispatch_sent", count=count, chat_id=chat_id)

def metric_circuit_breaker_opened(source: str):
    """Logs circuit breaker open events."""
    log = get_logger('metrics')
    log.warning("metric", metric="circuit_breaker_opened", source=source)

def metric_dlq_items(count: int):
    """Logs current number of items in DLQ."""
    log = get_logger('metrics')
    log.info("metric", metric="dlq_items", count=count)

def metric_dlq_retry(count: int):
    """Logs number of items retried from DLQ."""
    log = get_logger('metrics')
    log.info("metric", metric="dlq_retry", count=count)
