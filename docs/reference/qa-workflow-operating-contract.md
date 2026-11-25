# QAワークフロー共通運用契約

2026-11-25時点のmain（197f1e0e1abe870b0cc793355e7abf73bf241d87）を基準に、利用者とAgentの協働、保存・承認・質問・再開を横断整理する。新しいSkill、schema、中央台帳、保存provider、承認方式を導入しない。

## 適用範囲と正本

各SKILL.mdとそのreferenceが工程固有契約の正本。[qa-workflow](../../skills/qa-workflow/SKILL.md)と[詳細契約](../../skills/qa-workflow/references/guidance.md)が全体routingの正本。[保存・承認契約](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)と[人間編集契約](../plans/2026-11-07_170134_qa-full-process-implementation_08_human-artifact-editing.md)を維持する。本書のcheckpointとゲートは運用上の整理であり、全Skillで自動化済みという意味ではない。差異は正本・実装を確認し報告する。

[成果物マトリクス](qa-workflow-artifact-matrix.md)、[利用者マニュアル](qa-workflow-user-guide.md)を併用する。実装改善候補は[改善一覧](../reports/2026-11-25_qa-workflow-operating-improvements.md)に分離する。

## 責務と進行モード

<!-- dprint-ignore -->
| 主体 | 担当 | 代行しないこと |
| --- | --- | --- |
| 利用者・権限者 | 目的・対象・成果物指定、仕様決定、計画・保存・実行承認、リスク受容 | ID採番・機械的検証・既知資料の再入力 |
| 呼出し側 | PR/merge/release/資料改版・定期起動、認証済み接続の提供 | Skillの意味判断 |
| qa-workflow | 要求scope、開始点、再利用、routing、停止・再開、変更伝播、完了 | 個別成果物の意味判断 |
| 各担当Skill | 正本の意味判断・候補作成・根拠・履歴・担当validator | 他ownerの正本の無断変更 |
| Runtime/helper | ID、schema、fingerprint、coverage、currentness等の決定論的検証 | 仕様・リスク・承認の捏造 |
| 保存provider・認可元 | 原子的保存・履歴・独立readback・認証済み権限 | 自己申告による成功認定 |
| レビュー担当 | 独立反証・指摘・修正先 | 正本ownerの無断上書き |

continuousが既定。次工程へ利用可能なら要求成果物まで進み、局所ブロッカーだけ停止する。gatedは現在Skillの成果物提示後に停止し、進行指示を待つ。優先順位は利用者明示指示 > Project Context > continuous。ゲートグループ化は設定欄があるが、実際の制御保証は別途確認する。進行指示、仕様決定、正式保存承認、実操作認可、リリース判断は別。

## ユーザー介入ゲート

G1〜G5は運用上の分類であり固定実行順序や新しいruntime stateではない。既存承認のscope・revision・失効条件が有効なら不要な再確認をしない。

<!-- dprint-ignore -->
| ID | タイミング | Agentが提示 | 利用者の対応 | 継続条件 |
| --- | --- | --- | --- | --- |
| G1 | 初回正式書込み前・配置/設定変更時 | 既存正本、配置維持案、owner、編集範囲、保存先、権限、未決事項 | 案件設定・配置合意 | 合意と必要provider能力。独立読取は先行可 |
| G2 | 任意工程の未解決事項 | Q ID、根拠、影響、回答なしの扱い、再開先 | 仕様回答、正式決定、暫定仮定承認 | owner正規化・根拠反映 |
| G3 | QA要求・方式・計画の確定/改版前 | 目的、品質目標、方式、計画、基準、対象revision | 権限者の承認 | 各ownerの保存・承認契約 |
| G4 | 正式保存・外部書込み・副作用開始前 | 操作、scope、保存先、before revision、差分、権限、上限、cleanup | 必要な承認・認証・条件提供 | 認可、preflight、claim、必要予約。保存後readback |
| G5 | 報告・改善採用・引継ぎ | 実測、未実行、残存risk、終了基準、改善案 | 必要時にリスク受容、リリース判断、採否、受領 | 正本ownerの記録と必要な認証済み承認 |

gatedによる停止は別途必要。質問・承認をまとめる場合は独立した回答単位、対象scope/revision、保留、拒否、失効を区別する。集約の自動化は未実証。承認対象を勝手に拡張しない。

## 質問から再開まで

1. 担当Skillが情報源優先順位、既存DEC/ASM、既存質問・回答を確認する。解消済みの論点を再質問せず、期待仕様が確定した実装差異を仕様質問へ戻さない。
2. [question-analysis](../../skills/question-analysis/references/guidance.md)がQ ID、関連UNKNOWN、根拠、影響、停止範囲、正規化先、再開ownerを確定する。
3. ブロッカーは影響scope停止。要確認は可視化して継続。仮定可能はドラフト等で継続できるが正式PASS/FAILには権限者の明示承認とASM正本への反映が必要。提案・任意は継続。
4. 単発は対話/Markdownで提示。複数質問をHTMLで渡す必要がある場合だけ[agent-answer-form](../../skills/agent-answer-form/SKILL.md)を利用する。Skill外の作業dirにquestions.jsonとanswer-form.htmlを生成しQ IDを保持。保留や推奨案は承認ではない。
5. 質問で中断する前に、許可された保存先へ分析済み成果物、未解決質問、停止scope、入力revision、再開先を記録する運用とする。保存できない場合は未保存を明示し候補・再開情報を返す。これは横断checkpointの運用指針であり、全ownerの自動永続化を保証しない。
6. 回答受領後、元Q IDと照合し、更新された仕様はSPEC、正式決定はDEC、暫定合意は承認済みASMへ正規化。意味が不明なら再確認。担当正本へ反映し、回答文をそのまま期待結果にしない。
7. 解決済みQ IDの履歴を保持し、別論点へ流用しない。同一論点の再開は既存IDを使用。qa-workflowが意味が変わる最も早い担当工程に戻し、依存scopeだけ再検証する。

## 保存・承認・履歴

Project ContextのSection 4/12〜14/16を確認する。既存正本と配置を維持し、変更時だけ合意を更新する。案件固有の資料・証跡をSkill assetsや本repositoryへ自動commitしない。

- 新規はnative atomic create-if-absent、更新は期待revisionを条件にしたnative CAS。必要な履歴・独立readback・認可が不足すれば正式保存をblockする。read-compare-unconditional-writeはCASではない。
- 保存前にowner、scope、artifact ref、source refs/revisions、変更理由、期待revision、必要承認・権限、再開ownerを確定。保存後は独立読戻しで本文/hash・revisionを確認する。実際に取得した参照のみ下流へ渡す。
- draft、形式valid、意味上の完成候補、保存済みcurrent、承認済み、workflow完了を別々に扱う。競合やreadback失敗時は候補と旧currentを保全し、無条件上書き・無断別保存先作成をしない。
- Git案件の既定承認は2026-11-12利用者決定に従う。操作・scope・ref/branch・before SHA・差分提示 → 対話で明示同意 → 合意した認証済みアカウントで通常push（force禁止）→ repository activity APIのactor/before/after照合。取得遅延は共通契約に従い再取得し、確認不能なら未承認・blocked。commit author・PRコメント・LLM approvedだけでは認可証拠にならない。別方式は案件で合意。全ownerの実接続は未実証。
- secret・cookie・token・個人情報等のraw証跡を無断永続化・共有しない。必要最小限の事実・参照と非保存理由を記録する。

## Checkpoint

以下は既存契約を横断する運用指針。永続化を要求しない単発読取まで保存を強制しない。保存先未合意はG1へ戻す。各ownerの正式writerを使う。

<!-- dprint-ignore -->
| ID | イベント | owner | 記録・保存内容 | 失敗時 |
| --- | --- | --- | --- | --- |
| CP01 | 開始・再開 | qa-workflow | 要求scope、入力revision、既存state、再利用/再実行判断 | 未取得scope明示、旧baseline保持 |
| CP02 | 案件設定合意・更新 | project-context | Context、DEC/ASM、配置参照、revision | draft保持・正式保存block |
| CP03 | 質問提示・中断前 | question-analysis / qa-workflow | Q/UNKNOWN、候補、停止scope、再開先、完了済み参照 | 未保存明示・再開情報提示 |
| CP04 | 回答反映後 | 仕様・決定・仮定owner | SPEC/DEC/ASM、質問履歴、影響refs | 未解決として保持 |
| CP05 | 工程引継ぎ前 | 担当Skill | 成果物、ID、依存revision、validator、必要な保存結果 | stale/未保存/不適合を区別 |
| CP06 | mutable operation開始直前 | 実行owner / qa-workflow | 対象、認可、期待revision、claim、必要予約、上限・cleanup | 実操作を開始しない |
| CP07 | 実行後・異常停止 | 実行owner | raw結果、attempt、観測、実開始、cleanup、未実行・判定不能 | 元証跡保持、盲目的再試行禁止 |
| CP08 | 上流変更・中断再開 | qa-workflow / owner | affected scopes、source差分、要再検証、旧revision | 関連範囲のみ停止 |
| CP09 | 正式保存後 | owner/provider | 独立readback、hash、revision、認可証拠、引継ぎref | 成功とせず旧current保持 |
| CP10 | 完了判定 | qa-workflow | 全要求scope検証、残存risk、必要レビュー、完了baseline | blocked/部分完了/未検証を明示 |

## State・変更・人間編集

persisted workflow stateはqa.workflow_state_root配下のcanonical UUID.json。claimは同rootのclaims/<identity digest>.json。input-revisions.jsonは指定成果物保存先に置く。Regression/Exploration履歴rootとは別。WCAG固有stateの対応local SQLiteは汎用保存providerではない。

入力revision同一でcurrentなら再利用し、changed/added/removedは依存範囲だけ再実行。途中中断はstateの次工程から再開。claimは認可・実行成功の証明ではない。実状態、cleanup、保存revisionを独立取得できない場合は同一identityの副作用を自動再実行しない。安全な解放・予約provider未接続はblock。

PR/merge/release/外部仕様改版は呼出し側が起動し、変更元ownerが差分を扱う。人間は承認済み作業用branch/copyで編集し、canonical packageを直接置換しない。元snapshot・差分・根拠・レビュー承認を別々に追跡し、ownerの意味検証と既存writerを経て反映。MANIFEST、生成metadata、CHANGELOG、Machine Entity、標準heading/file名を手編集しない。手動IDや行削除を正式採番・廃止にしない。

## 完了・制約

要求集合・必要レビュー・最終runtime gate・owner verifierに従う。未検証scopeや承認真正性を確認できない除外は完了不可。FAILが残っても要求された実行・分析・報告・cleanupが完了すればworkflow完了とは別に扱う。リリース判断は人間。

[PR #22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md)の最終受入未達を維持する。実provider・承認・製品CI・reservation/claim回復・owner verifierの未接続と効率改善未実証を、文書追加で解消済みとしない。
