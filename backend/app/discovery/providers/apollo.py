"""Apollo.io organization search (B2B company database). Requires a plan with API access."""
from __future__ import annotations

from typing import Iterator

from .base import Page, Provider, ProviderQuery, RawItem


class ApolloProvider(Provider):
    name = "apollo"
    kind = "b2b_api"
    confidence = "high"
    min_interval = 0.5
    URL = "https://api.apollo.io/api/v1/mixed_companies/search"

    def __init__(self, key: str):
        super().__init__()
        self.key = key

    def enabled(self) -> bool:
        return bool(self.key)

    def build_queries(self, specs, limit):
        # Structured API: query = keyword tag + location, no need for company-type wording.
        seen, out = set(), []
        for s in specs:
            loc = s.city or s.state or "India"
            key = (s.term, loc)
            if key in seen:
                continue
            seen.add(key)
            out.append(ProviderQuery(f"{s.term} | {loc}", {"term": s.term, "location": loc}))
            if len(out) >= limit:
                break
        return out

    def search(self, pq, max_pages, http) -> Iterator[Page]:
        loc = pq.params.get("location", "India")
        location = "India" if loc == "India" else f"{loc}, India"
        for page in range(1, max_pages + 1):
            self._throttle()
            data = http.post_json(self.URL, {
                "q_organization_keyword_tags": [pq.params["term"]],
                "organization_locations": [location], "page": page, "per_page": 100},
                headers={"X-Api-Key": self.key, "Cache-Control": "no-cache"})
            orgs = data.get("organizations") or data.get("accounts") or []
            items = [RawItem(
                name=o.get("name", ""), website=o.get("website_url") or o.get("primary_domain") or "",
                source_id=str(o.get("id", "")), source_url=o.get("linkedin_url", "") or "",
                city=o.get("city") or "", state=o.get("state") or "", phone=o.get("phone") or "",
                description=o.get("short_description") or o.get("industry") or "", raw=o) for o in orgs]
            pg = data.get("pagination") or {}
            more = bool(items) and page < int(pg.get("total_pages", page + 1))
            yield Page(page, items, more)
            if not more:
                return
