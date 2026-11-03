from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "code-quality.yml"


class CodeQualityWorkflowContracts(unittest.TestCase):
    def test_user_namespace_smokes_mount_the_trusted_noop_runtime(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        probes = re.findall(
            r"(?m)^\s*(?:if ! )?timeout 10 bwrap --unshare-user --uid 0 --gid 0 ([^\n]+)",
            workflow,
        )

        self.assertEqual(len(probes), 2, "baseline and post-profile probes required")
        for arguments in probes:
            with self.subTest(arguments=arguments):
                self.assertIn("--clearenv", arguments)
                self.assertIn("--dir /usr", arguments)
                self.assertIn("--ro-bind /usr /usr", arguments)
                self.assertIn("--symlink usr/lib /lib", arguments)
                self.assertIn("--symlink usr/lib64 /lib64", arguments)
                self.assertIn("-- /usr/bin/true", arguments)

    def test_profile_application_requires_a_matching_kernel_denial(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name=\"proc/[0-9]+/uid_map\"", workflow)
        self.assertIn("capname=\"setpcap\"", workflow)
        self.assertIn(
            '&& [ "$apparmor_denial_matches_probe" = true ]',
            workflow,
        )

    def test_post_profile_audit_is_scoped_after_a_fresh_cursor(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("journalctl -k -n 0 --show-cursor", workflow)
        self.assertIn('journalctl -k --after-cursor "$audit_cursor"', workflow)


if __name__ == "__main__":
    unittest.main()
