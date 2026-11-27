# 成果物・コンテキスト・保存先の改修

## 目的・対象

OPS-09・12〜14・16・17・18。指定がない通常のQA依頼でも、人間が利用しやすい成果物を一貫した場所に保存し、既存資産を変更せず再利用する。全39 Skillを対象とし、共通成果物マトリクスと各ownerの契約を改修する。保存・承認の実処理は02、currentnessは03、実行証跡の操作条件は04で扱う。

## 現状・既存契約

- `skills/project-context/SKILL.md`、`scripts/project_context.py`（同Skill配下）の `discover`、`prepare_create`、`prepare_sections`、`prepare_update`、`prepare_ids`、`placement`、`prepare_placement`、`persist_prepared` は案件発見・初回配置合意・owner・保存能力を含む。
- `skills/qa-workflow/assets/project-context-template.md` Section 10/14/16、`scripts/artifact_graph.py` の `parse_project_context`、`validate_required_context_fields`、`compare_used_context`、`workflow_state_root_from_project_context` 等は既存入力・状態解決に利用される。
- 計画3 Skillの正本はcanonical JSON、Markdownは描画物。各 `references/data-contract.md` のpacket項目とMarkdown表の対応、各 `assets/output-template.md`、owner runtime、`qa-workflow/scripts/owner_verifiers.py` に依存がある。
- UI target packageの固定構造・single writer、Knowledgeのentry-ref、#40の3 kindと履歴、runtime-v2のMachine Entity、runnerのraw形式は個別の機械契約を持つ。

#40の指定root・3 kindの固定相対配置、不変batchと履歴は実装済み。通常保存と条件付き更新の実測は[#40検証記録](../implementation/pr40/verification.md)のext4・9pの範囲に限る。新規の標準配置は既存資産の移行や再実装を前提としない。

## 実装1 保存先・指定の解決

全Skillの保存先解決を次の順に統一する。必要な成果物の有無を先に判断し、単発の相談・読取・レビュー・調査に保存先確認を要求しない。再利用価値のある知識は許可済み保存先が既知の場合に限り自律的に蓄積し、任意蓄積のために通常回答を止めない。明示非保存を尊重する。

1. 現在の依頼で利用者が指定した保存先・形式・命名・履歴・運用ルールを適用する。既存資産の変更を伴う場合は勝手に上書き・移行しない。
2. 明示された成果物ref、許可された作業範囲にある既存の有効な規則・正本を適用する。既存ファイルを更新する場合は元の場所・IDを維持する。既存ルールとの矛盾があれば必要な論点だけ確認する。
3. 指定がなく新規作成する場合、現在のAgentが書込みを許可された作業ディレクトリの `qa/` を既定の成果物rootとする。既にQA専用rootが指定・認識されている場合はその直下を利用し、`qa/qa/` を作らない。対象repoの読取許可だけを保存許可にしない。外部情報源repoを成果物rootとして推測しない。sandbox等から許可範囲が判断できなければ、必要な保存先・許可のみ質問する。
4. 必要時の質問は「保存先・形式・運用ルールに指定はありますか。なければ標準で進めます」を基本とする。既知の指定・既存規則は再質問しない。専用Provider、CAS、revisionの方式選択を利用者に求めない。指定が必須の意味・安全条件と両立しない場合は具体的な制約と可能な方法を説明する。
5. refは指定root内の実在する正本または許可direct refへ解決する。symlink、path traversal、別root同名、読取不能、列挙不全、重複を区別し、曖昧な正本への新規作成・更新だけ停止する。通常保存のための専用ハーネス・案件登録・root登録CLI・新しい全成果物indexは作らない。

既定の形式は人間向け文書は通常Markdown、機械処理用データはJSON。実行raw・HTMLなど必要な専用形式は維持し、同じ意味のMarkdownとJSONを二重保存しない。既定の相対配置は以下。利用者指定・既存配置が優先する。機械形式を独自形式へ変える指定は、必要な検証と相互利用が維持できる場合に適用する。

## 実装2 39 Skillの標準配置・保存粒度

`<root>` は前節の成果物root。既存正本の探索を先に行い、同じowner・論理対象・用途の有効な正本が一つならpathや形式を変更しない。新規の `<scope>` は単一機能なら既存FEAT ID、単一の別対象なら担当ownerの安定対象ID、複数対象なら既存の安定scope ref、案件横断なら common を用いる。複数対象で既存refがなければ対象の安定ref集合を重複除去・辞書順にしてscopeを構成する。IDを新規発行する必要がない単発対象では対象の正式名と情報源refを用いる。source revision、時刻、作業Agent名は継続成果物のidentityに含めない。

IDが安全な単一path要素ならそのまま使う。そうでないrefや対象名を使う場合は、UTF-8の正規化NFC文字列に対するSHA-256の全64桁を使用する（複数要素は既存canonical JSONの配列としてhash）。名称変更時は既存正本を先に見つけてrefを維持する。Windows予約名・大小文字衝突・禁止文字・root逸脱がある場合も同じdigest方式を使い、実在する別identityに衝突したら上書きせず確認する。ファイル名を採番の根拠にしない。

継続する同じ対象の仕様・設計は同一正本へ更新する。並立する計画は計画の既存ID、なければ明示された対象release/build・期間・環境の組を上記digestで区別し `planning/<scope>/<plan-key>/` 配下に置く。QA要求・方式が同じ計画固有の対象を持つ場合は同じ計画ディレクトリへ保存し、複数計画で共用する有効な要求・方式は既存refで参照する。一つの継続計画の改版は同じpath。実行・観測・報告は既存run/attempt/snapshot/evaluation/session identityで分離する。既存の別scope・別案件と同じIDが衝突する場合は有効な既存案件root・対象refで区別する。大文字小文字やUnicodeの表記差を同一正本と推測せず、正本の実際のpathと論理identityを確認する。別writerの新規作成は出力先を分離し、同一正本の作成担当を決める。例: FEAT-001の設計は design/FEAT-001/test-cases.md、別環境のrunは実行ownerが発行した別runのディレクトリ、既存の tests/design/foo.md が同じ正本ならその場所のまま。新規中央台帳・命名サービスは不要。

表のファイル名を新規成果物の既定値とする。既存writerがファイル名・内部構造を固定しているものは、表のディレクトリをwriterへ渡し、その固定名・拡張子・公開単位を変更しない。`<run>`、`<attempt>`、`<snapshot>`、`<entry-ref>`、`<workflow-ref>` は担当ownerの既存識別子を用いる。正式な正本が存在する場合はこの表より既存refを優先する。

<!-- dprint-ignore -->
| Skill | 新規の既定相対path | 正本・保存粒度/例外 |
| --- | --- | --- |
| qa-workflow | 必要時 `state/<workflow-ref>/`、`reports/<scope>/workflow.md` | 復元不能な要求・未解決・再開・baseline参照のみMarkdownまたはJSON。SQLite不要 |
| project-context | `context/PROJECT_CONTEXT.md` | QA目的・用語・DEC/ASM・環境等の共通文書。既存正本優先、必須の初期化なし |
| feature-analysis | `features/feature-registry.json` | 現行snapshotのschema・source inventory・ID・履歴。既存writer固定名があれば維持 |
| spec-analysis | `specifications/<scope>/specification.md` | Authority・US/UC/Behavior/AC/UNKNOWN、Machine Entity。UI package利用時はその専用構造、別正本を作らない |
| ui-target-analysis | `specifications/<scope>/ui-target/` | ui-target-v1内部構造、既存single writer・履歴 |
| question-analysis | `questions/<scope>/questions.md` | Q ID、根拠、元質問・回答履歴、状態・再開先。同一論点を重複発行しない |
| agent-answer-form | `questions/<scope>/forms/<既存form IDまたは論点集合ID>/` | `questions.json`・`answer-form.html`、必要な旧定義/HTML・回答。単発フォームは指定先/許可作業dir |
| test-requirements-analysis | `planning/<scope>/requirements.md`（計画固有は `planning/<scope>/<plan-key>/requirements.md`） | 人間向けMarkdown、機械処理用JSON。06に従い一方を正本とする |
| test-architecture-design | `planning/<scope>/architecture.md`（計画固有は `planning/<scope>/<plan-key>/architecture.md`） | 同じ形式選択。割当・制約・根拠・承認 |
| test-management | `planning/<scope>/<plan-key>/plan.md`（単一継続計画は `planning/<scope>/plan.md`） | 同じ形式選択。計画・予定母集団・基準、必要snapshotは既存形式 |
| test-analysis | `analysis/<scope>/risk-analysis.md` | Risk・重点・技法候補、Machine Entity |
| test-item-analysis | `analysis/<scope>/test-items.json` | test-item-candidates-v1、ID・親子・履歴 |
| test-condition-analysis | `analysis/<scope>/condition-candidates.json` | test-condition-candidates-v1、共有条件はcommonに一度だけ保存 |
| test-requirement-design | `design/<scope>/requirements.md` | TR・Machine Entity・runtime契約 |
| test-condition-design | `design/<scope>/conditions.md` | TCN/CI・Disposition・runtime契約 |
| test-case-design | `design/<scope>/test-cases.md` | TC・データ・期待結果・runtime契約 |
| e2e-test-selection | `automation/<scope>/selection.json` | 選定理由・安定ID・必要な過去版。全snapshot内包は見直し、旧形式読取を維持 |
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
| context-rule-synthesis | `cross-context/context-rule-candidate/<identity>.json`、`cross-context/context-synthesis-run/<identity>.json` | #40の候補・run・根拠・必要な履歴。通常JSON更新 |
| qa-knowledge | `knowledge/<entry-ref>.md` | 現行entry形式、1 entry=1 artifact、意味identityを保持 |
| defect-management | `defects/<scope>/defects.md` | 欠陥候補・外部Issue参照。外部操作は許可時のみ |
| test-reporting | `reports/<scope>/<snapshot>/report.json` | immutable snapshot、既存owner verifierの形式/拡張子を維持。人間向け表示必要時 |
| test-evaluation | `reports/<scope>/evaluation.md` | 活動評価・改善・効果測定。元実績は参照 |
| usability-evaluation | `usability/<scope>/evaluation.md` | 資料評価・根拠・改善案 |
| usability-inspection | `usability/<scope>/<run>/inspection.md` | live観測・測定、保護証跡は指定安全領域 |
| wcag-conformance-evaluation | `usability/<scope>/<evaluation-ref>/` | Plan・sample・結果・正式closureのJSONと報告Markdown、必要時EARL。04の専用検証を維持しSQLite依存を解消 |

feature-registry.json、selection.json、report.json は固定名のない新規保存の既定名。regressionのbaseline・membership・Activity・RunとexplorationのCharter・Session・Finding・Observationは既存schemaとowner単位を保ち、既存writerの固定名がない場合はそれぞれ baseline.json、membership.json、activity.json、run.json、charter.md、session.json、finding.json、observation.json（複数の独立identityは既存IDごとのファイル）とする。既存writerによる一括更新が必要な構造は分割しない。UI package、testware実行manifest/raw、#40の3 kindは専用writerの実契約が正本であり改名しない。現行固定名を照合し成果物マトリクスへ記載する。形式を二重化せず、既存のwriterやschemaの目的を満たすことを確認する。この確認は利用者への設計質問にしない。

## 実装3 project-contextの責務

`skills/project-context/SKILL.md` の発火条件をQA目的・用語・業務ルール・環境制約・DEC/ASMの整理/更新に限定する。既存Contextを単に読む場合は独立Skillを起動する必要はない。指定されたContext、許可範囲の既存資料から必要な情報だけ取得し、不足がQA判断に影響する場合だけ質問する。Contextを新規に作ることを他Skillの利用前提にしない。

- `project_context.py` の `discover` は指定済み文書・許可候補の解決に限定し、案件選択・案件探索を削る。`prepare_create` の前提から初回配置合意・案件ID必須を外す。`prepare_sections`、`prepare_update`、`prepare_ids`、`project_context_ids.py` の必要な意味管理・採番・履歴を維持する。`placement` / `prepare_placement` は新規通常経路から除き、既存配置・履歴を読む互換経路がある場合だけ維持する。呼出し元がなくなった管理専用分岐は削除する。
- templateのSection番号とDEC/ASM・stable keyを使う既存parseの互換性を維持する。新規文書ではSection 10の案件進行設定を要求しない（02）。Section 14/16は既存ref・設定の読取互換として扱い、標準root解決に不要な設定を新規利用者に記入させない。QAの意味情報を削らない。既存文書から設定や承認履歴を無断削除しない。
- `artifact_graph.py` の `parse_project_context`、`validate_required_context_fields`、`compare_used_context` と各Skillの呼出し元で、Context未作成を一律blockedにする経路を外す。必要なfieldの明示入力で成立させる。利用したfieldのcurrentnessは維持する。
- 独立SkillはQAの意味管理とDEC/ASM更新の責務があるため維持する。配置管理削除後にその責務が他ownerと実際に完全重複していると確認された場合のみ、05の構成評価で統合を判断する。

### Contextなしで利用する入力

明示入力、有効な既存正本、許可済み環境、以下の既定の順で必要fieldだけ解決する。parse_project_context と validate_required_context_fields はContextが入力された場合に内容を検証する。既存stable keyは入力の意味名として維持し、Context文書作成を要求しない。利用した値と根拠だけをcompare_used_contextへ渡す。

<!-- dprint-ignore -->
| 既存field/意味 | 未指定時の取得・扱い |
| --- | --- |
| QA目的・対象・優先順位・DEC/ASM・用語 | 現依頼、既存仕様/決定、担当SkillのAuthority解決。正式な決定不足のみ質問 |
| 環境・認証・データ・非機能制約 | 許可済み実行環境と指定資料。実行不能なら実行のみ停止 |
| qa.regression_scope / qa.regression_policy | 依頼scope、既存baseline/方針、担当Skillのリスク判断。必要範囲不明なら質問 |
| qa.knowledge_root | 既存配置、なければ <root>/knowledge |
| qa.workflow_state_root | 既存設定を優先。成果物から復元できない継続情報が必要な場合だけ <root>/state。正式WCAGの評価成果物は評価ディレクトリを利用 |
| qa.reservation_root | 旧設定の読取互換。実際に必要な既存環境の制御がある場合のみ利用し、新規の汎用予約rootを要求しない |
| qa.auxiliary_testware_refs / qa.feature_source_refs | 直接refと許可範囲で発見した実資料、未取得は明示 |
| qa.feature_artifact_root | 既存配置、なければ <root>/features |
| qa.feature_base_ref | 実Git差分・保存済みsource revision。なければ初回として扱い差分取得済みとしない |
| qa.feature_approval_policy_ref | 指定された正式再分類・組織決裁にのみ適用。通常保存では不要 |
| qa.defect_issue_tracker_ref | 指定・既存の有効な外部連携先。なければローカル候補まで |

Contextからrootを取得する既存呼出し（workflow_state_root_from_project_context、workflow_state_context_from_project_context、Knowledge/feature/defect/Regressionの入力）では、同じ意味の明示値を優先して受け、未設定時は上表を使う。架空のContext本文や設定値を生成して必須チェックを通さない。旧Contextはそのまま読める。

## 実装4 計画3 Skillの正本形式

QA要求・architecture・計画は人間向けなら通常Markdown、機械集計が主用途ならJSON。指定・既存形式を優先し同一内容を二重正本化しない。専用JSON block・固定escape・厳密Markdown文法を強制しない。既存v1 JSONを読み取り、必要な機械処理は実際に使う入力を既存validatorへ渡す。

[06 計画成果物の形式・承認](2026-11-27_111830_qa-operating-improvements_06_planning-artifact-contract.md)に従いvalidate/impact/completion_check/build_snapshotの意味・集計・承認を維持する。v2形式・共通parserの新設は既定としない。

## 実装5 人間編集・履歴・保護・互換性

- 通常のMarkdownは直接編集可能とし、必要な差分確認・根拠・承認済み意味の保全だけを要求する。計画3 Skillの承認時点の内容保全と未承認変更の扱いは06に従う。UI packageは `skills/ui-target-analysis/scripts/human_editing.py` と `skills/spec-analysis/scripts/ui_target_package.py` の編集提出・生成領域・ID・writer・履歴を維持する。通常Markdownにこの専用writerを要求しない。
- 継続文書は安定ファイル名。Q/DEC/ASM/ITEM/COND/Entityの安定ID・retire・履歴は各owner。正式報告・依存再現・実行のRun/Attempt/snapshotを保持する。全更新の連番ファイル複製は不要。必要な旧フォームの復元は02。
- `test-target-inspection`、`usability-inspection`、`test-execution`、`e2e-test-execution`、`testware-execution`、`agent-answer-form`、#40の保護契約を共通運用文書と各ownerへ同期する。成果物・未回収回答・再開draft・raw・一時物を区別する。秘密実値を通常成果物へ保存しない。rawを安全な許可先に保全できない場合は安全な要約と未保存/取得不能を報告する。保存要求がある証跡は保存不能を正式完了にしない。任意snapshotは未保存だけで完了を妨げない。cleanupは許可された今回の一時物だけを対象とし、履歴・継続資料を削除しない。
- 既存配置をdirect ref/許可rootで読取・更新できるようにする（OPS-17）。標準化を理由に既存資産を移動・改名・再保存しない。別rootの同名refを分離する。実際に移行が必要な場合だけ、対象・旧新ref・履歴・依存・互換読取・条件付き切替・rollbackを別途合意する。無断移行やrollbackはしない。

既存DB候補は `.qa-context-feature/artifacts.sqlite3` と `workflow-state.sqlite3`。許可済み利用先の存在を確認し、必要な場合だけ旧DBの読取・export、内容・ID・参照・必要な過去版の照合を用意する。実資産未確認を移行完了とせずDBを削除しない。既存Git専用branchの正本やviewは明示された運用として扱い、無断で移さない。

## 検証・完了条件

- `test_project_context_owner.py`、`test_project_context_ids.py`、`test_pr24_artifact_store.py`、`test_pr24_git_artifact_store.py`、`test_ui_human_editing.py`、`test_feature_registry.py`、`test_test_item_condition_analysis.py`、`test_context_artifact_store.py`、`test_context_runtime_transport.py` と計画3 Skillの `test_f_verifier_requirements.py`、`test_f_verifier_architecture.py`、`test_f_verifier_management.py`、`test_cross_owner_results_to_reporting.py` を変更箇所に応じて個別実行する。05の全suiteも実行する。
- AT-01/02/03/09/12〜14/16/19/20/21/24/25: 新規・既存・指定あり/なし、別Agent、同一refの再利用、異なるscope・root、権限不足、重複、symlink、旧JSON、Markdown人間編集、変更前後の承認、機密raw、部分保存、必要な旧revisionを確認する。
- 39 Skillの標準配置・形式・粒度・保存不要条件が現行成果物マトリクスと各ownerで一致し、特定ハーネス/案件初期化/Provider選択なしで利用可能。既存資産を失わず、計画3 Skillの新旧形式で意味・母集団・検証結果が同等。必要な機密保護と旧形式互換を維持した場合に完了。
