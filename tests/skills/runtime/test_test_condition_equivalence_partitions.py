from __future__ import annotations

import unittest

from tests.skills.runtime.test_ep_runtime import run


class EquivalencePartitionsRuntimeTests(unittest.TestCase):
    def test_minimal_partition_has_stable_materializable_target(self) -> None:
        value = {"sets": [{"set_key": "role", "label": "Role", "partitions": [{"partition_key": "admin", "label": "Admin", "validity": "valid", "definition": {"type": "enum", "values": [{"type": "enum", "value": "admin"}]}, "representative": None, "authority_refs": []}]}]}
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertTrue(result["payload"]["targets"][0]["materializable"])


if __name__ == "__main__":
    unittest.main()
