# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルはWCAG-EM 2.0 Step 5.5で生成する `earl-report.jsonld` の物理serializationを固定します。

EARL 1.0 vocabularyとJSON-LD 1.1を使用します。W3Cがrepository固有のJSON-LD byte形式を定義しているとは扱いません。本Planでいうcanonicalは、同じnormalized inputから同じUTF-8 bytesを生成するrepository内のdeterministic serializationです。RDF dataset canonicalizationや汎用JSON-LD canonicalizationを意味しません。

## 1. owner

`skills/wcag-conformance-evaluation/scripts/earl_report.py` がnormalized formal resultからsidecarを生成します。

LLMはJSON-LD object、IRI、outcome、mode、node順序を手作成しません。

semantic layerへ残すのはEARL生成前のformal criterion resultとprovenance判断です。

## 2. fixed @context

`@context` は次へ固定します。

```json
{
  "earl": "http://www.w3.org/ns/earl#",
  "dct": "http://purl.org/dc/terms/",
  "xsd": "http://www.w3.org/2001/XMLSchema#"
}
```

runtime inputからcontext URLやprefix mappingを受け付けません。

## 3. graph node

top-levelは次へ固定します。

```json
{
  "@context": { "...": "..." },
  "@graph": []
}
```

`@graph` に次のnodeだけを出します。

- evaluator / toolを表すassertor node。`@type` は少なくとも `earl:Assertor`、software assertorなら `earl:Software` も保持する
- canonical sample / variationを表すtest subject node。`@type` は `earl:TestSubject`
- formal resultごとの `earl:Assertion` node
- Assertionごとの `earl:TestResult` node

generic RDF node追加interfaceは作りません。

## 4. stable IRI

artifact-local Markdown refだけをJSON-LDのglobal identityとして使いません。各node `@id` は次から生成します。

```text
urn:qa-workflow-skills:earl:<kind>:<sha256(canonical_identity)>
```

`canonical_identity` はnode kindごとに固定します。

- assertor: evaluator identity / tool identity / evaluation revision
- subject: evaluation ref / sample identity / presentation variation identity
- assertion: evaluation revision / subject IRI / test URI / result identity
- result: assertion identity / formal result ref

表示名、自然言語description、array index、render順はidentityへ使いません。

同じnormalized evaluationを再renderした場合は同じIRIを生成します。

## 5. Assertion node

各formal requirement resultへ1件のAssertionを作ります。

必須property:

- `@id`
- `@type`: `earl:Assertion`
- `earl:assertedBy`: `{ "@id": "<assertor IRI>" }`
- `earl:subject`: `{ "@id": "<subject IRI>" }`
- `earl:test`: `{ "@id": "<versioned static catalogのcanonical Success Criterion / conformance requirement URI>" }`
- `earl:result`: `{ "@id": "<TestResult IRI>" }`
- `earl:mode`: `{ "@id": "<provenanceから導出したEARL mode IRI>" }`

`earl:outcome` をAssertion直下へ置きません。

## 6. TestResult node

各Assertionへ1件の `earl:TestResult` を作ります。

必須property:

- `@id`
- `@type`: `earl:TestResult`
- `earl:outcome`: `{ "@id": "earl:passed | earl:failed | earl:cantTell | earl:untested" }`

evaluation issued timeをformal inputとして保持している場合だけ `dct:date` を出せます。renderer実行時の現在時刻を挿入しません。

outcome mapping:

- `satisfied` → `earl:passed`
- `not-satisfied` → `earl:failed`
- `undetermined` → `earl:cantTell`
- 明示的な未実施resultをblocked / incomplete artifactへ出力する場合だけ `earl:untested`

Success Criterionにapplicable contentが存在しないことをprocedure closureで確認してformal resultが `satisfied` になった場合、EARLだけ別のoutcomeへ変更しません。

fixed `@context` はprefix mappingだけなので、IRI-valued propertyをplain stringで書きません。`earl:assertedBy / subject / test / result / mode / outcome` のIRI valueは必ず `{"@id": ...}` objectとしてrenderし、JSON-LD processorがliteralとして解釈する形を禁止します。

## 7. mode

`earl:mode` はevidence provenanceから次のいずれかへ一意に閉じます。

- `earl:automatic`
- `earl:manual`
- `earl:semiAuto`
- `earl:undisclosed`
- `earl:unknownMode`

複数procedureを含むcriterionでmodeが混在する場合、単純な優先順位で1つを捏造しません。procedure provenanceからcriterion-level modeを一意に導出できる場合だけ対応modeを使用し、導出不能なら `earl:unknownMode` とします。

## 8. subject

subjectはcanonical sample identityとrequired presentation variation identityへ対応します。

同じURLでも別application state / presentation variationは別subjectです。URLだけをidentityにしません。

subject nodeにはsecret query / fragmentを含むraw URLを必須にしません。安全に保持できるscope / sample ref / variation ref等をrepository-local propertyとして追加する場合も、EARL語彙と混同しない固定namespaceを新設しません。人間向けcross-referenceはhuman-readable report側を正本とします。

## 9. deterministic byte serialization

`earl_report.py` はPython標準libraryで次へ固定します。

- UTF-8
- BOMなし
- LF
- top-level key順: `@context`, `@graph`
- `@context` key順: `earl`, `dct`, `xsd`
- graph nodeは `@id` 昇順
- 各node propertyはlexicographic order。ただし `@id`, `@type` を先頭にrenderしてもよく、その順序をrenderer / validatorで固定する
- set semanticsのarrayはIRI / canonical scalar昇順
- duplicate node / duplicate property valueをreject
- compact JSONまたはindent付きJSONのどちらか1形式を実装開始時に選ばず、**indent=2、ensure_ascii=false、末尾LFあり**へ固定する

rendererを同じnormalized inputへ2回実行してbyte一致することをfixtureで確認します。

## 10. structural validator

独立validatorはproduction rendererをimportしません。

次を確認します。

- JSON parse成功
- fixed `@context` 完全一致
- top-level key集合完全一致
- `@graph` node ID一意
- 許可node typeだけ
- Assertionのrequired property
- IRI-valued EARL propertyがplain stringではなく `@id` objectであること
- `earl:result` が存在するTestResultを参照
- TestResultのrequired `earl:outcome`
- subject / assertedBy ref解決
- `earl:test` がtarget version static catalogのcanonical URI
- outcome / modeが許可IRI
- human-readable reportのformal result集合とAssertion集合の差分0
- normalized inputから期待identityを独立再計算しIRI一致
- canonical ordering / duplicate無し
- parse後にvalidator側の独立serializerで再構成した期待bytesとactual bytes一致

汎用RDF reasonerやJSON-LD processorをcompletion dependencyにしません。外部processorが利用可能な環境では追加smokeとして展開可能ですが、それをrepository実装の必須条件にはしません。

## 11. sensitive data

- credential / token / cookie / storageStateをsidecarへ含めない
- raw DOM / screenshot bytesを埋め込まない
- subject identityへsecret URLを使わない
- evidenceの詳細はhuman-readable artifact / immutable evidence refへ残し、EARL sidecarへ複製しない

## 12. fixture

少なくとも次を持ちます。

- `satisfied / not-satisfied / undetermined / explicit untested`
- automatic / manual / semiAuto / unknownMode
- multiple sample / variation subject
- same normalized input → same IRI / same bytes
- input order shuffle → same bytes
- broken result ref → reject
- outcomeをAssertion直下へ置く → reject
- `earl:result / mode / outcome` 等をplain string IRIとして置く → reject
- unknown mode / outcome → reject
- wrong criterion URI / wrong target version → reject
- human-readable result欠落 / EARL extra assertion → reject
- unsafe raw URL / secret field → reject

## 13. 完了条件

- EARL 1.0のAssertion → TestResult → outcome関係を保持する
- JSON-LD 1.1のfixed context / IRI semanticsを固定する
- arbitrary context / arbitrary RDF graphを受け付けない
- artifact-local refとmachine-readable IRIを混同しない
- formal resultからoutcome / mode / test URI / identityをscript導出する
- same normalized inputからbyte-identicalなsidecarを生成する
- human-readable reportとassertion coverageが一致する
- production rendererと独立validatorを分離する
