"""Maps discovery companies onto the frontend's Prospect shape (src/types/index.ts).

Discovery has no scoring, signals or decision makers yet (later phases), so those fields are
neutral placeholders. If the frontend's Company/Prospect interfaces differ from this guess,
this is the ONLY place to change.
"""
from __future__ import annotations


def company_to_prospect(c: dict) -> dict:
    location = ", ".join(x for x in (c.get("city"), c.get("state")) if x) or "India"
    return {
        "id": f"co_{c['id']}",
        "company": {
            "id": c["id"], "name": c.get("name") or c.get("domain") or "Unknown company",
            "website": c.get("website") or (f"https://{c['domain']}" if c.get("domain") else ""),
            "domain": c.get("domain") or "", "location": location, "city": c.get("city") or "",
            "state": c.get("state") or "", "country": c.get("country") or "India",
            "phone": c.get("phone") or "", "address": c.get("address") or "",
            "description": c.get("description") or "", "industry": "", "size": "",
        },
        "fitScore": 0, "signals": [], "painPoints": [], "decisionMakers": [],
        "whyIdentified": "Discovered from " + ", ".join(sorted({s["provider"] for s in c.get("sources", [])}) or ["search"]),
        "fitReasoning": [], "outreachAngle": "",
        "discovery": {"confidence": c.get("confidence", "low"), "sources": c.get("sources", [])},
    }
