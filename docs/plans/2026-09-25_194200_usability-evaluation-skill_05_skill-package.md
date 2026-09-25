# UIユーザビリティ評価Skill追加Plan

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

- UI / UXレビュー
- usability評価
- accessibilityを含むinteraction評価
- UI patternの妥当性確認
- UIの使いやすさ確認
- 表示崩れ / responsive問題の評価
- test analysisでUI / UXリスクを洗い出す要求
- test designでUI patternから観点候補が必要な要求
- live UI / screenshot / DOMをbest practiceと照合する要求

直接発火の非発火対象:

- 単純なTC実行だけ
- Product Risk採点だけ
- current UI inventoryの収集だけ
- Playwright E2E実装だけ
- screenshot pixel diffだけ
- 一般的なデザイン案の創作だけ
- user researchそのもの

ここでのnegativeは「最初のSkillとして直接選択しない」という意味です。`test-execution` / `test-target-inspection` 等がevidenceを取得した後にworkflow内で `usability-evaluation` を呼ぶことは妨げません。

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

merge後の既存artifact-local ref規則がある場合はそれを使い、ない場合はcanonicalな出力順で `EVAL-001` から採番します。

各行:

- evaluation ref
- 上位観点
- target
- observed fact
- pattern / principle
- referenceの位置づけ
- project Authority refs（project固有のbinding根拠がある場合）
- expected characteristic
- difference
- 想定される影響
- 想定される影響の根拠
- 観測済みのユーザー影響（証拠がある場合だけ）
- source item refs
- evidence ref
- status
- routing
- finding ref（Findingを作成した場合だけ）
- note

statusは評価契約の `問題を確認 / 問題なし / 判定不能 / 対象外` を使います。

### Finding

PR #13のFinding契約を再利用し、後続QA活動で扱う必要がある評価項目だけをFindingへ昇格します。`問題なし` / `対象外` にFinding refを付けません。

## 6. source ID / source item ref

`source ID` と `source item ref` を分離します。

- `source ID`: 情報源単位。例: `W3C-WCAG22`
- `source item ref`: source-coverage上の個別item単位。例: `W3C-WCAG22-2.4.7`

reference entry、UI / UX評価項目、Findingの根拠追跡では原則 `source item ref` を使用します。

例:

~~~text
W3C-WCAG22-2.4.7
W3C-WAIARIA12-DIALOG
W3C-HTMLARIA-BUTTON
W3C-APG-DIALOG
GOVUK-PATTERN-ERROR-RECOVERY
USWDS-COMPONENT-ACCORDION
CARBON-PATTERN-LOADING
NNG-H01
SOCIOMEDIA-...
~~~

実装時に実際のsource inventoryから命名規則を固定します。

URLだけを自由記述して同一source itemが分散しないようにします。

ただし新しい全QA共通ID体系にはしません。usability-evaluation package内のsource参照です。
## 7. reference catalog validator

all-source coverage要件を人手だけに依存させないため、Skill-localの小さいvalidatorを追加します。

確認対象:

- index linkが存在する
- source-catalogのsource IDが一意
- source-catalogのcandidate statusが許可値で、pendingが残っていない
- source-coverageのsource IDがcatalogへ存在し、source item refがsource-coverage内で一意
- coverage disposition / access stateが許可値
- source自身がmaturity / lifecycleを明示する場合は値を保持する
- included / merged-duplicate itemにreference destinationがある
- included / merged-duplicate itemで `available_dimensions = captured_dimensions` が成立する
- reference destinationが実在する
- pattern entryのsource item refがsource-coverageへ解決し、そこからsource IDがsource-catalogへ解決する
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
- 各評価項目に上位観点とreferenceの位置づけがある
- 問題を確認した評価項目にobserved fact / source / evidence / 想定影響の根拠がある
- project固有のbinding根拠を適用した評価項目にproject Authority refがある
- finding refがある場合は対応Findingが存在し、PR #13の最低契約を満たす
- 問題なし / 対象外の評価項目にfinding refがない
- source item ref形式と参照先
- evidence ref存在
- 判定不能に制約理由がある
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
- project Authorityとの優先順位
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
