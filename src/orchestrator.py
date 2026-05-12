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

GLOBAL_MAX_ARTICLES = 100

@app.task(name='src.orchestrator.trigger_all', bind=True)
def trigger_all(self):
    """Main task to trigger all collectors with a fair distribution limit."""
    today = datetime.now().strftime('%Y-%m-%d')

    if not acquire_digest_lock(today):
        log.warning("digest_already_running", date=today)
        return {"status": "skipped", "reason": "already_running"}

    try:
        all_articles = []
        for collector_class in COLLECTORS:
            try:
                collector = collector_class()
                articles = collector.collect()
                # Store with source info for fair distribution
                for a in articles:
                    all_articles.append(a)
                log.info("collector_finished", source=collector_class.source, count=len(articles))
            except Exception as e:
                log.error("collector_failed", source=collector_class.source, error=str(e))

        # Fair distribution: we want a mix of sources
        # Simple approach: shuffle or sort by source and take top N
        import random
        random.shuffle(all_articles) # Randomize to avoid one source dominating the start
        
        articles_to_queue = all_articles[:GLOBAL_MAX_ARTICLES]
        
        # Queue for extract phase
        from src.processors.extractor import process_extract
        for article in articles_to_queue:
            process_extract.delay(article.to_dict())

        log.info("trigger_all_completed", total_collected=len(articles_to_queue), total_found=len(all_articles))
        return {"status": "ok", "collected": len(articles_to_queue), "date": today}

    finally:
        release_digest_lock(today)

@app.task(name='src.orchestrator.process_dispatch_placeholder', bind=True)
def process_dispatch_placeholder(self, article_dict):
    """Triggers the real telegram dispatch."""
    log.info("triggering_real_dispatch", url=article_dict.get('url'))
    from src.dispatchers.telegram import process_dispatch
    # We delay the dispatch slightly to allow other articles in the same batch to finish
    # or we could use a separate trigger. For now, let's call the real one.
    process_dispatch.delay()
    pass

# Delete old process_extract placeholder
