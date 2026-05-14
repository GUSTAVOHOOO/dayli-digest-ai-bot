import json
from unittest.mock import MagicMock, patch

from src.models.article import Article
from src.dispatchers.telegram import (
    article_to_digest_item,
    cluster_to_digest_item,
    process_dispatch,
    select_digest_articles,
)
from src.models.cluster import TopicCluster


def make_article(url, score, analysis=None):
    return Article(
        url=url,
        title=f'Title {score}',
        source='blogs',
        md5_hash=url,
        summary=f'Summary {score}',
        score=score,
        status='processed',
        analysis_json=json.dumps(analysis) if analysis is not None else None,
    )


def test_select_digest_articles_sorts_and_limits_by_score():
    articles = [
        make_article('a', 6.0),
        make_article('b', 9.0),
        make_article('c', 5.9),
        make_article('d', 8.0),
    ]
    selected = select_digest_articles(articles, max_items=2, min_score=6.0)
    assert [article.url for article in selected] == ['b', 'd']


def test_article_to_digest_item_uses_analysis_contract():
    article = make_article('https://example.com', 8.0, {
        'category': 'agent_ecosystem',
        'summary': 'Short analysis summary',
        'implementation_value': 8,
        'novelty': 7,
        'authority': 6,
        'technical_depth': 5,
        'why_it_matters': 'Important for agent tools.',
        'worth_testing': True,
        'key_points': ['MCP support'],
    })
    item = article_to_digest_item(article)
    assert item.category == 'Agent Ecosystem'
    assert item.tier == 'A'
    assert item.importance == 8.0
    assert item.why_it_matters == 'Important for agent tools.'
    assert item.worth_testing is True
    assert item.key_points == ['MCP support']


def test_cluster_to_digest_item_preserves_links_and_trend_signals():
    cluster = TopicCluster(
        cluster_id='c1',
        topic_name='Model Context Protocol',
        final_score=8.5,
        tier='A',
        cross_source_validation=8.0,
        trend_score=4.2,
        correlation_boost=1.2,
        trend_signals=['fonte oficial', 'confirmado por GitHub'],
        items=[
            {
                'url': 'https://github.com/modelcontextprotocol/servers',
                'title': 'MCP servers',
                'source': 'github',
                'links': [{'url': 'https://github.com/modelcontextprotocol/servers', 'title': 'Repo'}],
            },
            {
                'url': 'https://example.com/mcp',
                'title': 'MCP article',
                'source': 'blogs',
                'links': [{'url': 'https://example.com/mcp', 'title': 'Article'}],
            },
        ],
    )

    item = cluster_to_digest_item(cluster)

    assert item.title == 'Model Context Protocol'
    assert item.key_points == ['fonte oficial', 'confirmado por GitHub']
    assert [link.url for link in item.links] == [
        'https://github.com/modelcontextprotocol/servers',
        'https://example.com/mcp',
    ]


def test_process_dispatch_digest_without_articles():
    with patch('src.dispatchers.telegram.get_articles_by_date', return_value=[]), \
         patch('src.dispatchers.telegram.release_dispatch_schedule_lock') as release_schedule, \
         patch('src.dispatchers.telegram.release_digest_lock') as release_pipeline:
        result = process_dispatch.run(chat_id=123)

    assert result == {'status': 'ok', 'sent': 0}
    release_schedule.assert_called_once()
    release_pipeline.assert_called_once()


def test_process_dispatch_partial_send_does_not_mark_sent():
    articles = [make_article('a', 9.0), make_article('b', 8.0)]
    dispatcher = MagicMock()
    dispatcher.send_messages_sync.return_value = 0

    with patch('src.dispatchers.telegram.get_articles_by_date', return_value=articles), \
         patch('src.dispatchers.telegram.TelegramDispatcher', return_value=dispatcher), \
         patch('src.dispatchers.telegram.save_article') as save_article, \
         patch('src.dispatchers.telegram.release_dispatch_schedule_lock'), \
         patch('src.dispatchers.telegram.release_digest_lock'):
        result = process_dispatch.run(chat_id=123)

    assert result['selected_articles'] == 2
    assert result['sent'] == 0
    save_article.assert_not_called()


def test_process_dispatch_mark_sent_false_preserves_status():
    articles = [make_article('a', 9.0)]
    dispatcher = MagicMock()
    dispatcher.send_messages_sync.return_value = 1

    with patch('src.dispatchers.telegram.get_articles_by_date', return_value=articles), \
         patch('src.dispatchers.telegram.TelegramDispatcher', return_value=dispatcher), \
         patch('src.dispatchers.telegram.save_article') as save_article, \
         patch('src.dispatchers.telegram.release_dispatch_schedule_lock'), \
         patch('src.dispatchers.telegram.release_digest_lock'):
        result = process_dispatch.run(chat_id=123, mark_sent=False)

    assert result['selected_articles'] == 1
    save_article.assert_not_called()
    assert articles[0].status == 'processed'
