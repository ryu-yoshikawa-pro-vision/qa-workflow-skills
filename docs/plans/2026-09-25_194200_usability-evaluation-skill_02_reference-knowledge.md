# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-evaluation` が使用するUI pattern / principle / accessibility / platform / Design System knowledgeのreference設計です。

`usability-inspection` のlive inspection / measurement / Playwright-specific methodologyは `_05a_usability-inspection-package-and-evaluation.md` で別管理し、本reference corpusへ重複収録しません。

## 1. reference知識の目的

usability-evaluation の判断をAgentの暗黙知だけに依存させず、Skill package内のreferenceから再現可能にします。

SKILL.mdは評価契約とindex参照方法だけを持ち、詳細知識はreferences配下へ分離します。

## 2. 網羅性の定義

reference corpusの完成条件は、公開Web上のUI / UX資料をできるだけ多く複製することではありません。

本Skillが今回提供する評価能力を有限なcoverage軸として定義し、その各軸に必要な根拠・pattern知識・standard・methodologyを辿れる状態を完成条件にします。

能力coverageは次を含みます。

- UI component / interaction patternのpurpose / applicability
- usability principle / heuristic
- accessibility standard / conformance methodology
- keyboard / focus / semantics
- layout / responsive / visual hierarchy
- status / feedback
- loading / empty / error / recovery
- form / validation / input
- navigation / search / filtering / sorting
- dialog / disclosure / overlay
- selection / collections / tables / grids
- onboarding / guidance / help
- target project / platformにapplicableなDesign System / HIG

既知sourceの公式URLは `_02c_seed-source-catalog.md` に固定します。

source catalogへ登録したsource全体の全pageをnormalized corpusへ収録する必要はありません。normalized referenceへ実際に使うsource itemだけを取り込み、その全itemを原文と意味照合します。

探索・採用・能力coverageの終了条件は `_02a_source-acquisition-and-coverage.md`、normalized corpusの完全性は `_02b_reference-validation-and-completeness.md` を正本とします。

## 3. 採用する情報源

既知sourceの公式URL・publisher・category・既定の位置づけは `_02c_seed-source-catalog.md` を正本とします。

本ファイルではsourceの「役割」を定義し、各sourceの全pageをnormalized corpusへ取り込むことは要求しません。

### W3C / WAI

利用対象:

- WCAG 2.2 Success Criteriaとconformance関連定義
- Understanding / Techniques / Failuresのうち、対象requirementの理解・観測・判定に必要な公開情報
- WCAG-EM 2.0
- WAI-ARIA 1.2
- current ARIA in HTML
- WAI-ARIA APGの対象pattern / practice
- ACT Rules Format 1.1
- All ACT Rulesのうち、supported ACT Ruleまたはrequirement理解に必要なrule

扱い:

- WCAG / WAI-ARIA / ARIA in HTMLのnormative requirementとinformative guidanceを分離する
- WCAG-EM 2.0はexplicit WCAG conformance evaluationのmethodologyとして扱う
- APGはinformative guidanceであり、example実装を唯一のproduction要件へ昇格しない
- ACT Rulesはinformative testing methodであり、全rule実装を完成条件にしない
- WAI-ARIA 1.3等のDraftをcurrent Recommendationと同じ強さで扱わない
- native HTMLで解決できる場合に不要なARIAを要求しない

WCAG Success Criteriaはstandard inventoryとして全criterionを参照可能にします。ただしgeneral accessibility inspectionで全criterionを毎回実行することとは別です。

### public Design System / platform guidance

seed catalogに登録するDesign System / HIG:

- GOV.UK Design System
- USWDS
- Carbon Design System
- Fluent 2
- Atlassian Design System
- Adobe Spectrum
- GitHub Primer
- Salesforce Lightning Design System 2
- SAP Fiori for Web
- GNOME Human Interface Guidelines
- Apple Human Interface Guidelines
- Material Design 3
- Shopify Polaris

これらは、次の場合にreference itemとして読み込みます。

- projectがそのDesign Systemを明示採用している
- target platform / productが直接該当する
- common UI patternのpurpose / interaction / accessibility / responsive guidanceを補う必要がある
- source固有差分を保持しないと誤適用が生じる

Design Systemの全component / pattern pageをbundled normalized corpusへ複製することは完成条件にしません。

projectが採用していないDesign System固有規約をbinding requirementへ昇格しません。

### usability / interaction principles

seed catalogに登録するsource:

- ISO 9241-110
- Nielsen Norman Groupの10 Usability Heuristics / heuristic evaluation methodology
- UI-Patterns.com
- Welie Interaction Design Pattern Library
- ソシオメディア UIデザインパターン

扱い:

- ISOの有料本文は公開metadata / previewを超えて複製しない
- heuristicはadvisory guidanceであり仕様Authorityへ昇格しない
- pattern libraryはpurpose / when / when not / interaction / rationale等、評価能力に必要なitemだけnormalized referenceへ取り込む
- 古いsourceは公開されていること自体をcurrent best practiceの証明にせず、年代・platform前提・current sourceとの整合を保持する
- sourceのlicense / termsを実装時に確認する

### inspection-specific source

Playwright、Navigation Timing、Paint Timing、Web Vitals等のlive inspection / measurement sourceは `usability-inspection/references/source-catalog.md` に置きます。WCAG-EM / WCAG-EM Report Tool等のformal conformance methodology sourceは `wcag-conformance-evaluation/references/source-catalog.md` に置きます。

UI pattern knowledgeをinspection packageへ複製しません。

## 3.1 追加source discovery

`_02c_seed-source-catalog.md` の既知sourceは実装時に全件再確認します。

追加source discoveryは、`_02a_source-acquisition-and-coverage.md` の能力coverageにgapがある場合だけ行います。

- 標準化団体またはplatform vendorの公式UI / accessibility guidance
- 公開Design Systemのcomponent / pattern / interaction guidance
- UI patternの目的・適用条件・rationaleを体系化した公開資料
- usability評価方法を体系化した一次資料、または方法論の原著が公開されていない場合に手順と出典を追跡できる公開資料
- visual / responsive / error / feedback / form / navigation等、既存referenceで不足する領域を補う資料

追加sourceを見つけても「新しいsourceが見つからなくなるまで」探索を再帰的に拡大しません。coverage gapを埋めるか、独立して保持すべきAuthority / provenanceを持つかを判断し、source-catalogへ採否と理由を残します。

## 4. sourceの適用性と要求の強さ

sourceの発行元だけを固定順位にして評価しません。

評価対象ごとに、まず次を確認します。

- 今回の対象へ適用されるprojectの現在有効な仕様 / 契約か
- projectが明示採用しているDesign System / platform guidelineか
- 明示的に適用されるstandard / conformance requirementか
- source自身がnormative / bindingとして定義する要求か、advisory / informative guidanceか
- 対象platform / user goal / interaction modelへ適用可能か
- currentなversion / statusか

### bindingな要求

projectの現在有効な仕様、明示的な適合基準、対象platformで要求される契約等、今回の対象へbindingな要求は、一般的なadvisory guidanceより優先します。

bindingな要求同士が矛盾する場合は、source種別の固定順位で片方を採用しません。仕様Authority / 適用範囲の解決が必要なconflictとして扱い、既存のquestion-analysis / spec-analysisへroutingします。

### advisoryなguidance

bindingな要求がない範囲では、projectでの明示採用、対象platform、user goal / task、interaction model、sourceの対象範囲、maturity / lifecycle、更新時点から適用可能なguidanceを選びます。

対象projectが採用していないDesign Systemは、pattern理解や複数sourceに共通するpracticeの補助根拠にはできますが、そのDesign System固有規約をbinding requirementとして適用しません。

一般的なUI pattern libraryやusability heuristicはadvisory guidanceとして扱います。

## 5. source conflict

- binding requirement同士が競合する → 無理に選ばずAuthority conflictとしてrouting
- binding requirementとadvisory guidanceが競合する → bindingな要求を評価基準とする
- advisory guidance同士が競合する → project採用、platform、user goal、interaction model、maturity、更新時点から適用可能性を判断
- 対象文脈だけでは選べない → 複数候補と判定不能理由を残す

source数の多数決や、発行元の固定ランキングだけで「正解」を決めません。

## 6. reference entryの共通形式

各pattern / principleは可能な範囲で次を持ちます。

~~~text
ID
名称
別名 / 関連用語
分類
対象platform
ユーザーの目的
patternの目的
解決する問題
なぜこの構造 / interactionを使うか
適用する状況
適用しない状況
基本構造
主要interaction
状態
feedback
error / recovery
keyboard
focus
semantics / accessibility
visual / layout
responsive / zoom / text expansion
loading / empty / disabled等の関連状態
よくある問題
観測方法
評価時の注意
関連pattern
source items:
  - source item ref
  - source上の位置づけ
  - source status / maturity（formal / proposed / draft / stable等、sourceが持つ場合）
  - 適用条件
source確認日
~~~

sourceに存在しない項目を推測補完しません。

各 `source item ref` は、そのitem自身の `source上の位置づけ` と `適用条件` を1対1で保持します。複数source itemを1つのreference entryへ統合しても、normative requirement / informative guidance / advisory guidance等を1つの値へ潰しません。

同じreference entry内で複数source itemが異なる位置づけ・適用条件を持つ場合も、その対応関係を維持します。

一方、今回のprojectでbindingかどうかはreferenceへ固定しません。project Authority、明示された適合基準、platform、採用Design System、対象文脈と組み合わせて評価時に決定し、UI / UX評価項目の `referenceの位置づけ` へ残します。

reference entryの物理marker / Source Items tableは `_02d_reference-artifact-schema.md` を正本とします。

### reference entry ID

reference entryの `ID` はusability-evaluation package内だけのappend-onlyなIDとします。

- 形式: `REF-\d{4,}`
- 初回作成時は、最終的なreference file path、entry名称の順で並べ、`REF-0001` から採番する
- 初回採番後は並べ替え、名称変更、file移動だけを理由にIDを変更しない
- 新しいentryは既存最大番号+1を使う
- 削除・統合したIDを別entryへ再利用しない
- 同じ意味のentryを更新する場合は既存IDを維持し、意味上別entryへ分割する場合は新しいIDを付ける

このIDはSkill package内のreference追跡用であり、新しい全QA共通identityやMachine Entityにはしません。
## 7. reference構造

実装構成:

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
│   │   ├── index.md
│   │   ├── wcag-2.2.md
│   │   ├── wai-aria-1.2.md
│   │   ├── aria-in-html.md
│   │   ├── aria-apg-patterns.md
│   │   └── aria-apg-practices.md
│   ├── patterns/
│   │   ├── index.md
│   │   ├── actions-and-controls.md
│   │   ├── forms-and-input.md
│   │   ├── navigation-and-wayfinding.md
│   │   ├── disclosure-dialogs-and-overlays.md
│   │   ├── selection-and-collections.md
│   │   ├── data-tables-and-visualization.md
│   │   ├── search-filter-and-sort.md
│   │   ├── status-feedback-and-progress.md
│   │   ├── errors-validation-and-recovery.md
│   │   ├── loading-empty-and-disabled-states.md
│   │   ├── help-onboarding-and-guidance.md
│   │   └── layout-responsive-and-visual-integrity.md
│   └── platforms/
│       ├── index.md
│       ├── govuk.md
│       ├── uswds.md
│       ├── carbon.md
│       ├── fluent.md
│       ├── atlassian.md
│       ├── spectrum.md
│       ├── primer.md
│       ├── salesforce-lightning.md
│       ├── sap-fiori.md
│       ├── gnome-hig.md
│       ├── apple-hig.md
│       ├── material.md
│       ├── shopify-polaris.md
│       └── sociomedia.md
~~~

reference fileの分割単位はruntime契約に含めません。1 pattern = 1 fileを機械的に強制せず、意味上同じentryのsource provenanceを分断しない範囲で分割できます。

## 8. index.md

SKILL.mdから最初に読むreferenceは `references/index.md` だけにします。

情報量が大きくなるため、root indexへ全pattern名・全aliasを平置きしません。

~~~text
SKILL.md
  ↓
references/index.md
  ├→ patterns/index.md
  │    └→ 分野別pattern reference
  ├→ accessibility/index.md
  │    └→ WCAG / APG
  └→ platforms/index.md
       └→ Design System / HIG別reference
~~~

root indexには次だけを持たせます。

- 評価段階 / 入力種別から最初に読むsub-index
- user goal / UI種別の大分類からpattern indexへのrouting
- accessibility concernからaccessibility indexへのrouting
- platform / adopted Design Systemからplatform indexへのrouting
- visual issue、error、loading、empty、feedback等のcross-cutting concernから該当indexへのrouting
- source authority / evidence判断への導線

pattern名 / aliasの詳細索引は `patterns/index.md` または既存の分野別indexに置きます。root indexへ全aliasを平置きしません。

Design System固有名称は `platforms/index.md` からcommon patternまたはsource-specific referenceへ解決します。

Agentが全referenceを毎回読み込む前提にはしません。

対象UIに関連する複数patternがある場合だけ、indexから複数referenceを選択します。

root indexの肥大化が確認された場合も、新しい検索runtimeを追加する前にindexを意味単位で分割します。

## 9. source-catalog.md

source-catalog.mdは、known source、採用source、reference-only source、source discoveryで確認したcandidateを辿る正本です。machine-readableなheading / table column / escapingは `_02d_reference-artifact-schema.md` を正本とします。

`_02c_seed-source-catalog.md` の公式URLを実装時に再確認して初期化します。

source row:

- source ID（adopted / reference-onlyとして追跡する場合）
- source name
- canonical URL
- publisher / owner
- category
- source position: normative / informative / advisory / methodology
- platform / product scope
- source status / lifecycle
- access state
- checked_at
- adoption status: adopted / reference-only / replaced / unavailable / rejected
- license / terms確認結果
- coverage axes
- note

projectへのbindingはcatalogのsource positionだけで決めません。project Authorityはevaluation時に別途解決します。

candidate / discovery row:

- candidate name
- canonical URL
- discovery origin: seed / query / cross-link
- discovery detail
- coverage gap
- status: pending / adopted / reference-only / rejected / duplicate / unavailable / replaced
- reason
- checked_at

### source discovery実行記録

Q1〜Q7とcoverage gap由来の追加queryについて、

- discovery type
- discovery target
- discovery category
- checked_at
- 確認範囲
- 確認件数
- 新規candidate件数
- retrieval boundary
- completion: completed / blocked
- block理由

をsource-catalog.mdへ残します。

Plan側で検索結果件数・page数を恣意的に制限しません。

一方、cross-linkを「新しいsourceがなくなるまで」再帰探索することもcompletion条件にしません。normative dependency、current version / successor、coverage gap解消に必要なlinkだけを追跡します。

source discoveryの完了条件は `_02a_source-acquisition-and-coverage.md` を正本とします。

### package-local source ID

source IDはusability-evaluation package内だけのappend-onlyなprovenance keyです。

- 形式: `SRC-\d{3,}`
- 初回実装ではadopted / reference-onlyとして追跡するsourceをcanonical URL昇順で並べて `SRC-001` から採番する
- 追加sourceは既存最大番号+1を使う
- canonical URL、名称、並び順の変更だけを理由に既存source IDを振り直さない
- 削除・duplicate化したsource IDを別sourceへ再利用しない
- Agentが手計算せず `scripts/reference_catalog.py` で採番する

candidate行は採用またはreference-onlyへ確定した時点でsource IDへ対応付けます。

## 10. source-coverage.md

source-coverage.mdはsource page全件表ではなく、評価能力coverageを追跡します。

coverage row:

- coverage axis
- concern / pattern family
- required source position
- selected source refs
- reference entry refs
- coverage status: covered / not-applicable / blocked
- gap / reason
- checked_at

normalized referenceへ実際に使うpage / sectionだけをsource itemとして別途登録します。

source item:

- source ID
- source item ref
- source item name / section
- document canonical URL
- locator type
- locator
- coverage disposition: included / merged-duplicate / reference-only / unavailable / out-of-scope
- access state
- source status / lifecycle
- reference destination
- available_dimensions
- captured_dimensions
- semantic validation
- checked_at

source全体の全pageをitem化しません。

source itemのdocument URLとdocument内locatorを分離します。fragment付きURLをcanonical document URLへ変換する際にlocatorを失いません。source item identityと物理Markdown形式は `_02d_reference-artifact-schema.md` を正本とします。

source ID / source item ref / reference entry IDの採番・canonicalizationは `_05_skill-package.md` のproduction scriptへ移します。

## 11. 著作権・ライセンス

外部資料の長文をreferenceへコピーする設計にはしません。

既定:

- 事実・概念・評価観点を独自の短い日本語で構造化して要約
- source URLを保持
- 必要な attribution を保持
- code exampleや長文説明を転載しない
- 許諾条件が不明なsourceはreference-onlyまたは要約に限定

W3C等、明示ライセンスがあるsourceも実装時に対象ページの適用ライセンスを確認します。

## 12. 鮮度

referenceはsource確認日を持ちます。

runtime時にWeb取得を必須化しません。

ただし対象projectが最新Design Systemへの厳密準拠を要求し、bundled referenceの確認日以降にsource更新があることが分かった場合は、古いreferenceだけでcurrent準拠を断定しません。

自動crawler / 定期更新serviceは今回の実装対象外です。
