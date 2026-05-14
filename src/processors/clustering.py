import hashlib
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from src.models.article import Article
from src.models.cluster import TopicCluster
from src.processors.entities import extract_entities
from src.processors.knowledge_graph import record_cluster_entities
from src.processors.scorer import classify_attention_tier
from src.utils.metrics import metric_clusters_generated


DEFAULT_EMBEDDING_THRESHOLD = 0.92


def cluster_analyzed_items(
    items: Iterable[Any],
    embedding_threshold: float = DEFAULT_EMBEDDING_THRESHOLD,
) -> List[TopicCluster]:
    """Groups analyzed items by embeddings when present, otherwise deterministic signals."""
    clusters: List[List[Dict[str, Any]]] = []
    normalized_items = [_item_to_dict(item) for item in items]

    for item in normalized_items:
        target_cluster = None
        for cluster in clusters:
            if _items_match(item, cluster[0], embedding_threshold):
                target_cluster = cluster
                break
        if target_cluster is None:
            clusters.append([item])
        else:
            target_cluster.append(item)

    built_clusters = [_build_cluster(cluster_items) for cluster_items in clusters]
    metric_clusters_generated(len(built_clusters))
    for cluster in built_clusters:
        try:
            record_cluster_entities(cluster)
        except Exception:
            pass
    return built_clusters


def _items_match(item: Dict[str, Any], other: Dict[str, Any], threshold: float) -> bool:
    item_embedding = item.get("embedding")
    other_embedding = other.get("embedding")
    if item_embedding and other_embedding:
        return _cosine_similarity(item_embedding, other_embedding) >= threshold

    item_repos = _github_repos(item)
    other_repos = _github_repos(other)
    if item_repos and item_repos.intersection(other_repos):
        return True

    item_entities = _entity_keys(item)
    other_entities = _entity_keys(other)
    if item_entities and item_entities.intersection(other_entities):
        return True

    return bool(_title_tokens(item).intersection(_title_tokens(other))) and _same_domain(item, other)


def _build_cluster(items: List[Dict[str, Any]]) -> TopicCluster:
    entities = _merge_entities(items)
    sources = sorted({str(item.get("source") or "") for item in items if item.get("source")})
    topic_name = _topic_name(items, entities)
    cluster_seed = "|".join(sorted(item.get("url", "") for item in items)) or topic_name

    return TopicCluster(
        cluster_id=hashlib.md5(cluster_seed.encode()).hexdigest(),
        topic_name=topic_name,
        items=items,
        entities=entities,
        sources=sources,
        cross_source_count=len(sources),
        final_score=max((float(item.get("score", 0.0) or 0.0) for item in items), default=0.0),
        tier=classify_attention_tier(
            max((float(item.get("score", 0.0) or 0.0) for item in items), default=0.0),
            noise_risk=0.0,
        ),
    )


def _item_to_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, Article):
        data = item.to_dict()
    elif hasattr(item, "to_dict"):
        data = item.to_dict()
    elif isinstance(item, dict):
        data = dict(item)
    else:
        data = {}

    analysis = data.get("analysis")
    if not isinstance(analysis, dict):
        analysis = _json_dict(data.get("analysis_json"))

    entities = analysis.get("entities") or data.get("entities") or []
    if not entities:
        entities = [
            entity.to_dict()
            for entity in extract_entities(
                title=str(data.get("title") or ""),
                text=str(data.get("clean_text") or data.get("summary") or ""),
                url=str(data.get("url") or ""),
                source=str(data.get("source") or ""),
                analysis=analysis,
            )
        ]

    links = data.get("links") or [{"url": data.get("url"), "title": data.get("title"), "source": data.get("source")}]
    return {
        "url": str(data.get("url") or ""),
        "title": str(data.get("title") or "Sem titulo"),
        "source": str(data.get("source") or ""),
        "score": float(data.get("score", data.get("importance", 0.0)) or 0.0),
        "summary": data.get("summary"),
        "analysis_json": data.get("analysis_json"),
        "analysis": analysis,
        "github_velocity": analysis.get("github_velocity") or data.get("github_velocity"),
        "paper_authority": analysis.get("paper_authority") or data.get("paper_authority"),
        "social_buzz": analysis.get("social_buzz") or data.get("social_buzz"),
        "entities": entities,
        "links": links,
        "embedding": data.get("embedding"),
    }


def _json_dict(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        import json

        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _entity_keys(item: Dict[str, Any]) -> Set[str]:
    keys: Set[str] = set()
    for entity in item.get("entities") or []:
        if isinstance(entity, dict):
            normalized = entity.get("normalized_name") or entity.get("name")
            entity_type = entity.get("type") or "concept"
            if normalized:
                keys.add(f"{entity_type}:{str(normalized).lower()}")
        elif entity:
            keys.add(f"concept:{str(entity).lower()}")
    return keys


def _github_repos(item: Dict[str, Any]) -> Set[str]:
    return {
        key.removeprefix("github_repo:")
        for key in _entity_keys(item)
        if key.startswith("github_repo:")
    }


def _title_tokens(item: Dict[str, Any]) -> Set[str]:
    title = str(item.get("title") or "").lower()
    return {token for token in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", title)}


def _same_domain(item: Dict[str, Any], other: Dict[str, Any]) -> bool:
    def domain(value: Dict[str, Any]) -> str:
        from urllib.parse import urlparse

        return urlparse(str(value.get("url") or "")).netloc.lower()

    return bool(domain(item) and domain(item) == domain(other))


def _merge_entities(items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    for item in items:
        for entity in item.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            normalized = str(entity.get("normalized_name") or entity.get("name") or "").lower()
            entity_type = str(entity.get("type") or "concept")
            if normalized:
                merged.setdefault(f"{entity_type}:{normalized}", {
                    "name": str(entity.get("name") or normalized),
                    "type": entity_type,
                    "normalized_name": normalized,
                })
    return list(merged.values())


def _topic_name(items: List[Dict[str, Any]], entities: List[Dict[str, str]]) -> str:
    priority = {"github_repo": 0, "model": 1, "framework": 2, "protocol": 3, "company": 4, "concept": 5}
    if entities:
        entity = sorted(entities, key=lambda item: priority.get(item.get("type", "concept"), 9))[0]
        return entity["name"]
    return str(items[0].get("title") or "Sem titulo")


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(a) * float(a) for a in left))
    right_norm = math.sqrt(sum(float(b) * float(b) for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)
