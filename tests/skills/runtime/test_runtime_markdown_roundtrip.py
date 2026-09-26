from __future__ import annotations

import unittest

from tests.skills.runtime.test_ep_vertical_integration import EpVerticalIntegrationTests


class RuntimeMarkdownRoundTripTests(unittest.TestCase):
    def test_standalone_evidence_markdown_round_trips_through_cli_verifier(self) -> None:
        EpVerticalIntegrationTests().test_standalone_evidence_and_qa_workflow_integration()


if __name__ == "__main__":
    unittest.main()
