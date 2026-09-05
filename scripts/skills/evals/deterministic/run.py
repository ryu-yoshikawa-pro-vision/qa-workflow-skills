from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from scripts.skills.evals.deterministic.loader import load_validators
else:
    from .loader import load_validators

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


def grade(skill: str, eval_id: str, output_path: Path) -> dict:
    _, expected = load_eval_definition(skill, eval_id)
    text = output_path.read_text(encoding="utf-8")
    result = VALIDATORS[skill](text, expected, eval_id)
    return result.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic output evals against saved Agent outputs.")
    parser.add_argument("--skill", required=True, choices=[*sorted(VALIDATORS), "all"])
    parser.add_argument("--eval-id", help="Eval ID for single-skill mode")
    parser.add_argument("--output", type=Path, help="Generated Markdown output for single-skill mode")
    parser.add_argument("--output-root", type=Path, help="All-mode directory containing <skill>/<eval-id>.md")
    parser.add_argument("--result", type=Path, help="Optional JSON result output path")
    args = parser.parse_args()

    results: list[dict] = []
    missing_outputs: list[str] = []

    if args.skill != "all":
        if not args.eval_id or not args.output:
            parser.error("--eval-id and --output are required unless --skill all")
        results.append(grade(args.skill, args.eval_id, args.output))
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
                    results.append(grade(skill, case["id"], output))
                else:
                    missing_outputs.append(relative)
        payload = {
            "status": "fail"
            if missing_outputs or any(r["status"] == "fail" for r in results)
            else "pass",
            "missing_outputs": missing_outputs,
            "results": results,
        }

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if payload.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
