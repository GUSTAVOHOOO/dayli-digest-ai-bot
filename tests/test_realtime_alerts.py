import json
from unittest.mock import MagicMock, patch

from src.dispatchers.formatter import TelegramFormatter
from src.dispatchers.telegram import send_realtime_alert, should_send_realtime_alert
from src.models.article import Article
from src.models.digest import DigestItem, DigestLink


def make_article(tier='S'):
    return Article(
        url='https://example.com/api-release',
        source='blogs',
        title='Critical API release for a major model',
        md5_hash='alert-hash',
        score=9.2,
        summary='Major model API release.',
        analysis_json=json.dumps({
            'tier': tier,
            'summary': 'Critical API release.',
            'why_it_matters': 'Breakthrough API change for production agents.',
            'key_points': ['API release'],
            'entities': [{'name': 'GPT-5', 'type': 'model', 'normalized_name': 'gpt-5'}],
        }),
    )


def test_tier_s_realtime_candidate_triggers():
    assert should_send_realtime_alert(make_article()) is True


def test_tier_a_realtime_candidate_does_not_trigger():
    assert should_send_realtime_alert(make_article(tier='A')) is False


def test_realtime_alert_uses_daily_dedup_lock():
    dispatcher = MagicMock()
    dispatcher.send_messages_sync.return_value = 1

    with patch('src.dispatchers.telegram.acquire_realtime_alert_lock', return_value=False) as lock, \
         patch('src.dispatchers.telegram.TelegramDispatcher', return_value=dispatcher):
        result = send_realtime_alert(make_article(), chat_id=123, date='2026-05-14')

    assert result == {'status': 'skipped', 'reason': 'duplicate_alert'}
    lock.assert_called_once()
    dispatcher.send_messages_sync.assert_not_called()


def test_realtime_alert_format_is_html_safe():
    item = DigestItem(
        title='<bad>',
        category='Breaking News',
        tier='S',
        importance=9.8,
        why_it_matters='A & B < C',
        links=[DigestLink(url="https://example.com?a='x'&b=<bad>", title='<link>')],
    )

    message = TelegramFormatter().format_realtime_alert(item)

    assert '&lt;bad&gt;' in message
    assert 'A &amp; B &lt; C' in message
    assert "a=&#x27;x&#x27;&amp;b=&lt;bad&gt;" in message
    assert '<bad>' not in message
