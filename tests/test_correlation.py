from src.models.cluster import TopicCluster
from src.processors.correlation import apply_cross_source_correlation, correlate_cluster


def test_correlation_boosts_github_official_blog_and_hn_cluster():
    cluster = TopicCluster(
        cluster_id='c1',
        topic_name='Codex',
        final_score=7.0,
        items=[
            {'url': 'https://github.com/openai/codex', 'source': 'github'},
            {'url': 'https://openai.com/blog/codex', 'source': 'blogs'},
            {'url': 'https://news.ycombinator.com/item?id=1', 'source': 'hn'},
        ],
    )

    [result] = apply_cross_source_correlation([cluster])

    assert result.cross_source_count == 3
    assert result.cross_source_validation == 10.0
    assert result.correlation_boost == 1.5
    assert result.final_score == 8.5
    assert 'fonte oficial' in result.correlation_signals


def test_correlation_boost_is_idempotent():
    cluster = TopicCluster(
        cluster_id='c1',
        topic_name='Codex',
        final_score=7.0,
        items=[
            {'url': 'https://github.com/openai/codex', 'source': 'github'},
            {'url': 'https://openai.com/blog/codex', 'source': 'blogs'},
        ],
    )

    [first] = apply_cross_source_correlation([cluster])
    [second] = apply_cross_source_correlation([first])

    assert first.final_score == second.final_score


def test_same_domain_links_do_not_count_as_high_diversity():
    cluster = TopicCluster(
        cluster_id='c1',
        topic_name='Same domain',
        final_score=7.0,
        items=[
            {'url': 'https://example.com/a', 'source': 'blogs'},
            {'url': 'https://example.com/b', 'source': 'blogs'},
            {'url': 'https://example.com/c', 'source': 'blogs'},
        ],
    )

    result = correlate_cluster(cluster)

    assert result.independent_sources == 1
    assert result.correlation_boost == 0.0


def test_isolated_official_source_has_validation_without_boost():
    cluster = TopicCluster(
        cluster_id='c1',
        topic_name='OpenAI API',
        final_score=9.0,
        items=[{'url': 'https://openai.com/index/api-update', 'source': 'blogs'}],
    )

    result = correlate_cluster(cluster)

    assert result.independent_sources == 1
    assert result.cross_source_validation == 4.0
    assert result.correlation_boost == 0.0
    assert 'fonte oficial' in result.signals
