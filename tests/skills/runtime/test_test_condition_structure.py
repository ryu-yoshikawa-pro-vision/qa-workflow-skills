from __future__ import annotations

import unittest

from tests.skills.runtime.test_ep_vertical_integration import CONDITION_SCRIPT, condition_input, condition_metadata, run_script


class ConditionStructureRuntimeTests(unittest.TestCase):
    def test_condition_structure_assigns_stable_tcn_and_model_state(self) -> None:
        result = run_script(CONDITION_SCRIPT, {"metadata": condition_metadata(), "input": condition_input()})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["tcn_id_map"][0]["tcn_id"], "TCN-001")
        self.assertEqual(result["payload"]["active_model_metadata"][0]["model_key"], "ep-001")


if __name__ == "__main__":
    unittest.main()
