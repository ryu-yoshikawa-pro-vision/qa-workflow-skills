# Regression Suite / QA Activity 統合Plan

## 1. 決定論的補助runtimeの位置づけ

補助runtimeは新しいuser-facing Skillにしません。

最初からGraph Harnessを実装せず、次の順に必要な処理だけ追加します。

1. Regression Suite / Activity artifactのvalidation
2. activity artifactの発見
3. direct refで不足するqueryの確認
4. 必要な場合だけrelation index build / query

## 2. Regression Suiteの保持方法

PR #11 merge後に次を確認します。

### current TC集合を直接列挙できる場合

Regression Suiteは派生viewとして扱います。

必要な追加情報だけ別artifactへ保持します。

- Regression対象範囲ref
- membership判断
- 一時検証 / 対象外の理由
- optionalなhuman-friendly filter

TC本文、stable ID lifecycle、freshnessを複製しません。

### 直接列挙できない場合

project-local artifactへmember refを保持します。

それでも保持するのは参照だけで、TC本文やdesign stateはPR #11を正本とします。

## 3. activity発見

Regression / Exploration / Investigation artifactを後から発見する必要があります。

実装開始時に既存のartifact保存規約を確認し、次の順で選びます。

1. 固定directory / path規則から決定論的に列挙できるならindexを作らない
2. 案件ごとに保存場所が異なる場合だけproject-local activity indexを持つ

indexが必要な場合の最小項目:

```text
activity_ref
activity_type
artifact_ref / path
release / version（利用可能な場合）
completed_at（利用可能な場合）
```

TC、Result、Finding本文やlifecycleを複製しません。

## 4. validator

Graph schema validatorではなく、source artifactごとの必要最小限のvalidatorから始めます。

### Regression Suite / baseline

- duplicate member ref
- deleted / superseded相当をcurrent memberとして利用していない
- memberがPR #11 current TCへ解決できる
- membership判断 / 理由の形式
- optional feature filterが既知scope refへ解決できる場合は参照整合

feature tagの不存在だけでは失敗にしません。

### Regression activity

- Suite / baseline snapshot ref
- selected refsがsnapshot内にある
- fullの場合はsnapshot全memberをselectedにしている
- selectedをfullとして表現していない
- selected TCごとにexecution routeまたは未解決理由がある
- executed / unexecuted / blockedを区別できる
- past activityを書き換えていない

### Exploration / Investigation

- local Finding ref一意
- evidence ref整合
- follow-up ref整合
- secret実値を含めない

## 5. execution route

Regression Activityでは、selected logical TCごとに今回の実行方法を確定します。

候補:

- manual
- 1件以上のE2E testware
- manual + E2E
- 未実行 / blocked

E2E testwareが存在するだけではmanualを省略しません。

`coverage-analysis`（対象: `TC → E2E実装`）が十分な検証責務を確認した結果を入力にします。

1 TC → 複数testware、複数TC → 1 testwareを許容し、1対1前提を置きません。

TCなしE2Eは架空TCを作らず、Regression方針上必要なら補助的なtestware実行対象として扱います。TC-basedな全機能coverageの証拠には自動で数えません。

## 6. relation index gate

direct refで回答不能なqueryが確認された場合だけrelation indexを実装します。

その場合も、

- relation recordのcanonical sort
- duplicate / dangling ref
- artifact-local scope
- query completeness
- reproducible build

だけを決定論的に処理します。

design lifecycle / currentness / cycle判定をPR #13へ持ち込みません。

## 7. source manifest

relation index buildが必要になった場合だけ、今回のbuild input一覧としてmanifestを導入できます。

manifestはartifact registryではありません。

- current QA成果物
- relevant activity artifact
- relevant execution artifact
- relevant exploratory artifact

を列挙するだけにします。

## 8. versioning

Regression Suite / Activity等のpersisted machine blockには必要なschema versionを持たせます。

relation indexを実装しない場合、Graph schema versionやHarness contract versionは追加しません。

relation indexをpersistする場合も、repo revisionで実装versionを識別できるなら独自fingerprint体系を追加しません。
