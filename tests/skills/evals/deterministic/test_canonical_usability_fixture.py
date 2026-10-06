from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import threading
import urllib.request
import unittest


ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "tests" / "skills" / "fixtures" / "usability-canonical"


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass


class CanonicalUsabilityFixtureTests(unittest.TestCase):
    def test_empty_search_query_does_not_report_a_matching_product(self):
        script = (FIXTURE / "fixture.js").read_text(encoding="utf-8")
        self.assertIn('const query = event.target.value.trim();', script)
        self.assertIn('if (!query) {', script)
        self.assertIn('"Enter a product name to filter the fixture list."', script)
        self.assertIn('"trail pack".includes(query.toLowerCase())', script)

    def test_document_location_is_url_only_and_document_title_is_a_separate_fixed_probe(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_browser_probes.js").read_text(encoding="utf-8")
        observation = (ROOT / "skills" / "usability-inspection" / "scripts" / "observation_contract.py").read_text(encoding="utf-8")
        catalog = json.loads((ROOT / "skills" / "usability-inspection" / "assets" / "browser-observation-catalog.json").read_text(encoding="utf-8"))
        rules = json.loads((ROOT / "skills" / "usability-inspection" / "assets" / "test-rule-catalog.json").read_text(encoding="utf-8"))

        self.assertIn("}, page.url());", probe)
        self.assertIn("new URL(rawUrl)", probe)
        for sensitive_component in ("parsedUrl.username", "parsedUrl.password", "parsedUrl.search", "parsedUrl.hash"):
            with self.subTest(component=sensitive_component):
                self.assertIn(sensitive_component, probe)
        self.assertIn("safe_url: `${parsedUrl.origin}${parsedUrl.pathname}`", probe)
        self.assertIn('"document.location": ["safe_url", "status", "limitation"]', observation)
        self.assertIn('"document.title": "document-title"', observation)
        title_probe = next(row for row in catalog["probes"] if row["probe_key"] == "document-title")
        self.assertEqual(title_probe["provided_observation_fields"], ["document.title"])
        self.assertEqual(next(row for row in rules["rules"] if row["rule_id"] == "2779a5")["required_observation_fields"], ["document.title"])
        self.assertIn("never persist raw document.title text", title_probe["sensitive_data_handling"])

    def test_environment_and_safe_fixture_contract_are_repository_owned(self):
        readme = (FIXTURE / "README.md").read_text(encoding="utf-8")
        html = (FIXTURE / "index.html").read_text(encoding="utf-8")
        css = (FIXTURE / "fixture.css").read_text(encoding="utf-8")
        script = (FIXTURE / "fixture.js").read_text(encoding="utf-8")
        fallback = (FIXTURE / "manual-limitations.html").read_text(encoding="utf-8")
        empty_title = (FIXTURE / "title-empty.html").read_text(encoding="utf-8")
        ua_fallback = (FIXTURE / "ua-text-scaling-manual.html").read_text(encoding="utf-8")
        unreadable_scale = (FIXTURE / "text-scale-unreadable.html").read_text(encoding="utf-8")

        for contract in ("python -m http.server 4173", "1280 × 800", "390 × 844", "unauthenticated", "reload resets"):
            with self.subTest(contract=contract):
                self.assertIn(contract, readme)
        for element_id in ("start-journey", "continue-checkout", "delivery-method", "place-order", "text-scale", "current-view"):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', html)
        for feature in ("@container (width < calc(42rem - 1px))", "@container product-layout style(--contrast: high)", "2cqw", "100vw"):
            with self.subTest(feature=feature):
                self.assertIn(feature, css)
        for behavior in ("Checkout started", "Delivery details opened", "No external order was submitted", "--text-scale"):
            with self.subTest(behavior=behavior):
                self.assertIn(behavior, script)
        self.assertIn('window.matchMedia("(max-width: 48rem)")', script)
        self.assertIn('params.get("view") === "alternate"', script)
        self.assertIn("`?view=alternate` renders the same information and controls", readme)
        self.assertIn("`/title-empty.html` provides a whitespace-only HTML title", readme)
        self.assertIn("<title>   </title>", empty_title)
        self.assertIn('Math.min(200, 100 + (setting - 100) * 2)', script)
        self.assertIn('textScale.max = responsiveLayout.matches ? "150" : "200"', script)
        self.assertIn("formal probe must measure used font sizes", readme)
        self.assertIn("linear-gradient", fallback)
        self.assertIn("complex-focus", fallback)
        self.assertIn("browser chrome zoom menu", ua_fallback)
        self.assertIn('id="canvas-text-size" type="range"', unreadable_scale)
        self.assertIn("canvas.getContext(\"2d\")", unreadable_scale)
        self.assertIn("context.fillText", unreadable_scale)
        self.assertNotIn("transform:", unreadable_scale)
        for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)

    def test_formal_resize_text_uses_the_package_owned_fixed_probe(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        observation_reference = (ROOT / "skills" / "usability-inspection" / "references" / "playwright-observation.md").read_text(encoding="utf-8")
        for requirement in ("mp-resize-text-run", "getByRole(\"slider\"", "ArrowRight", "ArrowLeft",
                           "mechanism_state_sequence", "text_candidates", "content_loss_refs", "cleanup"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, probe)
        self.assertIn("fixed_wcag_machine_probes.js", observation_reference)
        for forbidden in ("setViewportSize", "deviceScaleFactor", "dispatchEvent(", "style.setProperty("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, probe)

    def test_fixed_static_server_serves_entry_views_and_manual_fallback(self):
        handler = partial(QuietStaticHandler, directory=str(FIXTURE))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            for path, content_type in (("/", "text/html"), ("/fixture.css", "text/css"),
                                       ("/fixture.js", "javascript"), ("/manual-limitations.html", "text/html"),
                                       ("/ua-text-scaling-manual.html", "text/html"),
                                       ("/text-scale-unreadable.html", "text/html"),
                                       ("/fixture-icon.svg", "image/svg+xml")):
                with self.subTest(path=path), urllib.request.urlopen(base + path, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn(content_type, response.headers.get("Content-Type", ""))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_formal_manual_fallback_probe_dispatch_is_fixed_and_bounded(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        for requirement in ("mp-computed-color-context", "mp-focus-appearance-evidence", "mp-target-geometry",
                            "background-not-machine-resolvable", "focus-indicator-not-machine-resolvable",
                            "text-scaling-mechanism-not-machine-executable",
                            "text-scaling-state-not-machine-readable", "unsupported_visible_canvas"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, probe)
        self.assertIn("fixedProbeKeys", probe)
        for forbidden in ("setViewportSize", "deviceScaleFactor", "style.setProperty(", "transform: scale"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, probe)

    def test_formal_title_probe_keeps_only_safe_title_predicates(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        title_start = probe.index('case "mp-document-title"')
        title_end = probe.index('case "mp-document-language"', title_start)
        title_probe = probe[title_start:title_end]
        self.assertIn("has_title_element", title_probe)
        self.assertIn("first_title_children_are_text", title_probe)
        self.assertIn("has_non_whitespace_text", title_probe)
        self.assertNotIn("title: safeText", title_probe)


if __name__ == "__main__":
    unittest.main()
