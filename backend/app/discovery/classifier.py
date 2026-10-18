"""Deterministic "is this a company?" filter, plus a tiny Ollama check for genuinely uncertain cases.

classify() returns (verdict, reason):
  ok        -> keep as a company
  reject    -> product / listing / section heading / article text: never saved as a company
  uncertain -> cannot be decided by rules; the engine asks Ollama (and rejects if Ollama is unavailable)
"""
from __future__ import annotations

import json
import re

from .normalize import COMPANY_SUFFIX, GENERIC_CATEGORY_WORDS, domain_matches_name

MAX_VET_CALLS_PER_RUN = 150

# Whole-name matches: page furniture / section labels, never a company.
BOILERPLATE = {
    "industries", "tech hubs", "hubs", "share this page", "for recruiters", "for candidates",
    "offerings", "customers", "results total", "total results", "investors", "funding", "news",
    "faq", "faqs", "locations", "resources", "solutions", "products", "services", "categories",
    "filters", "sort by", "companies", "startups", "top companies", "related companies",
    "similar companies", "popular searches", "popular categories", "trending", "featured",
    "sponsored", "advertisement", "testimonials", "partners", "clients", "reviews", "events",
    "newsletter", "subscribe", "follow us", "quick links", "explore", "discover", "features",
    "benefits", "why us", "our team", "leadership", "founders", "alumni", "sectors", "sector",
    "overview", "highlights", "key highlights", "statistics", "stats", "trends", "get in touch",
    "request a quote", "enquiry", "inquiry", "send enquiry", "view more", "load more",
}
# Phrases that mark a report/section/article heading wherever they appear in the name.
SECTION_RE = re.compile(
    r"\b(faqs?\s+about|funding\s+(?:trends?|rounds?)|recent\s+funding|total\s+funding|"
    r"year[- ]on[- ]year|founded\s+by|top\s+(?:news|investors|companies|startups)|"
    r"acquisition\s+trends?|m&a\s+activity|ipos?\s+in|results\s+total|share\s+this|"
    r"for\s+(?:recruiters|candidates|employers|investors)|key\s+(?:facts|highlights)|"
    r"trends?\s+in|news\s+in|investors\s+in|companies\s+(?:founded|in)|startups\s+in|"
    r"how\s+to|what\s+is)\b", re.I)
# Product specification / price text ("4x6 ft", "15 kW", "Popular Price", "Automation Grade: ...").
SPEC_RE = re.compile(
    r"\d\s?(?:kw|hp|mm|cm|kg|ft|mtr|rpm|hz|kva|ltr|litre|tons?|inch|watts?)\b|"
    r"\b\d+(?:\.\d+)?\s?[x×]\s?\d+|"
    r"\b(?:price|prices|wholesale|for\s+sale|starting\s+at|grade|capacity)\b|[₹$]|\brs\.?\s?\d", re.I)
# Product/equipment words. One alone is ambiguous ("Sharma CNC"), several together are a product.
PRODUCT_WORDS = {
    "machine", "machines", "machinery", "machining", "cnc", "edm", "vmc", "lathe", "router",
    "centre", "center", "turning", "milling", "drilling", "grinding", "cutting", "welding",
    "printer", "scanner",
}
# Extractor outputs whose outbound link is only loosely tied to the heading/card text.
LOOSE_LINK_TYPES = {"article_heading", "card_item"}


def classify(name: str, domain: str = "", source_type: str = "", title_derived: bool = False) -> tuple[str, str]:
    n = re.sub(r"\s+", " ", (name or "")).strip(" .,-|:")
    if not n:
        return ("ok", "domain only") if domain else ("reject", "no name or domain")
    low = n.lower()
    toks = re.findall(r"[a-z0-9]+", low)
    if not toks:
        return "reject", "no usable name"
    if low in BOILERPLATE or SECTION_RE.search(low):
        return "reject", "page section / boilerplate heading"
    if len(toks) > 8:
        return "reject", "sentence-like text, not a name"
    if SPEC_RE.search(low):
        return "reject", "product specification / price text"

    strong = bool(COMPANY_SUFFIX.search(n)) or bool(domain and domain_matches_name(n, domain))
    if not strong:
        prod = [t for t in toks if t in PRODUCT_WORDS]
        if prod:
            if (any(ch.isdigit() for ch in low) or len(prod) >= 3
                    or all(t in PRODUCT_WORDS or t in GENERIC_CATEGORY_WORDS for t in toks)):
                return "reject", "product name"
            return "uncertain", "possible product name"
        if domain and (title_derived or source_type in LOOSE_LINK_TYPES):
            return "uncertain", "domain not confirmed by name"
    return "ok", ""


_PROMPT = """Is the following a real company (its name or its own official website)?
Answer false if it is a product, product listing, category, directory, article, news item or page section.
Name: {name}
Domain: {domain}
Page: {url}
Text: {text}
Reply ONLY with JSON: {{"is_company": true}} or {{"is_company": false}}"""


def ollama_vet(http, ollama_url: str, model: str, cand: dict) -> bool | None:
    """Ask Ollama about ONE uncertain candidate. True/False, or None if Ollama failed / gave junk."""
    try:
        resp = http.post_json(
            ollama_url.rstrip("/") + "/api/generate",
            {"model": model, "stream": False, "format": "json",
             "prompt": _PROMPT.format(name=cand.get("name", "")[:120], domain=cand.get("domain", ""),
                                      url=cand.get("url", "")[:200], text=cand.get("text", "")[:300]),
             "options": {"temperature": 0, "num_predict": 30}})
        val = json.loads(resp.get("response", "{}")).get("is_company")
        return val if isinstance(val, bool) else None
    except Exception:
        return None