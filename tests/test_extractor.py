import pytest
from unittest.mock import patch, MagicMock
from src.processors.extractor import extract_with_jina, extract_with_trafilatura

def test_jina_cache_hit(mock_redis):
    """Tests if Jina extraction returns cached content if available."""
    mock_redis.get.return_value = "Cached Content"
    result = extract_with_jina("http://test.com", "md5_url")
    assert result == "Cached Content"
    mock_redis.get.assert_called_once_with("jina_cache:md5_url")

def test_jina_cache_miss_success(mock_redis, mock_httpx):
    """Tests successful Jina extraction on cache miss."""
    mock_get, mock_post = mock_httpx
    mock_redis.get.return_value = None
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "Extracted Content"
    
    result = extract_with_jina("http://test.com", "md5_url")
    
    assert result == "Extracted Content"
    mock_redis.setex.assert_called_once()

def test_trafilatura_fallback():
    """Tests if trafilatura is used correctly."""
    with patch('trafilatura.extract') as mock_traf:
        mock_traf.return_value = "Trafilatura Content"
        result = extract_with_trafilatura("http://test.com")
        assert result == "Trafilatura Content"
        mock_traf.assert_called_once()
