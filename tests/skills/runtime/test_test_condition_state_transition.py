from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "state_transition.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "state-transition-v1",
        "runtime_unit_key": "model:state-001", "model_key": "state-001", "model_type": "state", "technique_slug": "state", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def base(mode="valid-transitions"):
    return {
        "states": [{"state_key": "draft", "label": "Draft", "authority_refs": []}, {"state_key": "published", "label": "Published", "authority_refs": []}, {"state_key": "archived", "label": "Archived", "authority_refs": []}],
        "initial_states": ["draft"], "terminal_states": ["archived"],
        "transitions": [
            {"transition_key": "T-001", "from": "draft", "event": "publish", "guard_status": True, "guard_refs": [], "to": "published", "authority_refs": []},
            {"transition_key": "T-002", "from": "published", "event": "archive", "guard_status": True, "guard_refs": [], "to": "archived", "authority_refs": []},
            {"transition_key": "T-003", "from": "published", "event": "edit", "guard_status": True, "guard_refs": [], "to": "draft", "authority_refs": []},
        ],
        "reset_options": [{"reset_key": "RESET-001", "from_states": ["*"], "to_state": "draft", "action": "reset", "authority_refs": ["SPEC-RESET"]}],
        "invalid_transition_candidates": [{"candidate_key": "INV-001", "from": "archived", "event": "publish", "authority_refs": ["SPEC-INVALID"]}],
        "coverage_mode": mode,
    }


class StateTransitionRuntimeTests(unittest.TestCase):
    def test_valid_transition_has_self_contained_setup_and_labels(self) -> None:
        result = run(base())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        target = next(row for row in result["payload"]["targets"] if row["target_key"] == "state:transition:T-002")
        self.assertEqual(target["execution"]["initial_state_label"], "Draft")
        self.assertEqual(target["execution"]["setup_prefix"][0]["event"], "publish")
        self.assertEqual(target["execution"]["coverage_sequence"][0]["event"], "archive")

    def test_n_switch_and_round_trip_have_distinct_stable_identities(self) -> None:
        n_switch = base("n-switch")
        n_switch["switch_count"] = 1
        result = run(n_switch)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertTrue(result["payload"]["targets"])
        round_trip = run(base("round-trip"))
        self.assertEqual(round_trip["runtime_status"], "ok")
        self.assertTrue(any(row["target_key"].startswith("state:round-trip:draft:h") for row in round_trip["payload"]["targets"]))

    def test_invalid_transition_uses_attempted_transition_and_uncertain_guard_blocks(self) -> None:
        value = base("invalid-transitions")
        result = run(value)
        target = result["payload"]["targets"][0]
        self.assertEqual(target["execution"]["coverage_sequence"], [])
        self.assertEqual(target["execution"]["attempted_transition"]["candidate_key"], "INV-001")
        uncertain = base()
        uncertain["transitions"][1]["guard_status"] = None
        uncertain["transitions"][1]["guard_refs"] = []
        blocked = run(uncertain)
        self.assertEqual(blocked["result_status"], "unresolved")
        self.assertEqual(blocked["issues"][0]["issue_type"], "uncertain_transition_guard")

    def test_false_guard_requires_authority(self) -> None:
        value = base()
        value["transitions"][0]["guard_status"] = False
        self.assertEqual(run(value)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
