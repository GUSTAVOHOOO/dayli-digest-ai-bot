import json
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from src.utils.logger import get_logger


log = get_logger('metrics')


def emit_metric(
    event_name: str,
    metric_name: Optional[str] = None,
    count: float = 1,
    source: Optional[str] = None,
    reason: Optional[str] = None,
    duration_ms: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    """Logs and best-effort persists a local metric event."""
    event = {
        "event_name": event_name,
        "metric_name": metric_name or event_name,
        "count": count,
        "source": source,
        "reason": reason,
        "duration_ms": duration_ms,
        "metadata_json": json.dumps(metadata or {}, sort_keys=True),
    }
    log.info(
        "metric",
        metric=event["metric_name"],
        event_name=event_name,
        count=count,
        source=source,
        reason=reason,
        duration_ms=duration_ms,
        metadata=metadata or {},
    )
    try:
        from src.storage.sqlite import save_metric_event

        save_metric_event(event)
    except Exception as e:
        log.warning("metric_persist_failed", event=event_name, error=str(e))
    return event


@contextmanager
def measure_stage(stage: str, source: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    started = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
        emit_metric(
            event_name=f"{stage}_duration",
            metric_name="stage_duration_ms",
            source=source,
            duration_ms=duration_ms,
            metadata=metadata,
        )

def metric_articles_collected(count: int, source: str):
    """Logs metrics for collected articles."""
    emit_metric("articles_collected", count=count, source=source)

def metric_articles_processed(count: int):
    """Logs metrics for successfully processed articles."""
    emit_metric("articles_processed", count=count)

def metric_articles_failed(count: int, reason: str):
    """Logs metrics for failed article processing."""
    emit_metric("articles_failed", count=count, reason=reason)

def metric_dispatch_sent(count: int, chat_id: int):
    """Logs metrics for sent digest messages."""
    emit_metric("dispatch_sent", count=count, metadata={"chat_id": chat_id})

def metric_circuit_breaker_opened(source: str):
    """Logs circuit breaker open events."""
    emit_metric("circuit_breaker_opened", source=source)

def metric_dlq_items(count: int):
    """Logs current number of items in DLQ."""
    emit_metric("dlq_items", count=count)

def metric_dlq_retry(count: int):
    """Logs number of items retried from DLQ."""
    emit_metric("dlq_retry", count=count)


def metric_items_discarded(count: int, reason: str, source: Optional[str] = None):
    emit_metric("items_discarded", count=count, source=source, reason=reason)


def metric_clusters_generated(count: int):
    emit_metric("clusters_generated", count=count)


def metric_trends_detected(count: int):
    emit_metric("trends_detected", count=count)


def metric_llm_failure(reason: str, source: Optional[str] = None):
    emit_metric("llm_failure", source=source, reason=reason)
