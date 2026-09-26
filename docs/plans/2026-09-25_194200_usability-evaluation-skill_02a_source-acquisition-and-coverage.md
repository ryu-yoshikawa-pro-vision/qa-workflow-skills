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

## 2.1 public-only境界

bundled reference corpusへ収録する本文・要約の根拠は、認証なしで公開参照できる情報に限定します。

- paywall、契約者限定、organization限定、login必須本文を迂回取得しない
- 公開metadataだけ確認できる非公開sourceは、公開metadataの範囲をcandidateとして記録できますが、非公開本文を推測しない
- projectから別途正当に提供された内部仕様・契約資料はruntime時のproject Authorityとして利用できますが、bundled corpusのsource discoveryへ混ぜない
- public sourceでも利用条件上要約収録できない場合は公開metadata / URLだけを `source-reference-only` として保持する

この境界はsource数を減らすためではなく、取得権限と再配布条件を守るための固定条件です。

## 3. source discoveryの対象category

次をすべて独立したcategoryとして探索します。

### Standards / accessibility

- W3C / WAI
- WCAG
- WAI-ARIA / APG
- ACT Rules Format / formal ACT Rules
- UI操作・入力・認知・視覚に直接関係する公開accessibility guidance

### Platform HIG

- Apple
- Android / Material
- GNOME
- source ownerが公開し、currentなplatform向けUI behaviorを体系化し、§4の採用条件を満たすplatform HIG

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
- usability methodの一次資料。一次資料が公開されていない場合は、手順・原著・適用条件を追跡できる公開資料

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

seed以外のsource探索は、実装開始時に次のquery matrixを初期queryとして実施します。これは探索の開始点であり、query数の上限ではありません。

| Query ID | 検索語 |
| --- | --- |
| Q1 | `design system components patterns accessibility` |
| Q2 | `human interface guidelines interaction accessibility` |
| Q3 | `UI pattern library interaction design patterns` |
| Q4 | `usability heuristics heuristic evaluation interface` |
| Q5 | `accessibility design patterns keyboard focus` |
| Q6 | `responsive adaptive design system patterns` |
| Q7 | `form error feedback navigation design patterns` |

各queryについて、利用する検索手段がpagination可能な範囲を結果終了まで確認します。検索手段自体に取得件数・pagination・rate limit等の外部制約がある場合は、その実際の到達境界を実行記録へ残します。Plan側では「先頭N件」「N pageまで」等の上限を置きません。

同一canonical rootの重複を除いた候補を `source-catalog.md` へ記録し、§4のsource採用条件へ照合します。検索順位自体をsourceの強さには使いません。

初期queryを閉じた後も、source category、coverage、採用候補の内容から未探索の領域が見つかった場合は追加queryを採番して探索します。追加queryの件数は固定しません。追加queryを実行した場合はquery、理由、確認範囲、結果をsource-catalogへ残します。探索は `_02b_reference-validation-and-completeness.md` の固定点条件まで続けます。

### 5.3 cross-link探索

adoptした各sourceについて、adopted scope内の公式ページから直接参照される次のlinkを確認します。

- standard
- accessibility guidance
- related official Design System
- research / pattern source
- その他、§4の採用条件へ照らしてUI / UX評価上の追加価値を持つ可能性があるsource

独立した評価根拠として§4の採用条件を満たすものをcandidateへ追加します。

cross-linkで新しく見つけたcandidateをadoptした場合、そのsourceもcross-link確認対象へ追加します。canonical rootでvisited sourceを重複排除し、未確認のadopted sourceがなくなるまで同じ処理を続けます。Plan側で固定段数の上限は設けません。

これは無制限な一般Web crawlではありません。adopted scopeから参照される関連linkと§4の採用条件で探索対象を制約します。無関係なmarketing、実装API、広告、任意の外部linkは探索対象へ拡張しません。

### 5.4 source discovery closure

source discoveryを「Web全体を完全探索した」とは表現しません。

次を満たした状態を、本実装の探索完了とします。

- 全categoryのseed sourceを確認済み
- Q1〜Q7と追加した全queryがsource-catalogのdiscovery実行記録で `completion=completed` へ閉じている
- 検索手段ごとの実際の到達範囲とprovider側の取得境界が記録されている
- 全candidateが `pending` 以外の `adopted / rejected / unavailable / duplicate` へ閉じている
- 全adopted sourceについてadopted scope内のcross-link確認が `completion=completed`
- cross-link由来candidateも採否が閉じ、adoptされたsourceのcross-link確認も完了している
- discovery実行記録に `blocked` が残っていない
- adopted sourceがsource-catalog / source-coverageへ入っている

Plan側では検索件数、検索結果page数、source数、cross-link段数を探索終了条件にしません。

取得日以後にsourceが更新・追加され得ることは鮮度契約で扱います。今回の完成条件は取得時点の公開source discovery closureです。定期crawlerは要求しません。

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
- ACT Rules: W3Cのformal rules一覧。proposed ruleを確認する場合はformal inventoryと分離し、statusを保持する
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

login / organization限定等で本文を確認できないitemはbundled corpusへadoptしません。公開metadataだけ確認できる場合はcandidate行へ `access_state=restricted` と理由を残し、公開metadataをsource参照として保持する場合だけ `source-reference-only` とします。非公開本文の内容はcoverageへ含めません。

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

Skill-local validatorで次をすべて確認します。

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

Web上に未知のsourceが存在しないことまではvalidatorで証明しません。一方、adopted source本文からのdimension抽出とreferenceへの意味反映は `_02b_reference-validation-and-completeness.md` の全item semantic validationで検証し、samplingだけで完了扱いにしません。

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

source-catalogのsource discovery closure記録として:

- 初期query / 追加queryの実行状態
- 検索手段ごとのretrieval boundary
- cross-link確認済みadopted source IDs
- pending candidate数
- blocked discovery数
- closure確認日時

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
