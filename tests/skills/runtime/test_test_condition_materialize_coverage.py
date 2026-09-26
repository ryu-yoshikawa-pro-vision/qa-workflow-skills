from __future__ import annotations

import unittest

from tests.skills.runtime.test_materialize_runtime import MaterializeRuntimeTests


class MaterializeCoverageRuntimeTests(unittest.TestCase):
    def test_ep_target_round_trip_preserves_stable_ci_identity(self) -> None:
        MaterializeRuntimeTests().test_targets_materialize_to_stable_ci_and_machine_entity()


if __name__ == "__main__":
    unittest.main()
