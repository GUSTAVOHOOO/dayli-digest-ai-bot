import pytest
from unittest.mock import patch, MagicMock
from src.processors.summarizer import summarize, get_prompt_for_category

def test_get_prompt_for_category():
    """Tests prompt generation logic."""
    with patch('src.processors.summarizer.load_config') as mock_load:
        mock_load.return_value = {'blogs': {'system': 'Test System'}}
        prompt = get_prompt_for_category('blogs', 'Article Text', 'Article Title')
        assert 'Test System' in prompt
        assert 'Article Text' in prompt
        assert 'Article Title' in prompt

def test_summarize_success(mock_httpx):
    """Tests successful summarization via Ollama API."""
    mock_get, mock_post = mock_httpx
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'response': 'Summary Text', 'total_duration': 1000}
    mock_post.return_value = mock_response
    
    with patch('src.processors.summarizer.load_config', return_value={'blogs': {'system': 'S'}}):
        result = summarize({'clean_text': 'Text', 'title': 'Title', 'id': 1}, 'blogs')
        assert result == 'Summary Text'
        mock_post.assert_called_once()

def test_summarize_no_content():
    """Tests summarization with empty content."""
    result = summarize({'clean_text': '', 'id': 1}, 'blogs')
    assert result is None
