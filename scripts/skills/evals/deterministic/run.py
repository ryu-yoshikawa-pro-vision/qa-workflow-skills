from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from scripts.skills.evals.deterministic.loader import load_validators
    from scripts.skills.evals.deterministic.markdown_parser import (
        MarkdownTableParseError,
    )
    from scripts.skills.evals.deterministic.result import EvalResult
    from scripts.skills.evals.deterministic.runtime_validator import (
        validate_runtime_evidence,
        validate_skill_local_runtime_evidence,
    )
else:
    from .loader import load_validators
    from .markdown_parser import MarkdownTableParseError
    from .result import EvalResult
    from .runtime_validator import (
        validate_runtime_evidence,
        validate_skill_local_runtime_evidence,
    )

REPO_ROOT = Path(__file__).resolve().parents[4]
VALIDATORS = load_validators()


def load_eval_definition(skill: str, eval_id: str) -> tuple[dict, dict]:
    eval_file = REPO_ROOT / "skills" / skill / "evals" / "output" / "evals.json"
    data = json.loads(eval_file.read_text(encoding="utf-8"))
    for case in data.get("cases", []):
        if case["id"] == eval_id:
            expected_path = eval_file.parent / case["expected"]
            return case, json.loads(expected_path.read_text(encoding="utf-8"))
    raise KeyError(f"unknown eval id for {skill}: {eval_id}")


def load_skill_runtime_policy(skill: str) -> dict | None:
    eval_file = (
        REPO_ROOT / "skills" / skill / "evals" / "output" / "evals.json"
    )
    data = json.loads(eval_file.read_text(encoding="utf-8"))
    if data.get("skill") != skill:
        raise ValueError(f"output eval manifest skill does not match: {skill}")
    policy = data.get("skill_runtime_verification")
    if policy is not None and not isinstance(policy, dict):
        raise ValueError("skill_runtime_verification must be a JSON object")
    return policy


def grade(
    skill: str,
    eval_id: str,
    output_path: Path,
    *,
    runtime_source_root: Path | None = None,
    expected_override: dict | None = None,
) -> dict:
    if expected_override is None:
        _, expected = load_eval_definition(skill, eval_id)
    else:
        expected = expected_override
    text = output_path.read_text(encoding="utf-8")
    try:
        result = VALIDATORS[skill](text, expected, eval_id)
    except MarkdownTableParseError as exc:
        result = EvalResult(skill, eval_id)
        result.add(
            "OUTPUT-MD-TABLE-001",
            False,
            "成果物のMarkdown表を安全に解析できること",
            evidence={"error": str(exc)},
        )
    validate_runtime_evidence(text, expected, result, source_root=runtime_source_root)
    content_status = result.status
    try:
        policy = load_skill_runtime_policy(skill)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        policy = None
        runtime_verification = {
            "status": "execution error",
            "valid": None,
            "reason": f"skill_runtime_policy_unavailable:{type(exc).__name__}",
        }
    else:
        runtime_verification = None
    if policy is not None:
        runtime_verification = validate_skill_local_runtime_evidence(
            text,
            skill,
            eval_id,
            policy,
            result,
            source_root=runtime_source_root,
        )
    elif runtime_verification is None:
        runtime_verification = {"status": "not_required", "valid": None}
    payload = result.to_dict()
    if policy is not None or runtime_verification["status"] == "execution error":
        payload["content_status"] = content_status
        payload["runtime_verification"] = runtime_verification
    if runtime_verification["status"] == "execution error":
        payload["status"] = "execution error"
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic output evals against saved Agent outputs."
    )
    parser.add_argument("--skill", required=True, choices=[*sorted(VALIDATORS), "all"])
    parser.add_argument("--eval-id", help="Eval ID for single-skill mode")
    parser.add_argument(
        "--output", type=Path, help="Generated Markdown output for single-skill mode"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="All-mode directory containing <skill>/<eval-id>.md",
    )
    parser.add_argument(
        "--runtime-source-root",
        type=Path,
        help="Trusted source checkout used to verify runtime implementation fingerprints",
    )
    parser.add_argument(
        "--expected-json",
        type=Path,
        help="Private expected JSON for a held-out single case outside the tracked manifest",
    )
    parser.add_argument("--result", type=Path, help="Optional JSON result output path")
    args = parser.parse_args()

    if args.expected_json and args.skill == "all":
        parser.error("--expected-json is supported only for a single-skill case")
    expected_override = None
    if args.expected_json:
        try:
            expected_override = json.loads(
                args.expected_json.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            parser.error(f"--expected-json is unreadable or invalid: {exc}")
        if not isinstance(expected_override, dict):
            parser.error("--expected-json must contain a JSON object")

    results: list[dict] = []
    missing_outputs: list[str] = []

    if args.skill != "all":
        if not args.eval_id or not args.output:
            parser.error("--eval-id and --output are required unless --skill all")
        results.append(
            grade(
                args.skill,
                args.eval_id,
                args.output,
                runtime_source_root=args.runtime_source_root,
                expected_override=expected_override,
            )
        )
        payload = results[0]
    else:
        if not args.output_root:
            parser.error("--output-root is required with --skill all")
        for skill in sorted(VALIDATORS):
            eval_file = REPO_ROOT / "skills" / skill / "evals" / "output" / "evals.json"
            data = json.loads(eval_file.read_text(encoding="utf-8"))
            for case in data.get("cases", []):
                relative = f"{skill}/{case['id']}.md"
                output = args.output_root / relative
                if output.is_file():
                    results.append(
                        grade(
                            skill,
                            case["id"],
                            output,
                            runtime_source_root=args.runtime_source_root,
                        )
                    )
                else:
                    missing_outputs.append(relative)
        if any(result["status"] == "execution error" for result in results):
            aggregate_status = "execution error"
        elif missing_outputs or any(result["status"] == "fail" for result in results):
            aggregate_status = "fail"
        else:
            aggregate_status = "pass"
        payload = {
            "status": aggregate_status,
            "missing_outputs": missing_outputs,
            "results": results,
        }

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if payload.get("status") == "execution error":
        return 2
    return 1 if payload.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
