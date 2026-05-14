import re
from typing import Any, Dict, Iterable, List, Optional


PAPER_TYPES = {
    "breakthrough",
    "benchmark",
    "survey",
    "implementation",
    "educational",
    "research_infrastructure",
    "incremental",
    "low_signal",
}

AUTHORITY_INSTITUTIONS = {
    "openai": 10.0,
    "anthropic": 10.0,
    "google deepmind": 9.5,
    "deepmind": 9.5,
    "meta ai": 9.0,
    "fair": 9.0,
    "stanford": 8.5,
    "berkeley": 8.5,
    "cmu": 8.5,
    "mit": 8.5,
}


def analyze_paper_signals(text: Optional[str], title: str = "", entities: Optional[Iterable[Any]] = None) -> Dict[str, Any]:
    content = f"{title}\n{text or ''}"
    lowered = content.lower()
    paper_type = _paper_type(lowered)
    institutions = _institutions(lowered)
    has_code = bool(re.search(r"\b(code|github|implementation|repository|repo)\b", lowered))
    has_benchmark = bool(re.search(r"\b(benchmark|eval|evaluation|leaderboard|sota|state-of-the-art)\b", lowered))
    has_dataset = bool(re.search(r"\b(dataset|corpus|data set)\b", lowered))
    has_implementation = bool(re.search(r"\b(implementation|system|framework|library|open-source)\b", lowered))
    github_entities = _github_entities(entities or [])
    authority = max((AUTHORITY_INSTITUTIONS[name] for name in institutions), default=4.0)
    if has_code and has_benchmark:
        authority = min(10.0, authority + 0.5)
    impact = _impact_score(paper_type, authority, has_code, has_benchmark, has_dataset, has_implementation)
    return {
        "paper_type": paper_type,
        "paper_authority": round(authority, 1),
        "authority_institutions": institutions,
        "has_code": has_code,
        "has_benchmark": has_benchmark,
        "has_dataset": has_dataset,
        "has_implementation": has_implementation,
        "correlates_with_github": bool(github_entities or "github.com" in lowered),
        "github_entities": github_entities,
        "paper_impact_score": impact,
    }


def apply_paper_intelligence(analysis: Dict[str, Any], paper: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(analysis)
    signals = analyze_paper_signals("", entities=updated.get("entities"))
    signals.update(validate_paper_intelligence(paper))
    updated["paper_intelligence"] = signals
    updated["paper_authority"] = signals["paper_authority"]
    if signals["paper_type"] in {"incremental", "low_signal"}:
        updated["novelty"] = max(0.0, float(updated.get("novelty", 0.0) or 0.0) - 2.0)
        updated["noise_risk"] = min(10.0, float(updated.get("noise_risk", 0.0) or 0.0) + 2.0)
    if signals["has_code"] and signals["has_benchmark"]:
        updated["implementation_value"] = min(10.0, float(updated.get("implementation_value", 0.0) or 0.0) + 1.5)
        updated["cross_source_validation"] = min(10.0, float(updated.get("cross_source_validation", 0.0) or 0.0) + 1.0)
    updated["authority"] = max(float(updated.get("authority", 0.0) or 0.0), signals["paper_authority"])
    return updated


def validate_paper_intelligence(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    paper_type = str(data.get("paper_type") or "low_signal").strip().lower().replace("-", "_").replace(" ", "_")
    if paper_type not in PAPER_TYPES:
        paper_type = "low_signal"
    return {
        "paper_type": paper_type,
        "paper_authority": _score(data.get("paper_authority", 4.0)),
        "authority_institutions": _string_list(data.get("authority_institutions")),
        "has_code": bool(data.get("has_code", False)),
        "has_benchmark": bool(data.get("has_benchmark", False)),
        "has_dataset": bool(data.get("has_dataset", False)),
        "has_implementation": bool(data.get("has_implementation", False)),
        "correlates_with_github": bool(data.get("correlates_with_github", False)),
        "github_entities": _string_list(data.get("github_entities")),
        "paper_impact_score": _score(data.get("paper_impact_score", 0.0)),
    }


def _paper_type(text: str) -> str:
    if re.search(r"\b(breakthrough|new state-of-the-art|outperforms|novel architecture)\b", text):
        return "breakthrough"
    if re.search(r"\b(benchmark|leaderboard|evaluation suite|eval)\b", text):
        return "benchmark"
    if re.search(r"\b(survey|review|taxonomy|tutorial)\b", text):
        return "survey"
    if re.search(r"\b(system|implementation|framework|library|open-source)\b", text):
        return "implementation"
    if re.search(r"\b(dataset|infrastructure|corpus|toolkit)\b", text):
        return "research_infrastructure"
    if re.search(r"\b(incremental|marginal|preliminary)\b", text):
        return "incremental"
    return "low_signal"


def _institutions(text: str) -> List[str]:
    found = []
    for name in AUTHORITY_INSTITUTIONS:
        if name in text:
            found.append(name)
    return found


def _github_entities(entities: Iterable[Any]) -> List[str]:
    repos = []
    for entity in entities:
        if isinstance(entity, dict):
            entity_type = str(entity.get("type") or "")
            name = str(entity.get("name") or entity.get("normalized_name") or "")
            if entity_type == "github_repo" and name:
                repos.append(name)
        elif "/" in str(entity):
            repos.append(str(entity))
    return repos


def _impact_score(
    paper_type: str,
    authority: float,
    has_code: bool,
    has_benchmark: bool,
    has_dataset: bool,
    has_implementation: bool,
) -> float:
    base = {
        "breakthrough": 7.5,
        "benchmark": 6.5,
        "implementation": 6.0,
        "research_infrastructure": 6.0,
        "survey": 4.5,
        "educational": 4.0,
        "incremental": 2.5,
        "low_signal": 1.5,
    }.get(paper_type, 1.5)
    base += authority * 0.15
    base += 1.0 if has_code else 0.0
    base += 1.0 if has_benchmark else 0.0
    base += 0.5 if has_dataset else 0.0
    base += 0.5 if has_implementation else 0.0
    return round(max(0.0, min(10.0, base)), 1)


def _score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(10.0, score)), 1)


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]
