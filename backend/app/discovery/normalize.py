"""Normalization: raw provider item -> comparable company record. Never rejects for missing fields."""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

from .geo import canonical_city, canonical_state, detect_locations, state_of
from .providers.base import RawItem

# Domains that are aggregators / directories / social / media, NOT a company's own site.
# A result on one of these never yields a company "domain".
NON_COMPANY_DOMAINS = {
    # Tech & Startup directories / listings
    "f6s.com", "beststartup.asia", "beststartup.in", "beststartup.co.uk",
    "getlatka.com", "latka.com", "wellfound.com", "angel.co",
    "tracxn.com", "crunchbase.com", "clutch.co", "goodfirms.co",
    "softwaresuggest.com", "g2.com", "capterra.com", "producthunt.com",
    "saashub.com", "alternativeto.net", "trustradius.com", "peerspot.com",
    "startuptalky.com", "failory.com", "topstartups.io", "pitchbook.com",
    "cbinsights.com", "apollo.io", "rocketreach.co", "lusha.com",
    "zoominfo.com", "dnb.com", "kompass.com", "dealroom.co",
    "ventureslist.com", "startupranking.com",

    # Media, blogs, publishers, social
    "inc42.com", "yourstory.com", "entrackr.com", "medianama.com",
    "techinasia.com", "techcrunch.com", "venturebeat.com", "forbes.com",
    "business-standard.com", "economictimes.com", "moneycontrol.com",
    "livemint.com", "hindubusinessline.com", "timesofindia.com", "ndtv.com",
    "medium.com", "substack.com", "wordpress.com", "blogspot.com",
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "pinterest.com", "reddit.com", "quora.com",
    "wikipedia.org", "wikimedia.org", "github.com",

    # B2B Trade directories & Aggregators
    "indiamart.com", "tradeindia.com", "exportersindia.com", "justdial.com",
    "sulekha.com", "yellowpages.in", "asklaila.com", "made-in-china.com",
    "alibaba.com", "aliexpress.com", "amazon.in", "amazon.com", "flipkart.com",
    "zaubacorp.com", "tofler.in", "instafinancials.com", "thecompanycheck.com",
    "tradeindia.in",

    # Job boards & search engines
    "glassdoor.com", "glassdoor.co.in", "ambitionbox.com", "naukri.com",
    "indeed.com", "google.com", "google.co.in", "bing.com", "yahoo.com",
    "duckduckgo.com", "mapquest.com",

    # Govt & Trade Associations
    "gov.in", "nic.in", "mca.gov.in", "fieo.org", "cii.in", "ficci.in",
    "eepcindia.org", "nasscom.in", "assocham.org",
}

LEGAL_SUFFIXES = {
    "pvt", "private", "ltd", "limited", "llp", "inc", "incorporated", "co", "company",
    "corp", "corporation", "opc", "p", "the",
}
GENERIC_SEGMENTS = {
    "home", "homepage", "welcome", "contact us", "about us", "about", "official website",
    "official site", "products", "services", "index", "linkedin", "facebook", "f6s",
    "wellfound", "crunchbase", "clutch", "getlatka", "latka", "beststartup", "tracxn",
}
LISTING_HINT = re.compile(
    r"\b(top\s+\d+|best\s+\d+|\d+\s+(?:best|top|leading)|list\s+of|directory|companies\s+in|"
    r"startups\s+in|manufacturers\s+in|suppliers\s+in|exporters\s+in|leading\s+\w+\s+in|"
    r"\d{1,3}\+?\s+(?:best|top|leading)"
    # Catches "Top B2B SaaS Companies", "Best SaaS Companies", "Leading Startups", etc.
    r"|(?:top|best|leading|top-rated)\s+\w[\w\s]*?\s+(?:companies|startups|firms|vendors|providers|manufacturers|suppliers|exporters)"
    r")\b", re.I)
COMPANY_SUFFIX = re.compile(
    r"\b(pvt\.?|private|ltd\.?|limited|llp|industries|enterprises|exports?|engineering|"
    r"mfg|manufacturing|technologies|systems|corporation|works|fabricators|products|software|"
    r"solutions|labs|tech|ai|analytics|robotics)\b", re.I)
SEPARATORS = re.compile(r"\s+[-–—|:•»·]\s+|\s*\|\s*")

# "Key facts about Razorpay" / "About SaaS sector" -> captures the part after "about".
# Whether the captured text is a genuine company or itself a generic label is decided
# separately (see is_generic_category_name); this only unwraps the "about"-style framing
# so the real subject can be evaluated on its own.
ABOUT_PREFIX_RE = re.compile(
    r"^(?:key\s+facts?\s+about|quick\s+facts?\s+about|facts?\s+about|about)\s+(.+)$", re.I)

# "About Us" / "About Our Company" style headings never name a company; captured text
# matching these is rejected outright rather than treated as a company candidate.
_ABOUT_STOPWORDS = {
    "us", "this", "this company", "our company", "our team", "our business",
    "the company", "this business", "the team",
}

# Bare category / industry / sector labels that are sometimes mistaken for company names
# (e.g. a page heading "SaaS" or "About SaaS sector"). A name consisting ONLY of these
# tokens is rejected; a real company name that happens to include one (e.g. "Capillary
# Technologies") is unaffected since it also carries a non-generic token.
GENERIC_CATEGORY_WORDS = {
    "saas", "b2b", "b2c", "d2c", "fintech", "edtech", "healthtech", "insurtech", "proptech",
    "agritech", "cleantech", "deeptech", "martech", "adtech",
    "ecommerce", "e-commerce", "sector", "industry", "market", "domain", "space",
    "vertical", "niche", "companies", "startups", "startup", "company",
}


def resolve_about_prefix(name: str) -> str:
    """Unwrap an "about"-style heading into its subject.

    'Key facts about Razorpay' -> 'Razorpay'; 'About SaaS sector' -> 'SaaS sector'.
    Returns the name unchanged if it doesn't match the "about" pattern, and returns ''
    when the pattern matches but the subject is itself non-company boilerplate
    ("About Us").
    """
    if not name:
        return name
    m = ABOUT_PREFIX_RE.match(name.strip())
    if not m:
        return name
    captured = re.sub(r"\s+", " ", m.group(1)).strip(" .")
    if captured.lower() in _ABOUT_STOPWORDS:
        return ""
    return captured


def is_generic_category_name(name: str) -> bool:
    """True when `name` is a bare category/industry label rather than a real company,
    e.g. 'SaaS', 'B2B SaaS', 'SaaS sector' -- but not 'Capillary Technologies'."""
    if not name:
        return False
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    if not tokens:
        return False
    return all(t in GENERIC_CATEGORY_WORDS for t in tokens)


def domain_matches_name(name: str, domain: str) -> bool:
    """Loose but reasonably strong check that `domain` plausibly belongs to `name`,
    used to verify a domain found via search before attaching it to a company."""
    if not name or not domain:
        return False
    name_slug = normalize_name(name).replace(" ", "")
    host_slug = re.sub(r"[^a-z0-9]", "", domain.split(".")[0].lower())
    if not name_slug or not host_slug:
        return False
    if name_slug == host_slug:
        return True
    if len(name_slug) >= 4 and (name_slug in host_slug or host_slug in name_slug):
        return True
    if len(name_slug) >= 6 and len(host_slug) >= 6 and name_slug[:6] == host_slug[:6]:
        return True
    return False


def extract_domain(url: str) -> str:
    """Registrable-ish domain ('shop.abc.co.in' -> 'abc.co.in'). '' if none."""
    if not url:
        return ""
    u = url.strip()
    if "://" not in u:
        u = "http://" + u
    try:
        host = (urllib.parse.urlparse(u).hostname or "").lower().strip(".")
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return ""
    labels = host.split(".")
    if len(labels) >= 3 and labels[-2] in {"co", "com", "org", "net", "ac", "gov", "edu", "nic", "res"} and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def is_company_domain(domain: str) -> bool:
    if not domain:
        return False
    return not any(domain == d or domain.endswith("." + d) for d in NON_COMPANY_DOMAINS)


def normalize_name(name: str) -> str:
    n = (name or "").lower().replace("&", " and ")
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    toks = [t for t in n.split() if t]
    core = [t for t in toks if t not in LEGAL_SUFFIXES]
    return " ".join(core or toks)


def name_from_title(title: str, domain: str = "") -> str:
    """Pull a company-looking name out of a page/search title."""
    t = re.sub(r"\s+", " ", (title or "")).strip()
    if not t:
        return domain.split(".")[0].replace("-", " ").title() if domain else ""
    segs = [s.strip() for s in SEPARATORS.split(t) if s.strip()]
    segs = [s for s in segs if s.lower() not in GENERIC_SEGMENTS] or segs
    for s in segs:                       # prefer a segment that looks like a company name
        if COMPANY_SUFFIX.search(s) and len(s) <= 80:
            return s
    first = segs[0] if segs else t
    if len(first) > 80 and domain:
        return domain.split(".")[0].replace("-", " ").title()
    return first[:120]


@dataclass
class NormalizedItem:
    name: str
    name_norm: str
    domain: str
    website: str
    city: str
    state: str
    city_norm: str
    state_norm: str
    phone: str
    address: str
    description: str
    source_id: str
    source_url: str
    is_listing: bool = False
    note: str = ""
    verdict: str = "ok"          # ok | reject | uncertain (see classifier.classify)
    reason: str = ""

    @property
    def resolvable(self) -> bool:
        """Identifiable enough to become a company record: needs a name or a domain, and must
        not be a listing/product/section (uncertain stays unresolved until the engine vets it)."""
        return bool(self.name_norm or self.domain) and not self.is_listing and self.verdict == "ok"


def normalize(item: RawItem, trusted: bool = False) -> NormalizedItem:
    """`trusted` = structured provider data (Maps, Apollo, directory scrapers): skip the name filter."""
    raw_website = (item.website or "").strip()
    raw_source = (item.source_url or "").strip()
    domain = extract_domain(raw_website)
    
    # If the domain is an aggregator / directory, clear domain so directory is never saved as company domain
    if not is_company_domain(domain):
        domain, website = "", ""
    elif raw_website and "://" not in raw_website:
        website = "https://" + raw_website
    else:
        website = raw_website

    name = (item.name or "").strip()
    # Unwrap "Key facts about X" / "About X" style names/titles into their subject X
    # before anything else, so downstream checks (listing detection, generic-category
    # rejection, dedup) see the real candidate rather than the framing text.
    if name:
        name = resolve_about_prefix(name)
    if not name and item.title:
        resolved_title = resolve_about_prefix(item.title)
        if resolved_title:            # "" means the title was "About Us"-style boilerplate
            name = name_from_title(resolved_title, domain)
    first_seg = (SEPARATORS.split(item.title.strip())[0] if item.title else "")
    
    # Detect listing/article page from title, domain, or URL path
    path = urllib.parse.urlparse(raw_source or raw_website).path.lower()
    is_listing_path = any(s in path for s in ("/top-", "/best-", "/companies-in-", "/startups-in-", "/list-of-", "/directory/"))
    # Check both the title (when no explicit name) AND the name itself:
    # A RawItem with name="Top B2B SaaS Companies" must also be flagged as a listing.
    _listing_candidate = first_seg or item.title or ""
    is_listing = bool(
        (
            # Title-derived listing detection (original logic, no explicit name)
            not item.name and (
                (_listing_candidate and LISTING_HINT.search(_listing_candidate) and not COMPANY_SUFFIX.search(first_seg))
                or is_listing_path
            )
        ) or (
            # Name-based listing detection: catches names like "Top B2B SaaS Companies"
            item.name and LISTING_HINT.search(item.name) and not COMPANY_SUFFIX.search(item.name)
        ) or (
            # Bare category/industry labels ("SaaS", "About SaaS sector" -> "SaaS sector")
            # are never a company, whether they arrived as name or as the unwrapped subject.
            is_generic_category_name(name)
        )
    )

    city = canonical_city(item.city)
    state = canonical_state(item.state)
    if not city and not state:
        c, s = detect_locations(item.address or "")
        if not (c or s):
            c, s = detect_locations(item.location_hint or "")
        if not (c or s):
            c, s = detect_locations(item.title or "")
        city, state = c, s
    if city and not state:
        state = state_of(city)

    verdict, reason = "ok", ""
    if not trusted and not is_listing:
        from .classifier import classify          # local import: classifier imports this module
        title_derived = not (item.name or "").strip()
        verdict, reason = classify(name, domain, str((item.raw or {}).get("source_type", "")), title_derived)
        if verdict == "reject" and title_derived and domain:
            # Product/section title on a real company domain: never use the title as the name;
            # keep the bare domain only if the engine can confirm it is a company site.
            name, verdict, reason = "", "uncertain", f"domain only ({reason})"

    return NormalizedItem(
        name=name, name_norm=normalize_name(name), domain=domain, website=website,
        city=city, state=state, city_norm=city.lower(), state_norm=state.lower(),
        phone=(item.phone or "").strip(), address=(item.address or "").strip(),
        description=(item.description or "").strip()[:1000],
        source_id=(item.source_id or "").strip(), source_url=raw_source or raw_website,
        is_listing=is_listing,
        note=("listing/article page, not a single company" if is_listing
              else f"rejected: {reason}" if verdict == "reject" else ""),
        verdict=verdict, reason=reason,
    )