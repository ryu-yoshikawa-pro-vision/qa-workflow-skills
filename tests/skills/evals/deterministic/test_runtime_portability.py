from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]

VALID_RISK_OUTPUT = """# テスト分析
## Product Risk一覧
| リスクID | 製品上のリスク / 失敗 | 関連Current Effective Authority / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 |
| --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | 誤保存 | SPEC-001 / CHG-001 | 4 | 2 | 高 | 保存処理の全面変更 |
## 選択したテスト技法
| テスト技法 | 適用領域 | 選択理由 |
| --- | --- | --- |
| 状態遷移 | 保存 | 状態を持つ保存フローを確認するため |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル |
| --- | --- | --- | --- | --- |
| 保存 | 可 | 可 | 可 | システム |
"""


class RuntimePortabilityTests(unittest.TestCase):
    def test_single_skill_copy_runs_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(REPO_ROOT / "skills" / "test-analysis", root / "skills" / "test-analysis")
            shutil.copytree(REPO_ROOT / "scripts" / "skills" / "evals", root / "scripts" / "skills" / "evals")

            self.assertFalse((root / "scripts" / "__init__.py").exists())
            self.assertFalse((root / "scripts" / "skills" / "__init__.py").exists())
            self.assertEqual([path.name for path in (root / "skills").iterdir()], ["test-analysis"])

            output_path = root / "valid-output.md"
            output_path.write_text(VALID_RISK_OUTPUT, encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/skills/evals/deterministic/run.py",
                    "--skill",
                    "test-analysis",
                    "--eval-id",
                    "RISK-OUT-001",
                    "--output",
                    str(output_path),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "pass")


if __name__ == "__main__":
    unittest.main()
