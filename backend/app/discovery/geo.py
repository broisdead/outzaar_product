"""Indian geography used for query expansion and location detection."""
from __future__ import annotations

import re

STATES = [
    "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Puducherry", "Chandigarh",
    "Jammu and Kashmir",
]

# city -> state
CITIES: dict[str, str] = {
    "Mumbai": "Maharashtra", "Navi Mumbai": "Maharashtra", "Thane": "Maharashtra",
    "Pune": "Maharashtra", "Nashik": "Maharashtra", "Nagpur": "Maharashtra",
    "Aurangabad": "Maharashtra", "Kolhapur": "Maharashtra", "Solapur": "Maharashtra",
    "Delhi": "Delhi", "New Delhi": "Delhi",
    "Noida": "Uttar Pradesh", "Greater Noida": "Uttar Pradesh", "Ghaziabad": "Uttar Pradesh",
    "Lucknow": "Uttar Pradesh", "Kanpur": "Uttar Pradesh", "Agra": "Uttar Pradesh",
    "Varanasi": "Uttar Pradesh", "Meerut": "Uttar Pradesh", "Moradabad": "Uttar Pradesh",
    "Aligarh": "Uttar Pradesh", "Firozabad": "Uttar Pradesh",
    "Gurugram": "Haryana", "Faridabad": "Haryana", "Manesar": "Haryana", "Sonipat": "Haryana",
    "Panipat": "Haryana", "Bahadurgarh": "Haryana", "Rohtak": "Haryana", "Ambala": "Haryana",
    "Ludhiana": "Punjab", "Jalandhar": "Punjab", "Amritsar": "Punjab", "Mohali": "Punjab",
    "Chandigarh": "Chandigarh", "Baddi": "Himachal Pradesh",
    "Jaipur": "Rajasthan", "Jodhpur": "Rajasthan", "Udaipur": "Rajasthan",
    "Bhiwadi": "Rajasthan", "Kota": "Rajasthan",
    "Ahmedabad": "Gujarat", "Surat": "Gujarat", "Vadodara": "Gujarat", "Rajkot": "Gujarat",
    "Morbi": "Gujarat", "Vapi": "Gujarat", "Bharuch": "Gujarat", "Ankleshwar": "Gujarat",
    "Gandhinagar": "Gujarat", "Sanand": "Gujarat",
    "Bengaluru": "Karnataka", "Mysuru": "Karnataka", "Hubballi": "Karnataka",
    "Belagavi": "Karnataka", "Tumakuru": "Karnataka", "Mangaluru": "Karnataka",
    "Chennai": "Tamil Nadu", "Coimbatore": "Tamil Nadu", "Hosur": "Tamil Nadu",
    "Tiruppur": "Tamil Nadu", "Madurai": "Tamil Nadu", "Salem": "Tamil Nadu",
    "Tiruchirappalli": "Tamil Nadu", "Vellore": "Tamil Nadu", "Sriperumbudur": "Tamil Nadu",
    "Hyderabad": "Telangana", "Warangal": "Telangana",
    "Visakhapatnam": "Andhra Pradesh", "Vijayawada": "Andhra Pradesh", "Tirupati": "Andhra Pradesh",
    "Kochi": "Kerala", "Thiruvananthapuram": "Kerala", "Kozhikode": "Kerala",
    "Kolkata": "West Bengal", "Howrah": "West Bengal", "Durgapur": "West Bengal",
    "Bhubaneswar": "Odisha", "Cuttack": "Odisha", "Rourkela": "Odisha",
    "Jamshedpur": "Jharkhand", "Ranchi": "Jharkhand", "Dhanbad": "Jharkhand",
    "Raipur": "Chhattisgarh", "Bhilai": "Chhattisgarh",
    "Bhopal": "Madhya Pradesh", "Indore": "Madhya Pradesh", "Pithampur": "Madhya Pradesh",
    "Dewas": "Madhya Pradesh", "Gwalior": "Madhya Pradesh",
    "Dehradun": "Uttarakhand", "Haridwar": "Uttarakhand", "Rudrapur": "Uttarakhand",
    "Guwahati": "Assam", "Patna": "Bihar", "Panaji": "Goa", "Puducherry": "Puducherry",
}

# Canonical spelling for common aliases (lowercase -> canonical)
ALIASES = {
    "bangalore": "Bengaluru", "gurgaon": "Gurugram", "bombay": "Mumbai",
    "calcutta": "Kolkata", "madras": "Chennai", "poona": "Pune", "baroda": "Vadodara",
    "cochin": "Kochi", "trivandrum": "Thiruvananthapuram", "vizag": "Visakhapatnam",
    "mysore": "Mysuru", "trichy": "Tiruchirappalli", "orissa": "Odisha",
    "chhatrapati sambhajinagar": "Aurangabad", "new delhi": "Delhi", "delhi ncr": "Delhi",
    "uttaranchal": "Uttarakhand", "pondicherry": "Puducherry",
}

# Hubs used when the ICP names no location (India-wide coverage)
TOP_HUBS = [
    "Mumbai", "Pune", "Delhi", "Noida", "Gurugram", "Faridabad", "Ghaziabad", "Bengaluru",
    "Chennai", "Hyderabad", "Kolkata", "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Jaipur",
    "Ludhiana", "Coimbatore", "Nashik", "Aurangabad", "Nagpur", "Indore", "Bhopal", "Lucknow",
    "Kanpur", "Faridabad", "Vapi", "Hosur", "Tiruppur", "Kochi", "Visakhapatnam", "Raipur",
    "Jamshedpur", "Bhubaneswar", "Chandigarh", "Mohali", "Jalandhar", "Panipat", "Sonipat",
    "Morbi", "Ankleshwar", "Pithampur", "Baddi", "Manesar", "Sanand", "Dehradun", "Guwahati", "Patna",
]

_STATE_LOWER = {s.lower(): s for s in STATES}
_STATE_LOWER["orissa"] = "Odisha"
_PLACE_PATTERNS: list[tuple[re.Pattern, str, str]] = []


def canonical_city(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return ""
    return ALIASES.get(n.lower(), n)


def canonical_state(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return ""
    low = n.lower()
    return ALIASES.get(low) if ALIASES.get(low) in STATES else _STATE_LOWER.get(low, n)


def state_of(city: str) -> str:
    return CITIES.get(canonical_city(city), "")


def _patterns():
    if not _PLACE_PATTERNS:
        names = set(CITIES) | set(ALIASES) | set(STATES)
        for n in sorted(names, key=len, reverse=True):     # longest first: "Navi Mumbai" before "Mumbai"
            _PLACE_PATTERNS.append((re.compile(r"\b" + re.escape(n) + r"\b", re.I), n, ""))
    return _PLACE_PATTERNS


def detect_locations(text: str) -> tuple[str, str]:
    """Best-effort (city, state) from free text. Empty strings when unknown."""
    if not text:
        return "", ""
    city = state = ""
    for pat, name, _ in _patterns():
        if pat.search(text):
            canon = canonical_city(name)
            if canon in CITIES or name.lower() in ALIASES and canon not in STATES:
                if not city:
                    city = canon
            elif canonical_state(name) in STATES and not state:
                state = canonical_state(name)
            if city and state:
                break
    if city and not state:
        state = state_of(city)
    return city, state
