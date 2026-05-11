import os
from celery import Task
from src.celery_app import app
from src.models.article import Article
from src.storage.sqlite import save_article
from src.utils.logger import get_logger

log = get_logger(__name__)

POSITIVE_KEYWORDS = {
    "SOTA", "state-of-the-art", "benchmark", "GPT-5",
    "DeepSeek", "open source", "vulnerability", "breakthrough"
}

NEUTRAL_KEYWORDS = {"demo", "review", "opinion"}

MAX_SCORE = 5.0
MIN_SCORE_THRESHOLD = float(os.getenv('MIN_SCORE_THRESHOLD', '3'))

def calculate_score(text: str) -> float:
    """Calculates article relevance score based on keywords."""
    if not text:
        return 0.0

    text_lower = text.lower()
    score = 0.0

    for kw in POSITIVE_KEYWORDS:
        # Count occurrences, but a single keyword shouldn't dominate too much? 
        # The spec says +1 each, let's assume existence for now or simple count.
        # Snippet base uses count().
        score += text_lower.count(kw.lower())

    for kw in NEUTRAL_KEYWORDS:
        score += 0.5 * text_lower.count(kw.lower())

    return min(score, MAX_SCORE)

@app.task(
    name='src.processors.scorer.process_score',
    bind=True,
    acks_late=True,
)
def process_score(self, article_dict: dict):
    """Celery task for the scoring phase."""
    url = article_dict.get('url', '')
    summary = article_dict.get('summary', '')

    score = calculate_score(summary)
    article_dict['score'] = score

    log.info("score_calculated", url=url, score=score)

    if score >= MIN_SCORE_THRESHOLD:
        article_dict['status'] = 'processed'
        log.info("article_queued_for_dispatch", url=url, score=score)
        
        # Import here to avoid circular dependency
        from src.orchestrator import process_dispatch_placeholder
        process_dispatch_placeholder.delay(article_dict)
    else:
        article_dict['status'] = 'skipped'
        log.info("score_too_low", url=url, score=score, status="skipped")

    # Save final result to SQLite
    article = Article.from_dict(article_dict)
    save_article(article)

    return {"status": "ok", "score": score}
