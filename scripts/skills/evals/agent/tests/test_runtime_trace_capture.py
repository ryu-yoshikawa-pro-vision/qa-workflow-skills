from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent import common_runtime_checks
from scripts.skills.evals.agent.common import (
    capture_codex_jsonl_trace,
    trace_confirms_capture_invocation,
)
from scripts.skills.evals.agent.verifier_capture import capture_invocation


class RuntimeTraceCaptureTests(unittest.TestCase):
    def test_codex_jsonl_extracts_final_message_and_successful_skill_read(self) -> None:
        events = [
            {"type": "thread.started", "thread_id": "thread-001"},
            {
                "type": "item.completed",
                "item": {
                    "id": "item-read",
                    "type": "command_execution",
                    "command": "cat /workspace/.agents/skills/qa-workflow/SKILL.md",
                    "exit_code": 0,
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "item-final",
                    "type": "agent_message",
                    "text": "Final output.",
                },
            },
            {"type": "turn.completed"},
        ]
        captured = capture_codex_jsonl_trace(
            "\n".join(json.dumps(event) for event in events) + "\n",
            skill_names=["qa-workflow"],
        )
        self.assertEqual(captured["format"], "codex_exec_jsonl")
        self.assertEqual(captured["status"], "captured")
        self.assertEqual(captured["final_message"], "Final output.")
        self.assertEqual(captured["skill_use_observation"]["qa-workflow"], "observed")
        self.assertTrue(captured["commands"][0]["successful"])
        self.assertIsNone(captured["trace_jsonl"])
        self.assertNotIn(
            "cat /workspace/.agents/skills/qa-workflow/SKILL.md",
            json.dumps(captured["trace_summary"]),
        )

    def test_launcher_envelope_keeps_only_safe_jsonl_observations(self) -> None:
        envelope = {
            "protocol": "codex_docker_launcher_v1",
            "exit_code": 0,
            "final_message": "Final output.",
            "observations": {
                "status": "completed",
                "auth_mode": "temporary_auth_file",
                "image": {
                    "image_id": "sha256:" + "a" * 64,
                    "codex_cli_version": "codex-cli 0.163.0",
                    "python_version": "Python 3.11.17",
                },
                "jsonl": {
                    "status": "captured",
                    "event_count": 2,
                    "event_types": {"item.completed": 1, "turn.completed": 1},
                    "command_count": 1,
                    "turn_completed": True,
                    "turn_failed": False,
                    "commands": [
                        {
                            "exit_code": 0,
                            "successful": True,
                            "skill_files_read": ["qa-workflow"],
                            "verifier_capture_invocations": [],
                        }
                    ],
                },
            },
        }
        captured = capture_codex_jsonl_trace(
            json.dumps(envelope), skill_names=["qa-workflow"]
        )
        self.assertEqual(captured["format"], "codex_docker_launcher_v1")
        self.assertEqual(captured["execution_status"], "completed")
        self.assertEqual(
            captured["launcher_observations"]["image"]["codex_cli_version"],
            "codex-cli 0.163.0",
        )
        self.assertEqual(captured["skill_use_observation"]["qa-workflow"], "observed")
        self.assertIsNone(captured["trace_jsonl"])
        self.assertNotIn('"command":', json.dumps(captured["trace_summary"]))

    def test_jsonl_with_unknown_event_type_is_not_saved_as_candidate_output(
        self,
    ) -> None:
        raw = json.dumps({"type": "future.event", "payload": "sensitive"})
        captured = capture_codex_jsonl_trace(raw, skill_names=["qa-workflow"])
        self.assertEqual(captured["final_message"], "")
        self.assertIsNone(captured["trace_jsonl"])
        self.assertEqual(captured["status"], "unverified")

    def test_final_message_after_failed_or_incomplete_turn_is_unverified(self) -> None:
        final_message = {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "Partial output."},
        }
        cases = (
            [final_message],
            [final_message, {"type": "turn.failed"}],
            [final_message, {"type": "error", "message": "request failed"}],
        )
        for events in cases:
            with self.subTest(event_types=[event["type"] for event in events]):
                captured = capture_codex_jsonl_trace(
                    "\n".join(json.dumps(event) for event in events),
                    skill_names=["qa-workflow"],
                )
                self.assertEqual(captured["final_message"], "Partial output.")
                self.assertEqual(captured["status"], "evidence_unverified")
                self.assertEqual(
                    captured["trace_summary"]["status"], "evidence_unverified"
                )

    def test_nonzero_or_missing_command_exit_code_does_not_confirm_skill_use(
        self,
    ) -> None:
        for exit_code in (None, 1):
            with self.subTest(exit_code=exit_code):
                item = {
                    "id": "item-read",
                    "type": "command_execution",
                    "command": "cat /workspace/.agents/skills/qa-workflow/SKILL.md",
                }
                if exit_code is not None:
                    item["exit_code"] = exit_code
                raw = json.dumps({"type": "item.completed", "item": item})
                captured = capture_codex_jsonl_trace(raw, skill_names=["qa-workflow"])
                self.assertEqual(
                    captured["skill_use_observation"]["qa-workflow"], "unverified"
                )

    def test_trace_confirms_exact_completed_wrapper_request_and_record(self) -> None:
        invocation = {
            "skill": "qa-workflow",
            "operation": "verify",
            "request_relative_path": ".runtime-evidence/qa-workflow/"
            + "a" * 64
            + "/attempt-01/request.json",
            "record_relative_path": ".runtime-evidence/qa-workflow/"
            + "a" * 64
            + "/attempt-01",
        }
        good = {
            "successful": True,
            "command": (
                "python .qa-eval-tools/verifier_capture.py --skill qa-workflow --operation verify "
                "--request .qa-eval-output/"
                + invocation["request_relative_path"]
                + " --record .qa-eval-output/"
                + invocation["record_relative_path"]
            ),
        }
        self.assertTrue(trace_confirms_capture_invocation([good], invocation))
        self.assertFalse(
            trace_confirms_capture_invocation(
                [{**good, "successful": False}], invocation
            )
        )
        self.assertFalse(
            trace_confirms_capture_invocation(
                [
                    {
                        **good,
                        "command": good["command"].replace("attempt-01", "attempt-02"),
                    }
                ],
                invocation,
            )
        )

    def test_standalone_wrapper_captures_verify_result_without_turning_valid_false_into_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_root = root / ".agents" / "skills" / "qa-workflow" / "scripts"
            skill_root.mkdir(parents=True)
            script = skill_root / "runtime_contract.py"
            script.write_text(
                "import json, sys\n"
                "json.loads(sys.stdin.buffer.read())\n"
                "print(json.dumps({'valid': False, 'current_structure_state': []}))\n",
                encoding="utf-8",
            )
            record = (
                root
                / ".qa-eval-output"
                / ".runtime-evidence"
                / "qa-workflow"
                / ("b" * 64)
                / "attempt-01"
            )
            record.mkdir(parents=True)
            request = record / "request.json"
            request_bytes = (
                b'{ "operation": "verify_runtime_evidence", "partial_rerun": false }\n'
            )
            request.write_bytes(request_bytes)
            with patch.object(Path, "cwd", return_value=root):
                result = capture_invocation(
                    skill="qa-workflow",
                    operation="verify",
                    request_path=request,
                    record_path=record,
                )
            saved_result = json.loads(
                (record / "result.json").read_text(encoding="utf-8")
            )
            saved_request = (record / "request.json").read_bytes()
            invocation = json.loads(
                (record / "invocation.json").read_text(encoding="utf-8")
            )
        self.assertEqual(result["evidence_status"], "captured")
        self.assertFalse(saved_result["valid"])
        self.assertEqual(saved_request, request_bytes)
        self.assertEqual(
            invocation["request_sha256"],
            "sha256:" + hashlib.sha256(request_bytes).hexdigest(),
        )
        self.assertEqual(
            invocation["result_relative_path"].split("/")[-1], "result.json"
        )

    def test_nested_runtime_capture_is_replayed_only_when_trace_confirms_it(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_root = root / ".agents" / "skills" / "qa-workflow" / "scripts"
            skill_root.mkdir(parents=True)
            (skill_root / "runtime_contract.py").write_text(
                "import json, sys\njson.loads(sys.stdin.buffer.read())\nprint(json.dumps({'valid': False}))\n",
                encoding="utf-8",
            )
            artifact_path = "docs/checkout-analysis.md"
            artifact_id = hashlib.sha256(artifact_path.encode("utf-8")).hexdigest()
            record = (
                root
                / ".qa-eval-output"
                / ".runtime-evidence"
                / "qa-workflow"
                / artifact_id
                / "attempt-01"
            )
            record.mkdir(parents=True)
            request = record / "request.json"
            request.write_text(
                '{"operation":"verify_runtime_evidence"}\n', encoding="utf-8"
            )
            with patch.object(Path, "cwd", return_value=root):
                invocation = capture_invocation(
                    skill="qa-workflow",
                    operation="verify",
                    request_path=request,
                    record_path=record,
                )
            invocation = json.loads(
                (record / "invocation.json").read_text(encoding="utf-8")
            )
            trace_command = {
                "successful": True,
                "command": (
                    "python .qa-eval-tools/verifier_capture.py --skill qa-workflow --operation verify "
                    f"--request .qa-eval-output/{invocation['request_relative_path']} "
                    f"--record .qa-eval-output/{invocation['record_relative_path']}"
                ),
            }
            with (
                patch.object(
                    common_runtime_checks,
                    "run_candidate_verifier_offline",
                    return_value={
                        "status": "verified",
                        "result": {"valid": False},
                        "result_sha256": "sha256:" + "0" * 64,
                    },
                ),
                patch.object(
                    common_runtime_checks,
                    "_run",
                    return_value=subprocess.CompletedProcess(
                        [], 0, b'{"valid":false}', b""
                    ),
                ),
            ):
                checked = common_runtime_checks.evaluate_runtime_captures(
                    capture_root=root / ".qa-eval-output" / ".runtime-evidence",
                    candidate_package_root=root,
                    verifier_image="sha256:" + "b" * 64,
                    fixed_evaluator_root=root,
                    expected_artifacts=[
                        {"skill": "qa-workflow", "path": artifact_path}
                    ],
                    trace_commands=[trace_command],
                )
        self.assertEqual(invocation["evidence_status"], "captured")
        self.assertEqual(checked["status"], "fail")
        self.assertTrue(checked["captures"][0]["tool_trace_confirmed"])

    def test_nested_workflow_runtime_capture_requires_trace_and_can_replay(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_root = root / ".agents" / "skills" / "qa-workflow" / "scripts"
            skill_root.mkdir(parents=True)
            (skill_root / "workflow_runtime.py").write_text(
                "import json, sys\njson.loads(sys.stdin.buffer.read())\nprint(json.dumps({'payload': {'can_complete': False}}))\n",
                encoding="utf-8",
            )
            artifact_path = "docs/checkout-analysis.md"
            artifact_id = hashlib.sha256(artifact_path.encode("utf-8")).hexdigest()
            record = (
                root
                / ".qa-eval-output"
                / ".runtime-evidence"
                / "qa-workflow"
                / artifact_id
                / "workflow-01"
            )
            record.mkdir(parents=True)
            request = record / "request.json"
            request.write_text('{"payload":{"runtime_units":[]}}\n', encoding="utf-8")
            with patch.object(Path, "cwd", return_value=root):
                invocation = capture_invocation(
                    skill="qa-workflow",
                    operation="workflow-runtime",
                    request_path=request,
                    record_path=record,
                )
            invocation = json.loads(
                (record / "invocation.json").read_text(encoding="utf-8")
            )
            trace_command = {
                "successful": True,
                "command": (
                    "python .qa-eval-tools/verifier_capture.py --skill qa-workflow --operation workflow-runtime "
                    f"--request .qa-eval-output/{invocation['request_relative_path']} "
                    f"--record .qa-eval-output/{invocation['record_relative_path']}"
                ),
            }
            with patch.object(
                common_runtime_checks,
                "_workflow_replay",
                return_value={"status": "pass", "workflow_runtime_can_complete": False},
            ):
                checked = common_runtime_checks.evaluate_workflow_runtime_capture(
                    capture_root=root / ".qa-eval-output" / ".runtime-evidence",
                    candidate_package_root=root,
                    verifier_image="sha256:" + "b" * 64,
                    fixed_evaluator_root=root,
                    expected_artifacts=[
                        {"skill": "qa-workflow", "path": artifact_path}
                    ],
                    trace_commands=[trace_command],
                )
        self.assertEqual(invocation["evidence_status"], "captured")
        self.assertEqual(checked["status"], "pass")
        self.assertTrue(checked["captures"][0]["tool_trace_confirmed"])

    def test_wrapper_rejects_non_allowlisted_skill_and_workflow_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(Path, "cwd", return_value=root):
                with self.assertRaises(ValueError):
                    capture_invocation(
                        skill="adversarial-review",
                        operation="verify",
                        request_path=Path("missing.json"),
                        record_path=Path("missing"),
                    )


if __name__ == "__main__":
    unittest.main()
