from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

log = get_logger(__name__)

REQUIRED_ANALYSIS_FIELDS = (
    "category",
    "entities",
    "summary",
    "technical_depth",
    "novelty",
    "momentum",
    "community_adoption",
    "authority",
    "implementation_value",
    "cross_source_validation",
    "noise_risk",
    "why_it_matters",
    "worth_testing",
    "key_points",
)

NUMERIC_ANALYSIS_FIELDS = (
    "technical_depth",
    "novelty",
    "momentum",
    "community_adoption",
    "authority",
    "implementation_value",
    "cross_source_validation",
    "noise_risk",
)

DEFAULT_ANALYSIS: Dict[str, Any] = {
    "category": "ai_engineering",
    "entities": [],
    "summary": "",
    "technical_depth": 0.0,
    "novelty": 0.0,
    "momentum": 0.0,
    "community_adoption": 0.0,
    "authority": 0.0,
    "implementation_value": 0.0,
    "cross_source_validation": 0.0,
    "noise_risk": 10.0,
    "why_it_matters": "",
    "worth_testing": False,
    "key_points": [],
}


def validate_analysis(data: Any, url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Normalizes LLM analysis output into the supported JSON contract."""
    if not isinstance(data, dict):
        log.warning("analysis_invalid_type", url=url, data_type=type(data).__name__)
        return None

    validated = DEFAULT_ANALYSIS.copy()
    for field in REQUIRED_ANALYSIS_FIELDS:
        if field not in data:
            log.warning("analysis_missing_field", url=url, field=field)

    validated["category"] = _string_field(data, "category", validated["category"], url)
    validated["entities"] = _string_list_field(data, "entities", url)
    validated["summary"] = _string_field(data, "summary", validated["summary"], url)
    validated["why_it_matters"] = _string_field(
        data, "why_it_matters", validated["why_it_matters"], url
    )
    validated["worth_testing"] = _bool_field(
        data, "worth_testing", validated["worth_testing"], url
    )
    validated["key_points"] = _string_list_field(data, "key_points", url)

    for field in NUMERIC_ANALYSIS_FIELDS:
        validated[field] = _score_field(data, field, validated[field], url)

    return validated


def _string_field(data: Dict[str, Any], field: str, fallback: str, url: Optional[str]) -> str:
    value = data.get(field, fallback)
    if value is None:
        return fallback
    if not isinstance(value, str):
        log.warning("analysis_field_coerced", url=url, field=field, from_type=type(value).__name__)
    return str(value)


def _string_list_field(data: Dict[str, Any], field: str, url: Optional[str]) -> List[str]:
    value = data.get(field, [])
    if value is None:
        return []
    if not isinstance(value, list):
        log.warning("analysis_invalid_field", url=url, field=field, expected="list")
        return []
    return [str(item) for item in value if item is not None]


def _bool_field(data: Dict[str, Any], field: str, fallback: bool, url: Optional[str]) -> bool:
    value = data.get(field, fallback)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "sim", "1"}:
            return True
        if normalized in {"false", "no", "nao", "não", "0"}:
            return False
    log.warning("analysis_invalid_field", url=url, field=field, expected="boolean")
    return fallback


def _score_field(data: Dict[str, Any], field: str, fallback: float, url: Optional[str]) -> float:
    value = data.get(field, fallback)
    try:
        score = float(value)
    except (TypeError, ValueError):
        log.warning("analysis_invalid_field", url=url, field=field, expected="number")
        return fallback

    clamped = max(0.0, min(10.0, score))
    if clamped != score:
        log.warning("analysis_score_clamped", url=url, field=field, value=score, clamped=clamped)
    return clamped
