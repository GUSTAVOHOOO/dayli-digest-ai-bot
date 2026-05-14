from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class TopicCluster:
    cluster_id: str
    topic_name: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, str]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    cross_source_count: int = 0
    cross_source_validation: float = 0.0
    correlation_boost: float = 0.0
    correlation_signals: List[str] = field(default_factory=list)
    final_score: float = 0.0
    tier: str = "C"
    trend_score: float = 0.0
    trend_signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
