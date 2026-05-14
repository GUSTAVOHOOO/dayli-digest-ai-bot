from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass
class AttentionScore:
    final_score: float
    tier: str
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    noise_risk: float = 0.0
    passed: bool = False
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
