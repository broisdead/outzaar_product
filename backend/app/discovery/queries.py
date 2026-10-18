"""Query expansion: ICP spec -> many diverse (term x company type x location) specs."""
from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass

from .geo import CITIES, STATES, TOP_HUBS, canonical_city, canonical_state, state_of
from .icp import DEFAULT_COMPANY_TYPES, IcpSpec


@dataclass(frozen=True)
class QuerySpec:
    term: str
    ctype: str        # may be ''
    city: str         # '' if not city-scoped
    state: str        # '' if not state-scoped

    @property
    def location(self) -> str:
        return self.city or self.state or "India"

    @property
    def text(self) -> str:
        loc = self.location
        parts = [self.term]
        if self.ctype:
            parts.append(self.ctype)
        if loc != "India":
            parts += ["in", loc, "India"]
        else:
            parts += ["in", "India"]
        return " ".join(p for p in parts if p)


def _clean(values: list[str]) -> list[str]:
    """Normalize vocabulary while preserving useful phrases."""
    out = []
    for value in values:
        value = " ".join(str(value).strip().lower().split())
        if value and value not in out:
            out.append(value)
    return out


def _canonical_city(name: str) -> str:
    c = canonical_city(name)
    for official in CITIES:
        if official.lower() == c.lower():
            return official
    return c.title() if c else ""


def _canonical_state(name: str) -> str:
    s = canonical_state(name)
    for official in STATES:
        if official.lower() == s.lower():
            return official
    return s.title() if s else ""


def _build_terms(icp: IcpSpec) -> list[str]:
    """Build high-recall search terms directly from the ICP."""
    terms: list[str] = []

    base_terms = _clean(list(icp.terms()))
    synonyms = _clean(list(getattr(icp, "synonyms", []) or []))
    keywords = _clean(list(getattr(icp, "keywords", []) or []))
    sub_industries = _clean(list(getattr(icp, "sub_industries", []) or []))

    # Keep explicit phrases first
    terms.extend(base_terms)
    terms.extend(synonyms)
    terms.extend(sub_industries)

    # Filter out generic stop words from standalone terms
    generic = {
        "company", "companies", "business", "businesses", "industry", "industries",
        "service", "services", "solution", "solutions", "provider", "providers",
    }
    useful_keywords = [k for k in keywords if k not in generic and len(k) > 2]
    terms.extend(useful_keywords)

    # Create selective combinations if core terms are short
    core = [t for t in _clean(base_terms + synonyms + sub_industries) if len(t.split()) <= 2]
    for a in core[:4]:
        for b in useful_keywords[:4]:
            if a != b and b not in a and a not in b:
                terms.append(f"{a} {b}")

    terms = _clean(terms)

    # Fallback if empty
    if not terms and icp.raw_text.strip():
        terms = [icp.raw_text.strip().lower()]

    return terms


def _build_company_types(icp: IcpSpec) -> list[str]:
    """Expand company-type vocabulary tailored strictly to the ICP domain."""
    explicit = _clean(list(getattr(icp, "company_types", []) or []))
    raw = (icp.raw_text or "").lower()

    # Detect domain context
    is_mfg = any(w in raw for w in ("manufactur", "factory", "fabricat", "oem", "machin", "industrial", "producer", "supplier", "exporter", "equipment", "parts"))
    is_startup = any(w in raw for w in ("startup", "startups", "tech", "saas", "software", "ai", "app", "platform", "fintech", "edtech", "healthtech", "b2b"))
    is_agency = any(w in raw for w in ("agency", "agencies", "consult", "consulting", "studio", "services firm"))

    extra = []
    if is_startup:
        extra = ["startups", "companies", "platforms"]
    elif is_mfg:
        extra = ["manufacturers", "suppliers", "OEMs", "companies", "exporters"]
    elif is_agency:
        extra = ["agencies", "companies", "firms", "consultants"]
    else:
        extra = ["companies", "startups", "firms", "providers"]

    return _clean(explicit + extra)


def _build_locations(
    icp: IcpSpec,
    extra_cities: list[str] | None,
    extra_states: list[str] | None,
) -> list[tuple[str, str]]:
    """Build geographic coverage according to the ICP and requested filters."""
    raw_cities = list(extra_cities or []) + list(icp.cities)
    raw_states = list(extra_states or []) + list(icp.states)
    
    seen_cities = set()
    cities = []
    for c in raw_cities:
        if c:
            canon = _canonical_city(c)
            if canon and canon.lower() not in seen_cities:
                seen_cities.add(canon.lower())
                cities.append(canon)

    seen_states = set()
    states = []
    for s in raw_states:
        if s:
            canon = _canonical_state(s)
            if canon and canon.lower() not in seen_states:
                seen_states.add(canon.lower())
                states.append(canon)

    locations: list[tuple[str, str]] = []

    if cities or states:
        # 1. India-wide general search for this ICP
        locations.append(("", ""))

        # 2. Explicit cities
        for city in cities:
            locations.append((city, state_of(city)))

        # 3. Explicit states
        for state in states:
            locations.append(("", state))
            # Expand state to known cities in that state
            for city_name, st in CITIES.items():
                if st.lower() == state.lower():
                    locations.append((city_name, st))

    else:
        # No geographic restriction -> India-wide coverage + all states + top commercial hubs
        locations.append(("", ""))
        for state in STATES:
            locations.append(("", state))
        for city in TOP_HUBS:
            locations.append((city, state_of(city)))

    # Deduplicate locations while preserving order
    seen = set()
    unique = []
    for loc in locations:
        key = (loc[0].lower(), loc[1].lower())
        if key not in seen:
            seen.add(key)
            unique.append(loc)

    return unique


def expand(
    icp: IcpSpec,
    *,
    extra_cities: list[str] | None = None,
    extra_states: list[str] | None = None,
    cap: int = 20000,
) -> list[QuerySpec]:
    """Expand one ICP into a large, diverse set of search queries."""
    terms = _build_terms(icp)
    ctypes = _build_company_types(icp)
    locations = _build_locations(icp, extra_cities, extra_states)

    raw = (icp.raw_text or "").lower()
    is_mfg = any(w in raw for w in ("manufactur", "factory", "fabricat", "oem", "machin", "industrial", "producer", "supplier", "exporter"))
    is_startup = any(w in raw for w in ("startup", "startups", "tech", "saas", "software", "ai", "platform", "fintech", "edtech", "b2b"))

    combos: list[QuerySpec] = []

    for city, state in locations:
        for term in terms:
            # 1. Direct term + company type
            for ctype in ctypes:
                combos.append(
                    QuerySpec(
                        term=term,
                        ctype=ctype,
                        city=city,
                        state="" if city else state,
                    )
                )

            # 2. Pure term
            combos.append(
                QuerySpec(
                    term=term,
                    ctype="",
                    city=city,
                    state="" if city else state,
                )
            )

            # 3. High-intent search variations matching the ICP domain
            intents = [
                f"top {term}",
                f"list of {term}",
                f"best {term} companies",
                f"{term} directory",
            ]
            if is_startup:
                intents.extend([
                    f"top {term} startups",
                    f"list of {term} startups",
                    f"{term} tech companies",
                ])
            elif is_mfg:
                intents.extend([
                    f"{term} manufacturers",
                    f"{term} suppliers",
                    f"top {term} manufacturers",
                ])

            for intent in intents:
                combos.append(
                    QuerySpec(
                        term=intent,
                        ctype="",
                        city=city,
                        state="" if city else state,
                    )
                )

    # Deduplicate exact QuerySpec combinations
    seen = set()
    unique: list[QuerySpec] = []
    for q in combos:
        key = (
            q.term.lower().strip(),
            q.ctype.lower().strip(),
            q.city.lower().strip(),
            q.state.lower().strip(),
        )
        if key not in seen:
            seen.add(key)
            unique.append(q)

    # When ICP has explicit cities/states, prioritise those queries so providers
    # with small query limits actually search the requested geography.  India-wide
    # queries are still included but appended afterwards (never replace city queries).
    has_explicit_geo = bool(icp.cities or icp.states or extra_cities or extra_states)

    seed = int(hashlib.md5(icp.raw_text.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)

    if has_explicit_geo:
        city_state = [q for q in unique if q.location != "India"]
        india_wide = [q for q in unique if q.location == "India"]
        rng.shuffle(india_wide)
        return (city_state + india_wide)[:cap]
    else:
        head = [q for q in unique if q.location == "India"]
        rest = [q for q in unique if q.location != "India"]
        rng.shuffle(rest)
        return (head + rest)[:cap]