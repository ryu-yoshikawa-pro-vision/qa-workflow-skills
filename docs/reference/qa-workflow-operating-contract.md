# QAワークフロー共通運用契約

2026-11-25時点のmain（197f1e0e1abe870b0cc793355e7abf73bf241d87）を基準に、利用者とAgentの協働、保存・承認・質問・再開を横断整理する。新しいSkill、schema、中央台帳、保存provider、承認方式を導入しない。

## 確定した設計方針（OPS-18）

2026-11-25 利用者決定（今後の設計に適用）：成果物は指定root配下のディレクトリで統一管理する。案件識別・探索・切替、ブランチ管理、保存技術/Provider・認証方式の選択、配置の都度決定はSkillの責務外。必要な環境条件・許可root・権限をハーネスが提供し、不要な管理は移管せず削除する。Skillは専門的なQAの意味判断、成果物の内容・形式・相対配置、質問・引継ぎに集中し、Helperは決定論的な採番・計算・検証・保存を担当する。案件管理や特定ハーネスの実装、新たな保存基盤を改善の必須要件にしない。

この方針は利用者が承認済みの変更境界であり、現行実装の安全条件を無効にするものではない。下記の現行運用説明にある案件設定・配置合意・Git保存方式等は旧実装を扱う場合の記録であり、今後のSkill設計へ継承する要件ではない。新規/改修Skillでは、ハーネスからの許可済みroot・必要情報・操作可否だけを受け取る。必要なQA業務上のscope、仕様、環境・権限差、DEC/ASM、リスク等は維持する。

<!-- dprint-ignore -->
| 層 | 残す責務 | 削除・責務外 |
| --- | --- | --- |
| Skill | QAの意味判断・必要質問・依存判断・出力契約・相対配置 | 案件識別、保存技術選択、branch管理、認証方式選択 |
| Helper | 採番、検証、相対ref解決、条件付き保存、履歴・readback | 意味判断、権限自己発行、正本の無断上書き |
| ハーネス/実行環境 | 許可root、必要入力、実行条件・権限、必要な状態/隔離 | 不要な案件管理機能の新設、専門QA判断の代行 |

固定ディレクトリ構造は成果物の分類・発見のための契約とする。rootは外部指定。正式成果物・継続作業・保護証跡・テストコードは必要な境界だけ分け、同一構造の事前作成を強制しない。別rootの同名refを同じ正本としない。認可、条件付き更新、履歴、独立readback、冪等性、依存・scope完全性は維持し、保証不能な操作だけ停止する。Skillが不足能力を補うための管理機構を作らない。PR #40の最終構成と実装証拠を確認してから既存Skillを改修する。

## 適用範囲と正本

各SKILL.mdとそのreferenceが工程固有契約の正本。[qa-workflow](../../skills/qa-workflow/SKILL.md)と[詳細契約](../../skills/qa-workflow/references/guidance.md)が全体routingの正本。[保存・承認契約](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)と[人間編集契約](../plans/2026-11-07_170134_qa-full-process-implementation_08_human-artifact-editing.md)を維持する。本書のcheckpointとゲートは運用上の整理であり、全Skillで自動化済みという意味ではない。差異は正本・実装を確認し報告する。

[成果物マトリクス](qa-workflow-artifact-matrix.md)、[利用者マニュアル](qa-workflow-user-guide.md)を併用する。実装改善候補は[改善一覧](../reports/2026-11-25_qa-workflow-operating-improvements.md)に分離する。

## 記述の状態

- 現行契約：正本Skill・Planに規定がある。実provider・実Agentで検証済みという意味ではない。
- 部分実装：helper・validator等の入口が存在するが、全ownerへの接続や真正性等が未確立。
- 運用指針：既存契約の範囲で行う確認手順。未実装の保存・承認・状態遷移を成立させない。
- 改善候補：OPS-01〜18に記録する。OPS-18の責務境界は決定済み。具体的な実装・実環境受入は別途合意し、現行のblocked条件を緩めない。

単発読取は継続保存・配置合意を前提にしない。継続利用の要求がある場合の必要なstate・保存契約は省略しない。利用者は依頼・必要な判断/承認・環境提供・gatedの進行・結果判断を担当し、許可済み範囲の発見・検証・採番・引継ぎはAgentが担当する。

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
| G2 | 任意工程で回答が必要な未解決事項 | Q ID、根拠、影響、回答なしの扱い、再開先 | 仕様回答、正式決定、暫定仮定承認 | owner正規化・根拠反映 |
| G3 | QA要求・方式・計画の確定/改版前 | 目的、品質目標、方式、計画、基準、対象revision | 権限者の承認 | 各ownerの保存・承認契約 |
| G4 | 正式保存・外部書込み・副作用開始前 | 操作、scope、保存先、before revision、差分、権限、上限、cleanup | 必要な承認・認証・条件提供 | 認可、必要preflight、ownerの原子的開始契約またはclaim、必要予約。保存後readback |
| G5 | 報告・改善採用・引継ぎ | 実測、未実行、残存risk、終了基準、改善案 | 必要時にリスク受容、リリース判断、採否、受領 | 正本ownerの記録と必要な認証済み承認 |

gatedによる停止は別途必要。質問・承認をまとめる場合は独立した回答単位、対象scope/revision、保留、拒否、失効を区別する。集約の自動化は未実証。承認対象を勝手に拡張しない。初回配置合意・工程進行は個々の正式保存を包括承認しない。承認は操作種別、対象scope/ref/revision、差分、build/source、承認者、理由、必要な有効期間・失効条件に束縛する。

## 質問から再開まで

1. 担当Skillが情報源優先順位、既存DEC/ASM、既存質問・回答を確認する。解消済みの論点を再質問せず、期待仕様が確定した実装差異を仕様質問へ戻さない。
2. [question-analysis](../../skills/question-analysis/references/guidance.md)がQ ID、関連UNKNOWN、根拠、影響、停止範囲、正規化先、再開ownerを確定する。
3. ブロッカーは影響scope停止。要確認は可視化して継続。仮定可能はドラフト等で継続できるが正式PASS/FAILには権限者の明示承認とASM正本への反映が必要。提案・任意は継続。
4. 単発は対話/Markdownで提示。複数質問をHTMLで渡す必要がある場合だけ[agent-answer-form](../../skills/agent-answer-form/SKILL.md)を利用する。Skill外の許可済み作業dirにquestions.jsonとanswer-form.htmlを生成し、Q ID・元質問成果物を維持して双方を利用者へ渡す。質問ID・選択肢の意味が変わる場合は旧HTMLを保管し、旧ブラウザ回答を新定義へ自動適用しない。秘密情報を含めない。保留や推奨案は承認ではない。
5. 質問で中断する前に分析済み成果物、未解決質問、停止scope、入力revision、再開先を保全する運用指針とする。既に許可された作業領域がある場合に限り候補・質問・再開情報を中間保存できる。正式保存はG4の必要な承認・保存条件を満たす場合だけ行い、draftをcurrentとしない。安全な作業領域が未設定、保存未承認・失敗の場合は質問自体を止めず、未保存範囲と安全な候補・再開情報を利用者に返す。別session復元は保証しない。横断自動化と中間保存の許可範囲の整備はOPS-01/02/16の改善候補。
6. 回答受領後、元Q ID・元質問定義・根拠を照合し、意味や根拠が変わった旧回答は再確認する（revisionとの機械的束縛はOPS-01/13の改善候補）。更新された権威ある仕様はSPEC、権限者の正式決定はDEC、明示承認された暫定合意は承認済みASMへ正規化。有効なSPEC/DECISIONをASMで上書きしない。意味が不明なら再確認。担当正本へ反映し、回答文をそのまま期待結果にしない。
7. current質問一覧は未解決のみ。使用済みQ IDは履歴へ残し別論点へ流用しない。意味同一性を担当Skillが判断し、既存question_ids.py materializeで前回成果物を用いて更新する。qa-workflowが意味が変わる最も早い担当工程に戻し、依存scopeだけ再検証する。

## 保存先・保存領域（現行契約の記録）

現行配置は[Q06](../plans/2026-11-07_122247_development-qa-traceability.md)に従う。初回は対象案件・許可された探索入口・既存Project Context候補・読取権限を確認し、候補列挙が完全な場合だけ不存在と判断する。重複・アクセス不能・案件不一致は未解決とし、勝手に新規正本を作らない。既存配置・正本・有効な配置合意を優先し、初回または変更時だけ合意する。Section 12/14・16と各ownerの保存契約を利用する。標準root・命名がない成果物の現状は[マトリクス](qa-workflow-artifact-matrix.md)を参照。

次の4領域は混同防止のための論理分類（運用指針）。新規root/provider/権限を自動作成しない。横断的な標準配置・命名・発見・初期化契約はOPS-09/12〜17の改善候補。

<!-- dprint-ignore -->
| 領域 | 内容 | 扱い |
| --- | --- | --- |
| 正式成果物 | 正本、確定判断、正式報告、継続資産 | ownerの保存・承認・履歴・readback |
| 継続作業 | draft、未解決Q、フォーム、編集案、再開情報 | 明示許可された領域のみ。正本としない |
| 保護証跡 | rawログ、trace、動画、snapshot、runner出力 | 保存可否・機密性・アクセス・保持・cleanupを確認 |
| テストコード | Playwright、非E2E testware、fixture、設定 | 対象repoの既存構成・変更権限 |

Skill記述はsandbox・hook・OS/provider権限の代替ではない。PR #22の運用制約に従い、必要な書込み・読取・認証・実行境界を環境側でも確認する。必要な境界を確認できない操作は止める。横断的な強制・受入は未実証（OPS-16）。一時物cleanupで正式履歴や未解決の再開情報を消さない。

## 保存・承認・履歴（現行契約の記録）

Project ContextのSection 4/12〜14/16を確認する。既存正本と配置を維持し、変更時だけ合意を更新する。案件固有の資料・証跡をSkill assetsや本repositoryへ自動commitしない。

- 新規はnative atomic create-if-absent、更新は期待revisionを条件にしたnative CAS。必要な履歴・独立readback・認可が不足すれば正式保存をblockする。read-compare-unconditional-writeはCASではない。
- 保存前にowner、scope、artifact ref、source refs/revisions、変更理由、期待revision、必要承認・権限、再開ownerを確定。保存後は独立読戻しで本文/hash・revisionを確認する。実際に取得した参照のみ下流へ渡す。
- draft、形式valid、意味上の完成候補、実保存状態、認証済み承認、currentness、workflow完了を別々に扱う。書込み応答消失・readback不一致・承認照合不能では外部先が旧revisionのままと断定しない。最後の検証済みbaselineと候補を保全し、実ref/revision/hash/操作結果・承認を独立再取得するまで新成果物をcurrentとして引き渡さない。同一副作用の盲目的再試行、無条件上書き、無断rollback・別正本作成をしない。
- 複数owner・複数ファイルの個別CASは一括整合の証明ではない。commit/snapshot境界と依存ref/revisionを固定し、部分保存・中断時は実際に確定したものと未確定を分けて保持する。必要な参照整合・owner検証が成立するまで依存する下流をcurrentにしない。独立scopeは継続可能。一体更新を要求する既存packageのwriter境界を守る。汎用分散transactionや自動rollbackは前提としない。
- Git案件の既定承認は2026-11-12利用者決定に従う。操作・scope・ref/branch・before SHA・差分提示 → 対話で明示同意 → 保存直前のrevision・権限確認後、合意したwrite権限のある利用者の認証済みアカウントで通常push（force禁止）→ repository activity APIのactor/before/after照合と保存本文の独立readback。取得遅延は共通契約に従い再取得し、確認不能なら正式保存・承認確定はblocked（物理的書込みの成否は別途確認）。commit author・PRコメント・LLM approvedだけでは認可証拠にならない。別方式は案件で合意。全ownerの実接続は未実証。
- secret・cookie・token・個人情報等のraw証跡を無断永続化・共有しない。必要最小限の事実・参照と非保存理由を記録する。

## Checkpoint

以下は既存契約を横断する運用指針。永続化を要求しない単発読取まで保存を強制しない。正式保存先未合意はG1へ戻す。各ownerの正式writerを使う。状態欄は主な実装境界を示し、全ownerの自動化・実環境PASSを意味しない。

<!-- dprint-ignore -->
| ID | イベント | owner | 記録・保存内容 | 失敗時 | 状態・制約 |
| --- | --- | --- | --- | --- | --- |
| CP01 | 開始・再開 | qa-workflow | 元依頼・要求成果物・要求scope、入力母集団/revision、既存state、再利用/再実行判断 | 未取得scope明示、旧baseline保持 | 現行＋指針：宣言・列挙完全性は呼出し側 |
| CP02 | 案件設定合意・更新 | project-context | Context、DEC/ASM、配置参照、revision | draft保持・正式保存block | 部分：対応providerのみ |
| CP03 | 質問提示・中断前 | question-analysis / qa-workflow | Q/UNKNOWN、元質問定義、候補、停止scope、再開先、完了済み参照 | 未保存明示・再開情報提示 | 指針：許可中間保存と正式保存を区別 |
| CP04 | 回答反映後 | 仕様・決定・仮定owner | SPEC/DEC/ASM、質問履歴、影響refs | 未解決として保持 | 現行の正規化＋指針：横断保存未実証 |
| CP05 | 工程引継ぎ前 | 担当Skill | 成果物、ID、依存revision、validator、必要な保存結果 | stale/未保存/不適合を区別 | 部分：owner別保存・検証 |
| CP06 | mutable operation開始直前 | 操作owner / qa-workflow | 対象、認可、期待revision、owner開始契約/claim、必要予約、上限・cleanup | 実操作を開始しない | 部分：予約・claim回復未接続あり |
| CP07 | 実行後・異常停止 | 実行owner | raw結果、attempt、観測、実開始、cleanup、未実行・判定不能 | 元証跡保持、盲目的再試行禁止 | 現行owner契約＋部分：保存接続 |
| CP08 | 上流変更・中断再開 | qa-workflow / owner | affected scopes、source差分、要再検証、旧revision | 関連範囲のみ停止 | 現行＋指針：入力完全性を確認 |
| CP09 | 正式保存後 | owner/provider | 独立readback、hash、revision、認可証拠、引継ぎref | 結果不明を再取得、最後の検証済みbaseline保持 | 部分：実provider・承認真正性 |
| CP10 | 完了判定 | qa-workflow | 元依頼とのscope照合、全要求scope検証、残存risk、必要レビュー、完了baseline | blocked/部分完了/未検証を明示 | 部分：未登録owner・要求集合完全性 |

## State・変更・人間編集

persisted workflow stateはqa.workflow_state_root配下のcanonical UUID.json。claimは同rootのclaims/<identity digest>.json。input-revisions.jsonは指定成果物保存先に置く。Regression/Exploration履歴rootとは別。WCAG固有stateの対応local SQLiteは汎用保存providerではない。

再利用前に要求scope、入力母集団・依存関係の列挙完全性、source revision、利用したProject Contextのused fields、担当ownerの意味契約・currentness・追跡情報を確認する。input_revision.pyは渡されたpathだけを比較し、sameだけでは完全性を証明しない。変更・追加・削除は依存scopeを要再検証とし、無関係な成果物を再生成しない。途中中断は有効なstateと検証済み成果物から再開し、前提が変われば影響scopeへ戻る。要求された継続stateの保存先未解決はblockする。入力完全性の横断受入はOPS-05/15。

mutable operation（正式保存・外部Issue更新・副作用操作等）の前は同一identity向けownerの原子的claimまたは冪等開始契約を優先し、存在しない場合は既存qa-workflow claim契約に従う。claimは認可・実行成功・遠隔CASの証明ではない。実開始・実保存・cleanup・claim revisionを独立取得できない場合は同一identityの副作用を自動再実行しない。実分離を確認できない共有resourceは必要な予約・解放providerが未接続ならblock。同一案件の並列workflowはPR #22の運用制約に従い共有予約・分離の確認まで避ける。

PR/merge/release/外部仕様改版は呼出し側が起動し、変更元ownerが差分を扱う。人間は配置・編集合意に従い作業用branch/copyで編集し、未確定差分をcanonical rootへ直接反映しない。元revision・差分・根拠・編集者・レビュー承認を別々に追跡し、ownerの意味検証と既存writerを経て反映。作業branchへのpushは編集提出であり正本更新承認とは別。

ui-target-v1固有の規則としてMANIFEST、生成README metadata、機械生成CHANGELOG、Machine Entity、標準heading/file名を手編集しない。新規行はdraft keyで提案し、手動IDや行削除を正式採番・廃止にしない。正本直接改変時は元snapshotと編集案を保全し、元revision・復旧権限がなければblocked。他成果物は各ownerの編集・履歴・validator契約を使用し、UI package固有制約を一律流用しない。

## 完了・制約

開始時に元依頼・要求成果物・必須scope・除外候補の対応を確認し、完了時に元依頼と宣言済みrequested_scopesを再照合する（運用指針）。最終runtime gateは宣言済み集合の欠落・未検証を検出するが宣言自体の完全性は保証しない。除外は現行runtimeでは承認真正性の照合が未接続のため必須scopeのまま残り完了不可。未登録ownerはunverified_scopes。最終gate・owner検証・必要レビューに従い、can_completeだけで完了を宣言しない。runtime-v2の最終baselineは既存immutable snapshot・exact refetch・state CAS契約を使用し、失敗時は最後の検証済みbindingを維持する。

<!-- dprint-ignore -->
| 判定軸 | 意味 |
| --- | --- |
| 成果物完成 | 担当Skillの意味・形式契約と必要検証 |
| 正式保存・承認 | provider保存・独立readback・認証済み承認。各状態は別 |
| 実行完了 | 実開始、予定母集団、観測、収集、必要cleanup |
| テスト合否 | PASS/FAIL/未実行/判定不能等を実測で判定 |
| 報告・終了基準 | 取得完全性、計画母集団、指標、終了基準を独立判定。母集団不明なら全体率・終了判定はundetermined |
| Workflow完了 | 元依頼・要求scope、必要owner検証・currentness・実行・報告・保存・cleanup等の充足 |
| リリース承認 | 権限者が残存リスクを判断。Workflow完了やFAILの有無と別 |

FAILは必要工程の完了と両立し得る。FAILだけでWorkflow未完了とせず、必要な未実行・判定不能・cleanup未確認等が残る場合は該当scopeを完了としない。

[PR #22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md)の最終受入未達を維持する。実provider・承認・製品CI・reservation/claim回復・owner verifierの未接続と効率改善未実証を、文書追加で解消済みとしない。過去に承認された対象外は維持し、今回の改善で検証を追加する場合は新しい実装・受入範囲として合意する。
