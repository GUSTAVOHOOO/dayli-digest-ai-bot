import pytest
from unittest.mock import patch, MagicMock
import json

def test_add_to_dlq(mock_redis):
    """Tests adding an item to the DLQ."""
    from src.utils.dlq import add_to_dlq
    
    with patch('builtins.open', MagicMock()), \
         patch('pathlib.Path.mkdir', MagicMock()):
        add_to_dlq({'url': 'http://test.com', 'title': 'Test'}, 'Timeout')
    
    mock_redis.lpush.assert_called_once()
    args, _ = mock_redis.lpush.call_args
    assert 'http://test.com' in args[1]
    assert 'Timeout' in args[1]

def test_retry_dlq(mock_redis):
    """Tests retrying items from the DLQ."""
    mock_redis.lrange.return_value = [
        json.dumps({'url': 'http://test1.com', 'error': 'E', 'timestamp': 'T'}),
        json.dumps({'url': 'http://test2.com', 'error': 'E', 'timestamp': 'T'})
    ]
    
    with patch('src.processors.extractor.process_extract.delay') as mock_task:
        from src.utils.dlq import retry_dlq
        count = retry_dlq()
        
        assert count == 2
        assert mock_task.call_count == 2
        mock_redis.delete.assert_called_once()

def test_clear_dlq(mock_redis):
    """Tests clearing the DLQ."""
    from src.utils.dlq import clear_dlq
    clear_dlq()
    mock_redis.delete.assert_called_once()
