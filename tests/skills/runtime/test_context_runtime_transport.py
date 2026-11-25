from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import downstream_state  # noqa: E402
import runtime_contract as runtime  # noqa: E402


def owner_scope(content: str, *, skill: str = "context-rule-synthesis") -> dict:
    return {
        "skill": skill,
        "target": "context-synthesis-run/" + "a" * 64 + ".json",
        "execution_range": "run:identity",
        "input_mode": "artifact",
        "normalized_input": {
            "owner_verification": {
                "stored_content": content,
                "readback": {"content": content},
                "provider_readbacks": {
                    "context-rule-candidate/" + "b" * 64 + ".json": {"content": content}
                },
            }
        },
        "current_structure_state": None,
    }


def workflow_transport(content: str, *, skill: str = "context-rule-synthesis") -> dict:
    return {"workflow_scopes": [owner_scope(content, skill=skill)]}


class ContextRuntimeTransportTests(unittest.TestCase):
    def test_64_kib_boundary_is_byte_based_and_narrowly_exempted(self) -> None:
        at_limit = "a" * runtime.MAX_STRING_BYTES
        above_limit = "a" * (runtime.MAX_STRING_BYTES + 1)
        self.assertEqual(
            runtime.strict_loads(json.dumps({"value": at_limit}).encode("utf-8"))[
                "value"
            ],
            at_limit,
        )
        with self.assertRaises(runtime.LimitExceeded):
            runtime.strict_loads(json.dumps({"value": above_limit}).encode("utf-8"))

        accepted = workflow_transport(above_limit)
        self.assertEqual(
            runtime.strict_loads(json.dumps(accepted).encode("utf-8"), aggregate=True),
            accepted,
        )
        # The exception is registered-owner and exact-field scoped. Other fields
        # inside the same owner evidence keep the ordinary limit.
        accepted["workflow_scopes"][0]["normalized_input"]["owner_verification"][
            "diagnostic"
        ] = above_limit
        with self.assertRaises(runtime.LimitExceeded):
            runtime.strict_loads(json.dumps(accepted).encode("utf-8"), aggregate=True)

    def test_unregistered_or_misplaced_large_content_is_rejected(self) -> None:
        too_large = "x" * (runtime.MAX_STRING_BYTES + 1)
        for value in (
            workflow_transport(too_large, skill="qa-workflow"),
            {
                "workflow_scopes": [
                    {
                        "skill": "context-rule-synthesis",
                        "owner_verification": {"stored_content": too_large},
                    }
                ]
            },
            {"stored_content": too_large},
        ):
            with self.subTest(value=value.keys()):
                with self.assertRaises(runtime.LimitExceeded):
                    runtime.strict_loads(
                        json.dumps(value).encode("utf-8"), aggregate=True
                    )

    def test_downstream_frozen_tree_uses_the_same_exact_owner_paths(self) -> None:
        content = "日" * 22_000
        transport = workflow_transport(content)
        allowed = runtime._owner_transport_paths(transport)
        self.assertTrue(allowed)
        downstream_state._check_tree(transport, allowed_large_strings=allowed)
        with self.assertRaises(runtime.LimitExceeded):
            downstream_state._check_tree(transport)
        changed = workflow_transport(content, skill="qa-workflow")
        with self.assertRaises(runtime.LimitExceeded):
            downstream_state._check_tree(
                changed, allowed_large_strings=runtime._owner_transport_paths(changed)
            )

    def test_all_skill_runtime_contract_copies_are_synchronized(self) -> None:
        copies = sorted((ROOT / "skills").glob("*/scripts/runtime_contract.py"))
        self.assertEqual(len(copies), 9)
        self.assertEqual(len({path.read_bytes() for path in copies}), 1)


if __name__ == "__main__":
    unittest.main()
