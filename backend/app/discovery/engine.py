"""Discovery orchestration: interpret ICP -> expand queries -> fan out to providers -> ingest -> track."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .classifier import MAX_VET_CALLS_PER_RUN, ollama_vet
from .config import DiscoverySettings
from .extractor import extract_from_snippet, extract_listing_page_full
from .http import AuthError, HttpClient
from .icp import IcpSpec, interpret_icp
from .normalize import (domain_matches_name, extract_domain, is_company_domain,
                         normalize, normalize_name)
from .providers.base import Provider, ProviderQuery
from .queries import expand
from .store import Store, now


class _Health:
    """Per-provider circuit breaker for one run: one provider dying never stops the others."""
    def __init__(self, threshold: int):
        self.threshold, self.fails, self.disabled_reason = threshold, 0, ""
        self.lock = threading.Lock()

    def ok(self):
        with self.lock:
            self.fails = 0

    def fail(self, fatal: bool, reason: str) -> bool:
        with self.lock:
            self.fails += 1
            if fatal or self.fails >= self.threshold:
                self.disabled_reason = self.disabled_reason or reason
            return bool(self.disabled_reason)

    @property
    def disabled(self) -> bool:
        return bool(self.disabled_reason)


class DiscoveryEngine:
    def __init__(self, store: Store, settings: DiscoverySettings, providers: list[Provider],
                 http: HttpClient | None = None,
                 interpreter: Callable[[str], tuple[IcpSpec, str | None]] | None = None,
                 vetter: Callable[[dict], bool | None] | None = None):
        self.store, self.s, self.providers = store, settings, providers
        self.http = http or HttpClient(settings.http_timeout, settings.http_retries)
        self._interpret = interpreter or (lambda text: interpret_icp(
            text, ollama_url=settings.ollama_url, model=settings.ollama_model, timeout=settings.ollama_timeout))
        self._cancelled: set[int] = set()
        self._vetter = vetter or self._ollama_vetter      # only used for genuinely uncertain candidates
        self._vet_state: dict[int, dict] = {}
        self._vet_lock = threading.Lock()

    # -- public ---------------------------------------------------------
    def create_run(self, icp_text: str, options: dict | None = None) -> int:
        return self.store.create_run(icp_text, options or {})

    def cancel(self, run_id: int) -> None:
        self._cancelled.add(run_id)

    def start_background(self, run_id: int) -> threading.Thread:
        t = threading.Thread(target=self.execute, args=(run_id,), daemon=True, name=f"discovery-{run_id}")
        t.start()
        return t

    def execute(self, run_id: int) -> None:
        import json
        run = self.store.get_run(run_id)
        opts = json.loads(run["options_json"] or "{}")
        self.store.update_run(run_id, status="running", started_at=now())
        self._vet_state[run_id] = {"on": bool(opts.get("use_ollama", True)), "calls": 0, "fails": 0,
                                   "cache": {}, "warned": False}
        try:
            # 1) ICP -> search vocabulary (Ollama only here)
            if opts.get("use_ollama", True):
                icp, err = self._interpret(run["icp_text"])
                if err:
                    self.store.add_error(run_id, "ollama", None, err)
            else:
                from .icp import fallback_interpret
                icp = fallback_interpret(run["icp_text"])
            self.store.update_run(run_id, icp_spec_json=json.dumps(icp.to_dict()))

            # 2) expand
            specs = expand(icp, extra_cities=opts.get("cities"), extra_states=opts.get("states"))
            target = opts.get("target_unique")
            default_limit = self.s.max_queries_per_provider
            if target and not opts.get("max_queries_per_provider"):
                default_limit = max(default_limit, int(target) * 3)
            limit = int(opts.get("max_queries_per_provider") or default_limit)
            max_pages = int(opts.get("max_pages") or self.s.max_pages)
            wanted = set(opts.get("providers") or [])
            active = [p for p in self.providers if p.enabled() and (not wanted or p.name in wanted)]
            if not active:
                raise RuntimeError("No discovery providers are enabled (check API keys / provider filter)")

            # 3) register every query up front so progress is visible
            plan: list[tuple[Provider, list[tuple[int, object]]]] = []
            for p in active:
                pqs = p.build_queries(specs, limit)
                ids = self.store.add_queries(run_id, p.name, [(q.text, q.params) for q in pqs])
                plan.append((p, list(zip(ids, pqs))))

            # 4) fan out: one pool per provider, so a slow/blocked provider never starves the rest
            pools, futures = [], []
            health = {p.name: _Health(self.s.provider_failure_threshold) for p, _ in plan}
            for p, tasks in plan:
                pool = ThreadPoolExecutor(max_workers=max(1, min(p.workers, self.s.workers_per_provider)),
                                          thread_name_prefix=f"disc-{p.name}")
                pools.append(pool)
                for qid, pq in tasks:
                    futures.append(pool.submit(self._run_query, run_id, p, qid, pq, max_pages, health[p.name], target))
            for f in futures:
                f.result()
            for pool in pools:
                pool.shutdown(wait=True)

            # 5) Adaptive queries: use non-company domains discovered in raw results
            #    to generate bonus site-scoped queries (e.g. site:tracxn.com saas startups Bangalore)
            if not self._should_stop(run_id, target):
                raw_rows = self.store.list_raw(run_id, limit=2000)
                discovered_domains: set[str] = set()
                for row in raw_rows:
                    for url_field in (row.get("source_url") or "", row.get("website") or ""):
                        d = extract_domain(url_field)
                        if d and not is_company_domain(d):
                            discovered_domains.add(d)
                self._adaptive_queries(run_id, icp, active, health, max_pages, target, discovered_domains)

            # 6) Website resolution pass: try to find domains for name-only candidates
            if not self._should_stop(run_id, target):
                search_providers = [p for p in active if getattr(p, "kind", "") == "search"
                                    and not health.get(p.name, _Health(1)).disabled]
                self._resolve_websites(run_id, search_providers, target)

            r = self.store.get_run(run_id)
            if run_id in self._cancelled:
                status = "cancelled"
            else:
                status = "completed_with_errors" if r["error_count"] else "completed"
            self.store.update_run(run_id, status=status, finished_at=now())
        except Exception as e:                    # only truly unexpected/global failures land here
            self.store.add_error(run_id, None, None, f"Run failed: {e}")
            self.store.update_run(run_id, status="failed", finished_at=now())
        finally:
            self._cancelled.discard(run_id)
            self._vet_state.pop(run_id, None)

    # -- internals ------------------------------------------------------
    def _ollama_vetter(self, cand: dict) -> bool | None:
        http = getattr(self, "_llm_http", None)
        if http is None:
            http = self._llm_http = HttpClient(self.s.ollama_timeout, 1)
        return ollama_vet(http, self.s.ollama_url, self.s.ollama_model, cand)

    def _vet(self, run_id: int, n, url: str = "", text: str = ""):
        """Resolve an 'uncertain' candidate. Rules already ran; Ollama is asked only here, once per
        candidate, capped per run. No answer (Ollama off/down/limit reached) = rejected, never guessed."""
        if n.verdict != "uncertain":
            return n
        st = self._vet_state.setdefault(run_id, {"on": True, "calls": 0, "fails": 0, "cache": {}, "warned": False})
        key = (n.name_norm, n.domain)
        with self._vet_lock:
            known = st["cache"].get(key)
            ask = known is None and st["on"] and st["calls"] < MAX_VET_CALLS_PER_RUN
            if ask:
                st["calls"] += 1
        if ask:
            try:
                ans = self._vetter({"name": n.name, "domain": n.domain, "url": url, "text": text})
            except Exception:
                ans = None
            with self._vet_lock:
                st["cache"][key] = known = bool(ans)
                st["fails"] = st["fails"] + 1 if ans is None else 0
                if st["fails"] >= 3:                 # Ollama is down: stop waiting on it for this run
                    st["on"] = False
                warn = ans is None and not st["warned"]
                st["warned"] = st["warned"] or warn
            if warn:
                self.store.add_error(run_id, "ollama", None,
                                     "Ollama could not vet uncertain candidates; they were rejected (kept in raw results)")
        if known:
            n.verdict, n.note = "ok", ""
        else:
            n.verdict, n.note = "reject", f"rejected: {n.reason} (not confirmed as a company)"
        return n

    def _should_stop(self, run_id: int, target) -> bool:
        if run_id in self._cancelled:
            return True
        if target:
            return self.store.get_run(run_id)["unique_count"] >= int(target)
        return False

    def _ingest_extracted(self, run_id: int, qid: int, provider_name: str,
                          query_text: str, page_num: int,
                          extracted_items, source_url: str, target) -> int:
        """Ingest a list of extracted sub-items; return count of new unique companies added."""
        added = 0
        for sub_item in extracted_items:
            sub_n = self._vet(run_id, normalize(sub_item), source_url,
                              f"{sub_item.title} {sub_item.description}")
            if sub_n.resolvable:
                self.store.ingest_item(
                    run_id, qid, provider_name, query_text, page_num,
                    sub_n, sub_item.raw or {"extracted_from": source_url, "name": sub_item.name},
                    confidence="high" if sub_n.domain else "medium",
                )
                added += 1
                if self._should_stop(run_id, target):
                    break
        return added

    def _run_query(self, run_id, provider: Provider, qid, pq, max_pages, health: _Health,
                   target, max_listing_pages: int = 3) -> None:
        store = self.store
        if health.disabled or self._should_stop(run_id, target):
            reason = health.disabled_reason or ("cancelled" if run_id in self._cancelled else "target reached")
            store.update_query(qid, status="skipped", error=reason, finished_at=now())
            return
        store.update_query(qid, status="running")
        pages = results = 0
        try:
            for page in provider.search(pq, max_pages, self.http):
                for item in page.items:
                    n = self._vet(run_id, normalize(item, trusted=provider.confidence == "high"),
                                  item.source_url or item.website, f"{item.title} {item.description}")
                    # 1. Ingest raw result
                    store.ingest_item(run_id, qid, provider.name, pq.text, page.number, n, item.raw, provider.confidence)
                    results += 1

                    # 2. Listing / directory page detected — extract + follow pagination
                    page_url = item.website or item.source_url or ""
                    url_domain = extract_domain(page_url)
                    if n.is_listing or not is_company_domain(url_domain):
                        visited_listing_urls: set[str] = set()
                        urls_to_process: list[str] = []
                        if page_url.startswith("http://") or page_url.startswith("https://"):
                            urls_to_process.append(page_url)

                        listing_page_idx = 0
                        while urls_to_process and listing_page_idx < max_listing_pages:
                            current_url = urls_to_process.pop(0)
                            if current_url in visited_listing_urls:
                                continue
                            visited_listing_urls.add(current_url)
                            listing_page_idx += 1

                            extracted_items, next_pages = [], []
                            try:
                                html = self.http.get_text(current_url)
                                if html:
                                    extracted_items, next_pages = extract_listing_page_full(
                                        current_url, html,
                                        location_hint=f"{pq.text} {item.title} {item.description}")
                            except Exception:
                                pass

                            if extracted_items:
                                store.bump(run_id, listing_count=1)
                                added = self._ingest_extracted(
                                    run_id, qid, provider.name, pq.text, page.number,
                                    extracted_items, current_url, target)
                                results += added
                                store.bump(run_id, extracted_count=added)
                                # Queue next-page URLs for pagination following
                                for np in next_pages:
                                    if np not in visited_listing_urls:
                                        urls_to_process.append(np)
                            else:
                                # No structured extraction — try snippet fallback
                                if item.title or item.description:
                                    snippet_items = extract_from_snippet(
                                        item.title, page_url, item.description,
                                        location_hint=f"{pq.text} {item.location_hint}")
                                    if snippet_items:
                                        added = self._ingest_extracted(
                                            run_id, qid, provider.name, pq.text, page.number,
                                            snippet_items, page_url, target)
                                        results += added

                            if self._should_stop(run_id, target):
                                break

                    if self._should_stop(run_id, target):
                        break

                pages += 1
                store.update_query(qid, pages_fetched=pages, results_count=results)
                if self._should_stop(run_id, target):
                    break

            store.update_query(qid, status="done", finished_at=now())
            store.bump(run_id, queries_done=1)
            health.ok()
        except Exception as e:
            fatal = isinstance(e, AuthError)
            msg = f"{type(e).__name__}: {e}"
            status = "partial" if pages else "failed"
            store.update_query(qid, status=status, error=msg[:500], finished_at=now())
            store.add_error(run_id, provider.name, qid, msg)
            store.bump(run_id, queries_failed=1)
            was_disabled = health.disabled
            health.fail(fatal, f"{provider.name} disabled for this run: {msg[:200]}")
            if health.disabled and not was_disabled:
                store.add_error(run_id, provider.name, None, health.disabled_reason)

    # -- website resolution pass ------------------------------------------
    def _resolve_websites(self, run_id: int, active_search_providers: list[Provider],
                          target) -> None:
        """For each name-only company in this run, try to find a domain via search."""
        if not active_search_providers:
            return
        candidates = self.store.find_unresolved_companies(run_id, limit=200)
        if not candidates:
            return
        provider = active_search_providers[0]   # use first available search provider
        for cand in candidates:
            if self._should_stop(run_id, target):
                break
            name = cand["name"]
            city = cand.get("city") or ""
            q_text = f'"{name}" {city} India official website'.strip()
            pq = ProviderQuery(q_text, {"term": name, "city": city})
            try:
                resolved = False
                for page in provider.search(pq, 1, self.http):
                    for item in page.items:
                        w = item.website or item.source_url or ""
                        d = extract_domain(w)
                        # Never trust a directory/aggregator as the official domain, and
                        # only attach a domain when there's real evidence it belongs to
                        # this company (name/host correspondence), not just the top hit.
                        if d and is_company_domain(d) and domain_matches_name(name, d):
                            updated = self.store.update_company_domain(
                                cand["id"], d, w if "://" in w else f"https://{w}")
                            if updated:
                                self.store.bump(run_id, resolved_count=1)
                            resolved = True
                            break
                    if resolved:
                        break
            except Exception:
                pass

    # -- adaptive query expansion -----------------------------------------
    def _adaptive_queries(self, run_id: int, icp: IcpSpec, active: list[Provider],
                          existing_health: dict, max_pages: int, target,
                          discovered_domains: set[str]) -> None:
        """Generate bonus site-scoped queries from directories discovered during the run."""
        if not target or self._should_stop(run_id, target):
            return
        # Only use search providers for adaptive queries
        search_providers = [p for p in active if getattr(p, "kind", "") == "search" and not existing_health[p.name].disabled]
        if not search_providers:
            return

        from .normalize import NON_COMPANY_DOMAINS
        bonus_sites = [d for d in discovered_domains if not is_company_domain(d) and d not in (
            "google.com", "google.co.in", "bing.com", "duckduckgo.com", "yahoo.com")]
        if not bonus_sites:
            return

        bonus_specs = expand(icp, cap=50)
        for site in bonus_sites[:5]:
            for provider in search_providers[:1]:
                q_texts: list[tuple[str, dict]] = []
                for spec in bonus_specs[:10]:
                    q = f"site:{site} {spec.term} {spec.ctype} {spec.location}".replace("  ", " ").strip()
                    q_texts.append((q, {"term": spec.term, "city": spec.city, "site": site}))
                if not q_texts:
                    continue
                bonus_ids = self.store.add_queries(run_id, provider.name, q_texts)
                health = existing_health[provider.name]
                for qid, (q_text, params) in zip(bonus_ids, q_texts):
                    if self._should_stop(run_id, target):
                        break
                    pq = ProviderQuery(q_text, params)
                    self._run_query(run_id, provider, qid, pq, max_pages, health, target)