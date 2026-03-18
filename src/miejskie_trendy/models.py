from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class RawItem:
    title: str
    summary: str
    url: str
    source: str
    published_at: datetime | None
    raw_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.published_at:
            d["published_at"] = self.published_at.isoformat()
        return d


@dataclass
class Source:
    title: str
    url: str


@dataclass
class Event:
    id: str
    name: str
    description: str
    category: str
    location: str | None
    relevance: str
    confidence: float
    sources: list[Source] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "location": self.location,
            "relevance": self.relevance,
            "confidence": self.confidence,
            "sources": [{"title": s.title, "url": s.url} for s in self.sources],
        }
