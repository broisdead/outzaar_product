"""Config-driven directory / list-page scraper.

Each source in the JSON config describes a listing URL and CSS selectors. Nothing here
claims to know a specific site's markup: selectors MUST be checked against the live page,
and you are responsible for each site's terms of service. robots.txt is honoured.

Config shape: see directories.json.example
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.robotparser
from typing import Iterator

from .base import Page, Provider, ProviderQuery, RawItem


class DirectoryProvider(Provider):
    kind = "directory"
    confidence = "high"
    min_interval = 2.0
    workers = 1

    def __init__(self, source: dict):
        super().__init__()
        self.src = source
        self.name = "dir_" + source["name"]
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def enabled(self) -> bool:
        return not self.src.get("disabled", False)

    def build_queries(self, specs, limit):
        seen, out = set(), []
        for s in specs:
            key = (s.term, s.city)
            if key in seen:
                continue
            seen.add(key)
            out.append(ProviderQuery(f"{s.term} | {s.city or 'India'}", {"term": s.term, "city": s.city, "state": s.state}))
            if len(out) >= min(limit, int(self.src.get("max_queries", limit))):
                break
        return out

    def _allowed(self, url: str, http) -> bool:
        if not self.src.get("respect_robots", True):
            return True
        host = urllib.parse.urlparse(url)
        base = f"{host.scheme}://{host.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                rp.parse(http.get_text(base + "/robots.txt").splitlines())
                self._robots[base] = rp
            except Exception:
                self._robots[base] = None        # robots unreachable -> allow
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch("*", url)

    def search(self, pq, max_pages, http) -> Iterator[Page]:
        from bs4 import BeautifulSoup
        s = self.src
        for page in range(1, min(max_pages, int(s.get("max_pages", max_pages))) + 1):
            url = s["url_template"].format(
                query=urllib.parse.quote_plus(pq.params.get("term", "")),
                city=urllib.parse.quote_plus(pq.params.get("city", "") or ""), page=page)
            if not self._allowed(url, http):
                raise RuntimeError(f"robots.txt disallows {url}")
            self._throttle()
            soup = BeautifulSoup(http.get_text(url), "lxml")
            items = []
            for node in soup.select(s["item_selector"]):
                def txt(sel):
                    el = node.select_one(sel) if sel else None
                    return el.get_text(" ", strip=True) if el else ""
                link = node.select_one(s["link_selector"]) if s.get("link_selector") else None
                href = urllib.parse.urljoin(url, link["href"]) if link and link.get("href") else ""
                name = txt(s["name_selector"])
                if not name and not href:
                    continue
                items.append(RawItem(
                    name=name, source_url=href or url, source_id=href, city=txt(s.get("city_selector")),
                    address=txt(s.get("address_selector")), phone=txt(s.get("phone_selector")),
                    website=(node.select_one(s["website_selector"]) or {}).get("href", "") if s.get("website_selector") else "",
                    description=txt(s.get("description_selector")), raw={"html": str(node)[:4000], "page_url": url}))
            yield Page(page, items, bool(items))
            if not items:
                return


def load_directory_providers(path: str) -> list[DirectoryProvider]:
    if not path:
        return []
    with open(path) as f:
        return [DirectoryProvider(src) for src in json.load(f)]
