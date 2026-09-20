# テスト対象資料管理・テスト実行Skill追加Plan

## 1. `qa-workflow`への追加

`qa-workflow`を16 Skill前提へ更新します。

工程固有ロジック表へ次を追加します。

| 工程固有ロジック | 担当Skill |
| --- | --- |
| 生きたテスト対象のUI情報・ふるまい収集 / 管理 | `test-target-inspection` |
| AIによるTC実行・期待結果比較・結果報告 | `test-execution` |

`test-target-inspection`は通常のテスト分析・設計フローへ無条件に挿入しません。実対象情報の収集・更新・鮮度確認が必要な場合だけ使用します。

`test-execution`は実行要求がある場合だけ使用します。テスト設計だけのworkflowでは省略します。

## 2. 代表routing

### 生きたテスト対象情報を収集 / 更新

```text
test-target-inspection
```

既存資料がある場合も今回対象範囲を実対象で確認し、`変更なし / 更新 / 削除確認 / 未確認 / 確認不能`へ閉じます。

### テスト設計でcurrentな実対象情報が必要

```text
必要な時点
  ↓
test-target-inspection
  ↓
必要な設計Skillへ再開
```

資料更新後に必ず`spec-analysis`からやり直しません。影響する最も早い責任Skillへ戻します。

### AIがTCを実行して結果を報告

```text
詳細TC
  ↓
test-execution
  ↓
各TCをGiven / When / Then構造のYAMLへ整理
  ↓ unresolvedあり
該当TCは未実行として解消条件を報告
  ↓ unresolvedなし
Playwright MCP等の対話操作
または
Playwright CLI / 今回run用の一時Playwrightコード
  ↓
必要時に画像確認
  ↓
期待結果と実測結果を比較
  ↓
PASS / FAIL / 未実行 / 判定不能
  ↓
テスト実行結果を報告
```

`test-execution`は、AI自身が現在の実対象を操作・観測することを基本とします。操作開始前に各TCをGiven / When / Then構造のYAMLへ整理し、実行または合否判定に影響する曖昧さが残るTCは推測で補完せず`未実行`とします。既存の過去結果を読み替えるだけで新規実行要求を完了にしません。

### repoへ残すPlaywright E2Eが必要

`test-execution`中に、今回runだけの一時コードではなく将来も維持するE2E資産が必要と判明した場合、実行要求だけから暗黙にrepoへ追加しません。

ユーザー要求またはworkflow範囲に永続E2E実装が含まれる場合だけ次へroutingします。

```text
qa-workflow
  ↓
e2e-test-inspection
  ↓
e2e-test-implementation
  ↓
e2e-test-execution
  ↓
必要なら test-execution へ戻してTC結果を報告
```

### 既存repo E2Eを正式なrunner契約で実行

既存経路を維持します。

```text
e2e-test-execution
  ├─ 正常
  │    ├─ Playwright固有報告だけ必要 → e2e-test-reporting
  │    └─ TC結果報告も必要 → test-execution
  └─ 異常 / 未実行 / cleanup問題
       ↓
     e2e-test-result-analysis
       ↓
     必要な再実行はqa-workflow経由でe2e-test-execution
       ↓
     TC結果報告が必要ならtest-execution
```

`test-execution`は、既存repo E2Eのrunner内部契約を再実装しません。

## 3. テスト対象資料の保存・再利用

案件固有のテスト対象資料は、ユーザーまたは案件が指定した保存先へだけ永続化します。

`test-target-inspection`は次を返します。

- 保存済み成果物参照
- 今回確認した対象範囲
- version / build
- 確認条件
- 変更有無
- 未確認 / 確認不能範囲

`qa-workflow`利用時だけ、`qa-workflow`が案件コンテキストの既存`既存QA成果物`欄へ反映します。

成果物全体の更新日時だけでcurrentと判断しません。今回利用する行が実対象でいつ・どの条件で確認されたかを確認します。

今回必要な行が古い、または確認条件が異なり影響を否定できない場合は、必要範囲だけ`test-target-inspection`へ戻します。

## 4. 画像観測の統合

`test-target-inspection`と`test-execution`の両方で、構造情報だけでは判断できない場合に画像を使用できます。

`qa-workflow`は画像確認を別Skillへroutingしません。画像判断は各Skillの観測手段です。

- UI情報・ふるまい管理のための画像確認 → `test-target-inspection`
- TC期待結果を検証するための画像確認 → `test-execution`

画像差分専用Skillや共通画像判定workflowは追加しません。

## 5. `test-target-inspection`と`e2e-test-inspection`の境界

currentなテスト対象資料がある場合、`e2e-test-inspection`は実対象情報の一部を再利用できます。

再利用できる例:

- 到達経路
- UI要素
- role / accessible name
- 現在の状態・ふるまい
- 非同期状態
- 視覚情報
- データ / 権限依存

ただし`e2e-test-inspection`は次を引き続き自分で確認します。

- repo / workspace構造
- Playwright config / project
- fixture / helper / Page Object
- locator方針
- setup / teardown
- E2E実装可否
- Playwright固有の安全条件

テスト対象資料が古い場合は、E2E inspection全体をやり直さず、必要な実対象範囲だけ`test-target-inspection`へ戻せます。

## 6. `test-execution`と既存E2E Skillの境界

### `e2e-test-inspection` / `e2e-test-implementation`

将来も維持するrepo内E2Eコードを作成・更新する場合に使用します。

今回runだけの一時Playwrightコード生成は`test-execution`内で完結できます。

### `e2e-test-execution`

既存 / 実装済みrepo E2Eを正式なrunner契約で実行する責務を維持します。

`test-execution`が直接Playwright MCP等で人間相当の操作を行う経路とは別です。

### `e2e-test-result-analysis`

既存repo E2Eのrun異常、未実行、cleanup問題等の原因分析を維持します。

`test-execution`のUI操作中に見つけた製品挙動不一致を、原因分析のためだけに必ず`e2e-test-result-analysis`へ送ることはしません。

### `e2e-test-reporting`

Playwright runner固有のrun / logical primary / resolved TestCase / attempt / raw status / cleanup等の詳細報告を担当します。

一般TCの実行結果報告は`test-execution`が担当します。

## 7. workflow状態

`skills/qa-workflow/assets/workflow-state-template.md`へ次を追加します。

```text
| test-target-inspection |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-execution |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
```

両Skillを`MULTI_USE_SKILL_TARGETS`へ追加しません。

`test-execution = 再利用`は過去結果の確認だけが要求された場合等に限ります。新規実行要求では、過去結果だけで実行完了にしません。

## 8. 修正routing

`qa-workflow` guidanceへ次を追加します。

- 実対象UI情報・ふるまい・鮮度 → `test-target-inspection`
- TC手順 / 期待結果自体の問題 → `test-case-design`
- TCの実行前整理、AIによる実行・実測・判定・結果報告 → `test-execution`
- 実行前YAMLで判明した元TCの期待結果・手順自体の曖昧さ → 元TCを推測修正せず、必要に応じて`test-case-design`または入力元 / ユーザーへ戻す
- currentな仕様根拠が不明 / 競合 → `question-analysis` / `spec-analysis`
- repoへ残すE2E実装が必要 → `e2e-test-inspection` / `e2e-test-implementation`
- 既存repo E2Eのrunner実行 → `e2e-test-execution`
- 既存repo E2Eの異常原因分析 → `e2e-test-result-analysis`
- Playwright runner固有報告 → `e2e-test-reporting`

`test-execution`の実行中に資料の陳腐化を発見しても、TC実行を安全に継続できるなら結果報告を完了できます。テスト対象資料の管理まで要求されている場合、または後続でcurrentな資料が必要な場合だけ`test-target-inspection`へ更新を戻します。

## 9. 変更伝播

### テスト対象資料が変更された場合

資料更新だけで仕様やTCの意味が変わらない場合、既存テスト設計を一律に`要再検証`へ戻しません。

次が判明した範囲だけ責任Skillへ戻します。

- TC手順が実行不能
- 観測方法が成立しない
- 前提条件が実対象に存在しない
- currentな実対象と仕様根拠の競合を解消する必要がある

### TCが変更された場合

既存`test-execution`結果は、手順または期待結果へ影響する変更があればcurrentな結果として再利用しません。

進行中の実行では固定TC集合を書き換えず、旧成果物を理由付きで閉じ、必要なcleanup後に新しい成果物 / versionを開始します。

### 対象version / build・実施条件が変わった場合

過去の`test-target-inspection` / `test-execution`成果物は履歴として保持します。

対象version / build、role、viewport、locale、feature flag、テストデータ等の差異が観測事実やTC判定へ影響しないことを確認できない場合はcurrentな証拠として自動再利用しません。

## 10. 完了判定

### `test-target-inspection`

今回対象範囲が次のいずれかへ閉じていることを確認します。

- 今回確認・変更なし
- 今回確認・更新
- 今回確認・削除確認
- 未確認
- 確認不能

要求上必要な範囲に未解決の`未確認 / 確認不能`が残る場合は完了にしません。

永続更新が要求成果物なら保存成功まで完了にしません。

### `test-execution`

今回要求されたTC集合について、各TCの実行前YAMLが元TCへ追跡でき、操作開始前の`unresolved`判定が完了していることを確認します。その上で、TC集合が`PASS / FAIL / 未実行 / 判定不能`のいずれかへ漏れなく対応し、必要な実行結果報告が作成されていることを確認します。

全TC PASSはworkflow完了条件ではありません。`FAIL`があっても、要求された実行と報告が終わり、未処理のcleanup / ブロック / 要再検証がなければworkflowは完了できます。

