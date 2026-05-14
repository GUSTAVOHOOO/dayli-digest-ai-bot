try:
    import httpx
except ImportError:
    class _HttpxUnavailable:
        @staticmethod
        def post(*args, **kwargs):
            raise RuntimeError("httpx package is not installed")

    httpx = _HttpxUnavailable()
import os
import json
from typing import Optional, Dict
import re
from src.utils.logger import get_logger
from src.utils.config_loader import load_config
from src.celery_app import app
from src.models.article import Article
from src.models.analysis import validate_analysis
from src.processors.entities import entities_to_dicts, extract_entities
from src.processors.knowledge_graph import novelty_score_for_entities, record_item_entities, record_repo_organization
from src.processors.papers_intelligence import analyze_paper_signals, apply_paper_intelligence
from src.processors.readme_intelligence import (
    apply_readme_intelligence,
    infer_readme_intelligence,
    validate_readme_intelligence,
)
from src.storage.sqlite import save_article
from src.utils.metrics import measure_stage, metric_llm_failure

log = get_logger(__name__)

OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:3b')
TIMEOUT = 45.0 # Analyzing takes a bit longer

def get_analysis_prompt(source: str, text: str, title: str) -> str:
    """Builds the analysis prompt based on source and content."""
    prompts = load_config('config/prompts.yaml')
    analysis_config = prompts.get('analysis_rules', {})
    
    # Generic rules + source specific rules
    generic_rules = analysis_config.get('generic', '')
    source_rules = analysis_config.get(source, analysis_config.get('blogs', ''))
    
    prompt = (
        f"{generic_rules}\n\n"
        f"REGRAS ESPECÍFICAS PARA {source.upper()}:\n{source_rules}\n\n"
        f"TÍTULO: {title}\n"
        f"CONTEÚDO: {text[:5000]}\n\n"
        f"RETORNE APENAS O JSON NO FORMATO SOLICITADO."
    )
    return prompt

def analyze_content(article: dict) -> Optional[Dict]:
    """Analyzes article content using Ollama to extract technical signals."""
    clean_text = article.get('clean_text', '')
    title = article.get('title', '')
    source = article.get('source', 'blogs')

    if not clean_text:
        return None

    prompt = get_analysis_prompt(source, clean_text, title)

    try:
        with measure_stage("llm_analysis", source=source, metadata={"url": article.get("url")}):
            response = httpx.post(
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json", # Force JSON output
                    "options": {
                        "temperature": 0.1, # Low temperature for consistent JSON
                        "num_predict": 500,
                    }
                },
                timeout=TIMEOUT,
            )

        response.raise_for_status()
        data = response.json()
        raw_json = data.get('response', '').strip()
        
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            metric_llm_failure("json_invalid", source=source)
            raise
        analysis = validate_analysis(parsed, url=article.get('url'))
        if analysis is None:
            metric_llm_failure("schema_invalid", source=source)
            return None
        analysis = _enrich_source_analysis(article, analysis, parsed)
        analysis["entities"] = entities_to_dicts(extract_entities(
            title=title,
            text=clean_text,
            url=article.get("url", ""),
            source=source,
            analysis=analysis,
        ))
        novelty_score = novelty_score_for_entities(analysis["entities"])
        analysis["novelty"] = max(float(analysis.get("novelty", 0.0) or 0.0), novelty_score)
        _record_knowledge(article, analysis["entities"])
        if source == "papers":
            paper = analyze_paper_signals(clean_text, title=title, entities=analysis["entities"])
            if isinstance(parsed.get("paper_intelligence"), dict):
                paper.update(parsed["paper_intelligence"])
            analysis = apply_paper_intelligence(analysis, paper)
        return analysis

    except Exception as e:
        reason = _analysis_failure_reason(e)
        if reason not in {"json_invalid", "schema_invalid"}:
            metric_llm_failure(reason, source=source)
        log.error("analysis_failed", url=article.get('url'), error=str(e))
        return None

@app.task(
    name='src.processors.analyzer.process_analyze',
    bind=True,
    max_retries=2,
    acks_late=True,
)
def process_analyze(self, article_dict: dict):
    """Celery task for the technical analysis phase."""
    url = article_dict.get('url', '')
    log.info("analysis_started", url=url)

    analysis = analyze_content(article_dict)
    
    if analysis:
        # We store the analysis as a JSON string in the article_dict
        article_dict['analysis_json'] = json.dumps(analysis)
        log.info("analysis_completed", url=url, type=analysis.get('content_type'))
        
        # Trigger Scorer phase
        from src.processors.scorer import process_score
        process_score.delay(article_dict)
        return {"status": "ok", "analysis": analysis}
    else:
        if article_dict.get('clean_text') and self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (self.request.retries + 1))

        # If analysis keeps failing, we still go to score but it might be lower
        from src.processors.scorer import process_score
        process_score.delay(article_dict)
        return {"status": "failed", "reason": "analysis_returned_none"}


def _enrich_source_analysis(article: dict, analysis: Dict, raw_analysis: Dict) -> Dict:
    source = article.get("source", "blogs")
    clean_text = article.get("clean_text", "")
    title = article.get("title", "")

    if source == "github":
        readme_data = validate_readme_intelligence(raw_analysis.get("readme_intelligence"))
        if readme_data == validate_readme_intelligence({}):
            readme_data = infer_readme_intelligence(clean_text, title=title)
        analysis = apply_readme_intelligence(analysis, readme_data)
        repo_metadata = _extract_repo_metadata(clean_text)
        if repo_metadata:
            velocity = repo_metadata.get("github_velocity") or {}
            analysis["repo"] = repo_metadata.get("repo") or {}
            analysis["repo_score"] = float(repo_metadata.get("repo_score", 0.0) or 0.0)
            analysis["github_velocity"] = float(velocity.get("repo_score", analysis["repo_score"]) or 0.0)
            analysis["github_velocity_signals"] = velocity.get("signals") or []
            analysis["momentum"] = max(float(analysis.get("momentum", 0.0) or 0.0), analysis["github_velocity"])
            analysis["community_adoption"] = max(
                float(analysis.get("community_adoption", 0.0) or 0.0),
                min(10.0, analysis["github_velocity"] + 1.0),
            )
    return analysis


def _extract_repo_metadata(text: str) -> Dict:
    match = re.search(r"Repo metadata JSON:\s*(\{[^\n]*\})", text or "")
    if not match:
        return {}
    try:
        data = json.loads(match.group(1).strip())
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _record_knowledge(article: dict, entities: list):
    try:
        record_item_entities(article, entities)
        for entity in entities:
            if isinstance(entity, dict) and entity.get("type") == "github_repo":
                record_repo_organization(entity)
    except Exception as e:
        log.warning("knowledge_record_failed", url=article.get("url"), error=str(e))


def _analysis_failure_reason(error: Exception) -> str:
    if isinstance(error, json.JSONDecodeError):
        return "json_invalid"
    name = type(error).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "http" in name:
        return "http_error"
    return "analysis_error"
