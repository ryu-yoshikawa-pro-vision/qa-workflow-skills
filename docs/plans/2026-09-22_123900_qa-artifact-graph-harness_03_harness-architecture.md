# Regression Suite / QA Activity 統合Plan

## 1. 決定論的補助runtimeの位置づけ

補助runtimeは新しいuser-facing Skillにしません。

最初からGraph Harnessを実装せず、次の処理だけ必要に応じて追加します。

- current TC discovery / baseline completeness検査
- Regression Suite / Activity artifact validation
- execution route closureの構造検査
- Activity discovery
- direct ref + deterministic scan
- 必要性を実証した場合だけrelation index build / query

## 2. current TC discovery

PR #11 merge後、PR #11のidentity / lifecycleとartifact discoveryを分離して確認します。

discovery rootの優先順位:

1. PR #11 merge後にproject-wide current TCを完全列挙できる既存canonical inventoryがあるなら再利用する
2. なければproject contextの「既存QA成果物」にauthoritative TC成果物の所在を列挙し、それを入口にする

current Regression対象範囲に関係するTC sourceを完全に列挙できない場合、baseline completenessをtrueにしません。

新しい汎用artifact registryは作りません。

## 3. Regression Suiteの保持方法

### current TCとmembershipを再構成できる場合

Suiteは派生viewとします。

別artifactに必要な場合だけ次を保持します。

- Regression対象範囲ref / source revision
- TC refごとのmembership判断
- membership判断のsource refs / revisions
- 一時検証 / 対象外理由
- optional filter

### 再構成できない場合

project-local Suite artifactへmember refを保持します。

それでもTC本文、stable ID lifecycle、freshnessはPR #11を正本とします。

## 4. Activity discovery

最初に固定project-relative rootからの列挙を検討します。

固定rootを使える場合:

- indexを追加しない
- root配下をdeterministicにscanしてactivityを発見する
- rename / moveは既存artifact保存規約に従い、完了済みActivityの参照を壊さない

固定rootを使えない場合だけproject-local activity indexを追加します。

indexの正規入口はproject contextの「既存QA成果物」から一意に参照できる1件に固定します。

index最小項目:

```text
activity_ref
activity_type
artifact_ref / path
release / version（利用可能な場合）
completed_at（利用可能な場合）
```

index方式ではActivity artifact保存とindex登録を1つの保存処理として扱い、両方が成功するまでActivity保存完了にしません。

TC、Result、Finding本文やlifecycleをindexへ複製しません。

## 5. Activity validator

### Regression activity

- baseline / scope source ref / revisionがある
- selectionに使用したinput ref / revisionを辿れる
- selected refsがmember snapshot内にある
- fullの場合はsnapshot全memberをselectedにしている
- auxiliary TC-free testwareをTC selected countへ混ぜない
- selected logical TCごとにrequired execution routeまたは明示未実行理由がある
- required routeとexecution refの対応が一意に辿れる
- executed / unexecuted / blockedとPASS / FAIL等のresultを混同していない
- 完了後のActivityを上書きしていない

### Suite / baseline

- duplicate member ref
- deleted / superseded相当をcurrent memberとして利用していない
- memberがPR #11 current TCへ解決できる
- membership source ref / revisionを辿れる
- optional filterが既知scopeへ解決できる場合は参照整合
- feature tagの不存在だけでは失敗にしない

### Exploration / Investigation

- local Finding ref一意
- evidence ref整合
- follow-up ref整合
- secret実値を含めない

## 6. execution route contract

Regression Activityではselected logical TCごとに今回必要なrouteを固定します。

route種別:

- manual
- 1件以上のE2E testware
- manual + E2E
- 未実行 / blocked

`coverage-analysis`（`TC → E2E実装`）の結果を入力にしてrequired routeを決めます。

### logical TCのexecuted判定

- required routeが1件でも`未実行`または開始不能のままならlogical TCをexecuted countへ入れない
- required routeがすべて実際のexecution artifactへ閉じた場合、logical TCをexecutedとして数えられる
- execution結果がFAIL / 判定不能でも「実行した」事実とPASSは分離する
- blocked / unresolvedは別集計を保持する
- 1つのexecutionが複数TCをcoverする場合、execution自体は1回だけ実行し、複数TCのrouteから同じexecution refを参照できる
- 1 TCに複数testwareがrequiredなら必要な全routeを追跡する

PR #13でPASS / FAIL判定を再計算しません。source execution resultを参照します。

## 7. TCなしE2E

TCなしE2Eへ架空TCを作りません。

Regressionへ参加させる条件は次だけです。

- ユーザーが明示した
- project contextのRegression方針で補助testwareとして明示されている

full Runでは、Suite TC member全件に加え、案件方針でfull対象と明示された補助testwareを対象にできます。

selected Runではユーザーまたは案件方針で今回scopeへ含めた補助testwareだけを対象にします。

補助testwareはTC selected / executed countと別に集計し、TC-based coverageへ算入しません。

## 8. Activity lifecycle

Activity stateは既存`qa-workflow`の状態語彙を再利用します。

- `未開始`
- `実行中`
- `部分完了（ブロック中あり）`
- `ブロック中`
- `完了`

新しいActivity専用state taxonomyは作りません。

- scope / baseline snapshotが不変ならblock後も同じ`activity_ref`で再開できる
- scopeまたはbaseline snapshotを変更する必要がある場合は別Activity / versionとして開始する
- `完了`後はimmutable
- `完了`前のActivityはexecution refsや状態を更新できる
- workflow完了と全TC PASSを同一視しない

## 9. relation index gate

direct refと発見済みartifactのdeterministic scanで回答不能、または実測したscan costが要件を満たさない場合だけrelation indexを実装します。

その場合も次だけを決定論的に処理します。

- relation record canonicalization
- duplicate / dangling ref
- artifact-local scope
- query completeness
- reproducible build

design lifecycle / currentness / cycle判定をPR #13へ持ち込みません。

## 10. versioning

persistするSuite metadata / Activity machine blockにはschema versionを持たせます。

relation indexを実装しない場合、Graph schema versionやHarness contract versionは追加しません。

relation indexをpersistする場合もrepo revisionで実装versionを識別できるなら独自fingerprint体系を追加しません。
