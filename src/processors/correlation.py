from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Set
from urllib.parse import urlparse

from src.models.cluster import TopicCluster


SOURCE_WEIGHTS = {
    "official": 4.0,
    "github": 3.0,
    "paper": 3.0,
    "papers": 3.0,
    "arxiv": 3.0,
    "hn": 2.0,
    "hackernews": 2.0,
    "reddit": 2.0,
    "youtube": 1.0,
    "twitter": 1.0,
    "x": 1.0,
    "blogs": 1.5,
}

OFFICIAL_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "ai.google",
    "microsoft.com",
    "meta.com",
    "nvidia.com",
}


@dataclass
class CorrelationResult:
    cross_source_validation: float
    correlation_boost: float
    independent_sources: int
    domains: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def correlate_cluster(cluster: TopicCluster) -> CorrelationResult:
    """Calculates cross-source validation without treating same-domain links as independent."""
    source_types: Set[str] = set()
    domains: Set[str] = set()

    for item in cluster.items:
        source_type = _source_type(item)
        domain = _domain_from_item(item)
        if domain:
            domains.add(domain)
            if _is_official_domain(domain):
                source_type = "official"
        source_types.add(source_type)

    independent_sources = len(domains) if domains else len(source_types)
    weighted_signal = sum(SOURCE_WEIGHTS.get(source_type, 1.0) for source_type in source_types)
    diversity_bonus = max(0, independent_sources - 1) * 1.5
    cross_source_validation = min(10.0, round(weighted_signal + diversity_bonus, 1))
    correlation_boost = round(cross_source_validation * 0.15, 1) if independent_sources >= 2 else 0.0

    signals = _signals(source_types, domains, independent_sources, cross_source_validation)
    return CorrelationResult(
        cross_source_validation=cross_source_validation,
        correlation_boost=correlation_boost,
        independent_sources=independent_sources,
        domains=sorted(domains),
        signals=signals,
    )


def apply_cross_source_correlation(clusters: Iterable[TopicCluster]) -> List[TopicCluster]:
    """Applies correlation metadata and score boost to clusters."""
    correlated = []
    for cluster in clusters:
        result = correlate_cluster(cluster)
        base_score = max(0.0, float(cluster.final_score or 0.0) - float(cluster.correlation_boost or 0.0))
        cluster.cross_source_count = result.independent_sources
        cluster.cross_source_validation = result.cross_source_validation
        cluster.correlation_boost = result.correlation_boost
        cluster.correlation_signals = result.signals
        cluster.final_score = min(10.0, round(base_score + result.correlation_boost, 1))
        correlated.append(cluster)
    return correlated


def _source_type(item: Dict[str, Any]) -> str:
    source = str(item.get("source") or "").strip().lower().replace("-", "_")
    if source in SOURCE_WEIGHTS:
        return source
    if source in {"hacker_news", "hacker-news"}:
        return "hn"
    return "blogs"


def _domain_from_item(item: Dict[str, Any]) -> str:
    urls = []
    if item.get("url"):
        urls.append(str(item["url"]))
    for link in item.get("links") or []:
        if isinstance(link, dict) and link.get("url"):
            urls.append(str(link["url"]))
    for url in urls:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain:
            return domain
    return ""


def _is_official_domain(domain: str) -> bool:
    return any(domain == official or domain.endswith(f".{official}") for official in OFFICIAL_DOMAINS)


def _signals(source_types: Set[str], domains: Set[str], independent_sources: int, validation: float) -> List[str]:
    signals = [f"{independent_sources} fonte(s) independente(s)", f"validacao cruzada {validation:.1f}/10"]
    if "official" in source_types:
        signals.append("fonte oficial")
    if "github" in source_types:
        signals.append("confirmado por GitHub")
    if source_types.intersection({"paper", "papers", "arxiv"}):
        signals.append("confirmado por paper")
    if source_types.intersection({"hn", "hackernews", "reddit"}):
        signals.append("discussao tecnica em comunidade")
    if domains:
        signals.append(f"dominios: {', '.join(sorted(domains)[:3])}")
    return signals
