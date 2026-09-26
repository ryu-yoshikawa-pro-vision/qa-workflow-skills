# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルのsource discovery / coverage契約は `usability-evaluation` のUI / UX reference corpusに適用します。

`usability-inspection` のmethodology sourceへこのall-source discoveryを複製しません。

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

- ISO 9241-110のcurrent公式情報
- Nielsen Norman Groupの10 Usability Heuristics
- Heuristic Evaluation方法
- 各heuristicの理解に直接必要な公式公開補足

ISO本文が公開範囲を超える場合は、公開metadata / abstract等で確認できる範囲をsource-reference-onlyとして扱い、本文を推測・複製しません。

NN/gの全記事を無条件に対象母集団にはしません。評価方法・principle・UI interactionの判断根拠としてsource catalogへ採用した記事だけをitemとして閉じます。

## 4. source採用条件

候補sourceは次を確認します。

必須:

- 公開URLで参照できる
- UI / UX評価に直接利用できる体系的な情報がある
- source ownerまたは運営主体を特定できる
- canonicalまたはcurrentな入口を特定できる
- 採用範囲のsource item母集団を一覧・category・sitemap・repository等から合理的に列挙できる。source全体を列挙できない場合は、公式index等から有限に列挙できるsubsetをadopted scopeとして固定できる
- 既存adopted sourceに対して、少なくとも1つの明確な追加評価価値がある。例: normative requirement、platform固有要件、projectで採用されるDesign System、固有のpattern / rationale、既存sourceでは扱えないinteraction / accessibility / visual guidance

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
- 既存adopted sourceと実質同じ一般guidanceだけを持ち、追加の評価価値を説明できないDesign System / pattern library
- loginしないと本文を取得できず公開sourceとして再利用できないもの

採用しない候補も `source-catalog.md` にcandidateとして残し、採否と理由を記録します。別のsource discovery logは作りません。

seed sourceであること自体はadoptedを意味しません。seedも§4の採用条件へ照合し、追加評価価値が不足する場合は `rejected` または意味上適切な `duplicate` として閉じます。

一方、一度adoptしたsourceについては従来どおりadopted scope内の関連情報をitem単位で閉じ、代表例だけを収録して完了扱いにはしません。

## 5. source discoveryの進め方

### 5.1 seed source確認

`_02_reference-knowledge.md` のseed sourceについて、current canonical rootを確認します。

legacy URLや検索結果の古いversionをcurrent rootとして固定しません。

### 5.2 category別追加探索

seed以外のsource探索は、実装開始時に次のquery matrixを1回固定して実施します。

| Query ID | 検索語 |
| --- | --- |
| Q1 | `design system components patterns accessibility` |
| Q2 | `human interface guidelines interaction accessibility` |
| Q3 | `UI pattern library interaction design patterns` |
| Q4 | `usability heuristics heuristic evaluation interface` |
| Q5 | `accessibility design patterns keyboard focus` |
| Q6 | `responsive adaptive design system patterns` |
| Q7 | `form error feedback navigation design patterns` |

各queryについて、利用する検索手段が返す先頭20件または結果終了までのうち早い方を確認し、同一root URLの重複を除いた候補を `source-catalog.md` へ記録します。

検索結果をそのまま採用せず、§4のsource採用条件へ照合します。検索順位自体をsourceの強さには使いません。

実装中にquery matrixを変更する場合は、旧query結果を消さず、変更理由と再実行したQuery IDを `source-catalog.md` に残します。

### 5.3 cross-link探索

seed確認とQ1〜Q7のcandidate採否を閉じた後、`_02_reference-knowledge.md` §9の規則で `cross-link root set` を固定します。

cross-link探索は、そのroot setに含まれるsourceの公式ページから直接参照される次のlinkだけを1 hop確認します。

- standard
- accessibility guidance
- related official Design System
- research / pattern source

独立した評価根拠として§4の採用条件を満たすものをcandidateへ追加します。

cross-linkで新しく見つけたcandidateをadoptしても、そのsourceは今回のcross-link root setへ追加しません。追加sourceからさらに外部linkを辿らず、`root set → 直接link先` の1段で終了します。

seed / Q1〜Q7の採否変更でroot set対象が変わった場合は、root setを作り直してcross-link確認を再実行します。

### 5.4 source discovery closure

source discoveryを「Web全体を完全探索した」とは表現しません。

次を満たした状態を、本実装の探索完了とします。

- 全categoryのseed sourceを確認済み
- Q1〜Q7がそれぞれsource-catalogのdiscovery実行記録で `completion=completed` へ閉じている
- seed / query由来のadopted sourceへsource IDを付与し、cross-link root setが固定されている
- cross-link root setの全source IDについて1-hop確認がsource-catalogのdiscovery実行記録で `completion=completed` へ閉じている。対象linkまたは新規candidateが0件でも0件として記録されている
- cross-link由来で新たにadoptしたsourceはroot setへ追加せず、cross-link探索完了後にsource IDを付与している
- discovery実行記録に `blocked` が残っていない
- 全candidateが `pending` 以外の `adopted / rejected / unavailable / duplicate` へ閉じている
- adopted sourceがsource-catalog / source-coverageへ入っている

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

source全体の公開itemを合理的に列挙できない場合、source全体をadopted scopeとして「全件取得済み」にはしません。

その場合は、公式index / category / sitemap等から有限に列挙できる範囲をadopted scopeとして明示し、source-catalog / source-coverageへscope boundaryと列挙元を記録します。

例:

~~~text
Apple HIG全体
→ 全件取得済みとは扱わない

Apple HIGのcurrent Components / Patterns / Inputs indexから列挙できた公開item
→ adopted scopeとして全itemをclosure可能
~~~

列挙不能な残りのsource surfaceを暗黙にincluded扱いしません。

## 7. source itemの状態

source itemは次の3軸を分離して保持します。

### coverage disposition

- `included`: 意味情報をreferenceへ収録
- `merged-duplicate`: 他entryへ統合し、source provenanceだけ保持
- `out-of-scope`: UI / UX評価へ直接使わない
- `unavailable`: itemの存在は確認できるが、現在の取得手段では評価に必要な本文を確認できない
- `source-reference-only`: 利用条件等により詳細要約を持たずsource参照だけ保持

### access state

- `public`
- `restricted`

login / organization限定等で本文を確認できないitemは `access_state=restricted` とし、coverage dispositionは実際の取り込み結果に応じて `unavailable` または `source-reference-only` とします。

### maturity / lifecycle

source自身が明示する状態だけを保持します。例: stable / beta / early access / experimental / community / proposal / deprecated / retired / feature flag。

状態がsourceに存在しない場合は独自に推測しません。deprecatedなitemでもhistorical comparison等の目的で `included` になり得るため、coverage dispositionとは分離します。

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

Carbon Community等で一部がinternal-onlyの場合、公開itemの存在だけ確認できても本文が取得できなければ `access_state=restricted` とし、coverage dispositionは `unavailable` または利用条件に応じて `source-reference-only` とします。

内容を推測しません。

## 9. source maturity / lifecycle

maturity / lifecycleは§7の独立軸を使用します。source自身が明示する状態だけを保持し、community / experimental / proposalをstable guidanceと同じ強さで評価しません。

deprecated / retiredでも、current guidanceとしてではなく比較・移行判断に必要で、利用条件を満たす場合はreferenceへ含められます。

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

### field-level coverage

`included` / `merged-duplicate` itemはitem単位のdispositionだけで完了扱いにしません。

sourceに存在すると確認したUI / UX評価上の情報種別を `available_dimensions`、referenceまたは統合先referenceへ収録したものを `captured_dimensions` として記録します。

完了条件:

~~~text
available_dimensions = captured_dimensions
~~~

取得できた関連情報を「今回は省略する」という理由だけで除外できる `excluded_dimensions` は設けません。

利用条件、取得制約、対象外等で収録できない場合は、そのitemを `included` のまま閉じず、`source-reference-only` / `unavailable` / `out-of-scope` 等の既存dispositionへ移します。

`merged-duplicate` では、統合先referenceがそのitemの全 `available_dimensions` を収録していることを確認します。

sourceにそのdimensionが存在するかの意味判断は取得時に行い、deterministic validatorがWeb本文を再解釈しません。

## 12. completenessを機械検証する範囲

Skill-local validatorで最低限確認します。

- source-catalogの全candidateがpending以外へ閉じている
- adopted sourceがcatalogにある
- adopted sourceのadopted scopeと列挙元が記録され、inventory item数が0でない
- 各itemにcoverage dispositionがある
- 各itemにaccess stateがある
- source自身がmaturity / lifecycleを明示する場合はその値を保持している
- included / merged-duplicateのdestinationが存在する
- included / merged-duplicateの各itemに `available_dimensions` / `captured_dimensions` がある
- included / merged-duplicateで `available_dimensions = captured_dimensions`
- source item refがsource-coverage内で一意
- canonical URLがある
- checked_atがある
- source itemの重複がない
- reference entryからsourceへ逆引きできる

Web上の「未知のsourceが存在しないこと」や、source本文中のdimension抽出が意味的に正しいことまではvalidatorで証明しません。

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

最終referenceだけでなく、次を `source-catalog.md` / `source-coverage.md` の対応項目へ実装記録として残します。別の調査ログを正本にしません。

source-catalogのdiscovery実行記録として:

- discovery type
- Query ID / cross-link元source ID
- discovery対象category
- checked_at
- 確認範囲
- 確認件数
- 新規candidate件数
- completion
- block理由

source-catalogのcross-link root set記録として:

- fixed_at
- source IDs（昇順）
- root setを固定した時点のseed / Q1〜Q7採否状態

candidate / adopted sourceの記録として:

- candidate source
- discovery status
- 採否理由
- canonical root
- item enumeration method
- inventory count
- unavailable / restricted数
- checked_at
- license / terms確認先

実装途中の一時scrape本文をrepositoryへ保存する必要はありません。

著作物本文のローカルdumpを正本成果物にはしません。
