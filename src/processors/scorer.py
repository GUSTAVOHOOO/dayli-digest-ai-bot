import os
import json
from src.celery_app import app
from src.models.article import Article
from src.models.scoring import AttentionScore
from src.storage.sqlite import save_article
from src.utils.logger import get_logger
from src.utils.metrics import metric_articles_processed, metric_items_discarded

log = get_logger(__name__)

MIN_SCORE_THRESHOLD = float(os.getenv('MIN_SCORE_THRESHOLD', '3.0'))
ATTENTION_SCORE_FIELDS = (
    "technical_depth",
    "novelty",
    "momentum",
    "community_adoption",
    "authority",
    "implementation_value",
    "cross_source_validation",
    "noise_risk",
)


def calculate_attention_score(analysis: dict, min_score: float = MIN_SCORE_THRESHOLD) -> AttentionScore:
    """Calculates the attention-economy score and tier for the new analysis contract."""
    breakdown = {
        "technical_depth": _clamp_score(analysis.get("technical_depth", 0.0)),
        "novelty": _clamp_score(analysis.get("novelty", 0.0)),
        "momentum": _clamp_score(analysis.get("momentum", 0.0)),
        "community_adoption": _clamp_score(analysis.get("community_adoption", 0.0)),
        "authority": _clamp_score(analysis.get("authority", 0.0)),
        "implementation_value": _clamp_score(analysis.get("implementation_value", 0.0)),
        "cross_source_validation": _clamp_score(analysis.get("cross_source_validation", 0.0)),
    }
    noise_risk = _clamp_score(analysis.get("noise_risk", 10.0))
    final_score = (
        breakdown["technical_depth"] * 0.20
        + breakdown["novelty"] * 0.20
        + breakdown["momentum"] * 0.20
        + breakdown["community_adoption"] * 0.15
        + breakdown["authority"] * 0.15
        + breakdown["implementation_value"] * 0.10
    ) - (noise_risk * 0.20)
    github_velocity = _clamp_score(analysis.get("github_velocity", analysis.get("repo_score", 0.0)))
    paper_intelligence = analysis.get("paper_intelligence") if isinstance(analysis.get("paper_intelligence"), dict) else {}
    paper_impact = _clamp_score(paper_intelligence.get("paper_impact_score", 0.0))
    wrapper_risk = _clamp_score(analysis.get("wrapper_risk", 0.0))
    final_score += github_velocity * 0.05
    final_score += paper_impact * 0.05
    if wrapper_risk >= 7.0:
        final_score -= wrapper_risk * 0.10
    if github_velocity:
        breakdown["github_velocity"] = github_velocity
    if paper_impact:
        breakdown["paper_impact_score"] = paper_impact
    if wrapper_risk:
        breakdown["wrapper_risk"] = wrapper_risk
    final_score = round(max(0.0, min(10.0, final_score)), 1)
    tier = classify_attention_tier(final_score, noise_risk)
    passed = final_score >= min_score and tier != "C"
    reason = _score_reason(final_score, tier, noise_risk, passed)
    return AttentionScore(
        final_score=final_score,
        tier=tier,
        score_breakdown=breakdown,
        noise_risk=noise_risk,
        passed=passed,
        reason=reason,
    )


def classify_attention_tier(score: float, noise_risk: float = 0.0) -> str:
    """Classifies content into digest tiers. S requires high score and low noise."""
    if score >= 8.8 and noise_risk <= 2.0:
        return "S"
    if score >= 7.5 and noise_risk <= 4.0:
        return "A"
    if score >= 5.5 and noise_risk <= 6.0:
        return "B"
    return "C"

def calculate_intelligent_score(analysis: dict) -> float:
    """Calculates a score from 0 to 10 based on technical analysis."""
    if all(
        field in analysis
        for field in ("technical_depth", "novelty", "authority", "implementation_value", "noise_risk")
    ):
        return calculate_attention_score(analysis).final_score

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


def _clamp_score(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, score))


def _score_reason(score: float, tier: str, noise_risk: float, passed: bool) -> str:
    if passed:
        return f"passed_attention_filter_tier_{tier}"
    if tier == "C":
        return "discarded_tier_c_low_attention_or_high_noise"
    if noise_risk > 6.0:
        return "discarded_high_noise_risk"
    return f"discarded_below_threshold_{score}"

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
        if all(field in analysis for field in ("technical_depth", "novelty", "authority", "implementation_value", "noise_risk")):
            attention_score = calculate_attention_score(analysis)
            score = attention_score.final_score
            analysis["score_breakdown"] = attention_score.score_breakdown
            analysis["attention_score"] = attention_score.to_dict()
            analysis["tier"] = attention_score.tier
            article_dict["analysis_json"] = json.dumps(analysis)
        else:
            attention_score = None
            score = calculate_intelligent_score(analysis)
    else:
        attention_score = None
        score = 0.0

    article_dict['score'] = score
    log.info(
        "intelligent_score_calculated",
        url=url,
        score=score,
        tier=attention_score.tier if attention_score else None,
        reason=attention_score.reason if attention_score else "legacy_score",
    )

    if score >= MIN_SCORE_THRESHOLD and (attention_score is None or attention_score.passed):
        article_dict['status'] = 'processed'
        log.info(
            "article_passed_filter",
            url=url,
            score=score,
            tier=attention_score.tier if attention_score else None,
            reason=attention_score.reason if attention_score else "legacy_threshold",
        )
        try:
            from src.processors.source_discovery import enqueue_source_suggestions

            analysis_for_discovery = json.loads(article_dict.get("analysis_json") or "{}")
            discovery_item = dict(article_dict)
            discovery_item["analysis"] = analysis_for_discovery
            discovery_item["entities"] = analysis_for_discovery.get("entities") or []
            enqueue_source_suggestions(discovery_item)
        except Exception as e:
            log.warning("source_discovery_failed", url=url, error=str(e))
        metric_articles_processed(1)
        
        # Trigger SUMMARIZER only for high-score articles
        if attention_score and attention_score.tier == "S":
            from src.dispatchers.telegram import send_realtime_alert

            alert_result = send_realtime_alert(article_dict)
            log.info("realtime_alert_evaluated", url=url, result=alert_result)

        from src.processors.summarizer import process_summarize
        process_summarize.delay(article_dict)
    else:
        article_dict['status'] = 'skipped'
        log.info(
            "article_filtered_out",
            url=url,
            score=score,
            tier=attention_score.tier if attention_score else None,
            reason=attention_score.reason if attention_score else "below_threshold",
        )
        metric_items_discarded(1, reason=attention_score.reason if attention_score else "below_threshold", source=article_dict.get("source"))
        # Save skipped article anyway to avoid re-processing
        article = Article.from_dict(article_dict)
        save_article(article)

    return {"status": "ok", "score": score}
