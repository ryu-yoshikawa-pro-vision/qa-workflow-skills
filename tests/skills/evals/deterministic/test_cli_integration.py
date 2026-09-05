from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
RUNNER = REPO_ROOT / "scripts" / "skills" / "evals" / "deterministic" / "run.py"

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


class CliIntegrationTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_single_valid_output_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "valid.md"
            path.write_text(VALID_RISK_OUTPUT, encoding="utf-8")
            completed = self.run_cli("--skill", "test-analysis", "--eval-id", "RISK-OUT-001", "--output", str(path))
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["status"], "pass")

    def test_single_invalid_output_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.md"
            path.write_text(VALID_RISK_OUTPUT.replace("| 4 | 2 | 高 |", "| 4 | 2 | 中 |"), encoding="utf-8")
            completed = self.run_cli("--skill", "test-analysis", "--eval-id", "RISK-OUT-001", "--output", str(path))
            self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["status"], "fail")

    def test_all_mode_missing_output_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = self.run_cli("--skill", "all", "--output-root", tmp)
            self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "fail")
            self.assertTrue(payload["missing_outputs"])


if __name__ == "__main__":
    unittest.main()
