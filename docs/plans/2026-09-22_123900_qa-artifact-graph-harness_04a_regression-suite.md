# Regression Suite / QA Activity 統合Plan

## 1. Regression Suiteの位置づけ

Regression Suiteは、**現在のRegression対象範囲を継続的に検証するための、currentかつ再利用可能な論理Test Caseの基準集合**です。

Suiteを全TCの履歴保管庫にしません。

各新規・改修セッションでは必ずSuiteを見直しますが、current TCを機械的に全件加入させません。

## 2. Regression対象範囲

Suiteの完全性を判定する母集団はSuite自身から作りません。

入力:

- 案件コンテキストの対象機能 / 業務フロー / role
- test level
- 現在有効な仕様根拠
- Product Risk
- 明示された非機能テスト範囲
- 対象外

`coverage-analysis`はこの独立したtest basisから、既存traceabilityを使ってSuite memberへ閉じているか確認します。

```text
current Regression test basis
→ specification / Risk
→ TR
→ TCN / CI
→ current TC
→ Regression Suite
```

feature tag一覧を「全機能」の正本にしません。

## 3. Suite membership

member条件:

- PR #11上でcurrentな論理TCである
- 現在のRegression対象範囲に属する
- 今後の変更後にも繰り返し検証する意味がある

一回限りのmigration確認、調査専用、一時的な確認等はcurrent TCでも恒常memberにしないことがあります。

一方、実行コストが高い、特殊環境が必要、manualであることだけをmembership除外理由にしません。それらはRun側のscope / execution routeで扱います。

membershipの意味判断は、既存のProduct Risk・scope・test objectiveを扱う`test-analysis`へ寄せます。`qa-workflow`は判断結果を記録・反映します。

新しいRegression専用Skillは追加しません。

## 4. Suiteの保持方法

PR #11 merge後にcurrent TCをproject全体で列挙できるか確認します。

### 直接列挙できる場合

Suiteは派生viewとし、TC本文やlifecycleを複製しません。

必要な追加情報だけ保持します。

- Regression対象範囲ref
- membership判断
- 明示的な一時検証 / 対象外理由
- optional filter

### 直接列挙できない場合

project-localなSuite artifactへmember refを保持します。

それでもTC本文、freshness、deleted / superseded判定はPR #11を正本とします。

## 5. feature tag / filter

feature tagは任意のhuman-friendly filterです。

- projectに既存の機能分類がある場合は再利用できる
- 1 TCに複数tagを付けてもよい
- cross-feature TCを許容する
- renameでTC identityを変更しない
- tagがないことだけでmembership / coverageをblockしない
- hierarchyはv1で追加しない

feature指定Regressionを要求されたのにfilterとcurrent scopeのmappingを確定できない場合だけ、そのselected scopeをblockまたは安全側へ拡張します。

coverageはtagではなく既存traceabilityを正本とします。

## 6. add / update / remove

各セッションでは今回意味が変わった範囲だけ更新します。

- stable TC IDが維持された変更 → 同じmember refとしてcurrent sourceを更新
- 新規TC → membership判断後に追加
- split / merge → PR #11のidentity / lifecycle判断に従う
- deleted / superseded相当 → current Suiteから外す
- 今回の成果物に存在しないだけ → 削除しない

過去Regression activityのsnapshotはcurrent Suite更新で書き換えません。

## 7. Full / Selected Run

SuiteとRunを分離します。

### scope決定の優先順位

1. ユーザーが明示したscope
2. 案件コンテキストのRegression方針
3. どちらも未定義なら安全側fallbackとしてfull

### full

snapshot時点の全memberをselectedにします。

`full`は「全memberをscopeへ含めた」という意味であり、「全memberを実際に実行済み」という意味ではありません。

### selected

feature filter、明示TC、PR #11 impact、Product Risk、過去FAIL / Finding等からsubsetを選べます。

`test-analysis`が意味上のselectionを行い、candidate / selected / excluded / rationale / residual riskをactivityへ残します。

selected RunをSuite全体のRegression完了として扱いません。

## 8. 実行状況

Regression activityは最低限次を区別します。

- snapshot member count
- selected count
- executed count
- unexecuted count
- blocked / unresolved count

未実行理由が残っていてもactivityを報告可能にできますが、「全件実行済み」とは表現しません。

## 9. Regression activity成果物

最低限:

- activity ref
- Suite / baseline source ref / revision
- member snapshot refs
- run scope: `full` / `selected`
- optional filter / explicit scope
- candidate refs（selected時）
- selected refs
- excluded refsと理由（selected時）
- selection根拠
- query completeness（利用時）
- residual risk
- execution route refs
- execution refs
- executed / unexecuted / blocked集計
- unresolved

TC本文のsnapshotをここへ複製しません。実行時TC snapshotはPR #12を正本とします。

## 10. manual / E2E

Suite membershipは論理TC単位です。

E2E testwareは実装先です。

- E2E存在だけでmanual不要と判断しない
- `coverage-analysis`（対象: `TC → E2E実装`）で検証責務を確認する
- 十分なE2Eで閉じられるTC → E2E routeを選択可能
- 部分的なE2E → manual + E2E、適切なTC分割、または未解決として扱う
- 1 TC → 複数testwareを許容する
- 複数TC → 1 testwareを許容する
- TCなしE2EへTCを創作しない

TCなしE2EをRegressionで実行する必要がある場合は補助testware対象として扱えますが、TC-basedなRegression対象範囲のcoverage証拠へ自動算入しません。

## 11. candidate不完全時

部分scopeを決めるcandidate queryが`complete=false`の場合、そのcandidateだけでscopeを狭めません。

安全側の処理:

1. ユーザー明示scopeがあれば維持する
2. current test basisから対象範囲を確定できるなら、その範囲のSuite memberまで広げる
3. 対象範囲も確定できなければfullへ広げる、または必要範囲をblockする

候補0件だけを根拠にRegression不要と判断しません。

## 12. 責務

| 処理 | 担当 |
| --- | --- |
| TC設計 | `test-case-design` |
| design traceability / impact / freshness | PR #11 runtime |
| 継続Regression対象かの意味判断 | `test-analysis` |
| Regression対象範囲の意味上coverage | `coverage-analysis` |
| Suite反映 / snapshot / routing | `qa-workflow` |
| TC → E2E実装coverage | `coverage-analysis` |
| manual相当実行 | `test-execution` |
| E2E実行 | `e2e-test-execution` |
| E2E failure分析 | `e2e-test-result-analysis` |
