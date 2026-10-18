"""ICP interpretation + query expansion.

Ollama is used ONLY here: to turn free-text ICP into search vocabulary. It never
produces companies. If Ollama is down or returns junk, a rule-based fallback keeps
discovery running.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from .geo import CITIES, STATES, TOP_HUBS, canonical_city, detect_locations, state_of
from .http import HttpClient

DEFAULT_COMPANY_TYPES = ["companies", "startups", "firms", "providers"]
STOPWORDS = set("""a an the and or of in for with to from at by on who that which are is be we our their
companies company firms firm businesses business india indian mid midsize sized small large medium
sme smes looking find need needs want targeting target selling sell based located""".split())


@dataclass
class IcpSpec:
    raw_text: str = ""
    industries: list[str] = field(default_factory=list)
    sub_industries: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    company_types: list[str] = field(default_factory=list)
    cities: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)
    company_size: str = ""
    source: str = "fallback"        # 'ollama' | 'fallback'

    def terms(self) -> list[str]:
        seen, out = set(), []
        for t in self.industries + self.sub_industries + self.synonyms + self.keywords:
            t = re.sub(r"\s+", " ", t.strip().lower())
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out

    def to_dict(self) -> dict:
        return asdict(self)


PROMPT = """You help a sales team search for companies in India.
Read the ideal customer profile and return ONLY a JSON object with these keys:
"industries": up to 5 short industry/sector names (e.g. "B2B SaaS", "Fintech", "Automotive"),
"sub_industries": up to 12 specific niche phrases or categories,
"synonyms": up to 12 alternative search terms or keywords in this domain,
"keywords": up to 10 relevant keywords (products, technologies, services),
"company_types": words like startup, startups, company, companies, platform, provider, agency, manufacturer, etc. (ONLY if relevant to the ICP),
"cities": Indian cities mentioned or strongly implied (empty list if none),
"states": Indian states mentioned or strongly implied (empty list if none),
"company_size": short text or "".
Do NOT invent unrelated industries or terms. Keep every phrase 1-4 words.

ICP: {icp}
JSON:"""


def _clean_list(v, limit: int) -> list[str]:
    if not isinstance(v, list):
        return []
    out = []
    for x in v:
        if isinstance(x, str) and 1 < len(x.strip()) <= 60 and x.strip().lower() not in {o.lower() for o in out}:
            out.append(x.strip())
        if len(out) >= limit:
            break
    return out


def fallback_interpret(text: str) -> IcpSpec:
    city, state = detect_locations(text)
    cities = []
    for c in CITIES:                      # every city mentioned, not just first
        if re.search(r"\b" + re.escape(c) + r"\b", text, re.I):
            cities.append(c)
    for alias_hit in re.findall(r"\b(bangalore|gurgaon|bombay|calcutta|madras|poona|vizag)\b", text, re.I):
        cities.append(canonical_city(alias_hit))
    states = [s for s in STATES if re.search(r"\b" + re.escape(s) + r"\b", text, re.I)]
    cities = list(dict.fromkeys(cities))
    if state and state not in states and not cities:
        states.append(state)

    # Extract alphanumeric tokens (supporting b2b, b2c, d2c, ai, etc.)
    tokens = re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", text.lower())
    loc_tokens = {c.lower() for c in cities} | {s.lower() for s in states}
    meaningful = [w for w in tokens if w not in STOPWORDS and w not in loc_tokens and len(w) >= 2]

    # Detect company type hints from text
    company_types = []
    low_text = text.lower()
    if re.search(r"\b(startup|startups)\b", low_text):
        company_types.extend(["startups", "companies"])
    elif re.search(r"\b(manufactur\w*|factory|oem)\b", low_text):
        company_types.extend(["manufacturers", "suppliers"])
    elif re.search(r"\b(agency|agencies)\b", low_text):
        company_types.extend(["agencies", "companies"])
    elif re.search(r"\b(consult\w*|advisory)\b", low_text):
        company_types.extend(["consultants", "firms"])
    
    # Generate multi-word phrases and individual tokens
    phrases = []
    if meaningful:
        # Full phrase of meaningful tokens (e.g. "b2b saas", "auto components")
        full_phrase = " ".join(meaningful)
        if full_phrase:
            phrases.append(full_phrase)
        # Bigrams
        for i in range(len(meaningful) - 1):
            phrases.append(f"{meaningful[i]} {meaningful[i+1]}")
        # Individual words
        phrases.extend(meaningful)

    phrases = list(dict.fromkeys(phrases))[:10]
    return IcpSpec(
        raw_text=text,
        industries=phrases[:3],
        keywords=phrases[3:],
        company_types=company_types,
        cities=cities,
        states=states,
        source="fallback",
    )


def interpret_icp(text: str, *, ollama_url: str, model: str, timeout: int = 90,
                  http: HttpClient | None = None) -> tuple[IcpSpec, str | None]:
    """Returns (spec, error). error is set when Ollama failed and the fallback was used."""
    base = fallback_interpret(text)
    http = http or HttpClient(timeout=timeout, retries=1)
    try:
        resp = http.post_json(
            ollama_url.rstrip("/") + "/api/generate",
            {"model": model, "prompt": PROMPT.format(icp=text), "stream": False,
             "format": "json", "options": {"temperature": 0.2}},
        )
        data = json.loads(resp.get("response", "{}"))
        if not isinstance(data, dict):
            raise ValueError("Ollama did not return a JSON object")
        spec = IcpSpec(
            raw_text=text,
            industries=_clean_list(data.get("industries"), 5),
            sub_industries=_clean_list(data.get("sub_industries"), 12),
            synonyms=_clean_list(data.get("synonyms"), 12),
            keywords=_clean_list(data.get("keywords"), 10),
            company_types=_clean_list(data.get("company_types"), 8),
            cities=[canonical_city(c) for c in _clean_list(data.get("cities"), 20)],
            states=_clean_list(data.get("states"), 20),
            company_size=str(data.get("company_size") or "")[:80],
            source="ollama",
        )
        if not spec.terms():
            raise ValueError("Ollama returned no usable terms")
        # Never lose locations the user literally typed
        spec.cities = list(dict.fromkeys(spec.cities + base.cities))
        spec.states = list(dict.fromkeys(spec.states + base.states))
        # Keep base company types if Ollama returned empty
        if not spec.company_types and base.company_types:
            spec.company_types = base.company_types
        return spec, None
    except Exception as e:                       # Ollama down, timeout, bad JSON ...
        return base, f"Ollama interpretation failed, used rule-based fallback: {e}"
