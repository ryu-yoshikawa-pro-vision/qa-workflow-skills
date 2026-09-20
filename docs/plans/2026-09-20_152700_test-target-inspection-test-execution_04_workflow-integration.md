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
       ↓ 必要TC / E2E実装参照を返す   │
     qa-workflow                     │
       ↓                              │
     e2e-test-execution              │
       ↓ 異常時                       │
     e2e-test-result-analysis         │
       ↓                              │
     qa-workflow                     │
       ↓                              │
     test-executionへ再開 ←───────────┘
       ↓
     全TC結果を統合
```

テスト対象資料は利用可能なら再利用しますが必須依存にしません。AI直接操作だけ、自動実行だけの場合も同じ`test-execution`契約の部分集合として扱います。混在時は`test-execution`を未完了のまま保持し、workflow状態表の`成果物 / バージョン`に進行中の`test-execution`成果物参照を保持します。自動実行に新しいrunが必要な場合、`test-execution`は必要TCと既存E2E実装参照を返し、`qa-workflow`が`e2e-test-execution`へroutingします。Playwright側で追加runが必要になっても、`test-execution`自身はrun分割や再routingを管理しません。返却されたE2E成果物は`qa-workflow`が同じ`test-execution`へ戻して統合します。同じTC識別子を複数方式で暗黙に実行せず、新しいexecution IDやrun registryも追加しません。

### 自動化済みTCだけを実行してTC結果を確認

自動実行だけの場合も、TC単位の結果判定を要求しているなら`test-execution`から開始して固定TC識別子集合と方式を確定します。

```text
詳細TC
  ↓
test-execution
  ↓ currentなTC → E2E実装対応と自動実行subsetを確定
currentな今回runがない
  ↓
e2e-test-execution
  ├─ 正常run ─────────────────→ test-executionへ再開
  └─ 異常 / 未実行 / run-level error / cleanup失敗・未確認
        ↓
     e2e-test-result-analysis
        ├─ 追加実行不要 ───────→ test-executionへ再開
        └─ 追加実行必要 → e2e-test-execution → 既存E2E異常routingを再適用
```

`test-execution`はPlaywright raw statusを作り直さず、検証済み入力をTCの期待結果と対応付けます。現行`e2e-test-execution` / `qa-workflow`の異常routingを維持し、本変更だけを理由に`e2e-test-result-analysis`を省略しません。過去結果の確認だけを要求されている場合は新しいrunner実行を強制しません。

`qa-workflow`管理下のTCで自動実行開始前にcurrentな`TC → E2E実装`対応が欠落・陳腐化している場合は`qa-workflow`が`coverage-analysis`（対象: `TC → E2E実装`）へroutingします。外部 / ユーザー直接入力TCでは内部QA成果物へ自動変換せず、入力元・ユーザーからE2E実装参照との対応を確認できなければ自動実行対象をブロックします。対応E2Eの期待結果検証が不足・不明な場合は`qa-workflow`が必要に応じて`adversarial-review`（対象: `E2E実装`）へroutingします。E2Eコード変更が必要でも、ユーザー要求またはworkflow範囲に実装・更新が含まれない場合は`e2e-test-implementation`へ暗黙routingせず、`test-execution`の該当範囲を`ブロック中`とします。

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

再利用時は成果物全体の更新日時や成果物上部の今回version / buildだけでcurrentと判断せず、今回利用する対象・要素・状態・遷移等の各行がどの確認元・確認version / build・確認日時 / revision・確認条件に基づくか確認します。部分更新で`既存資料から継承・未再確認`となった行は、その行を実際に確認したversion / build・revision・確認条件を正本とします。repo由来事実はbranch / commitだけでなくworking tree状態も確認し、未commit変更に依存した事実をHEADだけでcurrentとみなしません。version / build変更時は関連範囲への影響を確認し、影響不明な範囲だけ`test-target-inspection`へ戻します。同一buildでも、今回利用する事実へ影響するrole / 権限、viewport、locale、feature flag、テストデータ等の確認条件が異なる場合は、差異が該当事実へ影響しないことを確認できる範囲だけ再利用します。

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
- `e2e-test-execution`が今回のE2E実行要求から解決したlogical primary対象
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

自動実行の対応は`今回TC識別子 → 既存TC ID（存在時のみ） → E2E実装参照 → E2E実行成果物参照 → logical primary → resolved primary TestCase → 実行結果 / 観測証拠`を辿れるようにします。既存`TC → E2E実装`対応を使う場合は、その既存TC IDと今回TC識別子が同一TCを指すことを確認し、外部IDを既存TC IDへ書き換えません。`test-execution`は今回TCとE2E実装参照の対応までを正本として保持し、logical / resolved primary、project、preflight、要求外primary、dependency / teardown、run分割は`e2e-test-execution`が返す既存成果物を正本とします。`qa-workflow`はその成果物を同じ`test-execution`へ戻します。

run全体PASS、`outcome=expected`、最終retry PASSだけではTCの`PASS`にしません。新しいrunner実行を開始する場合は、currentなE2E実装がPASS判定に必要な期待結果を検証していることを実行前に確認し、確認できなければrunnerを起動せず`未実行`として必要なroutingへ戻します。既存runを後からTC判定へ利用する場合に十分性を確認できなければ`判定不能`とします。`adversarial-review`を根拠にする場合は`qa-workflow`上の`要再検証`が残っていない等、現在TC / E2Eへ適用できることを確認し、鮮度を証明できなければ現在対象を再reviewします。`adversarial-review`へ`test-execution`専用のrevision / working tree schemaは追加しません。

`e2e-test-result-analysis`から追加runへ進む場合は、正式TC条件を維持する再実行と診断runを区別します。診断runは原因分析の証拠として利用できますが、それだけで正式TC結果をPASSへ変更しません。

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

`qa-workflow`が`test-execution`から他Skillへroutingしている間もworkflow状態は`実行中`のままにし、`成果物 / バージョン`には開始時に固定したTC集合を持つ進行中成果物を保持します。委譲先から戻った結果は`qa-workflow`がその成果物へ統合するため再開します。開始後のTC追加・除外または方式変更は同じ成果物を書き換えず、旧成果物の未開始 / 未完了TCを理由付きで閉じて必要なcleanupを終えた後、別の`test-execution`成果物 / versionとして開始します。


## 8. 修正routing

`qa-workflow` guidanceへ次を追加します。

- テスト対象資料の事実・鮮度・更新 → `test-target-inspection`
- TC手順 / 期待結果自体の問題 → `test-case-design`
- TC実行・実測・判定・cleanup → `test-execution`
- `qa-workflow`管理下のTC → E2E実装追跡の欠落・陳腐化 → `coverage-analysis`（対象: `TC → E2E実装`）。外部 / 直接入力TCは内部成果物へ自動取込せず、明示要求がある場合だけ既存設計workflowへrouting
- E2E実装がTCの必要な期待結果を検証しているかのreview → `adversarial-review`（対象: `E2E実装`）
- E2Eコード変更 → ユーザー要求 / workflow範囲に実装・更新が含まれる場合だけ`e2e-test-implementation`
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

既存の`test-execution`結果は、期待結果または手順へ影響するTC変更があれば`要再検証`として扱います。古いTC結果を新しいTCのPASS証拠として再利用しません。進行中の`test-execution`に対してTC追加・除外または方式変更が発生した場合も開始時の固定TC集合を書き換えません。旧成果物は変更要求時点の状態を保持し、未開始TCは`未実行`、開始済みだが判定前なら必要に応じて`判定不能`として理由を残し、必要なcleanup後に履歴として閉じます。その後、変更後の要求を別の`test-execution`成果物 / versionとして開始します。TC Machine Entityの`content_fingerprint`等、既存の内容同一性契約が利用可能ならそれを再利用し、今回独自のhashを追加しません。

### E2E実装が変更された場合

自動実行経路では既存E2E実装 / executionの再検証規則を維持し、必要なrunが更新された後に`test-execution`結果を再評価します。

### 対象version / build・実施環境が変更された場合

既存の`test-execution`結果は履歴として保持しますが、対象version / build、実施環境、role、locale等のTC判定に影響する条件が変わった場合は、その結果を現在のPASS証拠として自動再利用しません。影響がないことを確認できない範囲を`要再検証`として扱います。確認日時だけで現在の対象と同一とみなしません。

## 10. 完了判定

テスト実行を要求したworkflowでは、今回要求されたTC集合が`test-execution`成果物上で`PASS / FAIL / 未実行 / 判定不能`のいずれかへ漏れなく対応していることを確認します。

全TCのPASSをworkflow完了条件にはしません。`FAIL`があっても、要求された実行と必要な報告が完了し、cleanup失敗・未確認、未処理のworkflow上`ブロック中`、`要再検証`が残っていなければworkflowは完了できます。

必須TCが安全条件・権限・環境不足で`未実行`のまま再開待ちであれば`test-execution`をworkflow上`ブロック中`とし、全体を完了にしません。実行開始済みだが必要観測を完了できず`判定不能`になったTCも、要求範囲を閉じる追加対応が残る場合は完了にしません。開始後にユーザーが実行対象の追加・除外や方式変更を求めた場合、現在成果物の固定TC集合は変更せず、その変更要求を別の`test-execution`として扱います。

実行を要求したTCが理由なく欠落している場合も完了にしません。

`test-target-inspection`についても、今回確認すべき範囲に必要な`未確認`または`確認不能`が残り、要求資料を完成できない場合はworkflowを完了にしません。要求範囲外を`未確認`へ混ぜず、repo由来情報だけで実対象確認済みとして閉じません。永続保存・更新自体がユーザー要求に含まれる場合は、保存先不明、書込不能、安全な差分更新不能、保存後不整合が残る範囲も完了にしません。
