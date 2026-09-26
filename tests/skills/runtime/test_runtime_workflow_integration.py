from __future__ import annotations

import unittest

from tests.skills.runtime.test_ep_vertical_integration import EpVerticalIntegrationTests


class RuntimeWorkflowIntegrationTests(unittest.TestCase):
    def test_ep_standalone_runtime_is_accepted_by_qa_workflow(self) -> None:
        EpVerticalIntegrationTests().test_standalone_evidence_and_qa_workflow_integration()


if __name__ == "__main__":
    unittest.main()
