---
name: test-requirements-analysis
description: QA活動の目的・品質目標・要求元・対象範囲・制約・合意状態を定義し、テストアーキテクチャや計画の根拠を整える。案件QA目標を整理・改版するときに使用する。製品の個別テスト要求（TR）設計には使用しない。
---

# QA要求分析

## 実行契約

1. 実行前に`references/guidance.md`と`references/data-contract.md`を読み、要求の分離、参照、承認、履歴、停止条件に従います。
2. 本Skillが所有するのはQA活動の目的、品質目標、対象／対象外、制約、合意状態です。製品仕様の正本は`spec-analysis`、Product Riskは`test-analysis`、個別の製品検証責務（TR）は`test-requirement-design`です。
3. 利用者の依頼、stakeholder要求、承認済みProject Context、現在の仕様・Riskを参照し、各入力のowner・ref・revision・scope・currentnessを記録します。要求元や承認根拠を推測しません。
4. 明示された要求、提案、未回答、対象外、承認済みを区別します。LLMの記述やPR／Issue本文だけを認証済み承認として扱いません。
5. 仕様の不明・競合は`question-analysis`または`spec-analysis`へ、Product Riskの新規評価は`test-analysis`へ返します。読み取り可能な範囲の作業は継続し、影響範囲だけをblockedにします。
6. 既存のcurrent QA要求からarchitecture・計画を直接開始できます。不要な再分析、Product requirementやTRの複製、workflow stateの管理を行いません。
7. QA要求の変更では、source revisionと旧版との差を確認し、影響する要求だけを要再確認にします。無関係なcurrent成果物を一括stale化しません。
8. 最終出力前に入力・状態・成果物を`references/guidance.md`の品質ゲートで確認します。領域判断を要する不足は補わず、未解決の制約と担当・再開条件を明示します。

## 入出力

- **入力**: QA依頼・stakeholder要求、対象製品／release／build／期間、利用可能なProject Context、現行仕様・Risk、既存QA要求と履歴。
- **出力**: QA目的、品質目標、対象・対象外、成功条件、要求元、制約、情報源とrevision、未決事項、承認参照、architecture／計画への正規ref。
- **開始範囲**: 初回要求整理、既存要求の改版、要求のcurrentness確認。既存成果物からの途中開始では、要求の再作成を強制しません。

## 正規出力

`assets/output-template.md`の形式を使います。安定IDは当該artifactとscope内だけで一意とし、保存先から発行されたartifact ref・revisionと合わせて追跡します。保存・承認providerが未接続なら提案／草案のまま扱い、正式保存・認証済み承認を宣言しません。

## 次の担当

- QA全体のレベル／方式／環境割当: `test-architecture-design`
- 個別の製品検証責務: `test-requirement-design`
- 不明点・競合: `question-analysis`、`spec-analysis`
