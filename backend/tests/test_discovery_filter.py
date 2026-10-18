import unittest

from backend.app.discovery.classifier import classify
from backend.app.discovery.config import DiscoverySettings
from backend.app.discovery.engine import DiscoveryEngine
from backend.app.discovery.extractor import extract_listing_page_full
from backend.app.discovery.icp import IcpSpec
from backend.app.discovery.normalize import normalize
from backend.app.discovery.providers.base import Page, Provider, ProviderQuery, RawItem
from backend.app.discovery.store import Store


class ClassifyTests(unittest.TestCase):
    def test_products_and_sections_rejected(self):
        for name in ("CNC Machine", "Cnc Machine, 4x6 ft", "CNC Machines Popular Price",
                     "Virat-1030 Double Column Vertical Machining Center, 15 kW",
                     "Pinacho Cnc Turning Centre", "F50 CNC EDM",
                     "Double Column Machining Center, Automation Grade: Automatic",
                     "Industries", "Tech Hubs", "Share this page", "For Recruiters", "Customers",
                     "Funding Trends in the SaaS sector", "Top News in SaaS", "FAQs about SaaS sector",
                     "Companies founded year-on-year in the SaaS sector"):
            self.assertEqual(classify(name)[0], "reject", name)

    def test_real_companies_kept(self):
        for name, dom in (("Razorpay", "razorpay.com"), ("Hasura", "hasura.io"), ("Keka HR", ""),
                          ("Shree Auto Components", ""), ("ABC Pumps Pvt Ltd", "abcpumps.com"),
                          ("Trilok Lasers", "triloklasers.in")):
            self.assertEqual(classify(name, dom)[0], "ok", name)

    def test_ambiguous_is_uncertain(self):
        self.assertEqual(classify("Sharma CNC")[0], "uncertain")
        self.assertEqual(classify("Acme Labs X", "unrelated.com", "article_heading")[0], "ok")  # suffix 'labs'
        self.assertEqual(classify("Zentrix", "zxq.io", "article_heading")[0], "uncertain")


class NormalizeFilterTests(unittest.TestCase):
    def test_product_title_on_aggregator_not_resolvable(self):
        n = normalize(RawItem(title="Cnc Machine, 4x6 ft - IndiaMART",
                              website="https://www.indiamart.com/proddetail/cnc-123.html"))
        self.assertFalse(n.resolvable)
        self.assertTrue(n.note.startswith("rejected"))

    def test_product_title_on_company_domain_becomes_uncertain_domain_only(self):
        n = normalize(RawItem(title="CNC Machine - Buy Online", website="https://dhwaj.co.in/cnc-machine"))
        self.assertEqual((n.verdict, n.name, n.domain), ("uncertain", "", "dhwaj.co.in"))
        self.assertFalse(n.resolvable)

    def test_trusted_provider_skips_filter(self):
        n = normalize(RawItem(name="Sharma CNC Machines", website="https://sharmacnc.com"), trusted=True)
        self.assertTrue(n.resolvable)

    def test_listing_extractor_output_is_filtered(self):
        html = """<html><body>
        <h2>Industries</h2><p><a href="https://somenews.com/a">more</a></p>
        <h2>Top News in SaaS</h2><p><a href="https://roboticstomorrow.com/news/x">read</a></p>
        <h2>Cnc Machine, 4x6 ft</h2><p><a href="https://triloklasers.in">site</a></p>
        <h2>Razorpay</h2><p><a href="https://razorpay.com">Visit website</a></p></body></html>"""
        items, _ = extract_listing_page_full("https://dir.indiamart.com/pune/cnc.html", html)
        ok = [i.name for i in items if normalize(i).resolvable]
        self.assertEqual(ok, ["Razorpay"])


class OneShot(Provider):
    kind, confidence, workers = "search", "low", 1

    def __init__(self, items):
        super().__init__()
        self.name, self.items = "search", items

    def build_queries(self, specs, limit):
        return [ProviderQuery("q")]

    def search(self, pq, max_pages, http):
        yield Page(1, [RawItem(**i) for i in self.items], False)


class EngineVetTests(unittest.TestCase):
    ITEMS = [
        {"title": "CNC Machine - Buy Online", "website": "https://dhwaj.co.in/cnc", "source_id": "a"},
        {"title": "Cnc Machine, 4x6 ft - IndiaMART", "website": "https://www.indiamart.com/proddetail/x.html", "source_id": "b"},
        {"title": "Hasura | GraphQL", "website": "https://hasura.io", "source_id": "c"},
    ]

    def run_engine(self, vetter, use_ollama=True):
        calls = []
        eng = DiscoveryEngine(
            Store(":memory:"), DiscoverySettings(workers_per_provider=1), [OneShot(self.ITEMS)],
            http=type("H", (), {"get_text": lambda *a, **k: ""})(),
            interpreter=lambda t: (IcpSpec(raw_text=t, industries=["cnc"]), None),
            vetter=lambda c: (calls.append(c), vetter(c))[1])
        rid = eng.create_run("cnc", {"max_queries_per_provider": 1, "use_ollama": use_ollama})
        eng.execute(rid)
        return eng, rid, calls

    def test_only_uncertain_goes_to_ollama_and_products_never_saved(self):
        eng, rid, calls = self.run_engine(lambda c: True)
        self.assertEqual(len(calls), 1)                          # dhwaj only; hasura + indiamart decided by rules
        self.assertEqual(calls[0]["domain"], "dhwaj.co.in")
        names = {c["domain"]: c["name"] for c in eng.store.list_companies(rid)}
        self.assertEqual(names, {"dhwaj.co.in": "", "hasura.io": "Hasura"})

    def test_ollama_says_no_or_fails_rejects(self):
        for ans in (False, None):
            eng, rid, _ = self.run_engine(lambda c, a=ans: a)
            self.assertEqual({c["domain"] for c in eng.store.list_companies(rid)}, {"hasura.io"})
            self.assertEqual(eng.store.get_run(rid)["raw_count"], 3)    # raw results still kept

    def test_ollama_disabled_makes_no_calls(self):
        eng, rid, calls = self.run_engine(lambda c: True, use_ollama=False)
        self.assertEqual(calls, [])
        self.assertEqual({c["domain"] for c in eng.store.list_companies(rid)}, {"hasura.io"})


if __name__ == "__main__":
    unittest.main()