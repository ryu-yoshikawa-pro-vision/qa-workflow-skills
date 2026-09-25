# UIユーザビリティ評価Skill追加Plan

## 1. reference知識の目的

usability-evaluation の判断をAgentの暗黙知だけに依存させず、Skill package内のreferenceから再現可能にします。

SKILL.mdは評価契約とindex参照方法だけを持ち、詳細知識はreferences配下へ分離します。

## 2. 網羅性の定義

「すべての情報」はインターネット全体を無制限に収集する意味にはしません。

実装時に定義した採用情報源について、次を満たす公開・取得可能な情報を対象母集団とします。

- UI component / interaction pattern
- user task / user goal pattern
- usability principle / heuristic
- accessibility
- keyboard / focus / semantics
- layout / responsive / visual hierarchy
- status / feedback
- loading / empty / error / recovery
- form / validation / input
- navigation / search / filtering / sorting
- dialog / disclosure / overlay
- selection / collections / tables / grids
- onboarding / guidance / help
- platform固有UI guidance

対象母集団を先にsource inventoryとして固定し、各対象を次のいずれかへ閉じます。

- 収録済み
- 重複統合済み
- 本Skill対象外
- 取得不能
- 利用条件上、内容収録不可のためsource参照のみ

代表patternを数件入れただけで網羅済みとは扱いません。

## 3. 採用する情報源

実装時に各サイトの公開範囲、robots / access、利用条件、更新状況を再確認します。

### W3C / WAI

対象:

- WCAG 2.2の全Success Criteriaとconformance上必要な関連定義
- 各Success Criterionの公開Understanding document
- Techniques / Failuresのうち、そのSuccess Criterionの理解・観測・判定に利用できる公開情報
- WAI-ARIA APGの全公開Patterns
- WAI-ARIA APGの全公開Practices
- APG examplesから、pattern理解・keyboard・roles / states / properties・注意点に必要な情報

扱い:

- WCAG Success Criterionはtestableな標準要件として扱う
- Understanding / Techniquesはcriterionの理解・評価方法を補助する
- APGはARIAの利用方法に関するguidanceであり、example実装を唯一のproduction正解としない
- native HTMLで解決できる場合に不要なARIAを要求しない

### GOV.UK Design System

対象:

- 公開されている全Components
- 公開されている全Patterns
- accessibility / layout / content等、pattern利用判断に必要な関連guidance

目的:

- user-focused task
- when to use / when not to use
- how it works
- error / validation / task completion
- government service向けに具体化されたinteraction

GOV.UK固有の制度・ブランド要件は一般UI要件へ昇格しません。

### U.S. Web Design System

対象:

- 公開されている全Components
- 公開されている全Patterns
- accessibility guidance
- component maturity / usability guidanceで評価に必要な情報

USWDS固有の米国政府要件と一般化可能なUI原則を分離します。

### Carbon Design System

対象:

- 公開されているstable Components
- 公開されているuniversal Patterns
- 公開されているcommunity patternはsource statusを明示して別扱い
- accessibility guidance
- component usage / behavior / content guidance

community / experimentalをstable guidanceと同じ強さで扱いません。

### Fluent 2 Design System

対象:

- 公開Components
- accessibility
- layout
- content
- interaction / behavior guidance
- patternに相当する公開guidance

Microsoft製品固有の表現と一般化可能な原則を分離します。

### Atlassian Design System

対象:

- 公開Components
- Foundations
- accessibility
- interaction guidance
- public pattern guidance

Atlassian製品固有の規約は、対象プロジェクトが採用していない限りbinding requirementにしません。

### Adobe Spectrum

対象:

- 公開Components
- componentごとのusage / behavior / state / content / accessibility
- Inclusive Design
- layout / typography / color等、UI評価に関係するFoundations
- platform scale、responsive、internationalization等の公開guidance

Spectrum固有のvisual stylingを、採用していないprojectへbinding requirementとして適用しません。

### GitHub Primer

対象:

- 公開Components
- 公開UI Patterns
- Foundationsのうちcontent / layout / responsive / accessibility等の評価に必要なguidance
- component / pattern usage guidance

GitHub固有のproduct conventionと一般化可能なinteraction principleを分離します。

### Salesforce Lightning Design System

対象:

- 現行SLDSの公開Components / Component Blueprints
- accessibility
- interaction / usage / visual language
- responsive / spacing / sizing等の公開guidance

Lightning Base Componentとstyle-only Blueprintの保証範囲を混同しません。

### SAP Fiori

対象:

- 公開Design Principles / General Guidelines
- platform別Design Guidelines
- Components / Floorplans / Patterns相当の公開guidance
- accessibility、responsive、loading / waiting、validation等のUI評価に関係する情報

SAP固有業務・platform前提はsource metadataへ残します。

### GNOME Human Interface Guidelines

対象:

- Design principles
- Guidelines
- 全公開Patterns
- keyboard / pointer / touch / scaling / accessibility等の公開reference

GNOME / GTK / Libadwaita向けplatform conventionは対象platformが一致する場合に優先します。

### Apple Human Interface Guidelines

対象:

- 公開Design principles
- Foundations
- Patterns
- Components
- Inputs
- accessibility
- platform差がUI評価に必要なguidance

iOS / iPadOS / macOS / watchOS / tvOS / visionOS等のplatform固有要件は、対象platformが一致する場合だけ優先します。

### Material Design

実装時に公開・取得可能なMaterial Design 3の、

- foundations
- components
- interaction / behavior
- accessibility
- adaptive / responsive guidance

を対象inventoryへ入れます。

取得不能ページを推測で埋めません。

### Shopify Polaris

実装時に公開・取得可能な、

- components
- patterns
- accessibility
- content / interaction guidance

を対象inventoryへ入れます。

取得不能または現行公開範囲が縮小している場合は状態を記録します。

### ソシオメディア UIデザインパターン

公開されているUIデザインパターンページを対象inventoryへ入れます。

各patternから主に次を構造化します。

- pattern名
- 目的 / 理由
- 効能
- 用法
- 注意
- 関連pattern

本文をそのまま複製せず、評価に必要な意味を要約します。

### Nielsen Norman Group

対象を無制限な全記事にはしません。

本Skillの評価方法に直接必要な公開資料を対象とします。

最低限:

- 10 Usability Heuristics
- Heuristic Evaluationの実施方法
- 各heuristicを理解するための公式公開補足
- UI pattern / interaction評価に直接関係し、source inventoryへ採用すると判断した公開資料

heuristicは広い経験則であり、特定componentの仕様要件ではないことをreferenceに明記します。

### UI-Patterns.com / Welie等

公開され、UI patternの、

- problem
- context
- use when
- solution
- rationale
- examples / related patterns

を確認できる範囲を補助sourceとしてinventory化します。

古い資料では年代と現代Web / mobileへの適用制約を保持します。


## 3.1 追加source discovery

上記の情報源だけを固定リストとして「全情報」とは扱いません。

実装時に、UI / UX評価へ直接利用できる公開情報源を追加調査し、次の条件を満たすsourceが見つかった場合はsource inventoryへ追加します。

- 標準化団体またはplatform vendorの公式UI / accessibility guidance
- 公開Design Systemのcomponent / pattern / interaction guidance
- UI patternの目的・適用条件・rationaleを体系化した公開資料
- usability評価方法を体系化した一次または代表的な資料
- visual / responsive / error / feedback / form / navigation等、本Skillの既存sourceで不足する領域を補う資料

追加sourceを見つけた場合も、権威性だけで既存sourceより常に優先するとは扱わず、source-catalogへ位置づけを記録します。

検索結果やブログ記事を無制限に蓄積することはしません。source inventoryへ採用するかどうかを明示的に判断し、採用したsourceについては対象母集団を全件棚卸しします。

source discoveryと「取得できるすべて」の終了条件は `_02a_source-acquisition-and-coverage.md` を正本とします。

## 4. source優先順位

評価時の既定優先順位を次とします。

1. 対象プロジェクトの現在有効な仕様 / 採用Design System / platform契約
2. 明示的に適用される標準・適合基準
3. 対象platformの公式Human Interface Guidelines
4. W3C / WAI等の標準・公式accessibility guidance
5. 対象プロジェクトが採用しているDesign Systemの公式guidance
6. 他の公式Design Systemに共通して見られるpractice
7. 一般的なUI pattern library
8. usability heuristic

同じ優先度でも対象文脈が異なれば機械的多数決をしません。

## 5. source conflict

source間で異なる推奨がある場合、

- 対象platform
- user goal
- interaction model
- project採用規約
- sourceのnormative / advisory区分
- sourceの更新時点

を比較します。

競合を隠して1つの「正解」に統合しません。

対象文脈だけでは選べない場合は、複数の妥当な選択肢と判定不能理由を残します。

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
source refs
source種別
source確認日
~~~

sourceに存在しない項目を推測補完しません。

## 7. reference構造

予定構成:

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

実装時の実測で1ファイルが過大になる場合だけ意味単位で分割します。

1 pattern = 1 fileを機械的に強制しません。

## 8. index.md

SKILL.mdから最初に読むreferenceは index.md だけにします。

index.mdには次を持たせます。

- どの入力ならどのreferenceを読むか
- pattern名 / alias → reference
- user goal → reference
- cross-cutting concern → reference
- accessibility concern → reference
- platform / Design System → reference
- visual issue → reference
- error / loading / empty / feedback → reference

Agentが全referenceを毎回読み込む前提にはしません。

ただし、対象UIに関連する複数patternがある場合は必要なreferenceを複数読めるようにします。

## 9. source-catalog.md

各情報源について最低限次を管理します。

- source ID
- 名称
- official / third-party
- URL root
- 対象範囲
- normative / advisory
- platform
- 公開状態
- 取得日
- license / terms確認結果
- referenceへの取り込み方針
- 注意事項

## 10. source-coverage.md

「すべて取得した」を検証可能にするため、対象ページ / pattern単位でcoverageを保持します。

最低限:

- source ID
- source item
- canonical URL
- category
- status
- reference destination
- reason
- checked_at

statusの例:

- included
- merged-duplicate
- out-of-scope
- unavailable
- source-reference-only

source itemを追加・削除した場合、coverage表を更新します。

## 11. 著作権・ライセンス

外部資料の長文をreferenceへコピーする設計にはしません。

既定:

- 事実・概念・評価観点を独自の短い日本語で構造化して要約
- source URLを保持
- 必要な attribution を保持
- code exampleや長文説明を転載しない
- 許諾条件が不明なsourceはsource-reference-onlyまたは要約に限定

W3C等、明示ライセンスがあるsourceも実装時に対象ページの適用ライセンスを確認します。

## 12. 鮮度

referenceはsource確認日を持ちます。

runtime時にWeb取得を必須化しません。

ただし対象projectが最新Design Systemへの厳密準拠を要求し、bundled referenceの確認日以降にsource更新があることが分かった場合は、古いreferenceだけでcurrent準拠を断定しません。

自動crawler / 定期更新serviceは今回の実装対象外です。
