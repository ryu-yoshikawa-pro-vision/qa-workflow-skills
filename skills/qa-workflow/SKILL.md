---
name: qa-workflow
description: 新規・変更機能のQA設計と要求されたE2E工程に加え、Regression / Exploration / QA Knowledgeを含む複合QA workflowの開始点、既存成果物の再利用、routing、停止・再開、修正確認を成果物ベースで判断する。workflowを複数Skillへ接続するときに使用する。
---

# QAワークフロー

## 実行契約

1. 本Skillはオーケストレーションだけを担当し、工程固有ロジックを再定義しません。
2. ユーザー要求、要求成果物、対象範囲から最も早い開始Skillを判断します。作業の最初に既存のworkflow stateと成果物を読み、記録された入力revision（製品commit・仕様書の版など）が現在と同一なら保存済み成果物を再利用して再生成しません。入力が変わった範囲だけを再実行し、再利用・再実行の別と、中断・再開の事実をworkflow stateへ記録します。
3. 必要Skillが利用できない、または担当Skillの必須入力が不足する場合は、そのSkillが必要な範囲だけをブロック中として扱います。
4. 上流成果物の意味が変わった場合は、影響する下流だけを`要再検証`へ戻します。
5. Skillを参照するときは正規Skill名を使い、番号だけの参照は使用しません。
6. 開始点、再利用、ブロック中 / 再開、変更伝播、修正ルーティング、ワークフロー完了判定の詳細が必要な場合は`references/guidance.md`を読みます。
7. 案件固有情報を新規整理する場合は必要に応じて`assets/project-context-template.md`を利用できます。
8. ワークフロー状態を明示する必要がある場合だけ`assets/workflow-state-template.md`を使用します。
9. 同一Skillを複数用途で使う場合は、状態を`Skill + 対象 / 実行範囲`で識別し、開始・最終・再開の対象も正規値で保持します。
10. 案件配置・機能ID・QA要求・方式・計画・欠陥・統合報告・活動評価は各担当Skillへroutingし、本Skillで判断しません。`workflow_runtime.py`にowner verifierが登録されていないSkillのscopeは`unverified_scopes`として残し、Skill名がroutingに載っていることや担当Skillの自己申告だけで完了扱いしません。
11. E2E固有のlocator、Playwrightコード、実行command、原因分析、報告再解釈は担当E2E Skillへ委譲します。本SkillはE2Eを要求しない既存経路も維持します。
12. ワークフロー完了と全E2EテストPASSを同一視しません。必要な実行・分析・報告・cleanup確認・再検証が完了しているかで判定します。
13. 最終出力前に、実際に利用した入力が本Skillの入力契約を満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成したオーケストレーション成果物へ本Skill自身の出力契約・品質ゲートを適用して自己検証します。明白かつ局所的で新しい工程固有の判断を必要としないオーケストレーション契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。仕様根拠不足、上流判断不足、他Skillの工程固有ロジックが必要な問題は推測補完せず既存の停止条件・ブロック中・ルーティングに従います。最終確認後も本Skill自身のオーケストレーション契約違反が残り、既存の停止条件・ブロック中・ルーティングに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。自己検証でも他Skillの工程固有ロジックを再判定・再設計せず、自己検証の経緯や修正回数は出力しません。

## 横断コンテキスト分析

- 単一の仕様・決定・承認済みASM・実装確認・探索成果物から、中立な観察signalの抽出、範囲の訂正、batch再利用を求められた場合は`context-signal-audit`へroutingします。
- 別workflowのsignal・候補・Authority・回答・Knowledgeを横断する法則性分析、新機能QA開始時の再利用、重大反例や下流設計前の再評価は`context-rule-synthesis`へroutingします。A実行のたびにBを自動起動しません。
- 両Skillの候補は仮説であり、期待仕様・正式Product Risk・テスト期待結果へ昇格させません。Authorityは`spec-analysis`、未知事項は`question-analysis`、調査は対応する既存調査ownerへ渡します。
- モードが無効 / 未指定なら起動しません。補助モードの未設定・失敗は既存workflow完了を破壊せず、必須モードの未設定・不完全・認可不足はrequested scopeに残して該当範囲をblockedにします。単体実行も既存owner verifierと保存・認可条件を満たした範囲だけ正式完了とします。
- A試行とB run refは既存workflow stateへ記録します。指定されたrootにOS権限でアクセスできる場合、通常保存は既存ファイル操作で行い、専用認証hostや保存ごとの承認を要求しません。root不明・書込権限不足・必要な共有/外部owner認可の不足は該当scopeだけを未完了にし、独立した調査を続けます。

## 決定論的runtime統合

本Skillは工程固有generatorを再実装せず、対象scopeが1件以上ある場合だけ担当Skillのruntime dispatch結果を統合します。scope 0ではruntimeをdispatchせず、既存のworkflow契約を維持します。統合するMachine Runtime Input / ResultとMachine Entityは、Skill名・runtime unit・Model Key・stable ID・fingerprint・freshnessを持つ機械証拠です。

`workflow_runtime.py`へのnormalized inputは、既存workflow stateと同じcanonical UUIDの`workflow_ref`を必須で渡します。Result payloadも同じ値を返し、別workflowのevidence混在を許しません。
`workflow_runtime.py`へ渡す`requested_scopes`（各要素は`skill / target / execution_range / requirement`）は、今回の最終判定で必要なscope集合です。未宣言・空は完了不可（`required_scopes_undeclared`）です。Context A/Bを含む場合、開始時に受け付けた元要求は既存workflow stateに固定して保存します。仮targetから実artifact refへ具体化した後は、そのstate対応とowner検証から導ける実scope集合を最終runtime入力へ渡します。元要求はstateから削除せず、対応がない要求を最終集合から黙って落としません。要求集合に含まれる`required` scopeの欠落は`required_scope_missing`、`excluded_by_approval`は、承認の照合手段（承認provider）が定義されるまで対象外として確定しません。該当scopeは必須のまま残り、placeholderや欠落は`approval_ref_missing`、具体的な参照は`approval_unverifiable`として`unverified_exclusions`に出ます（完了不可）。`approval_ref`の形式があっても承認済みとして扱わず、真正性・対象scope・revision・承認状態は`workflow_runtime.py`が確認しません。再開条件と検証の範囲は`references/guidance.md`の「要求集合と「省略」」を参照します。要求外のSkillを推論で追加せず、状態値「省略」の定義は`references/guidance.md`の「要求集合と「省略」」に従います。

context A/Bが必須scopeに含まれるworkflowでは、最初のcontext処理前に同じ`workflow_ref`・指定artifact rootで`context_workflow_state.py register-requested-scopes`を呼び、開始時の全要求集合とA/Bの要求契約を既存stateへ保存します。既に初期stateへ保存済みなら同一内容の登録を再利用します。A契約には元source ref/hash、要求範囲、観測条件を、B契約には開始時の全operation input、分析scope、target batch refsを固定します。後続attempt/runはその契約内で実行し、要求範囲・source・条件を縮小または置換しません。A attemptの`request_scope`、B run groupの`request_scopes`には開始時の元scope identityを残し、仮targetを実refへ具体化した後は、stateの要求mappingと実readbackに対応するartifact scopeを最終`requested_scopes`と`workflow_scopes`へ渡します。

同じ必須context workflowの最終runtime inputには、`context_workflow_state_root`を`requested_scopes`と`workflow_scopes`とは独立して渡します。runtimeはこのrootから開始時の要求を再読込し、最終入力からA/Bの要求・scope・state参照がすべて落ちていても未完了にします。共通workflow runtimeでこのfieldは任意なので、Context A/Bを使わない単体・補助実行には追加しません。最終gateは開始要求、永続attempt/run group、最終scope集合を一体で照合します。補助実行と過去履歴は必須要求の充足に数えません。

runtimeの`can_complete`はオーケストレーションの要約であり、下流のsemantic coverage、実行結果、報告、cleanup確認を置き換えません。`current`でない上流Entityやruntime結果は再利用せず、変更があれば依存fingerprintから影響対象だけを`要再検証`へ伝播します。

### UIテスト対象分析とscope readiness

UI構造・画面・操作・状態・遷移を分析し、継続利用する`ui-target-v1` packageを作成・更新する要求は`ui-target-analysis`へroutingします。既存writer、validator、runtime、共通helperを再利用し、single writer、履歴、migration、`ui-target-v1`互換性を維持します。期待仕様、Authority、US / UC / Behavior / AC、UNKNOWNは`spec-analysis`が所有します。repository factや実装状態から期待仕様を推定しません。

package作成・更新後は必ず`ui_target_package.py inspect`を実行し、`current_scope_ids[] / ready_scope_ids[] / blocked_scope_ids[]`をそのまま使います。current UNKNOWN全件や手作業で選んだscope集合からready状態を推定しません。

- migrationが必要なartifactでは`migration_preflight.py`の`migration_status / cutover_next_action`に従い、runtime-v2 cutoverを固定Skill順で先に完了します。TCDの内部phaseは同Skillの`runtime_v1_cutover.py phase=resume`へ委譲します。
- 既存downstreamにscope ownershipがなく、migration preflightが`scope_ownership_baseline_required`を返した場合は、全current scopeがreadyの時だけ全scopeを含む初回TRD→TCD→TC normalizationを実施します。blocked scopeへownershipを推測配分しません。
- `ready_scope_ids[]`が1件以上なら、ready scope全件を一括handoffし、test-analysis→TRD→TCD→TC→coverage-analysisを1回ずつ進めます。blocked scopeをhandoffへ含めず、同一Skillをscopeごとに重複dispatchしません。
- `current_scope_ids[]`がnon-emptyで`ready_scope_ids[]`が空なら全scope blockedです。empty batchやdownstream runtimeを起動せず、最後に完了したbaselineを保持し、question-analysis等の必要な回答先とresume先だけをworkflow stateへ残します。
- `current_scope_ids[]`が空なら全scope retireです。全blocked経路へ戻しません。既存baselineがあれば`downstream_state.py`でterminal deletionを導出し、owner generatorのdeletion-only path、coverage-analysis、通常のqa-workflow final gateを通します。bindingがない初回workflowは削除runtimeなしでpackageをcompleteにできます。

previous downstream stateはcurrent workflow stateの`last_completed_qa_workflow_artifact` bindingからだけ復元します。local filesystemでは`artifact_graph.py`のexact historical revision readbackを行い、Markdown SHAとworkflow_refを検査してから`downstream_state.py`へ渡します。能力フラグやraw artifactの最新値だけでprevious baselineを選びません。

通常のblocked scopeは`scope_refs[]`に交差するEntityだけをinactiveへ移し、last-active snapshotをhelper出力どおり各generatorへ渡します。inactive自身はcurrent Entity / runtimeへ含めず、それだけでready scopeを停止させません。retired scopeはsemantic ownerのreuse / deletion判断とgenerator適用stateをhelperで照合するまで解決済みにしません。再ready時はEntity history / materialize historyをsemantic identityの比較とstable ID復元に使います。

candidate qa-workflow artifactの`verify_runtime_evidence.valid=true`とruntime payloadの`can_complete=true`を確認した後にだけbaselineを保存します。local単一hostではimmutable snapshotの保存・exact refetch・workflow-ref lock内state revision比較・atomic state updateがすべて成功した場合だけbindingを更新します。失敗・blocked・unresolvedでは直前のbindingを保持します。

### 最終runtime evidence gate

最終成果物の直前にqa-workflow-local `scripts/runtime_contract.py`の`operation=verify_runtime_evidence`へ、実際に使用したcanonical normalized inputとcandidate成果物全文を渡し、`partial_rerun=false`かつ`previous_artifact_markdown=null`に固定します。qa-workflowは自Skill Entityをcarry-forwardしません。`workflow_runtime.py`の前に、runtime-v2 rootを持つscopeの担当Skill verifierを実行し、`valid=true`で返った`current_structure_state`を変更せず`workflow_scopes[]`へ転記します。owner verifier対象のscopeは構造stateを返さず`current_structure_state=null`のため転記せず、`workflow_runtime.py`の`verified_owner_scopes`の判定に委ねます。stateやexpected Entityを組み立てません。最終gateの`valid=false`は既存の最大1回の局所修正・最終確認契約へ統合し、未解決なら完成扱いしません。`verify_runtime_evidence`は`workflow_runtime.py`のworkflow全体検証を置き換えず、両方を実行します。

### 新設Skillのowner verifier

runtime-v2 rootを持たないSkillのscopeは、`scripts/owner_verifiers.py`に登録されたowner validatorが保存済み成果物を検証できた場合だけ、`workflow_runtime.py`が完了対象（`verified_owner_scopes`）にします。登録済みownerは`test-item-analysis`、`test-condition-analysis`（保存本文のhash、owner validator、source currentness）、`e2e-test-selection`（owner validator、保存本文のhash）、`test-reporting`（入力からの再計算との一致、完全性、currentness）です。F 3 Skillの`test-requirements-analysis`・`test-architecture-design`・`test-management`も登録済みで、canonical JSON packetの保存本文を`validate`・`validate_readback`・`impact`・`completion_check`で検証します。`context-signal-audit`はcanonical batch、current source、要求範囲に対するreadback batchの和集合を検証し、`context-rule-synthesis`はrun identity、planned candidate、直接根拠、handoffと保存readback一式を検証します。新規2 ownerのverifierは渡されたreadbackの整合性を検証し、独立してproviderへ接続する機能は持ちません。通常の指定root保存はローカル実filesystem上の保存/readbackを含むテストで確認済みですが、運用rootは未指定で、共有writerと外部owner認可は未検証です。未検証・stale・未完了は完了扱いしません。

証拠は`normalized_input.owner_verification`に、保存境界がhashした**保存本文そのもの（JSON文字列）**で渡します。runtimeは構造化入力を並べ替えるため、構造化データではhashの元のbytesを保てません。本文のhash、ownerのvalidator、source currentnessのどれかが確認できない、ownerのscriptが無い・失敗する、scopeのtargetと成果物のrefが違う場合は未検証のままで、自己申告の`verified`や`can_complete`は証拠になりません。登録されていないSkill（`defect-management`、`test-evaluation`、`feature-analysis`、`project-context`、`ui-target-analysis`など）はowner入口が無いため、`unverified_scopes`として完了不可のままです。fixtureだけでは運用rootの権限や外部owner認可を証明しません。
保存済みv2 workflowを再開するときは、runtime-v2 rootのscopeの`current_structure_state`を従来どおり検証します。owner完了scopeは`current_structure_state=null`で、保存済みresultの`verified_owner_scopes`の記録と1対1に対応し、登録Skill、記録の`verified_artifact`（artifact_ref・artifact_revision・content_hash）、保存済み証拠の本文のsha256、targetが一致する場合だけ受理します。root以外のscopeに非nullの構造stateがある場合、rootのscopeにnullがある場合は拒否します。v1は従来の検査のままで（owner scopeのnullは従来どおり拒否）、新しい完了baselineにしません。この照合は保存された記録を信頼する境界の内側の整合性確認で、保存本文・記録・証拠を一式で偽造された場合は検出できません（残る制約）。

## 継続管理workflowの決定論的処理

persisted workflowのProject Context stable key parse / 必須key検証 / used-field currentness、workflow stateのcanonical path / 初回create、fixed-root scan、state CAS capability gate、mutable operation pre-start claim、shared resource reservationは、Resourcesに記載した`artifact_graph.py` production helperで実行します。これらの処理結果をAgentの意味判断や手計算で置き換えません。

WCAG formal report provenanceでは、`workflow_runtime.py`の`register-wcag-evaluation-plan` / `read-wcag-evaluation-state` / `finalize-wcag-report`を使います。これは既存`qa.workflow_state_root`配下のPython `sqlite3` providerを使う単一ホストlocal filesystem限定のstate operationです。評価refごとのcurrent revision、WCAG target、scope evidence refs、selected sample / variation / process、source refs、canonical Planとreport状態を保存します。generic JSON state / handoff / reservation providerには拡張せず、network filesystem・複数host・state root未設定・provider failureではblockします。保存済みrecordは承認の代替にならず、既存evaluation ownerの入力・scope根拠を確認して登録します。

`finalize-wcag-report`は呼び出し側の`wcag_runtime_result`や`upstream_runtime_units`を完了証拠として受け取りません。QA workflow ownerがcurrent evaluation stateを正式なQA runtimeで再読込し、同じ保存済みPlan・current results・提示されたWCAG-EM工程入力で公式`wcag_runtime.py close-report`を内部実行します。ownerはそのruntime envelopeと有限なclosure入力を生成した実行ref付きで既存SQLite stateへCAS保存し、独立再読込後に保存されたcurrent runを使ってclosureを再検証します。必須工程・accessible output・結果集合がcompleteの場合だけ、別のnative conditional writeと独立再読込でreportを完了します。再実行は新しいrefとなり過去実行を上書きしません。偽造した候補やmetadataの同時入力はfinalize schemaで拒否され、metadata自体は証明に使いません。評価ownerが実行前に与える意味上の工程判断は引き続きWCAG評価責務であり、SQLiteは特権DB writerや分散環境に対する暗号学的真正性を保証しません。WCAG evaluation revisionとSQLite provider revisionは別々に扱います。handoff用のtest-only SQLite providerは引き続きproductionで使いません。

helperの必須処理が入力不足・実行不能・保存先能力不足で失敗した場合、影響するscopeを`incomplete` / `unresolved` / `blocked`として閉じます。LLM fallbackで保存、CAS、claim、reservationを成立したことにしません。

## インターフェース

- **入力**: ユーザー要求、要求する最終成果物、識別可能な対象範囲。情報源、既存QA成果物、案件コンテキスト、進行モード、既知のブロック中 / 残存リスク / `要再検証`状態は利用可能な場合に補助入力とします。
- **処理**: 要求成果物に必要な開始Skillを決め、既存成果物の再利用可否、Skillのルーティング、ブロック中 / 再開、上流変更の伝播、修正ルーティング、ワークフロー完了状態を制御します。
- **出力**: ユーザーが要求した最終QA成果物と、必要に応じてワークフロー状態、ブロック中範囲、残存リスク、`要再検証`対象、再開先Skill / 対象を返します。

## 工程固有ロジックの担当

| 工程固有ロジック                                          | 担当Skill                     |
| --------------------------------------------------------- | ----------------------------- |
| 案件Project Context / 成果物配置・編集方針の合意          | `project-context`             |
| 単一sourceから中立signalを抽出・訂正                      | `context-signal-audit`        |
| 横断法則・差異条件の分析と候補run                         | `context-rule-synthesis`      |
| 製品機能ID / 情報源母集団 / 開発差分分類                  | `feature-analysis`            |
| 現在有効な仕様根拠                                        | `spec-analysis`               |
| UI構造・画面・操作・状態・遷移、human editing             | `ui-target-analysis`          |
| 不明点・矛盾 / 仮定                                       | `question-analysis`           |
| QA要求 / 品質目標 / 合意状態                              | `test-requirements-analysis`  |
| テストレベル・タイプ・方式・環境の全体設計                | `test-architecture-design`    |
| QA計画 / 開始・終了基準 / 進捗・差異 / プロジェクトリスク | `test-management`             |
| プロダクトリスク / テスト重点                             | `test-analysis`               |
| テスト要求                                                | `test-requirement-design`     |
| テストアイテム候補                                        | `test-item-analysis`          |
| テスト条件候補                                            | `test-condition-analysis`     |
| テスト条件 / カバレッジ基準 / カバレッジ項目              | `test-condition-design`       |
| 詳細テストケース / 期待結果の根拠の具体化                 | `test-case-design`            |
| E2E自動化対象の選定・理由・履歴                           | `e2e-test-selection`          |
| 生きたテスト対象のUI情報・ふるまい収集 / 管理             | `test-target-inspection`      |
| AIによる詳細TCの実行・期待結果比較・結果記録              | `test-execution`              |
| 非E2E testware実装・静的 / 軽量検証                       | `testware-implementation`     |
| 非E2E testware runner・実行結果・cleanup                  | `testware-execution`          |
| カバレッジ / ギャップ                                     | `coverage-analysis`           |
| 独立レビュー / 重大度                                     | `adversarial-review`          |
| E2E対象・実装可能性・安全条件                             | `e2e-test-inspection`         |
| Playwright E2E実装・静的 / 軽量検証                       | `e2e-test-implementation`     |
| E2E安全確認・実行・構造化結果・cleanup                    | `e2e-test-execution`          |
| E2E実行結果の原因分析・修正routing                        | `e2e-test-result-analysis`    |
| 検証済みE2E結果の報告                                     | `e2e-test-reporting`          |
| Regression baseline / membership / Run / Activity         | `regression-testing`          |
| Charterに沿ったExploration / Investigation                | `exploratory-testing`         |
| 継続QA knowledgeのtriage / lifecycle / lookup             | `qa-knowledge`                |
| 欠陥候補 / 外部Issue引継ぎ / 修正確認依頼                 | `defect-management`           |
| 計画母集団に基づく統合報告snapshot                        | `test-reporting`              |
| QA活動の評価・改善の効果測定                              | `test-evaluation`             |
| referenceや既存evidenceに基づくUI / UX評価                | `usability-evaluation`        |
| live Web UIの操作・観測・ユーザビリティ検査               | `usability-inspection`        |
| WCAG-EM 2.0によるformal WCAG conformance evaluation       | `wcag-conformance-evaluation` |

## ランタイム前提

本Skillは、同一のAgentクライアント上でrepositoryの全Skillが利用可能で、Agentが必要なSkillを追加で読み込み / 利用できる環境を前提とします。これはAgent Skills Specificationが共通Skill-to-Skill APIを保証しているという意味ではありません。

## リソース

- オーケストレーション詳細: `references/guidance.md`
- 製品CI向け成果物受渡しの決定論的検証と信頼境界: `references/ci-handoff.md`、`scripts/ci_handoff.py`。保存先・承認元未選定時の実CI接続はblocked。
- artifact graph / workflow state / currentness / claim / reservation production helper: `scripts/artifact_graph.py`
- Project ContextがDEC / ASM正本ownerの場合のID materialize / 履歴検証: `scripts/project_context_ids.py`
- runtime-v2 migration / scope ownershipのnext action: `scripts/migration_preflight.py`
- previous downstream scope ownership / inactive history / scope removal resolution: `scripts/downstream_state.py`
- 案件コンテキスト既定形: `assets/project-context-template.md`
- 任意のワークフロー状態表: `assets/workflow-state-template.md`
