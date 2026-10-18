"""FastAPI routes for discovery. Mount with:  app.include_router(discovery_router, prefix="/api")"""
from __future__ import annotations

import csv
import io
import json
import time

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import get_engine
from .adapters import company_to_prospect
from .icp import interpret_icp

router = APIRouter()


class RunRequest(BaseModel):
    icp_text: str = Field(min_length=3)
    providers: list[str] | None = None            # default: all enabled
    cities: list[str] | None = None               # extra cities on top of the ICP's
    states: list[str] | None = None
    max_queries_per_provider: int | None = Field(None, ge=1, le=5000)
    max_pages: int | None = Field(None, ge=1, le=20)
    target_unique: int | None = Field(None, ge=1)  # stop early once this many unique companies found
    use_ollama: bool = True


def _run_or_404(run_id: int) -> dict:
    run = get_engine().store.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


def _run_view(run: dict) -> dict:
    st = get_engine().store
    counts = {r["status"]: r["n"] for r in st._all(
        "SELECT status, COUNT(*) n FROM discovery_queries WHERE run_id=? GROUP BY status", (run["id"],))}
    finished = sum(counts.get(k, 0) for k in ("done", "partial", "failed", "skipped"))
    run = dict(run)
    run["options"] = json.loads(run.pop("options_json") or "{}")
    run["icp_spec"] = json.loads(run.pop("icp_spec_json") or "{}")
    run["query_status_counts"] = counts
    run["progress"] = round(finished / run["queries_total"], 3) if run["queries_total"] else 0.0
    return run


@router.get("/discovery/providers")
def providers():
    e = get_engine()
    return [{"name": p.name, "kind": p.kind, "confidence": p.confidence} for p in e.providers]


@router.post("/discovery/runs", status_code=202)
def start_run(req: RunRequest):
    e = get_engine()
    opts = req.model_dump(exclude={"icp_text"}, exclude_none=True)
    run_id = e.create_run(req.icp_text, opts)
    e.start_background(run_id)
    return _run_view(e.store.get_run(run_id))


@router.get("/discovery/runs")
def list_runs(limit: int = Query(50, le=200), offset: int = 0):
    return [_run_view(r) for r in get_engine().store.list_runs(limit, offset)]


@router.get("/discovery/runs/{run_id}")
def get_run(run_id: int):
    v = _run_view(_run_or_404(run_id))
    v["providers"] = get_engine().store.provider_breakdown(run_id)
    return v


@router.post("/discovery/runs/{run_id}/cancel")
def cancel_run(run_id: int):
    _run_or_404(run_id)
    get_engine().cancel(run_id)
    return {"ok": True}


@router.get("/discovery/runs/{run_id}/queries")
def run_queries(run_id: int, provider: str | None = None, status: str | None = None,
                limit: int = Query(100, le=1000), offset: int = 0):
    _run_or_404(run_id)
    return get_engine().store.list_queries(run_id, provider, status, limit, offset)


@router.get("/discovery/runs/{run_id}/errors")
def run_errors(run_id: int, limit: int = Query(100, le=1000), offset: int = 0):
    _run_or_404(run_id)
    return get_engine().store.list_errors(run_id, limit, offset)


@router.get("/discovery/runs/{run_id}/raw-results")
def run_raw(run_id: int, provider: str | None = None, limit: int = Query(100, le=1000), offset: int = 0):
    _run_or_404(run_id)
    return get_engine().store.list_raw(run_id, provider, limit, offset)


@router.get("/discovery/runs/{run_id}/companies")
def run_companies(run_id: int, q: str | None = None, limit: int = Query(100, le=1000), offset: int = 0):
    _run_or_404(run_id)
    st = get_engine().store
    return {"total": st.count_companies(run_id), "items": st.list_companies(run_id, q, limit, offset)}


@router.get("/discovery/runs/{run_id}/companies.csv")
def export_csv(run_id: int):
    _run_or_404(run_id)
    st = get_engine().store
    cols = ["id", "name", "domain", "website", "city", "state", "country", "phone", "address", "confidence"]

    def gen():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols + ["sources"])
        yield buf.getvalue(); buf.seek(0); buf.truncate()
        offset = 0
        while True:
            rows = st.list_companies(run_id, None, 1000, offset)
            if not rows:
                return
            for r in rows:
                w.writerow([r.get(c, "") for c in cols] + [";".join(s["provider"] for s in r["sources"])])
            yield buf.getvalue(); buf.seek(0); buf.truncate()
            offset += 1000

    return StreamingResponse(gen(), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="discovery_run_{run_id}.csv"'})


# ---- frontend contract (src/services/api.ts) --------------------------------------------------

class TextBody(BaseModel):
    text: str


@router.post("/icp/analyze")
def analyze_icp(body: TextBody):
    """IcpProfile for the 'OUTZAAR understands' panel. Decision makers / needs / signals belong to later phases."""
    e = get_engine()
    spec, _ = interpret_icp(body.text, ollama_url=e.s.ollama_url, model=e.s.ollama_model, timeout=e.s.ollama_timeout)
    return {
        "industry": ", ".join(spec.industries[:3]) or ", ".join(spec.terms()[:3]),
        "location": ", ".join(spec.cities or spec.states) or "India (all)",
        "companySize": spec.company_size or "Any",
        "potentialNeed": "", "decisionMakers": [], "buyingSignals": [],
    }


class ProspectSearch(BaseModel):
    icp_text: str | None = None
    text: str | None = None
    industry: str | None = None
    location: str | None = None
    wait_seconds: int = Field(20, ge=0, le=120)
    limit: int = Field(100, ge=1, le=500)
    max_queries_per_provider: int | None = 40      # keep interactive searches quick; full runs use /discovery/runs


@router.post("/prospects/search")
def prospects_search(body: ProspectSearch):
    """Starts a run, waits briefly, returns whatever was found so far as Prospect[].
    The run keeps going in the background: poll /discovery/runs/{id}/companies for more.
    The run id is returned in the X-Discovery-Run-Id header."""
    from fastapi.responses import JSONResponse
    text = body.icp_text or body.text or " ".join(x for x in (body.industry, body.location) if x)
    if len(text.strip()) < 3:
        raise HTTPException(422, "No ICP text supplied")
    e = get_engine()
    run_id = e.create_run(text, {"max_queries_per_provider": body.max_queries_per_provider})
    e.start_background(run_id)
    deadline = time.time() + body.wait_seconds
    while time.time() < deadline:
        r = e.store.get_run(run_id)
        if r["status"] not in ("pending", "running") or r["unique_count"] >= body.limit:
            break
        time.sleep(0.5)
    rows = e.store.list_companies(run_id, None, body.limit, 0)
    return JSONResponse([company_to_prospect(c) for c in rows], headers={"X-Discovery-Run-Id": str(run_id)})
