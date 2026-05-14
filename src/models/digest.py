from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DigestLink:
    url: str
    title: Optional[str] = None
    source: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DigestLink":
        return DigestLink(
            url=str(data.get("url", "")),
            title=data.get("title"),
            source=data.get("source"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreBreakdown:
    relevance: float = 0.0
    novelty: float = 0.0
    source_quality: float = 0.0
    urgency: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "ScoreBreakdown":
        if not data:
            return ScoreBreakdown()

        known_fields = {"relevance", "novelty", "source_quality", "urgency"}
        extra = {key: value for key, value in data.items() if key not in known_fields}
        return ScoreBreakdown(
            relevance=float(data.get("relevance", 0.0) or 0.0),
            novelty=float(data.get("novelty", 0.0) or 0.0),
            source_quality=float(data.get("source_quality", 0.0) or 0.0),
            urgency=float(data.get("urgency", 0.0) or 0.0),
            extra=extra,
        )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "relevance": self.relevance,
            "novelty": self.novelty,
            "source_quality": self.source_quality,
            "urgency": self.urgency,
        }
        data.update(self.extra)
        return data


@dataclass
class DigestItem:
    title: str
    category: str
    tier: str = "C"
    importance: float = 0.0
    why_it_matters: str = ""
    key_points: List[str] = field(default_factory=list)
    worth_testing: bool = False
    testing_reason: str = ""
    links: List[DigestLink] = field(default_factory=list)
    score_breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DigestItem":
        links = [
            link if isinstance(link, DigestLink) else DigestLink.from_dict(link)
            for link in data.get("links", []) or []
        ]
        score_breakdown = data.get("score_breakdown")
        if not isinstance(score_breakdown, ScoreBreakdown):
            score_breakdown = ScoreBreakdown.from_dict(score_breakdown)

        return DigestItem(
            title=str(data.get("title") or "Sem titulo"),
            category=str(data.get("category") or "AI Engineering"),
            tier=str(data.get("tier") or "C"),
            importance=float(data.get("importance", 0.0) or 0.0),
            why_it_matters=str(data.get("why_it_matters") or ""),
            key_points=[str(point) for point in data.get("key_points", []) or []],
            worth_testing=bool(data.get("worth_testing", False)),
            testing_reason=str(data.get("testing_reason") or ""),
            links=links,
            score_breakdown=score_breakdown,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "category": self.category,
            "tier": self.tier,
            "importance": self.importance,
            "why_it_matters": self.why_it_matters,
            "key_points": self.key_points,
            "worth_testing": self.worth_testing,
            "testing_reason": self.testing_reason,
            "links": [link.to_dict() for link in self.links],
            "score_breakdown": self.score_breakdown.to_dict(),
        }
