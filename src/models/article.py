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
    analysis_json: Optional[str] = None
    id: Optional[int] = None

    def __post_init__(self):
        if not self.md5_hash:
            # Generate MD5 hash of URL + Title for deduplication
            self.md5_hash = hashlib.md5(
                f"{self.url}{self.title or ''}".encode()
            ).hexdigest()

    @staticmethod
    def from_dict(data: dict) -> 'Article':
        # Filter dict keys to match dataclass fields
        import dataclasses
        fields = {f.name for f in dataclasses.fields(Article)}
        filtered_data = {k: v for k, v in data.items() if k in fields}
        return Article(**filtered_data)

    def to_dict(self) -> dict:
        return asdict(self)
