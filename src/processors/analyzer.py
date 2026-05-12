import httpx
import os
import json
from typing import Optional, Dict
from src.utils.logger import get_logger
from src.utils.config_loader import load_config
from src.celery_app import app
from src.models.article import Article
from src.storage.sqlite import save_article

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
        
        return json.loads(raw_json)

    except Exception as e:
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
        # If analysis fails, we still go to score but it might be lower
        from src.processors.scorer import process_score
        process_score.delay(article_dict)
        return {"status": "failed", "reason": "analysis_returned_none"}
