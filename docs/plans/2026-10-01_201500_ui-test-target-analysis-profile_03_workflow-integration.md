# UIテスト対象分析プロファイル: workflow integration

親Plan:
2026-10-01_201500_ui-test-target-analysis-profile.md

この文書はquestion-analysisとqa-workflowの統合契約を正本とします。

## 1. question-analysis変更

### 1.1 目的

profile packageのUNKNOWNを、回答反映のたびに再質問・再採番せず継続管理できるようにします。

既存のブロッカー / 要確認 / 仮定可能 / 提案・任意分類は変更しません。

### 1.2 SKILL.md

必要最小限の追加:

- 入力がspec-analysisのUNK-xxxを持つ場合、そのstable IDを保持する
- 回答済み論点を新しい質問IDだけで別論点化しない
- 回答反映で複数仕様fileが変わる場合でも、Authority正規化後はspec-analysisへ戻す
- versioned UI target packageの差分反映責務はspec-analysisであり、question-analysis自身がpackageを編集する責務を持たない

### 1.3 references/guidance.md

「回答の正規化」を次で補強します。

- 元UNKNOWN IDを保持する
- 暫定回答と正式回答を区別する
- 暫定回答が後で正式DECISIONへ変わっても同じUNKNOWN lineageを使う
- 「回答が不明」は回答履歴として残してもUNKNOWNは解消しない
- 正式回答で解消したUNKNOWNはcurrent unknownから除外する
- 解消済み事項を再質問しない
- 新資料で再び競合が発生した場合は旧UNKNOWNを無条件に再openせず、同一論点か新しい競合かを判断する

### 1.4 assets/output-template.md

既存Q-xxxを廃止しません。

次の列追加を検討します。

- 関連UNKNOWN ID

spec-analysis由来の論点ならUNK-xxxを記録し、質問単位のQ-xxxと仕様UNKNOWNを追跡できるようにします。

新しいUNKNOWN registryは作りません。

## 2. qa-workflow変更

### 2.1 routing

次の要求をspec-analysisのUI target profileへroutingします。

- テスト設計前に仕様理解だけ整理したい
- テスト対象をMarkdown package化したい
- PAGE / MODAL / STATE等に分けたい
- 既存対象分析packageを更新したい
- 不明点回答をpackageへ反映したい

基本経路:

spec-analysis(UI target profile)
→ unresolvedがあればquestion-analysis
→ 回答正規化
→ spec-analysis(UI target profile)差分更新
→ ユーザー要求が仕様理解までなら完了
→ テスト分析も要求されている場合だけtest-analysisへ進む

### 2.2 gated mode

ユーザーが「1手順ずつ」「理解を確認してから」「ファイル出力前に確認」等を指定した場合、既存gated modeを使います。

profile固有の新しいmodeは作りません。

### 2.3 test-target-inspection routing

次の場合だけtest-target-inspectionへ進めます。

- currentな実画面の表示名 / 到達可否が必要
- 仕様資料だけでは現在UI状態を判断できない
- userが実画面のcurrent観測を要求
- repository情報ではなく実対象の観測が必要

repositoryを読むだけの調査をtest-target-inspectionと呼びません。

### 2.4 repository調査

repository事実が必要で、AIエージェントがrepositoryを利用できる場合は補助入力として収集できます。

ただし:

- repo factはAuthorityではない
- spec-analysis packageの08へ分離
- 実装差分はquestion-analysisへ不要な仕様質問として戻さない
- Authority上の期待挙動が明確なら差分として記録する

特定のrepository接続方式、connector、tool名はSkill契約へ固定しません。

### 2.5 routing fixture

skills/qa-workflow/evals/deterministic/routing_cases.jsonへ最低限次を追加します。

1. 「テスト設計前に仕様理解を複数Markdownへ整理」→ spec-analysis
2. 「既存仕様理解packageへ不明点回答を反映」→ question-analysis解消後spec-analysis resume
3. 「current実画面を見て画面資料を更新」→ test-target-inspection
4. 「仕様書とrepoを比較して期待仕様を整理」→ spec-analysis。repo差分をAuthority化しない
5. 「仕様理解だけで止めたい」→ test-analysisへ自動進行しない

routing case数変更に伴うREADME / EVALS / PROJECT_CONTEXT等の現在値は実データに合わせて同期します。

## 3. Agent Skillsとしての利用前提

今回のprofileは既存Skillと同じAgent Skills構造で提供します。

- entry pointはskills/spec-analysis/SKILL.md
- 詳細規則はreferences/ui-test-target-analysis.md
- package templateはassets/ui-test-target-analysis/
- qa-workflowは必要なSkillへroutingする
- question-analysisは回答正規化とresume情報を返す

AIエージェントは利用環境で提供される通常のSkill読み込み機構に従います。

今回の実装では次を追加しません。

- 特定AI製品向けbootstrap
- GitHub connector固有手順
- remote Skill loader
- 新しいSkill-to-Skill API
- 全19 Skillを一括読み込みするruntime

## 4. README更新

READMEへ変更が必要な場合は、UIテスト対象分析profileがspec-analysisの条件付きprofileであることだけを簡潔に追記します。

特定AI製品の利用手順は追加しません。

## 5. 変更しないもの

- qa-workflowの19 Skill前提
- skill-to-skill API不存在の説明
- question-analysisの分類4種
- test-target-inspectionのlive target currentness契約
- runtime / artifact graph
- qa-knowledge lifecycle
- Regression / Exploration routing
- E2E Skill群

## 6. 完了条件

- profile requestがspec-analysisへrouteされる
- 不明点回答後に同じUNKNOWN lineageでspec-analysisへ戻る
- 仕様理解だけの要求でtest-analysisへ勝手に進まない
- current UI観測要求だけtest-target-inspectionへ分岐する
- profileが既存Agent Skills構造でAIエージェントから利用できる
- 特定AI製品向けintegrationを追加していない
