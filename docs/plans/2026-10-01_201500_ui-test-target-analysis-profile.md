# UIテスト対象分析プロファイル実装Plan

このPlanは、現在の19 Skill構成を維持したまま、テスト設計前の「仕様理解・テスト対象整理」を再現可能なAgent Skill契約として追加するための実装計画です。特定のAI製品向け連携機構は追加せず、既存のAgent Skills構造の中でAIエージェントが利用できる形にします。

## 対象ブランチ

feat/ui-test-target-analysis-profile

## 基準

- 対象リポジトリ: ryu-yoshikawa-pro-vision/qa-workflow-skills
- 基準branch: main
- 基準commit: dec3f7c764db2869dc24eb3d6f154712a6677068
- 正規Skill数: 19
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
- テスト分析・テスト条件・テストケースへ先回りせず、「対象理解」の成果物として閉じる

この不足を新Skillで埋めると、spec-analysisとのAuthority解決責務が重複します。またtest-target-inspectionへ統合すると、仕様理解と生きた実対象観測の境界を崩します。

そのため、新Skillは追加せずspec-analysisに条件付きの「UIテスト対象分析プロファイル」を追加します。

## 目的

1. テスト設計前の仕様理解を、案件固有資料・Q&A・実装証拠から追跡可能な複数Markdown packageへ整理できるようにする
2. UI構造、状態、業務ルール、入力制約、通知・外部連携、不明点、実装状況を同一の責務境界で継続更新できるようにする
3. question-analysisの回答正規化と連携し、既存UNKNOWNを再質問・再採番せず更新できるようにする
4. qa-workflowから「仕様理解packageだけ欲しい」要求へ最短routingできるようにする
5. test-target-inspectionの「生きた実対象観測」と役割を混同しない
6. 既存19 Skill、runtime、artifact graph、Regression / Exploration / QA Knowledge契約を壊さない

## 固定方針

### 1. 新Skillは追加しない

UIテスト対象分析はspec-analysisの条件付き出力プロファイルとして実装します。

新しいSkill名、20個目のSkill、別のAuthority ownerは作りません。

### 2. spec-analysisの既定出力を置換しない

既存assets/output-template.mdは通常の単一仕様分析に引き続き使用します。

複数Markdown packageが必要な場合だけ、追加するUIテスト対象分析プロファイルを選択します。

### 3. 実装は仕様Authorityではない

repository、実画面、Page Object、API実装は既存契約どおり補助証拠です。

案件コンテキストや正本一覧が明示的に実装をAuthorityへ指定しない限り、実装差分を仕様本文へ自動昇格させません。

仕様と実装の差はrepository implementation statusとして分離します。

### 4. test-target-inspectionと統合しない

- spec-analysis: 仕様書、Q&A、repository等から「期待挙動として何が有効か」を整理する
- test-target-inspection: 生きた実対象へ接続して「現在何が観測できるか」を記録する

currentなUI観測が必要になった場合だけqa-workflowでtest-target-inspectionへroutingし、観測事実をspec-analysisのAuthorityへ自動昇格させません。

### 5. 質問回答はquestion-analysis経由で正規化する

会話回答を生のまま仕様本文へ流しません。

正式決定ならDECISION、更新済みAuthorityならSPEC、暫定前提なら承認済みASMへ正規化してからspec-analysis packageへ反映します。

### 6. packageは完全版を正とする

version更新時は変更ファイルだけではなく、そのversionの完全なpackageを成立させます。

前versionの内容を参照しなければ現在状態を理解できない構造にしません。

### 7. AIエージェント用Skillとして既存Agent Skills構造を維持する

今回追加するprofileは、既存Skillと同じく `SKILL.md` / `references/` / `assets/` の段階的開示で利用できるようにします。

特定のAI製品、connector、remote loader、bootstrap runtimeは追加しません。AIエージェントがSkillを利用する方法そのものは既存のAgent Skills利用前提を継続します。

## Plan分割

- 責務・既存Skill境界:
  - 2026-10-01_201500_ui-test-target-analysis-profile_01_scope-and-responsibilities.md
- spec-analysisのUIテスト対象分析package:
  - 2026-10-01_201500_ui-test-target-analysis-profile_02_spec-analysis-package.md
- question-analysis / qa-workflow統合:
  - 2026-10-01_201500_ui-test-target-analysis-profile_03_workflow-integration.md
- 評価、CI、実装順序、完了条件:
  - 2026-10-01_201500_ui-test-target-analysis-profile_04_evaluation-ci-implementation-order.md

各詳細Planが担当範囲の正本です。本親Planへ詳細契約を重複記載しません。

## 主な変更対象

### spec-analysis

変更:
- skills/spec-analysis/SKILL.md
- skills/spec-analysis/references/guidance.md
- 新規 skills/spec-analysis/references/ui-test-target-analysis.md
- 新規 skills/spec-analysis/assets/ui-test-target-analysis/*

必要に応じて:
- skills/spec-analysis/evals/semantic/*
- spec-analysisのtrigger境界に影響がある場合のみtrigger dataset

### question-analysis

変更候補:
- skills/question-analysis/SKILL.md
- skills/question-analysis/references/guidance.md
- skills/question-analysis/assets/output-template.md
- skills/question-analysis/evals/semantic/*

目的はUNKNOWNの安定参照、回答後の差分反映、解消済み履歴とcurrent unknownの分離です。既存の質問分類自体は変更しません。

### qa-workflow

変更候補:
- skills/qa-workflow/references/guidance.md
- skills/qa-workflow/evals/deterministic/routing_cases.json
- 必要ならREADME.md

「テスト設計前の仕様理解package」はspec-analysisから開始し、未解決事項があればquestion-analysisへ進み、回答反映後spec-analysisへ戻すroutingを追加します。


## 対象外

- 特定のAI製品向けintegration / connector / remote loader
- 新しいSkill-to-Skill API
- 案件固有の仕様資料をqa-workflow-skills repoへ保存する仕組み
- 任意の複数Markdownをmergeする汎用document framework
- test-analysis以降のテスト設計ロジック変更
- test-target-inspectionのbrowser観測契約変更
- Agent Skills Specificationの独自拡張
- ZIP生成を必須とする特定AIエージェント環境依存runtime

## 成功条件

- 新Skillなしで今回の責務をspec-analysisへ収められる
- UI構造をPAGE / STATE・VIEW・STEP / MODAL / browser dialog / panel / external / sharedへ区別できる
- 仕様Authorityとrepository implementation statusが混同されない
- UNKNOWNが安定参照され、回答後に解消済み履歴とcurrent unknownが整合する
- package更新時にversion、CHANGELOG、MANIFESTと各ファイルの現在状態が一致する
- 通常のspec-analysis出力は従来どおり利用できる
- test-target-inspectionの責務を侵食しない
- qa-workflowが最短経路でprofileを選択できる
- profileが既存Agent Skills形式のままAIエージェントから利用できる
- 既存Agent Skills検証、trigger、semantic、deterministic / workflow routing回帰がPASSする
- README / EVALS等の現在値を変更した場合は実データと一致する
