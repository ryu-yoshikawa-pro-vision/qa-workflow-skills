# Regression Suite / QA Activity 統合Plan

## 1. 目的

PR #11 / #12後に残る課題だけを扱います。

- 新規・改修で作成したTCを、そのセッションだけで終わらせず継続Regressionへ再利用できるようにする
- 現在のRegression対象範囲を、Suite自身とは独立したtest basisから確定する
- project内のcurrent TCを漏れなく発見し、初回baselineと以後のmembership更新を成立させる
- Regressionごとのcandidate / selected / excluded / rationale / residual risk / executionを履歴として残す
- Exploration / InvestigationのCharter / Session / Finding / Follow-upを第一級成果物として扱う
- release / sessionを跨いで過去activityを欠落なく発見できるようにする

次はPR #13で再実装しません。

- SPEC → TR → TCN → CI → TCのdesign traceability
- design change impact
- freshness / stale / `要再検証`
- TC snapshot
- execution / result / rerun lineage

## 2. 実装開始時の確認

PR #11 / #12 merge後に次を確認します。

1. latest `main`のMachine Entity、traceability、change impact、freshness、execution、rerunの実契約を取得する。
2. PR #11がcurrent TCのidentity / lifecycleを提供することと、project-wideなartifact discoveryを提供することを分けて確認する。
3. project contextの「既存QA成果物」を入口に、current Regression対象範囲に関係するauthoritativeなTC成果物の所在を決定論的に列挙できるか確認する。
4. 3で列挙したsourceからcurrent TCを抽出し、PR #11のlifecycleでcurrent / deleted / superseded相当を解決できるか確認する。
5. discovery sourceの登録漏れを検出できる契約がない場合、project-wide current TC集合を完全とみなさない。
6. TC → current E2E testware、execution → TC snapshot / target version / previous executionを実成果物で確認する。
7. Activity成果物を固定project-relative rootから列挙できるか確認する。できない場合だけproject-local activity indexを検討する。
8. relation indexを作る前に、direct refと発見済みartifactのdeterministic scanで必要queryを回答できるか確認する。

### project-wide current TC discoveryの成立条件

current TC集合を「全件」と扱うには、次を満たす必要があります。

- authoritativeなTC成果物のdiscovery rootが明示されている
- discovery rootはproject contextまたはPR #11 merge後に確認できた既存のcanonical inventoryから一意に辿れる
- current Regression対象範囲に属するTC sourceを黙って除外しない
- discovery不能 / source不足があればbaseline completenessを未確定として扱う

PR #11 merge後により強いcanonical inventoryが実装されている場合はそれを利用し、project contextへ第二のregistryを作りません。

## 3. 初回baseline

PR #13の初回有効化では、増分更新から始めません。

```text
current Regression対象範囲
→ authoritative TC discovery roots
→ 全current TCを列挙
→ membership判断
→ Regression baseline
→ coverage-analysis
```

このreconciliationが完了するまで、既存projectのbaselineを完全なfull基準集合として扱いません。

専用migration Skillは追加しません。

## 4. Regression対象範囲の正本

既存`project-context-template.md`を再利用します。

- §3 テスト範囲: test level、対象機能、画面、role、業務フロー
- §8 非機能テスト範囲
- §11 対象外
- §14 既存QA成果物

実装時はproject contextへ、既存欄と重複しない最小のRegression方針だけ追加します。

- Regression Runの案件既定方針（必要な場合）
- TCなしE2E等の補助testwareをRegressionへ含める明示ref（必要な場合）

対象機能やrole等は§3を正本とし、Regression専用に重複記載しません。

Activityは、当時利用したproject context artifact ref / revisionと、必要なcurrent仕様・Risk等のsource ref / revisionを保持します。独立した「Regression scope revision」管理機構は作りません。

Suite自身のmember / feature tag集合をRegression対象範囲の母集団にしません。

## 5. Regression Suiteのmaterialization gate

project-wide current TCとmembership判断を既存成果物から決定論的に再構成できる場合、Regression Suiteは派生viewとして扱います。

保持するのは必要な追加情報だけです。

- Regression対象範囲ref / source revision
- TC refごとのmembership判断
- membership判断に利用したsource refs / revisions
- 一時検証 / 対象外の理由
- optionalなhuman-friendly filter

TC本文、stable ID lifecycle、freshnessを複製しません。

再構成できない場合だけ、project-localなSuite artifactへmember TC refを保持します。それでもPR #11と競合する第二のTC正本にはしません。

## 6. membership再評価

membershipはTC内容だけに依存しません。

次のいずれかが変わった場合、影響するTCを再評価します。

- TC lifecycle / content
- current Regression対象範囲
- project contextのRegression方針
- membership判断に使用したProduct Risk / test objective
- one-off / 対象外判断の根拠

PR #11のchange impactや既存traceabilityで影響範囲を安全に限定できる場合はその範囲だけ再評価します。

影響範囲を完全に確定できない場合、古いmembershipを維持せずcurrent TC全体を再確認します。

PR #13独自のfreshness stateは作りません。

## 7. 責務境界

### 意味判断

既存Skillが担当します。

- current仕様根拠
- Product Risk
- Test Requirement / Condition / Case
- 継続Regression対象か一時的な検証か
- selected Regressionの意味上のscope
- TC → E2E実装のcoverage
- Exploration / Findingの意味

### qa-workflow

- initial baseline reconciliationの起動
- Suite見直しの起動
- full / selected routing
- Activity lifecycle
- execution routeの受け渡し
- activity discovery
- query不完全時の安全側routing

### 決定論的補助runtime

必要な場合だけ追加します。

- discovery / schema / ref整合
- duplicate / dangling検出
- baseline completeness確認
- Activity discovery
- execution route closureの構造検査
- query completeness

PR #11のdesign impact / freshnessを再計算しません。
