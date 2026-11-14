"""Prepare and finish a semantic re-evaluation with separated Agent sessions.

``prepare``: builds a Skill snapshot without ``evals``/``tests`` (so a candidate
Agent cannot see rubrics, references or expectations) and, per case, a candidate
prompt that contains only the Eval Input.

``judge-prompt``: after a candidate output exists, writes the repository's own
Judge prompt (rubric, reference, input, candidate) for a *separate* Judge session.

``finish``: feeds the saved Judge response through ``scripts/skills/evals/semantic/run.py``
(the repository runtime computes every status and the overall verdict).
"""

# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO))

from scripts.skills.evals.semantic.loader import load_semantic_case
from scripts.skills.evals.semantic.prompt_builder import build_judge_prompt

SKILL_OF = {
    "RISK": "test-analysis",
    "E2E-SEL": "e2e-test-selection",
    "COV": "coverage-analysis",
    "TC": "test-case-design",
    "TCN": "test-condition-design",
}


def skill_for(eval_id: str) -> str:
    prefix = eval_id.rsplit("-SEM-", 1)[0]
    return SKILL_OF[prefix]


def prepare(root: Path, eval_ids: list[str]) -> None:
    snapshot = root / "snapshot" / "skills"
    if snapshot.exists():
        shutil.rmtree(snapshot.parent)
    shutil.copytree(
        REPO / "skills",
        snapshot,
        ignore=shutil.ignore_patterns("evals", "tests", "__pycache__"),
    )
    for eval_id in eval_ids:
        skill = skill_for(eval_id)
        dataset, case = load_semantic_case(skill, eval_id)
        folder = root / "cases" / eval_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "eval-input.md").write_text(case["input_text"], encoding="utf-8")
        (folder / "candidate-prompt.md").write_text(
            f"""あなたは評価対象Skill `{skill}` を使うAgentです。

1. 次のSkill packageだけを読んで使います: `{snapshot / skill}`（SKILL.mdから読み、必要なreferences／assets／scriptsを読みます）。必要な他のSkillは `{snapshot}` 配下にあります。
2. このprojectの他のfile（特にevals、reference、rubric、期待値、docs）は読みません。
3. 評価入力は `{folder / "eval-input.md"}` です。Skillの出力契約に従う成果物を作ります。Skillがruntime（scripts）の使用を求める場合は、実際に実行して結果を使います。実行できない・入力が足りない場合は、推測で補わずSkillの停止条件に従います。
4. 成果物のMarkdown全文を `{folder / "candidate-output.md"}` へ書き込みます。最終返信には、書き込んだこと、実行したruntimeの要約、判断に迷った点だけを短く書きます。
""",
            encoding="utf-8",
        )


def judge_prompt(root: Path, eval_id: str) -> None:
    skill = skill_for(eval_id)
    dataset, case = load_semantic_case(skill, eval_id)
    folder = root / "cases" / eval_id
    criteria = [dataset["criteria_by_id"][c] for c in case["criteria"]]
    prompt = build_judge_prompt(
        criteria=criteria,
        eval_input=case["input_text"],
        reference=case["reference_text"],
        candidate_output=(folder / "candidate-output.md").read_text(encoding="utf-8"),
    )
    (folder / "judge-prompt.md").write_text(prompt, encoding="utf-8")


def finish(root: Path, eval_id: str) -> int:
    skill = skill_for(eval_id)
    folder = root / "cases" / eval_id
    response = folder / "judge-response.json"
    adapter = folder / "replay_judge.py"
    adapter.write_text(
        "import sys\nsys.stdin.read()\n"
        f"sys.stdout.write(open({str(response)!r}, encoding='utf-8').read())\n",
        encoding="utf-8",
    )
    done = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/skills/evals/semantic/run.py"),
            "--skill",
            skill,
            "--eval-id",
            eval_id,
            "--output",
            str(folder / "candidate-output.md"),
            "--judge-command",
            sys.executable,
            str(adapter),
        ],
        capture_output=True,
        text=True,
    )
    (folder / "result.json").write_text(done.stdout, encoding="utf-8")
    verdict = json.loads(done.stdout)["verdict"] if done.stdout.strip() else "error"
    print(f"{eval_id}: {verdict}")
    return done.returncode


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("command", choices=["prepare", "judge-prompt", "finish"])
    cli.add_argument("--root", type=Path, required=True)
    cli.add_argument("--eval-id", action="append", default=[])
    args = cli.parse_args()
    if args.command == "prepare":
        prepare(args.root, args.eval_id)
        return 0
    status = 0
    for eval_id in args.eval_id:
        if args.command == "judge-prompt":
            judge_prompt(args.root, eval_id)
        else:
            status = max(status, finish(args.root, eval_id))
    return 0 if args.command == "judge-prompt" else status


if __name__ == "__main__":
    raise SystemExit(main())
