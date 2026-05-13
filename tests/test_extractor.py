import pytest
from unittest.mock import patch, MagicMock
from src.processors.extractor import extract_article, extract_with_jina, extract_with_trafilatura

def test_extract_article_cache_hit(mock_redis):
    """Tests if extraction returns cached content before using network extractors."""
    mock_redis.get.return_value = "Cached Content"
    article = {'url': 'http://test.com', 'source': 'blogs', 'md5_hash': 'md5_url'}

    result = extract_article(article)

    assert result['clean_text'] == "Cached Content"
    assert result['status'] == 'processed'
    mock_redis.get.assert_called_once_with("jina_cache:md5_url")

def test_jina_success(mock_httpx):
    """Tests successful Jina extraction."""
    mock_get, mock_post = mock_httpx
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "Extracted Content"
    
    result = extract_with_jina("http://test.com", "md5_url")
    
    assert result == "Extracted Content"

def test_trafilatura_fallback():
    """Tests if trafilatura is used correctly."""
    with patch('trafilatura.fetch_url', return_value='<html>content</html>'), \
         patch('trafilatura.extract') as mock_traf:
        mock_traf.return_value = "Trafilatura Content"
        result = extract_with_trafilatura("http://test.com")
        assert result == "Trafilatura Content"
        mock_traf.assert_called_once()
