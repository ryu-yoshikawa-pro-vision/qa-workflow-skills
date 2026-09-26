# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、`usability-evaluation` のsource catalog、source coverage、reference entryについて、production scriptとvalidatorが読む物理Markdown形式を固定します。

logical fieldの意味は `_02_reference-knowledge.md`、source discoveryは `_02a_source-acquisition-and-coverage.md`、semantic validationは `_02b_reference-validation-and-completeness.md` を正本とします。

## 1. 共通Markdown規則

machine-readable tableでは次を固定します。

- heading名とtable column名は本Plan記載どおり
- tableの未設定値は空欄ではなく `-`
- `Checked At` は `YYYY-MM-DD`
- list fieldは `;` 区切り
- list token内のliteral `;` は `\;`、literal `\` は `\\` としてescape
- list tokenは値として前後空白を除去し、unescape後に重複排除して昇順
- machine-readable field内に改行を入れない
- literal `|` は `\|` としてescape
- human note / reasonで改行が必要な場合だけ `<br>` を使用
- parserはheading / column不足、column追加、row column数不一致を拒否する
- unknown enumを拒否する

Markdown本文の説明文をmachine fieldとして推測解析しません。

## 2. references/source-catalog.md

必須sectionは次の3つです。

### Sources

column順を固定します。

| Source ID | Name | Canonical URL | Publisher / Owner | Category | Source Position | Platform / Product Scope | Source Status / Lifecycle | Access State | Checked At | Adoption Status | License / Terms | Coverage Axes | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`Source ID` はadopted / reference-only / replacedとして追跡するsourceで必須です。

`Canonical URL` はsource / document rootのURLであり、fragmentを含めません。

### Candidates

| Candidate Name | Canonical URL | Discovery Origin | Discovery Detail | Coverage Gap | Status | Reason | Checked At | Source ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`Source ID` はadopted / reference-only / replacedへ閉じたcandidateで必要です。それ以外は `-` とします。

### Discovery Runs

| Discovery Type | Discovery Target | Discovery Category | Checked At | Checked Scope | Checked Count | New Candidate Count | Retrieval Boundary | Completion | Block Reason |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |

0件確認もrowを残します。

## 3. references/source-coverage.md

必須sectionは2つです。

### Capability Coverage

| Coverage Axis | Concern / Pattern Family | Required Source Position | Selected Source Refs | Reference Entry Refs | Coverage Status | Gap / Reason | Checked At |
| --- | --- | --- | --- | --- | --- | --- | --- |

`Coverage Status`:

- covered
- not-applicable
- blocked

### Source Items

| Source ID | Source Item Ref | Name / Section | Document Canonical URL | Locator Type | Locator | Disposition | Access State | Source Status / Lifecycle | Reference Destination | Available Dimensions | Captured Dimensions | Semantic Validation | Checked At |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`Document Canonical URL` はfragmentを除いたdocument URLです。

`Locator Type`:

- none
- fragment
- section-id
- heading
- page

`Locator` はdocument内の位置を表します。`Locator Type=none` の場合だけ `-` とします。

source itemのidentityは少なくとも、

```text
Source ID + Document Canonical URL + Locator Type + Locator
```

で区別します。

source root URLのnormalizationとdocument内locatorを同じ処理で潰しません。

## 4. reference entry

leaf reference fileでは1 entryを次の形で持ちます。

```markdown
## <entry name>
<!-- reference-entry-id: REF-0001 -->

...

### Source Items

| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-001-ITEM-0001 | informative | Recommendation | ... |
```

規則:

- entry headingはH2
- ID markerはentry heading直後、次のnon-empty lineに1件だけ置く
- ID markerは `<!-- reference-entry-id: REF-\d{4,} -->`
- `### Source Items` tableを1件だけ持つ
- Source Item Refはsource-coverageへ解決する
- source item refごとのposition / applicabilityを保持する
- prose本文からsource item relationshipを推測しない

## 5. canonical URLとsource locator

`reference_catalog.py normalize-url` はsource / document canonical URLだけを対象とします。

fragment付きURLを入力した場合はfragmentを黙って捨てず、source item用入力である可能性を示すvalidation errorにします。

source itemではAgent / research工程が、

- Document Canonical URL
- Locator Type
- Locator

を分離して入力します。

redirectやofficial canonicalの意味判断はscriptが行いません。

## 6. parser境界

production script / validatorは、

- fixed heading
- fixed table header
- fixed ID marker
- enum
- local cross-reference

だけをparseします。

自然言語本文、URL先本文、Markdown見出し名から意味を推測しません。

## 7. 完了条件

- source-catalog / source-coverageのheadingとcolumnが一意
- empty表現、list separator、backslash / semicolon / pipe escapingが固定
- source item locatorがdocument URLと分離
- reference entry ID markerとSource Items tableが固定
- production scriptとvalidatorが同じartifactを独立実装でparseできる
- malformed heading / column / enum / cross-referenceをfailできる
