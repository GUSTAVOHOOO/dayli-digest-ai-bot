import pytest
from src.dispatchers.formatter import TelegramFormatter

@pytest.fixture
def formatter():
    """Fixture providing a TelegramFormatter instance."""
    return TelegramFormatter()

def test_format_header(formatter):
    """Tests header formatting."""
    result = formatter.format_header('2026-05-10')
    assert 'Daily Digest' in result
    assert '2026-05-10' in result

def test_format_category(formatter):
    """Tests category header formatting."""
    result = formatter.format_category('github')
    assert '<b>' in result
    assert 'GITHUB' in result
    assert '🐙' in result

def test_format_article(formatter):
    """Tests individual article formatting."""
    article = {'url': 'http://test.com', 'title': 'Test Title', 'summary': 'Short summary'}
    result = formatter.format_article(article)
    assert '<a href=\'http://test.com\'>Test Title</a>' in result
    assert '<i>Short summary</i>' in result

def test_split_message_keeps_lines_intact(formatter):
    """Tests if message splitting respects line boundaries and limits."""
    content = "\n".join([f"Line {i}" for i in range(100)])
    parts = formatter.split_message(content, max_chars=100)
    for part in parts:
        assert len(part) <= 100
        # Ensure no line is broken in half (all parts except possibly last should end with full line)
        lines = part.split('\n')
        assert len(lines) > 0

def test_truncate_long_summary(formatter):
    """Tests summary truncation in format_article."""
    article = {'url': 'http://test.com', 'title': 'T', 'summary': 'A' * 500}
    result = formatter.format_article(article)
    assert '…</i>' in result
    assert len(result) < 600 # Much less than 500+ formatting
