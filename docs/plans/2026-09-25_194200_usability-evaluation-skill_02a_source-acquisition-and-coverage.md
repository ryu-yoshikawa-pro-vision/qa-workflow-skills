# UIユーザビリティ評価Skill追加Plan

## 1. このPlanの目的

`_02_reference-knowledge.md` は、採用した情報源をreferencesへどう格納するかを定義します。

本ファイルはその前段として、次を固定します。

- どの種類のsourceを探索するか
- sourceを採用する条件
- 採用sourceから何を「全件」として取得するか
- 取得不能・動的ページ・廃止済み情報をどう扱うか
- どの状態になれば「取得できるすべてを棚卸しした」と判断するか

「代表的なUIパターンをいくつか収録した」状態で完了にしません。

## 2. 「取得できるすべて」の意味

対象は、採用したsourceの公開情報のうち、UI / UX評価に直接使える意味情報です。

含む:

- component / patternの目的
- user goal / task
- rationale
- when to use / when not to use
- anatomy / structure
- interaction / behavior
- states
- feedback
- error prevention / recovery
- content guidance
- keyboard / focus
- semantics / accessibility
- responsive / adaptive
- visual hierarchy / layout
- loading / empty / disabled
- input method
- platform差
- known issue / maturity / deprecated status
- related pattern
- evaluation上必要なdo / don't、注意、制約

原則として含めない:

- package install手順
- framework固有APIの全props
- CSS class一覧
- source code全文
- Figma libraryの操作手順
- changelog全文
- brand marketing
- UI評価へ影響しない実装内部詳細

ただし、API属性や実装詳細がinteraction、state、accessibility、focus、responsive behavior等の意味に直接影響する場合は、その意味だけを取り込み対象にできます。

外部source本文をそのまま複製することを「全情報」とは定義しません。評価に必要な意味を欠落させない構造化要約を作り、sourceへ追跡可能にします。

## 3. source discoveryの対象category

最低限、次を別categoryとして探索します。

### Standards / accessibility

- W3C / WAI
- WCAG
- WAI-ARIA / APG
- UI操作・入力・認知・視覚に直接関係する公開accessibility guidance

### Platform HIG

- Apple
- Android / Material
- GNOME
- その他、実装時に公開かつ現行で、UI behaviorを体系化した主要platform HIG

### Official public Design Systems

Plan作成時点のseed:

- GOV.UK Design System
- U.S. Web Design System
- IBM Carbon
- Microsoft Fluent 2
- Atlassian Design System
- Adobe Spectrum
- GitHub Primer
- Salesforce Lightning Design System
- SAP Fiori
- Shopify Polaris

seedを固定上限にしません。

### Structured UI pattern libraries

Plan作成時点のseed:

- ソシオメディア UIデザインパターン
- UI-Patterns.com
- Welie Interaction Design Patterns

### Usability evaluation / principles

Plan作成時点のseed:

- Nielsen Norman Groupの10 Usability Heuristics
- Heuristic Evaluation方法
- 各heuristicの理解に直接必要な公式公開補足

NN/gの全記事を無条件に対象母集団にはしません。評価方法・principle・UI interactionの判断根拠としてsource catalogへ採用した記事だけをitemとして閉じます。

## 4. source採用条件

候補sourceは次を確認します。

必須:

- 公開URLで参照できる
- UI / UX評価に直接利用できる体系的な情報がある
- source ownerまたは運営主体を特定できる
- canonicalまたはcurrentな入口を特定できる
- source itemの母集団を一覧・category・sitemap・repository等から合理的に列挙できる、または列挙不能であることを明示できる

優先:

- 標準化団体
- platform vendor
- Design System owner
- 長期利用されている体系的pattern library
- usability methodの一次資料または代表的な公開資料

原則採用しない:

- 出典不明のまとめ記事
- screenshot galleryだけでrationale / usage guidanceがないもの
- SEO目的の断片的なbest-practice記事
- 他sourceの転載だけのページ
- loginしないと本文を取得できず公開sourceとして再利用できないもの

採用しない候補も、調査対象として意味がある場合はsource discovery logに理由を残します。

## 5. source discoveryの進め方

### 5.1 seed source確認

`_02_reference-knowledge.md` のseed sourceについて、current canonical rootを確認します。

legacy URLや検索結果の古いversionをcurrent rootとして固定しません。

### 5.2 category別追加探索

各source categoryで、seed以外の主要sourceを追加探索します。

検索では少なくとも次の概念を組み合わせます。

- design system
- human interface guidelines
- UI patterns
- interaction patterns
- component usage
- accessibility
- usability heuristics
- responsive / adaptive design
- error / feedback / forms / navigation

検索結果をそのまま採用せず、source採用条件へ照合します。

### 5.3 cross-link探索

採用source自身が参照する、

- standard
- accessibility guidance
- related official Design System
- research / pattern source

のうち、評価根拠として独立利用する価値があるものは候補へ追加します。

### 5.4 source discovery closure

source discoveryを「Web全体を完全探索した」とは表現しません。

次を満たした状態を、本実装の探索完了とします。

- 全categoryでseed sourceを確認済み
- category別追加探索を実施済み
- cross-linkから得た候補を確認済み
- 候補ごとにadopted / rejected / unavailable / duplicateを記録済み
- 未処理candidateが0件
- 追加採用sourceがsource-catalog / source-coverageへ入っている

新しいsourceが将来存在し得ることは鮮度契約で扱います。

## 6. source item母集団の固定

sourceを採用したら、そのsourceのitem母集団を先に固定します。

列挙元の優先順:

1. source公式のindex / overview
2. source公式のcategory一覧
3. source公式sitemap / navigation
4. source公式repositoryのdocs manifest
5. 上記で取れない場合だけ、同一domain内の検索結果で補完

例:

- APG: Patterns一覧 / Practices一覧
- GOV.UK: Components一覧 / Patterns一覧
- USWDS: Components overview / Patterns
- Carbon: Components overview / Patterns overview / Community patterns
- Primer: Components / UI Patterns / Foundations
- GNOME HIG: Patterns / Guidelines
- ソシオメディア: UIデザインパターンcategoryの全pagination

itemを見つけるたびに追加する方式ではなく、可能なsourceは先に全item一覧を作ります。

## 7. source itemの取得状態

source-coverageのstatusは少なくとも次を使います。

- `included`: 意味情報をreferenceへ収録
- `merged-duplicate`: 他entryへ統合し、source provenanceだけ保持
- `out-of-scope`: UI / UX評価へ直接使わない
- `unavailable`: 公開itemだが現在の取得手段では本文確認不能
- `source-reference-only`: 利用条件等により詳細要約を持たずsource参照だけ保持
- `deprecated`: source自身がdeprecated / retiredとしている。current guidanceへ昇格せず必要な比較用途だけ保持
- `restricted`: login / organization限定等で公開内容として取得不能

`deprecated` / `restricted` を他statusへ畳むかは実装時のvalidator設計で最終決定します。少なくとも意味上は区別します。

## 8. 動的・取得困難なsource

### JavaScript依存

Material Design 3等、HTML取得だけでは本文を得られないsourceでは次の順で確認します。

1. officialな静的 / machine-readable代替ページ
2. official repository / docs source
3. current canonical pageをbrowserで確認可能か
4. 取得できなければunavailable

第三者転載を公式sourceの代替として無言利用しません。

### redirect / 再編

Shopify Polaris等、旧URLが別documentationへredirectする場合:

- current canonical locationを特定
- legacy pathをcurrent itemとして数えない
- 現行surface別reference構造をinventory化
- 旧情報が必要ならhistorical / deprecatedとして分離

### login / internal限定

Carbon Community等で一部がinternal-onlyの場合、公開itemの存在だけ確認できても本文が取得できなければrestricted / unavailableとして閉じます。

内容を推測しません。

## 9. source status / maturity

source itemが次の状態を持つ場合はreferenceへ保持します。

- stable
- beta
- early access
- experimental
- community
- proposal
- deprecated
- retired
- feature flag

状態が存在しないsourceへ独自maturityを付けません。

community / experimental / proposalをstable guidanceと同じ強さで評価しません。

## 10. normalized referenceへの統合

複数sourceが同じpatternを扱う場合、sourceごとに全文を複製しません。

例:

~~~text
Dialog
├─ common purpose / user goal
├─ common interaction concerns
├─ accessibility
├─ visual / responsive
└─ source-specific guidance
   ├─ APG
   ├─ GOV.UK
   ├─ Carbon
   ├─ Fluent
   └─ platform-specific
~~~

統合時にsource間の差異を消しません。

次はsource-specificとして残します。

- platform固有interaction
- Design System固有のwhen / when not
- maturity
- accessibility guaranteeの範囲
- conflicting recommendation
- product / government固有要件

## 11. reference field coverage

各included itemについて、sourceに存在する次の情報種別を取りこぼしていないか確認します。

- purpose
- user goal
- problem
- rationale
- when to use
- when not to use
- anatomy
- variants
- behavior
- states
- feedback
- error / recovery
- keyboard
- focus
- semantics / accessibility
- responsive / adaptive
- content
- visual / layout
- internationalization
- input method
- known issues
- maturity / lifecycle
- related pattern
- source date / version

sourceに存在しないfieldは空欄を埋めるために推測しません。

sourceに存在するのに未収録ならcoverage未完了です。

## 12. completenessを機械検証する範囲

Skill-local validatorで最低限確認します。

- adopted sourceがcatalogにある
- adopted sourceのinventory item数が0でない
- 各itemにstatusがある
- included / merged-duplicateのdestinationが存在する
- source refが一意
- canonical URLがある
- checked_atがある
- source itemの重複がない
- reference entryからsourceへ逆引きできる
- sourceにfield inventoryを持たせる場合、required extraction stateが空欄でない
- discovery candidateが未処理状態で残っていない

Web上の「未知のsourceが存在しないこと」まではvalidatorで証明しません。

## 13. Plan作成時点の確認事項

2026-09-25時点の調査で、少なくとも次を確認しています。

- WAI-ARIA APGはPatternsとPracticesの一覧を持ち、各patternで目的、keyboard、ARIA roles / states / propertiesを体系化している。
- GOV.UKはComponentsとPatternsを分け、Patternsを特定のuser-focused task / page type向けbest practiceとしている。
- USWDSはComponentsとPatternsを持ち、Plan調査時点のComponents overviewで47 componentsを表示している。component lifecycle / statusも公開する。
- CarbonはUniversal patternsとCommunity patternsを区別し、Communityはcore team非保証のものを含む。
- Fluent 2、Atlassian、Primer、Spectrum、SLDS、SAP Fiori、GNOME HIG、Apple HIGはいずれも公開UI guidanceを持つ。
- PrimerはComponentsに加えてcommon user workflow向けUI Patternsを公開する。
- GNOME HIGはPatternsをContainers / Navigation / Controls / Feedbackに分類する。
- Apple HIGはDesign principles / Foundations / Patterns / Components / Inputsを公開する。
- ソシオメディアのUIデザインパターン一覧は複数ページに分かれる。
- Material Design 3は主要ページがJavaScript依存で、単純なHTML取得では本文を取得できない場合がある。
- 旧Polaris URLは現在Shopify DeveloperのPolaris referencesへredirectするものがある。

これらは実装開始時に再確認し、Plan調査時点の状態をcurrentとみなし続けません。

## 14. 実装時に残す調査記録

最終referenceだけでなく、次を実装記録として残します。

- discovery対象category
- candidate source
- 採否
- 理由
- canonical root
- item enumeration method
- inventory count
- unavailable / restricted数
- checked_at
- license / terms確認先

実装途中の一時scrape本文をrepositoryへ保存する必要はありません。

著作物本文のローカルdumpを正本成果物にはしません。
