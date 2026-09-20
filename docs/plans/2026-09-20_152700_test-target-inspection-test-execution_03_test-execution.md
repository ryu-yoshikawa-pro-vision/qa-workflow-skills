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
- 実行対象環境を識別できる情報
- 実行方式、または要求から一意に決められる実行方式

詳細テストケースには少なくとも、実行に必要な前提条件・手順・期待結果が存在することを確認します。期待結果が未確定の場合は自力で補完せず、`test-case-design`または`question-analysis`へ戻します。

### 現スコープの実行方式

正規値は次の2つにします。

- `AI直接操作`
- `自動実行`

`AI直接操作`は、利用可能なbrowser / computer操作能力を使ってAIがTC手順を対象環境で実施する方式です。

`自動実行`は、Playwright等の既存自動テストrunnerで取得された検証済み実行結果を利用してTCの期待結果と実測結果を対応付ける方式です。本変更ではPlaywright経路として`e2e-test-execution`を既存の実行担当とします。

「自動実行」を理由に`test-execution`自身がPlaywright commandを直接組み立てません。

## 3. AI直接操作の実行契約

`references/guidance.md`で次の順序を固定します。

1. 対象TC、対象環境、URL / originを確認する
2. 必要な認証、開始状態、テストデータ、権限を確認する
3. TCの副作用とcleanup条件を確認する
4. browser / computer操作能力が対象操作を実施できるか確認する
5. 前提条件を満たさないTCは実行を開始せず局所的に`未実行`または`ブロック中`とする
6. TCの手順順序を維持して操作する
7. TCが要求する観測点で実測結果を取得する
8. 期待結果と実測結果を比較する
9. TC単位の状態を確定する
10. 必要なcleanupと残存状態を確認する
11. 証跡参照と未確認事項を記録する

TC手順にない探索的な操作を、PASSを得るために追加しません。診断目的の追加操作が必要な場合は正式TC実行と区別します。

## 4. 自動実行の実行契約

Playwright経路では既存Skillを利用します。

```text
詳細TC
  ↓
E2E実装参照が必要なら既存E2E経路
  ↓
e2e-test-execution
  ↓
必要時 e2e-test-result-analysis
  ↓
test-execution
```

`test-execution`が利用するのは、`e2e-test-execution`が検証済みとして記録したrunner事実と、実施済みの場合は`e2e-test-result-analysis`の分析結果です。

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

assertion結果等から期待結果と実測結果の差を確認できる場合だけ、TCの`FAIL`判定へ利用します。Playwrightの`failed`というstatusだけを根拠に製品期待結果の不一致と断定しません。

## 5. TC結果状態

正規状態は次です。

- `PASS`: 必要な手順を実施し、対象TCの期待結果と実測結果が一致した
- `FAIL`: 必要な観測が成立し、期待結果と実測結果の不一致を確認した
- `未実行`: runner未開始、前提不足、対象未解決等によりTCの実行自体が開始されていない、または有効な判定まで到達していない
- `ブロック中`: 必須情報・権限・環境・安全条件等の未解決により、現在のままでは妥当な実行 / 判定を進められない

`PASS` / `FAIL`には期待結果・実測結果・判定根拠を必須にします。

`未実行` / `ブロック中`には理由を必須にし、実測していない結果を埋めません。

複数期待結果を持つTCでは、必要な期待結果が1つでも未観測なら機械的に`PASS`へしません。部分実施状態を新しい結果ラベルとして増やすのではなく、どの期待結果を観測できなかったかを理由として保持し、TC全体は`未実行`または`ブロック中`へ閉じます。実装時に既存テストケース契約上より適切な状態がある場合は、それを優先します。

## 6. 出力Asset

`skills/test-execution/assets/output-template.md`を正規出力として追加します。

### 実行情報

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 |  |  |
| 環境 / URL |  |  |
| version / build ID |  |  |
| 実行日時 |  |  |
| 実行方式 | AI直接操作 / 自動実行 |  |
| repo revision / E2E code revision |  |  |
| テスト対象資料参照 |  |  |

テスト対象資料を利用していない場合は`未使用`等の明示状態を使用します。

### TC実行結果

| TC ID | 実行方式 | 状態 | 期待結果 | 実測結果 | 判定根拠 | 実行結果参照 / 証跡 |
| --- | --- | --- | --- | --- | --- | --- |

### 手順・観測結果

| TC ID | 手順 / 観測点 | 操作 | 期待結果 | 実測結果 | 状態 / 備考 |
| --- | --- | --- | --- | --- | --- |

全TCで全手順を冗長に複製することを目的にしません。ただしPASS / FAIL判定や再現に必要な観測点は追跡できるようにします。

### 未実行・ブロック

| TC ID | 状態 | 理由 | 必要な情報 / 対応 | 再開先 |
| --- | --- | --- | --- | --- |

### cleanup・残存状態

| 対象 | 状態 | 内容 | 根拠 |
| --- | --- | --- | --- |

### 集計

| 状態 | 件数 |
| --- | ---: |
| PASS |  |
| FAIL |  |
| 未実行 |  |
| ブロック中 |  |

集計はTC単位で行い、自動実行のretry attempt数をTC件数へ加算しません。

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
- `skills/coverage-analysis/*`

Playwright raw result contractそのものを変更するためだけの修正は行いません。
