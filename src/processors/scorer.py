import os
import json
from src.celery_app import app
from src.models.article import Article
from src.storage.sqlite import save_article
from src.utils.logger import get_logger

log = get_logger(__name__)

MIN_SCORE_THRESHOLD = float(os.getenv('MIN_SCORE_THRESHOLD', '3.0'))

def calculate_intelligent_score(analysis: dict) -> float:
    """Calculates a score from 0 to 10 based on technical analysis."""
    score = 0.0
    
    # Authority (Max 3.0)
    authority = analysis.get('author_authority')
    if authority == 'high': score += 3.0
    elif authority == 'medium': score += 1.5
    
    # Content Type (Max 3.0)
    ctype = analysis.get('content_type')
    if ctype == 'breakthrough': score += 3.0
    elif ctype == 'educational': score += 2.5
    elif ctype == 'news': score += 1.0
    
    # Technical Signals (Max 4.0)
    if analysis.get('has_code'): score += 2.0
    
    complexity = analysis.get('complexity_level')
    if complexity == 'expert': score += 2.0
    elif complexity == 'intermediate': score += 1.0
    
    keywords = analysis.get('technical_keywords', [])
    score += min(len(keywords) * 0.2, 1.0) # Bonus for many technical terms

    return min(score, 10.0)

@app.task(
    name='src.processors.scorer.process_score',
    bind=True,
    acks_late=True,
)
def process_score(self, article_dict: dict):
    """Celery task for the intelligent scoring phase."""
    url = article_dict.get('url', '')
    analysis_raw = article_dict.get('analysis_json')
    
    if analysis_raw:
        analysis = json.loads(analysis_raw)
        score = calculate_intelligent_score(analysis)
    else:
        score = 0.0

    article_dict['score'] = score
    log.info("intelligent_score_calculated", url=url, score=score)

    if score >= MIN_SCORE_THRESHOLD:
        article_dict['status'] = 'processed'
        log.info("article_passed_filter", url=url, score=score)
        
        # Trigger SUMMARIZER only for high-score articles
        from src.processors.summarizer import process_summarize
        process_summarize.delay(article_dict)
    else:
        article_dict['status'] = 'skipped'
        log.info("article_filtered_out", url=url, score=score)
        # Save skipped article anyway to avoid re-processing
        article = Article.from_dict(article_dict)
        save_article(article)

    return {"status": "ok", "score": score}
