---
name: exploratory-testing
description: 固定Charterの範囲で未知の問題を探索する。既存ownerがないsymptom / hypothesisの実対象検証もinvestigation modeで行う。current UI収集、既知TC実行、E2E原因分析には使用しない。
---

# Exploratory Testing

事前定義TCの忠実実行と分離して、Charterの目的に沿って学習・test design・execution・evaluationを進めます。`exploration`と`investigation`は同じSession / Observation / Finding / Evidence / Follow-up契約を使います。

## 実行契約

1. 操作前に`references/guidance.md`を読み、Charter、allowed origin、side-effect上限、cleanup、安全条件を固定します。
2. ExplorationはChange / Risk / Question / Feature / user goalから未知領域を探索します。Investigationは既存ownerで扱えないsymptom / hypothesis / unresolved Findingだけを検証します。
3. current UI / known behaviorの収集は`test-target-inspection`、既知TCの忠実実行は`test-execution` / `e2e-test-execution`、E2E原因分析は`e2e-test-result-analysis`へroutingします。「調査」という語だけでInvestigationにしません。
4. Observationは実測事実、Findingはfollow-upを要する検出事項として分離します。実測を仕様、原因、Defectへ自動昇格しません。
5. unknown attemptはside effect上限を消費した扱いにし、状態を確認せず盲目的に再試行しません。必要なcleanupが失敗 / 未確認ならSessionを安全完了扱いしません。
6. Production helperが必須のschema / lifecycle処理に失敗した場合は`incomplete` / `unresolved` / `blocked`に閉じ、LLMで同じ処理を代替しません。

## 正規対象

- `exploration`
- `investigation`

## リソース

- Charter・session・cleanup手順: `references/guidance.md`
- 正規出力形: `assets/output-template.md`
- Session machine input: `assets/session-template.json`
- production helper: `scripts/exploratory_runtime.py`
- deterministic contract: `evals/deterministic/validator.py`
