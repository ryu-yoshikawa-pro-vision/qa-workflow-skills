from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.skills.evals.deterministic.loader import load_validators


VALIDATORS = load_validators()
REPO_ROOT = Path(__file__).resolve().parents[4]


def assertion_ids(result: dict, status: str = "fail") -> set[str]:
    return {item["id"] for item in result["assertions"] if item["status"] == status}


class E2EContractTests(unittest.TestCase):
    def assert_pass(self, skill: str, text: str, expected: dict) -> None:
        result = VALIDATORS[skill](text, expected, "E2E-UNIT").to_dict()
        self.assertEqual(result["status"], "pass", result)

    def assert_fails(self, skill: str, text: str, expected: dict, assertion_id: str) -> None:
        result = VALIDATORS[skill](text, expected, "E2E-UNIT").to_dict()
        self.assertIn(assertion_id, assertion_ids(result), result)

    def inspection_output(self, *, tc_free: bool = False) -> str:
        tc_id = "" if tc_free else "TC-101"
        return f"""# E2E対象inspection
## 対象決定
| E2E対象 / 識別子 | TC ID（存在時のみ） | E2E実装参照 | 決定根拠 | 扱い |
| --- | --- | --- | --- | --- |
| login flow | {tc_id} | tests/auth/login.spec.ts > login succeeds | 明示対象と既存構成 | 新規E2E実装 |
## repo / 実対象の確認元・鮮度
| 項目 | 値 | 確認元 | 確認日時 / commit |
| --- | --- | --- | --- |
| branch | feat/e2e | repo | 2026-09-12 |
| commit | abc123 | repo | 2026-09-12 |
| working tree | clean | repo | 2026-09-12 |
| 対象repo / workspace | app | repo | 2026-09-12 |
| テスト環境URL / origin | https://app.test | 実対象 | 2026-09-12 |
| 実対象確認日時 | 2026-09-12T10:00+09:00 | 実対象 | 2026-09-12 |
| version / build ID | build-1 | 実対象 | 2026-09-12 |
## 実装・実行に影響する事実
| 事実 | 内容 | 確認元 | 実装 / 実行への影響 |
| --- | --- | --- | --- |
| Playwright構成 / 実行入口 | playwright.config.ts / npm test:e2e | repo | 既存入口を再利用 |
| spec / fixture / helper / Page Object | tests/auth/login.spec.ts | repo | 既存helperを再利用 |
| 認証・データ・開始状態 | test user / clean account | repo | login前状態 |
| locator / 観測方法 | data-testid / URL | 実対象 | 安定参照 |
| 実効設定・reporter・証跡 | chromium / json reporter | repo | result artifact |
## 安全条件・準備・cleanup
| 条件 | 状態 | 根拠 / 許可 | 実行主体 / cleanup制約 |
| --- | --- | --- | --- |
| URL / origin | 許可済み | ユーザー提供情報 | execution |
| 副作用 | テストデータのみ | ユーザー提供情報 | runner cleanup |
| run外の準備 | test user準備済み | repo | 秘密情報を出力しない |
| runner管理setup / cleanup | 確認済み | repo | runner管理 |
| 証跡・認証状態 | local artifactのみ | repo | 共有不可 |
## 既存E2Eとの関係
| 対象 | 扱い | 既存E2E実装参照 | 根拠 / 備考 |
| --- | --- | --- | --- |
| login flow | 新規E2E実装 |  | 既存対象なし |
## 実装可否・未確認・ブロック
| 範囲 | 実装可否 / 状態 | 理由 | 次の担当 |
| --- | --- | --- | --- |
| login flow | 実装可能 | 必要事実が確認済み | e2e-test-implementation |
"""

    def implementation_output(self, *, tc_free: bool = False) -> str:
        tc_id = "" if tc_free else "TC-101"
        return f"""# E2Eテスト実装
## 実装対象
| E2E対象 / 識別子 | TC ID（存在時のみ） | 明示対象 / 既存E2E参照 | 確認済み期待挙動 | 扱い |
| --- | --- | --- | --- | --- |
| login flow | {tc_id} | tests/auth/login.spec.ts > login succeeds | dashboardが表示される | 新規実装 |
## 実装前の状態
| 項目 | 値 | 確認元 |
| --- | --- | --- |
| branch | feat/e2e | repo |
| HEAD commit | abc123 | repo |
| working tree | clean | repo |
| 変更予定ファイルとの競合 | なし | repo |
| inspectionからの差分 | なし | repo |
## E2E実装参照
| E2E実装参照 | test file | Playwright title path | TC ID（存在時のみ） | 扱い |
| --- | --- | --- | --- | --- |
| tests/auth/login.spec.ts > login succeeds | tests/auth/login.spec.ts | login succeeds | {tc_id} | 新規実装 |
## 変更・再利用したファイル
| ファイル | 変更内容 / 再利用理由 | inspection事実との対応 |
| --- | --- | --- |
| tests/auth/login.spec.ts | login testを追加 | data-testid |
## 静的・軽量検証
| 検証 | 実行command / 条件 | 結果 | 非破壊確認 / 未実施理由 |
| --- | --- | --- | --- |
| lint / typecheck / discovery | npm run lint | PASS | 実E2Eではない |
## inspection差分・ブロック・要再検証
| 範囲 | 状態 | 理由 / 影響 | 次の担当 |
| --- | --- | --- | --- |
| login flow | なし |  | e2e-test-execution |
"""

    def execution_output(self, *, tc_free: bool = False) -> str:
        tc_suffix = "" if tc_free else " / TC-101"
        return f"""# E2Eテスト実行
## 実行条件
| 項目 | 値 | 確認元 | raw fact / 導出値 |
| --- | --- | --- | --- |
| 対象URL / origin | https://app.test | 実対象 | raw fact |
| 実行入口 / command chain | npm run test:e2e | repo | raw fact |
| Playwright project | chromium | repo | raw fact |
| retries / repeatEach / workers / parallel | 1 / 1 / 1 / false | repo | raw fact |
| setup / dependency / webServer / teardown | runner / none / webServer設定あり / runner | repo | raw fact |
| run外準備 | 対象なし | repo | raw fact |
| 必要な認証 / テストデータ / 開始状態 | test user / clean account | repo | raw fact |
| 副作用の許可範囲 / 最大回数 | test data only / max 1 | ユーザー提供情報 | raw fact |
| cleanup方法 | runner teardown / run外なし | repo | raw fact |
| branch / HEAD / working tree | feat/e2e / abc123 / clean | repo | raw fact |
| テスト対象version / build ID | build-1 | 実対象 | raw fact |
## Playwright run結果
| 項目 | 値 | 確認元 | raw fact / 導出値 |
| --- | --- | --- | --- |
| Playwright run全体status | passed | reporter | raw fact |
| CLI process exit code | 0 | process | raw fact |
| run-level / global error | なし | reporter | raw fact |
| runner開始 | はい | execution | raw fact |
| result artifactの今回run生成・更新 | はい | filesystem | raw fact |
## webServer process ownership
| server識別子 | 起動状態 | 今回run所有か | 既存 / 再利用か | cleanup対象か | 根拠 |
| --- | --- | --- | --- | --- | --- |
| app | 今回runが起動 | 今回runが所有 | 新規起動 | 対象 | Playwright webServer |
## logical primary対象の解決
| 論理的な要求primary対象 | E2E実装参照 / TC ID（存在時のみ） | resolved primary TestCase数 | 未実行 / 解決不能理由 |
| --- | --- | ---: | --- |
| login-flow | tests/auth/login.spec.ts > login succeeds{tc_suffix} | 1 |  |
## resolved primary TestCase結果
| resolved primary TestCase参照 | 論理要求primary対象 | test file / title path | project | repeatEachIndex | 実行開始 | 結果 / 未実行理由 |
| --- | --- | --- | --- | --- | --- | --- |
| result-1 | login-flow | tests/auth/login.spec.ts > login succeeds | chromium | 0 | 開始 | passed |
## attempt結果（retryをresolved件数へ加算しない）
| resolved primary TestCase参照 | attempt番号 | 実行区分 | status | expectedStatus | outcome | retry番号 | duration | error / errors |
| --- | ---: | --- | --- | --- | --- | ---: | --- | --- |
| result-1 | 1 | 要求primary test | passed | passed | expected | 0 | 10ms |  |
## working tree・証跡
| 項目 | 実行前 | 実行後 | 今回runの変更 / 安全確認 |
| --- | --- | --- | --- |
| working tree | clean | clean | 変更なし |
| output / report / snapshot / source | なし | result.json | 今回run |
| trace / screenshot / video / HTML report / network / storageState | なし | trace.zip | secretなし |
| stale artifactの今回結果利用 | なし | なし | 利用していない |
## cleanup・残存副作用
| cleanup対象 / 実行主体 | 状態 | 結果 / 残存副作用 | 確認元 |
| --- | --- | --- | --- |
| runner管理 | 成功 | 残存なし | reporter |
| run外処理 | 対象なし | run外準備なし | execution |

- 実行成果物状態: 完了
- ブロック中: なし
"""

    def analysis_output(self, *, tc_free: bool = False) -> str:
        tc_row = "" if tc_free else "| TC ID（存在時のみ） | TC-101 | execution.md |\n"
        return f"""# E2Eテスト結果分析
## 分析対象・実行事実
| 項目 | 値 | 参照 |
| --- | --- | --- |
| E2E対象 / logical primary | login-flow | execution.md |
| E2E実装参照 | tests/auth/login.spec.ts > login succeeds | implementation.md |
{tc_row}| resolved primary TestCase / 実行結果参照 | result-1 | execution.md |
| Playwright status / outcome / expectedStatus | passed / expected / passed | result-1 |
| run全体status / process exit code / run-level error | passed / 0 / なし | execution.md |
| cleanup状態 / 残存副作用 | 未確認 / なし | execution.md |
## 判定
| 対象参照 | 判定状態 | 原因 | 再現性 | 根拠 |
| --- | --- | --- | --- | --- |
| result-1 | 判定可能 | 異常なし | 未確認 | execution.md |
## 不足証拠・追加実行要求
| 追加実行の必要性 | 取得したい証拠 | 検証する仮説 | 必要な実行範囲 | 実行担当 |
| --- | --- | --- | --- | --- |
| 必要 | cleanup確認ログ | cleanupが成功しているか | cleanupのみ | e2e-test-execution |
## 修正routing・要再検証
| 判定 / 不足 | 修正先Skill | 対象 / 実行範囲 | 要再検証範囲 | 理由 |
| --- | --- | --- | --- | --- |
| cleanup未確認 | e2e-test-execution | cleanup | cleanup確認 | 証拠不足 |
## 検出事項として報告可能な内容
| 内容 | 判定状態 | 根拠 / 証跡参照 | 残存リスク |
| --- | --- | --- | --- |
| cleanup確認待ち | 確認不能 | execution.md | 未確認 |
"""

    def reporting_output(self, *, tc_free: bool = False) -> str:
        tc_id = "" if tc_free else "TC-101"
        return f"""# E2Eテスト結果報告
## 対象・環境
| 項目 | 値 | 参照 / 確認元 |
| --- | --- | --- |
| 対象機能 / 範囲 | login | inspection.md |
| テスト環境URL / origin | https://app.test | 実対象 |
| テスト対象version / build ID | build-1 | 実対象 |
| E2Eコードbranch / commit / working tree | feat/e2e / abc123 / clean | repo |
| 実行日時 / Playwright project | 2026-09-12 / chromium | reporter |
## run全体結果
| 項目 | 値 | 確認元 | raw fact / 導出値 |
| --- | --- | --- | --- |
| Playwright run全体status | passed | reporter | raw fact |
| process exit code | 0 | process | raw fact |
| run-level / global error | なし | reporter | raw fact |
## primary対象集計（単位を混同しない）
| 論理的な要求primary対象 | E2E実装参照 | TC ID（存在時のみ） | resolved primary TestCase数 | 実際に開始したresolved primary TestCase数 | 未実行logical理由 | 未実行resolved理由 |
| --- | --- | --- | ---: | ---: | --- | --- |
| login-flow | tests/auth/login.spec.ts > login succeeds | {tc_id} | 1 | 1 |  |  |
## resolved primary結果 / attempt結果
| 論理的な要求primary対象 | resolved primary TestCase参照 | 実行開始 | 結果 | 未実行理由 | expectedStatus | outcome | retry attempt数（別集計） | 初回 / retry履歴 | 実行結果参照 |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| login-flow | result-1 | 開始 | passed |  | passed | expected | 1 | passed (retry 0) | result-1 |
## TC・E2E・実行・分析追跡
| TC ID（存在時のみ） | E2E実装参照 | resolved primary TestCase / 実行結果参照 | 分析結果参照 | 報告上の扱い |
| --- | --- | --- | --- | --- |
| {tc_id} | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |
## cleanup・証跡・残存リスク
| 項目 | 状態 / 内容 | 安全な参照 |
| --- | --- | --- |
| cleanup | 成功 | execution.md |
| 残存副作用 | なし | execution.md |
| 証跡 | trace.zip / secretなし | local artifact |
| ブロック中 / 未解決事項 / 残存リスク | なし | analysis.md |
"""

    def test_new_e2e_skill_valid_outputs_and_negative_contracts(self):
        inspection = self.inspection_output()
        self.assert_pass(
            "e2e-test-inspection",
            inspection,
            {
                "required_tc_ids": ["TC-101"],
                "required_e2e_refs": ["tests/auth/login.spec.ts > login succeeds"],
                "required_fact_labels": ["Playwright構成 / 実行入口", "認証・データ・開始状態"],
            },
        )
        self.assert_fails(
            "e2e-test-inspection",
            self.inspection_output().replace("TC-101", "TC-999"),
            {"required_tc_ids": ["TC-101"]},
            "E2E-INSP-D010",
        )

        implementation = self.implementation_output()
        self.assert_pass(
            "e2e-test-implementation",
            implementation,
            {
                "required_tc_ids": ["TC-101"],
                "required_e2e_refs": ["tests/auth/login.spec.ts > login succeeds"],
                "require_no_e2e_execution": True,
            },
        )
        self.assert_pass(
            "e2e-test-implementation",
            implementation + "\nPlaywrightを実行しません。",
            {"require_no_e2e_execution": True},
        )
        self.assert_fails(
            "e2e-test-implementation",
            implementation + "\nPlaywrightを実行します。",
            {"require_no_e2e_execution": True},
            "E2E-IMPL-D013",
        )
        self.assert_fails(
            "e2e-test-implementation",
            implementation.replace("tests/auth/login.spec.ts > login succeeds", "C:\\repo\\login.spec.ts > login succeeds"),
            {},
            "E2E-IMPL-D005",
        )

        execution = self.execution_output()
        self.assert_pass(
            "e2e-test-execution",
            execution,
            {"expected_logical_primary_count": 1, "expected_resolved_primary_count": 1},
        )
        self.assert_fails(
            "e2e-test-execution",
            execution.replace("| login-flow | tests/auth/login.spec.ts > login succeeds / TC-101 | 1 |", "| login-flow | tests/auth/login.spec.ts > login succeeds / TC-101 | 0 |"),
            {"expected_logical_primary_count": 1, "expected_resolved_primary_count": 1},
            "E2E-EXEC-D008",
        )
        retry_execution = execution.replace(
            "| result-1 | 1 | 要求primary test | passed | passed | expected | 0 | 10ms |  |",
            "| result-1 | 1 | 要求primary test | failed | passed | unexpected | 0 | 10ms | first failure |\n| result-1 | 2 | 要求primary test | passed | passed | flaky | 1 | 8ms | retry success |",
        )
        retry_expected = {
            "expected_logical_primary_count": 1,
            "expected_resolved_primary_count": 1,
            "expected_attempts": [
                {"resolved_ref": "result-1", "attempt_no": 1, "status": "failed", "retry_no": 0},
                {"resolved_ref": "result-1", "attempt_no": 2, "status": "passed", "retry_no": 1},
            ],
        }
        self.assert_pass("e2e-test-execution", retry_execution, retry_expected)
        self.assert_fails(
            "e2e-test-execution",
            retry_execution.replace("| result-1 | 1 | 要求primary test | failed | passed | unexpected | 0 | 10ms | first failure |\n", ""),
            retry_expected,
            "E2E-EXEC-D017",
        )

        analysis = self.analysis_output()
        self.assert_pass(
            "e2e-test-result-analysis",
            analysis,
            {
                "required_e2e_ref": "tests/auth/login.spec.ts > login succeeds",
                "required_cleanup_text": "未確認",
                "additional_execution_required": True,
            },
        )
        self.assert_pass(
            "e2e-test-result-analysis",
            analysis + "\nPlaywrightを直接再実行しません。",
            {},
        )
        self.assert_fails(
            "e2e-test-result-analysis",
            analysis + "\nPlaywrightを直接再実行します。",
            {},
            "E2E-AN-D005",
        )
        self.assert_fails(
            "e2e-test-result-analysis",
            analysis.replace("| 必要 | cleanup確認ログ | cleanupが成功しているか | cleanupのみ | e2e-test-execution |", "| 必要 | cleanup確認ログ | cleanupが成功しているか | cleanupのみ | e2e-test-result-analysis |"),
            {"additional_execution_required": True},
            "E2E-AN-D010",
        )
        self.assert_fails(
            "e2e-test-result-analysis",
            analysis.replace("tests/auth/login.spec.ts > login succeeds", "tests/auth/login.spec.ts > login succeeds as admin"),
            {"required_e2e_ref": "tests/auth/login.spec.ts > login succeeds"},
            "E2E-AN-D007",
        )
        self.assert_fails(
            "e2e-test-result-analysis",
            analysis.replace("| E2E対象 / logical primary | login-flow | execution.md |", "| E2E対象 / logical primary |  | execution.md |"),
            {},
            "E2E-AN-D012",
        )
        self.assert_fails(
            "e2e-test-result-analysis",
            analysis.replace("| E2E対象 / logical primary | login-flow | execution.md |", "| E2E対象 / logical primary | login-flow |  |"),
            {},
            "E2E-AN-D012",
        )
        self.assert_fails(
            "e2e-test-result-analysis",
            analysis.replace("| result-1 | 判定可能 | 異常なし | 未確認 | execution.md |\n", ""),
            {},
            "E2E-AN-D013",
        )
        self.assert_fails(
            "e2e-test-result-analysis",
            analysis.replace("| 必要 | cleanup確認ログ | cleanupが成功しているか | cleanupのみ | e2e-test-execution |\n", ""),
            {},
            "E2E-AN-D014",
        )
        no_additional = analysis.replace(
            "| 必要 | cleanup確認ログ | cleanupが成功しているか | cleanupのみ | e2e-test-execution |",
            "| 不要 |  |  |  | なし |",
        )
        self.assert_pass("e2e-test-result-analysis", no_additional, {"additional_execution_required": False})
        self.assert_fails(
            "e2e-test-result-analysis",
            analysis,
            {"additional_execution_required": False},
            "E2E-AN-D011",
        )
        self.assert_pass(
            "e2e-test-result-analysis",
            analysis.replace("| result-1 | 判定可能 | 異常なし | 未確認 | execution.md |", "| result-1 | 判定不能 | 原因未確定 | 未確認 | 証拠不足 |"),
            {},
        )

        report = self.reporting_output()
        self.assert_pass(
            "e2e-test-reporting",
            report,
            {"expected_logical_primary_count": 1, "expected_resolved_primary_count": 1, "required_cleanup_text": "成功"},
        )
        self.assert_pass(
            "e2e-test-reporting",
            report,
            {
                "expected_logical_primary_count": 1,
                "expected_resolved_primary_count": 1,
                "analysis_performed": True,
                "required_analysis_ref": "analysis.md",
            },
        )
        self.assert_fails(
            "e2e-test-reporting",
            report.replace("| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |", "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 |  | 実行済み |"),
            {"analysis_performed": True},
            "E2E-REPORT-D020",
        )
        self.assert_fails(
            "e2e-test-reporting",
            report.replace("| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |", "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis-999 | 実行済み |"),
            {"analysis_performed": True, "required_analysis_ref": "analysis.md"},
            "E2E-REPORT-D020",
        )
        analysis_not_performed = report.replace(
            "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |",
            "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 |  | 実行済み |",
        )
        self.assert_pass("e2e-test-reporting", analysis_not_performed, {"analysis_performed": False})
        self.assert_fails(
            "e2e-test-reporting",
            report,
            {"analysis_performed": False},
            "E2E-REPORT-D020",
        )
        retry_report = report.replace(
            "| login-flow | result-1 | 開始 | passed |  | passed | expected | 1 | passed (retry 0) | result-1 |",
            "| login-flow | result-1 | 開始 | passed |  | passed | flaky | 2 | failed (retry 0) -> passed (retry 1) | result-1 |",
        )
        retry_report_expected = {
            "expected_logical_primary_count": 1,
            "expected_resolved_primary_count": 1,
            "required_cleanup_text": "成功",
            "required_retry_history": "failed",
        }
        self.assert_pass("e2e-test-reporting", retry_report, retry_report_expected)
        self.assert_fails(
            "e2e-test-reporting",
            retry_report.replace("failed (retry 0) -> passed (retry 1)", ""),
            retry_report_expected,
            "E2E-REPORT-D015",
        )
        self.assert_fails(
            "e2e-test-reporting",
            report.replace("| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |", "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 0 | 0 |"),
            {"expected_logical_primary_count": 1, "expected_resolved_primary_count": 1},
            "E2E-REPORT-D005",
        )

    def test_e2e_false_pass_regressions_for_review_findings(self):
        inspection = self.inspection_output()
        for mutated, assertion_id in (
            (inspection.replace("| branch | feat/e2e | repo | 2026-09-12 |", "| branch |  | repo | 2026-09-12 |"), "E2E-INSP-D005"),
            (inspection.replace("| commit | abc123 | repo | 2026-09-12 |", "| commit |  | repo | 2026-09-12 |"), "E2E-INSP-D005"),
            (inspection.replace("| テスト環境URL / origin | https://app.test | 実対象 | 2026-09-12 |", "| テスト環境URL / origin |  | 実対象 | 2026-09-12 |"), "E2E-INSP-D005"),
            (inspection.replace("| 副作用 | テストデータのみ | ユーザー提供情報 | runner cleanup |", "| 副作用 |  | ユーザー提供情報 | runner cleanup |"), "E2E-INSP-D006"),
            (inspection.replace("| URL / origin | 許可済み | ユーザー提供情報 | execution |", "| URL / origin | 許可済み |  | execution |"), "E2E-INSP-D006"),
        ):
            self.assert_fails("e2e-test-inspection", mutated, {}, assertion_id)
        self.assert_fails(
            "e2e-test-inspection",
            inspection.replace("| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | 明示対象と既存構成 | 新規E2E実装 |", "|  | TC-101 | tests/auth/login.spec.ts > login succeeds | 明示対象と既存構成 | 新規E2E実装 |"),
            {},
            "E2E-INSP-D015",
        )
        self.assert_fails(
            "e2e-test-inspection",
            inspection.replace("| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | 明示対象と既存構成 | 新規E2E実装 |", "| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds |  | 新規E2E実装 |"),
            {},
            "E2E-INSP-D015",
        )
        self.assert_fails(
            "e2e-test-inspection",
            inspection.replace("| Playwright構成 / 実行入口 | playwright.config.ts / npm test:e2e | repo | 既存入口を再利用 |", "| Playwright構成 / 実行入口 |  | repo | 既存入口を再利用 |"),
            {},
            "E2E-INSP-D016",
        )
        self.assert_fails(
            "e2e-test-inspection",
            inspection.replace("| Playwright構成 / 実行入口 | playwright.config.ts / npm test:e2e | repo | 既存入口を再利用 |", "| Playwright構成 / 実行入口 | playwright.config.ts / npm test:e2e |  | 既存入口を再利用 |"),
            {},
            "E2E-INSP-D016",
        )
        self.assert_pass(
            "e2e-test-inspection",
            inspection.replace("| locator / 観測方法 | data-testid / URL | 実対象 | 安定参照 |", "| locator / 観測方法 | 未確認（実対象未接続） | 未確認 | 実対象確認待ち |"),
            {},
        )
        self.assert_fails(
            "e2e-test-inspection",
            inspection.replace("| login flow | 新規E2E実装 |  | 既存対象なし |", "| login flow |  |  | 既存対象なし |"),
            {},
            "E2E-INSP-D007",
        )

        selection_only = """# テスト分析
## プロダクトリスク一覧
| リスクID | 製品上のリスク / 失敗 | 関連する現在有効な仕様根拠 / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 |
| --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | login失敗 | SPEC-001 | 4 | 2 | 高 | 変更 |
## 選択したテスト技法
| テスト技法 | 適用領域 | 選択理由 |
| --- | --- | --- |
| シナリオ | login | 主要経路 |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル |
| --- | --- | --- | --- | --- |
| login | 可 | 可 | 可 | システム |
- 対象 / 実行範囲: E2E対象選定
## E2E対象選定
| 自動化目的 | 候補範囲 | 技術非依存の判断基準 / 根拠 |
| --- | --- | --- |
        """
        self.assert_fails("test-analysis", selection_only, {}, "RISK-D017")
        optional_e2e_table = selection_only.replace("- 対象 / 実行範囲: E2E対象選定", "- 対象 / 実行範囲: テスト分析")
        self.assert_pass("test-analysis", optional_e2e_table, {})

        implementation = self.implementation_output()
        tc_without_explicit_target = implementation.replace(
            "| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | dashboardが表示される | 新規実装 |",
            "| login flow | TC-101 |  | dashboardが表示される | 新規実装 |",
        )
        self.assert_pass("e2e-test-implementation", tc_without_explicit_target, {})
        empty_validation = implementation.replace(
            "| lint / typecheck / discovery | npm run lint | PASS | 実E2Eではない |\n", ""
        )
        self.assert_fails("e2e-test-implementation", empty_validation, {}, "E2E-IMPL-D014")
        no_reason = implementation.replace(
            "| lint / typecheck / discovery | npm run lint | PASS | 実E2Eではない |",
            "| lint / typecheck / discovery | - | 未実施 |  |",
        )
        self.assert_fails("e2e-test-implementation", no_reason, {}, "E2E-IMPL-D014")
        failed_as_complete = implementation.replace(
            "| lint / typecheck / discovery | npm run lint | PASS | 実E2Eではない |",
            "| lint / typecheck / discovery | npm run lint | FAIL | lint error |",
        )
        self.assert_fails("e2e-test-implementation", failed_as_complete, {}, "E2E-IMPL-D015")
        self.assert_fails(
            "e2e-test-implementation",
            implementation.replace("| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | dashboardが表示される | 新規実装 |\n", ""),
            {},
            "E2E-IMPL-D018",
        )
        self.assert_fails(
            "e2e-test-implementation",
            implementation.replace("| tests/auth/login.spec.ts > login succeeds | tests/auth/login.spec.ts | login succeeds | TC-101 | 新規実装 |\n", ""),
            {},
            "E2E-IMPL-D019",
        )
        self.assert_fails(
            "e2e-test-implementation",
            implementation.replace(
                "| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | dashboardが表示される | 新規実装 |",
                "| login flow |  |  | dashboardが表示される | 新規実装 |",
            ),
            {},
            "E2E-IMPL-D018",
        )
        implementation_block = implementation.replace(
            "| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | dashboardが表示される | 新規実装 |",
            "| login flow |  | ユーザー明示E2E対象 | 未確認 | ブロック中 |",
        ).replace(
            "| tests/auth/login.spec.ts > login succeeds | tests/auth/login.spec.ts | login succeeds | TC-101 | 新規実装 |\n",
            "",
        ).replace(
            "| login flow | なし |  | e2e-test-execution |",
            "| login flow | ブロック中 | inspection情報不足 | e2e-test-inspection |",
        ).replace(
            "| tests/auth/login.spec.ts | login testを追加 | data-testid |",
            "| なし | 変更なし |  |",
        ).replace(
            "| lint / typecheck / discovery | npm run lint | PASS | 実E2Eではない |",
            "| lint / typecheck / discovery | - | 未実施 | 実装前blockのため未実施 |",
        )
        self.assert_pass("e2e-test-implementation", implementation_block, {})
        self.assert_fails(
            "e2e-test-implementation",
            implementation_block.replace("| login flow | ブロック中 | inspection情報不足 | e2e-test-inspection |", "| login flow | ブロック中 |  |  |"),
            {},
            "E2E-IMPL-D020",
        )
        self.assert_fails(
            "e2e-test-implementation",
            implementation.replace(
                "| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | dashboardが表示される | 新規実装 |",
                "| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | 未確認 | 新規実装 |",
            ),
            {},
            "E2E-IMPL-D021",
        )
        self.assert_fails(
            "e2e-test-implementation",
            implementation.replace(
                "| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | dashboardが表示される | 新規実装 |",
                "| login flow | TC-101 | tests/auth/login.spec.ts > login succeeds | 確認不能 | 既存E2E拡張 |",
            ),
            {},
            "E2E-IMPL-D021",
        )
        block_only_with_artifacts = implementation_block.replace(
            "| なし | 変更なし |  |",
            "| tests/auth/login.spec.ts | login testを追加 | data-testid |",
        ).replace(
            "| lint / typecheck / discovery | - | 未実施 | 実装前blockのため未実施 |",
            "| lint / typecheck / discovery | npm run lint | PASS | 実E2Eではない |",
        )
        self.assert_fails("e2e-test-implementation", block_only_with_artifacts, {}, "E2E-IMPL-D022")

        execution = self.execution_output()
        for mutated in (
            execution.replace("| 対象URL / origin | https://app.test | 実対象 | raw fact |", "| 対象URL / origin |  | 実対象 | raw fact |"),
            execution.replace("| 実行入口 / command chain | npm run test:e2e | repo | raw fact |", "| 実行入口 / command chain |  | repo | raw fact |"),
        ):
            self.assert_fails("e2e-test-execution", mutated, {}, "E2E-EXEC-D018")

        preflight_block = execution
        preflight_block = preflight_block.replace(
            "| login-flow | tests/auth/login.spec.ts > login succeeds / TC-101 | 1 |  |",
            "| login-flow | tests/auth/login.spec.ts > login succeeds / TC-101 | 0 | credential不足でrunner未開始 |",
        )
        preflight_block = preflight_block.replace(
            "| result-1 | login-flow | tests/auth/login.spec.ts > login succeeds | chromium | 0 | 開始 | passed |\n", ""
        )
        preflight_block = preflight_block.replace(
            "| result-1 | 1 | 要求primary test | passed | passed | expected | 0 | 10ms |  |\n", ""
        )
        preflight_block = preflight_block.replace("| runner開始 | はい | execution | raw fact |", "| runner開始 | いいえ | execution | raw fact |")
        preflight_block = preflight_block.replace(
            "| app | 今回runが起動 | 今回runが所有 | 新規起動 | 対象 | Playwright webServer |",
            "| app | 未開始 | 今回runは所有しない | 起動なし | 対象外 | runner未開始 |",
        )
        preflight_block = preflight_block.replace(
            "| Playwright run全体status | passed | reporter | raw fact |",
            "| Playwright run全体status | 未確認 | reporter / API / 確認不能 | 確認不能 |",
        )
        preflight_block = preflight_block.replace(
            "| CLI process exit code | 0 | process | raw fact |",
            "| CLI process exit code | 未実施 | process / 未実施 | 確認不能 |",
        )
        preflight_block = preflight_block.replace(
            "| run-level / global error | なし | reporter | raw fact |",
            "| run-level / global error | 未実施 | reporter / process / 未実施 | 確認不能 |",
        )
        preflight_block = preflight_block.replace(
            "| result artifactの今回run生成・更新 | はい | filesystem | raw fact |",
            "| result artifactの今回run生成・更新 | 未生成 | filesystem | raw fact |",
        )
        preflight_block = preflight_block.replace(
            "| output / report / snapshot / source | なし | result.json | 今回run |",
            "| output / report / snapshot / source | なし | なし | runner未開始で今回run結果なし |",
        )
        preflight_block = preflight_block.replace(
            "- 実行成果物状態: 完了\n- ブロック中: なし",
            "- 実行成果物状態: ブロック中\n- ブロック中: credential不足のため実行しなかった。stale artifactを今回結果として利用していない。",
        )
        preflight_block = preflight_block.replace(
            "| runner管理 | 成功 | 残存なし | reporter |",
            "| runner管理 | 対象なし | runner未開始 | execution |",
        )
        self.assert_pass("e2e-test-execution", preflight_block, {})
        self.assert_fails(
            "e2e-test-execution",
            preflight_block.replace("| Playwright run全体status | 未確認 | reporter / API / 確認不能 | 確認不能 |", "| Playwright run全体status | passed | reporter | raw fact |"),
            {},
            "E2E-EXEC-D024",
        )
        self.assert_fails(
            "e2e-test-execution",
            preflight_block.replace("| CLI process exit code | 未実施 | process / 未実施 | 確認不能 |", "| CLI process exit code | 0 | process | raw fact |"),
            {},
            "E2E-EXEC-D024",
        )
        self.assert_fails(
            "e2e-test-execution",
            preflight_block.replace("| runner管理 | 対象なし | runner未開始 | execution |", "| runner管理 | 成功 | 残存なし | reporter |"),
            {},
            "E2E-EXEC-D024",
        )
        external_cleanup_block = preflight_block.replace(
            "| run外準備 | 対象なし | repo | raw fact |",
            "| run外準備 | 実施（seed） | repo | raw fact |",
        ).replace(
            "| run外処理 | 対象なし | run外準備なし | execution |",
            "| run外処理 | 成功 | run外seedをcleanup済み | execution |",
        )
        self.assert_pass("e2e-test-execution", external_cleanup_block, {})
        self.assert_fails(
            "e2e-test-execution",
            preflight_block.replace("| run外処理 | 対象なし | run外準備なし | execution |", "| run外処理 | 成功 | run外seedをcleanup済み | execution |"),
            {},
            "E2E-EXEC-D024",
        )
        misleading_external_cleanup = preflight_block.replace(
            "| setup / dependency / webServer / teardown | runner / none / webServer設定あり / runner | repo | raw fact |",
            "| setup / dependency / webServer / teardown | runner / run外seed / webServer設定あり / runner | repo | raw fact |",
        ).replace(
            "| run外処理 | 対象なし | run外準備なし | execution |",
            "| run外処理 | 成功 | run外seedをcleanup済み | execution |",
        )
        self.assert_fails("e2e-test-execution", misleading_external_cleanup, {}, "E2E-EXEC-D024")
        started_external_cleanup_without_preparation = execution.replace(
            "| run外処理 | 対象なし | run外準備なし | execution |",
            "| run外処理 | 成功 | run外seedをcleanup済み | execution |",
        )
        self.assert_fails("e2e-test-execution", started_external_cleanup_without_preparation, {}, "E2E-EXEC-D027")
        started_external_cleanup_with_preparation = started_external_cleanup_without_preparation.replace(
            "| run外準備 | 対象なし | repo | raw fact |",
            "| run外準備 | 実施（seed） | repo | raw fact |",
        )
        self.assert_pass("e2e-test-execution", started_external_cleanup_with_preparation, {})
        for mutated in (
            preflight_block.replace(
                "| run-level / global error | 未実施 | reporter / process / 未実施 | 確認不能 |",
                "| run-level / global error | browser crashed | reporter | raw fact |",
            ),
            preflight_block.replace(
                "| run-level / global error | 未実施 | reporter / process / 未実施 | 確認不能 |",
                "| run-level / global error | timeout | Playwright | raw fact |",
            ),
        ):
            self.assert_fails("e2e-test-execution", mutated, {}, "E2E-EXEC-D024")
        self.assert_fails(
            "e2e-test-execution",
            execution.replace("| 対象URL / origin | https://app.test | 実対象 | raw fact |", "| 対象URL / origin | 未確認 | 実対象 | raw fact |"),
            {},
            "E2E-EXEC-D026",
        )
        self.assert_fails(
            "e2e-test-execution",
            execution.replace("| cleanup方法 | runner teardown / run外なし | repo | raw fact |", "| cleanup方法 | 未確認 | repo | 確認不能 |"),
            {},
            "E2E-EXEC-D026",
        )
        self.assert_fails(
            "e2e-test-execution",
            execution.replace("| cleanup方法 | runner teardown / run外なし | repo | raw fact |", "| cleanup方法 | 未実施 | repo | raw fact |"),
            {},
            "E2E-EXEC-D026",
        )
        self.assert_fails(
            "e2e-test-execution",
            execution.replace("| 必要な認証 / テストデータ / 開始状態 | test user / clean account | repo | raw fact |", "| 必要な認証 / テストデータ / 開始状態 | 未実施 | repo | raw fact |"),
            {},
            "E2E-EXEC-D026",
        )
        self.assert_pass(
            "e2e-test-execution",
            execution.replace("| テスト対象version / build ID | build-1 | 実対象 | raw fact |", "| テスト対象version / build ID | 未確認 | 実対象 | 確認不能 |"),
            {},
        )
        self.assert_fails(
            "e2e-test-execution",
            execution.replace("| login-flow | tests/auth/login.spec.ts > login succeeds / TC-101 | 1 |  |\n", ""),
            {},
            "E2E-EXEC-D023",
        )

        multi_server = execution.replace(
            "| app | 今回runが起動 | 今回runが所有 | 新規起動 | 対象 | Playwright webServer |",
            "| frontend | 今回runが起動 | 今回runが所有 | 新規起動 | 対象 | Playwright webServer |\n| backend | 既存process | 今回runは所有しない | 既存process再利用 | 対象外 | reuseExistingServer=true |",
        )
        self.assert_pass("e2e-test-execution", multi_server, {"expected_webserver_ids": ["frontend", "backend"]})
        self.assert_fails(
            "e2e-test-execution",
            multi_server.replace("| backend | 既存process |", ""),
            {"expected_webserver_ids": ["frontend", "backend"]},
            "E2E-EXEC-D025",
        )
        self.assert_fails(
            "e2e-test-execution",
            multi_server.replace("| backend | 既存process | 今回runは所有しない |", "| backend | 既存process |  |"),
            {},
            "E2E-EXEC-D025",
        )
        self.assert_fails(
            "e2e-test-execution",
            multi_server.replace("| frontend | 今回runが起動 | 今回runが所有 | 新規起動 | 対象 |", "| frontend | 今回runが起動 | 今回runは所有しない | 新規起動 | 対象外 |").replace("Playwright webServer |", "Playwright webServer |", 1),
            {"expected_webserver_ids": ["frontend", "backend"]},
            "E2E-EXEC-D025",
        )
        self.assert_fails(
            "e2e-test-execution",
            multi_server.replace("| backend | 既存process | 今回runは所有しない | 既存process再利用 | 対象外 |", "| backend | 既存process | 今回runは所有しない | 既存process再利用 | 対象 |"),
            {},
            "E2E-EXEC-D025",
        )

        stale_artifact = execution.replace(
            "| result artifactの今回run生成・更新 | はい | filesystem | raw fact |",
            "| result artifactの今回run生成・更新 | 未生成 | filesystem | raw fact |",
        ).replace(
            "| output / report / snapshot / source | なし | result.json | 今回run |",
            "| output / report / snapshot / source | なし | result.json | stale artifactは利用していない |",
        )
        self.assert_fails("e2e-test-execution", stale_artifact, {}, "E2E-EXEC-D005")

        reuse_existing = execution.replace(
            "| setup / dependency / webServer / teardown | runner / none / webServer設定あり / runner | repo | raw fact |",
            "| setup / dependency / webServer / teardown | runner / none / reuseExistingServer=true / runner | repo | raw fact |",
        )
        reuse_existing = reuse_existing.replace(
            "| app | 今回runが起動 | 今回runが所有 | 新規起動 | 対象 | Playwright webServer |",
            "| app | 実行前から存在 | 今回runは所有しない | 既存process再利用 | 対象外 | reuseExistingServer=true |",
        )
        self.assert_pass("e2e-test-execution", reuse_existing, {})
        contradictory_reuse = execution.replace(
            "| setup / dependency / webServer / teardown | runner / none / webServer設定あり / runner | repo | raw fact |",
            "| setup / dependency / webServer / teardown | runner / none / reuseExistingServer=true / runner | repo | raw fact |",
        )
        self.assert_fails("e2e-test-execution", contradictory_reuse, {}, "E2E-EXEC-D025")
        unknown_webserver = preflight_block.replace(
            "| setup / dependency / webServer / teardown | runner / none / webServer設定あり / runner | repo | raw fact |",
            "| setup / dependency / webServer / teardown | runner / none / webServer=未確認 / runner | repo | raw fact |",
        ).replace(
            "| app | 未開始 | 今回runは所有しない | 起動なし | 対象外 | runner未開始 |\n",
            "",
        )
        self.assert_pass("e2e-test-execution", unknown_webserver, {})
        self.assert_fails(
            "e2e-test-execution",
            unknown_webserver.replace("| runner開始 | いいえ | execution | raw fact |", "| runner開始 | はい | execution | raw fact |").replace("- 実行成果物状態: ブロック中", "- 実行成果物状態: 完了"),
            {},
            "E2E-EXEC-D025",
        )

        for mutated, assertion_id in (
            (execution.replace("| result-1 | 1 | 要求primary test | passed | passed | expected | 0 | 10ms |  |", "| result-1 | 1 | 要求primary test | timedout | passed | expected | 0 | 10ms |  |"), "E2E-EXEC-D010"),
            (execution.replace("| result-1 | 1 | 要求primary test | passed | passed | expected | 0 | 10ms |  |", "| result-1 | 1 | 要求primary test | passed | passed | timedOut | 0 | 10ms |  |"), "E2E-EXEC-D010"),
            (execution.replace("| result-1 | 1 | 要求primary test | passed | passed | expected | 0 | 10ms |  |", "| result-1 | 1 | 要求primary test | passed | passed | 未実行 | 0 | 10ms |  |"), "E2E-EXEC-D010"),
            (execution.replace("| result-1 | 1 | 要求primary test | passed | passed | expected | 0 | 10ms |  |", "| result-1 | 1 | 要求primary test | passed | invalid | expected | 0 | 10ms |  |"), "E2E-EXEC-D010"),
            (execution.replace("| Playwright run全体status | passed | reporter | raw fact |", "| Playwright run全体status | passed | process exit code | raw fact |"), "E2E-EXEC-D003"),
        ):
            self.assert_fails("e2e-test-execution", mutated, {}, assertion_id)

        report = self.reporting_output()
        resolved_row = "| login-flow | result-1 | 開始 | passed |  | passed | expected | 1 | passed (retry 0) | result-1 |"
        for mutated, assertion_id in (
            (report.replace(resolved_row, resolved_row.replace("| 開始 | passed |  | passed |", "| 開始 | timedout |  | passed |")), "E2E-REPORT-D017"),
            (report.replace(resolved_row, resolved_row.replace("| expected | 1 |", "| timedOut | 1 |")), "E2E-REPORT-D017"),
            (report.replace(resolved_row, resolved_row.replace("| expected | 1 |", "| 未実行 | 1 |")), "E2E-REPORT-D017"),
            (report.replace(resolved_row, resolved_row.replace("| passed |  | passed | expected |", "| passed |  | passed | invalid |")), "E2E-REPORT-D017"),
            (report.replace("| Playwright run全体status | passed | reporter | raw fact |", "| Playwright run全体status | passed | process exit code | raw fact |"), "E2E-REPORT-D003"),
        ):
            self.assert_fails("e2e-test-reporting", mutated, {}, assertion_id)

        partial = report.replace(
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |  |  |",
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 3 | 2 |  |  |",
        )
        self.assert_fails("e2e-test-reporting", partial, {}, "E2E-REPORT-D005")
        unresolved_logical = report.replace(
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |  |  |",
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 0 | 0 |  |  |",
        ).replace(resolved_row + "\n", "")
        self.assert_fails("e2e-test-reporting", unresolved_logical, {}, "E2E-REPORT-D005")
        unresolved_reason_placeholder = report.replace(
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |  |  |",
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 2 | 1 |  | なし |",
        )
        self.assert_fails("e2e-test-reporting", unresolved_reason_placeholder, {}, "E2E-REPORT-D005")
        retry_count_as_resolved = report.replace(
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |  |  |",
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 2 | 2 |  |  |",
        )
        self.assert_fails("e2e-test-reporting", retry_count_as_resolved, {}, "E2E-REPORT-D005")
        trace_empty = report.replace(
            "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |\n", ""
        )
        self.assert_fails("e2e-test-reporting", trace_empty, {}, "E2E-REPORT-D018")
        not_started = report.replace(
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |  |  |",
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 0 |  | credential不足のため未実行 |",
        ).replace(
            resolved_row,
            "| login-flow | result-1 | 未開始 |  | credential不足のため未実行 |  |  | 0 |  |  |",
        )
        self.assert_pass("e2e-test-reporting", not_started, {})
        self.assert_fails(
            "e2e-test-reporting",
            report.replace("| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |", "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-999 | analysis.md | 実行済み |"),
            {},
            "E2E-REPORT-D009",
        )
        self.assert_fails(
            "e2e-test-reporting",
            report.replace("| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |", "| TC-101 | tests/auth/admin.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |"),
            {},
            "E2E-REPORT-D009",
        )
        two_resolved = report.replace(
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |  |  |",
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 2 | 2 |  |  |",
        ).replace(
            "| login-flow | result-1 | 開始 | passed |  | passed | expected | 1 | passed (retry 0) | result-1 |",
            "| login-flow | result-1 | 開始 | passed |  | passed | expected | 1 | passed (retry 0) | result-1 |\n| login-flow | result-2 | 開始 | passed |  | passed | expected | 1 | passed (retry 0) | result-2 |",
        ).replace(
            "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |",
            "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |\n| TC-101 | tests/auth/login.spec.ts > login succeeds | result-2 | analysis.md | 実行済み |",
        )
        self.assert_pass("e2e-test-reporting", two_resolved, {})
        self.assert_fails(
            "e2e-test-reporting",
            two_resolved.replace("| TC-101 | tests/auth/login.spec.ts > login succeeds | result-2 | analysis.md | 実行済み |\n", ""),
            {},
            "E2E-REPORT-D009",
        )
        self.assert_pass(
            "e2e-test-reporting",
            report.replace("| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |", "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 |  | 実行済み |"),
            {},
        )
        self.assert_pass(
            "e2e-test-reporting",
            report.replace("| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |", "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 |  | 実行済み |"),
            {"analysis_performed": False},
        )
        logical_only = report.replace(
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |  |  |",
            "| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 0 | 0 | credential不足で未実行 |  |",
        ).replace(
            "| login-flow | result-1 | 開始 | passed |  | passed | expected | 1 | passed (retry 0) | result-1 |\n",
            "",
        ).replace(
            "| TC-101 | tests/auth/login.spec.ts > login succeeds | result-1 | analysis.md | 実行済み |",
            "| TC-101 | tests/auth/login.spec.ts > login succeeds | login-flow |  | 未実行 |",
        )
        self.assert_pass("e2e-test-reporting", logical_only, {})
        self.assert_fails(
            "e2e-test-reporting",
            report.replace("| login-flow | tests/auth/login.spec.ts > login succeeds | TC-101 | 1 | 1 |  |  |\n", ""),
            {},
            "E2E-REPORT-D019",
        )

    def test_tc_free_paths_do_not_fabricate_tc_ids(self):
        self.assert_pass(
            "e2e-test-inspection",
            self.inspection_output(tc_free=True),
            {"required_e2e_refs": ["tests/auth/login.spec.ts > login succeeds"], "tc_absent": True},
        )
        self.assert_pass(
            "e2e-test-implementation",
            self.implementation_output(tc_free=True),
            {"required_e2e_refs": ["tests/auth/login.spec.ts > login succeeds"], "tc_absent": True, "require_no_e2e_execution": True},
        )
        self.assert_pass(
            "e2e-test-execution",
            self.execution_output(tc_free=True),
            {"expected_logical_primary_count": 1, "expected_resolved_primary_count": 1, "tc_absent": True},
        )
        self.assert_pass(
            "e2e-test-result-analysis",
            self.analysis_output(tc_free=True),
            {"required_e2e_ref": "tests/auth/login.spec.ts > login succeeds", "required_cleanup_text": "未確認", "tc_absent": True},
        )
        self.assert_pass(
            "e2e-test-reporting",
            self.reporting_output(tc_free=True),
            {"expected_logical_primary_count": 1, "expected_resolved_primary_count": 1, "required_cleanup_text": "成功", "tc_absent": True},
        )

    def test_workflow_and_question_restart_targets_are_scoped(self):
        workflow = """# Workflow
- ワークフロー全体状態: 実行中
- 開始Skill: test-analysis
- 開始対象 / 実行範囲: E2E対象選定
- 最終Skill: coverage-analysis
- 最終対象 / 実行範囲: TC → E2E実装
| Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考 |
| --- | --- | --- | --- | --- |
| test-analysis | E2E対象選定 | 完了 | selection | |
| coverage-analysis | TC → E2E実装 | 完了 | mapping | |
| adversarial-review | E2E実装 | 要再検証 | review | |
| e2e-test-inspection |  | 完了 | inspection | |
"""
        self.assert_pass(
            "qa-workflow",
            workflow,
            {
                "expected_start_skill": "test-analysis",
                "expected_start_target": "E2E対象選定",
                "expected_final_skill": "coverage-analysis",
                "expected_final_target": "TC → E2E実装",
                "expected_skills": ["test-analysis", "coverage-analysis", "adversarial-review", "e2e-test-inspection"],
                "expected_scoped_skill_states": [
                    {"skill": "test-analysis", "target": "E2E対象選定", "state": "完了"},
                    {"skill": "coverage-analysis", "target": "TC → E2E実装", "state": "完了"},
                    {"skill": "adversarial-review", "target": "E2E実装", "state": "要再検証"},
                ],
            },
        )
        self.assert_fails(
            "qa-workflow",
            workflow.replace("開始対象 / 実行範囲: E2E対象選定", "開始対象 / 実行範囲: "),
            {},
            "WF-D017",
        )

        question = """# 不明点
## 不明点 / 質問一覧
| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill | 再開対象 / 実行範囲 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q-101 | E2E期待結果が未確定 | 仕様決定待ち | ブロッカー | E2E実装 | 停止 | 未確定 | coverage-analysis | TC → E2E実装 |
## 仮定候補
| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | 正式ASM ID |
| --- | --- | --- | --- | --- |
## ブロック中範囲
| ブロッカーID | ブロック中成果物 / 範囲 | 必要な決定 / 情報源 | 再開Skill | 再開対象 / 実行範囲 |
| --- | --- | --- | --- | --- |
| Q-101 | E2E実装 | 仕様決定 | coverage-analysis | TC → E2E実装 |
"""
        self.assert_pass(
            "question-analysis",
            question,
            {"require_blocked_for_blockers": True, "expected_restarts": {"Q-101": {"skill": "coverage-analysis", "target": "TC → E2E実装"}}},
        )
        self.assert_fails(
            "question-analysis",
            question.replace("TC → E2E実装", "誤った範囲"),
            {"require_blocked_for_blockers": True},
            "QUESTION-D017",
        )

    def test_existing_skill_e2e_target_contracts(self):
        test_analysis = """# テスト分析
## プロダクトリスク一覧
| リスクID | 製品上のリスク / 失敗 | 関連する現在有効な仕様根拠 / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 | 判断信頼度 / 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | login失敗 | SPEC-001 | 4 | 2 | 高 | 変更 | 高 |
## 選択したテスト技法
| テスト技法 | 適用領域 | 選択理由 | 関連プロダクトリスク / 現在有効な仕様根拠 | `test-condition-design`への着眼点 |
| --- | --- | --- | --- | --- |
| シナリオ | login | 主要経路 | RISK-001 | 認証 |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル | 扱い / 備考 |
| --- | --- | --- | --- | --- | --- |
| login | 可 | 可 | 可 | システム | E2E候補 |
- 対象 / 実行範囲: E2E対象選定
## E2E対象選定
| 自動化目的 | 候補範囲 | 技術非依存の判断基準 / 根拠 | 対象外 / 保留 |
| --- | --- | --- | --- |
| 主要ログイン回帰 | login | 重要な利用者価値と安定した観測点 | 外部IdP |
"""
        self.assert_pass("test-analysis", test_analysis, {"known_authorities": ["SPEC-001"], "require_e2e_selection": True})
        self.assert_fails("test-analysis", test_analysis.replace("| 主要ログイン回帰 | login | 重要な利用者価値と安定した観測点 | 外部IdP |", "| 主要ログイン回帰 | login |  | 外部IdP |"), {"require_e2e_selection": True}, "RISK-D017")

        graph = {
            "node_types": {"SPEC-001": "Authority", "TR-001": "TR", "TCN-001": "TCN", "TCN-001-CI01": "CI", "TC-101": "TC"},
            "edges": [["SPEC-001", "TR-001"], ["TR-001", "TCN-001"], ["TCN-001", "TCN-001-CI01"], ["TCN-001-CI01", "TC-101"]],
            "dispositions": {},
        }
        coverage = """# Coverage
## 仕様根拠 / プロダクトリスクの閉鎖状況
| 上流ID | 種別 | 接続先テスト要求 / 扱い | 状態 | 根拠 / ギャップ |
| --- | --- | --- | --- | --- |
| SPEC-001 | 仕様根拠 | TR-001 | 閉鎖 | |
## カバレッジ項目の扱い
| カバレッジ項目ID / 項目 | 観点ID | 扱い | 対応テストケースID / 扱い | 根拠 / 備考 |
| --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 | テストケース | TC-101 | |
## カバレッジマトリクス
| 上流層 | 上流ID / 挙動 | 下流層 | 下流ID / 扱い | カバレッジ | プロダクトリスク / 優先度 | 根拠 / ギャップ | 推奨対応 | 修正Skill / 層 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CI | TCN-001-CI01 | TC | TC-101 | 網羅済み | | | | test-case-design |
| E2E | tests/auth/login.spec.ts > login succeeds | 実行結果 | result-1 | 網羅済み | | passed | | e2e-test-execution |
## TC → E2E実装対応表
| TC ID | 扱い | E2E実装参照 | 根拠 / 備考 |
| --- | --- | --- | --- |
| TC-101 | 新規E2E実装 | tests/auth/login.spec.ts > login succeeds | |
"""
        self.assert_pass(
            "coverage-analysis",
            coverage,
            {
                "graph": graph,
                "expected_tc_e2e": [{"tc_id": "TC-101", "handling": "新規E2E実装", "implementation_ref": "tests/auth/login.spec.ts > login succeeds"}],
                "expected_e2e_execution": [{"implementation_ref": "tests/auth/login.spec.ts > login succeeds", "result_ref": "result-1", "result_contains": "passed"}],
            },
        )
        self.assert_fails(
            "coverage-analysis",
            coverage.replace("| E2E | tests/auth/login.spec.ts > login succeeds | 実行結果 | result-1 |", "| E2E | tests/auth/login.spec.ts > login succeeds | 実行結果 | result-10 |"),
            {
                "expected_e2e_execution": [{"implementation_ref": "tests/auth/login.spec.ts > login succeeds", "result_ref": "result-1"}],
            },
            "COV-D011",
        )
        self.assert_fails(
            "coverage-analysis",
            coverage.replace("tests/auth/login.spec.ts > login succeeds | 実行結果", "tests/auth/login.spec.ts > login as admin | 実行結果"),
            {
                "expected_e2e_execution": [{"implementation_ref": "tests/auth/login.spec.ts > login succeeds", "result_ref": "result-1"}],
            },
            "COV-D011",
        )

        review = """# Review
## 指摘概要
| 重要度 | 件数 |
| --- | ---: |
| 致命的 | 0 |
| 重大 | 1 |
| 軽微 | 0 |
| 提案 | 0 |
## 指摘一覧
| 指摘ID | 重要度 | 対象成果物 / 位置 | 問題 | 根拠 | 影響 | 推奨修正 | 修正Skill / 層 | 処置 | 処置根拠 / 承認参照 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REV-101 | 重大 | TC-001 | 仕様根拠参照不足 | 仕様根拠 | 影響 | 修正 | test-case-design | 修正済み | |
## E2E実装参照一覧
| E2E実装参照 | 対象 / 実行範囲 | 安定したtest identifierまたはrepo-relative path + title path | 一致根拠 |
| --- | --- | --- | --- |
| tests/auth/login.spec.ts > login succeeds | E2E実装 | tests/auth/login.spec.ts > login succeeds | inspection |
"""
        self.assert_pass("adversarial-review", review, {"known_artifact_ids": ["TC-001"], "expected_e2e_implementation_refs": ["tests/auth/login.spec.ts > login succeeds"]})
        self.assert_fails("adversarial-review", review.replace("tests/auth/login.spec.ts > login succeeds", "tests/auth/missing.spec.ts > login succeeds"), {"expected_e2e_implementation_refs": ["tests/auth/login.spec.ts > login succeeds"]}, "REV-D016")

    def test_qa_workflow_routing_fixture_covers_plan_cases(self):
        cases_path = REPO_ROOT / "skills" / "qa-workflow" / "evals" / "deterministic" / "routing_cases.json"
        candidates_path = REPO_ROOT / "skills" / "qa-workflow" / "evals" / "deterministic" / "routing_candidate_outputs.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 29)
        self.assertEqual(len(candidates), 29)
        self.assertEqual({case["id"] for case in cases}, {candidate["id"] for candidate in candidates})
        default_targets = {
            "test-analysis": "テスト分析",
            "coverage-analysis": "テスト設計",
            "adversarial-review": "テスト設計成果物",
        }
        multi_use = set(default_targets)
        cases_by_id = {case["id"]: case for case in cases}
        candidates_by_id = {candidate["id"]: candidate for candidate in candidates}

        def expected_for(case):
            targets = dict(case.get("targets", {}))
            for skill in case["skills"]:
                if skill in multi_use:
                    targets.setdefault(skill, default_targets[skill])
            expected = {
                "expected_start_skill": case["start"],
                "expected_final_skill": case["final"],
                "expected_skills": case["skills"],
                "expected_overall_state": case["overall"],
                "expected_skill_states": {skill: case.get("states", {}).get(skill, "完了") for skill in case["skills"]},
            }
            if case["start"] in multi_use:
                expected["expected_start_target"] = case.get("start_target", targets.get(case["start"], ""))
            if case["final"] in multi_use:
                expected["expected_final_target"] = case.get("final_target", targets.get(case["final"], ""))
            return expected

        def render(candidate):
            targets = dict(candidate.get("targets", {}))
            rows = []
            for skill in candidate["skills"]:
                rows.append(
                    f"| {skill} | {targets.get(skill, '')} | {candidate.get('states', {}).get(skill, '完了')} | {candidate['id']} | |"
                )
            return f"""# Workflow
- ワークフロー全体状態: {candidate['overall']}
- 開始Skill: {candidate['start']}
- 開始対象 / 実行範囲: {candidate.get('start_target', targets.get(candidate['start'], ''))}
- 最終Skill: {candidate['final']}
- 最終対象 / 実行範囲: {candidate.get('final_target', targets.get(candidate['final'], ''))}
| Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考 |
| --- | --- | --- | --- | --- |
{chr(10).join(rows)}
"""

        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case.get("input_conditions", "").strip())
                self.assert_pass("qa-workflow", render(candidates_by_id[case["id"]]), expected_for(case))

        direct_implementation = dict(candidates_by_id["WF-E2E-002"])
        direct_implementation["start"] = "e2e-test-implementation"
        direct_implementation["skills"] = ["e2e-test-implementation"]
        self.assert_fails(
            "qa-workflow",
            render(direct_implementation),
            expected_for(cases_by_id["WF-E2E-002"]),
            "WF-D006",
        )
        unnecessary_design = dict(candidates_by_id["WF-E2E-003"])
        unnecessary_design["start"] = "test-analysis"
        unnecessary_design["skills"] = ["test-analysis", "test-case-design", "e2e-test-implementation"]
        self.assert_fails(
            "qa-workflow",
            render(unnecessary_design),
            expected_for(cases_by_id["WF-E2E-003"]),
            "WF-D006",
        )


if __name__ == "__main__":
    unittest.main()
