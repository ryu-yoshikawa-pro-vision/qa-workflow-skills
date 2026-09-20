# テスト対象資料管理・テスト実行Skill追加Plan

## 1. 追加ファイル

```text
skills/test-execution/
├── SKILL.md
├── references/
│   └── guidance.md
├── assets/
│   └── output-template.md
└── evals/
    ├── trigger/
    │   ├── train_queries.json
    │   └── validation_queries.json
    ├── output/
    │   ├── evals.json
    │   └── cases/
    ├── deterministic/
    │   └── validator.py
    └── semantic/
        ├── rubric.json
        ├── evals.json
        └── cases/
```

新しいrunner / browser libraryは追加しません。

## 2. `SKILL.md` 契約

`test-execution`は「TCを実際に実行し、期待結果と実測結果を比較する」責務を持ちます。

### 必須入力

- 実行対象の詳細テストケース
- 元テストケース成果物参照
- 今回実行を要求されたTC ID集合または識別可能な実行範囲
- 元テストケース成果物のrevision、または既存契約で利用可能な内容同一性情報
- 実行対象環境を識別できる情報
- 実行方式、または要求と既存実装からTC単位で一意に決められる情報

詳細テストケースには少なくとも、実行に必要な前提条件・手順・期待結果が存在することを確認します。期待結果が未確定の場合は自力で補完せず、`test-case-design`または`question-analysis`へ戻します。PR #11等によりTC Machine Entityの`content_fingerprint`が既存契約として利用可能ならTC revision判定へ再利用し、`test-execution`専用のhash機構を追加しません。

### 現スコープの実行方式

正規値は次の2つにします。

- `AI直接操作`
- `自動実行`

`AI直接操作`は、利用可能なbrowser / computer操作能力を使ってAIがTC手順を対象環境で実施する方式です。

`自動実行`は、Playwright等の既存自動テストrunnerで取得された検証済み実行結果を利用してTCの期待結果と実測結果を対応付ける方式です。本変更ではPlaywright経路として`e2e-test-execution`を既存の実行担当とします。

「自動実行」を理由に`test-execution`自身がPlaywright commandを直接組み立てません。

実行方式はTC単位で決めます。ユーザーが方式を指定した場合はその指定を優先します。指定がなく、現在有効で安全に実行できるE2E実装と対応関係がある場合は`自動実行`を使用し、それ以外でAI直接操作が安全に成立する場合は`AI直接操作`を使用します。どちらも成立しないTCは開始しません。同一成果物内で両方式を混在できます。

`自動実行`を実施した後に、失敗回避やPASS取得を目的として同じTCを自動的に`AI直接操作`で再実行しません。方式変更による再実行は、ユーザー要求または明示した診断目的がある場合だけ別実行として扱います。

## 3. AI直接操作の実行契約

`references/guidance.md`で次の順序を固定します。

1. 対象TC、対象環境、URL / originを確認する
2. 使用するアカウント / role、認証方法、開始状態、テストデータを確認する
3. TCの副作用について許可範囲と最大回数を確認し、cleanup対象 / 方法を確認する。副作用なしの場合も明示する
4. browser / computer操作能力が対象操作を実施できるか確認する
5. 必須の安全条件を確認できないTCは実行を開始せず`未実行`とし、必要な条件が解消するまで該当範囲をworkflow上`ブロック中`とする
6. TCごとに開始状態を再確認し、前TCが残した状態を暗黙前提にしない
7. TCの手順順序を維持して操作する
8. TCが要求する観測点で実測結果を取得する
9. 期待結果と実測結果を比較する。期待結果との不一致が確定し、その後の手順前提が成立しない場合は無理に後続操作を続けない
10. TC単位の状態を確定する
11. 必要なcleanupと残存状態をTC判定とは別に確認する
12. 実在する場合だけ証跡参照を記録し、未確認事項を記録する

TC手順にない探索的な操作を、PASSを得るために追加しません。診断目的の追加操作が必要な場合は正式TC実行と区別します。

## 4. 自動実行の実行契約

Playwright経路では既存Skillを利用します。

```text
詳細TC + currentなTC → E2E実装対応
  ↓
e2e-test-execution
  ↓
test-execution
  └─ raw factだけではTC判定不能 / 原因分析要求 / 追加実行判断が必要
       ↓
     e2e-test-result-analysis
       ↓ 必要時
     e2e-test-execution / test-execution
```

`test-execution`が利用するのは、`e2e-test-execution`が検証済みとして記録したrunner事実と、実施済みの場合は`e2e-test-result-analysis`の分析結果です。異常runであることだけを理由に原因分析を必須にしません。

次を再解釈しません。

- Playwright run全体status
- process exit code
- `TestResult.status`
- `expectedStatus`
- `TestCase.outcome()`
- retry attempt履歴
- webServer ownership
- artifact鮮度
- runner管理cleanup

runner異常、認証失敗、setup failure、未解決、cleanup問題等によりTCの期待結果を観測できていない場合、TCを製品`FAIL`にしません。`未実行`または`ブロック中`として理由を記録します。

assertion結果等から期待結果と実測結果の差を確認できる場合だけ、TCの`FAIL`判定へ利用します。Playwrightの`failed`というstatusだけを根拠に製品期待結果の不一致と断定しません。run全体PASS、`TestCase.outcome() = expected`、最終retry PASSも単独ではTCの`PASS`根拠にしません。

自動実行では、最低限`TC ID → E2E実装参照 → logical primary → resolved primary TestCase → 実行結果 / 観測証拠`を辿れることを要求します。1 TCが複数のE2E実装 / resolved primaryへ対応する場合も、TCの期待結果を判定するために必要な対応先をすべて確認します。retry attemptは別TCとして数えません。既存`TC → E2E実装`対応がある場合はそれを正本として再利用し、raw結果側の任意TC IDだけに依存しません。

## 5. TC結果状態

正規状態は次です。

- `PASS`: PASS判定に必要なすべての期待結果を観測し、すべて一致した
- `FAIL`: 有効な期待結果との不一致を1つ以上実測で確認した
- `未実行`: 対象TCの実行自体を開始していない
- `判定不能`: 実行は開始したが、必要な観測が成立せずPASS / FAILを確定できない

`ブロック中`はTC結果状態に含めず、必須情報・権限・環境・安全条件等の未解決で現在の実行を進められないSkill / workflow状態として扱います。

`PASS` / `FAIL`には期待結果・実測結果・判定根拠を必須にします。`未実行` / `判定不能`には理由を必須にし、実測していない結果を埋めません。

複数期待結果を持つTCでは次の規則で判定します。

- 1つ以上の期待結果で不一致を確認した場合は`FAIL`。後続手順の前提が崩れて未観測項目が残っても、確認済み不一致を`判定不能`へ弱めない
- 不一致はないが、PASSに必要な期待結果を1つでも観測できなければ`判定不能`
- 実行開始前に停止した場合だけ`未実行`
- 必要な期待結果をすべて観測し、すべて一致した場合だけ`PASS`

cleanup状態はTC結果と別軸です。TCの期待結果をすべて満たした後でcleanupに失敗した場合、TC結果は`PASS`のまま保持し、cleanup失敗により`test-execution` / workflowを完了させません。

## 6. 出力Asset

`skills/test-execution/assets/output-template.md`を正規出力として追加します。

### 実行情報

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 |  |  |
| 元テストケース成果物参照 |  |  |
| TC revision / content identity |  |  |
| 今回の実行対象TC / 範囲 |  |  |
| 環境 / URL / origin |  |  |
| 実施環境 / 対象条件 |  |  |
| version / build ID |  |  |
| 実行日時 |  |  |
| 実行方式概要 | AI直接操作 / 自動実行 / 混在 |  |
| repo revision / E2E code revision |  |  |
| テスト対象資料参照 |  |  |

テスト対象資料を利用していない場合は`未使用`等の明示状態を使用します。

### TC実行結果

| TC ID | 実行方式 | 状態 | 期待結果 | 実測結果 | 判定根拠 | 実行結果参照 / 証跡 |
| --- | --- | --- | --- | --- | --- | --- |

実行方式の正本はTC実行結果表の`実行方式`列とし、複数方式が混在してもrun全体に1方式を強制しません。`TC revision / content identity`は既存のrevision / fingerprint契約を優先し、独自hashを新設しません。

自動実行を利用する場合は次の対応表も出力します。

### 自動実行対応

| TC ID | E2E実装参照 | logical primary | resolved primary TestCase | 実行結果 / 観測証拠 | 対応状態 |
| --- | --- | --- | --- | --- | --- |

### 手順・観測結果

| TC ID | 手順 / 観測点 | 操作 | 期待結果 | 実測結果 | 状態 / 備考 |
| --- | --- | --- | --- | --- | --- |

全TCで全手順を冗長に複製することを目的にしません。ただしPASS / FAIL判定や再現に必要な観測点は追跡できるようにします。

### 未実行・判定不能

| TC ID | 状態 | 理由 | 必要な情報 / 対応 | 再開先 |
| --- | --- | --- | --- | --- |

`状態`は`未実行 / 判定不能`だけを使用します。Skill / workflow上の`ブロック中`はこの表へTC結果として混ぜません。

### cleanup・残存状態

| 対象 | 状態 | 内容 | 根拠 |
| --- | --- | --- | --- |

cleanupの成功 / 失敗 / 未確認はTCのPASS / FAILと独立して記録します。

### 集計

| 状態 | 件数 |
| --- | ---: |
| PASS |  |
| FAIL |  |
| 未実行 |  |
| 判定不能 |  |

集計は今回実行を要求されたTC集合を母集団としてTC単位で行い、自動実行のretry attempt数をTC件数へ加算しません。結果表から要求TCが欠落している、または要求外TCが混入している場合は成果物を完成扱いしません。

永続的な証跡参照が存在しないAI直接操作では架空のURL / artifact参照を作りません。`実測結果`と`判定根拠`は必須とし、`実行結果参照 / 証跡`は実在する参照がある場合だけ記録します。TC判定に不要な個人データ・機密情報を成果物や証跡へ転載しません。

## 7. テスト対象資料の利用

`test-target-inspection`成果物は任意入力です。

次の情報が現在有効なら、AI直接操作時の探索コスト削減や操作の安定化に利用できます。

- 到達経路
- UI要素
- role / accessible name等
- 状態・非同期条件
- データ / 権限依存
- 既存Page Object等の参照

資料が存在しない場合でもTCと実対象だけで安全に実行できるなら開始できます。資料を作るためだけに必ず`test-target-inspection`へ戻しません。

資料と実対象が明らかに不一致の場合は、資料を正として実対象を無視せず、今回観測した事実を保持します。更新要求がある場合だけ`test-target-inspection`へルーティングします。

## 8. `e2e-test-reporting`との境界

`test-execution`の成果物はTC結果です。`e2e-test-reporting`はPlaywright固有のrun / resolved primary / attempt / raw status / cleanup等を人間向けに報告する既存Skillです。

以下を維持します。

- TC実行結果が必要 → `test-execution`
- Playwright runnerの詳細報告が必要 → `e2e-test-reporting`
- 両方必要 → 両成果物を作るが、一方を他方の代替として解釈しない

`e2e-test-reporting`を一般テスト報告Skillへ拡張しません。

## 9. 実装時の主な変更先

新規Skill以外では、ルーティング上必要な範囲だけ変更します。

- `skills/qa-workflow/SKILL.md`
- `skills/qa-workflow/references/guidance.md`
- `skills/qa-workflow/assets/workflow-state-template.md`
- `skills/e2e-test-execution/SKILL.md`またはguidanceの次担当記述（必要な場合）
- `skills/e2e-test-result-analysis/SKILL.md`またはguidanceのrouting記述（必要な場合）

Playwright raw result contractそのものを変更するためだけの修正は行いません。
