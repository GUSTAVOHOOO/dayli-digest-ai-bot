import re
from typing import Any, Dict, Optional


README_FIELDS = {
    "category": "unknown",
    "problem_solved": "",
    "target_audience": "",
    "maturity": "unknown",
    "complexity": "unknown",
    "tool_type": "unknown",
    "practical_value": 0.0,
    "wrapper_risk": 5.0,
    "documentation_quality": 0.0,
}


def validate_readme_intelligence(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    validated = dict(README_FIELDS)
    for field in ("category", "problem_solved", "target_audience", "maturity", "complexity", "tool_type"):
        value = data.get(field, validated[field])
        validated[field] = "" if value is None else str(value)
    for field in ("practical_value", "wrapper_risk", "documentation_quality"):
        validated[field] = _score(data.get(field, validated[field]))
    return validated


def infer_readme_intelligence(text: Optional[str], title: str = "") -> Dict[str, Any]:
    """Deterministic fallback when README LLM output is unavailable."""
    content = text or ""
    lowered = content.lower()
    has_install = bool(re.search(r"\b(pip install|npm install|uv add|docker run|installation|install)\b", lowered))
    has_usage = bool(re.search(r"\b(usage|quickstart|example|getting started|cli|api)\b", lowered))
    has_architecture = bool(re.search(r"\b(architecture|pipeline|benchmark|evaluation|provider|adapter|plugin)\b", lowered))
    wrapper_terms = ("wrapper", "thin wrapper", "openai api", "chatgpt wrapper", "simple ui", "boilerplate")
    wrapper_hits = sum(1 for term in wrapper_terms if term in lowered)
    docs_quality = min(10.0, (len(content) / 600.0) + (2.0 if has_install else 0.0) + (2.0 if has_usage else 0.0) + (1.5 if has_architecture else 0.0))
    wrapper_risk = min(10.0, wrapper_hits * 2.5 + (2.0 if len(content) < 500 else 0.0))
    practical_value = max(0.0, min(10.0, docs_quality + (1.0 if has_usage else 0.0) - wrapper_risk * 0.4))

    return validate_readme_intelligence({
        "category": "emerging_repository",
        "problem_solved": _first_sentence(content) or title,
        "target_audience": "developers" if has_install or has_usage else "unknown",
        "maturity": "documented" if docs_quality >= 6.0 else "early",
        "complexity": "advanced" if has_architecture else "basic",
        "tool_type": _tool_type(lowered),
        "practical_value": practical_value,
        "wrapper_risk": wrapper_risk,
        "documentation_quality": docs_quality,
    })


def apply_readme_intelligence(analysis: Dict[str, Any], readme: Dict[str, Any]) -> Dict[str, Any]:
    """Adds README intelligence and adjusts score inputs before final scoring."""
    updated = dict(analysis)
    validated = validate_readme_intelligence(readme)
    updated["readme_intelligence"] = validated
    updated["wrapper_risk"] = validated["wrapper_risk"]
    updated["documentation_quality"] = validated["documentation_quality"]
    updated["implementation_value"] = max(
        0.0,
        min(10.0, float(updated.get("implementation_value", 0.0) or 0.0) + (validated["practical_value"] - 5.0) * 0.25),
    )
    if validated["wrapper_risk"] >= 7.0:
        updated["noise_risk"] = min(10.0, float(updated.get("noise_risk", 0.0) or 0.0) + 2.0)
        updated["novelty"] = max(0.0, float(updated.get("novelty", 0.0) or 0.0) - 1.5)
    if validated["documentation_quality"] < 3.0:
        updated["implementation_value"] = max(0.0, float(updated.get("implementation_value", 0.0) or 0.0) - 1.0)
        updated["noise_risk"] = min(10.0, float(updated.get("noise_risk", 0.0) or 0.0) + 1.0)
    return updated


def _score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(10.0, score)), 1)


def _first_sentence(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return ""
    return re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0][:240]


def _tool_type(text: str) -> str:
    if "agent" in text:
        return "agent_tool"
    if "rag" in text or "retrieval" in text:
        return "rag_tool"
    if "cli" in text:
        return "cli"
    if "api" in text:
        return "api_tool"
    return "developer_tool"
