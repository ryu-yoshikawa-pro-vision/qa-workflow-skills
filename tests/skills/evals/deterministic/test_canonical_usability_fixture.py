from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import urllib.request
import unittest


ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "tests" / "skills" / "fixtures" / "usability-canonical"


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass


class CanonicalUsabilityFixtureTests(unittest.TestCase):
    def test_environment_and_safe_fixture_contract_are_repository_owned(self):
        readme = (FIXTURE / "README.md").read_text(encoding="utf-8")
        html = (FIXTURE / "index.html").read_text(encoding="utf-8")
        css = (FIXTURE / "fixture.css").read_text(encoding="utf-8")
        script = (FIXTURE / "fixture.js").read_text(encoding="utf-8")
        fallback = (FIXTURE / "manual-limitations.html").read_text(encoding="utf-8")

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
        self.assertIn("linear-gradient", fallback)
        self.assertIn("complex-focus", fallback)
        for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)

    def test_fixed_static_server_serves_entry_views_and_manual_fallback(self):
        handler = partial(QuietStaticHandler, directory=str(FIXTURE))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            for path, content_type in (("/", "text/html"), ("/fixture.css", "text/css"),
                                       ("/fixture.js", "javascript"), ("/manual-limitations.html", "text/html"),
                                       ("/fixture-icon.svg", "image/svg+xml")):
                with self.subTest(path=path), urllib.request.urlopen(base + path, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn(content_type, response.headers.get("Content-Type", ""))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
