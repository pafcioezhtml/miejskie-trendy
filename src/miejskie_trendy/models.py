from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


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
    published_at: datetime | None = None


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
            "sources": [
                {
                    "title": s.title,
                    "url": s.url,
                    "published_at": s.published_at.isoformat() if s.published_at else None,
                }
                for s in sorted(
                    self.sources,
                    key=lambda s: (
                        s.published_at.replace(tzinfo=timezone.utc)
                        if s.published_at and s.published_at.tzinfo is None
                        else s.published_at or datetime.min.replace(tzinfo=timezone.utc)
                    ),
                    reverse=True,
                )
            ],
        }
