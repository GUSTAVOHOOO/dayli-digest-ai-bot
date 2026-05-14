from src.models.cluster import TopicCluster
from src.processors.trend_engine import calculate_trend_score, rank_trend_clusters


def test_trend_ranking_prefers_cross_source_validation():
    high_cross_source = TopicCluster(
        cluster_id='a',
        topic_name='Validated topic',
        final_score=7.0,
        tier='A',
        items=[
            {'url': 'https://github.com/openai/codex', 'source': 'github'},
            {'url': 'https://openai.com/blog/codex', 'source': 'blogs'},
            {'url': 'https://news.ycombinator.com/item?id=1', 'source': 'hn'},
        ],
    )
    isolated = TopicCluster(
        cluster_id='b',
        topic_name='Isolated topic',
        final_score=7.0,
        tier='A',
        items=[{'url': 'https://example.com/isolated', 'source': 'blogs'}],
    )

    ranked = rank_trend_clusters([isolated, high_cross_source])

    assert ranked[0].cluster_id == 'a'
    assert ranked[0].trend_score > ranked[1].trend_score


def test_trend_score_falls_back_without_github_velocity():
    cluster = TopicCluster(
        cluster_id='a',
        topic_name='Paper topic',
        final_score=8.0,
        cross_source_validation=6.0,
        items=[{'paper_authority': 7.0}],
    )

    assert calculate_trend_score(cluster) == 3.2


def test_trend_ranking_discards_tier_c_by_default():
    cluster = TopicCluster(
        cluster_id='c',
        topic_name='Low signal',
        final_score=4.0,
        tier='C',
        items=[{'url': 'https://example.com/low', 'source': 'blogs'}],
    )

    assert rank_trend_clusters([cluster]) == []
    assert len(rank_trend_clusters([cluster], include_tier_c=True)) == 1


def test_trend_score_is_clamped_between_zero_and_ten():
    cluster = TopicCluster(
        cluster_id='a',
        topic_name='Huge signals',
        final_score=10.0,
        cross_source_validation=99.0,
        items=[{'github_velocity': 99.0, 'paper_authority': 99.0, 'social_buzz': 99.0}],
    )

    assert calculate_trend_score(cluster) == 10.0
