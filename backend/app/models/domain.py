from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stable_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass
class Document:
    title: str
    content: str
    source_type: str
    source_uri: str | None = None
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    content_hash: str = ""
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = stable_hash(self.content)


@dataclass
class Chunk:
    document_id: str
    text: str
    section_path: list[str]
    order_index: int
    page: int | None = None
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    embedding: list[float] = field(default_factory=list)

