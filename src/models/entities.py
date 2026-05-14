from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class Entity:
    name: str
    type: str
    normalized_name: str

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Entity":
        name = str(data.get("name") or data.get("normalized_name") or "")
        entity_type = str(data.get("type") or "concept")
        normalized_name = str(data.get("normalized_name") or name).strip().lower()
        return Entity(name=name, type=entity_type, normalized_name=normalized_name)

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)
