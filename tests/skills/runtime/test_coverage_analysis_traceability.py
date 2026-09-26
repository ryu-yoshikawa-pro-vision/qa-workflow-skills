from __future__ import annotations

import unittest

from tests.skills.runtime.test_traceability_runtime import TraceabilityRuntimeTests


class CoverageAnalysisTraceabilityTests(unittest.TestCase):
    def test_expected_runtime_and_entity_closure_is_complete(self) -> None:
        TraceabilityRuntimeTests().test_expected_sets_and_graph_are_complete()


if __name__ == "__main__":
    unittest.main()
