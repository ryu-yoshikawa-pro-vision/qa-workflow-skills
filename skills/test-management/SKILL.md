---
name: test-management
description: QA計画の作成・改版、開始／終了基準、予定source・実行母集団、進捗・差異、プロジェクトリスクと是正処置を管理する。「QA計画・開始終了基準・日程・進捗・計画対実績・見積差異・計画改版」を求められたら、自分で計画を書く前に必ずこのSkillを読み込む。Product Risk、qa-workflow state、Regression Run、raw実行結果、統合reportは管理しない。
---

# テスト計画・モニタリング・コントロール

## 実行契約

1. 実行前に`references/guidance.md`と`references/data-contract.md`を読み、計画revision、承認、母集団、実績取得、project risk、是正の契約に従います。
2. 本Skillの正本は計画・開始／終了基準・予定source inventory・進捗／差異・project risk・是正処置です。Product Riskは`test-analysis`、QA要求は`test-requirements-analysis`、architecture割当は`test-architecture-design`です。
3. `qa-workflow`のrouting／resume state、`regression-testing`のbaseline／membership／Run、source ownerの実行結果を複製・更新しません。実行結果の統合snapshotは`test-reporting`です。
4. 既存current QA要求・architecture・TC／testware／runから、計画／monitoringだけを直接開始できます。新規B/Dが未実装でも既存sourceを読み、未提供のIDやschemaは推測しません。
5. 計画変更は新revisionの草案として扱います。承認証拠が同じscope・artifact ref・revisionを指すまでcurrentな承認済み計画としません。旧版は履歴として保持します。
6. 予定source inventoryと取得後readback ledgerを分けます。未取得・部分取得・0件確認・実行失敗・未実行・取消・結果不明を区別し、未取得や取得失敗を0件と扱わず、raw結果を書き換えません。
7. 進捗は計画分母、取得済み母集団、実行状態の単位を明示します。別build／環境／retry／runの単位を足し合わせず、report側のPASS率や全体完了を代行しません。
8. 人員・予算・日程・準備・外部依存は根拠がある場合だけ記録します。project riskとProduct Riskを分離し、差異・risk・actionのscope、状態、処理／受容証拠を追跡します。
9. 保存・承認providerが未接続なら更新を草案／blockedに留めます。claimやローカルfixtureを実保存・認証済み承認とみなしません。
10. 最終出力前に`references/guidance.md`の品質ゲートで分母・currentness・承認・差異・再開条件を確認し、不明な範囲を完了扱いしません。

## 入出力

- **入力**: QA要求・architecture、release/build/期間、担当／資源／日程、既存TC／testware・source owner・run／Regression Activity・欠陥／Risk／未実行のcurrent ref。
- **出力**: versioned plan、予定sourceと必要実行の母集団、source owner readback ledger、基準、担当／資源／順序、承認、状態別monitoring snapshot、予実差、project risk、是正処置と履歴。
- **mode**: 計画作成／改版、進捗参照、差異／是正管理。1つのSkill内のmodeとして扱います。

## 正規出力

`assets/output-template.md`を使います。artifact-local IDは保存先ref・revision・scopeと合わせます。Regression Runの実行対象選定、workflow状態、統合結果reportをここへ取り込みません。

## 保存・検証（JSON正本）

保存する正本はcanonical JSON packet（`references/data-contract.md`の「JSON正本packet」）で、Markdownは描画物です。`scripts/management_runtime.py`（stdin/stdoutのJSON、stdlibのみ）を、保存後にowner検証から`validate_readback`（保存本文とreadback・expected_revisionの照合）、`impact`（予定sourceの現在性）、`build_snapshot`（件数の再計算）、`completion_check`（完了条件）の順で呼びます。`assets/plan-packet.example.json`が入力例です。scriptは保存先・承認主体・source ownerの真正性を検証せず、それらは呼出し側の証拠として`not_established_by_this_validator`と返します。

## 次の担当

- 統合実行結果snapshot: `test-reporting`
- Activity／Run selection: `regression-testing`
- 実行・結果・cleanup: 該当する実行owner
- 追加／変更された要求・割当: `test-requirements-analysis` / `test-architecture-design`
