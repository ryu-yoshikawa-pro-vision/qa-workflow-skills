# テスト対象資料管理・テスト実行Skill追加Plan

## 1. `qa-workflow`への追加

`qa-workflow`を16 Skill前提へ更新します。

工程固有ロジック表へ次を追加します。

| 工程固有ロジック | 担当Skill |
| --- | --- |
| テスト対象資料の作成・更新 | `test-target-inspection` |
| テストケース実行・期待結果比較 | `test-execution` |

`test-target-inspection`は既定のテスト分析・設計フローへ固定挿入しません。

`test-execution`もテスト設計だけを要求されたworkflowでは省略します。実行要求がある場合だけ開始または後段Skillとして利用します。

## 2. 代表routing

### テスト対象資料だけ作成 / 更新

```text
test-target-inspection
```

既存資料が有効なら更新範囲だけ確認します。

### テスト設計で実対象資料が必要

```text
必要な時点
  ↓
test-target-inspection
  ↓
既存の設計Skillへ再開
```

資料作成後に必ず`spec-analysis`からやり直しません。開始 / 再開先は要求成果物と影響範囲から決めます。

### AI直接操作でTCを実行

```text
詳細TC
  ↓
test-target-inspection
  ↓
既存の設計Skillへ再開
```

資料作成後に必ず`spec-analysis`からやり直しません。開始 / 再開先は要求成果物と影響範囲から決めます。

### AI直接操作でTCを実行

```text
詳細TC
  ↓
test-execution
  ↓ 必要時
coverage-analysis（対象: TC → テスト実行結果）
```

テスト対象資料は利用可能なら再利用しますが必須依存にしません。

### 自動化済みTCを実行してTC結果を確認

```text
詳細TC + E2E実装参照
  ↓
e2e-test-execution
  ├─ 正常かつ原因分析不要 ─────────┐
  └─ 異常 / 未実行 / cleanup問題 ─→ e2e-test-result-analysis
                                      ↓
                                  test-execution
                                      ↓ 必要時
                         coverage-analysis（TC → テスト実行結果）
```

`test-execution`はPlaywright raw statusを作り直さず、検証済み入力をTCの期待結果と対応付けます。

### 既存E2Eのraw実行だけ

既存経路を維持します。

```text
e2e-test-execution
  ├─ 正常 → 必要なら e2e-test-reporting
  └─ 異常 → e2e-test-result-analysis → 必要なら e2e-test-reporting
```

ユーザーがTC単位のPASS / FAIL確認を求めていなければ`test-execution`を強制しません。

### E2E実装前にテスト対象資料がある

```text
test-target-inspection成果物
      ↓（任意入力）
e2e-test-inspection
      ↓
e2e-test-implementation
```

`e2e-test-inspection`は資料の鮮度と対象範囲を確認して再利用し、Playwright固有事実だけ追加確認します。

## 3. `coverage-analysis`の変更

複数用途Skillの正規対象へ次を追加します。

`TC → テスト実行結果`

現在の正規対象は次です。

```text
テスト設計
TC → E2E実装
E2E実装 → 実行結果
```

追加後:

```text
テスト設計
TC → E2E実装
E2E実装 → 実行結果
TC → テスト実行結果
```

### 比較内容

`TC → テスト実行結果`では、対象TCが次のいずれかへ閉じていることを確認します。

- `PASS`
- `FAIL`
- `未実行` + 理由
- `ブロック中` + 理由

自動化対象外を未実行理由として自動採用しません。自動化対象かどうかと、今回テストを実行するかどうかは別です。

retry attemptやresolved Playwright TestCaseをTC件数として扱いません。TC IDと`test-execution`成果物のTC結果を比較します。

### 変更対象

最低限:

- `skills/coverage-analysis/SKILL.md`
- `skills/coverage-analysis/references/guidance.md`
- `skills/coverage-analysis/assets/output-template.md`
- `skills/coverage-analysis/evals/deterministic/validator.py`
- `skills/coverage-analysis/evals/trigger/*`
- 必要なoutput / semantic eval fixture

既存3用途の意味を変えず、新規用途だけ追加します。

## 4. `e2e-test-inspection`との統合

現在有効なテスト対象資料がある場合だけ、確認済み実対象事実として再利用します。

再利用条件:

- 対象範囲が今回E2E対象を含む
- 確認元が追跡できる
- version / buildまたは確認日時が今回の判断に使える
- `未確認`の値を確認済みとして扱っていない
- repo参照が現在branch / commitと矛盾していない、または差分が判断へ影響しない

資料が古い場合は、E2E inspection全体を停止せず、必要な実対象事実だけ`test-target-inspection`へ更新依頼できます。

`e2e-test-inspection`成果物内には、テスト対象資料を使用した場合だけその参照を残します。資料が存在しない既存経路との互換性を維持します。

## 5. `e2e-test-execution` / `e2e-test-result-analysis`との統合

既存のPlaywright固有契約を維持します。

`e2e-test-execution`から`test-execution`へ渡すのは、既存出力で確認済みの次の情報です。

- logical primary対象
- TC ID（存在時）
- resolved primary TestCase
- 実行開始 / 未実行理由
- raw TestResult status
- expectedStatus / outcome
- attempt履歴
- run-level error
- cleanup / 残存副作用
- artifact / 証跡参照

既存出力でTC判定に必要な対応情報が不足することが実装時に確認された場合だけ、`e2e-test-execution`の出力へ最小のtrace情報を追加します。一般化のために既存raw result表を作り直しません。

異常runでは、必要に応じて`e2e-test-result-analysis`を先に実施し、環境 / データ / 実装 / runner等の原因情報を`test-execution`が未実行 / ブロック判断へ利用できます。ただし原因分析をTC期待結果そのものへ変更しません。

## 6. `e2e-test-reporting`との統合

既存Skillを変更しないことを第一候補とします。

`test-execution`成果物ができても、Playwright固有の実行履歴を報告する要求では`e2e-test-reporting`を引き続き利用します。

README / `qa-workflow`では、次を区別して説明します。

- TC結果: `test-execution`
- Playwright実行報告: `e2e-test-reporting`

## 7. workflow状態表

`skills/qa-workflow/assets/workflow-state-template.md`へ次を追加します。

```text
| test-target-inspection |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-execution |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
```

現時点では両Skillを単一用途Skillとして扱い、`MULTI_USE_SKILL_TARGETS`へ追加しません。

実行方式は`test-execution`成果物内の属性であり、workflow状態の対象 / 実行範囲へ重複して持たせません。

一方、`coverage-analysis`には新しい複数用途の正規対象`TC → テスト実行結果`を追加します。

## 8. 修正routing

`qa-workflow` guidanceへ次を追加します。

- テスト対象資料の事実・鮮度・更新 → `test-target-inspection`
- TC手順 / 期待結果自体の問題 → `test-case-design`
- TC実行・実測・判定・cleanup → `test-execution`
- Playwright runner条件 / raw結果 → `e2e-test-execution`
- Playwright異常の原因分析 → `e2e-test-result-analysis`
- TC → テスト実行結果の追跡 → `coverage-analysis`（対象: `TC → テスト実行結果`）

実装観測と仕様根拠が矛盾する場合、`test-target-inspection`で仕様を変更せず、必要に応じて`question-analysis`または`spec-analysis`へ戻します。

## 9. 変更伝播

### テスト対象資料だけ更新された場合

資料の変更が仕様根拠やTCの意味変更を示さない限り、既存テスト設計を自動で`要再検証`にしません。

ただし、更新により次が判明した場合は影響する担当Skillへ戻します。

- TC手順が実行不能
- 観測方法が成立しない
- 前提条件が実対象に存在しない
- 実装差分と仕様の競合が見つかった

### TCが変更された場合

既存の`test-execution`結果は、期待結果または手順へ影響するTC変更があれば`要再検証`として扱います。古いTC結果を新しいTCのPASS証拠として再利用しません。

### E2E実装が変更された場合

自動実行経路では既存E2E実装 / executionの再検証規則を維持し、必要なrunが更新された後に`test-execution`結果を再評価します。

## 10. 完了判定

テスト実行を要求したworkflowでは、対象TCが`test-execution`成果物上で結果または妥当な未実行 / ブロック状態へ閉じていることを確認します。

全TCのPASSをworkflow完了条件にはしません。FAILでも、要求された実行、必要な原因分析 / 報告、cleanup、未処理ブロッカー、`要再検証`が適切に閉じていればworkflowは完了できます。

一方、実行を要求したTCが理由なく欠落している場合は完了にしません。
