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

### TCを実行

```text
詳細TC
  ↓
test-execution
  ↓ TC識別子集合を固定し、TCごとに実行方式を確定
  ├─ AI直接操作subset ───────────────┐
  └─ 自動実行subset                  │
       ↓                              │
     e2e-test-execution              │
       ↓ 異常時                       │
     e2e-test-result-analysis         │
       ↓                              │
     test-executionへ再開 ←───────────┘
       ↓
     全TC結果を統合
```

テスト対象資料は利用可能なら再利用しますが必須依存にしません。AI直接操作だけ、自動実行だけの場合も同じ`test-execution`契約の部分集合として扱います。混在時は`test-execution`を未完了のまま保持し、自動実行subsetの結果が戻った後に同じ成果物へ統合します。同じTC識別子を複数方式で暗黙に実行しません。

### 自動化済みTCだけを実行してTC結果を確認

```text
詳細TC + currentなTC → E2E実装対応
  ↓
今回の新規実行要求でcurrentなrunがない
  ↓
e2e-test-execution
  ├─ 正常run ─────────────────→ test-execution
  └─ 異常 / 未実行 / run-level error / cleanup失敗・未確認
        ↓
     e2e-test-result-analysis
        ├─ 追加実行不要 ───────→ test-execution
        └─ 追加実行必要 → e2e-test-execution → 既存E2E異常routingを再適用
```

`test-execution`はPlaywright raw statusを作り直さず、検証済み入力をTCの期待結果と対応付けます。現行`e2e-test-execution` / `qa-workflow`の異常routingを維持し、本変更だけを理由に`e2e-test-result-analysis`を省略しません。過去結果の確認だけを要求されている場合は新しいrunner実行を強制しません。

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

## 3. テスト対象資料の保存・再利用

案件固有のテスト対象資料は、ユーザーまたは案件が指定した保存先へだけ永続化します。`test-target-inspection`は保存済み成果物参照・対象範囲・鮮度 / バージョンを返し、`qa-workflow`利用時だけ`qa-workflow`が既存の`skills/qa-workflow/assets/project-context-template.md`にある`既存QA成果物`欄へ反映します。`test-target-inspection`単体利用では案件コンテキストを変更しません。永続保存・更新自体が要求成果物なのに保存できない場合は、候補資料を返してもworkflowを完了にしません。新しいartifact registry / DBは追加しません。

再利用時は成果物全体の更新日時や成果物上部の今回version / buildだけでcurrentと判断せず、今回利用する対象・要素・状態・遷移等の各行がどの確認元・確認version / build・確認日時 / revisionに基づくか確認します。部分更新で`既存資料から継承・未再確認`となった行は、その行を実際に確認したversion / buildを正本とします。version / build変更時は関連範囲への影響を確認し、影響不明な範囲だけ`test-target-inspection`へ戻します。同一buildでも、今回利用する事実へ影響するrole / 権限、viewport、locale、feature flag、テストデータ等の確認条件が異なる場合は、差異が該当事実へ影響しないことを確認できる範囲だけ再利用します。

テスト設計で利用する場合、現在有効なテスト対象資料を`test-case-design`の補助入力として利用できます。UI名称、到達方法、具体手順、観測可能性には利用できますが、期待結果や合格条件の仕様根拠にはしません。
## 4. `e2e-test-inspection`との統合

現在有効なテスト対象資料がある場合だけ、確認済み実対象事実として再利用します。

再利用条件:

- 対象範囲が今回E2E対象を含む
- 確認元が追跡できる
- 同一version / build、または対象変更がないことを別根拠で確認できる。version / build不明時は確認日時だけでcurrentと判断しない
- `未確認`の値を確認済みとして扱っていない
- repo参照が現在branch / commitと矛盾していない、または差分が判断へ影響しない
- role / 権限、viewport、locale、feature flag、テストデータ等、今回再利用する事実へ影響する確認条件が一致するか、差異が該当事実へ影響しない

資料が古い場合は、E2E inspection全体を停止せず、必要な実対象事実だけ`test-target-inspection`へ更新依頼できます。

`e2e-test-inspection`成果物内には、テスト対象資料を使用した場合だけその参照を残します。資料が存在しない既存経路との互換性を維持します。

## 5. `e2e-test-execution` / `e2e-test-result-analysis`との統合

既存のPlaywright固有契約を維持します。

`e2e-test-execution`から`test-execution`へ渡すのは、既存出力で確認済みの次の情報です。`test-execution`はこれらを今回要求されたTC・対象環境と照合してからTC判定へ使用します。

- currentな`TC → E2E実装`対応
- 今回固定したTC識別子集合の自動実行subsetから解決したlogical primary対象
- 対象URL / origin、Playwright project、必要な認証 / 開始状態 / テストデータ、version / build ID等の実行条件
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

異常、未実行、run-level error、cleanup失敗 / 未確認は現行契約どおり`e2e-test-result-analysis`へ渡し、その分析結果を必要なTC判定へ利用します。正常runでは原因分析要求がなければ`test-execution`へ直接接続できます。原因分析をTC期待結果そのものへ変更しません。

自動実行の対応は`TC識別子 → E2E実装参照 → logical primary → resolved primary TestCase → 実行結果 / 観測証拠`を辿れるようにします。既存`TC → E2E実装`対応を使う場合は、その既存TC IDと今回TC識別子が同一TCを指すことを確認します。今回固定したTC識別子集合の自動実行subsetから必要なlogical primary集合を実行前に解決し、要求外primaryを暗黙追加しません。runner上必要なdependency / teardown等は既存`e2e-test-execution`契約へ委ねます。run全体PASS、`outcome=expected`、最終retry PASSだけではTCの`PASS`にしません。TCを`PASS`にする場合は、currentなE2E実装がPASS判定に必要な期待結果を検証していることを、現在有効なE2E実装成果物、`adversarial-review`（対象: `E2E実装`）の結果、または同等の確認済み事実から確認できることを要求します。`adversarial-review`を根拠にする場合はE2E実装変更後の`要再検証`が残っていない等、reviewがcurrentな実装へ適用できることを確認します。確認できない場合は`判定不能`として必要な担当Skillへ戻します。

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

実行方式は`test-execution`成果物内の属性であり、workflow状態の対象 / 実行範囲へ重複して持たせません。`test-execution = 再利用`は過去結果の確認・分析・報告等で既存成果物をそのまま利用できる場合だけ使用します。ユーザーが今回の新規実行を要求している場合は、過去結果だけを再利用して実行完了にしません。


## 8. 修正routing

`qa-workflow` guidanceへ次を追加します。

- テスト対象資料の事実・鮮度・更新 → `test-target-inspection`
- TC手順 / 期待結果自体の問題 → `test-case-design`
- TC実行・実測・判定・cleanup → `test-execution`
- Playwright runner条件 / raw結果 → `e2e-test-execution`
- Playwright異常の原因分析 → `e2e-test-result-analysis`

実装観測と仕様根拠が矛盾しても、現在有効な仕様根拠が明確なら`test-target-inspection`で仕様を変更せず、不一致事実として後続へ渡します。どの仕様が有効か不明、仕様根拠同士が競合、期待結果の意味を確定できない場合だけ`question-analysis`または`spec-analysis`へ戻します。

`question-analysis`の再開先へ、一般的なテスト対象資料・実対象事実の変更では`test-target-inspection`、汎用TC実行の再開では`test-execution`を追加します。Playwright固有の事実・実行・原因分析は既存E2E Skillへ戻します。

## 9. 変更伝播

### テスト対象資料だけ更新された場合

資料の変更が仕様根拠やTCの意味変更を示さない限り、既存テスト設計を自動で`要再検証`にしません。

ただし、更新により次が判明した場合は影響する担当Skillへ戻します。

- TC手順が実行不能
- 観測方法が成立しない
- 前提条件が実対象に存在しない
- 実装差分と仕様の競合が見つかった

### TCが変更された場合

既存の`test-execution`結果は、期待結果または手順へ影響するTC変更があれば`要再検証`として扱います。古いTC結果を新しいTCのPASS証拠として再利用しません。TC Machine Entityの`content_fingerprint`等、既存の内容同一性契約が利用可能ならそれを再利用し、今回独自のhashを追加しません。

### E2E実装が変更された場合

自動実行経路では既存E2E実装 / executionの再検証規則を維持し、必要なrunが更新された後に`test-execution`結果を再評価します。

### 対象version / build・実施環境が変更された場合

既存の`test-execution`結果は履歴として保持しますが、対象version / build、実施環境、role、locale等のTC判定に影響する条件が変わった場合は、その結果を現在のPASS証拠として自動再利用しません。影響がないことを確認できない範囲を`要再検証`として扱います。確認日時だけで現在の対象と同一とみなしません。

## 10. 完了判定

テスト実行を要求したworkflowでは、今回要求されたTC集合が`test-execution`成果物上で`PASS / FAIL / 未実行 / 判定不能`のいずれかへ漏れなく対応していることを確認します。

全TCのPASSをworkflow完了条件にはしません。`FAIL`があっても、要求された実行と必要な報告が完了し、cleanup失敗・未確認、未処理のworkflow上`ブロック中`、`要再検証`が残っていなければworkflowは完了できます。

必須TCが安全条件・権限・環境不足で`未実行`のまま再開待ちであれば`test-execution`をworkflow上`ブロック中`とし、全体を完了にしません。実行開始済みだが必要観測を完了できず`判定不能`になったTCも、要求範囲を閉じる追加対応が残る場合は完了にしません。ユーザーが明示的に実行対象外へ変更したTCは今回要求TC集合から外した根拠を保持します。

実行を要求したTCが理由なく欠落している場合も完了にしません。

`test-target-inspection`についても、今回確認すべき範囲に必要な`未確認`または`確認不能`が残り、要求資料を完成できない場合はworkflowを完了にしません。要求範囲外を`未確認`へ混ぜず、repo由来情報だけで実対象確認済みとして閉じません。永続保存・更新自体がユーザー要求に含まれる場合は、保存先不明、書込不能、安全な差分更新不能、保存後不整合が残る範囲も完了にしません。
