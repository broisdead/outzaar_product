"""Search-engine and business-listing providers.

All of them also run *site-scoped* queries (site:indiamart.com ..., site:cii.in ...) so
directories and association member pages are covered without brittle scraping.
"""
from __future__ import annotations

import urllib.parse
from typing import Iterator

from .base import Page, Provider, ProviderQuery, RawItem


class SearchProvider(Provider):
    kind = "search"
    confidence = "low"
    site_share = 0.35            # fraction of the query budget spent on site-scoped queries

    def __init__(self, directory_sites=None, association_sites=None):
        super().__init__()
        self.sites = list(directory_sites or []) + list(association_sites or [])

    def build_queries(self, specs, limit: int) -> list[ProviderQuery]:
        site_budget = int(limit * self.site_share) if self.sites else 0
        plain = super().build_queries(specs, limit - site_budget)
        out = list(plain)
        if site_budget:
            per_site = max(1, site_budget // len(self.sites))
            for idx, site in enumerate(self.sites):
                n = 0
                for s in specs[idx::len(self.sites)]:      # different slice per site -> more variety
                    q = f"site:{site} {s.term} {s.ctype} {s.location}".replace("  ", " ").strip()
                    out.append(ProviderQuery(q, {"term": s.term, "city": s.city, "state": s.state, "site": site}))
                    n += 1
                    if n >= per_site:
                        break
        return out

    @staticmethod
    def _item(title: str, url: str, snippet: str) -> RawItem:
        return RawItem(
            title=title, website=url, source_id=url.split("#")[0], source_url=url,
            description=snippet, location_hint=f"{title} {snippet}",
            name="", raw={"title": title, "url": url, "snippet": snippet},
        )


class SerpApiProvider(SearchProvider):
    name = "serpapi_google"
    min_interval = 0.3

    def __init__(self, key: str, **kw):
        super().__init__(**kw)
        self.key = key

    def enabled(self) -> bool:
        return bool(self.key)

    def search(self, pq, max_pages, http) -> Iterator[Page]:
        for page in range(1, max_pages + 1):
            self._throttle()
            data = http.get_json("https://serpapi.com/search.json", params={
                "engine": "google", "q": pq.text, "api_key": self.key, "gl": "in",
                "google_domain": "google.co.in", "hl": "en", "num": 10, "start": (page - 1) * 10})
            if data.get("error") and "hasn't returned any results" not in data["error"]:
                raise RuntimeError(f"SerpAPI: {data['error']}")
            res = data.get("organic_results") or []
            items = [self._item(r.get("title", ""), r.get("link", ""), r.get("snippet", ""))
                     for r in res if r.get("link")]
            more = bool((data.get("serpapi_pagination") or {}).get("next"))
            yield Page(page, items, more)
            if not items or not more:
                return


class SerpApiMapsProvider(Provider):
    """Google Maps business listings via SerpAPI: structured, includes website/phone/address."""
    name = "serpapi_maps"
    kind = "business_listing"
    confidence = "high"
    min_interval = 0.3

    def __init__(self, key: str):
        super().__init__()
        self.key = key

    def enabled(self) -> bool:
        return bool(self.key)

    def search(self, pq, max_pages, http) -> Iterator[Page]:
        for page in range(1, max_pages + 1):
            self._throttle()
            data = http.get_json("https://serpapi.com/search.json", params={
                "engine": "google_maps", "type": "search", "q": pq.text, "api_key": self.key,
                "hl": "en", "gl": "in", "start": (page - 1) * 20})
            if data.get("error") and "hasn't returned any results" not in data["error"]:
                raise RuntimeError(f"SerpAPI maps: {data['error']}")
            res = data.get("local_results") or []
            items = [RawItem(
                name=r.get("title", ""), website=r.get("website", ""),
                source_id=str(r.get("place_id") or r.get("data_id") or ""),
                source_url=r.get("website") or "", address=r.get("address", ""),
                phone=r.get("phone", ""), description=r.get("type", ""), raw=r) for r in res]
            yield Page(page, items, bool(items))
            if not items:
                return


class GoogleCseProvider(SearchProvider):
    name = "google_cse"
    min_interval = 0.2

    def __init__(self, key: str, cx: str, **kw):
        super().__init__(**kw)
        self.key, self.cx = key, cx

    def enabled(self) -> bool:
        return bool(self.key and self.cx)

    def search(self, pq, max_pages, http) -> Iterator[Page]:
        for page in range(1, min(max_pages, 10) + 1):       # API hard limit: 100 results
            self._throttle()
            data = http.get_json("https://www.googleapis.com/customsearch/v1", params={
                "key": self.key, "cx": self.cx, "q": pq.text, "num": 10,
                "start": (page - 1) * 10 + 1, "gl": "in", "cr": "countryIN"})
            res = data.get("items") or []
            items = [self._item(r.get("title", ""), r.get("link", ""), r.get("snippet", ""))
                     for r in res if r.get("link")]
            yield Page(page, items, bool(items))
            if not items:
                return


class BraveProvider(SearchProvider):
    name = "brave_search"
    min_interval = 1.0           # free tier is 1 req/s

    def __init__(self, key: str, **kw):
        super().__init__(**kw)
        self.key = key

    def enabled(self) -> bool:
        return bool(self.key)

    def search(self, pq, max_pages, http) -> Iterator[Page]:
        for page in range(0, min(max_pages, 10)):           # offset is a page index, max 9
            self._throttle()
            data = http.get_json("https://api.search.brave.com/res/v1/web/search",
                                 params={"q": pq.text, "count": 20, "offset": page, "country": "IN"},
                                 headers={"X-Subscription-Token": self.key, "Accept": "application/json"})
            res = (data.get("web") or {}).get("results") or []
            items = [self._item(r.get("title", ""), r.get("url", ""), r.get("description", ""))
                     for r in res if r.get("url")]
            yield Page(page + 1, items, bool(items))
            if not items:
                return


class DuckDuckGoProvider(SearchProvider):
    """Keyless best-effort HTML endpoint. Frequently rate-limited/CAPTCHA'd; failure is tolerated."""
    name = "duckduckgo_html"
    min_interval = 2.5
    workers = 1

    def enabled(self) -> bool:
        return True

    def search(self, pq, max_pages, http) -> Iterator[Page]:
        from bs4 import BeautifulSoup
        for page in range(0, min(max_pages, 3)):
            self._throttle()
            html = http.request("POST", "https://html.duckduckgo.com/html/",
                                form={"q": pq.text, "s": str(page * 30), "kl": "in-en"})
            soup = BeautifulSoup(html, "lxml")
            if soup.select_one("form#challenge-form, .anomaly-modal"):
                raise RuntimeError("DuckDuckGo served a bot challenge")
            items = []
            for r in soup.select("div.result"):
                a = r.select_one("a.result__a")
                if not a or not a.get("href"):
                    continue
                href = a["href"]
                if "uddg=" in href:
                    href = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0])
                sn = r.select_one(".result__snippet")
                items.append(self._item(a.get_text(" ", strip=True), href, sn.get_text(" ", strip=True) if sn else ""))
            yield Page(page + 1, items, bool(items))
            if not items:
                return
