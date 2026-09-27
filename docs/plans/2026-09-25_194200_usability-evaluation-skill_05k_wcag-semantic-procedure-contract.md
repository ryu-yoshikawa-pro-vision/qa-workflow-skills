# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `s-wcag-<criterion-ref>` のcriterion固有semantic契約を固定します。目的は、実装時またはruntime時にLLMが「このSuccess Criterionで何を意味判断するか」を再設計しないようにすることです。

一方、LLMがevidence間の関係、目的、意味、equivalence、例外の成立、判断理由、uncertaintyを柔軟に評価する責務は維持します。semantic contractは自然言語rule engineや回答テンプレートではありません。

## 1. 正本とasset

`skills/wcag-conformance-evaluation/assets/wcag-semantic-contracts.json` を追加します。

supported target versionごとに、そのversionに存在する全Success Criterionへ1件のcontract rowを持ちます。

- WCAG 2.0: 61 rows
- WCAG 2.1: 78 rows
- WCAG 2.2: 86 rows。4.1.1 rowは存在しない

同じcriterion refでもversionごとに別rowとします。normative wording、definition、exception、conformance noteの差を別versionへ暗黙継承しません。

## 2. contract row

各rowは次を持ちます。

- `semantic_contract_key`: `s-wcag-<criterion-ref>@<version>`
- `criterion_ref`
- `target_wcag_version`
- `level`
- `normative_source_item_refs`
- `normative_clause_refs`
- `definition_refs`
- `exception_refs`
- `semantic_evaluation_points`
- `required_evidence_roles`
- `allowed_additional_observation_fields`
- `forbidden_shortcuts`
- `missing_evidence_behavior`

`normative_clause_refs` はSuccess Criterion本文の意味上独立した要求、例外、conditionへ一意に戻れるsource item locatorです。単にSuccess Criterion全体のURLだけを持って「実装時に本文を読んで分解する」構造にしません。

`semantic_evaluation_points` は次のfieldだけを持つ有限rowです。

- `point_key`
- `source_clause_refs`
- `decision_kind`: `applicability / exception / purpose / meaning / equivalence / relationship / sequence / instruction-feedback / accessibility-support / other-normative-semantic`
- `required_evidence_roles`
- `completion_required`: boolean

`other-normative-semantic` は自由なcatch-allではありません。W3C本文上の意味判断が上記kindへ自然に分類できない場合だけ使用し、`source_clause_refs` を必須にします。実装時にsource clauseなしで独自観点を追加しません。

## 3. required evidence role

evidence roleはprocedure catalogから決定論的に導出できるものを優先し、semantic contractがsibling procedureを省略する経路を作りません。

許可role:

- `population-completeness`
- `machine-procedure-result`
- `manual-procedure-result`
- `assistive-technology-result`
- `external-evidence-result`
- `current-browser-observation`
- `visual-evidence`
- `process-context`
- `presentation-variation`
- `accessibility-support-baseline`
- `technology-context`
- `authority-context`

`wcag_criterion_plan.py` はcriterionのprocedure keysとsemantic contractを突合し、required procedure resultに対応するevidence roleをmaterializeします。LLMがrequired evidence role集合を完成集合として入力しません。

## 4. semantic procedure Input / Output

Input:

- semantic contract row
- sample / variation / process refs
- current population result
- sibling machine / manual / AT / external procedure result refs
- current evidence refs
- accessibility support baseline
- technology context
- project Authority / Step 1.4 additional requirement refs（applicableな場合）

Output:

- `applicability`: `applicable / not-applicable / unknown`
- `evaluation_point_decisions[]`: point key、`satisfied / not-satisfied / undetermined / not-applicable`、reason、evidence refs
- exception decision / source clause refs
- overall semantic decision: `satisfied / not-satisfied / undetermined`
- judgment reason
- evidence refs
- uncertainty / limitation
- additional observation draft（必要な場合）

scriptはoverall decision本文を生成しません。validatorはrequired point coverage、enum、source / evidence refs、procedure closureとの整合だけを検証します。

## 5. LLMへ残す判断

LLMは次を判断できます。

- criterionがcurrent contentへ意味的に適用されるか
- normative exceptionが現在のevidenceで成立するか
- text / image / control / relationship / sequence / feedback等のpurposeや意味
- alternativeが同等の情報・機能・結果を提供するか
- machine / manual / AT evidenceをcriterion全体へどう適用するか
- conflicting evidenceや不確実性
- fixed evidenceだけで閉じない場合に追加観測が必要か

LLMは次を変更しません。

- required criterion集合
- procedure key集合
- semantic evaluation point集合
- required machine probe集合
- source clause
- required evidence role
- completion status / summary count

## 6. 追加観測

追加観測が必要な場合、semantic procedureは `_05g` の16 canonical observation fieldとfixed predicateから表現できるdraftだけを返します。

- existing fieldで取得可能 → observation requestへmaterialize
- same request identity + same evidence fingerprint → `no-progress`
- fixed observation contractで表現不能 → ad hoc probeを作らず `undetermined / blocked`

追加観測によってcriterion / procedure / semantic evaluation point集合を増減しません。取得したnew evidenceで同じsemantic procedureを再評価します。

## 7. 4.1.1特別契約

WCAG 2.2には4.1.1 rowを作りません。

WCAG 2.0 / 2.1では `m-parsing-version-rule` を先に実行します。

- content technologyがHTMLまたはXML → W3C current conformance noteに従い `always-satisfied-html-xml`。`s-wcag-4.1.1` のsemantic実行を不要としてscriptがclosureする
- HTML / XML以外 → `evaluate-normative-rule`。versioned `s-wcag-4.1.1` contractを通常実行する
- technology不明 → shortcutせず `undetermined / blocked`

project独自のHTML validity / parsing quality gateが存在しても、WCAG 4.1.1 conformance resultとは別Authority / requirementとして扱います。

## 8. asset作成契約

実装時はW3C正本から各version / Success Criterionを全件確認し、rowを生成・レビューします。

1. normative Success Criterion本文をsource item化する
2. requirementの意味上独立したclause / exception / conditionへlocatorを付ける
3. meaning judgmentが必要なclauseだけsemantic evaluation pointへする
4. 数値、集合、fixed state / attribute comparison等はmachine procedureへ残し、semantic pointへ重複させない
5. procedure catalogからrequired evidence roleを照合する
6. shortcut禁止条件を明記する
7. source原文とのsemantic validationを全row実施する
8. canonical JSON hashを `static_data_versions.wcag_semantic_contracts` へ固定する

「86件あるため一部だけ先に実装する」は許可しません。supported versionの全rowを同じ実装範囲で閉じます。

## 9. forbidden shortcuts

少なくとも次を全row共通で禁止します。

- 単一ACT Rule PASSだけでSuccess Criterion全体を `satisfied` にする
- 単一element 0件だけでapplicable population `none` にする
- machine procedure一部PASSだけでsemantic requirementを閉じる
- screenshotなしでvisual meaningを観測済みとする
- required manual / AT / external evidenceをLLM推測で補う
- exceptionを根拠なしで適用する
- neighboring Success Criterionの判断をそのまま流用する
- version違いのnormative wordingを暗黙利用する

criterion固有で追加の禁止shortcutがある場合はrowへ固定します。

## 10. deterministic validator

validatorは次を独立確認します。

- version別criterion集合とsemantic contract row集合の差分0
- duplicate contract key / duplicate point key 0
- source / clause / definition / exception refs全解決
- semantic evaluation pointのsource clause coverage
- required evidence roleが許可enumで、procedure catalogとの整合がある
- machine-only decisionをsemantic pointへ重複させていない
- allowed additional observation fieldが `_05g` の16 keyの部分集合
- forbidden shortcutがrequired common guardを含む
- 4.1.1 version / technology rule
- asset canonical hash / approved hash一致

## 11. semantic eval

semantic evalは代表SCだけの品質確認ではなく、asset全件のcontract completenessをdeterministicに確認したうえで、meaning判断の代表caseを実Judgeで確認します。

少なくとも次を含めます。

- applicable / not-applicable / unknown
- normative exception成立 / 不成立 / evidence不足
- machine resultとsemantic meaningが一致しないcase
- visual evidenceが必要なcase
- manual / AT evidenceが必要なcase
- additional observationで解決するcase
- no-progressでundeterminedへ残るcase
- conflicting evidence
- WCAG 2.0 / 2.1 4.1.1 HTML/XML shortcutとnon-HTML/XML path

## 12. 完了条件

- supported versionの全Success Criterionにversioned semantic contract rowがある
- 各rowのnormative clause / definition / exception / semantic evaluation point / required evidence roleがsourceへ追跡可能
- machine化できる処理をsemanticへ逃がしていない
- LLMの判断理由・uncertainty・evidence関係・追加観測の柔軟性を維持する
- criterion / procedure / point集合をLLMが変更できない
- 4.1.1特別契約がversion / technology別に固定される
- deterministic validator / semantic evalがPASSする
