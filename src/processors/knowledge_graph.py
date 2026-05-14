from typing import Any, Dict, Iterable, List, Optional

from src.storage.sqlite import (
    get_entities_related_to,
    get_entity_history,
    save_knowledge_relation,
    upsert_knowledge_entity,
)
from src.utils.logger import get_logger

log = get_logger(__name__)


def record_item_entities(item: Dict[str, Any], entities: Iterable[Dict[str, Any]]) -> List[int]:
    """Records entity appearances for an item URL/hash. Best-effort by caller."""
    relation_ids = []
    target_key = str(item.get("url") or item.get("md5_hash") or "")
    if not target_key:
        return relation_ids
    for entity in entities:
        try:
            entity_id = upsert_knowledge_entity(entity)
            relation_ids.append(save_knowledge_relation(
                entity_id,
                relation_type="appears_in_item",
                target_key=target_key,
                target_type="item",
                context_url=str(item.get("url") or ""),
            ))
        except Exception as e:
            log.warning("knowledge_item_entity_failed", entity=entity, error=str(e))
    return relation_ids


def record_cluster_entities(cluster) -> List[int]:
    """Records entity-cluster relations for a TopicCluster-like object."""
    relation_ids = []
    cluster_id = str(getattr(cluster, "cluster_id", "") or "")
    if not cluster_id:
        return relation_ids
    for entity in getattr(cluster, "entities", []) or []:
        try:
            entity_id = upsert_knowledge_entity(entity)
            relation_ids.append(save_knowledge_relation(
                entity_id,
                relation_type="belongs_to_cluster",
                target_key=cluster_id,
                target_type="cluster",
                context_url="",
            ))
        except Exception as e:
            log.warning("knowledge_cluster_entity_failed", cluster_id=cluster_id, entity=entity, error=str(e))
    return relation_ids


def record_repo_organization(repo_entity: Dict[str, Any]) -> Optional[int]:
    """Records owner relationship for github_repo entities like owner/repo."""
    repo_name = str(repo_entity.get("normalized_name") or repo_entity.get("name") or "")
    if "/" not in repo_name:
        return None
    org = repo_name.split("/", 1)[0]
    try:
        org_id = upsert_knowledge_entity({"name": org, "normalized_name": org.lower(), "type": "organization"})
        return save_knowledge_relation(
            org_id,
            relation_type="owns_repo",
            target_key=repo_name.lower(),
            target_type="github_repo",
        )
    except Exception as e:
        log.warning("knowledge_repo_org_failed", repo=repo_name, error=str(e))
        return None


def has_entity_appeared(normalized_name: str, entity_type: Optional[str] = None) -> bool:
    return bool(get_entity_history(normalized_name, entity_type=entity_type))


def novelty_score_for_entities(entities: Iterable[Dict[str, Any]]) -> float:
    """Returns high novelty when most entities have no graph history."""
    entity_list = list(entities or [])
    if not entity_list:
        return 5.0
    unseen = 0
    for entity in entity_list:
        normalized = str(entity.get("normalized_name") or entity.get("name") or "").lower()
        entity_type = str(entity.get("type") or "concept")
        if normalized and not has_entity_appeared(normalized, entity_type=entity_type):
            unseen += 1
    return round((unseen / len(entity_list)) * 10.0, 1)


def related_entities_for_topic(topic_key: str, target_type: str = "cluster") -> List[dict]:
    return get_entities_related_to(topic_key, target_type=target_type)
