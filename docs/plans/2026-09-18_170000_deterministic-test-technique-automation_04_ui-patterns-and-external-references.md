# テスト分析・テスト技法の決定論的自動化Plan

## 1. UIパターンをテスト条件へ利用する方針

UI要素の種類から、一般的に確認すべき候補を機械的に引けるようにします。

ただし、一般的なUIパターンや外部標準を、対象製品の仕様より強い根拠として扱いません。

優先順は次です。

1. 対象製品の現在有効な仕様根拠
2. 対象platform / native controlが規定する挙動
3. 製品が採用すると明示した外部標準・design system
4. 一般的な確認候補

4はテスト観点の候補を増やすために使い、製品固有の期待結果を確定する根拠にはしません。

例えばDialogについて一般的なkeyboard / focus確認候補が存在しても、対象製品の仕様がESC操作を持たない場合に「ESCで閉じる」を期待結果として追加しません。

## 2. 追加するファイル

```text
skills/test-condition-design/
├── references/
│   └── ui-patterns.md
├── assets/
│   └── ui-pattern-catalog.json
└── scripts/
    └── ui_pattern_candidates.py
```

### `ui-pattern-catalog.json`

機械参照する正本です。generatorはcatalog file contentのSHA-256を`static_data_versions.ui_pattern_catalog`として出力し、成果物へ保持します。catalog変更後は旧versionで生成したUI候補をstaleとして再検証します。

各patternは最低限、次を持ちます。

- 正規pattern名
- alias
- 対応するHTML要素 / ARIA role等の識別候補
- 一般的な確認候補
- keyboard / focus候補
- state / value候補
- `reference_refs`として扱う外部資料URLと確認日 / revision
- 製品仕様なしでは期待結果へ昇格させない項目

### `references/ui-patterns.md`

次だけを説明します。

- catalogの使い方
- 一般候補と製品固有期待結果の違い
- 外部標準の位置付け
- 対象要素を誤分類した場合の扱い
- catalog自体を実行中に変更しないこと。catalogにないUIでも、現在有効な仕様根拠から通常のテスト設計は継続できること

catalogとreferenceで同じ一覧を二重管理しません。

## 3. catalog対象

UIで一般的に出現し、確認項目の再利用価値が高いものを対象にします。

| UI要素 / pattern | 機械的に提示できる主な確認候補 |
| --- | --- |
| Button | enabled / disabled、pointer操作、keyboard activation、focus、二重操作、loading中の状態 |
| Link | 遷移先、keyboard activation、focus、外部 / 内部遷移、disabled相当表現がある場合の扱い |
| Text Input | required、空、文字数境界、入力可能文字、readonly / disabled、clear、paste、validation |
| Textarea | Text Input共通、複数行、改行、max length、resize要件がある場合 |
| Number Input / Spinbutton | min / max / step、直接入力、増減操作、非数値、decimal |
| Password | required、長さ・形式、mask表示、表示切替が仕様にある場合、paste可否が仕様にある場合 |
| Checkbox | checked / unchecked、keyboard、disabled、group制約、初期状態 |
| Radio Group | 単一選択、初期選択、keyboard移動、disabled option、必須選択 |
| Switch / Toggle | on / off、keyboard、disabled、labelとの対応 |
| Select | option一覧、選択、初期値、disabled option、keyboard、未選択 |
| Combobox / Autocomplete | 入力、候補表示、絞り込み、候補選択、keyboard、focus、no-result、clear |
| Listbox | option移動、単一 / 複数選択、keyboard、selected state |
| Slider | min / max / step、keyboard、pointer、表示値、disabled |
| Date / Time Picker | min / max、禁止日、直接入力、picker選択、timezone要件がある場合 |
| File Upload | 許可形式、サイズ境界、複数選択、取消、同一ファイル再選択、失敗時 |
| Dialog / Modal | open / close経路、focus初期位置、focus移動、background操作、confirm / cancel、close control |
| Alert / Toast / Notification | 表示条件、内容、表示回数、消滅条件、操作可能な場合のfocus |
| Tabs | selected tab、panel対応、keyboard候補、disabled tab |
| Accordion / Disclosure | open / close、複数開閉可否、keyboard、state |
| Menu / Menu Button | open / close、項目選択、keyboard、focus return |
| Tooltip | 表示trigger、非表示条件、内容、pointer / keyboardでの到達性 |
| Table | column / row表示、empty state、overflow、headerとの対応 |
| Grid / Data Grid | focus移動、selection、sort / editがある場合、virtualizationがある場合 |
| Pagination | first / last、前後、current page、件数変動、境界page |
| Search | 空検索、完全 / 部分一致等の仕様、clear、0件、特殊文字候補 |
| Filter | 各値、複数条件、clear、初期値、結果件数、URL / state保持が仕様にある場合 |
| Sort | 各列、昇順 / 降順、同値時、他sortとの独立性、初期順 |
| Drag and Drop | drag可否、drop target、順序、取消、境界、keyboard代替が要件にある場合 |
| Tree / Tree View | expand / collapse、selection、keyboard、階層、leaf |
| Progress / Status | 初期 / 進行中 / 完了 / 失敗、値範囲、重複表示 |
| Breadcrumb / Navigation | current、階層、遷移、keyboard、折返し |
| Form | submit、validation順序、複数field相関、reset、二重submit、エラー後再送信 |

catalogは「よくある挙動一覧」ではなく「確認候補一覧」とします。

catalog validationでは、正規pattern名の一意性、aliasの一意性、aliasと別patternの正規名との衝突がないことを確認します。

## 4. UI属性からの機械展開

LLMまたは対象調査で次が取得できる場合、技法へ接続します。

例:

```json
{
  "pattern": "text-input",
  "attributes": {
    "required": true,
    "minlength": 3,
    "maxlength": 20
  }
}
```

この場合:

- `required` → 空 / 非空partition候補
- `minlength`、`maxlength` → BVA入力
- pattern catalog → readonly / disabled / focus等の確認候補

HTML constraintをBVA / partitionへ渡す前に、そのcontrolがconstraint validation対象かを確認します。`disabled`、`readonly`、control type等によりvalidation対象外の場合、属性が存在するだけでinvalid候補を生成しません。

DOM属性と仕様書が矛盾する場合、DOMを正として期待結果を決めません。既存の`spec-analysis` / `question-analysis`のルールへ戻します。

## 5. 外部標準

### ISTQBのテスト技法

自動化対象の一覧化に使う基準集合として、次を参照します。

- CTFL v4.0.1: https://www.istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf
- CTAL-TA v4.0: https://istqb.org/wp-content/uploads/sdm-uploads/ISTQB-CTAL-TA-Syllabus-v4.0-EN-4.pdf
- CTAL-TTA v4.0: https://www.istqb.org/wp-content/uploads/2024/11/ISTQB-CTAL-TTA_Syllabus_v4.0.pdf

CTAL-TA v4.0で扱われるDomain Testing、Base Choice / Pairwise等のCombinatorial Testing、Random Testing、CRUD Testing、N-switch、Round-trip Coverage、Metamorphic Testing等を一覧化の確認に使います。

技法契約では、CTAL-TA v4.0の次の点を反映します。

- Domain TestingはReliable Domain Coverageを採用する。`< / <= / > / >=`ではON / OFF / IN / OUT、`=`ではON + 両側OFF、`!=`ではOFF + 両側ONをCoverage Itemとする
- CRUD Testingはcompleteness testingとconsistency testingの両方を扱う。completenessはmatrix operation、consistencyはentity lifecycleとAuthorityで明示されたnegative sequenceを対象にする
- Random Testingには一般に認められたCoverage基準がなく、件数・時間等の終了条件で扱う。本Planの決定論的runtimeでは件数へ正規化された終了条件だけを機械判定する
- Metamorphic Testingにも有用な一般Coverage measureを設定せず、MRを1回扱っただけで十分としない

これらは網羅性確認と技法契約の確認に使います。既存技法のCoverage modeとして表現できるものは既存名を再利用し、Domain Testing、CRUD Testing、Random Testing、Metamorphic Testing、Syntax-Based Testingのように独立したproblem model / selection reason / Coverageまたは終了条件の契約を持つものは、本Planで正規技法名・Skill契約・成果物契約・評価まで追加します。

### Syntax-Based Testingの参照

参照先:

- Paul Ammann / Jeff Offutt, *Introduction to Software Testing*, Chapter 5 "Syntax-Based Testing": https://www.cambridge.org/core/services/aop-cambridge-core/content/view/43BC474F5271ECA36F789D65F5243055/9780511809163c5_p170-212_CBO.pdf/syntaxbased_testing.pdf

本Planの`Syntax-Based Testing`は、grammar / BNF等のsyntactic descriptionをmodelとしてvalid artifactを生成し、production Coverageを確認する考え方を根拠にします。mutationで作ったcandidateを製品上のinvalid expected resultへ自動昇格しません。
### WAI-ARIA Authoring Practices Guide

参照先:

- https://www.w3.org/WAI/ARIA/apg/patterns/

Button、Checkbox、Combobox、Dialog、Radio Group、Slider、Tabs、Menu等のpatternについて、keyboard interaction、role、state、focus等の確認候補に利用します。

APGの例示や推奨を対象製品の仕様へ無条件に昇格しません。APG等のURLは`reference_refs`であり、Coverage Itemの製品固有expected resultに必要な`authority_refs`とは区別します。

### HTML Standard

参照先:

- https://html.spec.whatwg.org/

native HTML controlの属性、constraint validation、form control、button、select等について、platform semanticsを確認する一次資料として使用します。参照したLiving StandardのURLと確認日をcatalogの`reference_refs`へ残します。

### WCAG / WAI資料

アクセシビリティ要件が対象scopeに含まれる場合だけ利用します。すべてのテスト条件へ自動で大量追加する使い方はしません。

## 6. 既存プロジェクト・Agent Skillsの調査結果

### Agent Skills Specification

このリポジトリが`validate-skills.yml`でpinしているAgent Skills仕様を正本として確認します。

仕様上、Skill packageの`scripts/`は任意の実行可能リソースで、実際に対応するscript言語はAgent実装に依存します。また環境要件はfrontmatterの`compatibility`へ記載できます。

このためPython runtime scriptを追加するSkillにはPython 3.11要件を`compatibility`へ明記し、Skill単体移植性を「ファイルをコピーできること」だけでなく「必要runtimeが明示されていること」まで含めて検証します。

### Microsoft PICT

- Repository: https://github.com/microsoft/pict
- 有限parameter / valueとconstraintからPairwise等の組合せを生成する
- CLI / APIを持つ
- Pairwise / combinatorial testingの実装参考として有用

採用判断:

本PlanのPairwise / N-wise / mixed-strength契約はPython実装で満たすため、PICTを必須依存にはしません。契約どおりの正確性を満たせない、または代表runtime fixtureがGitHub ActionsのUbuntu runnerで30秒timeoutを継続して超えることを確認した場合だけ、その場で別実装へ迂回せずPlanを更新して依存追加を判断します。

### NIST ACTS

- NIST Automated Combinatorial Testing for Software
- t-way covering array、constraint、coverage measurementの考え方を持つ
- 2-wayより高いinteraction strengthの参考になる

参照先:

- https://csrc.nist.gov/projects/automated-combinatorial-testing-for-software

採用判断:

アルゴリズム・評価観点の参考にします。本Planではruntime dependencyにしません。

### GraphWalker

- Repository: https://github.com/GraphWalker/graphwalker-project
- Model-Based Testingでgraphからpath / coverageを生成する既存プロジェクト

採用判断:

状態遷移Coverageとpath生成の参考にします。本Planのstate / transition / n-switch / Round-trip / fork-join CoverageはSkill内scriptで実装し、GraphWalker runtimeは依存に追加しません。

### Z3

- Repository: https://github.com/Z3Prover/z3
- SAT / SMTにより複雑な制約充足、矛盾、到達可能性等を扱える

採用判断:

本Planのconstraintは`_02` / `_03`で定義した有限domainとDomain Testingの明示式へ限定するため、Z3は依存に追加しません。対応契約を将来用に広げるadapterも作りません。

### `jovd83/test-design-orchestrator`

- Repository: https://github.com/jovd83/test-design-orchestrator
- BVA、Equivalence Partitioning、Decision Table、Classification Tree / N-Wise、State Transition等をtechnique別Skillへ分けている
- technique selectionと成果物構造の参考になる

確認した範囲では、技法の生成そのものは主にSkill instructionでLLMへ実行させており、BVA / Decision Table / N-wise等をすべて決定論的scriptへ移した構造ではありません。

本リポジトリではSkill数を増やさず、現在の責務分界どおり`test-condition-design`配下のscriptへ置きます。

### `jovd83/test-analysis-skill`

- Repository: https://github.com/jovd83/test-analysis-skill
- リスクscore計算を`scripts/calculate_risk.py`へ分離している

「意味判断はLLM、数値計算はscript」という実装例として参考にします。

### `omkamal/pypict-claude-skill`

- Repository: https://github.com/omkamal/pypict-claude-skill
- PICT / pypictをAgent Skillから利用する例

外部Pairwise engineをSkillから呼ぶ実装例として参考にしますが、本リポジトリの必須依存にはしません。

## 7. UI候補の適用深度

`ui_pattern_candidates.py`は、現在のテスト要求・選択技法・Coverage基準に関係するpatternの候補を返すために使います。

現行`test-condition-design`のリスク深度契約を維持し、低リスクという理由で対象内の仕様候補を消さない一方、低リスク領域へcatalogの一般edge caseを無条件に全展開しません。候補の採否と深度は既存Skillが判断します。

## 8. 外部依存の方針

本Planで定義した処理はPython 3.11標準ライブラリで実装する前提とします。ただし、標準ライブラリに固執して正確性・保守性を落とすことは目的ではありません。

実装中に、Planで固定した入力契約・Coverage要件を満たせない、または代表runtime fixtureがGitHub ActionsのUbuntu runnerで30秒timeoutを継続して超えることを確認した場合は、実装者が独自判断で簡略化や別アルゴリズムへ切り替えず、次を確認した上でPlanを更新します。

- 既存依存または成熟した外部依存で正しく満たせるか
- Skill単体移植性への影響
- Windows / macOS / Linuxでの利用方法
- licenseと保守状況
- 自前実装より保守しやすいか

将来用のPICT / GraphWalker / Z3 adapter、plugin機構は作りません。

外部資料の文章・表・コード等をcatalogへ転載・改変して同梱する場合はlicenseと帰属条件を確認します。URLと独自記述の確認候補だけを保持する場合は転載と同一には扱いません。
