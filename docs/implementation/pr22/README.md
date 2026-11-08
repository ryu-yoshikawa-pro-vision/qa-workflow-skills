# PR #22 並行実装の統合管理

## 方針

2026-11-08の利用者指示により、**各担当の最終統合先は[PR #22](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)の作業branch `feat/development-qa-traceability`**とする。既存Plan索引には計画作成時点の「文書変更PR」という記述があるが、この新しい指示に従い、PR #22で実装の統合・全条件の検証を行う。

- 担当A〜Jは、PR #22のcommit `718005961ade89a848788e8ad3a354d4c711b84a`から分岐した10 branch。
- 各PRはDraftで作成。初期差分は**担当範囲・着手条件・完了条件のMarkdownのみ**。実装済みを意味しない。
- A〜Jの単独テスト成功だけでPR #22全体を完了にしない。親Planの15＋10完了条件、詳細01〜08、S1〜S17、編集8ケース、実Agent／実runner／実providerの証拠を必要とする。
- この一覧は統合管理用。各担当の作業内容・着手／完了基準は**各branchのMarkdown**を参照する。

## 担当PR

| 担当 | PR | 主な責務 | 作業定義 |
| --- | --- | --- | --- |
| A | [#23](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/23) | 共有runtime・評価・CIの編集owner／全条件の統合判定 | [共通runtime・保存・CI・統合](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-a-runtime-integration/docs/implementation/pr22/A_runtime-integration.md) |
| B | [#24](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/24) | 案件配置・機能ID・開発差分・情報源母集団 | [Project Context・機能分析](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-b-context-feature/docs/implementation/pr22/B_context-feature.md) |
| C | [#25](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/25) | ui-target-v1と人間編集8受入 | [UI分析・人間編集](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-c-ui-human-editing/docs/implementation/pr22/C_ui-human-editing.md) |
| D | [#26](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/26) | item／condition候補・stable IDと照合 | [テストアイテム・共通条件](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-d-item-condition/docs/implementation/pr22/D_item-condition.md) |
| E | [#27](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/27) | Risk→TR→TCN/CI→TC・E2E選定 | [正式設計・E2E選定](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-e-formal-design-e2e-selection/docs/implementation/pr22/E_formal-design-e2e-selection.md) |
| F | [#28](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/28) | QA要求・方式・計画／開始・終了基準 | [QA要求・アーキテクチャ・管理](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-f-qa-planning-architecture/docs/implementation/pr22/F_qa-planning-architecture.md) |
| G | [#29](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/29) | API／バッチ／Vitest・静的テスト・runner／cleanup | [非E2E testware・実行](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-g-non-e2e-testware/docs/implementation/pr22/G_non-e2e-testware.md) |
| H | [#30](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/30) | testware route・必須補助・Activity判定 | [Regression・Activity](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-h-regression-routing/docs/implementation/pr22/H_regression-routing.md) |
| I | [#31](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/31) | identity／scope・read revision・探索直接開始 | [QA Knowledge・探索](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-i-knowledge-exploration/docs/implementation/pr22/I_knowledge-exploration.md) |
| J | [#32](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/32) | 外部Issue／元実測の集計完全性・改善の効果確認 | [欠陥・統合報告・活動評価](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/feat/pr22-j-defects-reporting-evaluation/docs/implementation/pr22/J_defects-reporting-evaluation.md) |

## 実装開始の共通条件

- [ ] [Plan索引](../../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)と[開発連動QA Plan](../../plans/2026-11-07_122247_development-qa-traceability.md)、[QA全工程Plan](../../plans/2026-11-07_170134_qa-full-process-implementation.md)、詳細01〜08を担当ごとに確認した。
- [ ] 各担当の編集owner・共有ファイルの書込み担当と、既存Skill／runtime／テスト・現在の`main`・PR #17／#10との重複を確認した。
- [ ] source／artifact ref・revision・evidence・承認・native CAS・blocked／resumeの引継ぎ条件を定めた。必要な外部接続が未決定ならその範囲をblockedにした。
- [ ] 対象案件と検証基準を固定した。実製品で不足する技術だけ独立fixtureを用い、実製品の代替成功にはしない。

## 共有ファイルの編集owner

| 共有箇所 | 書込みowner |
| --- | --- |
| `skills/qa-workflow/scripts/**`、Project Contextの共有template、共通評価runtime、`EVALS.md`、共通CI・全体README | A |
| `skills/spec-analysis/scripts/ui_target_package.py`およびUI関連既存経路 | C |
| `test-analysis`、正式TR／TCN／CI／TC・coverage既存Skill | E |
| `adversarial-review`、`test-execution`の対象拡張 | G |
| `regression-testing/**` | H |
| `qa-knowledge/**`・探索接続 | I |

B／D／F／Jは原則として新設Skillと担当固有のテストを変更する。共有ファイルの変更が必要なら上表のownerに要件・fixture・検証条件を引き渡し、同時編集しない。PR #17が共有runtimeや評価データを変更している場合は、統合時点の差分を再確認する。

## 並行実装と統合の順序

1. Aが最小限の共通契約を提示し、B／C／D／F／G／Iを独立着手可能にする。E／H／Jも合意済みfixtureにより並行実装してよい。
2. D→E、G→H、F／G／H／I→Jなどの依存は、最初に契約fixture、後からownerが実際に保存した成果物・revisionで統合検証する。
3. 担当PR内で局所受入・既存互換・負例を確認し、検証証拠と未実施／blockedをPR本文に追記する。親Planの完了条件は担当間に割り当てても削除しない。
4. PR #22へ取り込んだ差分を統合側で再検証する。**本管理ファイルの作成は各担当PRのmerge権限を意味しない**。
5. 全ownerの正規成果物・保存・承認・runner・source現在性・別セッション再開を使い、S1〜S17、人間編集8ケース、詳細01〜08、15＋10の完了条件をすべて判定する。
6. 詳細07の初回／変更なし／局所コード変更／外部仕様改版／中断再開について、独立した品質・安全基準と実測効率比較を記録する。未測定・比較不能を改善済み扱いしない。

## 最終統合の完了条件

- [ ] 担当A〜Jの実装範囲・負例・legacy／migration・セキュリティ・回帰テストと未完了事項を全件照合した。
- [ ] 新規14 Skill、既存23 Skillの構造・trigger／routing・意味評価と共有runtime／保存／承認の契約を検証した。
- [ ] 固定された`qa-training-store` commit、独立fixture、実Agent、実runnerで必要な正常／異常／再開シナリオを確認した。
- [ ] 実providerのCAS・履歴・readbackと承認の認証、製品CIの成果物受渡し方式を実接続で検証した。未接続はblockedとして残し、全完了にしない。
- [ ] Plan索引で参照する15＋10完了条件と詳細01〜08の全条件について、証拠ref・結果・残件を残した。
- [ ] 詳細07の効率比較を品質／安全／測定不能と分離して判定し、悪化した範囲の是正・再測定を行った。
- [ ] 統合後の各GitHub Actionsと個別コマンドの結果を確認し、PR #22に未実施／SKIP／blockedを明記した。

## 依存・未決定事項

製品CI向けのローカル成果物受渡し方式、案件ごとの保存provider／認可／外部Issue／実行環境／非機能閾値はPlanで一律に確定されていない。A〜Jが案件の実能力を確認し、選定・実証が必要な条件だけblockedにする。条件未選定を理由に独立可能な読取・設計・局所テストを止めず、未実証なのに最終完了ともしない。

最終merge／close／force push／branch削除／releaseは明示指示まで行わない。
