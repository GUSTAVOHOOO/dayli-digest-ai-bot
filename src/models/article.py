from dataclasses import dataclass, field, asdict
from typing import Optional
import hashlib

@dataclass
class Article:
    url: str
    source: str
    md5_hash: str = ""
    title: Optional[str] = None
    date_published: Optional[str] = None
    date_processed: Optional[str] = None
    summary: Optional[str] = None
    score: float = 0.0
    status: str = 'processed'
    clean_text: Optional[str] = None
    id: Optional[int] = None

    def __post_init__(self):
        if not self.md5_hash:
            # Generate MD5 hash of URL + Title for deduplication
            self.md5_hash = hashlib.md5(
                f"{self.url}{self.title or ''}".encode()
            ).hexdigest()

    @staticmethod
    def from_dict(data: dict) -> 'Article':
        return Article(**data)

    def to_dict(self) -> dict:
        return asdict(self)
