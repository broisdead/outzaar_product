"""Provider contract. Each provider yields pages of RawItem; the engine handles the rest."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class RawItem:
    name: str = ""
    website: str = ""
    source_id: str = ""
    source_url: str = ""
    city: str = ""
    state: str = ""
    phone: str = ""
    address: str = ""
    description: str = ""
    title: str = ""              # page title (search results); name derived from it if name is empty
    location_hint: str = ""      # free text scanned for a place name when city/state are unknown
    raw: dict = field(default_factory=dict)


@dataclass
class Page:
    number: int
    items: list[RawItem]
    has_more: bool = True


@dataclass
class ProviderQuery:
    text: str
    params: dict = field(default_factory=dict)


class Provider:
    name = "base"
    kind = "search"              # search | b2b_api | business_listing | directory
    confidence = "low"           # 'high' when results are structured company records
    min_interval = 0.0           # seconds between requests (per provider)
    workers = 2

    def __init__(self):
        self._tlock = threading.Lock()
        self._last = 0.0

    def enabled(self) -> bool:
        return True

    def build_queries(self, specs, limit: int) -> list[ProviderQuery]:
        seen, out = set(), []
        for s in specs:
            if s.text not in seen:
                seen.add(s.text)
                out.append(ProviderQuery(s.text, {"term": s.term, "city": s.city, "state": s.state}))
            if len(out) >= limit:
                break
        return out

    def search(self, pq: ProviderQuery, max_pages: int, http) -> Iterator[Page]:
        raise NotImplementedError

    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        with self._tlock:
            wait = self._last + self.min_interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
