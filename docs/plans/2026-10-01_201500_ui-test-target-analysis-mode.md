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

LLM / deterministic処理の責務境界は `2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md` を正本とします。LLMの意味判断をscriptへ移さず、形式・参照・集計・fingerprint等の再現可能な定型処理だけをSkill-local helper / validatorへ移します。


### 1. 新Skillは追加しない

UIテスト対象分析はspec-analysisの条件付き出力モードとして実装します。

新しいSkill名、23個目のSkill、別のAuthority ownerは作りません。

### 2. spec-analysisの既定出力を置換しない

既存assets/output-template.mdは通常の単一仕様分析に引き続き使用します。

UIテスト設計前の対象理解を継続利用する成果物として残す場合、複数資料を統合して画面・状態・業務ルール・不明点を追跡可能に管理する場合、または既存の対象理解packageを更新する場合にUIテスト対象分析モードを選択します。単発の仕様要約、Authority競合解消、単一表で十分な仕様整理では既存の通常出力を使います。Markdownという語の有無だけでは選択しません。

### 3. canonical仕様モデルを1箇所に維持する

複数Markdown packageでも、既存 `assets/output-template.md` が持つ `情報源 / 正本参照一覧`、`分析項目`、`現在有効な仕様根拠`、Machine Entityとの対応を失いません。

modeでは `09_authority_and_traceability.md` をcanonical仕様モデルの正本とし、他ファイルはそのstable IDを参照する構造化ビューとします。SPEC / DECISION / INFERENCE / UNKNOWNやCurrent Effective Authorityを複数ファイルで別々に再定義しません。

Machine Entityは既存 `authority_entities.py` の入力となるCurrent Effective Authorityから生成し、fingerprintを手入力しません。

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

既存 `skills/spec-analysis/scripts/authority_entities.py` は変更要否を確認し、既存contractで足りる場合は変更しません。Machine Entity生成の正本として再利用します。

### question-analysis

変更:
- skills/question-analysis/SKILL.md
- skills/question-analysis/references/guidance.md
- skills/question-analysis/assets/output-template.md
- 新規 skills/question-analysis/scripts/unknown_links.py
- skills/question-analysis/evals/semantic/*
- skills/question-analysis/evals/deterministic/validator.py
- skills/question-analysis/evals/output/*
- unknown_links.py用repository unit test

目的はUNKNOWNの安定参照、回答後の差分反映、解消済み履歴とcurrent unknownの分離です。既存の質問分類自体は変更しません。

### qa-workflow

変更:
- skills/qa-workflow/references/guidance.md
- skills/qa-workflow/evals/deterministic/routing_cases.json
- skills/qa-workflow/evals/deterministic/routing_candidate_outputs.json
- routing fixtureの固定件数を検証するrepository test / docs current count

「テスト設計前の仕様理解package」はspec-analysisから開始し、未解決事項があればquestion-analysisへ進み、回答反映後spec-analysisへ戻すroutingを追加します。

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
- test-analysis以降のテスト設計ロジック変更
- test-target-inspectionのbrowser観測契約変更
- Agent Skills Specificationの独自拡張
- ZIP専用runtime。archive出力は利用Agentのartifact機能で行い、Skillの正規処理には含めない

## 成功条件

- 新Skillなしで今回の責務をspec-analysisへ収められる
- UI構造をPAGE / STATE・VIEW・STEP / MODAL / browser dialog / panel / external / sharedへ区別できる
- 仕様Authorityとrepository implementation statusが混同されない
- UNKNOWNが安定参照され、回答後に解消済み履歴とcurrent unknownが整合する
- package更新時にpackage schema version、content version、CHANGELOG、MANIFESTと各ファイルの現在状態が一致する
- 通常のspec-analysis出力は従来どおり利用できる
- test-target-inspectionの責務を侵食しない
- qa-workflowが最短経路でmodeを選択でき、usability-evaluation / usability-inspection / wcag-conformance-evaluationへ誤routeしない
- package内のcanonical Authority / Machine Entity契約が既存spec-analysisと互換であり、09からMachine EntityまでLLM手組みなしで接続できる
- 複数Markdown packageを既存semantic runnerへ入力できる一意なevaluation projectionが定義されている
- modeが既存Agent Skills形式のままAIエージェントから利用できる
- mode導入前のlegacy / unversioned packageをsemantic mapping + deterministic validationでcurrent schemaへ移行できる
- PR #14後のAgent Skills検証、trigger、semantic、deterministic / workflow routing回帰がPASSする
- README / EVALS等の現在値を変更した場合はPR #14後のcurrent repositoryから導出した実データと一致する
- PR #14のusability / WCAG finding・observation・resultを仕様Authorityへ自動昇格しない
- LLMは仕様意味・UI意味・semantic identity判断に集中し、version / hash /参照整合 / UNKNOWN件数 / MANIFEST等の定型処理はhelper / validatorで補助・検証される
- helperがsemantic判断を代替せず、通常spec-analysisの柔軟性を損なわない
