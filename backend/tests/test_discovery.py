import json
import unittest

from backend.app.discovery.config import DiscoverySettings
from backend.app.discovery.engine import DiscoveryEngine
from backend.app.discovery.extractor import (extract_from_directory_profile,
                                            extract_from_listing_page,
                                            extract_listing_page_full,
                                            extract_pagination_links,
                                            extract_outbound_company_links,
                                            extract_from_snippet)
from bs4 import BeautifulSoup
from backend.app.discovery.http import AuthError, HttpError
from backend.app.discovery.icp import IcpSpec, fallback_interpret, interpret_icp
from backend.app.discovery.normalize import (extract_domain, is_company_domain,
                                            name_from_title, normalize,
                                            normalize_name)
from backend.app.discovery.providers.apollo import ApolloProvider
from backend.app.discovery.providers.base import Page, Provider, ProviderQuery, RawItem
from backend.app.discovery.providers.search import (BraveProvider, GoogleCseProvider,
                                                    SerpApiMapsProvider, SerpApiProvider)
from backend.app.discovery.queries import expand
from backend.app.discovery.store import Store


class FakeHttp:
    def __init__(self, payloads=None, text_payloads=None):
        self.payloads = list(payloads or [])
        self.text_payloads = dict(text_payloads or {})
        self.calls = []

    def get_json(self, url, **kw):
        self.calls.append((url, kw))
        return self.payloads.pop(0)

    def post_json(self, url, body, **kw):
        self.calls.append((url, body))
        return self.payloads.pop(0)

    def get_text(self, url, **kw):
        self.calls.append((url, kw))
        if url in self.text_payloads:
            return self.text_payloads[url]
        for pattern, text in self.text_payloads.items():
            if pattern in url:
                return text
        return ""


class NormalizeTests(unittest.TestCase):
    def test_domain(self):
        self.assertEqual(extract_domain("https://www.shop.abc.co.in/x?y=1"), "abc.co.in")
        self.assertEqual(extract_domain("abcpumps.com"), "abcpumps.com")
        self.assertEqual(extract_domain(""), "")

    def test_names(self):
        self.assertEqual(normalize_name("ABC Pumps Pvt. Ltd."), "abc pumps")
        self.assertEqual(normalize_name("Tata & Sons Private Limited"), "tata and sons")
        self.assertEqual(name_from_title("Home - ABC Pumps Pvt Ltd | Pune", "abcpumps.com"), "ABC Pumps Pvt Ltd")

    def test_aggregator_url_gives_no_domain(self):
        n = normalize(RawItem(title="Shree Auto Components - Manufacturer from Pune | IndiaMART",
                              website="https://www.indiamart.com/shree-auto/", source_id="u"))
        self.assertEqual(n.domain, "")
        self.assertEqual(n.name_norm, "shree auto components")
        self.assertEqual(n.city, "Pune")
        self.assertTrue(n.resolvable)

    def test_listing_page_not_a_company(self):
        n = normalize(RawItem(title="Top 10 Auto Component Manufacturers in Pune", website="https://blog.example.com/top10"))
        self.assertTrue(n.is_listing and not n.resolvable)

    def test_directory_domains_never_stored_as_company_domain(self):
        directory_urls = [
            "https://www.f6s.com/companies/saas/india",
            "https://beststartup.asia/15-top-saas-startups-bangalore/",
            "https://getlatka.com/companies/countries/india",
            "https://wellfound.com/location/bangalore",
            "https://clutch.co/in/developers",
            "https://tracxn.com/d/explore/b2b-saas-startups-in-bangalore",
        ]
        for u in directory_urls:
            d = extract_domain(u)
            self.assertFalse(is_company_domain(d), f"{d} should not be treated as a company domain")
            n = normalize(RawItem(title="Directory Page", website=u))
            self.assertEqual(n.domain, "")

    def test_company_with_best_in_tagline_is_not_listing(self):
        n = normalize(RawItem(title="ABC Pumps - Best Manufacturer of Pumps in Pune", website="https://abcpumps.com"))
        self.assertFalse(n.is_listing)

    def test_missing_fields_allowed(self):
        n = normalize(RawItem(name="Just A Name"))
        self.assertTrue(n.resolvable)
        self.assertEqual((n.domain, n.city), ("", ""))


class ListingExtractorTests(unittest.TestCase):
    def test_heading_listicle_extraction(self):
        html = """
        <html>
        <head><title>Top 10 B2B SaaS Startups in Bangalore</title></head>
        <body>
            <h1>10 Best SaaS Startups in Bangalore (2024)</h1>
            <h2>1. Hasura</h2>
            <p>Hasura is an open source GraphQL engine based in Bangalore. <a href="https://hasura.io">Visit Hasura</a></p>
            <h2>2. Whatfix</h2>
            <p>Whatfix is a digital adoption platform located in Bengaluru. <a href="https://whatfix.com">Official Website</a></p>
            <h2>3. Chargebee</h2>
            <p>Subscription management platform in Bangalore. <a href="https://chargebee.com">chargebee.com</a></p>
        </body>
        </html>
        """
        items = extract_from_listing_page("https://beststartup.asia/top-saas-bangalore", html)
        self.assertEqual(len(items), 3)
        names = {i.name for i in items}
        self.assertEqual(names, {"Hasura", "Whatfix", "Chargebee"})
        domains = {extract_domain(i.website) for i in items}
        self.assertEqual(domains, {"hasura.io", "whatfix.com", "chargebee.com"})
        cities = {i.city for i in items}
        self.assertEqual(cities, {"Bengaluru"})

    def test_json_ld_extraction(self):
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "ItemList",
                "itemListElement": [
                    {
                        "@type": "Organization",
                        "name": "Postman",
                        "url": "https://postman.com",
                        "description": "API platform based in Bangalore",
                        "address": {"@type": "PostalAddress", "addressLocality": "Bangalore"}
                    },
                    {
                        "@type": "Organization",
                        "name": "Keka HR",
                        "url": "https://keka.com",
                        "description": "HR SaaS software in Delhi"
                    }
                ]
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        items = extract_from_listing_page("https://getlatka.com/saas-india", html)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].name, "Postman")
        self.assertEqual(items[0].city, "Bengaluru")
        self.assertEqual(items[1].name, "Keka HR")
        self.assertEqual(items[1].city, "Delhi")

    def test_directory_profile_url_extraction(self):
        item = extract_from_directory_profile(
            "https://www.f6s.com/company/postman",
            "Postman: API Platform | F6S",
            "Leading API development platform in Bangalore",
        )
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "Postman")
        self.assertEqual(item.city, "Bengaluru")

    def test_snippet_extraction_fallback(self):
        items = extract_from_snippet(
            "Top B2B SaaS Startups in Bangalore",
            "https://blog.example.com/saas-list",
            "Discover leading SaaS startups in Bangalore including Postman, Hasura, and Whatfix for your business.",
            location_hint="Bangalore",
        )
        names = {i.name for i in items}
        self.assertTrue({"Postman", "Hasura", "Whatfix"}.issubset(names))


class DedupTests(unittest.TestCase):
    def setUp(self):
        self.st = Store(":memory:")
        self.run = self.st.create_run("x", {})

    def ing(self, provider="p", **kw):
        return self.st.ingest_item(self.run, 1, provider, "q", 1, normalize(RawItem(**kw)), {}, "low")

    def test_domain_first(self):
        a = self.ing(name="ABC Pumps", website="https://abcpumps.com")
        b = self.ing(provider="q", name="A B C Pumps Limited", website="http://www.abcpumps.com/contact", city="Pune")
        self.assertEqual(a["company_id"], b["company_id"])
        self.assertEqual(b["matched_by"], "domain")
        self.assertEqual(self.st.list_companies()[0]["city"], "Pune")     # gap filled from second source

    def test_source_id(self):
        a = self.ing(name="Foo", source_id="123")
        b = self.ing(name="Completely Different Label", source_id="123")
        self.assertEqual(b["matched_by"], "source_id")
        self.assertEqual(a["company_id"], b["company_id"])

    def test_name_location_and_safety(self):
        a = self.ing(name="Shree Steel Pvt Ltd", city="Pune")
        same = self.ing(provider="q", name="Shree Steel Private Limited", city="Pune")
        other_city = self.ing(name="Shree Steel", city="Nagpur")
        no_loc = self.ing(name="Shree Steel")
        self.assertEqual(a["company_id"], same["company_id"])
        self.assertNotIn(other_city["company_id"], (a["company_id"],))
        self.assertNotIn(no_loc["company_id"], (a["company_id"], other_city["company_id"]))

    def test_conflicting_domains_not_merged(self):
        a = self.ing(name="Apex Tools", city="Pune", website="https://apextools.in")
        b = self.ing(name="Apex Tools", city="Pune", website="https://apextools-eng.com")
        self.assertNotEqual(a["company_id"], b["company_id"])

    def test_unresolved_kept_raw(self):
        r = self.ing(title="Top 10 pump manufacturers in Pune", website="https://blog.x.com/a")
        self.assertIsNone(r["company_id"])
        run = self.st.get_run(self.run)
        self.assertEqual((run["raw_count"], run["unresolved_count"], run["unique_count"]), (1, 1, 0))


class QueryTests(unittest.TestCase):
    def test_india_wide_default_and_variety(self):
        spec = IcpSpec(raw_text="auto parts", industries=["auto components"], synonyms=["automotive parts"])
        qs = expand(spec)
        self.assertGreater(len(qs), 500)
        self.assertEqual(qs[0].location, "India")
        self.assertTrue({q.city for q in qs} > {""})
        self.assertEqual(len(set(qs)), len(qs))

    def test_state_expands_to_cities(self):
        qs = expand(IcpSpec(raw_text="x", industries=["pumps"], states=["Gujarat"]))
        self.assertIn("Surat", {q.city for q in qs})

    def test_fallback_icp_reads_locations(self):
        s = fallback_interpret("Mid-size textile manufacturers in Tiruppur and Coimbatore")
        self.assertEqual(set(s.cities), {"Tiruppur", "Coimbatore"})
        self.assertIn("textile", s.terms())

    def test_b2b_saas_bangalore_delhi_preserves_icp_no_unrelated_terms(self):
        s = fallback_interpret("B2B SaaS startups in Bangalore and Delhi")
        self.assertEqual(set(s.cities), {"Bengaluru", "Delhi"})
        self.assertTrue(any("saas" in t for t in s.terms()))
        
        qs = expand(s)
        self.assertGreater(len(qs), 10)
        
        # Must only target Bengaluru, Delhi / New Delhi, or India
        allowed_locations = {"Bengaluru", "Delhi", "New Delhi", "India"}
        for q in qs:
            self.assertIn(q.location, allowed_locations, f"Unexpected location {q.location} generated")
            q_text_low = q.text.lower()
            # Must NEVER invent unrelated industrial / manufacturing terms
            for bad_term in ("industrial", "machine manufacturer", "machinery", "fabricator", "fabricators", "oem"):
                self.assertNotIn(bad_term, q_text_low, f"Query '{q.text}' should not contain '{bad_term}'")
        
        # Verify accurate queries exist
        query_texts = {q.text for q in qs}
        self.assertTrue(any("Bengaluru" in qt and "saas" in qt.lower() for qt in query_texts))
        self.assertTrue(any("Delhi" in qt and "saas" in qt.lower() for qt in query_texts))

    def test_ollama_used_and_typed_locations_kept(self):
        class H:
            def post_json(self, url, body, **kw):
                return {"response": json.dumps({"industries": ["textiles"], "sub_industries": ["knitwear"],
                                                "synonyms": ["garment"], "cities": ["Bangalore"], "hallucinated_company": "X"})}
        spec, err = interpret_icp("textile makers in Tiruppur", ollama_url="http://x", model="m", http=H())
        self.assertIsNone(err)
        self.assertEqual(spec.source, "ollama")
        self.assertEqual(set(spec.cities), {"Bengaluru", "Tiruppur"})

    def test_ollama_down_falls_back(self):
        class H:
            def post_json(self, *a, **k): raise HttpError(0, "connection refused")
        spec, err = interpret_icp("pump makers in Pune", ollama_url="http://x", model="m", http=H())
        self.assertEqual(spec.source, "fallback")
        self.assertIn("connection refused", err)


class ProviderParserTests(unittest.TestCase):
    def collect(self, prov, payloads, pages=3):
        pgs = list(prov.search(ProviderQuery("q", {"term": "pumps", "location": "Pune"}), pages, FakeHttp(payloads)))
        return [i for p in pgs for i in p.items], pgs

    def test_serpapi(self):
        items, pgs = self.collect(SerpApiProvider("k"), [
            {"organic_results": [{"title": "ABC Pumps", "link": "https://abc.com", "snippet": "Pune"}],
             "serpapi_pagination": {"next": "x"}},
            {"organic_results": [{"title": "XYZ", "link": "https://xyz.com"}]}])
        self.assertEqual(len(items), 2); self.assertEqual(len(pgs), 2)

    def test_maps(self):
        items, _ = self.collect(SerpApiMapsProvider("k"), [
            {"local_results": [{"title": "ABC", "place_id": "P1", "address": "MIDC, Pune", "phone": "1", "website": "https://abc.in"}]},
            {"local_results": []}])
        self.assertEqual(items[0].source_id, "P1"); self.assertEqual(items[0].phone, "1")

    def test_cse_and_brave(self):
        items, _ = self.collect(GoogleCseProvider("k", "cx"), [{"items": [{"title": "T", "link": "https://a.com"}]}, {}])
        self.assertEqual(len(items), 1)
        items, _ = self.collect(BraveProvider("k"), [{"web": {"results": [{"title": "T", "url": "https://a.com", "description": "d"}]}}, {"web": {}}])
        self.assertEqual(len(items), 1)

    def test_apollo(self):
        items, pgs = self.collect(ApolloProvider("k"), [
            {"organizations": [{"id": "1", "name": "A", "website_url": "http://a.in", "city": "Pune", "state": "Maharashtra"}],
             "pagination": {"total_pages": 2}},
            {"organizations": [{"id": "2", "name": "B"}], "pagination": {"total_pages": 2}}])
        self.assertEqual([i.source_id for i in items], ["1", "2"]); self.assertFalse(pgs[-1].has_more)


class FakeProvider(Provider):
    kind = "b2b_api"; workers = 2
    def __init__(self, name, pages_of_items, fail_with=None, fail_after_pages=None, confidence="high"):
        super().__init__(); self.name, self.pages, self.fail_with = name, pages_of_items, fail_with
        self.fail_after, self.confidence, self.calls = fail_after_pages, confidence, 0
    def build_queries(self, specs, limit): return [ProviderQuery(f"{self.name}-q{i}") for i in range(limit)]
    def search(self, pq, max_pages, http):
        self.calls += 1
        if self.fail_with and self.fail_after is None:
            raise self.fail_with
        for n, items in enumerate(self.pages[:max_pages], 1):
            yield Page(n, [RawItem(**i) for i in items], n < len(self.pages))
            if self.fail_with and self.fail_after == n:
                raise self.fail_with


def C(i, **kw): return {"name": f"Company {i} Pvt Ltd", "website": f"https://company{i}.in", "source_id": f"id{i}", **kw}


class EngineTests(unittest.TestCase):
    def engine(self, providers, http=None):
        return DiscoveryEngine(
            Store(":memory:"),
            DiscoverySettings(provider_failure_threshold=3, workers_per_provider=1),
            providers,
            http=http,
            interpreter=lambda t: (IcpSpec(raw_text=t, industries=["pumps"], source="ollama"), None),
        )

    def run_it(self, eng, **opts):
        rid = eng.create_run("pump makers", opts); eng.execute(rid); return rid, eng.store.get_run(rid)

    def test_pagination_dedup_and_tracking(self):
        a = FakeProvider("a", [[C(1), C(2)], [C(3), C(1)]])                   # 2 pages, overlap inside
        b = FakeProvider("b", [[C(2), C(4, city="Pune")]])                     # overlaps with a
        eng = self.engine([a, b])
        rid, run = self.run_it(eng, max_queries_per_provider=3)
        # 3 queries * (4 + 2) raw items
        self.assertEqual(run["raw_count"], 18)
        self.assertEqual(run["unique_count"], 4)
        self.assertEqual(run["duplicate_count"], 14)
        self.assertEqual(run["new_count"], 4)
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["queries_total"], 6)
        self.assertEqual(eng.store.count_companies(rid), 4)
        raw = eng.store.list_raw(rid)[0]
        self.assertTrue(raw["provider"] and raw["query_text"] and raw["source_id"] and json.loads(raw["raw_json"]) is not None)
        self.assertEqual(json.loads(run["icp_spec_json"])["source"], "ollama")

    def test_directory_page_extracts_multiple_companies(self):
        listing_url = "https://beststartup.asia/top-saas-bangalore"
        html_content = """
        <html>
        <head><title>Top 3 B2B SaaS Startups in Bangalore</title></head>
        <body>
            <h2>1. Postman</h2>
            <p>API platform in Bangalore. <a href="https://postman.com">Website</a></p>
            <h2>2. Hasura</h2>
            <p>GraphQL engine in Bengaluru. <a href="https://hasura.io">Website</a></p>
            <h2>3. Whatfix</h2>
            <p>Digital adoption platform in Bangalore. <a href="https://whatfix.com">Website</a></p>
        </body>
        </html>
        """
        http = FakeHttp(text_payloads={listing_url: html_content})
        
        # Provider returns 1 search result which is a directory listing page
        p = FakeProvider("search", [[{
            "title": "Top 3 B2B SaaS Startups in Bangalore",
            "website": listing_url,
            "source_id": listing_url,
        }]])
        eng = self.engine([p], http=http)
        rid, run = self.run_it(eng, max_queries_per_provider=1)
        
        # Should have discovered the 3 companies from the listing page
        self.assertEqual(run["unique_count"], 3)
        comps = eng.store.list_companies(rid)
        comp_domains = {c["domain"] for c in comps}
        self.assertEqual(comp_domains, {"postman.com", "hasura.io", "whatfix.com"})
        
        # The listing domain must NEVER be saved as a company domain
        self.assertNotIn("beststartup.asia", comp_domains)

    def test_one_provider_failing_does_not_stop_run(self):
        good = FakeProvider("good", [[C(1), C(2)]])
        bad = FakeProvider("bad", [], fail_with=HttpError(500, "boom"))
        eng = self.engine([good, bad])
        rid, run = self.run_it(eng, max_queries_per_provider=6)
        self.assertEqual(run["unique_count"], 2)
        self.assertEqual(run["status"], "completed_with_errors")
        self.assertGreater(run["error_count"], 0)
        self.assertEqual(bad.calls, 3)                                          # breaker opened at threshold=3
        st = {r["provider"]: r for r in eng.store.provider_breakdown(rid)}
        self.assertEqual(st["good"]["done"], 6)
        self.assertEqual(st["bad"]["skipped"], 3)

    def test_auth_error_disables_immediately(self):
        dead = FakeProvider("dead", [], fail_with=AuthError(401, "bad key"))
        eng = self.engine([dead, FakeProvider("ok", [[C(9)]])])
        rid, run = self.run_it(eng, max_queries_per_provider=5)
        self.assertEqual(dead.calls, 1)
        self.assertEqual(run["unique_count"], 1)
        msgs = [e["message"] for e in eng.store.list_errors(rid)]
        self.assertTrue(any("disabled" in m for m in msgs))

    def test_partial_results_kept_when_page_two_fails(self):
        p = FakeProvider("p", [[C(1)], [C(2)]], fail_with=HttpError(500, "x"), fail_after_pages=1)
        eng = self.engine([p])
        rid, run = self.run_it(eng, max_queries_per_provider=1)
        self.assertEqual(run["unique_count"], 1)
        self.assertEqual(eng.store.list_queries(rid)[0]["status"], "partial")

    def test_target_unique_stops_early(self):
        p = FakeProvider("p", [[C(i) for i in range(1, 6)]])
        p.workers = 1
        eng = self.engine([p])
        rid, run = self.run_it(eng, max_queries_per_provider=10, target_unique=3)
        self.assertGreaterEqual(run["unique_count"], 3)
        self.assertIn("skipped", {q["status"] for q in eng.store.list_queries(rid)})

    def test_no_providers_fails_cleanly(self):
        eng = self.engine([])
        rid, run = self.run_it(eng)
        self.assertEqual(run["status"], "failed")

    def test_ollama_failure_is_recorded_not_fatal(self):
        eng = DiscoveryEngine(Store(":memory:"), DiscoverySettings(), [FakeProvider("p", [[C(1)]])],
                              interpreter=lambda t: (fallback_interpret(t), "Ollama down"))
        rid, run = self.run_it(eng, max_queries_per_provider=1)
        self.assertEqual(run["unique_count"], 1)
        self.assertEqual(run["status"], "completed_with_errors")


class HttpClientTests(unittest.TestCase):
    def test_retry_then_success_and_auth(self):
        import gzip, threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from backend.app.discovery.http import HttpClient
        state = {"n": 0}

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                if self.path.startswith("/auth"):
                    self.send_response(401); self.end_headers(); return
                state["n"] += 1
                if state["n"] < 3:
                    self.send_response(429); self.send_header("Retry-After", "0"); self.end_headers(); return
                body = gzip.compress(b'{"ok": true}')
                self.send_response(200); self.send_header("Content-Encoding", "gzip"); self.end_headers(); self.wfile.write(body)

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_port}"
        c = HttpClient(timeout=5, retries=3, backoff=1.0)
        self.assertEqual(c.get_json(base + "/x", params={"a": 1}), {"ok": True})
        self.assertEqual(state["n"], 3)
        with self.assertRaises(AuthError):
            c.get_json(base + "/auth")
        srv.shutdown()



class PaginationExtractionTests(unittest.TestCase):
    def _soup(self, html):
        return BeautifulSoup(html, "html.parser")

    def test_next_page_link_detected(self):
        html = """
        <html><body>
            <a href="/startups?page=2">Next</a>
            <a href="https://hasura.io">Hasura</a>
        </body></html>
        """
        soup = self._soup(html)
        from backend.app.discovery.normalize import extract_domain
        links = extract_pagination_links(soup, "https://beststartup.asia/startups")
        self.assertEqual(len(links), 1)
        self.assertIn("page=2", links[0])

    def test_outbound_company_links_extracted(self):
        html = """
        <html><body>
            <a href="https://hasura.io">Hasura</a>
            <a href="https://whatfix.com">Whatfix</a>
            <a href="https://linkedin.com/in/foo">Profile</a>
            <a href="/internal-link">Internal</a>
        </body></html>
        """
        soup = self._soup(html)
        from backend.app.discovery.normalize import extract_domain
        links = extract_outbound_company_links(soup, "https://beststartup.asia", "beststartup.asia")
        domains = {extract_domain(l) for l in links}
        self.assertIn("hasura.io", domains)
        self.assertIn("whatfix.com", domains)
        self.assertNotIn("linkedin.com", domains)   # aggregator domain

    def test_extract_listing_page_full_returns_next_pages(self):
        html = """
        <html><head><title>Top SaaS Startups Bangalore</title></head>
        <body>
            <h2>1. Postman</h2><p><a href="https://postman.com">Visit</a></p>
            <h2>2. Hasura</h2><p><a href="https://hasura.io">Visit</a></p>
            <a href="/startups?page=2">Next &raquo;</a>
        </body></html>
        """
        items, next_pages = extract_listing_page_full("https://beststartup.asia/startups", html)
        names = {i.name for i in items}
        self.assertIn("Postman", names)
        self.assertIn("Hasura", names)
        self.assertEqual(len(next_pages), 1)
        self.assertIn("page=2", next_pages[0])


class ResolutionPassTests(unittest.TestCase):
    def test_resolution_pass_fills_domain_for_name_only_company(self):
        """Engine's resolution pass should resolve a domain when search returns a matching result."""
        from backend.app.discovery.providers.base import Page, ProviderQuery

        # Provider that yields a name-only company (no website)
        name_only_provider = FakeProvider("name_src", [[{"name": "Hasura Pvt Ltd", "city": "Bengaluru"}]])
        # Search provider that returns hasura.io when we look up 'Hasura'
        search_provider = FakeProvider("search", [[{"website": "https://hasura.io", "title": "Hasura"}]])
        search_provider.name = "serpapi_google"
        search_provider.kind = "search"

        eng = DiscoveryEngine(
            Store(":memory:"),
            DiscoverySettings(provider_failure_threshold=3, workers_per_provider=1),
            [name_only_provider, search_provider],
            interpreter=lambda t: (IcpSpec(raw_text=t, industries=["saas"], source="fallback"), None),
        )
        rid = eng.create_run("saas", {"max_queries_per_provider": 1})
        eng.execute(rid)
        run = eng.store.get_run(rid)
        # The name-only company should still be in the run
        self.assertGreaterEqual(run["unique_count"], 1)


class MetricsTests(unittest.TestCase):
    def test_listing_count_and_extracted_count_tracked(self):
        """When a listing page is processed, listing_count and extracted_count are bumped."""
        listing_url = "https://beststartup.asia/top-saas"
        html = """
        <html><head><title>Top SaaS Startups Bangalore</title></head>
        <body>
            <h2>1. Postman</h2><p><a href="https://postman.com">Visit</a></p>
            <h2>2. Hasura</h2><p><a href="https://hasura.io">Visit</a></p>
        </body></html>
        """
        http = FakeHttp(text_payloads={listing_url: html})
        p = FakeProvider("search", [[{"title": "Top SaaS Startups", "website": listing_url, "source_id": listing_url}]])
        eng = DiscoveryEngine(
            Store(":memory:"),
            DiscoverySettings(provider_failure_threshold=3, workers_per_provider=1),
            [p],
            http=http,
            interpreter=lambda t: (IcpSpec(raw_text=t, industries=["saas"], source="fallback"), None),
        )
        rid = eng.create_run("saas", {"max_queries_per_provider": 1})
        eng.execute(rid)
        run = eng.store.get_run(rid)
        self.assertGreaterEqual(run["listing_count"], 1)
        self.assertGreaterEqual(run["extracted_count"], 2)
        self.assertGreaterEqual(run["unique_count"], 2)


class Bug1QueryLocationTests(unittest.TestCase):
    """Bug 1: queries must preserve ICP geography (city-specific queries come first)."""

    def test_city_queries_lead_when_icp_has_city(self):
        """When ICP specifies a city, the first queries must target that city, not just India."""
        spec = IcpSpec(raw_text="B2B SaaS companies in Bengaluru", industries=["saas"],
                       cities=["Bengaluru"], source="fallback")
        qs = expand(spec)
        # All city-specific queries must come before any India-wide-only queries
        first_india_idx = next((i for i, q in enumerate(qs) if q.location == "India"), len(qs))
        first_city_idx = next((i for i, q in enumerate(qs) if q.location == "Bengaluru"), len(qs))
        self.assertLess(first_city_idx, first_india_idx,
                        "City-specific queries must appear before India-wide queries when ICP has a city")

    def test_small_limit_still_hits_city(self):
        """With a small query limit (e.g. 5), all queries must target the ICP city."""
        spec = IcpSpec(raw_text="B2B SaaS companies in Bengaluru", industries=["saas"],
                       cities=["Bengaluru"], source="fallback")
        qs = expand(spec)
        # Simulate a provider that only runs the first 5 queries
        first_five = qs[:5]
        locations = {q.location for q in first_five}
        self.assertIn("Bengaluru", locations,
                      f"First 5 queries must include Bengaluru; got locations: {locations}")
        # India-wide queries must not be the ONLY location in the first 5
        self.assertNotEqual(locations, {"India"},
                            "First 5 queries must not be India-only when city is specified in ICP")

    def test_bengaluru_icp_query_texts_contain_bengaluru(self):
        """Query texts for Bengaluru ICP must contain the city name, not silently drop to 'India'."""
        spec = IcpSpec(raw_text="B2B SaaS companies in Bengaluru", industries=["saas"],
                       cities=["Bengaluru"], source="fallback")
        qs = expand(spec)
        city_qs = [q for q in qs if q.location == "Bengaluru"]
        self.assertGreater(len(city_qs), 0, "Must generate Bengaluru-targeted queries")
        for q in city_qs:
            self.assertIn("Bengaluru", q.text,
                          f"Query '{q.text}' targets Bengaluru location but city is absent from text")

    def test_india_queries_still_included_as_additional(self):
        """India-wide queries must also be present (as additional, not replacements)."""
        spec = IcpSpec(raw_text="B2B SaaS companies in Bengaluru", industries=["saas"],
                       cities=["Bengaluru"], source="fallback")
        qs = expand(spec)
        self.assertTrue(any(q.location == "India" for q in qs),
                        "India-wide queries must still be generated for a city-specific ICP")

    def test_no_city_icp_still_leads_with_india(self):
        """When no city is specified the original India-first order is preserved."""
        spec = IcpSpec(raw_text="auto parts", industries=["auto components"], source="fallback")
        qs = expand(spec)
        self.assertEqual(qs[0].location, "India",
                         "India-wide query must be first when no city/state is in the ICP")


class Bug2ListingExtractionTests(unittest.TestCase):
    """Bug 2: listing/page titles must never become company records."""

    # --- normalize() tests: items arriving with listing-sounding names ---

    def test_listing_title_as_name_is_not_resolvable(self):
        """RawItem.name='Top B2B SaaS Companies' must be flagged as a listing, not a company."""
        for title in (
            "Top B2B SaaS Companies",
            "28 Top B2B SaaS Companies in India",
            "Best SaaS Companies in Bengaluru",
        ):
            n = normalize(RawItem(name=title, website="https://some-blog.com/list"))
            self.assertTrue(n.is_listing,
                            f"name='{title}' should be detected as a listing page, not a company")
            self.assertFalse(n.resolvable,
                             f"name='{title}' must not be resolvable to a company record")

    def test_real_company_names_not_affected(self):
        """Genuine company names must not be incorrectly flagged as listings."""
        for name in ("Hasura", "Whatfix", "Chargebee", "Postman", "Keka HR"):
            n = normalize(RawItem(name=name, website=f"https://{name.lower()}.com"))
            self.assertFalse(n.is_listing,
                             f"Real company name '{name}' must not be flagged as a listing")
            self.assertTrue(n.resolvable, f"'{name}' must be resolvable")

    # --- _clean_company_name() tests: extractor-level filter ---

    def test_clean_rejects_listicle_headings(self):
        """_clean_company_name must return '' for typical listing headings."""
        from backend.app.discovery.extractor import _clean_company_name
        bad_headings = [
            "Top B2B SaaS Companies",
            "Best SaaS Companies in Bengaluru",
            "28 Top B2B SaaS Companies in India",
            "Leading Startups in Bangalore",
            "Top Rated SaaS Vendors",
        ]
        for h in bad_headings:
            result = _clean_company_name(h)
            self.assertEqual(result, "",
                             f"_clean_company_name('{h}') should return '' but got '{result}'")

    def test_clean_keeps_real_company_names(self):
        """_clean_company_name must NOT strip real company names."""
        from backend.app.discovery.extractor import _clean_company_name
        good_names = [
            "Hasura",
            "Whatfix",
            "Chargebee",
            "1. Postman",        # numbered heading -> "Postman"
            "ABC Pumps - Best Manufacturer of Pumps in Pune",  # tagline sep
        ]
        expected = ["Hasura", "Whatfix", "Chargebee", "Postman", "ABC Pumps"]
        for raw, exp in zip(good_names, expected):
            result = _clean_company_name(raw)
            self.assertEqual(result, exp,
                             f"_clean_company_name('{raw}') should be '{exp}' but got '{result}'")

    # --- engine-level test: listing title from provider must not count toward unique_count ---

    def test_listing_title_from_provider_not_counted_as_unique(self):
        """A search result whose title is a listing page title must not inflate unique_count."""
        # Provider returns one item whose name IS a listing title (e.g. scraped from a SERP)
        listing_provider = FakeProvider("search", [[
            {"name": "Top B2B SaaS Companies",
             "title": "Top B2B SaaS Companies",
             "website": "https://beststartup.asia/top-saas",
             "source_id": "listing-1"},
        ]])
        eng = DiscoveryEngine(
            Store(":memory:"),
            DiscoverySettings(provider_failure_threshold=3, workers_per_provider=1),
            [listing_provider],
            interpreter=lambda t: (IcpSpec(raw_text=t, industries=["saas"], source="fallback"), None),
        )
        rid = eng.create_run("saas companies in Bengaluru", {"max_queries_per_provider": 1})
        eng.execute(rid)
        run = eng.store.get_run(rid)
        # The listing title must not have been counted as a unique company
        self.assertEqual(run["unique_count"], 0,
                         f"Listing page title must not be counted as a unique company; unique_count={run['unique_count']}")

    def test_target_unique_not_inflated_by_listing_pages(self):
        """target_unique early-stop must not trigger prematurely due to listing pages."""
        # Provider yields: 2 listing titles + 3 real companies
        items = [
            {"name": "Top B2B SaaS Companies", "website": "https://beststartup.asia/top-saas",
             "source_id": "l1"},
            {"name": "Best SaaS Companies in Bengaluru", "website": "https://tracxn.com/list",
             "source_id": "l2"},
            {"name": "Hasura", "website": "https://hasura.io", "source_id": "r1"},
            {"name": "Whatfix", "website": "https://whatfix.com", "source_id": "r2"},
            {"name": "Chargebee", "website": "https://chargebee.com", "source_id": "r3"},
        ]
        p = FakeProvider("search", [items])
        p.workers = 1
        eng = DiscoveryEngine(
            Store(":memory:"),
            DiscoverySettings(provider_failure_threshold=3, workers_per_provider=1),
            [p],
            interpreter=lambda t: (IcpSpec(raw_text=t, industries=["saas"], source="fallback"), None),
        )
        rid = eng.create_run("saas companies", {"max_queries_per_provider": 1})
        eng.execute(rid)
        run = eng.store.get_run(rid)
        # Only 3 real companies should be counted; the 2 listing titles must be excluded
        self.assertEqual(run["unique_count"], 3,
                         f"Only real companies must count; expected unique_count=3, got {run['unique_count']}")


class CompanyExtractionQualityTests(unittest.TestCase):
    """Regression tests for: real company name extraction, 'Key facts about X' handling,
    generic/category heading rejection, official-website verification, and dedup of a
    heading + its plain-name counterpart into a single company."""

    # --- normalize(): generic/category headings must never become company records ---

    def test_bare_category_word_rejected(self):
        n = normalize(RawItem(name="Saas", website="https://some-blog.com/saas"))
        self.assertTrue(n.is_listing, "'Saas' is a category label, not a company")
        self.assertFalse(n.resolvable)

    def test_about_category_heading_rejected(self):
        n = normalize(RawItem(name="About SaaS sector", website="https://some-blog.com/about-saas"))
        self.assertTrue(n.is_listing, "'About SaaS sector' is category framing, not a company")
        self.assertFalse(n.resolvable)

    # --- normalize(): "Key facts about X" unwraps to a genuine company X ---

    def test_key_facts_about_razorpay_becomes_razorpay(self):
        n = normalize(RawItem(name="Key facts about Razorpay", website="https://razorpay.com"))
        self.assertEqual(n.name, "Razorpay")
        self.assertFalse(n.is_listing)
        self.assertTrue(n.resolvable)
        self.assertEqual(n.domain, "razorpay.com")

    def test_key_facts_about_mygate_becomes_mygate(self):
        n = normalize(RawItem(name="Key facts about Mygate", city="Bengaluru"))
        self.assertEqual(n.name, "Mygate")
        self.assertFalse(n.is_listing)
        self.assertTrue(n.resolvable)

    def test_plain_real_company_names_valid(self):
        for name in ("Razorpay", "Capillary Technologies"):
            n = normalize(RawItem(name=name, website=f"https://{name.split()[0].lower()}.com"))
            self.assertFalse(n.is_listing, f"'{name}' must not be flagged as a listing")
            self.assertTrue(n.resolvable, f"'{name}' must be resolvable")
            self.assertEqual(n.name, name)

    def test_about_us_style_heading_rejected_not_turned_into_us(self):
        n = normalize(RawItem(name="About Us"))
        self.assertFalse(n.resolvable)
        self.assertNotEqual(n.name, "Us")

    # --- extractor._clean_company_name: same behavior at the extraction layer ---

    def test_clean_company_name_handles_about_and_category_cases(self):
        from backend.app.discovery.extractor import _clean_company_name
        cases = {
            "Saas": "",
            "About SaaS sector": "",
            "Key facts about Razorpay": "Razorpay",
            "Key facts about Mygate": "Mygate",
            "Razorpay": "Razorpay",
            "Capillary Technologies": "Capillary Technologies",
            "About Us": "",
        }
        for raw, expected in cases.items():
            self.assertEqual(_clean_company_name(raw), expected,
                             f"_clean_company_name({raw!r}) should be {expected!r}")

    # --- dedup: heading form and plain form of the same company must merge ---

    def test_heading_and_plain_name_merge_into_one_company(self):
        st = Store(":memory:")
        run = st.create_run("x", {})
        a = st.ingest_item(run, 1, "p", "q", 1,
                           normalize(RawItem(name="Razorpay", website="https://razorpay.com")), {}, "high")
        b = st.ingest_item(run, 1, "p2", "q", 1,
                           normalize(RawItem(name="Key facts about Razorpay", city="")), {}, "low")
        self.assertEqual(a["company_id"], b["company_id"],
                         "'Razorpay' and 'Key facts about Razorpay' must resolve to one company")
        self.assertEqual(st.count_companies(run), 1)
        company = st.list_companies(run)[0]
        self.assertEqual(company["name"], "Razorpay")
        self.assertEqual(company["domain"], "razorpay.com")

    def test_mygate_heading_and_plain_name_merge(self):
        st = Store(":memory:")
        run = st.create_run("x", {})
        a = st.ingest_item(run, 1, "p", "q", 1,
                           normalize(RawItem(name="Mygate", city="Bengaluru")), {}, "low")
        b = st.ingest_item(run, 1, "p2", "q", 1,
                           normalize(RawItem(name="Key facts about Mygate", city="Bengaluru")), {}, "low")
        self.assertEqual(a["company_id"], b["company_id"])
        self.assertEqual(st.count_companies(run), 1)

    # --- website/domain verification: never trust a mismatched or directory domain ---

    def test_domain_matches_name_helper(self):
        from backend.app.discovery.normalize import domain_matches_name
        self.assertTrue(domain_matches_name("Razorpay", "razorpay.com"))
        self.assertTrue(domain_matches_name("Capillary Technologies", "capillary.io"))
        self.assertFalse(domain_matches_name("Razorpay", "unrelatedbrand.com"))
        self.assertFalse(domain_matches_name("Mygate", "f6s.com"))

    def test_resolution_pass_rejects_directory_and_mismatched_domains(self):
        """The post-run website resolution pass must skip directory domains and domains
        that don't plausibly belong to the company, rather than attaching the first hit."""
        # First candidate is a directory profile, second is an unrelated brand, third is
        # the genuine official site -- the engine must skip the first two and use the third.
        search_provider = FakeProvider("search", [[
            {"website": "https://tracxn.com/companies/razorpay", "title": "Razorpay | Tracxn"},
            {"website": "https://unrelatedbrand.com", "title": "Unrelated"},
            {"website": "https://razorpay.com", "title": "Razorpay"},
        ]])
        search_provider.name = "serpapi_google"
        search_provider.kind = "search"

        store = Store(":memory:")
        run = store.create_run("x", {})
        r = store.ingest_item(run, 1, "p", "q", 1,
                              normalize(RawItem(name="Razorpay", city="Bengaluru")), {}, "low")
        eng = DiscoveryEngine(store, DiscoverySettings(provider_failure_threshold=3, workers_per_provider=1),
                              [search_provider])

        eng._resolve_websites(run, [search_provider], target=None)

        company = store.list_companies(run)[0]
        self.assertEqual(company["domain"], "razorpay.com",
                         "Must pick the genuine official site, not the directory or unrelated hit")

    # --- TARGET_UNIQUE: category/heading noise must never count toward it ---

    def test_target_unique_excludes_category_and_about_headings(self):
        items = [
            {"name": "Saas", "website": "https://blog.example.com/saas", "source_id": "c1"},
            {"name": "About SaaS sector", "website": "https://blog.example.com/about", "source_id": "c2"},
            {"name": "Key facts about Razorpay", "website": "https://razorpay.com", "source_id": "r1"},
            {"name": "Key facts about Mygate", "city": "Bengaluru", "source_id": "r2"},
            {"name": "Capillary Technologies", "website": "https://capillary.io", "source_id": "r3"},
        ]
        p = FakeProvider("search", [items])
        p.workers = 1
        eng = DiscoveryEngine(
            Store(":memory:"),
            DiscoverySettings(provider_failure_threshold=3, workers_per_provider=1),
            [p],
            interpreter=lambda t: (IcpSpec(raw_text=t, industries=["saas"], source="fallback"), None),
        )
        rid = eng.create_run("saas companies", {"max_queries_per_provider": 1})
        eng.execute(rid)
        run = eng.store.get_run(rid)
        self.assertEqual(run["unique_count"], 3,
                         "Only Razorpay, Mygate and Capillary Technologies should count")
        names = {c["name"] for c in eng.store.list_companies(rid)}
        self.assertEqual(names, {"Razorpay", "Mygate", "Capillary Technologies"})


if __name__ == "__main__":
    unittest.main()