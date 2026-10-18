"""Extractor to parse individual company records from listing / directory / article pages.

Detects and extracts company names, domains, websites, locations, and descriptions from:
- JSON-LD structured data (ItemList, Organization, LocalBusiness)
- Listicle / article headings (e.g. <h2>1. Postman</h2>)
- Directory card containers (.company-card, .listing-item, etc.)
- Outbound verified company website links
- Single-company directory profiles (e.g. f6s.com/company/..., getlatka.com/companies/...)
- Search snippet and title text fallbacks
"""
from __future__ import annotations

import json
import re
import urllib.parse
from bs4 import BeautifulSoup, Tag

from .geo import canonical_city, canonical_state, detect_locations, state_of
from .normalize import (domain_matches_name, extract_domain, is_company_domain,
                         is_generic_category_name, normalize_name, resolve_about_prefix)
from .providers.base import RawItem

# Non-company anchor texts / labels to ignore
IGNORE_NAMES = {
    "home", "homepage", "about", "about us", "contact", "contact us", "privacy policy",
    "terms of service", "terms", "careers", "jobs", "pricing", "login", "sign in",
    "sign up", "register", "blog", "articles", "news", "press", "cookies", "cookie policy",
    "read more", "learn more", "visit website", "website", "view profile", "click here",
    "see more", "source", "author", "share", "tweet", "facebook", "twitter", "linkedin",
    "instagram", "youtube", "table of contents", "overview", "faq", "faqs", "help",
    "support", "download", "get started", "top 10", "top 20", "top 50", "conclusion",
    "summary", "introduction", "related posts", "next", "previous", "search",
}

# Regex to clean numbered listicle headings: "1. Postman - API Platform" -> "Postman"
NUMBERED_HEADING_RE = re.compile(
    r"^(?:(?:#|\bNo\.?\s*)?\d{1,3}[\.\)\:\-–—\s]+|\b\d{1,3}\s*[\.\)\:\-–—]\s*)"
    r"([^\:\-–—\|•\(\)]+)"
)

# Regex to detect profile paths on directories
PROFILE_PATH_RE = re.compile(
    r"/(?:company|companies|organization|organizations|startup|startups|profile|seller|vendor|b)/([^/\?#]+)",
    re.I
)

# Common "next page" link text patterns
NEXT_PAGE_RE = re.compile(r"\b(next|next\s*page|\u203a|\u00bb|&gt;|>>)\b", re.I)

# Minimum length for a plausible company name extracted from an anchor
# Compiled listing-title pattern used by _clean_company_name.
# Applied BEFORE and AFTER location-suffix stripping so that inputs like
# "Leading Startups in Bangalore" are caught before the location is removed.
_LISTING_TITLE_RE = re.compile(
    r"\b("
    r"table of contents|why choose|how to|what is|frequently asked|conclusion|key takeaway"
    r"|top \d+|best \d+"
    # "Top B2B SaaS Companies", "Best SaaS Vendors", "Leading Startups in X"
    r"|(?:top|best|leading|top-rated|\d+\s+(?:best|top|leading))"
    r"\s+\w[\w\s]*?\s+(?:companies|startups|firms|vendors|providers|manufacturers|suppliers|exporters)"
    # "Companies in …" / "Startups in …" as a standalone heading
    r"|(?:companies|startups|firms|vendors|providers|manufacturers|suppliers)\s+in\b"
    r")\b",
    re.I,
)

_MIN_NAME_LEN = 2
_MAX_NAME_LEN = 80


def _clean_company_name(raw_name: str) -> str:
    """Clean heading or label into a proper company name."""
    if not raw_name:
        return ""
    name = re.sub(r"\s+", " ", raw_name).strip()
    # Unwrap "Key facts about X" / "About X" headings into their subject X before
    # anything else. "About Us"-style headings (no real subject) are rejected here.
    resolved = resolve_about_prefix(name)
    if resolved != name:
        if not resolved:
            return ""
        name = resolved
    # Strip leading numbers: "1. Postman" -> "Postman"
    m = NUMBERED_HEADING_RE.match(name)
    if m:
        name = m.group(1).strip()
    # Early listing-title check BEFORE stripping location suffixes so that
    # "Leading Startups in Bangalore" is caught before "in Bangalore" is removed.
    if _LISTING_TITLE_RE.search(name):
        return ""
    # Strip trailing filler phrases like "for your business", "in India", "based in Bangalore", "to help", etc.
    name = re.sub(r"\b(for\s+your\s+.*|in\s+(?:india|bangalore|bengaluru|delhi|mumbai|pune).*|based\s+in.*|to\s+help.*)\b", "", name, flags=re.I).strip()
    # Split on common tagline separators if the first part looks like a name
    for sep in (" - ", " – ", " — ", " | ", " : ", " • "):
        if sep in name:
            part = name.split(sep)[0].strip()
            if 1 < len(part) <= 60:
                name = part
                break
    name = re.sub(r"^[\W\d_]+|[\W_]+$", "", name).strip()
    if name.lower() in IGNORE_NAMES or len(name) < 2 or len(name) > 80:
        return ""
    # Final listing-title check after all transformations (catches residues like "Leading Startups")
    if _LISTING_TITLE_RE.search(name):
        return ""
    # Reject bare category/industry labels ("SaaS", "SaaS sector", "B2B SaaS")
    if is_generic_category_name(name):
        return ""
    return name


def _is_valid_external_website(url: str, current_page_domain: str) -> tuple[str, str]:
    """Returns (clean_url, domain) if url is a valid external company website."""
    if not url:
        return "", ""
    u = url.strip()
    if not u.startswith("http://") and not u.startswith("https://"):
        return "", ""
    domain = extract_domain(u)
    if not domain or domain == current_page_domain:
        return "", ""
    if not is_company_domain(domain):
        return "", ""
    return u, domain


def extract_pagination_links(soup: BeautifulSoup, page_url: str) -> list[str]:
    """Return candidate 'next page' URLs found in a listing page (up to 3)."""
    page_domain = extract_domain(page_url)
    candidates: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href:
            continue
        text = a.get_text(" ", strip=True)
        # Detect "next page" anchors by text or rel attribute
        is_next = NEXT_PAGE_RE.search(text) or a.get("rel") in (["next"], "next")
        # Also detect page-number links (e.g. ?page=2, /page/2)
        is_paged = bool(re.search(r"[?&/]page[=/]\d+", href, re.I))
        if not (is_next or is_paged):
            continue
        full = urllib.parse.urljoin(page_url, href)
        d = extract_domain(full)
        if d != page_domain:
            continue
        if full not in seen:
            seen.add(full)
            candidates.append(full)
        if len(candidates) >= 3:
            break
    return candidates


def extract_outbound_company_links(soup: BeautifulSoup, page_url: str, page_domain: str) -> list[str]:
    """Collect all external links that point to individual company websites (not aggregators)."""
    found: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        clean, domain = _is_valid_external_website(href, page_domain)
        if clean and domain not in seen:
            seen.add(domain)
            found.append(clean)
    return found


def extract_from_directory_profile(url: str, title: str, snippet: str = "", location_hint: str = "") -> RawItem | None:
    """Extract single company info from a directory profile URL (e.g. f6s.com/company/postman)."""
    if not url:
        return None
    domain = extract_domain(url)
    if is_company_domain(domain):
        return None  # Direct company website, not a directory profile

    path = urllib.parse.urlparse(url).path
    m = PROFILE_PATH_RE.search(path)
    slug_name = m.group(1).replace("-", " ").replace("_", " ").title() if m else ""

    # Name from title
    t_clean = (title or "").split("|")[0].split("-")[0].split("–")[0].split(":")[0].strip()
    name = _clean_company_name(t_clean) or slug_name
    if not name or len(name) < 2:
        return None

    city, state = detect_locations(f"{title} {snippet} {location_hint}")
    return RawItem(
        name=name,
        source_id=url,
        source_url=url,
        title=title,
        description=snippet,
        city=city,
        state=state,
        location_hint=location_hint or f"{title} {snippet}",
        raw={"extracted_from": url, "source_type": "directory_profile", "name": name},
    )


def extract_from_json_ld(soup: BeautifulSoup, page_url: str, page_domain: str, location_hint: str = "") -> list[RawItem]:
    """Extract companies from JSON-LD schema (ItemList, Organization, LocalBusiness)."""
    items: list[RawItem] = []
    scripts = soup.find_all("script", type=re.compile(r"application/ld\+json", re.I))

    def _parse_entity(entity: dict):
        if not isinstance(entity, dict):
            return
        etype = str(entity.get("@type", "")).lower()
        if etype in ("organization", "corporation", "localbusiness", "company", "softwareapplication"):
            name = _clean_company_name(str(entity.get("name", "")))
            web = str(entity.get("url") or entity.get("sameAs") or "")
            clean_web, _ = _is_valid_external_website(web, page_domain)
            address = entity.get("address", {})
            city = state = ""
            if isinstance(address, dict):
                city = canonical_city(str(address.get("addressLocality", "")))
                state = canonical_state(str(address.get("addressRegion", "")))
            if not (city or state):
                city, state = detect_locations(f"{str(entity.get('description', ''))} {location_hint}")
            if name:
                items.append(RawItem(
                    name=name, website=clean_web, source_id=f"{page_url}#{name}", source_url=page_url,
                    city=city, state=state, description=str(entity.get("description", ""))[:500],
                    raw={"source_type": "json_ld", "name": name, "url": clean_web, "page_url": page_url},
                ))
        elif etype in ("itemlist", "orderedlist"):
            elem_list = entity.get("itemListElement", [])
            if isinstance(elem_list, list):
                for elem in elem_list:
                    if isinstance(elem, dict):
                        sub_item = elem.get("item", elem)
                        if isinstance(sub_item, dict):
                            _parse_entity(sub_item)
                        elif isinstance(sub_item, str):
                            cname = _clean_company_name(sub_item)
                            if cname:
                                c, s = detect_locations(location_hint)
                                items.append(RawItem(
                                    name=cname, source_id=f"{page_url}#{cname}", source_url=page_url,
                                    city=c, state=s,
                                    raw={"source_type": "json_ld_list", "name": cname, "page_url": page_url},
                                ))

    for script in scripts:
        try:
            content = script.string or script.get_text()
            if not content:
                continue
            data = json.loads(content)
            if isinstance(data, list):
                for d in data:
                    _parse_entity(d)
            elif isinstance(data, dict):
                if "@graph" in data and isinstance(data["@graph"], list):
                    for d in data["@graph"]:
                        _parse_entity(d)
                else:
                    _parse_entity(data)
        except Exception:
            continue
    return items


def extract_from_listicle_headings(
    soup: BeautifulSoup,
    page_url: str,
    page_domain: str,
    location_hint: str = ""
) -> list[RawItem]:
    """Extract company sections from article/listicle headings.

    A heading is accepted only when an external company website is found
    in the heading or its following section. This prevents product names,
    category names, and other arbitrary headings from being treated as
    companies.
    """
    items: list[RawItem] = []
    headings = soup.find_all(["h2", "h3", "h4"])
    seen_names = set()

    for h in headings:
        text = h.get_text(" ", strip=True)
        name = _clean_company_name(text)
        if not name or name.lower() in seen_names:
            continue

        # Look for an external company website inside the heading itself.
        website, domain = "", ""

        for a in h.find_all("a", href=True):
            w, d = _is_valid_external_website(a["href"], page_domain)
            if w:
                website, domain = w, d
                break

        # Look in following sibling elements up to the next heading.
        desc_parts = []
        loc_text = location_hint
        sibling = h.find_next_sibling()
        steps = 0

        while sibling and steps < 6:
            if sibling.name in ["h1", "h2", "h3", "h4"]:
                break

            if not website:
                for a in sibling.find_all("a", href=True):
                    w, d = _is_valid_external_website(a["href"], page_domain)
                    if w:
                        website, domain = w, d
                        break

            stext = sibling.get_text(" ", strip=True)
            if stext:
                desc_parts.append(stext)
                loc_text += " " + stext

            sibling = sibling.find_next_sibling()
            steps += 1

        # IMPORTANT:
        # Do not treat an arbitrary heading as a company.
        # Require a verified external company website.
        if not website:
            continue

        city, state = detect_locations(loc_text)
        desc = " ".join(desc_parts)[:500]

        seen_names.add(name.lower())

        items.append(RawItem(
            name=name,
            website=website,
            source_id=f"{page_url}#{name}",
            source_url=page_url,
            city=city,
            state=state,
            description=desc,
            location_hint=loc_text,
            raw={
                "source_type": "article_heading",
                "name": name,
                "website": website,
                "page_url": page_url,
            },
        ))

    return items


def extract_from_cards_and_tables(
    soup: BeautifulSoup,
    page_url: str,
    page_domain: str,
    location_hint: str = ""
) -> list[RawItem]:
    """Extract companies from structured company/directory cards.

    Avoids treating generic product/listing <li>/<tr> elements as companies.
    A result must have a company-specific container/class or a clearly
    company-oriented name element, plus an external website.
    """
    items: list[RawItem] = []
    seen_names = set()

    # Only target containers that strongly suggest a company/business record.
    containers = soup.select(
        "[class*='company-item'], [class*='company-card'], "
        "[class*='company-listing'], [class*='directory-item'], "
        "[class*='directory-card'], [class*='business-item'], "
        "[class*='business-card'], [class*='provider-row'], "
        "[class*='seller-item']"
    )

    for c in containers:
        # Avoid huge containers such as an entire directory/list.
        if len(c.get_text(" ", strip=True)) > 2000:
            continue

        # Prefer explicit company/business name elements.
        name_el = c.select_one(
            "[class*='company-name'], "
            "[class*='business-name'], "
            "[class*='company_name'], "
            "[class*='business_name'], "
            "[class*='seller-name'], "
            "[class*='provider-name'], "
            "[class*='name']"
        )

        if not name_el:
            # Only fall back to headings when the container itself is
            # explicitly company/business-oriented.
            name_el = c.select_one("h2, h3, h4")

        if not name_el:
            continue

        raw_name = name_el.get_text(" ", strip=True)
        name = _clean_company_name(raw_name)

        if not name or name.lower() in seen_names or len(name) < 2:
            continue

        # A company record must have an external website.
        website = ""
        domain = ""

        for a in c.find_all("a", href=True):
            w, d = _is_valid_external_website(a["href"], page_domain)
            if w:
                website = w
                domain = d
                break

        if not website:
            continue

        card_text = c.get_text(" ", strip=True)
        city, state = detect_locations(
            f"{card_text} {location_hint}"
        )

        seen_names.add(name.lower())

        items.append(
            RawItem(
                name=name,
                website=website,
                source_id=f"{page_url}#{name}",
                source_url=page_url,
                city=city,
                state=state,
                description=card_text[:500],
                location_hint=f"{card_text} {location_hint}",
                raw={
                    "source_type": "card_item",
                    "name": name,
                    "website": website,
                    "domain": domain,
                    "page_url": page_url,
                },
            )
        )

    return items

def extract_from_snippet(title: str, url: str, snippet: str, location_hint: str = "") -> list[RawItem]:
    """Fallback: extract company entities mentioned in search result snippets or profile titles."""
    items: list[RawItem] = []
    # 1. Check if URL is a single-company directory profile
    profile_item = extract_from_directory_profile(url, title, snippet, location_hint)
    if profile_item:
        items.append(profile_item)

    # 2. Check if snippet mentions companies in a list: "e.g. Postman, Hasura, Whatfix, and Chargebee"
    full_text = f"{title}. {snippet}"
    city, state = detect_locations(f"{full_text} {location_hint}")

    # Look for list phrases like "such as X, Y, and Z" or "including X, Y, Z"
    m = re.search(r"\b(?:like|including|such as|top \w+ (?:are|include))\s+([A-Za-z0-9\s,\.&]{5,150})(?:\.|\;|\:|$)", snippet, re.I)
    if m:
        candidates = re.split(r",|\band\b|&", m.group(1))
        for cand in candidates:
            cname = _clean_company_name(cand.strip())
            if cname and 2 <= len(cname) <= 50 and cname.lower() not in IGNORE_NAMES:
                items.append(RawItem(
                    name=cname, source_id=f"{url}#{cname}", source_url=url,
                    city=city, state=state, description=snippet[:300],
                    raw={"source_type": "snippet_entity", "name": cname, "page_url": url},
                ))
    return items


def extract_from_listing_page(page_url: str, html: str, location_hint: str = "") -> list[RawItem]:
    """Parse an HTML listing/directory/article page and return individual company items."""
    items, _ = extract_listing_page_full(page_url, html, location_hint)
    return items


def extract_listing_page_full(
    page_url: str, html: str, location_hint: str = ""
) -> tuple[list[RawItem], list[str]]:
    """Parse a listing page and return (company_items, next_page_urls).

    The second element contains up to 3 candidate URLs for the next pagination page,
    which the engine can optionally follow to extract more companies.
    """
    if not html or not page_url:
        return [], []

    page_domain = extract_domain(page_url)
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return [], []

    # Inherit location from page title/h1 if not provided
    page_title = (soup.title.string if soup.title else "") or ""
    h1 = soup.find("h1")
    h1_text = h1.get_text(" ", strip=True) if h1 else ""
    page_loc_hint = f"{location_hint} {page_title} {h1_text}".strip()

    extracted: list[RawItem] = []
    seen: set[str] = set()

    def _add(items: list[RawItem]) -> None:
        for item in items:
            key = normalize_name(item.name) or extract_domain(item.website or "")
            if key and key not in seen:
                seen.add(key)
                # Also register domain so outbound-link fallback doesn't duplicate
                d = extract_domain(item.website or "")
                if d:
                    seen.add(d)
                extracted.append(item)

    # 1. Structured schema.org data
    _add(extract_from_json_ld(soup, page_url, page_domain, page_loc_hint))

    # 2. Heading listicles (e.g. 1. Postman, 2. Hasura)
    _add(extract_from_listicle_headings(soup, page_url, page_domain, page_loc_hint))

    # 3. Card/Table listings — always run, not only as a fallback
    _add(extract_from_cards_and_tables(soup, page_url, page_domain, page_loc_hint))

    # 4. Fallback: harvest verified outbound company website links if still very few results
    if len(extracted) < 3:
        for url in extract_outbound_company_links(soup, page_url, page_domain):
            d = extract_domain(url)
            if d and d not in seen:
                seen.add(d)
                city, state = detect_locations(page_loc_hint)
                extracted.append(RawItem(
                    website=url, source_id=url, source_url=page_url,
                    city=city, state=state,
                    raw={"source_type": "outbound_link", "url": url, "page_url": page_url},
                ))

    # Final sanity check: if city/state is missing, inherit from page context
    def_city, def_state = detect_locations(page_loc_hint)
    for it in extracted:
        if not it.city and def_city:
            it.city = def_city
        if not it.state and (def_state or state_of(it.city)):
            it.state = def_state or state_of(it.city)

    # Pagination links
    next_pages = extract_pagination_links(soup, page_url)

    return extracted, next_pages
