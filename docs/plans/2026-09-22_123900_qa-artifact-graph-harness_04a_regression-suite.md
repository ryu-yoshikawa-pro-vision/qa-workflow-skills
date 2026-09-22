# QA Artifact Graph / Harness 導入Plan

## 1. Regression Suiteの位置づけ

Regression Suiteは、各新規・改修セッションで設計された機能別Test Caseを継続的に統合した、**現在有効な全機能テストの基準集合**です。

Regressionのたびに変更影響からTCをゼロから集める方式を正本にしません。変更影響・Risk・過去FAIL等は部分実行時の抽出材料として利用します。

Suite memberは論理的なTest Caseです。E2E testwareはTCの実装先であり、同じTCをmanual memberとE2E memberへ二重登録しません。

## 2. Regression Suite成果物

`qa-workflow`配下にproject-localなRegression Suite成果物を持ちます。新しいuser-facing Skillは追加しません。

最小machine block:

```json
{
  "schema_version": "regression-suite-v1",
  "feature_tags": [
    {"tag": "...", "scope_refs": ["SPEC-..."]}
  ],
  "members": [
    {
      "test_case_ref": "TC-...",
      "feature_tags": ["..."],
      "source_artifact_ref": "..."
    }
  ],
  "exclusions": [
    {"test_case_ref": "TC-...", "reason": "..."}
  ]
}
```

current Suite成果物はcurrent membershipの正本です。過去runはactivity成果物内のSuite snapshotを正本とし、current Suite更新で書き換えません。

## 3. 機能タグ

機能タグはRegression Suiteを機能単位で整理・抽出するためのproject-localな分類です。

- 各current member TCは1件以上の機能タグを持つ
- 1 TCへ複数タグを付けてもよい
- tagは既存Suite、案件コンテキスト、現在有効な仕様根拠等で明示された機能区分を再利用する
- 文字列類似、画面名類似、LLM推測だけで新しい機能区分を作らない
- 新機能の明示的な機能区分が存在しない場合はSuite統合を確定せず、必要な区分を明示する
- 機能タグはcoverage証拠ではない

`scope_refs`はその機能タグがどのcurrent仕様範囲を表すかを明示するために使用します。新しい汎用Feature ID体系は作りません。

## 4. 各セッションからの統合

新規・改修セッションでは、`test-case-design`でTCを作成し、必要な`coverage-analysis` / reviewを終えた後にSuite統合を行います。

既定:

1. currentとして確定したTC集合を取得する
2. PR #11 stable IDで既存Suite memberと照合する
3. 同一TC IDがあればcurrent source ref / tagを更新する
4. 新規TC IDはmemberへ追加する
5. current設計から削除 / 置換されたTCはcurrent member集合から外す
6. 各memberの機能タグを確認する
7. current TCをRegressionへ含めない場合だけ`exclusions`へ理由を残す
8. `coverage-analysis`で全機能Suiteの意味上の閉鎖性を確認する

中間candidate、未解決、`要再検証`中のTCはcurrent Suiteの確定memberにしません。

各セッションでSuite更新を行うため、新しい機能・変更機能のテスト設計は次回以降のRegressionへ蓄積されます。

## 5. 全機能網羅の判定

「全機能を網羅」は、feature tagごとにTCが1件存在することでは判定しません。

`coverage-analysis`が現在有効な各機能について次を確認します。

- feature tagがcurrent機能scopeへ対応している
- 機能scope内のcurrent仕様根拠 / Product Risk / TR / TCN / CIが既存契約どおり下流へ閉じている
- その閉鎖先TCがcurrent Regression Suite memberに含まれている
- `要再検証` / stale / unresolvedなTCをcurrent coverageとして数えていない
- current機能scopeにSuite memberへ到達しない未カバーがない

未カバー、ブロック中、未解決feature tagがある場合は「全機能を網羅したRegression Suite」と扱いません。

## 6. 全件実行と部分実行

Regression activityはSuite snapshotを固定してから実行scopeを決めます。

### 全件実行

- ユーザーが単にRegression実施を要求し、絞り込みを指定しない場合の既定
- snapshot時点の全current memberを選択する
- change impact / Riskだけを理由にmemberを落とさない
- memberが実行不能 / ブロック中の場合も選択対象から消さず、未実行理由を残す
- 全memberについてexecutionまたは明示未実行理由が閉じるまで全件実行完了にしない

### 部分実行

次のいずれかが明示された場合だけ行います。

- 機能タグによる対象指定
- ユーザー指定TC / testware
- PR #11のchange impact candidate
- Product Risk
- 明示relationで接続された過去FAIL / Finding

`test-analysis`が意味上のselectionを行い、activity成果物へcandidate / selected / excluded / reason / residual riskを保存します。

部分実行は選択範囲内のRegressionであり、全機能Regression完了とは表現しません。

## 7. Regression activity成果物

各runはcurrent Suiteとは別に活動成果物を持ちます。

最小項目:

- activity artifact ref
- Suite source ref / revision（利用可能な場合）
- Suite member snapshot
- execution mode: `full` / `selected`
- feature tag filter（利用時）
- candidate refs（selected時）
- selected refs
- excluded refsと理由（selected時）
- selection根拠
- relation queryの`complete`
- residual risk
- execution refs
- unresolved / blocked

過去activityは完了後にcurrent Suite変更で書き換えません。

## 8. manual / E2Eの扱い

Suite membershipは論理TC単位です。

- currentなE2E testwareがTCを実装している場合は`implemented_by`等の既存relationを利用する
- testwareがないTCは`test-execution`で実行できる
- 1つのTCをmanualとE2Eの2件としてSuite memberへ重複登録しない
- E2E implementationがTCの検証責務を十分に満たすかは既存`coverage-analysis`（対象: `TC → E2E実装`）を正本とする
- 実行手段が異なっても、Regression activityでは同じlogical TCのexecution historyとして追跡する

## 9. relation不完全時の安全条件

部分実行で候補抽出に使ったrelation queryが`complete=false`の場合、その候補だけでscopeを狭めません。

安全側の選択順:

1. ユーザーが明示したscopeがあればそのscopeを維持する
2. 対応する機能タグが確定していれば対象機能のSuite member全件へ広げる
3. 対象機能も確定できなければ全件Regressionへ広げる、または必要範囲をブロック中として明示する

候補0件だけを根拠にRegression不要と判断しません。

## 10. 責務

| 処理 | 担当 |
| --- | --- |
| TC設計 | `test-case-design` |
| 設計traceability / change impact / freshness | PR #11 runtime |
| Suite bookkeeping / feature tag参照 / activity snapshot | `qa-workflow` |
| 全機能 / 選択範囲の意味上coverage確認 | `coverage-analysis` |
| 部分Regressionの意味上scope選定 | `test-analysis` |
| manual相当実行 | `test-execution` |
| E2E実行 | `e2e-test-execution` |
| E2E失敗分析 | `e2e-test-result-analysis` |

Regression専用Skillは追加しません。
