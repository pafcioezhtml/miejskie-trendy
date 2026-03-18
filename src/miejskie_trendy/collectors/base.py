from __future__ import annotations

from typing import Protocol

from miejskie_trendy.models import RawItem


class Collector(Protocol):
    name: str

    async def collect(self) -> list[RawItem]: ...
