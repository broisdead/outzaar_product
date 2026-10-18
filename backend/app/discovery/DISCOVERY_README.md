# OUTZAAR Discovery Engine (phase 1: company discovery only)

Given an ICP, discover as many raw Indian companies as possible. No decision makers, emails,
outreach or enrichment.

## Install
Copy `backend/app/discovery/` and `backend/tests/test_discovery.py` into your repo and replace `main.py`
(three small additions: import `init_discovery` + `discovery_router`, call `init_discovery()` in `startup`,
`app.include_router(discovery_router, prefix="/api")`). Python 3.10+. New dependencies: only
`beautifulsoup4` + `lxml` (DuckDuckGo / directory scrapers). Everything else is stdlib + FastAPI.

    pip install beautifulsoup4 lxml
    python -m unittest backend.tests.test_discovery     # 40 tests, no network needed

Copy `.env.example.discovery` into your `.env` and fill in keys.

## Flow
1. **ICP -> vocabulary** (`icp.py`): Ollama returns industries, sub-industries, synonyms, keywords, company types,
   cities/states. Ollama never returns companies and never invents unrelated terms. If it is down or returns junk,
   a rule-based fallback runs and the failure is logged as a run error (the run continues). Locations typed in the
   ICP are always kept.
2. **Expansion** (`queries.py`): term x company type x location. No location in the ICP = India-wide, all states and
   ~50 industrial hubs. A state also expands to its cities. India-wide queries go first, the rest are seeded-shuffled
   so any cap keeps variety. Cap per provider: `max_queries_per_provider` (default 200).
3. **Providers** (`providers/`), each isolated, paginated, throttled, retried with backoff:

   | Provider | Kind | Enabled by |
   |---|---|---|
   | `serpapi_google`, `google_cse`, `brave_search`, `duckduckgo_html` | search engines, ~35% of queries are site-scoped (IndiaMART, TradeIndia, ExportersIndia, JustDial, FIEO, CII, FICCI, EEPC) | key (DDG on by default) |
   | `serpapi_maps` | Google Maps business listings (name, website, phone, address) | `SERPAPI_API_KEY` |
   | `apollo` | B2B company database | `APOLLO_API_KEY` |
   | `dir_<name>` | config-driven directory / list-page scraper | `directories.json` |

4. **Directory / Listicle Extraction & Pagination** (`extractor.py`):
   Listing, directory, and article pages (e.g. F6S, Wellfound, GetLatka, BestStartup, listicles) are recognized
   and extracted into individual company records using JSON-LD, card containers, listicle headings, outbound company
   links, and snippet fallbacks. Pagination links (Next page, page 2, 3...) are discovered and followed up to
   `max_listing_pages` deep.
5. **Adaptive Query Expansion & Website Resolution Pass** (`engine.py`):
   - **Adaptive Queries**: Non-company directory domains found during search are fed back to generate targeted
     `site:<domain>` queries to discover deeper company listings.
   - **Website Resolution Pass**: Name-only candidate companies without a verified website are resolved via targeted
     search queries (`"<name>" <city> India official website`) to discover and bind their official domain.
6. **Raw first, then normalize + dedup** (`normalize.py`, `store.py`): Every provider result is stored in
   `raw_results` (provider, query, page, source id/url, full payload), then resolved to a company.
   Dedup order: **domain -> (provider, source id) -> normalized name + city** (name + state if city unknown).
   Safety: aggregator/social/directory domains never count as a company domain; records with conflicting domains are
   never merged; same name in a different city stays separate; merges only fill blanks. Missing fields never reject a
   record: a name *or* a domain is enough. Directory/article pages are recorded as sources and extracted (`listing_count`, `extracted_count`).
7. **Resilience**: per-provider thread pools; a 401/403 switches that provider off for the run;
   `provider_failure_threshold` (8) consecutive failures does the same; partial pages are kept. Run ends
   `completed`, `completed_with_errors`, `cancelled`, or `failed` (only if nothing could run at all).

## Tracking (SQLite at `DISCOVERY_DB_PATH`)
`discovery_runs` (raw / unique / new / duplicate / unresolved / error counters), `discovery_queries` (status, pages,
results, error), `raw_results`, `companies`, `company_sources`, `run_companies`, `provider_errors`.
`unique_count` = distinct companies seen in the run; `new_count` = of those, never seen in any earlier run.

## API (all under `/api`)
    POST /discovery/runs                 {icp_text, providers?, cities?, states?, max_queries_per_provider?, max_pages?, target_unique?, use_ollama?}
    GET  /discovery/runs, /discovery/runs/{id}          stats, progress, per-provider breakdown
    GET  /discovery/runs/{id}/companies | companies.csv | raw-results | queries | errors     (limit, offset)
    POST /discovery/runs/{id}/cancel
    GET  /discovery/providers
    POST /icp/analyze                    -> IcpProfile for the "OUTZAAR understands" panel
    POST /prospects/search               -> Prospect[]; waits `wait_seconds` (20), returns what's found so far; the run
                                            continues in the background (header X-Discovery-Run-Id)

## Frontend hookup (`src/services/api.ts` only)
`analyzeIcp(text)` -> `POST /icp/analyze {text}`. `getProspects(icp)` -> `POST /prospects/search {icp_text}`.
Fields the frontend expects but discovery doesn't produce yet (`fitScore`, `signals`, `painPoints`, `decisionMakers`,
`fitReasoning`, `outreachAngle`, `potentialNeed`) are empty placeholders. The Prospect/Company mapping in
`adapters.py` was written from the README, not from `src/types/index.ts`: adjust it there if field names differ.
Check `vite.config.ts`: if the proxy strips `/api`, either drop the `/api` prefix on the discovery router or
remove the rewrite (your existing routes are mounted at `/api/...`).

## Known limits
- **Nothing has been run against a live provider** (no network where this was built). Request/response shapes for
  SerpAPI, Google CSE, Brave and Apollo follow their documented formats and are unit-tested against canned payloads.
  Verify each with one small run (`max_queries_per_provider: 2`) and read `/runs/{id}/errors`.
  Apollo needs a plan with API access.
- Directory scrapers ship with no site-specific selectors on purpose. Fill `directories.json` (see `.example`) after
  inspecting the target pages and checking each site's terms; robots.txt is honoured by default. Meanwhile
  IndiaMART/TradeIndia/JustDial/association pages are still reached through site-scoped search queries.
- Search-engine results are `low` confidence (name comes from the page title); structured sources are `high`.
- SQLite + one process handled ~4k inserts/s in a 30k-result test. Move to Postgres/Celery when you scale out;
  `store.py` is the only file that touches SQL.
- Runs are in-process threads: a server restart abandons a running run (data stays, status stays `running`).
