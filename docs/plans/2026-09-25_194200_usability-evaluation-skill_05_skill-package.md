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
│   ├── reference_catalog.py
│   ├── evaluation_structure.py
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
4. target purpose / context / applicabilityを確認してからpattern guidanceを適用する。user goal / taskは存在する場合だけ利用し、存在しない場合に創作しない。
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

共通で必須:

- evaluation purpose
- target scope
- platform
- 利用可能なevidence / design artifact

user / role、user goal / task / flow、特定の利用者条件は、入力・仕様・evidenceに存在する場合だけ利用します。存在しないことだけで評価を停止せず、不足値を創作しません。

contextに存在する場合:

- project Authority
- adopted Design System
- applicable standard
- viewport / device
- locale
- current state
- before / after
- accessibility tree / DOM
- screenshot
- usability-inspectionのobjective observation refs / test rule result refs / requirement check refs / measurement refs（存在する場合）
- existing Finding / Observation
- related Product Risk / TR / TCN / TC refs

不足値を推測で埋めません。

## 5. 成果物

assets/output-template.mdは次を必須fieldとして持ちます。

### 評価条件

- 対象
- platform
- viewport / device
- locale
- state
- evidence refs
- project Authority / adopted Design System
- 評価制約
- user / role（存在する場合）
- user goal / task / flow（存在する場合）
- 上位観点ごとの今回の扱い: 今回評価する / 対象外
- 対象外理由

### pattern識別

- 対象領域
- pattern
- pattern purpose
- target purpose / user goalとの関係（user goalがある場合）
- applicability
- source item refs

### UI / UX評価結果

`evaluation ref` は1つのusability-evaluation成果物revision内だけで一意なartifact-local refとします。新しいglobal QA ID / Machine Entityにはしません。

merge後の既存artifact-local ref規則がある場合はそれを使います。ない場合はsemantic layerが確定したevaluation draft順を `evaluation_structure.py` が保持し、`EVAL-001` から決定論的に採番します。Agentがfinal refを手採番しません。別revisionでのstable identity維持は要求しません。

評価条件に `user goal / task / flow` が存在する場合だけ各評価行のdefaultとして継承します。行単位で異なる場合だけoverrideを記録します。存在しない場合は必須にしません。

各評価行の `適用したreference` は `_02_reference-knowledge.md` §6のreference entry IDと、そのentryに含まれるsource item refを1対1で対応付けて保持します。複数の根拠を使う場合は複数行に分け、`referenceの位置づけ` を1つへ潰しません。

各行:

- evaluation ref
- 上位観点
- target
- user goal / task / flow override（評価条件と異なる場合だけ。評価条件に存在しない場合は省略）
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
- related test rule result refs（存在する場合）
- related requirement check refs（存在する場合）
- related measurement refs（存在する場合）
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

`source ID`、`source item ref`、`reference entry ID` はusability-evaluation package内だけの追跡IDとします。PR #11のMachine Entityや全QA共通IDにはしません。これらはsource-coverage、reference entry、後続の評価成果物がfile移動や名称変更をまたいで同じsource / item / entryを参照するためのpackage-local provenance keyです。

### source ID

- 形式: `SRC-\d{3,}`
- 初回実装では採用・reference-onlyとして追跡するsourceをcanonical URL昇順で `SRC-001` から採番する
- 追加sourceは既存最大番号+1を使う
- 並び順、名称、canonical URL変更だけを理由に既存IDを振り直さない
- 削除・duplicate化したIDを別sourceへ再利用しない

### source item ref

- 形式: `<source ID>-ITEM-\d{4,}`
- normalized referenceへ実際に使うpage / sectionへだけ付与する
- 初回採番では同一source内をdocument canonical URL、locator type、locator、source item名称の順で並べ、`ITEM-0001` から採番する
- 追加itemは既存最大番号+1を使う
- 名称変更、redirectだけを理由にrefを変更しない
- 削除・統合したrefを別itemへ再利用しない

### reference entry ID

- 形式: `REF-\d{4,}`
- 初回作成時は最終reference file path、entry名称の順で `REF-0001` から採番する
- 追加entryは既存最大番号+1を使う
- 並べ替え、名称変更、file移動だけを理由にIDを変更しない
- 削除・統合したIDを別entryへ再利用しない

source ID / source item ref / reference entry IDはAgentが手計算しません。`reference_catalog.py` が既存catalogと候補入力から決定論的に採番します。

reference entry、UI / UX評価項目、Findingの根拠追跡ではsource item refを使い、評価項目ではさらにreference entry IDとの組を保持します。

例:

~~~text
source ID: SRC-001
source item ref: SRC-001-ITEM-0001
reference entry ID: REF-0001
~~~
## 7. reference catalog production script / validator

### reference_catalog.py

Agentへ手計算させない処理をproduction scriptへ移します。

scriptはrepository fileを直接writeする必要はありませんが、machine-owned fieldをcanonical JSONだけで返してAgentに値単位で転記させる構造にはしません。semantic layerはsource採用理由、dimension、merge / split等の意味判断だけをnormalized decision inputとして渡し、scriptがID、enum、sort、cross-reference、table rowを含むcanonical Markdown section / file contentをmaterializeします。Agentは返却されたmachine-owned contentを値単位で再構築せず、既存の安全な保存経路でそのまま保存します。

CLIは次のsubcommandに固定します。

#### normalize-url

Input:

- `--url <confirmed-canonical-url>`

Function:

- URL syntax検証
- scheme / hostのcase正規化
- default port等、URL identityを変えないsyntax正規化
- fragment付きURLをreject

source / document canonical URLとdocument内locatorを分離するため、fragmentを黙って除去しません。source itemは `_02d_reference-artifact-schema.md` の `Document Canonical URL + Locator Type + Locator` で保持します。

redirect追跡、official canonicalの意味判断、tracking parameter除去は行いません。Agent / research工程が公式sourceを確認してcanonical URLを入力します。

Output:

~~~json
{"canonical_url":"https://example.com/path"}
~~~

#### next-source-id

Input:

- `--catalog references/source-catalog.md`

Function:

- existing `SRC-\d{3,}` を全件読取
- duplicate / malformed IDを拒否
- 既存最大番号+1を採番

Output:

~~~json
{"source_id":"SRC-014"}
~~~

#### next-item-ref

Input:

- `--coverage references/source-coverage.md`
- `--source-id SRC-014`

Function:

- 同一sourceのexisting item refを全件読取
- duplicate / malformed refを拒否
- 既存最大番号+1を採番

Output:

~~~json
{"source_item_ref":"SRC-014-ITEM-0003"}
~~~

#### next-reference-id

Input:

- `--references-dir references`

Function:

- reference entry IDをreferences配下から全件読取
- duplicate / malformed IDを拒否
- 既存最大番号+1を採番

Output:

~~~json
{"reference_entry_id":"REF-0042"}
~~~

#### materialize

production artifact生成では `next-source-id` / `next-item-ref` / `next-reference-id` の結果をAgentが個別に貼り付けません。`materialize` が既存artifactとsemantic decision inputを受け、必要なIDを内部採番して次をcanonicalにrenderします。

- `references/source-catalog.md` のmachine-owned table
- `references/source-coverage.md` のCapability Coverage / Source Items table
- leaf reference entryのID marker / Source Items table

自然言語の要約本文はsemantic inputとして受け取れますが、ID、enum、row順序、locator分離、cross-reference、summary countはscript ownerです。

Output:

- target path
- rendered content
- allocated IDs / refs
- issues

#### summary

Input:

- `--catalog references/source-catalog.md`
- `--coverage references/source-coverage.md`
- `--references-dir references`

Function:

- pending / blocked件数集計
- capability coverage status集計
- source / item / reference件数集計
- duplicate ID / unresolved cross-reference検出
- deterministic sortしたsummary生成

Output:

~~~json
{
  "pending_candidates": 0,
  "blocked_coverage": 0,
  "source_count": 0,
  "source_item_count": 0,
  "reference_entry_count": 0,
  "issues": []
}
~~~

全subcommand:

- 成功時exit 0
- input / schema / duplicate / unresolved reference error時はnon-zero
- stdoutは1つのJSON objectだけ
- diagnosticはstderr
- locale / 実行順に依存しない
- network accessしない

source採用、dimension抽出、merge / split、source position、projectへのbinding等の意味判断は行いません。

### evaluation_structure.py

semantic layerが決めた評価内容からmachine処理だけを担当します。

Input:

- evaluation conditionのsemantic field
- top-level aspect decisions: aspect key / 今回評価する・対象外 / semantic reason
- pattern identification decisions
- evaluation decisions。status、observed fact、semantic impact、applied reference decision、follow_up_required等、意味判断でしか確定できないfield
- evidence / requirement / test rule / measurement refs
- Finding本文に必要なsemantic input（Findingを作る場合）

各semantic decisionはinvocation内一意の `draft_key` を持ちます。Agentはfinal evaluation ref、完成したclosure row、summary count、`finding_required` を入力しません。

Function:

- unknown field / enum / required field検証
- Planで固定したtop-level aspectのrow skeletonを全件生成し、semantic decisionを適用
- evaluation decision順を保持
- `EVAL-001` からartifact-local refを決定論的に採番
- draft key → final ref解決
- applied reference / evidence / related test rule / requirement / measurement cross-reference解決
- statusと `follow_up_required` からFinding作成要否を固定ruleで導出し、必要な場合だけFinding draft / refとのclosureを要求
- top-level aspect closure検証
- row order固定
- summary count生成
- machine-owned structured sectionをcanonical Markdownとしてrender

意味判断は行いません。

Output:

- normalized evaluation condition
- pattern identification rows
- evaluation rows
- Finding requirement / refs
- summary
- rendered machine-owned structured sections
- issues

同じnormalized inputから同じmachine outputになることをfixtureで検証します。

### validate-reference-catalog.py

production generatorとは別実装で検証します。

確認対象:

- index linkが存在する
- `_02c_seed-source-catalog.md` のseed確認結果がcatalogにある
- `_02d_reference-artifact-schema.md` の必須heading / table column / empty / list / escaping規則を満たす
- source-catalogにcanonical URLがある
- source IDが `SRC-\d{3,}` 形式で一意かつappend-only規則に従う
- candidate statusが許可値でpendingが残っていない
- Q1〜Q7とcoverage gapから追加したqueryがcompleted
- queryごとにretrieval boundaryが記録されている
- capability coverageの全rowがcovered / not-applicable / blockedへ閉じ、blockedが0
- source item refが `<source ID>-ITEM-\d{4,}` 形式で一意
- source itemのDocument Canonical URLにfragmentがなく、Locator Type / Locatorが整合する
- included / merged-duplicate itemにreference destinationがある
- included / merged-duplicate itemで `available_dimensions = captured_dimensions`
- semantic validation recordがありfailが0
- reference entry IDが `REF-\d{4,}` 形式で一意
- source / item / referenceのcross-referenceが解決する
- source position / platform / status / access state等のrequired metadataがある
- orphan referenceがない
- alias indexが存在しないentryを指さない

validatorはsource本文の意味品質を判定しません。

Webへアクセスしてsourceの最新状態を検査するruntimeにもせず、実装時のsource再確認はAgent / research工程が担当します。

## 8. deterministic output validator

評価成果物から機械的に検証できるものだけ扱います。

検証項目:

- evaluation refが `evaluation_structure.py` により成果物revision内で一意に採番されている
- evaluation refをglobal QA ID / Machine Entityとして要求しない
- status許可値
- 評価条件で「今回評価する」とした全上位観点が、少なくとも1件の評価結果へ到達している
- 評価条件で「対象外」とした上位観点に理由がある
- 各評価項目に上位観点と1件以上の `適用したreference` がある
- 各 `適用したreference` のreference entry refが実在し、source item refがそのentryに含まれ、referenceの位置づけがある
- 同一評価項目で複数source itemを使う場合もsource itemごとのreferenceの位置づけを別々に保持する
- 評価条件にuser goal / task / flowが存在する場合だけ、overrideがない評価項目はその値を継承できる
- 問題を確認した評価項目にobserved fact / source / evidence / 想定影響の根拠がある
- project固有のbinding根拠を適用した `適用したreference` にproject Authority refがある
- `follow_up_required` とstatusから導出したFinding作成要否が成果物と一致する
- finding refが必要な場合は対応Findingが存在し、PR #13の最低契約を満たす
- 問題なし / 対象外の評価項目にfinding refがない
- source item ref形式と参照先
- evidence ref存在
- related test rule / requirement check / measurement refsがある場合は参照先が実在する
- strict requirement resultを参照する評価項目が、そのresultをadvisory評価で上書きしていない
- 判定不能 / 対象外にstatus reason / 制約・未確認がある
- 観測済みのユーザー影響を出す場合は対応evidenceがある
- TC resultを書き換える欄を持たない
- source item refなしのbest practice断定を拒否

意味上「本当にDialogか」「本当に使いづらいか」「follow-upが必要か」はdeterministic validatorで判定しません。semantic layerが返した最小decisionを前提に、固定row、ID、Finding要否、cross-reference、summary、machine-owned renderingだけを機械検証します。production `evaluation_structure.py` とdeterministic validatorは別実装とし、同じ処理を互いにimportしません。

## 9. semantic eval

LLM Judgeで次をすべて評価します。

- target purpose / contextとpattern識別の妥当性
- user goal / task / flowが存在する場合はそのcontextとの整合
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

reference semantic evalは `_02b_reference-validation-and-completeness.md` の全included item検証を実施します。

- normalized corpusへ `included / merged-duplicate` とした全source itemを原文と照合する
- `reference-only / unavailable` はcatalog / itemとして保持したmetadata、理由、canonical URL、access stateを確認する
- referencesの `patterns / accessibility / platforms` の各経路についてindex解決を検証する
- source conflict / merge / split / aliasのfixtureを検証する
- capability coverageの各axisからreferenceへ到達できることを確認する

normalized corpusへ採用したitemについてsamplingは使いません。catalogへ載せただけのsource全pageをsemantic validation対象にはしません。

各itemの照合では少なくとも、

- source item refが正しい原文を指す
- source上の位置づけ / 適用条件が原文と整合する
- referenceへ記載したpurpose / when / when not / interaction / accessibility等が原文の意味を歪めていない
- sourceに存在しない意味を補っていない

ことを確認します。

全itemを同じLLM点数へ変換する方式は採用しません。構造網羅性はdeterministic validator、source原文との意味一致は全item semantic validation、Skillの判断品質はsemantic eval caseで分離して検証します。
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
