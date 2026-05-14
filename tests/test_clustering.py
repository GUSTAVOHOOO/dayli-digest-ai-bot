import json

from src.models.article import Article
from src.processors.clustering import cluster_analyzed_items


def test_same_repo_from_different_sources_becomes_one_cluster():
    items = [
        Article(
            url='https://github.com/openai/codex',
            source='github',
            title='Codex release',
            score=8.0,
            analysis_json=json.dumps({'entities': []}),
        ),
        Article(
            url='https://github.com/openai/codex/issues/1',
            source='blogs',
            title='Codex explained',
            score=7.0,
            analysis_json=json.dumps({'entities': []}),
        ),
    ]
    clusters = cluster_analyzed_items(items)
    assert len(clusters) == 1
    assert clusters[0].topic_name == 'openai/codex'
    assert clusters[0].cross_source_count == 2


def test_items_with_same_entities_cluster_without_embedding():
    items = [
        {'url': 'https://a.test/1', 'source': 'blogs', 'title': 'MCP guide', 'entities': [{'name': 'Model Context Protocol', 'type': 'protocol', 'normalized_name': 'model context protocol'}]},
        {'url': 'https://b.test/2', 'source': 'twitter', 'title': 'Agents and MCP', 'entities': [{'name': 'MCP', 'type': 'protocol', 'normalized_name': 'model context protocol'}]},
    ]
    clusters = cluster_analyzed_items(items)
    assert len(clusters) == 1
    assert clusters[0].topic_name == 'Model Context Protocol'


def test_clearly_different_items_stay_separate():
    items = [
        {'url': 'https://a.test/1', 'source': 'blogs', 'title': 'PyTorch kernel tuning'},
        {'url': 'https://b.test/2', 'source': 'papers', 'title': 'Claude tool calling evals'},
    ]
    clusters = cluster_analyzed_items(items)
    assert len(clusters) == 2


def test_embeddings_cluster_above_threshold_and_preserve_links():
    items = [
        {'url': 'https://a.test/1', 'source': 'blogs', 'title': 'Topic A', 'embedding': [1.0, 0.0], 'links': [{'url': 'https://a.test/1'}]},
        {'url': 'https://b.test/2', 'source': 'papers', 'title': 'Topic B', 'embedding': [0.99, 0.01], 'links': [{'url': 'https://b.test/2'}]},
    ]
    clusters = cluster_analyzed_items(items)
    assert len(clusters) == 1
    urls = {link['url'] for item in clusters[0].items for link in item['links']}
    assert urls == {'https://a.test/1', 'https://b.test/2'}
