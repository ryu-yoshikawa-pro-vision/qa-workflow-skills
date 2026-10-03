# UIテスト対象分析モード実装Plan

このPlanは、PR #14マージ後の22 Skill構成を維持したまま、テスト設計前の「仕様理解・テスト対象整理」を再現可能なAgent Skill契約として追加するための実装計画です。特定のAI製品向け連携機構は追加せず、既存のAgent Skills構造の中でAIエージェントが利用できる形にします。

## 対象ブランチ

feat/ui-test-target-analysis-profile

## 基準

- 対象リポジトリ: ryu-yoshikawa-pro-vision/qa-workflow-skills
- 基準branch: PR #14 merge後のlatest main
- 先行baseline: PR #14 `feat/usability-evaluation-skill`
- PR #14確認head: db61c4f0697b07ff9abbba0d2dde2571dfaaddb0
- 正規Skill数: 22
- 実装開始前に `_07_pr14-baseline-and-integration.md` のrebase / conflict gateを必ず通す
- 既存の主責務:
  - spec-analysis: 現在有効な仕様根拠、SPEC / DECISION / INFERENCE / UNKNOWN
  - question-analysis: 不明点・矛盾分類、回答正規化、再開先
  - qa-workflow: 開始点、再利用、routing、変更伝播、完了
  - test-target-inspection: 生きた実対象のcurrent UI / ふるまい観測
- 各Skillは既存どおり `skills/<skill-name>/SKILL.md` を持つAgent Skills形式で管理され、AIエージェントが必要なSkillを利用する前提を維持する

## 背景

現在のspec-analysisは、Figma、要件書、Q&A、リポジトリ、リリース資料などを統合し、現在有効な仕様根拠を解決する責務を既に持っています。question-analysisも、解決済み事項を再質問せず、回答をSPEC / DECISION / ASMへ正規化して最も早い責任Skillへ戻す契約を持っています。

一方、実務でテスト設計前に必要になる次の成果物契約は、現在の既定output-templateだけでは十分に固定されていません。

- 画面をURL / path単位のPAGEとして整理する
- 同一route内の表示差をSTATE / VIEW / STEPとしてPAGEと分離する
- MODAL、ブラウザ標準dialog、global panel、外部画面、shared pageを分離する
- 業務ルール、入力制約、通知、外部連携、CSV等の案件固有仕様を複数Markdownへ分割する
- 資料由来の仕様とrepositoryで観測した実装状況を別レイヤーで管理する
- UNKNOWNを安定IDで管理し、回答後に本文・不明点一覧・履歴を同期する
- 更新のたびに差分ファイルではなく完全版を生成する
- version、CHANGELOG、MANIFESTを揃え、複数ファイル間の状態を一貫させる
- 既存spec-analysisのcanonical仕様モデル（SRC / SPEC / DECISION / INFERENCE / UNKNOWN / Current Effective Authority / Machine Entity）を維持したまま、人間が利用しやすい複数Markdownへ構造化する
- テスト分析・テスト条件・テストケースへ先回りせず、「対象理解」の成果物として閉じる

この不足を新Skillで埋めると、spec-analysisとのAuthority解決責務が重複します。またtest-target-inspectionへ統合すると、仕様理解と生きた実対象観測の境界を崩します。

そのため、新Skillは追加せずspec-analysisに条件付きの「UIテスト対象分析モード」を追加します。

## 目的

1. テスト設計前の仕様理解を、案件固有資料・Q&A・実装証拠から追跡可能な複数Markdown packageへ整理できるようにする
2. UI構造、状態、業務ルール、入力制約、通知・外部連携、不明点、実装状況を同一の責務境界で継続更新しつつ、既存spec-analysisのcanonical Authority / Machine Entity契約を壊さない
3. question-analysisの回答正規化と連携し、既存UNKNOWNを再質問・再採番せず更新できるようにする
4. qa-workflowから「仕様理解packageだけ欲しい」要求へ最短routingできるようにする
5. test-target-inspectionの「生きた実対象観測」と役割を混同しない
6. PR #14後の既存22 Skill、runtime、artifact graph、Regression / Exploration / QA Knowledge、UI/UX / live usability / formal WCAG契約を壊さない

## 固定方針

LLM / deterministic処理の責務境界は `2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md` を正本とします。LLMの意味判断をscriptへ移さず、形式・参照・集計・fingerprint等の再現可能な定型処理だけをSkill-local helper / validatorへ移します。LLMはsemantic identity、UI分類、file trigger、UNKNOWNの関連Scope / Blocking Scope / 関連File、required domainの意味上の母集団、extension要否、same-UNK / new-UNK、explicit retire等を判断します。その後のstable ID採番、row状態導出、Markdown serialization、scope readiness、scope別machine handoff、Stable ID lifecycle / 影響file、README / Machine Entity / MANIFESTはhelperが決定論実行します。Current UNKNOWNの存在だけでpackage全体を停止せず、semantic quality gateはcanonical write前に実施します。DEC / ASMはcanonical `DEC-xxx / ASM-xxx` を維持し、Project Contextがownerの場合だけqa-workflow helperで番号決定・materialize・previous ID削除検証を行います。packageはDEC / ASMをterminal retireしません。


### 1. 新Skillは追加しない

UIテスト対象分析はspec-analysisの条件付き出力モードとして実装します。

新しいSkill名、23個目のSkill、別のAuthority ownerは作りません。

### 2. spec-analysisの既定出力を置換しない

既存assets/output-template.mdは通常の単一仕様分析に引き続き使用します。

UIテスト設計前の対象理解を継続利用する成果物として残す場合、複数資料を統合して画面・状態・業務ルール・不明点を追跡可能に管理する場合、または既存の対象理解packageを更新する場合にUIテスト対象分析モードを選択します。**継続利用・更新を目的とする場合は、初回時点で単一表に収まる規模でもmodeを優先します。** 単発の仕様要約、Authority競合解消、継続更新しない一時的な仕様整理では既存の通常出力を使います。Markdownという語の有無だけでは選択しません。

### 3. canonical仕様モデルを1箇所に維持する

複数Markdown packageでも、既存 `assets/output-template.md` が持つ `情報源 / 正本参照一覧`、`分析項目`、`現在有効な仕様根拠`、Machine Entityとの対応を失いません。

modeでは `09_authority_and_traceability.md` をcanonical仕様モデルの正本とし、他ファイルはそのstable IDを参照する構造化ビューとします。SPEC / DECISION / INFERENCE / UNKNOWNやCurrent Effective Authorityを複数ファイルで別々に再定義しません。

Authority Machine Entityは既存 `authority_entities.py`、下流handoff用のcurrent Acceptance Criteria Machine Entityは `ui_target_package.py build-machine-evidence` から決定論生成します。`build-machine-evidence` は既存 `render_machine_entities()` を使って `### Machine Entities: spec-analysis` のMarkdown section全体までread-onlyで返します。packageへの書込みは`materialize`内部の同一projectionだけが行い、Agent / callerは返却Markdownをpackageへ直接書き戻しません。US / UC / Behavior自体はMachine Entity化せず、fingerprint / normalized machine input / expected identity / JSON wrapperをLLMが手入力しません。

### 4. 実装は仕様Authorityではない

repository、実画面、Page Object、API実装は既存契約どおり補助証拠です。

案件コンテキストや正本一覧が明示的に実装をAuthorityへ指定しない限り、実装差分を仕様本文へ自動昇格させません。

仕様と実装の差はrepository implementation statusとして分離します。

### 5. test-target-inspectionと統合しない

- spec-analysis: 仕様書、Q&A、repository等から「期待挙動として何が有効か」を整理する
- test-target-inspection: 生きた実対象へ接続して「現在何が観測できるか」を記録する

currentなUI観測が必要になった場合だけqa-workflowでtest-target-inspectionへroutingし、観測事実をspec-analysisのAuthorityへ自動昇格させません。

### 6. 質問回答はquestion-analysis経由で正規化する

会話回答を生のまま仕様本文へ流しません。

正式決定ならDECISION、更新済みAuthorityならSPEC、暫定前提なら承認済みASMへ正規化してからspec-analysis packageへ反映します。

### 7. packageは完全版を正とする

version更新時は変更ファイルだけではなく、そのversionの完全なpackageを成立させます。

前versionの内容を参照しなければ現在状態を理解できない構造にしません。

### 8. AIエージェント用Skillとして既存Agent Skills構造を維持する

今回追加するmodeは、既存Skillと同じく `SKILL.md` / `references/` / `assets/` の段階的開示で利用できるようにします。

特定のAI製品、connector、remote loader、bootstrap runtimeは追加しません。AIエージェントがSkillを利用する方法そのものは既存のAgent Skills利用前提を継続します。

## Plan分割

- 責務・既存Skill境界:
  - 2026-10-01_201500_ui-test-target-analysis-mode_01_scope-and-responsibilities.md
- spec-analysisのUIテスト対象分析package:
  - 2026-10-01_201500_ui-test-target-analysis-mode_02_spec-analysis-package.md
- question-analysis / qa-workflow統合:
  - 2026-10-01_201500_ui-test-target-analysis-mode_03_workflow-integration.md
- 評価、CI、実装順序、完了条件:
  - 2026-10-01_201500_ui-test-target-analysis-mode_04_evaluation-ci-implementation-order.md
- LLM / deterministic処理の責務境界:
  - 2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md
- package schema / helper I/O / legacy migration:
  - 2026-10-01_201500_ui-test-target-analysis-mode_06_package-schema-and-helper-contracts.md
- PR #14 baseline / integration:
  - 2026-10-01_201500_ui-test-target-analysis-mode_07_pr14-baseline-and-integration.md
- UI操作の振る舞い分解 / Acceptance Criteria traceability:
  - 2026-10-01_201500_ui-test-target-analysis-mode_08_behavior-decomposition-and-acceptance-traceability.md
- Acceptance Criterion Machine Entity / shared runtime / test-requirement-design v2:
  - 2026-10-01_201500_ui-test-target-analysis-mode_09_runtime-entity-and-test-requirement-contracts.md

各詳細Planが担当範囲の正本です。本親Planへ詳細契約を重複記載しません。

## 主な変更対象

### spec-analysis

変更:
- skills/spec-analysis/SKILL.md
- skills/spec-analysis/references/guidance.md
- 新規 skills/spec-analysis/references/ui-test-target-analysis.md
- 新規 skills/spec-analysis/assets/ui-test-target-analysis/*
- 新規 skills/spec-analysis/scripts/ui_target_package.py（package schema / helper I/O / legacy migration contractは `_06_package-schema-and-helper-contracts.md` を正本とする）
- skills/spec-analysis/evals/semantic/*
- skills/spec-analysis/evals/deterministic/validator.py
- skills/spec-analysis/evals/output/*
- tests/skills/evals/semantic/*
- UI target package helper用repository unit test

既存 `skills/spec-analysis/scripts/authority_entities.py` はAuthority Entity生成の正本として再利用します。current AC Entity / spec-analysis normalized_skill_input / expected identityは `ui_target_package.py` が生成します。

### test-requirement-design

変更:
- skills/test-requirement-design/SKILL.md
- skills/test-requirement-design/references/guidance.md
- skills/test-requirement-design/assets/output-template.md
- skills/test-requirement-design/scripts/requirement_structure.py（`requirement-structure-v2`）
- 新規 skills/test-requirement-design/scripts/runtime_v1_cutover.py
- skills/test-requirement-design/evals/deterministic/*
- skills/test-requirement-design/evals/semantic/*
- skills/test-requirement-design/evals/output/*
- runtime / repository contract tests

目的はcurrent ACをTRまたは明示的dispositionへ閉じ、AC / linked UIOP / scope / direct UI構造とancestor / linked FIELD・RULE・FLOW・NOTIFY・INTERACT / linked INF / 親Behavior / 親UC / 親US / Authority変更をTR freshnessへ伝播させることです。package-local itemはAC content fingerprintへ寄与させ、Authorityだけをupstream Entity dependencyにします。repository由来のimplementation-only structureもtarget-model dependencyとしてfreshnessには影響しますが、Authorityへ昇格しません。`requirement-structure-v2` はtop-level `acceptance_criteria[]` をknown semantic AC集合として必須にし、artifact modeではupstream AC Entityとのexact一致とAC/Authority dependencyを要求、direct modeではknown ID / closure検証を行い存在しないMachine Entity dependencyを合成しません。TRの責務をACの言い換えへ変更しません。

### question-analysis

変更:
- skills/question-analysis/SKILL.md
- skills/question-analysis/references/guidance.md
- skills/question-analysis/assets/output-template.md
- 新規 skills/question-analysis/scripts/question_ids.py
- skills/question-analysis/evals/semantic/*
- skills/question-analysis/evals/deterministic/validator.py
- skills/question-analysis/evals/output/*
- question-analysis helper用repository unit test

目的はUNKNOWNの安定参照、回答後の差分反映、解消済み履歴とcurrent unknownの分離です。既存の質問分類自体は変更しません。new QとUNKNOWNの意味対応はLLMに残し、Q番号・使用済みQ ID履歴・current Q table serialization・UNKNOWN参照の形式 / 存在検証は `question_ids.py` にまとめて決定論化します。既存成果物更新ではprevious artifactを必須とし、回答済みQがcurrent一覧から消えても過去Q IDを再利用しません。

### shared runtime / Machine Entity contract

PR #14確認headに存在する9個のSkill-local `runtime_contract.py` を同一shared contractとして同期します。

- spec-analysis
- test-analysis
- test-requirement-design
- test-condition-design
- test-case-design
- coverage-analysis
- qa-workflow
- usability-inspection
- wcag-conformance-evaluation

変更:
- 上記9個の `runtime_contract.py`
- `tests/skills/runtime/test_runtime_dispatch.py`
- `tests/skills/runtime/test_runtime_portability.py`
- `scripts/skills/evals/deterministic/runtime_validator.py`
- shared runtime / Machine Entity versionを参照するcurrent Skill文書・asset・eval fixture・repository test
- requirement-structure contract versionを参照するruntime / fixture / integration tests
- 新規 skills/test-condition-design/scripts/runtime_v1_cutover.py
- 新規 skills/test-case-design/scripts/runtime_v1_cutover.py

`acceptance_criterion` Entity type、`acceptance_refs` canonicalization、spec-analysis Authority + AC expected Entity導出はshared runtime / Machine Entityの意味契約変更です。そのため9コピーをbyte-identicalに揃え、`RUNTIME_CONTRACT_VERSION` を `runtime-v1` → `runtime-v2`、`ENTITY_SCHEMA_VERSION` を `entity-state-v1` → `entity-state-v2` へ更新します。envelope field shapeとfreshness algorithmは維持します。

旧runtime-v1 / entity-state-v1 evidenceをv2 current evidenceとして読み替えません。shared `runtime_contract.py` はschema / canonicalization / evidence parse / validation / freshness等の共通契約だけを持ち、one-time migrationのSkill固有projectionは持ちません。TRD / TCD / TCのv1→v2変換だけを各Skill-local `runtime_v1_cutover.py` へ置きます。その他のruntime Skillはcanonical spec成果物、validated保存Machine Runtime Input、current workflow stateを正本としてv2 evidenceを再生成し、保存inputがないinspection系だけ既存Skillの通常rerun / re-observationへ戻します。proseからv2 inputを推測再構築しません。qa-workflow用の新しいcutover wrapperは追加せず、既存workflowが `_09` の固定順をオーケストレーションします。既存v1 downstream artifactがある場合はsemantic不変のruntime cutoverを先に完了し、その後UI target package migration / AC生成、requirement-structure-v2の通常semantic update、stale downstream再実行の順に進めます。

active Machine Evidence templateはversion文字列だけを置換しません。runtime Skillは `render_runtime_input()` / `render_runtime_result()` / `render_machine_entities()`、spec-analysisは `authority_entities.py` / `build-machine-evidence` の生成結果を正本とし、旧 `entity_schema_version` / `dependencies` / `runtime-contract-v1` / `runtime-envelope-v1` の手書き擬似schemaを削除します。

### qa-workflow

変更:
- skills/qa-workflow/references/guidance.md
- skills/qa-workflow/assets/project-context-template.md
- 新規 skills/qa-workflow/scripts/project_context_ids.py
- skills/qa-workflow/evals/deterministic/routing_cases.json
- skills/qa-workflow/evals/deterministic/routing_candidate_outputs.json
- project_context_ids.py用repository unit test
- routing fixtureの固定件数を検証するrepository test / docs current count

「テスト設計前の仕様理解package」はspec-analysisから開始し、未解決事項があればquestion-analysisへ進み、回答反映後spec-analysisへ戻すroutingを追加します。resolver失効時はspec-analysisがsame-UNK reopen / new UNKをcanonical modelへ先に反映してからquestion-analysisへcurrent UNKNOWN集合を渡します。正式DECISION / 承認済みASMへ正規化する場合、意味判断はquestion-analysis / stakeholder側に残します。Project Contextが実際の正本ownerである場合だけqa-workflow helperがDEC / ASM ID採番とSection 12 / 13 materialize、previous ID削除検証を行います。別ownerでもcanonical Authority IDは `DEC-xxx / ASM-xxx` を維持し、外部record IDをauthority_idへ流用しません。

### repository docs / CI

PR #14後のREADME / EVALS / PROJECT_CONTEXT / CIを編集baselineにします。

変更:
- README.md: mode導線と#14 Skillとの目的境界を必要最小限に追記
- EVALS.md: PR #16固有の評価差分だけ追記
- docs/PROJECT_CONTEXT.md: current状態を持つ場合だけ同期
- tests/skills/evals/semantic/*: critical criterion coverage / mode非選択回帰を追加
- production helperのrepository unit / portability test

PR #14後のCIは `skills/*/scripts` を動的compileするため、helper compile目的のworkflow個別path追加は行いません。新しいGitHub Actions workflowも追加しません。

## 対象外

- 特定のAI製品向けintegration / connector / remote loader
- 新しいSkill-to-Skill API
- 案件固有の仕様資料をqa-workflow-skills repoへ保存する仕組み
- 任意の複数Markdownをmergeする汎用document framework
- test-analysis / test-condition-design / test-case-designの責務変更。test-requirement-designにはAC traceability / closureだけを追加する
- test-target-inspectionのbrowser観測契約変更
- Agent Skills Specificationの独自拡張
- ZIP専用runtime。archive出力は利用Agentのartifact機能で行い、Skillの正規処理には含めない
- 導入先project固有のstorage / external API / connector / process起動 / timeout / lock / orchestrationを包むwrapper。Skill repoはQA契約固有の決定論処理だけを持ち、環境固有の接続・実行制御は導入先project / harnessが担当する
- 既存production scriptへ数行で収まるdefault補完・入力受け渡しだけのadapter script。独立した現在要件を持たない処理は既存scriptへ統合する

## 成功条件

- 新Skillなしで今回の責務をspec-analysisへ収められる
- UI構造をPAGE / STATE・VIEW・STEP / MODAL / browser dialog / panel / external / sharedへ区別できる
- 仕様Authorityとrepository implementation statusが混同されない
- UNKNOWNが安定参照され、回答後に解消済み履歴とcurrent unknownが整合する
- package更新時にpackage schema version、content version、CHANGELOG、MANIFESTと各ファイルの現在状態が一致し、Stable ID lifecycle / 影響fileをLLM手入力に依存しない
- 通常のspec-analysis出力は従来どおり利用できる
- test-target-inspectionの責務を侵食しない
- qa-workflowが最短経路でmodeを選択でき、usability-evaluation / usability-inspection / wcag-conformance-evaluationへ誤routeしない
- package内のcanonical Authority契約が既存spec-analysisと互換であり、Authority + current AC Machine Entity、spec-analysis normalized_skill_input、expected identity、Machine Entities Markdown sectionまでLLM手組みなしで接続できる
- 複数Markdown packageを既存semantic runnerへ入力できる一意なevaluation projectionが定義されている
- modeが既存Agent Skills形式のままAIエージェントから利用できる
- mode導入前のlegacy / unversioned packageをsemantic mapping + deterministic validationでcurrent schemaへ移行できる
- PR #14後のAgent Skills検証、trigger、semantic、deterministic / workflow routing回帰がPASSする
- README / EVALS等の現在値を変更した場合はPR #14後のcurrent repositoryから導出した実データと一致する
- PR #14のusability / WCAG finding・observation・resultを仕様Authorityへ自動昇格しない
- 機能scopeごとにUI操作有無を判定し、UI操作ありではUS → UC → Behavior → ACを完全に分析し、情報不足はnot-applicableへ逃げずUNKNOWN / blockedとして残る
- test-requirement-designまで進む要求では、current ACがTRまたは明示的dispositionへ閉じる。AC linkはACだけをcloseし、Authorityは従来どおりTR authority_refsまたはAuthority Dispositionで独立closureする。AC / 親Behavior / 親UC / 親US / Authority変更は必要なTR freshnessへ伝播する。仕様理解packageだけを要求された場合は、このclosureをpackage単体の完了条件にしない
- 標準package fileはrequired core payload + required control file `MANIFEST.md` + 固定triggerによる条件付き必須とし、Agentの自由裁量で作成有無を変えない
- LLMは仕様意味・UI意味・semantic identity / explicit retire判断に集中し、version / stable ID / Markdown table・known section・標準file materialization / hash /参照整合 / UNKNOWN件数 / MANIFEST / file applicability整合 / Stable ID lifecycle / Machine Entity projection等の定型処理はhelper / validatorへ移る
- runtime-v2 / entity-state-v2 cutoverでv1 evidence自体はcurrent扱いせず、TRD / TCD / TC Skill-local cutover helperにより内容不変のTR / TCN / model / CI / TC stable identityとdeleted / inactive履歴だけを決定論的に維持できる
- Project Context ownerのDEC / ASMは撤回 / 置換済みでもID rowを削除せず、previous IDの再利用をhelperが防ぐ
- current packageがrepository evidenceをcarry-forwardする場合、08の確認revisionを勝手にcurrentへ更新せず保持できる
- 同じpackage rootへの`materialize`はcallerが直列化し、helperはUTF-8 without BOM / LF / terminal LFのcanonical bytesをstagingへ生成・検証してからpackage単位でcommitする。途中I/O failureで旧版 / 新版が混在した完成packageを残さない
- package-local stable IDを持つ複数UI target packageのMachine Entity blockを同一current Entity collectionへ直接mergeせず、必要ならspec-analysisで1つのcurrent canonical package / normalized inputへ意味統合してから下流へ渡す
- helperがsemantic判断を代替せず、通常spec-analysisの柔軟性を損なわない
- production helperの公開CLIは独立した実行用途があるoperationだけに限定し、採番・version計算・MANIFEST生成・impact算出等のmaterialize内部処理をfocused useだけのために公開operation化しない
