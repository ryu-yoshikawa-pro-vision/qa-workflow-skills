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

    def test_document_location_uses_opaque_identity_and_redacted_value_with_title_separate(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_browser_probes.js").read_text(encoding="utf-8")
        observation = (ROOT / "skills" / "usability-inspection" / "scripts" / "observation_contract.py").read_text(encoding="utf-8")
        catalog = json.loads((ROOT / "skills" / "usability-inspection" / "assets" / "browser-observation-catalog.json").read_text(encoding="utf-8"))
        rules = json.loads((ROOT / "skills" / "usability-inspection" / "assets" / "test-rule-catalog.json").read_text(encoding="utf-8"))

        location_start = probe.index('if (request.probe_key === "document-location")')
        title_start = probe.index('if (request.probe_key === "document-title")', location_start)
        location_probe = probe[location_start:title_start]
        self.assertIn("Symbol.for(\"qa-workflow-skills.document-identity-key.v1\")", probe)
        self.assertIn("crypto.subtle.sign(", probe)
        self.assertIn('"HMAC"', probe)
        self.assertIn("new TextEncoder().encode(location.href)", probe)
        self.assertIn('return { safe_url: `${protocol}//[redacted]`', location_probe)
        self.assertNotIn("parsedUrl.origin", location_probe)
        self.assertNotIn("parsedUrl.pathname", location_probe)
        self.assertNotIn("parsedUrl.search", location_probe)
        self.assertNotIn("parsedUrl.hash", location_probe)
        self.assertIn('value["safe_url"] not in {"http://[redacted]", "https://[redacted]"}', observation)
        self.assertIn('"document.location": ["safe_url", "status", "limitation"]', observation)
        self.assertIn('"document.title": "document-title"', observation)
        location_catalog_probe = next(row for row in catalog["probes"] if row["probe_key"] == "document-location")
        self.assertIn("in-memory keyed HMAC token", location_catalog_probe["sensitive_data_handling"])
        title_probe = next(row for row in catalog["probes"] if row["probe_key"] == "document-title")
        self.assertEqual(title_probe["provided_observation_fields"], ["document.title"])
        self.assertEqual(next(row for row in rules["rules"] if row["rule_id"] == "2779a5")["required_observation_fields"], ["document.title"])
        self.assertIn("never persist raw document.title text", title_probe["sensitive_data_handling"])

    def test_formal_probe_distinguishes_unavailable_identity_from_stale_document(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        unavailable_check = probe.index("if (!initialDocumentIdentity) {")
        stale_check = probe.index("if (initialDocumentIdentity !== request.target_identity)")

        self.assertLess(unavailable_check, stale_check)
        self.assertIn('"browser cannot create an in-memory keyed current-document identity"', probe)
        self.assertIn('"typed WCAG machine probe request is stale for the current document"', probe)

    def test_container_query_states_are_never_inferred_from_computed_style(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_browser_probes.js").read_text(encoding="utf-8")
        contract = (ROOT / "skills" / "usability-inspection" / "scripts" / "observation_contract.py").read_text(encoding="utf-8")
        browser_reference = (ROOT / "skills" / "usability-inspection" / "references" / "playwright-observation.md").read_text(encoding="utf-8")
        self.assertNotIn("computedEffect", probe)
        self.assertNotIn("actual === expected", probe)
        self.assertIn('currentMatch = null;', probe)
        self.assertIn('executionStatus = "not-executable";', probe)
        self.assertIn('window.matchMedia(rule.conditionText).matches', probe)
        self.assertIn('standard browser APIs do not expose the current @container match state', probe)
        self.assertIn('if (row.execution_status !== "executable")', probe)
        self.assertIn("match: null", probe)
        self.assertIn('axis not in {"width", "height"}', contract)
        self.assertIn("@container` rules", browser_reference)

    def test_formal_link_inventory_retains_only_non_sensitive_link_context(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        start = probe.index('case "mp-link-inventory"')
        end = probe.index('case "mp-structure-inventory"', start)
        link_probe = probe[start:end]
        for allowed in ("safe_target", "has_query", "has_fragment", "path_segment_count", "rendered_text", "accessible_name"):
            self.assertIn(allowed, link_probe)
        for forbidden in ("target.href", "target.pathname,", "target.search,", "target.hash,", "href: element.getAttribute"):
            self.assertNotIn(forbidden, link_probe)

    def test_environment_and_safe_fixture_contract_are_repository_owned(self):
        readme = (FIXTURE / "README.md").read_text(encoding="utf-8")
        html = (FIXTURE / "index.html").read_text(encoding="utf-8")
        css = (FIXTURE / "fixture.css").read_text(encoding="utf-8")
        script = (FIXTURE / "fixture.js").read_text(encoding="utf-8")
        fallback = (FIXTURE / "manual-limitations.html").read_text(encoding="utf-8")
        empty_title = (FIXTURE / "title-empty.html").read_text(encoding="utf-8")
        ua_fallback = (FIXTURE / "ua-text-scaling-manual.html").read_text(encoding="utf-8")
        unreadable_scale = (FIXTURE / "text-scale-unreadable.html").read_text(encoding="utf-8")
        container_queries = (FIXTURE / "container-query-cases.html").read_text(encoding="utf-8")

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
        for condition in ("@container (min-width: 400px)", "@container style(--variant: promoted)",
                          "@container shared-card (min-width: 250px)", "@media (min-width: 600px)",
                          "@media (max-width: 600px)", "@media (400px < width < 600px)",
                          "@media (width: 500px)",
                          "@media (min-width: 400px) and (max-width: 600px)"):
            with self.subTest(condition=condition):
                self.assertIn(condition, container_queries)
        self.assertEqual(container_queries.count("#same-value"), 2)
        self.assertRegex(container_queries, r"#same-value\s*\{\s*color:\s*red;\s*\}")
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
        ordinary_probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_browser_probes.js").read_text(encoding="utf-8")
        title_start = probe.index('case "mp-document-title"')
        title_end = probe.index('case "mp-document-language"', title_start)
        title_probe = probe[title_start:title_end]
        self.assertIn("has_title_element", title_probe)
        self.assertIn("first_title_children_are_text", title_probe)
        self.assertIn("has_non_whitespace_text", title_probe)
        self.assertIn('getElementsByTagNameNS(htmlNamespace, "title")', title_probe)
        self.assertIn('document.contentType?.toLowerCase()', title_probe)
        self.assertIn('document.documentElement?.localName === "html"', title_probe)
        self.assertIn("titleElement.childNodes.length > 0", title_probe)
        self.assertIn("Array.from(titleElement.childNodes).every", title_probe)
        self.assertIn(r"/\P{White_Space}/u", title_probe)
        self.assertNotIn('document.querySelector("title")', title_probe)
        self.assertNotIn("title: safeText", title_probe)
        ordinary_title_start = ordinary_probe.index('if (request.probe_key === "document-title")')
        ordinary_title_end = ordinary_probe.index('if (request.probe_key === "navigation-timing"', ordinary_title_start)
        ordinary_title_probe = ordinary_probe[ordinary_title_start:ordinary_title_end]
        self.assertIn('document.contentType?.toLowerCase()', ordinary_title_probe)
        self.assertIn('getElementsByTagNameNS(htmlNamespace, "title")', ordinary_title_probe)

        multiple = (FIXTURE / "title-multiple-children.html").read_text(encoding="utf-8")
        non_html = (FIXTURE / "title-non-html.xml").read_text(encoding="utf-8")
        self.assertIn("<title>First title text</title>", multiple)
        self.assertIn("<title>Second title text</title>", multiple)
        self.assertIn('firstTitle.append(document.createElement("span"))', multiple)
        self.assertIn('xmlns="urn:qa-workflow-skills:fixture"', non_html)

    def test_formal_target_geometry_uses_locator_visibility_geometry_and_shadow_safe_refs(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        start = probe.index('if (request.machine_probe_key === "mp-target-geometry")')
        end = probe.index('if (request.machine_probe_key === "mp-focus-appearance-evidence")', start)
        geometry = probe[start:end]
        self.assertIn("page.locator(selector)", geometry)
        self.assertIn("target.isVisible()", geometry)
        self.assertIn("target.boundingBox()", geometry)
        self.assertIn("target.ariaSnapshotJSON", geometry)
        self.assertIn("included_in_accessibility_tree", geometry)
        self.assertIn('"::shadow"', probe)
        self.assertNotIn("querySelectorAll", geometry)
        self.assertNotIn("Number(style.opacity) > 0", geometry)

    def test_formal_component_probe_uses_browser_accessible_name_presence_only(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        start = probe.index('case "mp-component-semantics"')
        end = probe.index('case "mp-status-candidate-inventory"', start)
        component = probe[start:end]
        self.assertIn("role: roleOf(element)", component)
        self.assertIn("accessible_name_present: accessibilityTreeIncludes(element)", component)
        self.assertIn("? accessibleNamePresent(element)", component)
        self.assertIn("included_in_accessibility_tree: accessibilityTreeIncludes(element)", component)
        self.assertIn("element instanceof HTMLInputElement", component)
        self.assertIn("? element.type", component)
        self.assertIn('if (request.machine_probe_key !== "mp-component-semantics")', probe)
        self.assertNotIn("accessible_name:", component)

    def test_focus_probe_uses_real_tab_sequence_and_closes_limit_or_restore_failure(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        start = probe.index("const captureFocusSequence = async")
        end = probe.index("\n  };\n\n  if (", start)
        focus = probe[start:end]
        for contract in ("page.keyboard.press(\"Tab\")", "cycle_kind", "limitReached", "finally",
                         "originalFocus.evaluate", "window.scrollTo(position.x, position.y)",
                         "focus-observation-limit-reached", "focus-loop-detected",
                         "focus-cycle-not-complete", "focus-left-document", "focus-target-removed"):
            with self.subTest(contract=contract):
                self.assertIn(contract, focus)
        self.assertNotIn("querySelectorAll", focus)

    def test_formal_observations_use_playwright_semantics_and_shadow_safe_refs(self):
        probe = (ROOT / "skills" / "usability-inspection" / "scripts" / "fixed_wcag_machine_probes.js").read_text(encoding="utf-8")
        fixture = (FIXTURE / "playwright-observation-cases.html").read_text(encoding="utf-8")

        for contract in ("page.locator(selector)", "ariaSnapshotJSON({ depth: 0", "item.isVisible()", "item.isEnabled()",
                         "accessibility_tree_includes_element", "focus-observation-limit-reached",
                         "focus-loop-detected", '"::shadow"'):
            with self.subTest(contract=contract):
                self.assertIn(contract, probe)
        self.assertIn("locator.evaluateAll", probe)
        text_probe = probe[probe.index('case "mp-text-presentation-values"'):probe.index('case "mp-viewport-state"')]
        self.assertIn('allVisible("*")', text_probe)
        self.assertNotIn('createTreeWalker(document.body', text_probe)
        self.assertIn('page.locator("body *").evaluateAll', probe)
        self.assertIn("const textOf = (element) => safeText(element?.innerText || \"\")", probe)
        self.assertNotIn("const roleOf = (element) =>\n          element.getAttribute(\"role\")", probe)
        for element_id in ("submit-input", "image-input", "aria-hidden-child", "aria-label-button",
                           "labelledby-button", "empty-name-button", "synthetic-secret-name",
                           "synthetic-secret-value", "opacity-zero", "display-none",
                           "visibility-hidden", "aria-hidden-button", "viewport-outside",
                           "disabled-button", "aria-disabled-checkbox", "focus-trap", "remove-on-tab",
                           "host-a", "host-b"):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', fixture)
        self.assertIn('focusTrap.dataset.trap === "true"', fixture)
        self.assertIn('removeOnTab.dataset.removeOnTab === "true"', fixture)
        self.assertIn("button[data-focus-bound]", fixture)


if __name__ == "__main__":
    unittest.main()
