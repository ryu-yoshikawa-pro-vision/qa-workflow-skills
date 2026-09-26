from __future__ import annotations

import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_SKILLS = (
    "spec-analysis",
    "test-analysis",
    "test-requirement-design",
    "test-condition-design",
    "test-case-design",
    "coverage-analysis",
    "qa-workflow",
)

REPRESENTATIVES = (
    ("spec-analysis", "authority_entities.py", "authority_entities", None),
    ("test-analysis", "analysis_entities.py", "analysis_entities", "artifact:analysis_entities:all"),
    ("test-requirement-design", "requirement_structure.py", "requirement_structure", "artifact:requirement_structure:all"),
    ("test-condition-design", "condition_structure.py", "condition_structure", "artifact:condition_structure:all"),
    ("test-case-design", "case_structure.py", "case_structure", "artifact:case_structure:all"),
    ("coverage-analysis", "traceability.py", "traceability", "artifact:traceability:all"),
    ("qa-workflow", "workflow_runtime.py", "workflow_runtime", "artifact:workflow_runtime:all"),
)


def _runtime_metadata(skill: str, unit: str) -> dict:
    bare_unit = unit.split(":", 2)[1] if unit.startswith("artifact:") else unit
    contracts = {
        "analysis_entities": "analysis-entities-v1",
        "requirement_structure": "requirement-structure-v1",
        "condition_structure": "condition-structure-v1",
        "case_structure": "case-structure-v1",
        "traceability": "traceability-v1",
        "workflow_runtime": "workflow-runtime-v1",
    }
    scope_key = None if bare_unit == "case_structure" else "all"
    input_mode = "artifact" if bare_unit in {"traceability", "workflow_runtime"} else "direct"
    return {
        "envelope_version": "1",
        "skill": skill,
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": contracts[bare_unit],
        "runtime_unit_key": unit,
        "model_key": None,
        "model_type": None,
        "technique_slug": None,
        "selection_source": None,
        "selection_key": None,
        "scope_key": scope_key,
        "input_mode": input_mode,
        "upstream_entities": [],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": [],
        "reference_refs": [],
    }


class RuntimePortabilityTests(unittest.TestCase):
    def test_all_skill_local_contracts_are_byte_identical(self) -> None:
        paths = [REPO_ROOT / "skills" / skill / "scripts" / "runtime_contract.py" for skill in RUNTIME_SKILLS]
        self.assertTrue(all(path.is_file() for path in paths))
        self.assertEqual(len({path.read_bytes() for path in paths}), 1)

    def test_generators_have_no_repo_local_import_other_than_runtime_contract(self) -> None:
        allowed = set(getattr(sys, "stdlib_module_names", ())) | {"runtime_contract"}
        for skill in RUNTIME_SKILLS:
            for path in (REPO_ROOT / "skills" / skill / "scripts").glob("*.py"):
                if path.name == "runtime_contract.py":
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = [alias.name.split(".", 1)[0] for alias in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        names = [node.module.split(".", 1)[0]]
                    else:
                        continue
                    for name in names:
                        self.assertIn(name, allowed, f"{path}: {name}")

    def test_each_skill_package_runs_representative_runtime_from_single_copy(self) -> None:
        for skill, script_name, fixture_name, runtime_unit in REPRESENTATIVES:
            with self.subTest(skill=skill):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    copied_skill = root / "skills" / skill
                    shutil.copytree(REPO_ROOT / "skills" / skill, copied_skill)
                    fixture = json.loads(
                        (REPO_ROOT / "tests" / "skills" / "runtime" / "fixtures" / fixture_name / "valid_minimal.json").read_text(encoding="utf-8")
                    )
                    if runtime_unit is None:
                        request = fixture
                    else:
                        request = {"metadata": _runtime_metadata(skill, runtime_unit), "input": fixture}
                    completed = subprocess.run(
                        [sys.executable, str(copied_skill / "scripts" / script_name)],
                        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=copied_skill,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", "replace"))
                    self.assertEqual(completed.stderr, b"")
                    result = json.loads(completed.stdout)
                    if runtime_unit is None:
                        self.assertEqual(result["skill"], skill)
                    else:
                        self.assertEqual(result["runtime_unit_key"], runtime_unit)
                        if skill == "qa-workflow":
                            self.assertEqual(result["runtime_status"], "invalid_input")
                        else:
                            self.assertIn(result["runtime_status"], {"ok", "unsupported"})


if __name__ == "__main__":
    unittest.main()
