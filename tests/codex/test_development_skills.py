"""Repository-local contracts for the three development Agent Skills."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
EXPECTED = {"feature-plan", "code-review", "repair-loop"}
SOURCE_SPECIFIC = re.compile(
    r"\b(?:Run Artifact|Run Manifest|Repository mapping|Scenario Shop|Expo|Android|codex-task)\b",
    re.IGNORECASE,
)


class DevelopmentSkillTests(unittest.TestCase):
    def test_only_three_repository_owned_development_skills_exist(self) -> None:
        actual = {path.name for path in SKILLS.iterdir() if path.is_dir()}
        self.assertEqual(actual, EXPECTED)

    def test_frontmatter_and_all_local_markdown_references_resolve(self) -> None:
        for name in sorted(EXPECTED):
            with self.subTest(skill=name):
                skill_dir = SKILLS / name
                skill_file = skill_dir / "SKILL.md"
                text = skill_file.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"), skill_file)
                frontmatter = text.split("---", 2)[1]
                self.assertRegex(frontmatter, rf"(?m)^name:\s*{re.escape(name)}\s*$")
                self.assertRegex(frontmatter, r"(?m)^description:\s*\S")
                for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                    if link.startswith(("http://", "https://", "mailto:")):
                        continue
                    target = link.split("#", 1)[0].split("?", 1)[0]
                    if target:
                        self.assertTrue((skill_dir / target).resolve().is_file(), link)

    def test_skill_specific_references_and_responsibility_boundaries(self) -> None:
        expected_references = {
            "feature-plan": {
                "references/planning-workflow.md",
                "assets/plan-template.md",
            },
            "code-review": {"references/review-workflow.md"},
            "repair-loop": {"references/repair-workflow.md"},
        }
        forbidden_by_skill = {
            "feature-plan": (
                "Do not implement during planning",
                "Plan-only requests may update the plan document only",
            ),
            "code-review": (
                "Review only",
                "Do not modify files during review-only work",
            ),
            "repair-loop": (
                "Repair only supplied findings",
                "at most three repair passes",
            ),
        }
        for name in sorted(EXPECTED):
            with self.subTest(skill=name):
                directory = SKILLS / name
                files = {
                    path.relative_to(directory).as_posix()
                    for path in directory.rglob("*")
                    if path.is_file()
                }
                self.assertTrue(expected_references[name] <= files)
                text = "\n".join(
                    path.read_text(encoding="utf-8") for path in directory.rglob("*.md")
                )
                for contract in forbidden_by_skill[name]:
                    self.assertIn(contract, text)
                self.assertIsNone(SOURCE_SPECIFIC.search(text))

    def test_development_skills_do_not_enter_the_qa_skill_catalog(self) -> None:
        qa_skills = {
            path.name
            for path in (ROOT / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
        self.assertTrue(qa_skills)
        self.assertTrue(EXPECTED.isdisjoint(qa_skills))
        self.assertFalse((ROOT / "skills" / "feature-plan").exists())
        self.assertFalse((ROOT / "skills" / "code-review").exists())
        self.assertFalse((ROOT / "skills" / "repair-loop").exists())


if __name__ == "__main__":
    unittest.main()
