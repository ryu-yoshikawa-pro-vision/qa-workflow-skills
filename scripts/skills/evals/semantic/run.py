from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from scripts.skills.evals.semantic.loader import SKILLS_ROOT, load_semantic_case
    from scripts.skills.evals.semantic.prompt_builder import build_judge_prompt
    from scripts.skills.evals.semantic.result import normalize_judge_response
else:
    from .loader import SKILLS_ROOT, load_semantic_case
    from .prompt_builder import build_judge_prompt
    from .result import normalize_judge_response


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a saved Agent output with a Semantic Eval judge command.")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--eval-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--skills-root", type=Path, default=SKILLS_ROOT)
    parser.add_argument(
        "--judge-command",
        nargs=argparse.REMAINDER,
        required=True,
        help="Judge command argv. This option must be last.",
    )
    args = parser.parse_args()

    try:
        if not args.judge_command:
            raise ValueError("--judge-command requires at least one command argument")
        if not args.output.is_file():
            raise FileNotFoundError(args.output)

        dataset, case = load_semantic_case(args.skill, args.eval_id, args.skills_root)
        selected_criteria = [dataset["criteria_by_id"][criterion_id] for criterion_id in case["criteria"]]
        candidate_output = args.output.read_text(encoding="utf-8")
        prompt = build_judge_prompt(
            criteria=selected_criteria,
            eval_input=case["input_text"],
            reference=case["reference_text"],
            candidate_output=candidate_output,
        )

        completed = subprocess.run(
            args.judge_command,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            diagnostic = completed.stderr.strip()
            suffix = f": {diagnostic}" if diagnostic else ""
            raise RuntimeError(f"judge command failed with exit code {completed.returncode}{suffix}")

        result = normalize_judge_response(
            completed.stdout,
            skill=args.skill,
            eval_id=args.eval_id,
            requested_criteria=case["criteria"],
            criteria_by_id=dataset["criteria_by_id"],
        )
    except Exception as exc:
        print(f"semantic eval error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
