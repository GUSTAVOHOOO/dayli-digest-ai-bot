from datetime import datetime
from src.celery_app import app
from src.storage.redis_cache import acquire_digest_lock, release_digest_lock
from src.collectors.github import GitHubCollector
from src.collectors.arxiv import ArxivCollector
from src.collectors.blogs import BlogsCollector
from src.collectors.youtube import YouTubeCollector
from src.collectors.twitter import TwitterCollector
from src.utils.logger import get_logger

log = get_logger(__name__)

COLLECTORS = [
    GitHubCollector,
    ArxivCollector,
    BlogsCollector,
    YouTubeCollector,
    TwitterCollector,
]

@app.task(name='src.orchestrator.trigger_all', bind=True)
def trigger_all(self):
    """Main task to trigger all collectors."""
    today = datetime.now().strftime('%Y-%m-%d')

    if not acquire_digest_lock(today):
        log.warning("digest_already_running", date=today)
        return {"status": "skipped", "reason": "already_running"}

    try:
        total_collected = 0
        for collector_class in COLLECTORS:
            try:
                collector = collector_class()
                articles = collector.collect()
                total_collected += len(articles)

                # Queue for extract phase
                from src.processors.extractor import process_extract
                for article in articles:
                    process_extract.delay(article.to_dict())
            except Exception as e:
                log.error("collector_failed", source=collector_class.source, error=str(e))

        log.info("trigger_all_completed", total_collected=total_collected)
        return {"status": "ok", "collected": total_collected}

    finally:
        release_digest_lock(today)

@app.task(name='src.orchestrator.process_dispatch_placeholder', bind=True)
def process_dispatch_placeholder(self, article_dict):
    """Placeholder for dispatch task until Phase 3."""
    log.info("dispatch_queued_placeholder", url=article_dict.get('url'))
    pass

# Delete old process_extract placeholder
