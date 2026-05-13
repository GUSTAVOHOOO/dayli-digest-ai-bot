from unittest.mock import patch, MagicMock
from datetime import datetime
import json

def test_pipeline_flow():
    """Tests the conceptual flow of the pipeline from extraction to intelligent scoring."""
    article = {
        'url': 'http://test.com',
        'title': 'Test',
        'source': 'blogs',
        'md5_hash': 'abc123',
        'date_published': datetime.now().isoformat(),
    }

    with patch('src.processors.extractor.extract_with_crawl4ai') as mock_crawl, \
         patch('src.processors.summarizer.summarize') as mock_summarize, \
         patch('src.storage.sqlite.save_article') as mock_save:

        # 1. Extraction
        content = "Extracted content about SOTA AI benchmark. " * 5
        mock_crawl.return_value = content
        from src.processors.extractor import extract_article
        result = extract_article(article.copy())
        
        assert result['status'] == 'processed'
        assert result['clean_text'] == content

        # 2. Summarization
        mock_summarize.return_value = "This is a SOTA benchmark summary with GPT-5"
        from src.processors.summarizer import summarize
        summary = summarize(result, 'blogs')
        result['summary'] = summary
        
        assert result['summary'] == "This is a SOTA benchmark summary with GPT-5"

        # 3. Scoring
        from src.processors.scorer import calculate_intelligent_score
        score = calculate_intelligent_score({
            'author_authority': 'high',
            'content_type': 'breakthrough',
            'has_code': True,
            'complexity_level': 'expert',
            'technical_keywords': ['sota', 'benchmark', 'gpt'],
        })
        
        assert score == 10.0

def test_skip_low_score_articles():
    """Tests if low score articles are correctly identified."""
    from src.processors.scorer import calculate_intelligent_score
    score = calculate_intelligent_score({})
    assert score < 3.0

def test_orchestrator_skips_if_locked():
    """Tests if orchestrator correctly skips execution if lock is held."""
    with patch('src.orchestrator.acquire_digest_lock') as mock_lock:
        mock_lock.return_value = False
        from src.orchestrator import trigger_all
        result = trigger_all()
        assert result['status'] == 'skipped'
        assert result['reason'] == 'already_running'
