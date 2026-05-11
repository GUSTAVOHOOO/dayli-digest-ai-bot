import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def sample_article():
    """Fixture providing a sample article dictionary."""
    return {
        'id': 1,
        'url': 'https://example.com/article',
        'title': 'Test Article',
        'source': 'blogs',
        'date_published': '2026-05-10',
        'md5_hash': 'abc123',
        'summary': 'This is a SOTA benchmark demo about AI',
        'score': 3.5,
        'status': 'processed',
        'clean_text': 'Full article text for processing...',
    }

@pytest.fixture
def mock_redis():
    """Fixture to mock Redis client globally."""
    with patch('src.storage.redis_cache.get_redis') as mock:
        redis_mock = MagicMock()
        mock.return_value = redis_mock
        # Also patch where it might be imported specifically
        with patch('src.utils.dlq.get_redis', return_value=redis_mock):
            yield redis_mock

@pytest.fixture
def mock_httpx():
    """Fixture to mock httpx calls (GET and POST)."""
    with patch('httpx.get') as mock_get, patch('httpx.post') as mock_post:
        mock_get.return_value = MagicMock(status_code=200, text='<html>test</html>')
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {'response': 'Summary'})
        yield (mock_get, mock_post)

@pytest.fixture
def mock_sqlite():
    """Fixture to mock SQLite storage calls."""
    with patch('src.storage.sqlite.save_article') as mock_save, \
         patch('src.storage.sqlite.is_article_processed') as mock_check:
        mock_save.return_value = 1
        mock_check.return_value = False
        yield (mock_save, mock_check)
