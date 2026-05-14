from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse

from src.storage.sqlite import save_source_suggestion
from src.utils.logger import get_logger

log = get_logger(__name__)

COMPANY_OFFICIAL_SITES = {
    "openai": "https://openai.com/news/",
    "anthropic": "https://www.anthropic.com/news",
    "google deepmind": "https://deepmind.google/blog/",
    "meta": "https://ai.meta.com/blog/",
    "microsoft": "https://blogs.microsoft.com/ai/",
    "nvidia": "https://blogs.nvidia.com/blog/category/deep-learning/",
    "hugging face": "https://huggingface.co/blog",
    "langchain": "https://blog.langchain.dev/",
    "llamaindex": "https://www.llamaindex.ai/blog",
}


def discover_source_suggestions(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """Builds pending source suggestions from strong repo/entity signals."""
    suggestions: List[Dict[str, str]] = []
    url = str(item.get("url") or "")
    analysis = item.get("analysis") if isinstance(item.get("analysis"), dict) else {}
    entities = item.get("entities") or analysis.get("entities") or []

    github_org = _github_org(url)
    if github_org:
        suggestions.extend([
            _suggestion(
                source_url=f"https://github.com/{github_org}",
                source_type="github_org",
                entity=github_org,
                reason="Repo GitHub relevante encontrado; revisar organizacao para novas releases.",
                origin_url=url,
            ),
            _suggestion(
                source_url=f"https://github.com/{github_org}.atom",
                source_type="blog",
                entity=github_org,
                reason="Feed Atom de organizacao GitHub candidata para releases e repos novos.",
                origin_url=url,
            ),
        ])

    for entity in entities:
        name = _entity_name(entity)
        normalized = name.lower()
        official_site = COMPANY_OFFICIAL_SITES.get(normalized)
        if official_site:
            suggestions.append(_suggestion(
                source_url=official_site,
                source_type="blog",
                entity=name,
                reason="Entidade forte apareceu em item relevante; revisar fonte oficial.",
                origin_url=url,
            ))

    return _dedupe(suggestions)


def enqueue_source_suggestions(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Persists suggestions with pending status. Never activates sources automatically."""
    saved = []
    for suggestion in discover_source_suggestions(item):
        try:
            row = save_source_suggestion(suggestion)
            log.info(
                "source_suggestion_created",
                source_url=suggestion["source_url"],
                source_type=suggestion["source_type"],
                entity=suggestion["entity"],
                origin_url=suggestion.get("origin_url"),
            )
            saved.append(row)
        except Exception as e:
            log.warning("source_suggestion_failed", source_url=suggestion.get("source_url"), error=str(e))
    return saved


def _suggestion(source_url: str, source_type: str, entity: str, reason: str, origin_url: str) -> Dict[str, str]:
    return {
        "source_url": source_url,
        "source_type": source_type,
        "entity": entity,
        "reason": reason,
        "origin_url": origin_url,
        "status": "pending",
    }


def _github_org(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    if domain != "github.com":
        return ""
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    return parts[0] if len(parts) >= 2 else ""


def _entity_name(entity: Any) -> str:
    if isinstance(entity, dict):
        return str(entity.get("normalized_name") or entity.get("name") or "").strip()
    return str(entity or "").strip()


def _dedupe(suggestions: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped = []
    for suggestion in suggestions:
        key = suggestion["source_url"].rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(suggestion)
    return deduped
