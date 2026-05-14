from typing import Iterable, List

from src.models.cluster import TopicCluster
from src.processors.correlation import apply_cross_source_correlation
from src.processors.scorer import classify_attention_tier
from src.utils.metrics import metric_items_discarded, metric_trends_detected
from src.utils.logger import get_logger

log = get_logger(__name__)


def rank_trend_clusters(
    clusters: Iterable[TopicCluster],
    include_tier_c: bool = False,
) -> List[TopicCluster]:
    """Ranks clusters by deterministic trend signals."""
    ranked: List[TopicCluster] = []
    for cluster in apply_cross_source_correlation(clusters):
        cluster.trend_score = calculate_trend_score(cluster)
        cluster.tier = classify_attention_tier(cluster.final_score, noise_risk=0.0)
        if cluster.tier == "C" and not include_tier_c:
            log.info(
                "trend_cluster_discarded",
                cluster_id=cluster.cluster_id,
                topic=cluster.topic_name,
                tier=cluster.tier,
                trend_score=cluster.trend_score,
            )
            metric_items_discarded(1, reason="trend_tier_c", source="trend_engine")
            continue
        cluster.trend_signals = explain_trend_signals(cluster)
        log.info(
            "trend_cluster_ranked",
            cluster_id=cluster.cluster_id,
            topic=cluster.topic_name,
            trend_score=cluster.trend_score,
            signals=cluster.trend_signals,
        )
        ranked.append(cluster)

    ranked.sort(key=lambda cluster: (cluster.trend_score, cluster.final_score), reverse=True)
    metric_trends_detected(len(ranked))
    return ranked


def calculate_trend_score(cluster: TopicCluster) -> float:
    github_velocity = _max_item_signal(cluster, "github_velocity")
    paper_authority = _max_item_signal(cluster, "paper_authority")
    social_buzz = _max_item_signal(cluster, "social_buzz")
    cross_source_validation = cluster.cross_source_validation

    trend_score = (
        cross_source_validation * 0.30
        + github_velocity * 0.30
        + paper_authority * 0.20
        + social_buzz * 0.20
    )
    if trend_score == 0.0:
        trend_score = cluster.final_score * 0.5
    return round(max(0.0, min(10.0, trend_score)), 1)


def explain_trend_signals(cluster: TopicCluster) -> List[str]:
    signals = list(cluster.correlation_signals)
    for label, field in (
        ("GitHub velocity", "github_velocity"),
        ("paper authority", "paper_authority"),
        ("social buzz", "social_buzz"),
    ):
        value = _max_item_signal(cluster, field)
        if value > 0:
            signals.append(f"{label} {value:.1f}/10")
    if not signals:
        signals.append(f"score base {cluster.final_score:.1f}/10")
    return signals[:5]


def _max_item_signal(cluster: TopicCluster, field: str) -> float:
    values = []
    for item in cluster.items:
        value = item.get(field)
        if value is None and isinstance(item.get("analysis"), dict):
            value = item["analysis"].get(field)
        try:
            values.append(float(value or 0.0))
        except (TypeError, ValueError):
            values.append(0.0)
    return max(values, default=0.0)
