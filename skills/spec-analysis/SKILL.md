---
name: spec-analysis
description: Figma、要件書、Q&A、リポジトリ、リリース資料などの情報源から、SPEC・DECISION・INFERENCE・UNKNOWNを区別し、対象スコープのCurrent Effective Authorityを解決した追跡可能な仕様分析を作るSkill。テスト分析前の仕様整理、複数情報源の統合、矛盾・制約・状態・業務ルールの抽出に使用する。
---

# 仕様分析

## 実行契約

1. 案件固有の情報源優先順位・正式用語・対象範囲・Canonical Registryがある場合はそれを優先します。
2. 未定義の製品挙動を補完せず、`SPEC` / `DECISION` / `INFERENCE` / `UNKNOWN`を区別します。
3. Test Requirement・Test Condition・Test Caseを先回りして作りません。
4. 通常の仕様抽出、分類、停止条件、最低品質確認は`references/guidance.md`に従います。
5. 複数Authority、version差、情報源競合、Decisionの補足 / 上書き / 置換、承認済みASMの適用判断が必要な場合だけ`references/authority-resolution.md`を追加で読みます。
6. 既定出力形式が必要な場合は`assets/output-template.md`を使用します。案件固有形式がある場合は意味上の出力契約と追跡性を維持する限りそちらを優先します。
7. 他Skillを参照するときはCanonical Skill名を使用します。
8. 最終出力前に、本Skill自身のInput / Output Contract・停止条件・品質ゲートを対象成果物へ適用して自己検証します。明白かつ局所的で新しいDomain判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。最終確認で問題が残る場合は2回目の自動修正を行わず、Authority不足や未解決事項を推測補完せず既存の停止条件・Blocked・routingに従います。

## インターフェース

- **Input**: 対象機能・挙動について利用できる権威ある情報源またはCanonical Registry上の有効Authority。案件コンテキスト、変更差分、実装情報、既存QA成果物は利用可能な場合に補助入力とします。
- **Function**: 情報を`SPEC` / `DECISION` / `INFERENCE` / `UNKNOWN`へ分類し、対象スコープのCurrent Effective Authorityを解決して、後続QA設計で使える追跡可能な仕様モデルへ変換します。
- **Output**: 追跡可能な仕様分析。対象範囲内の現在有効な期待挙動が情報源またはCanonical Registryへ戻れ、業務ルール、状態・遷移、フロー、制約、不明点を必要に応じて表現できる状態にします。

## 基本停止条件

- 対象挙動についてAuthority候補となる権威ある情報源または有効Registry Authorityがない
- 対象範囲を意味のある程度に特定できない
- 必要資料へアクセスできず信頼できる分析が成立しない
- Current Effective Authorityを解決できない重大競合がある

局所的なUNKNOWNや非Blocker欠落だけで全体停止しません。

## リソース

- 通常の仕様分析: `references/guidance.md`
- Authority競合 / version / Decision / ASMの詳細解決: `references/authority-resolution.md`
- 既定出力形式: `assets/output-template.md`
