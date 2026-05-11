import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

def test_pipeline_flow():
    """Tests the conceptual flow of the pipeline from extraction to scoring."""
    article = {
        'url': 'http://test.com',
        'title': 'Test',
        'source': 'blogs',
        'md5_hash': 'abc123',
        'date_published': datetime.now().isoformat(),
    }

    with patch('src.processors.extractor.extract_with_jina') as mock_jina, \
         patch('src.processors.summarizer.summarize') as mock_summarize, \
         patch('src.storage.sqlite.save_article') as mock_save:

        # 1. Extraction
        content = "Extracted content about SOTA AI benchmark. " * 5
        mock_jina.return_value = content
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
        from src.processors.scorer import calculate_score
        score = calculate_score(result['summary'])
        
        assert score >= 3.0  # SOTA(1) + benchmark(1) + GPT-5(1) = 3.0
        # POSITIVE_KEYWORDS = {"SOTA", "state-of-the-art", "benchmark", "GPT-5", "DeepSeek", "open source", "vulnerability", "breakthrough"}
        # "SOTA benchmark" has SOTA and benchmark -> 2.0
        # If I want it to be >= 3.0, I need more keywords or check logic
        # Text "This is a SOTA benchmark summary" -> SOTA(1), benchmark(1) -> 2.0
        # Let's adjust expected score or input text
        
        text_high_score = "SOTA benchmark GPT-5 breakthrough"
        assert calculate_score(text_high_score) == 4.0

def test_skip_low_score_articles():
    """Tests if low score articles are correctly identified."""
    from src.processors.scorer import calculate_score
    summary = "Just a simple demo"
    score = calculate_score(summary)
    assert score < 3.0

def test_orchestrator_skips_if_locked():
    """Tests if orchestrator correctly skips execution if lock is held."""
    with patch('src.orchestrator.acquire_digest_lock') as mock_lock:
        mock_lock.return_value = False
        from src.orchestrator import trigger_all
        result = trigger_all()
        assert result['status'] == 'skipped'
        assert result['reason'] == 'already_running'
