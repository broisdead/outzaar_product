"""SQLite persistence (stdlib). Single connection guarded by a lock; safe for the engine's worker threads."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from .normalize import NormalizedItem

SCHEMA = """
CREATE TABLE IF NOT EXISTS discovery_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  icp_text TEXT NOT NULL, options_json TEXT DEFAULT '{}', icp_spec_json TEXT DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'pending',
  queries_total INTEGER DEFAULT 0, queries_done INTEGER DEFAULT 0, queries_failed INTEGER DEFAULT 0,
  raw_count INTEGER DEFAULT 0,          -- every provider result stored
  unique_count INTEGER DEFAULT 0,       -- distinct companies seen in this run
  new_count INTEGER DEFAULT 0,          -- of those, never seen in any earlier run
  duplicate_count INTEGER DEFAULT 0,    -- raw results that repeated a company already seen in this run
  unresolved_count INTEGER DEFAULT 0,   -- raw results with no name/domain, or list/article pages (kept raw)
  listing_count INTEGER DEFAULT 0,      -- listing/directory pages detected and processed
  extracted_count INTEGER DEFAULT 0,    -- companies extracted from listing pages
  resolved_count INTEGER DEFAULT 0,     -- name-only candidates whose domain was resolved post-discovery
  error_count INTEGER DEFAULT 0,
  created_at TEXT, started_at TEXT, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS discovery_queries (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, provider TEXT NOT NULL,
  query_text TEXT NOT NULL, params_json TEXT DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'pending',   -- pending|running|done|partial|failed|skipped
  pages_fetched INTEGER DEFAULT 0, results_count INTEGER DEFAULT 0, error TEXT,
  created_at TEXT, finished_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_q_run ON discovery_queries(run_id, provider, status);
CREATE TABLE IF NOT EXISTS companies (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, name_norm TEXT, domain TEXT, website TEXT,
  city TEXT, city_norm TEXT DEFAULT '', state TEXT, state_norm TEXT DEFAULT '', country TEXT DEFAULT 'India',
  phone TEXT, address TEXT, description TEXT, confidence TEXT DEFAULT 'low',
  first_run_id INTEGER, created_at TEXT, updated_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_c_domain ON companies(domain);
CREATE INDEX IF NOT EXISTS ix_c_name ON companies(name_norm, city_norm, state_norm);
CREATE TABLE IF NOT EXISTS company_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, provider TEXT NOT NULL,
  source_id TEXT NOT NULL, source_url TEXT, run_id INTEGER, created_at TEXT,
  UNIQUE(provider, source_id)
);
CREATE INDEX IF NOT EXISTS ix_cs_company ON company_sources(company_id);
CREATE TABLE IF NOT EXISTS run_companies (
  run_id INTEGER NOT NULL, company_id INTEGER NOT NULL, PRIMARY KEY(run_id, company_id)
);
CREATE TABLE IF NOT EXISTS raw_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, query_id INTEGER, provider TEXT NOT NULL,
  query_text TEXT, page INTEGER, source_id TEXT, source_url TEXT,
  name TEXT, website TEXT, city TEXT, state TEXT,
  company_id INTEGER, is_duplicate INTEGER DEFAULT 0, matched_by TEXT, note TEXT,
  raw_json TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_r_run ON raw_results(run_id, provider);
CREATE INDEX IF NOT EXISTS ix_r_company ON raw_results(company_id);
CREATE TABLE IF NOT EXISTS provider_errors (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, provider TEXT, query_id INTEGER,
  message TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_e_run ON provider_errors(run_id);
"""

RUN_COUNTERS = {"queries_done", "queries_failed", "raw_count", "unique_count", "new_count",
                "duplicate_count", "unresolved_count", "listing_count", "extracted_count",
                "resolved_count", "error_count", "queries_total"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = "outzaar_discovery.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            if path != ":memory:":
                self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.executescript(SCHEMA)

    @contextmanager
    def tx(self):
        with self.lock:
            self.conn.execute("BEGIN")
            try:
                yield self.conn
                self.conn.execute("COMMIT")
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise

    def _all(self, sql, params=()) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def _one(self, sql, params=()) -> dict | None:
        rows = self._all(sql, params)
        return rows[0] if rows else None

    # ---- runs -----------------------------------------------------------
    def create_run(self, icp_text: str, options: dict) -> int:
        with self.tx() as c:
            cur = c.execute("INSERT INTO discovery_runs(icp_text, options_json, created_at) VALUES (?,?,?)",
                            (icp_text, json.dumps(options), now()))
            return cur.lastrowid

    def get_run(self, run_id: int) -> dict | None:
        return self._one("SELECT * FROM discovery_runs WHERE id=?", (run_id,))

    def list_runs(self, limit=50, offset=0) -> list[dict]:
        return self._all("SELECT * FROM discovery_runs ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))

    def update_run(self, run_id: int, **fields) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        with self.tx() as c:
            c.execute(f"UPDATE discovery_runs SET {cols} WHERE id=?", (*fields.values(), run_id))

    def bump_run(self, c, run_id: int, **deltas) -> None:
        """Increment counters inside an open transaction."""
        for k in deltas:
            assert k in RUN_COUNTERS, k
        cols = ", ".join(f"{k}={k}+?" for k in deltas)
        c.execute(f"UPDATE discovery_runs SET {cols} WHERE id=?", (*deltas.values(), run_id))

    def bump(self, run_id: int, **deltas) -> None:
        with self.tx() as c:
            self.bump_run(c, run_id, **deltas)

    # ---- queries / errors -----------------------------------------------
    def add_queries(self, run_id: int, provider: str, queries: list[tuple[str, dict]]) -> list[int]:
        ids = []
        with self.tx() as c:
            for text, params in queries:
                cur = c.execute(
                    "INSERT INTO discovery_queries(run_id, provider, query_text, params_json, created_at) VALUES (?,?,?,?,?)",
                    (run_id, provider, text, json.dumps(params), now()))
                ids.append(cur.lastrowid)
            self.bump_run(c, run_id, queries_total=len(ids))
        return ids

    def update_query(self, qid: int, **fields) -> None:
        cols = ", ".join(f"{k}=?" for k in fields)
        with self.tx() as c:
            c.execute(f"UPDATE discovery_queries SET {cols} WHERE id=?", (*fields.values(), qid))

    def add_error(self, run_id: int, provider: str | None, query_id: int | None, message: str) -> None:
        with self.tx() as c:
            c.execute("INSERT INTO provider_errors(run_id, provider, query_id, message, created_at) VALUES (?,?,?,?,?)",
                      (run_id, provider, query_id, message[:1000], now()))
            self.bump_run(c, run_id, error_count=1)

    def list_queries(self, run_id, provider=None, status=None, limit=100, offset=0):
        sql, p = "SELECT * FROM discovery_queries WHERE run_id=?", [run_id]
        if provider:
            sql += " AND provider=?"; p.append(provider)
        if status:
            sql += " AND status=?"; p.append(status)
        return self._all(sql + " ORDER BY id LIMIT ? OFFSET ?", (*p, limit, offset))

    def list_errors(self, run_id, limit=100, offset=0):
        return self._all("SELECT * FROM provider_errors WHERE run_id=? ORDER BY id LIMIT ? OFFSET ?",
                         (run_id, limit, offset))

    # ---- dedup + ingest ---------------------------------------------------
    def _find_company(self, c, provider: str, n: NormalizedItem) -> tuple[int | None, str]:
        # 1) domain
        if n.domain:
            r = c.execute("SELECT id FROM companies WHERE domain=? LIMIT 1", (n.domain,)).fetchone()
            if r:
                return r["id"], "domain"
        # 2) source id (same provider + same id)
        if n.source_id:
            r = c.execute("SELECT company_id FROM company_sources WHERE provider=? AND source_id=?",
                          (provider, n.source_id)).fetchone()
            if r:
                return r["company_id"], "source_id"
        # 3) normalized name + location. Only merges when the location agrees; two records with
        #    conflicting domains are never merged.
        if n.name_norm:
            if n.city_norm:
                rows = c.execute("SELECT id, domain FROM companies WHERE name_norm=? AND city_norm=?",
                                 (n.name_norm, n.city_norm)).fetchall()
            else:
                rows = c.execute("SELECT id, domain FROM companies WHERE name_norm=? AND city_norm='' AND state_norm=?",
                                 (n.name_norm, n.state_norm)).fetchall()
            for r in rows:
                if r["domain"] and n.domain and r["domain"] != n.domain:
                    continue
                return r["id"], "name_location"
        return None, ""

    def ingest_item(self, run_id: int, query_id: int, provider: str, query_text: str, page: int,
                    n: NormalizedItem, raw: dict, confidence: str) -> dict:
        """Store one raw result and resolve it to a unique company. One transaction, all-or-nothing."""
        ts = now()
        with self.tx() as c:
            company_id, created, matched_by, in_run_new = None, False, "", False
            if n.resolvable:
                company_id, matched_by = self._find_company(c, provider, n)
                if company_id is None:
                    cur = c.execute(
                        """INSERT INTO companies(name,name_norm,domain,website,city,city_norm,state,state_norm,phone,
                           address,description,confidence,first_run_id,created_at,updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (n.name, n.name_norm, n.domain, n.website, n.city, n.city_norm, n.state, n.state_norm,
                         n.phone, n.address, n.description, confidence, run_id, ts, ts))
                    company_id, created, matched_by = cur.lastrowid, True, "new"
                else:                       # fill gaps only; never overwrite what we already know
                    c.execute(
                        """UPDATE companies SET
                           name=COALESCE(NULLIF(name,''),?), domain=COALESCE(NULLIF(domain,''),?),
                           website=COALESCE(NULLIF(website,''),?), city=COALESCE(NULLIF(city,''),?),
                           city_norm=COALESCE(NULLIF(city_norm,''),?), state=COALESCE(NULLIF(state,''),?),
                           state_norm=COALESCE(NULLIF(state_norm,''),?), phone=COALESCE(NULLIF(phone,''),?),
                           address=COALESCE(NULLIF(address,''),?), description=COALESCE(NULLIF(description,''),?),
                           confidence=CASE WHEN ?='high' THEN 'high' ELSE confidence END, updated_at=?
                           WHERE id=?""",
                        (n.name, n.domain, n.website, n.city, n.city_norm, n.state, n.state_norm, n.phone,
                         n.address, n.description, confidence, ts, company_id))
                if n.source_id:
                    c.execute("INSERT OR IGNORE INTO company_sources(company_id,provider,source_id,source_url,run_id,created_at) "
                              "VALUES (?,?,?,?,?,?)", (company_id, provider, n.source_id, n.source_url, run_id, ts))
                in_run_new = c.execute("INSERT OR IGNORE INTO run_companies(run_id, company_id) VALUES (?,?)",
                                       (run_id, company_id)).rowcount == 1
            is_dup = bool(company_id) and not in_run_new
            c.execute(
                """INSERT INTO raw_results(run_id,query_id,provider,query_text,page,source_id,source_url,name,website,
                   city,state,company_id,is_duplicate,matched_by,note,raw_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, query_id, provider, query_text, page, n.source_id, n.source_url, n.name, n.website,
                 n.city, n.state, company_id, int(is_dup), matched_by, n.note,
                 json.dumps(raw, default=str)[:20000], ts))
            self.bump_run(c, run_id, raw_count=1,
                          unique_count=1 if in_run_new else 0, new_count=1 if created else 0,
                          duplicate_count=1 if is_dup else 0, unresolved_count=0 if company_id else 1)
        return {"company_id": company_id, "created": created, "duplicate": is_dup, "matched_by": matched_by}

    # ---- reads ------------------------------------------------------------
    def list_companies(self, run_id=None, q=None, limit=100, offset=0) -> list[dict]:
        sql, p = "SELECT c.* FROM companies c", []
        cond = []
        if run_id is not None:
            sql += " JOIN run_companies rc ON rc.company_id=c.id"
            cond.append("rc.run_id=?"); p.append(run_id)
        if q:
            cond.append("(c.name LIKE ? OR c.domain LIKE ?)"); p += [f"%{q}%", f"%{q}%"]
        if cond:
            sql += " WHERE " + " AND ".join(cond)
        rows = self._all(sql + " ORDER BY c.id LIMIT ? OFFSET ?", (*p, limit, offset))
        for r in rows:
            r["sources"] = self._all("SELECT provider, source_id, source_url FROM company_sources WHERE company_id=?", (r["id"],))
        return rows

    def list_raw(self, run_id, provider=None, limit=100, offset=0) -> list[dict]:
        sql, p = "SELECT * FROM raw_results WHERE run_id=?", [run_id]
        if provider:
            sql += " AND provider=?"; p.append(provider)
        return self._all(sql + " ORDER BY id LIMIT ? OFFSET ?", (*p, limit, offset))

    def provider_breakdown(self, run_id: int) -> list[dict]:
        return self._all(
            """SELECT q.provider,
                 COUNT(*) AS queries,
                 SUM(q.status='done') AS done, SUM(q.status='partial') AS partial,
                 SUM(q.status='failed') AS failed, SUM(q.status='skipped') AS skipped,
                 COALESCE((SELECT COUNT(*) FROM raw_results r WHERE r.run_id=q.run_id AND r.provider=q.provider),0) AS raw_results,
                 COALESCE((SELECT COUNT(DISTINCT company_id) FROM raw_results r WHERE r.run_id=q.run_id AND r.provider=q.provider AND company_id IS NOT NULL),0) AS companies
               FROM discovery_queries q WHERE q.run_id=? GROUP BY q.provider""", (run_id,))

    def count_companies(self, run_id=None) -> int:
        if run_id is None:
            return self._one("SELECT COUNT(*) n FROM companies")["n"]
        return self._one("SELECT COUNT(*) n FROM run_companies WHERE run_id=?", (run_id,))["n"]

    # ---- website resolution helpers ---------------------------------------
    def find_unresolved_companies(self, run_id: int, limit: int = 500) -> list[dict]:
        """Return companies in this run that have a name but no domain yet."""
        return self._all(
            """SELECT c.id, c.name, c.city, c.state FROM companies c
               JOIN run_companies rc ON rc.company_id=c.id
               WHERE rc.run_id=? AND (c.domain IS NULL OR c.domain='')
               AND (c.name IS NOT NULL AND c.name!='')
               ORDER BY c.id LIMIT ?""",
            (run_id, limit))

    def update_company_domain(self, company_id: int, domain: str, website: str) -> bool:
        """Fill domain/website for a company that previously had none. Returns True if updated."""
        with self.tx() as c:
            cur = c.execute(
                """UPDATE companies SET domain=?, website=?, updated_at=?
                   WHERE id=? AND (domain IS NULL OR domain='')""",
                (domain, website, now(), company_id))
        return cur.rowcount > 0
