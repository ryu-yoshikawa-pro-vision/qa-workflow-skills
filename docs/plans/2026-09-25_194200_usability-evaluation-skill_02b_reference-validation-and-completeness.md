# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-evaluation` のreference corpusについて、source discoveryの終了条件、source採用、reference統合、全item意味検証、完全性を固定します。

`_02_reference-knowledge.md` はsource categoryとreference構造、`_02a_source-acquisition-and-coverage.md` は探索・item inventoryを扱い、本ファイルは「何をもって今回すべて対応したとするか」を正本化します。

## 1. 完全性の定義

Web全体に未知のsourceが存在しないことは証明対象にしません。

今回の完成条件は、次の集合に未処理を残さないことです。

1. Planで定義した全source category
2. seed source
3. Q1〜Q7
4. coverage不足から追加したquery
5. queryで発見したcandidate
6. adopted sourceのadopted scope内cross-linkから発見したcandidate
7. adopted sourceの公開item母集団
8. included / merged-duplicate itemの全available dimensions
9. referenceへ統合した全source itemの意味一致

検索件数、page数、source数、cross-link段数にPlan側の固定上限を設けません。

## 2. public-only境界

bundled corpusへ取り込む根拠は認証なしで公開参照できる情報だけです。

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

公開metadataだけ確認できるrestricted sourceはcandidateとして存在と理由を記録できますが、非公開本文の内容は推測しません。

projectから正当に提供された内部仕様・契約資料はevaluation時のproject Authorityとして利用できますが、bundled corpusのsource inventoryへ混ぜません。

## 3. source discoveryの固定点

source discoveryは1回の検索で終了しません。次を繰り返します。

1. 未完了queryをproviderが到達できる結果終端またはprovider側retrieval boundaryまで確認
2. 新規candidateをcanonical rootで重複排除してsource-catalogへ追加
3. 全candidateをadopted / rejected / duplicate / unavailableのいずれかへ閉じる
4. 新しくadoptしたsourceのadopted scope内cross-linkを確認
5. cross-link由来candidateを同じ採用処理へ戻す
6. coverage上の未探索category / dimensionが見つかった場合は追加queryを作る

次を同時に満たした状態を固定点とします。

- 未完了query = 0
- pending candidate = 0
- 未確認adopted source cross-link = 0
- blocked discovery record = 0
- 直前の処理cycleで新規adopted source = 0
- 未探索として識別されたsource category / coverage gap = 0

provider側の取得上限やrate limitがある場合はretrieval boundaryを記録します。Plan側で結果を途中切断して固定点としません。

## 4. source採用条件

sourceは次をすべて満たす場合だけadoptします。

- public-only境界を満たす
- owner / 運営主体とcanonical rootを特定できる
- UI / UX評価へ直接使える体系的な情報を持つ
- adopted scopeのitem母集団を公式index / category / sitemap / repository docs manifest等から有限に列挙できる
- source上の位置づけ、status、version / checked_atを追跡できる
- 既存adopted sourceに対して追加評価価値を1つ以上説明できる

追加評価価値は次のいずれかです。

- normative / conformance requirement
- platform固有requirement / convention
- Design System固有のcomponent / pattern contract
- 既存sourceにないuser goal / problem / rationale / when / when not
- 既存sourceにないinteraction / state / error / recovery / accessibility / responsive guidance
- usability inspection / evaluation方法を具体化する公開methodology

単に同じ一般論を別表現で繰り返すsourceはduplicate / rejectedへ閉じます。

## 5. source item母集団

adopt後に公式index等からitem母集団を固定し、source-coverageへ全件登録します。

全source surfaceを列挙できない場合は、有限に列挙できる公式subsetだけをadopted scopeとします。subset外を取得済みとは扱いません。

item追加・削除・redirectを確認した場合はstable source item refを維持できるかidentityを判定し、意味上同一ならrefを維持、別identityなら新規refを付与します。

## 6. referenceのmerge / split

複数source itemを同じreference entryへmergeできるのは、次をすべて満たす場合です。

- 同じUI problem / user goal / interaction patternを扱う
- source固有のapplicability / platform / status / requirement strengthを個別fieldで保持できる
- mergeしてもconflicting recommendationを消さない
- 各source itemのavailable dimensionsを統合先から逆引きできる

次の場合は別entryへsplitします。

- user goalまたはinteraction modelが異なる
- 同じ名称でもplatform上の意味が異なる
- source固有contractをcommon entryへ入れると誤適用が生じる
- conflicting recommendationを同一purposeとして表現できない
- mergeするとsource itemの適用条件・位置づけ・dimensionが失われる

aliasは既存entryへの検索導線として扱い、別identityを作りません。同一identityの名称変更だけでreference entry IDを振り直しません。

## 7. field-level coverage

各included / merged-duplicate itemについてsource本文に存在するUI / UX評価上のdimensionを `available_dimensions` に列挙し、referenceへ反映したdimensionを `captured_dimensions` に記録します。

完了条件は次です。

```
available_dimensions = captured_dimensions
```

ただしこの等式だけではdimension抽出の正しさを証明できないため、§8のsemantic validationを必須にします。

「今回は省略する」ための `excluded_dimensions` は設けません。公開情報を利用条件等でreferenceへ保持できない場合はincludedのまま閉じません。

## 8. 全item semantic validation

samplingは使いません。

### included / merged-duplicate

全source itemについて原文とreferenceを照合し、次を確認します。

- source item refが正しいcanonical sourceを指す
- source上の位置づけ・status・適用条件が一致する
- available_dimensionsに原文の評価関連dimensionを取りこぼしていない
- captured_dimensionsの内容が原文の意味を歪めていない
- sourceにないrequirement / rationale / exceptionを追加していない
- merge先でsource固有差分・conflictが保持されている
- normative / informative / advisoryを取り違えていない

1項目でも不一致ならreferenceまたはcoverageを修正し、PASSするまで完了にしません。

### unavailable / source-reference-only

全itemについて次を確認します。

- canonical URL / public metadata
- access state
- disposition
- reason
- 非公開・取得不能本文を推測していないこと

### 検証記録

source-coverageに次を追加します。

- semantic_validation: pass / fail
- semantic_validation_reason
- validated_at
- validated_source_version_or_checked_at

deterministic validatorは全対象itemにvalidation recordが存在し、failが0であることを検証します。意味一致そのものはsemantic validationが担当します。

## 9. source freshness

各source / itemにchecked_atとversion / publication statusを保持します。

runtime時の外部Webアクセスや定期crawlerは要求しません。取得日以後のWeb更新を今回の実装未完了として扱わず、成果物が参照したbundled referenceの確認時点を明示します。

projectが「current sourceへの厳密準拠」を要求し、bundled referenceより新しい公開versionがあることを確認した場合は、古いreferenceだけでcurrent準拠を断定しません。

## 10. 完了条件

- §3のsource discovery固定点へ到達
- adopted sourceの全itemをsource-coverageへ登録
- 全itemがcoverage dispositionへclosure
- included / merged-duplicateでavailable_dimensions = captured_dimensions
- §8の全item semantic validation PASS
- reference merge / split / alias規則に違反がない
- source / item / reference IDの参照整合PASS
- public-only境界違反0
- license / terms確認未完了0
- blocked 0

この条件を満たすまでreference corpus実装完了とは扱いません。
