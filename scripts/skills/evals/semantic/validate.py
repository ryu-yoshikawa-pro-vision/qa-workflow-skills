from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from scripts.skills.evals.semantic.loader import SKILLS_ROOT, discover_semantic_skills, load_semantic_skill
else:
    from .loader import SKILLS_ROOT, discover_semantic_skills, load_semantic_skill


def validate_skills_root(skills_root: Path) -> tuple[int, int]:
    skills = discover_semantic_skills(skills_root)
    total_cases = 0
    for skill in skills:
        dataset = load_semantic_skill(skill, skills_root)
        total_cases += len(dataset["cases"])
    return len(skills), total_cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Semantic Output Eval datasets.")
    parser.add_argument("--skills-root", type=Path, default=SKILLS_ROOT)
    args = parser.parse_args()
    try:
        skill_count, case_count = validate_skills_root(args.skills_root)
    except Exception as exc:
        print(f"semantic dataset validation error: {exc}", file=sys.stderr)
        return 1
    print(f"Semantic eval skills: {skill_count}")
    print(f"Semantic eval cases: {case_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
