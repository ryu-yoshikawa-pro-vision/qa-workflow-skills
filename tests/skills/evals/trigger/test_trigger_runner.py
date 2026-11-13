from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.skills.evals.trigger import run

INIT = json.dumps({"type": "system", "subtype": "init", "model": "claude-haiku-5-5"})


def assistant(*blocks: dict) -> str:
    return json.dumps({"type": "assistant", "message": {"content": list(blocks)}})


def skill_call(name: str) -> dict:
    return {"type": "tool_use", "name": "Skill", "input": {"skill": name}}


def result(subtype: str = "error_max_turns", is_error: bool = True) -> str:
    return json.dumps({"type": "result", "subtype": subtype, "is_error": is_error})


def stream(*lines: str) -> str:
    return "\n".join(lines)


def attempt(
    query_id: str, should: bool, triggered: bool, status: str = "valid"
) -> dict:
    return {
        "query_id": query_id,
        "skill": "defect-management",
        "should_trigger": should,
        "status": status,
        "invoked_skills": ["defect-management"] if triggered else [],
        "target_triggered": triggered,
    }


class ObservationTests(unittest.TestCase):
    def test_loaded_skills_come_from_the_skill_tool_call_not_from_text(self) -> None:
        text_only = assistant({"type": "text", "text": "I would use defect-management"})
        called = assistant(
            {"type": "text", "text": "ok"},
            skill_call("defect-management"),
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
        )
        self.assertEqual(run.invoked_skills(stream(INIT, text_only, result())), [])
        self.assertEqual(
            run.invoked_skills(stream(INIT, called, result())), ["defect-management"]
        )
        self.assertEqual(run.invoked_skills("not json\n{broken"), [])

    def test_attempts_without_a_finished_observation_are_invalid(self) -> None:
        ok = stream(INIT, assistant(skill_call("x")), result())
        self.assertEqual(
            run.classify_attempt(ok, timed_out=False, returncode=1), "valid"
        )
        self.assertEqual(
            run.classify_attempt(ok, timed_out=True, returncode=None), "invalid_timeout"
        )
        self.assertEqual(
            run.classify_attempt(stream(INIT), timed_out=False, returncode=1),
            "invalid_no_result",
        )
        self.assertEqual(
            run.classify_attempt(result(), timed_out=False, returncode=1),
            "invalid_no_result",
        )
        failed = stream(INIT, result("error_during_execution"))
        self.assertEqual(
            run.classify_attempt(failed, timed_out=False, returncode=1), "invalid_error"
        )


class AggregationTests(unittest.TestCase):
    def test_thresholds_are_strict_and_invalid_attempts_are_excluded(self) -> None:
        rows = [
            attempt("p", True, True),
            attempt("p", True, True),
            attempt("p", True, False),
            attempt("n", False, False),
            attempt("n", False, False),
            attempt("n", False, True),
            attempt("tie", True, True),
            attempt("tie", True, False),
        ]
        summary = {s["query_id"]: s for s in run.aggregate(rows)}
        self.assertEqual(summary["p"]["verdict"], "pass")
        self.assertEqual(summary["n"]["verdict"], "pass")
        # 0.5ちょうどは positive でも negative でも合格にしない。
        self.assertEqual(summary["tie"]["verdict"], "fail")

    def test_timeouts_are_not_counted_as_not_triggered(self) -> None:
        rows = [
            attempt("q", True, True),
            attempt("q", True, True),
            attempt("q", True, False, status="invalid_timeout"),
            attempt("q", True, False, status="invalid_timeout"),
        ]
        [row] = run.aggregate(rows)
        self.assertEqual((row["valid_attempts"], row["invalid_attempts"]), (2, 2))
        self.assertEqual(row["trigger_rate"], 1.0)
        self.assertEqual(row["verdict"], "pass")

    def test_too_few_valid_attempts_is_not_a_verdict(self) -> None:
        rows = [attempt("q", True, True)] + [
            attempt("q", True, False, status="invalid_timeout") for _ in range(2)
        ]
        [row] = run.aggregate(rows)
        self.assertEqual(row["verdict"], "insufficient_valid_attempts")
        [empty] = run.aggregate(
            [attempt("e", True, False, status="invalid_timeout") for _ in range(3)]
        )
        self.assertIsNone(empty["trigger_rate"])
        self.assertEqual(empty["verdict"], "insufficient_valid_attempts")

    def test_misfires_of_other_skills_are_reported(self) -> None:
        row = attempt("n", False, False)
        row["invoked_skills"] = ["test-reporting"]
        [summary] = run.aggregate([row, row])
        self.assertEqual(summary["other_skills_loaded"], ["test-reporting"])


class SelectionAndIsolationTests(unittest.TestCase):
    def test_queries_are_selected_by_class_in_file_order(self) -> None:
        picked = run.select_queries(["defect-management"], 2)
        self.assertEqual(
            [(p["should_trigger"]) for p in picked], [True, True, False, False]
        )
        self.assertEqual(len({p["query_id"] for p in picked}), 4)
        rows = json.loads(
            (
                run.SKILLS_ROOT
                / "defect-management"
                / "evals"
                / "trigger"
                / "validation_queries.json"
            ).read_text(encoding="utf-8")
        )
        positives = [r["query"] for r in rows if r["should_trigger"]][:2]
        self.assertEqual([p["query"] for p in picked[:2]], positives)

    def test_estimate_counts_runs(self) -> None:
        plan = run.estimate([{}] * 8, 3, 4)
        self.assertEqual((plan["queries"], plan["runs"]), (8, 24))

    def test_every_repository_skill_is_available_without_eval_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            names = run.build_workspace(Path(temp))
            root = Path(temp) / ".claude" / "skills"
            self.assertEqual(names, run.repository_skills())
            self.assertTrue(all((root / n / "SKILL.md").is_file() for n in names))
            self.assertFalse(any((root / n / "evals").exists() for n in names))

    def test_parent_session_variables_and_user_config_do_not_leak(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "x", "KEEP_ME": "yes"},
        ):
            env = run.clean_environment(Path("/isolated"))
        self.assertNotIn("CLAUDECODE", env)
        self.assertNotIn("CLAUDE_CODE_SESSION_ID", env)
        self.assertEqual(env["KEEP_ME"], "yes")
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], "/isolated")

    def test_config_dir_links_credentials_without_copying_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            credentials = Path(temp) / "credentials.json"
            credentials.write_text("{}", encoding="utf-8")
            config = run.make_config_dir(Path(temp) / "base", credentials)
            link = config / ".credentials.json"
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), str(credentials))
            self.assertEqual([p.name for p in config.iterdir()], [".credentials.json"])


class EarlyStopTests(unittest.TestCase):
    def test_decision_is_the_first_skill_call_in_a_line(self) -> None:
        called = assistant(
            {"type": "text", "text": "ok"},
            skill_call("defect-management"),
            skill_call("other"),
        )
        self.assertEqual(run.skill_call_in_line(called), "defect-management")

    def test_lines_without_a_skill_call_do_not_stop_the_run(self) -> None:
        bash = assistant({"type": "tool_use", "name": "Bash", "input": {}})
        text = assistant({"type": "text", "text": "Skill defect-management"})
        for line in (INIT, bash, text, result(), "not json"):
            self.assertIsNone(run.skill_call_in_line(line))


if __name__ == "__main__":
    unittest.main()
