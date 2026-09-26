from __future__ import annotations

import unittest

from tests.skills.runtime.test_workflow_runtime import WorkflowRuntimeTests


class QaWorkflowRuntimeTests(unittest.TestCase):
    def test_stale_entity_fingerprint_blocks_completion(self) -> None:
        WorkflowRuntimeTests().test_changed_entity_fingerprint_propagates_stale_to_runtime_completion()


if __name__ == "__main__":
    unittest.main()
