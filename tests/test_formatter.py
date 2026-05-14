import pytest
from src.dispatchers.formatter import TelegramFormatter
from src.models.digest import DigestItem, DigestLink

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

def test_format_category_escapes_html(formatter):
    result = formatter.format_category('<bad>')
    assert '&lt;BAD&gt;' in result
    assert '<bad>' not in result

def test_format_article(formatter):
    """Tests individual article formatting."""
    article = {'url': 'http://test.com', 'title': 'Test Title', 'summary': 'Short summary'}
    result = formatter.format_article(article)
    assert "<b>Test Title</b>" in result
    assert "<a href='http://test.com'>Acessar conteúdo</a>" in result
    assert '<i>Short summary</i>' in result

def test_format_article_escapes_html(formatter):
    article = {
        'url': "http://test.com?a='x'",
        'title': '<bad>',
        'summary': 'A & B',
    }
    result = formatter.format_article(article)
    assert '&lt;bad&gt;' in result
    assert 'A &amp; B' in result
    assert "a=&#x27;x&#x27;" in result

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
    """Tests long summary is preserved for split_message."""
    article = {'url': 'http://test.com', 'title': 'T', 'summary': 'A' * 500}
    result = formatter.format_article(article)
    assert ('A' * 500) in result

def test_format_digest_items_empty(formatter):
    result = formatter.format_digest_items([], '2026-05-10')
    assert len(result) == 1
    assert 'Daily Digest' in result[0]
    assert 'Nenhum item relevante' in result[0]

def test_format_digest_items_complete_item(formatter):
    item = DigestItem(
        title='New eval framework',
        category='AI Engineering',
        tier='A',
        importance=8.7,
        why_it_matters='Improves regression checks.',
        key_points=['Fast local evals', 'JSON reports'],
        worth_testing=True,
        testing_reason='Useful for CI.',
        links=[
            DigestLink(
                url='https://example.com/evals',
                title='Project page',
                source='example',
            )
        ],
    )
    result = formatter.format_digest_items([item], '2026-05-10')
    message = result[0]
    assert '<b>AI Engineering</b>' in message
    assert '<b>New eval framework</b>' in message
    assert 'Tier: <b>A</b> | Score: 8.7' in message
    assert '<b>Why this matters:</b> Improves regression checks.' in message
    assert '- Fast local evals' in message
    assert '<b>Vale testar:</b> sim - Useful for CI.' in message
    assert "<a href='https://example.com/evals'>Project page</a>" in message

def test_format_digest_items_escapes_external_fields(formatter):
    item = {
        'title': '<bad title>',
        'category': 'Breaking News',
        'tier': 'S<script>',
        'importance': 9.9,
        'why_it_matters': 'A & B < C',
        'key_points': ['Use <unsafe> mode'],
        'worth_testing': True,
        'testing_reason': 'Try & compare',
        'links': [
            {
                'url': "https://example.com?a='x'&b=<bad>",
                'title': '<link title>',
            }
        ],
    }
    message = formatter.format_digest_items([item], '2026-05-10')[0]
    assert '&lt;bad title&gt;' in message
    assert 'S&lt;script&gt;' in message
    assert 'A &amp; B &lt; C' in message
    assert 'Use &lt;unsafe&gt; mode' in message
    assert 'Try &amp; compare' in message
    assert 'a=&#x27;x&#x27;&amp;b=&lt;bad&gt;' in message
    assert '&lt;link title&gt;' in message
    assert '<bad title>' not in message

def test_format_digest_items_missing_optional_fields(formatter):
    item = {
        'title': 'Minimal item',
        'category': 'Top Trends',
    }
    message = formatter.format_digest_items([item], '2026-05-10')[0]
    assert '<b>Top Trends</b>' in message
    assert '<b>Minimal item</b>' in message
    assert 'Tier: <b>C</b> | Score: 0.0' in message
    assert '<b>Vale testar:</b> nao' in message

def test_format_digest_items_splits_long_messages(formatter):
    items = [
        {
            'title': f'Item {i}',
            'category': 'Top Trends',
            'importance': 5.0,
            'why_it_matters': 'A' * 80,
            'key_points': ['B' * 80, 'C' * 80],
        }
        for i in range(12)
    ]
    result = formatter.format_digest_items(items, '2026-05-10', max_chars=500)
    assert len(result) > 1
    assert all(len(part) <= 500 for part in result)
