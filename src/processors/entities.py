import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from src.models.entities import Entity


ALIAS_NORMALIZATION = {
    "mcp": ("Model Context Protocol", "protocol", "model context protocol"),
    "model context protocol": ("Model Context Protocol", "protocol", "model context protocol"),
    "llm": ("LLM", "concept", "large language model"),
    "large language model": ("LLM", "concept", "large language model"),
    "rag": ("RAG", "concept", "retrieval augmented generation"),
    "retrieval augmented generation": ("RAG", "concept", "retrieval augmented generation"),
}

KNOWN_ENTITIES = {
    "OpenAI": "company",
    "Anthropic": "company",
    "Google DeepMind": "company",
    "Meta": "company",
    "Microsoft": "company",
    "NVIDIA": "company",
    "LangChain": "framework",
    "LlamaIndex": "framework",
    "CrewAI": "framework",
    "AutoGen": "framework",
    "PyTorch": "framework",
    "TensorFlow": "framework",
    "Claude": "model",
    "Gemini": "model",
    "GPT-4": "model",
    "GPT-5": "model",
    "Llama": "model",
    "Qwen": "model",
    "Mistral": "model",
    "Model Context Protocol": "protocol",
}


def extract_entities(
    title: str = "",
    text: str = "",
    url: str = "",
    source: str = "",
    analysis: Optional[Dict[str, Any]] = None,
) -> List[Entity]:
    """Extracts deterministic, JSON-serializable entities from article context."""
    candidates: List[Entity] = []
    haystack = f"{title}\n{text}\n{url}\n{source}"

    repo = _github_repo_from_url(url)
    if repo:
        candidates.append(Entity(name=repo, type="github_repo", normalized_name=repo.lower()))

    for entity in _entities_from_analysis(analysis):
        candidates.append(entity)

    for name, entity_type in KNOWN_ENTITIES.items():
        if re.search(rf"\b{re.escape(name)}\b", haystack, flags=re.IGNORECASE):
            candidates.append(_normalize_entity(name, entity_type))

    for alias in ALIAS_NORMALIZATION:
        if re.search(rf"\b{re.escape(alias)}\b", haystack, flags=re.IGNORECASE):
            candidates.append(_normalize_entity(alias, "concept"))

    return _dedupe_entities(candidates)


def entities_to_dicts(entities: Iterable[Entity]) -> List[Dict[str, str]]:
    return [entity.to_dict() for entity in entities]


def _entities_from_analysis(analysis: Optional[Dict[str, Any]]) -> List[Entity]:
    if not analysis:
        return []
    raw_entities = analysis.get("entities") or []
    if not isinstance(raw_entities, list):
        return []

    entities: List[Entity] = []
    for raw in raw_entities:
        if isinstance(raw, dict):
            entity = Entity.from_dict(raw)
            entities.append(_normalize_entity(entity.name, entity.type))
        elif raw:
            entities.append(_normalize_entity(str(raw), "concept"))
    return entities


def _github_repo_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url or "")
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    return f"{parts[0]}/{parts[1]}"


def _normalize_entity(name: str, entity_type: str) -> Entity:
    cleaned = " ".join(str(name).strip().split())
    alias = ALIAS_NORMALIZATION.get(cleaned.lower())
    if alias:
        display_name, alias_type, normalized_name = alias
        return Entity(name=display_name, type=alias_type, normalized_name=normalized_name)
    return Entity(name=cleaned, type=entity_type, normalized_name=cleaned.lower())


def _dedupe_entities(entities: Iterable[Entity]) -> List[Entity]:
    deduped: Dict[str, Entity] = {}
    for entity in entities:
        if not entity.name or not entity.normalized_name:
            continue
        key = f"{entity.type}:{entity.normalized_name}"
        deduped.setdefault(key, entity)
    return list(deduped.values())
