# 成果物・コンテキスト・保存先の改修

## 目的・対象

OPS-09・12〜14・16・17・18。指定がない通常のQA依頼でも、人間が利用しやすい成果物を一貫した場所に保存し、既存資産を変更せず再利用する。全39 Skillを対象とし、共通成果物マトリクスと各ownerの契約を改修する。保存・承認の実処理は02、currentnessは03、実行証跡の操作条件は04で扱う。

## 現状・既存契約

- `skills/project-context/SKILL.md`、`scripts/project_context.py`（同Skill配下）の `discover`、`prepare_create`、`prepare_sections`、`prepare_update`、`prepare_ids`、`placement`、`prepare_placement`、`persist_prepared` は案件発見・初回配置合意・owner・保存能力を含む。
- `skills/qa-workflow/assets/project-context-template.md` Section 10/14/16、`scripts/artifact_graph.py` の `parse_project_context`、`validate_required_context_fields`、`compare_used_context`、`workflow_state_root_from_project_context` 等は既存入力・状態解決に利用される。
- 計画3 Skillの正本はcanonical JSON、Markdownは描画物。各 `references/data-contract.md` のpacket項目とMarkdown表の対応、各 `assets/output-template.md`、owner runtime、`qa-workflow/scripts/owner_verifiers.py` に依存がある。
- UI target packageの固定構造・single writer、Knowledgeのentry-ref、#40の3 kindと履歴、runtime-v2のMachine Entity、runnerのraw形式は個別の機械契約を持つ。

## 実装1 保存先・指定の解決

全Skillの保存先解決を次の順に統一する。必要な成果物の有無を先に判断し、単発の相談・読取・レビュー・調査に保存先確認を要求しない。

1. 現在の依頼で利用者が指定した保存先・形式・命名・履歴・運用ルールを適用する。既存資産の変更を伴う場合は勝手に上書き・移行しない。
2. 明示された成果物ref、許可された作業範囲にある既存の有効な規則・正本を適用する。既存ファイルを更新する場合は元の場所・IDを維持する。既存ルールとの矛盾があれば必要な論点だけ確認する。
3. 指定がなく新規作成する場合、現在のAgentが書込みを許可された作業ディレクトリの `qa/` を既定の成果物rootとする。既にQA専用rootが指定・認識されている場合はその直下を利用し、`qa/qa/` を作らない。対象repoの読取許可だけを保存許可にしない。外部情報源repoを成果物rootとして推測しない。sandbox等から許可範囲が判断できなければ、必要な保存先・許可のみ質問する。
4. 必要時の質問は「保存先・形式・運用ルールに指定はありますか。なければ標準で進めます」を基本とする。既知の指定・既存規則は再質問しない。専用Provider、CAS、revisionの方式選択を利用者に求めない。指定が必須の意味・安全条件と両立しない場合は具体的な制約と可能な方法を説明する。
5. refは指定root内の実在する正本または許可direct refへ解決する。symlink、path traversal、別root同名、読取不能、列挙不全、重複を区別し、曖昧な正本への新規作成・更新だけ停止する。通常保存のための専用ハーネス・案件登録・root登録CLI・新しい全成果物indexは作らない。

既定の相対配置は以下。利用者指定・既存配置が優先する。機械形式を独自形式へ変える指定は、必要な検証と相互利用が維持できる場合に適用する。

## 実装2 39 Skillの標準配置・保存粒度

`<root>` は前節で解決した成果物root。以下の `<scope>` は既存の機能ID・対象ID・安定scope refを優先したディレクトリ名。案件横断は `common`。明示的に区別される複数対象・build・環境・Runを同じ正本へ上書きしない。ID未付与の単発新規成果物では利用者指定の対象名を安全なファイル名にし、既存ref/対象との衝突時のみ既存ID又は正規scopeのdigestを付ける。ID自体はファイル名から生成しない。Windows等の禁止文字、大小文字衝突、`.`・`..`・予約名、root逸脱を既存ファイル操作で拒否する。必要なディレクトリだけ生成する。

表のファイル名は本Planの提案する新規成果物の既定値。既存writerがファイル名・内部構造を固定しているものは、そのwriterの契約を維持する。`<run>`、`<attempt>`、`<snapshot>`、`<entry-ref>`、`<workflow-ref>` は担当ownerの既存識別子を用いる。正式な正本が存在する場合はこの表より既存refを優先する。

<!-- dprint-ignore -->
| Skill | 新規の既定相対path | 正本・保存粒度/例外 |
| --- | --- | --- |
| qa-workflow | `state/`、必要時 `reports/<scope>/workflow.md` | 既存UUID/SQLite/baseline/claim・input-revisions.jsonの契約を維持。必要時のみstate。報告は同じ状態の複製台帳にしない |
| project-context | `context/PROJECT_CONTEXT.md` | QA目的・用語・DEC/ASM・環境等の共通文書。既存正本優先、必須の初期化なし |
| feature-analysis | `features/feature-registry.json` | 現行snapshotのschema・source inventory・ID・履歴。既存writer固定名があれば維持 |
| spec-analysis | `specifications/<scope>/specification.md` | Authority・US/UC/Behavior/AC/UNKNOWN、Machine Entity。UI package利用時はその専用構造、別正本を作らない |
| ui-target-analysis | `specifications/<scope>/ui-target/` | ui-target-v1内部構造、既存single writer・履歴 |
| question-analysis | `questions/<scope>/questions.md` | Q ID、根拠、元質問・回答履歴、状態・再開先。同一論点を重複発行しない |
| agent-answer-form | `questions/<scope>/forms/<既存form IDまたは論点集合ID>/` | `questions.json`・`answer-form.html`、必要な旧定義/HTML・回答。単発フォームは指定先/許可作業dir |
| test-requirements-analysis | `planning/<scope>/requirements.md` | 新規の構造化Markdown正本。既存JSONの読取互換を維持 |
| test-architecture-design | `planning/<scope>/architecture.md` | 同上、割当・制約・根拠・承認 |
| test-management | `planning/<scope>/plan.md` | 同上、計画・予定母集団・基準・履歴、独立の必要snapshotは既存形式 |
| test-analysis | `analysis/<scope>/risk-analysis.md` | Risk・重点・技法候補、Machine Entity |
| test-item-analysis | `analysis/<scope>/test-items.json` | test-item-candidates-v1、ID・親子・履歴 |
| test-condition-analysis | `analysis/<scope>/condition-candidates.json` | test-condition-candidates-v1、共有条件はcommonに一度だけ保存 |
| test-requirement-design | `design/<scope>/requirements.md` | TR・Machine Entity・runtime契約 |
| test-condition-design | `design/<scope>/conditions.md` | TCN/CI・Disposition・runtime契約 |
| test-case-design | `design/<scope>/test-cases.md` | TC・データ・期待結果・runtime契約 |
| e2e-test-selection | `automation/<scope>/selection.json` | 選定record・理由・履歴。owner verifierが要求する既存canonical形式を維持。人間向け表示は必要時のみ |
| coverage-analysis | `reviews/<scope>/coverage.md` | coverage・gap・閉鎖性・必要runtime evidence |
| adversarial-review | `reviews/<scope>/adversarial-review.md` | 独立指摘。単発は対話回答、継続時のみ保存 |
| e2e-test-inspection | `automation/<scope>/e2e-inspection.md` | 実装可否・実効設定、調査のみなら必要時保存 |
| e2e-test-implementation | 対象repoの既存test構成、`automation/<scope>/implementation.md` | 実コードは許可repo。実装記録は必要時、コード複製なし |
| e2e-test-execution | `execution/<scope>/<run>/` | 既存runner/reportersのraw・attempt・cleanup、保護領域優先 |
| e2e-test-result-analysis | `execution/<scope>/<run>/analysis.md` | raw参照と原因分析、raw再書込みなし |
| e2e-test-reporting | `reports/<scope>/<run>/e2e-report.md` | E2E報告、raw・分析の参照 |
| test-target-inspection | `specifications/<scope>/inspection.md` | 現在観測。ARIA snapshotは任意、保存要求時のみ必要な安全先 |
| test-execution | `execution/<scope>/<run>/execution.md` | 実行前YAML・TC結果・cleanup。raw/attemptは必要保護先 |
| testware-implementation | 対象repoの既存構成、`automation/<scope>/testware.md` | 非E2Eコードと実装参照、隔離・publish契約維持 |
| testware-execution | 許可済みrepo外保護領域の `<run>/` | 既存manifest.json・attempt log・raw。必要なrefのみexecutionへ |
| regression-testing | `regression/<scope>/baseline`、`regression/<scope>/<run>/` | baseline・membership・Activity・Run。内部名/拡張子は既存schema・writer優先 |
| exploratory-testing | `exploration/<scope>/<session>/` | Charter・Session・Finding・Observation、既存形式 |
| context-signal-audit | `cross-context/context-signal-batch/<identity>.json` | #40の不変batch、訂正batch。cross-contextを指定artifact rootとする |
| context-rule-synthesis | `cross-context/context-rule-candidate/<identity>.json`、`cross-context/context-synthesis-run/<identity>.json` | #40の候補・run・履歴・条件付き更新 |
| qa-knowledge | `knowledge/<entry-ref>.md` | 現行entry形式、1 entry=1 artifact、意味identityを保持 |
| defect-management | `defects/<scope>/defects.md` | 欠陥候補・外部Issue参照。外部操作は許可時のみ |
| test-reporting | `reports/<scope>/<snapshot>/report.json` | immutable snapshot、既存owner verifierの形式/拡張子を維持。人間向け表示必要時 |
| test-evaluation | `reports/<scope>/evaluation.md` | 活動評価・改善・効果測定。元実績は参照 |
| usability-evaluation | `usability/<scope>/evaluation.md` | 資料評価・根拠・改善案 |
| usability-inspection | `usability/<scope>/<run>/inspection.md` | live観測・測定、保護証跡は指定安全領域 |
| wcag-conformance-evaluation | `usability/<scope>/<evaluation-ref>/`、`state/workflow-state.sqlite3` | Plan・sample・結果・report・EARL。正式stateの既存SQLite契約とreport形式を維持 |

上表の既存機械writer優先の行（feature、selection、regression、exploration、reporting等）は、実装者が当該data-contract・writerの現行ファイル名/拡張子を確認し、既定の具体名を成果物マトリクスとowner契約に記載する。既存writerに固定名がないものは論理名に対応する `.json`（機械正本）、`.md`（人間向け正本）を用いる。形式を二重化せず、既存のwriterやschemaの目的を満たすことを確認する。この確認は利用者への設計質問にしない。

## 実装3 project-contextの責務

`skills/project-context/SKILL.md` の発火条件をQA目的・用語・業務ルール・環境制約・DEC/ASMの整理/更新に限定する。既存Contextを単に読む場合は独立Skillを起動する必要はない。指定されたContext、許可範囲の既存資料から必要な情報だけ取得し、不足がQA判断に影響する場合だけ質問する。Contextを新規に作ることを他Skillの利用前提にしない。

- `project_context.py` の `discover` は指定済み文書・許可候補の解決に限定し、案件選択・案件探索を削る。`prepare_create` の前提から初回配置合意・案件ID必須を外す。`prepare_sections`、`prepare_update`、`prepare_ids`、`project_context_ids.py` の必要な意味管理・採番・履歴を維持する。`placement` / `prepare_placement` は新規通常経路から除き、既存配置・履歴を読む互換経路がある場合だけ維持する。呼出し元がなくなった管理専用分岐は削除する。
- templateのSection番号とDEC/ASM・stable keyを使う既存parseの互換性を維持する。新規文書ではSection 10の案件進行設定を要求しない（02）。Section 14/16は既存ref・設定の読取互換として扱い、標準root解決に不要な設定を新規利用者に記入させない。QAの意味情報を削らない。既存文書から設定や承認履歴を無断削除しない。
- `artifact_graph.py` の `parse_project_context`、`validate_required_context_fields`、`compare_used_context` と各Skillの呼出し元で、Context未作成を一律blockedにする経路を外す。必要なfieldの明示入力で成立させる。利用したfieldのcurrentnessは維持する。
- 独立SkillはQAの意味管理とDEC/ASM更新の責務があるため維持する。配置管理削除後にその責務が他ownerと実際に完全重複していると確認された場合のみ、05の構成評価で統合を判断する。

## 実装4 計画3 Skillの人間向け正本

新規のQA要求・architecture・計画はMarkdownを唯一の保存正本とする設計を採用する。既存JSON packetを新規正本と二重保存しない。現行JSON資産はその形式のまま読取・更新できる。自動変換は行わず、利用者が形式指定した場合は互換経路を用いる。変更によって既存の機械集計・承認・依存の意味を欠落させない。

対象: `skills/test-requirements-analysis/scripts/qa_requirement_runtime.py`、`skills/test-architecture-design/scripts/architecture_runtime.py`、`skills/test-management/scripts/management_runtime.py`、各 `SKILL.md` / `references/data-contract.md` / `references/guidance.md` / `assets/output-template.md`、`qa-workflow/scripts/owner_verifiers.py` の `_stored_owner_artifact`、`_verify_requirements`、`_verify_architecture`、`_verify_management`、報告・計画・方式の既存packet読取側。

具体方式:

1. 各data-contractにあるpacket→Markdown対応表を使い、既存templateの見出しを基本に、必要なフィールドが一対一に読める表へ修正する。メタデータ・単一objectは項目/値表、配列は既存IDを持つ行の表とする。複合objectの列は意味に沿って分割し、配列セルはJSON配列（空配列は `[]`）、深い複合値だけJSON objectセルを許容する。本文・根拠・説明文は可読な文字列とし、改行は `\n`、区切りの `|` は `\|`、バックスラッシュは `\\` にescapeする。nullと空文字を区別する（nullable列の `null`、文字列のliteral `null` は引用文字列）。型・必須列・既存enumはdata-contractに明記する。必要な未確定値を欠落させず、未確定の状態を現行enumで表す。行順に意味がある配列は順序を保持する。
2. Markdown parserは各ownerの既存runtimeに入口を追加する。明示的な見出し・列・ID・値型を検査し、既存packetと等価なobjectへ変換する。曖昧な列・重複ID・未知の必須値・不正escapeは該当箇所を返す。既存の `validate` / `impact` / `completion_check` / `build_snapshot` には変換したobjectを渡す。新しい汎用文書schema、LLMによるJSON復元、外部依存を前提としない。実際に共通となる小さな表の読取処理のみ必要時再利用し、単体配布で失敗しないことを検証する。
3. QA要求の `purpose`（対象/対象外を分離）、`sources`（hash/acquisition/未取得理由）、`requirements`、`open_items`、`approval`、`downstream`、`history` の全項目を対応付ける。architectureの `requirement_coverage`、`assignments`（level/type/measurement/automation/selection_basis/approval_id/依存/下流ref等）、`sources`、`constraints`、`open_items`、`change_impacts`、`history` を保持する。計画の `planned_sources`、`planned_populations`、`readbacks`（actual/zero_check含む）、`plan_items`、`criteria`、`project_risks`、`corrective_actions`、`differences`、`approval`、`history`、`monitoring` を保持する。テンプレートにない列を補い、同じ情報の重複記述を正本扱いしない。
4. 原文Markdownの保存byte SHA-256と、変換した意味objectのfingerprintを区別する。実際の保存照合はMarkdown bytes、既存の意味fingerprintは正規化objectで求める。revisionは既存ownerの論理版・保存先revisionの意味を維持し、承認の対象となる内容が変わらない見た目の変更で不要な承認失効を起こさない。正式承認済みの過去revisionを必要時に再取得できるよう保持する。既存architecture `content_fingerprint` は自己fieldを除く既存算法で算出する。導出されるcurrentness・集計値は原則保存正本の二重入力にせず、正式報告snapshotに必要な値は既存の再計算・照合契約を維持する。
5. owner verifierは原文保存内容・実ref・revisionを読み、対応形式を判別する。Markdownを変換してvalidate/impact/completionへ渡すが、JSONへ変換したbyte hashを原文readbackとして使わない。旧JSON verifierは従来のcanonical JSON hashを維持する。schema判別に失敗したら勝手に別形式として採用しない。必要な64 KiB例外は実際の契約経路に限定し、他の入力制限を全体緩和しない。
6. 同一論理内容の旧JSON・新Markdownをfixtureとして比較し、要求・割当・母集団・集計・承認・影響結果が等価であることを確認する。利用者がMarkdown表を直接編集した場合に必要な意味変更のみ再判断し、生成領域の改変を見逃さない。編集後の承認・保存は02に従う。既存JSONからMarkdownへの移行作業は別途合意する。

## 実装5 人間編集・履歴・保護・互換性

- 通常のMarkdownは直接編集可能とし、必要な差分確認・根拠・承認済み意味の保全だけを要求する。UI packageは `skills/ui-target-analysis/scripts/human_editing.py` と `skills/spec-analysis/scripts/ui_target_package.py` の編集提出・生成領域・ID・writer・履歴を維持する。通常Markdownにこの専用writerを要求しない。
- 継続文書は安定ファイル名。Q/DEC/ASM/ITEM/COND/Entityの安定ID・retire・履歴は各owner。正式報告・依存再現・実行のRun/Attempt/snapshotを保持する。全更新の連番ファイル複製は不要。必要な旧フォームの復元は02。
- `test-target-inspection`、`usability-inspection`、`test-execution`、`e2e-test-execution`、`testware-execution`、`agent-answer-form`、#40の保護契約を共通運用文書と各ownerへ同期する。成果物・未回収回答・再開draft・raw・一時物を区別する。秘密実値を通常成果物へ保存しない。rawを安全な許可先に保全できない場合は安全な要約と未保存/取得不能を報告する。保存要求がある証跡は保存不能を正式完了にしない。任意snapshotは未保存だけで完了を妨げない。cleanupは許可された今回の一時物だけを対象とし、履歴・継続資料を削除しない。
- 既存配置をdirect ref/許可rootで読取・更新できるようにする（OPS-17）。標準化を理由に既存資産を移動・改名・再保存しない。別rootの同名refを分離する。実際に移行が必要な場合だけ、対象・旧新ref・履歴・依存・互換読取・条件付き切替・rollbackを別途合意する。無断移行やrollbackはしない。

## 検証・完了条件

- `test_project_context_owner.py`、`test_project_context_ids.py`、`test_pr24_artifact_store.py`、`test_pr24_git_artifact_store.py`、`test_ui_human_editing.py`、`test_feature_registry.py`、`test_test_item_condition_analysis.py`、`test_context_artifact_store.py`、`test_context_runtime_transport.py` と計画3 Skillの `test_f_verifier_requirements.py`、`test_f_verifier_architecture.py`、`test_f_verifier_management.py`、`test_cross_owner_results_to_reporting.py` を変更箇所に応じて個別実行する。05の全suiteも実行する。
- AT-01/02/03/09/12〜14/16/19/20/21/24/25: 新規・既存・指定あり/なし、別Agent、同一refの再利用、異なるscope・root、権限不足、重複、symlink、旧JSON、Markdown人間編集、変更前後の承認、機密raw、部分保存、必要な旧revisionを確認する。
- 39 Skillの標準配置・形式・粒度・保存不要条件が現行成果物マトリクスと各ownerで一致し、特定ハーネス/案件初期化/Provider選択なしで利用可能。既存資産を失わず、計画3 Skillの新旧形式で意味・母集団・検証結果が同等。必要な機密保護と旧形式互換を維持した場合に完了。
