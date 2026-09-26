from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_PATH = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "runtime_contract.py"


def entity_row() -> dict:
    content = {"authority_id": "SPEC-001", "title": "Example"}
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("cli_runtime_contract", RUNTIME_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.make_machine_entity("spec-analysis", "authority", "SPEC-001", content)


def metadata() -> dict:
    return {
        "envelope_version": "1",
        "skill": "test-condition-design",
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "ep-v1",
        "runtime_unit_key": "model:ep-001",
        "model_key": "ep-001",
        "model_type": "ep",
        "technique_slug": "ep",
        "selection_source": "analysis",
        "selection_key": "SEL-001",
        "scope_key": None,
        "input_mode": "artifact",
        "upstream_entities": [
            {
                "skill": "spec-analysis",
                "entity_type": "authority",
                "entity_ref": "SPEC-001",
                "content": {"authority_id": "SPEC-001", "title": "Example"},
            }
        ],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": ["SPEC-001"],
        "reference_refs": [],
    }


def run_request(request: dict) -> subprocess.CompletedProcess[bytes]:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(RUNTIME_PATH.parent)!r}); "
        "from runtime_contract import run_cli; "
        "raise SystemExit(run_cli(lambda input_value, metadata: {'payload': {'echo': input_value}}, "
        "skill='test-condition-design', generator='ep', generator_contract_version='ep-v1', "
        f"generator_path={str(RUNTIME_PATH)!r}))"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        check=False,
    )


def run_internal_error_request(request: dict) -> subprocess.CompletedProcess[bytes]:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(RUNTIME_PATH.parent)!r}); "
        "from runtime_contract import run_cli; "
        "raise SystemExit(run_cli(lambda input_value, metadata: (_ for _ in ()).throw(RuntimeError('boom')), "
        "skill='test-condition-design', generator='ep', generator_contract_version='ep-v1', "
        f"generator_path={str(RUNTIME_PATH)!r}))"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        check=False,
    )


class CliContractTests(unittest.TestCase):
    def test_valid_request_returns_one_deterministic_envelope(self) -> None:
        request = {"metadata": metadata(), "input": {"b": 2, "a": 1}}
        first = run_request(request)
        second = run_request(request)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stderr, b"")
        self.assertEqual(first.stdout, second.stdout)
        envelope = json.loads(first.stdout)
        self.assertEqual(envelope["runtime_status"], "ok")
        self.assertEqual(envelope["result_status"], "ready")
        self.assertTrue(envelope["runtime_required"])
        self.assertTrue(envelope["deterministic_generated"])
        self.assertEqual(envelope["payload"], {"echo": {"a": 1, "b": 2}})
        self.assertTrue(envelope["input_fingerprint"].startswith("sha256:"))
        self.assertTrue(envelope["generation_fingerprint"].startswith("sha256:"))

    def test_unknown_request_field_is_preparse_style_invalid_input(self) -> None:
        request = {"metadata": metadata(), "input": {}, "unexpected": True}
        result = run_request(request)
        self.assertEqual(result.returncode, 0)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["runtime_status"], "invalid_input")
        self.assertIsNone(envelope["input_fingerprint"])
        self.assertIsNone(envelope["runtime_unit_key"])

    def test_input_byte_limit_returns_blocked_preparse_envelope(self) -> None:
        request = {"metadata": metadata(), "input": {"text": "x" * (2 * 1024 * 1024)}}
        result = run_request(request)
        self.assertEqual(result.returncode, 0)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["runtime_status"], "limit_exceeded")
        self.assertEqual(envelope["result_status"], "blocked")
        self.assertTrue(envelope["runtime_required"])
        self.assertFalse(envelope["deterministic_generated"])
        self.assertIsNone(envelope["generation_fingerprint"])

    def test_invalid_upstream_fingerprint_is_not_accepted_from_caller(self) -> None:
        request = {"metadata": metadata(), "input": {}}
        request["metadata"]["upstream_entities"][0]["content"]["title"] = "changed"
        result = run_request(request)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["runtime_status"], "ok")
        self.assertNotEqual(envelope["upstream_entity_fingerprints"][0]["content_fingerprint"], "sha256:" + "0" * 64)

    def test_unexpected_handler_error_keeps_pairable_runtime_identity(self) -> None:
        result = run_internal_error_request({"metadata": metadata(), "input": {"a": 1}})
        self.assertEqual(result.returncode, 1)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["runtime_status"], "internal_error")
        self.assertEqual(envelope["runtime_unit_key"], "model:ep-001")
        self.assertEqual(envelope["model_key"], "ep-001")
        self.assertIsNotNone(envelope["input_fingerprint"])
        self.assertIsNotNone(envelope["generation_fingerprint"])


if __name__ == "__main__":
    unittest.main()
