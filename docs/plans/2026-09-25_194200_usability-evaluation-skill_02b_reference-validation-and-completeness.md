# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは usability-evaluation のnormalized reference corpusについて、reference entryのmerge / split、field coverage、意味検証、完全性を固定します。

source探索の終了条件は _02a_source-acquisition-and-coverage.md、既知sourceのURLは _02c_seed-source-catalog.md を正本とします。

## 1. 完全性の定義

reference corpusの完全性は「採用sourceの公開pageを全部複製したこと」ではありません。

今回の完成条件は、

- 定義した評価能力coverageにgapがない
- normalized referenceへ採用したsource itemの意味が正しく反映されている
- source provenanceと適用条件を失っていない
- project / platform固有guidanceを一般要件へ誤統合していない

ことです。

## 2. normalized referenceへ含める情報

source itemから、今回の評価に利用するdimensionを抽出します。

例:

- problem / user goal
- purpose / rationale
- when / when not
- applicability
- interaction
- states
- feedback
- error prevention / recovery
- accessibility
- responsive / visual
- keyboard / focus
- source-specific platform constraint
- source position / requirement strength

source本文に存在する情報を無条件に全fieldへ変換しません。UI / UX評価に使わないimplementation detail、install手順、API一覧、code sample全文はnormalized corpusへ複製しません。

## 3. referenceのmerge / split

複数source itemを同じreference entryへmergeできる条件:

- 同じUI problem / user goal / interaction patternを扱う
- source固有のapplicability / platform / status / requirement strengthを個別に保持できる
- conflicting recommendationを消さない
- 各source itemへ逆引きできる

splitする条件:

- user goalまたはinteraction modelが異なる
- 同じ名称でもplatform上の意味が異なる
- source固有contractをcommon entryへ入れると誤適用が生じる
- conflicting recommendationを同じpurposeとして表現できない
- mergeするとsource itemの適用条件・位置づけが失われる

aliasは検索導線として扱い、別identityを作りません。

## 4. field-level coverage

各 included / merged-duplicate source itemについて、

- available_dimensions
- captured_dimensions

を保持します。

available_dimensions は、そのsource itemから今回のreference能力へ利用すると判断したdimensionです。

source page内の無関係な全情報を列挙するfieldではありません。

完了条件:

available_dimensions = captured_dimensions

semantic validationでdimension抽出自体の妥当性も確認します。

## 5. 全included item semantic validation

samplingは使いません。

normalized corpusへ included / merged-duplicate とした全source itemについて原文とreferenceを照合します。

確認:

- canonical source / itemが正しい
- source status / positionが正しい
- applicability / platform条件が一致する
- available_dimensionsに評価上必要なdimensionを取りこぼしていない
- captured_dimensionsが原文の意味を歪めていない
- sourceにないrequirement / rationale / exceptionを追加していない
- merge先でsource固有差分・conflictが保持されている
- normative / informative / advisoryを取り違えていない
- projectへのbindingをsourceだけから勝手に決めていない

1項目でも不一致なら修正し、PASSするまで完了にしません。

## 6. reference-only / unavailable

normalized本文を持たないitemは次を確認します。

- canonical URL / public metadata
- access state
- disposition
- reason
- 非公開・取得不能本文を推測していない

source catalogだけで十分なsourceは無理にsource itemを作りません。

## 7. validation記録

source item:

- semantic_validation: pass / fail / not-required
- semantic_validation_reason
- validated_at
- validated_source_version_or_checked_at

deterministic validatorはrecord存在とfail 0を検証します。

意味一致そのものはsemantic validationが担当します。

## 8. source freshness

各source / itemにchecked_atとversion / publication statusを保持します。

runtime時の外部Webアクセスや定期crawlerは要求しません。

projectがcurrent sourceへの厳密準拠を要求し、bundled referenceより新しい公開versionが確認された場合は、古いreferenceだけでcurrent準拠を断定しません。

## 9. source catalogとの関係

references/source-catalog.md はsourceの索引です。

catalogへsourceを載せてもnormalized reference本文を作る必要はありません。

例:

- platform-specific Design Systemで、今回のcommon Web評価能力へ追加知識がない → catalogには保持、normalized common entryは作らない
- projectがそのDesign Systemを採用 → relevant source itemを読み、project-specific / platform-specific guidanceとして利用
- paid ISO本文 → official metadataをcatalogへ保持し、公開範囲を超える本文はsource-reference-only

## 10. 完了条件

- _02a のcapability coverageが閉じている
- normalized corpusで使用する全source itemがdispositionへclosure
- included / merged-duplicateで available_dimensions = captured_dimensions
- included / merged-duplicate全itemのsemantic validation PASS
- merge / split / alias規則違反0
- source / item / reference ID参照整合PASS
- source position / project bindingの混同0
- public-only境界違反0
- blocked 0
