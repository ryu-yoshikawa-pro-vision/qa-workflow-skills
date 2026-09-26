# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `skills/usability-evaluation/` packageの正本です。

live targetを能動操作する `skills/usability-inspection/` packageは `_05a_usability-inspection-package-and-evaluation.md` に分離します。

usability-evaluationへbrowser runner、task execution、timing measurement runtimeを追加しません。

## 1. 追加するSkill

~~~text
skills/usability-evaluation/
├── SKILL.md
├── references/
│   ├── index.md
│   ├── source-catalog.md
│   ├── source-coverage.md
│   ├── evaluation-method.md
│   ├── evidence-and-authority.md
│   ├── heuristics.md
│   ├── accessibility/
│   ├── patterns/
│   └── platforms/
├── assets/
│   └── output-template.md
├── scripts/
│   └── validate-reference-catalog.py
└── evals/
    ├── trigger/
    │   ├── train_queries.json
    │   └── validation_queries.json
    ├── output/
    │   ├── evals.json
    │   └── cases/
    ├── deterministic/
    │   └── validator.py
    └── semantic/
        ├── rubric.json
        ├── evals.json
        └── cases/
~~~

実装開始時にrepository標準構造がPR #11 / #12 / #13で変わっていれば最新構造へ合わせます。

## 2. SKILL.md

SKILL.mdは詳細なUI pattern知識を抱えません。

必須契約:

1. 実行前に `references/index.md` を読む。
2. root indexから必要な `patterns/index.md` / `accessibility/index.md` / `platforms/index.md` へ進み、対象pattern、cross-cutting concern、platformに必要なreferenceだけを読む。
3. 全referencesを一括で読み込まない。
4. user goal / context / applicabilityを確認してからpattern guidanceを適用する。
5. project Authorityと一般guidanceを分離する。
6. 観測事実と評価を分離する。
7. TCのPASS / FAILを勝手に上書きしない。
8. Product Riskを採点しない。
9. live UIを観測していない場合、その事実を保持する。
10. browser ownerが別Skillの場合は取得済みevidenceを優先し、同一sessionを勝手に操作しない。
11. visual判断が必要な場合は画像証跡を利用する。
12. sourceをUI / UX評価項目から追跡できるようにする。Findingを作成する場合も、元の評価項目・source・evidenceを追跡可能にする。
13. user researchでしか確定できない事項を断定しない。

## 3. trigger

発火対象:

- このDialogをUI pattern / heuristicに照らしてレビュー
- このscreenshot / Figma / specificationのUI / UXをbest practiceと照合
- WAI-ARIA / WCAG / Design Systemに照らして評価
- accessibilityを含むinteraction設計をreference knowledgeから評価
- test analysisでUI / UXリスク候補をpattern / heuristicから洗い出す要求
- test designでUI patternから観点候補が必要な要求
- 取得済みlive UI / screenshot / DOM evidenceをbest practiceと照合する要求

直接発火の非発火対象:

- 単純なTC実行だけ
- Product Risk採点だけ
- current UI inventoryの収集だけ
- Playwright E2E実装だけ
- screenshot pixel diffだけ
- 一般的なデザイン案の創作だけ
- user researchそのもの

ここでのnegativeは「最初のSkillとして直接選択しない」という意味です。`test-execution` / `test-target-inspection` 等の既存evidenceは、UI / UX評価が同じ依頼・案件scope・qa-workflowで明示的に選定された場合にread-only入力として再利用できます。evidenceが存在するだけでは `usability-evaluation` を自動起動しません。

次は `usability-evaluation` / `usability-inspection` のどちらかへ固定せず、boundary queryとして扱います。

- usabilityを確認して
- UIの使いやすさを見て
- 表示崩れやresponsive問題を確認して
- この画面にUX上の問題がないか確認して

live targetを実際に操作する要求なら `usability-inspection`、design artifact / screenshot / 取得済みevidenceをreference knowledgeへ照合する要求なら `usability-evaluation` へroutingします。

境界queryをtrigger evalへ入れます。

## 4. 入力契約

必須入力は利用形態で変わります。

共通で最低限必要:

- evaluation purpose
- target scope
- user / roleまたは不明であること
- user goal / taskまたは不明であること
- platform
- 利用可能なevidence / design artifact

可能なら:

- project Authority
- adopted Design System
- applicable standard
- viewport / device
- locale
- current state
- before / after
- accessibility tree / DOM
- screenshot
- existing Finding / Observation
- related Product Risk / TR / TCN / TC refs

不足値を推測で埋めません。

## 5. 成果物

assets/output-template.mdは最低限次を持ちます。

### 評価条件

- 対象
- user / role
- user goal / task
- platform
- viewport / device
- locale
- state
- evidence refs
- project Authority / adopted Design System
- 評価制約
- 上位観点ごとの今回の扱い: 今回評価する / 対象外
- 対象外理由

### pattern識別

- 対象領域
- pattern
- pattern purpose
- user goalとの関係
- applicability
- source item refs

### UI / UX評価結果

`evaluation ref` は1つのusability-evaluation成果物revision内だけで一意なartifact-local refとします。新しいglobal QA ID / Machine Entityにはしません。

merge後の既存artifact-local ref規則がある場合はそれを使い、ない場合は最終出力の評価行順で `EVAL-001` から採番します。並べ替えによるref維持は要求しません。

評価条件の `user goal / task` を各評価行のdefaultとして継承します。行単位で異なる場合だけ `user goal / task override` を記録します。

各評価行の `適用したreference` は `_02_reference-knowledge.md` §6のreference entry IDと、そのentryに含まれるsource item refを1対1で対応付けて保持します。複数の根拠を使う場合は複数行に分け、`referenceの位置づけ` を1つへ潰しません。

各行:

- evaluation ref
- 上位観点
- target
- user goal / task override（評価条件と異なる場合だけ）
- observed fact
- pattern / principle
- 適用したreference:
  - reference entry ref
  - source item ref
  - referenceの位置づけ
  - project Authority refs（project固有のbinding根拠を使う場合だけ）
- expected characteristic
- difference
- 想定される影響
- 想定される影響の根拠
- 観測済みのユーザー影響（証拠がある場合だけ）
- evidence ref
- status
- status reason / 制約・未確認
- routing
- finding ref（Findingを作成した場合だけ）
- note

`status reason / 制約・未確認` は `判定不能` / `対象外` では必須です。`問題を確認` / `問題なし` では、制約や補足理由を残す必要がある場合だけ記録します。

statusは評価契約の `問題を確認 / 問題なし / 判定不能 / 対象外` を使います。

### Finding

PR #13のFinding契約を再利用し、後続QA活動で扱う必要がある評価項目だけをFindingへ昇格します。`問題なし` / `対象外` にFinding refを付けません。

## 6. package-local ID

`source ID`、`source item ref`、`reference entry ID` はusability-evaluation package内だけの追跡IDとします。PR #11のMachine Entityや全QA共通IDにはしません。

### source ID

- 形式: `SRC-\d{3,}`
- seed / Q1〜Q7でadoptしたsourceは、cross-link root set固定前にcanonical root昇順で `SRC-001` から採番する
- cross-linkで新たにadoptしたsourceはcross-link探索完了後にcanonical root昇順で既存最大番号+1から採番する
- 将来追加するsourceも既存最大番号+1を使う
- 並び順、名称、canonical root変更だけを理由に既存IDを振り直さない
- 削除・duplicate化したIDを別sourceへ再利用しない

### source item ref

- 形式: `<source ID>-ITEM-\d{4,}`
- 初回inventoryでは同一source内をcanonical URL、source item名称の順で並べ、`ITEM-0001` から採番する
- 初回採番後は並べ替え、名称変更、redirectだけを理由にrefを変更しない
- 新規itemは同一source内の既存最大番号+1を使う
- 削除・統合したrefを別itemへ再利用しない

### reference entry ID

- 形式: `REF-\d{4,}`
- 初回作成時は最終reference file path、entry名称の順で並べ、`REF-0001` から採番する
- 初回採番後は並べ替え、名称変更、file移動だけを理由にIDを変更しない
- 新規entryは既存最大番号+1を使う
- 削除・統合したIDを別entryへ再利用しない

reference entry、UI / UX評価項目、Findingの根拠追跡ではsource item refを使い、評価項目ではさらにreference entry IDとの組を保持します。

例:

~~~text
source ID: SRC-001
source item ref: SRC-001-ITEM-0001
reference entry ID: REF-0001
~~~
## 7. reference catalog validator

all-source coverage要件を人手だけに依存させないため、Skill-localの小さいvalidatorを追加します。

確認対象:

- index linkが存在する
- source-catalogのsource IDが `SRC-\d{3,}` 形式で一意かつappend-only規則に従う
- source-catalogのcandidate statusが許可値で、pendingが残っていない
- source-catalogのdiscovery実行記録でQ1〜Q7がそれぞれ1件以上 `completed` へ閉じている
- cross-link root setがseed / query由来adopted sourceのsource ID集合と一致する
- cross-link root set内の各source IDの実行記録が1件以上 `completed` へ閉じ、0件結果も実行済みとして記録できる
- cross-link由来sourceが今回のcross-link root setへ再帰追加されていない
- discovery実行記録に `blocked` が残っていない
- source-coverageのsource IDがcatalogへ存在し、source item refが `<source ID>-ITEM-\d{4,}` 形式でsource-coverage内一意かつappend-only規則に従う
- coverage disposition / access stateが許可値
- source自身がmaturity / lifecycleを明示する場合は値を保持する
- included / merged-duplicate itemにreference destinationがある
- included / merged-duplicate itemで `available_dimensions = captured_dimensions` が成立する
- reference destinationが実在する
- reference entry IDが `REF-\d{4,}` 形式で一意かつappend-only規則に従う
- pattern entryの各source item refがsource-coverageへ解決し、そこからsource IDがsource-catalogへ解決する
- reference entryで各source item refにsource上の位置づけ / 適用条件が対応付いている
- required metadataが欠けていない
- orphan referenceがない
- alias indexが存在しないentryを指さない

validatorはsource本文の意味品質を判定しません。

Webへアクセスしてsourceの最新状態を検査するruntimeにはしません。

## 8. deterministic output validator

評価成果物から機械的に検証できるものだけ扱います。

候補:

- evaluation refが成果物revision内で一意
- evaluation refをglobal QA ID / Machine Entityとして要求しない
- status許可値
- 評価条件で「今回評価する」とした全上位観点が、少なくとも1件の評価結果へ到達している
- 評価条件で「対象外」とした上位観点に理由がある
- 各評価項目に上位観点と1件以上の `適用したreference` がある
- 各 `適用したreference` のreference entry refが実在し、source item refがそのentryに含まれ、referenceの位置づけがある
- 同一評価項目で複数source itemを使う場合もsource itemごとのreferenceの位置づけを別々に保持する
- user goal / task overrideがない評価項目は評価条件のuser goal / taskを継承できる
- 問題を確認した評価項目にobserved fact / source / evidence / 想定影響の根拠がある
- project固有のbinding根拠を適用した `適用したreference` にproject Authority refがある
- finding refがある場合は対応Findingが存在し、PR #13の最低契約を満たす
- 問題なし / 対象外の評価項目にfinding refがない
- source item ref形式と参照先
- evidence ref存在
- 判定不能 / 対象外にstatus reason / 制約・未確認がある
- 観測済みのユーザー影響を出す場合は対応evidenceがある
- TC resultを書き換える欄を持たない
- source item refなしのbest practice断定を拒否

意味上「本当にDialogか」「本当に使いづらいか」はdeterministic validatorで判定しません。

## 9. semantic eval

LLM Judgeで最低限次を評価します。

- user goalとpattern識別の妥当性
- applicability判断
- source選択
- binding / advisoryとapplicabilityを誤って扱っていないか
- observationとinterpretationの分離
- false positive抑制
- accessibility判断の妥当性
- visual evidenceの使い方
- project Authority / applicable standard / platform guidance等の関係をbinding / advisoryとapplicabilityに基づいて正しく扱っているか
- 一般heuristicを仕様FAILへ昇格していないか
- design-stageとlive-stageを混同していないか
- user researchなしでユーザー行動を断定していないか
- routingがowner責務へ戻っているか

## 10. reference semantic eval

通常のSkill出力とは別に、reference自体の品質をfixtureで確認します。

代表的な複合patternを選び、

- indexから必要referenceへ到達できる
- pattern purposeが判断に使える
- when / when notが区別できる
- source conflictを扱える
- accessibility / interaction / visualを横断できる

ことを確認します。

加えて、内容をreferenceへ収録した各adopted sourceについて、少なくとも1件のsource itemを原文と照合します。

spot-check対象は次で固定します。

- `included` / `merged-duplicate` itemがあるsource: source item refの辞書順で最初の対象itemを最低1件
- `unavailable` / `source-reference-only` しかないsource: 内容ではなくdisposition、理由、canonical URL、access stateの妥当性を最低1件
- referencesの `patterns / accessibility / platforms` の各経路について、少なくとも1件は意味内容を原文と照合する

実装上の明確な理由があり別itemをspot-checkへ使う場合は、fixtureへ選定理由を残します。確認しやすいitemだけへ恣意的に差し替えません。

spot-checkでは少なくとも、

- source item refが正しい原文を指す
- source上の位置づけ / 適用条件が原文と整合する
- referenceへ記載したpurpose / when / when not / interaction / accessibility等が原文の意味を歪めていない
- sourceに存在しない意味を補っていない

ことを確認します。

全referenceをLLM Judgeで1件ずつ採点する方式は採用しません。

構造網羅性はdeterministic、意味品質は代表case + adopted sourceごとの最低1件spot-checkで分離します。
## 11. portable Skill

Skill package単独で、

- SKILL.md
- references
- assets
- 必要なSkill-local script

を利用可能にします。

repository rootの独自runtimeを、production利用に必須のreference resolverにはしません。

indexはMarkdownリンクで解決できる構造を基本とします。

## 12. 追加しないもの

- vector DB
- RAG server
- graph DB
- web crawler runtime
- external search API
- browser automation framework
- screenshot diff engine
- design token parser framework
- UX scoring engine
- source recommendation AI
- source間多数決ロジック
