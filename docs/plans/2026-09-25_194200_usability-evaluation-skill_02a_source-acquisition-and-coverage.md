# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、reference sourceの探索、採用、source-level coverage、追加調査の終了条件を固定します。

「公開Web上に存在する有用なUI / UX sourceを全部見つけること」は証明対象にしません。完成条件は、Skillが今回提供する評価能力に必要なsource coverageを閉じることです。

既知sourceの公式URLは _02c_seed-source-catalog.md を正本とします。

## 1. 目的

source discoveryはreference corpusを無制限に大きくするためではありません。

次を満たすために行います。

- UI / UX評価に必要な能力ごとに、根拠となる公開sourceがある
- normative / informative / advisoryを区別できる
- project / platform固有sourceを一般要件へ誤適用しない
- sourceのcanonical URL、status、checked_atを追跡できる
- normalized reference entryからsource itemへ戻れる
- currentな重要sourceの抜けを能力coverageとして検出できる

## 2. public-only境界

bundled reference corpusへ取り込む根拠は、認証なしで公開参照できる情報だけです。

含める:

- 標準化団体・platform vendor・Design System owner等の公開document
- 公開pattern library / methodology
- 公開metadata、公開status、公開license / terms情報

含めない:

- paywall本文
- login / organization限定本文
- 契約者限定document
- private repository / private Design System
- 権限回避や第三者転載によって得た非公開本文

公開metadataだけ確認できるrestricted sourceはcatalogへ存在と理由を記録できますが、非公開本文を推測しません。

projectから正当に提供された内部仕様・契約資料はevaluation時のproject Authorityとして利用できますが、bundled corpusのsource discoveryへ混ぜません。

## 3. 能力coverage

source discoveryの完了は、次の能力coverageを正本とします。

### UI pattern / purpose

- UI component / interaction pattern
- pattern purpose / problem / rationale
- when / when not
- state / feedback / recovery
- cross-pattern / flow

### interaction / usability principles

- understandability
- controllability
- consistency / conformity with user expectations
- error tolerance / recovery
- learnability
- discoverability / feedback

### accessibility

- WCAG 2.2
- WCAG conformance evaluation methodology
- WAI-ARIA 1.2
- ARIA in HTML
- APG informative guidance
- ACT Rules as informative test method

### visual / responsive

- layout
- hierarchy
- responsive / adaptive behavior
- overflow / clipping / overlap
- focus / status / error visibility

### common Web interaction concerns

- form / validation / input
- navigation
- search / filtering / sorting
- dialog / disclosure / overlay
- selection / collections / tables / grids
- loading / empty / success / error
- onboarding / guidance / help

### platform / adopted Design System

対象projectが採用するDesign Systemまたはtarget platformがある場合、そのsourceをcoverageへ追加します。

すべてのDesign Systemを全page収録することはcompletion条件にしません。

### inspection methodology

usability-inspection に必要な、

- Playwright observation / emulation
- WCAG-EM
- performance measurement source

を別catalogで保持します。

## 4. seed source

_02c_seed-source-catalog.md に列挙した既知sourceは実装時に全件再確認します。

各seedを次へ閉じます。

- adopted
- reference-only
- replaced
- unavailable
- rejected

seedであることだけを理由に全本文をnormalized corpusへ収録しません。

## 5. source採用条件

sourceをnormalized reference knowledgeへadoptする条件:

- public-only境界を満たす
- owner / publisherとcanonical URLを特定できる
- source status / checked_atを追跡できる
- §3の能力coverageへ具体的な評価価値を提供する
- source上の適用条件 / platform / lifecycleを保持できる
- 既存referenceで不足する知識、または独立して保持すべきAuthority / provenanceを持つ

同じ一般論を別表現で繰り返すだけのsourceはcatalogには残せますが、normalized referenceを重複作成しません。

## 6. 追加source discovery

seed catalogを確認した後、§3の能力coverageに未解決gapがある場合だけ追加調査します。

初期query:

- Q1: current Web accessibility standards / conformance methodology
- Q2: current Web UI pattern / interaction guidance
- Q3: current public Design Systems with reusable Web components / patterns
- Q4: platform HIG relevant to Web / target platform
- Q5: usability evaluation / heuristic methodology
- Q6: responsive / visual / error / feedback guidance
- Q7: browser / measurement methodology needed by usability-inspection

query文面は実装時の検索手段へ合わせて具体化できますが、categoryを減らしません。

各queryは検索手段が到達できる結果範囲を確認し、Plan側の任意件数で打ち切りません。

ただし「新しいsourceが見つからなくなるまで再帰探索する」ことはcompletion条件にしません。

## 7. cross-link

adopted sourceのcross-linkは次の場合に確認します。

- source自身がnormative dependencyを参照する
- current version / successor / replacementの確認が必要
- §3の未解決coverage gapを埋める可能性がある
- sourceの意味理解に必要な公式関連documentがある

cross-link先を見つけたことだけで探索を再帰的に拡大しません。

新しいsourceがcoverage gapを埋める場合はcandidateとしてcatalogへ追加し、§5で採否を閉じます。

## 8. source discovery完了条件

次をすべて満たしたらsource discoveryを完了とします。

- _02c_seed-source-catalog.md の全seedを確認済み
- Q1〜Q7を実行済み
- 検索手段のretrieval boundaryを記録済み
- §3の各能力coverageが covered / not-applicable / blocked のいずれかへ閉じている
- blocked = 0
- coverage gapから追加したcandidateがすべて採否済み
- current version / replacement確認が必要なsourceに未処理cross-linkがない
- source catalogにpendingがない

「Web上に他の有用sourceが存在しないこと」は完了条件にしません。

## 9. source item

normalized referenceへ実際に取り込むsource page / document sectionをsource itemとして登録します。

source全体の全pageをitem化しません。

item化するもの:

- normalized reference entryの根拠として使用するpage / section
- normative requirement / methodologyとして直接参照するdocument
- source-specific differenceを保持するために必要なpage

catalogだけで存在を追跡すれば足りるsource pageはitem化しません。

## 10. disposition

source item:

- included
- merged-duplicate
- reference-only
- unavailable
- out-of-scope

access state:

- public
- restricted
- unavailable

source lifecycle / statusは別fieldとして保持します。

## 11. capability coverage artifact

source-coverage.md は「各sourceの全page一覧」ではなく、次を追跡します。

- coverage axis
- concern / pattern family
- required source position
- selected source refs
- reference entry refs
- coverage status
- gap / reason
- checked_at

必要な場合、source itemとのmappingも保持します。

## 12. deterministic化

source discoveryの意味判断はLLM / Agentへ残しますが、次はscriptへ移します。

- canonical URL正規化
- canonical URL duplicate検出
- source ID採番
- source item ref採番
- reference entry ID採番
- deterministic sort
- coverage status集計
- pending / blocked件数集計
- source / item / reference cross-reference整合
- required field検証

詳細は _05_skill-package.md を正本とします。

## 13. 完了条件

- seed catalog全件確認
- Q1〜Q7実行記録あり
- Plan側の任意検索件数上限なし
- capability coverageの全row closure
- blocked 0
- pending source candidate 0
- normalized corpusで使用するsource itemのdisposition closure
- public-only境界違反0
- canonical URL / source ID / source item ref整合PASS
