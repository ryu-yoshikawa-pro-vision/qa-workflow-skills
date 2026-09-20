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
- テストケース入力元を識別できる情報。`qa-workflow`成果物、外部成果物、ユーザー直接入力のいずれでもよく、永続参照がない場合は`ユーザー提供 / 永続参照なし`等の明示状態を使用する
- 今回実行を要求されたTC識別子集合または識別可能な実行範囲。各TCは既存TC ID、外部システムの一意識別子等、入力側で既に存在する一意識別子を持つこと
- 実行対象環境を識別できる情報
- 実行方式、または要求と既存実装からTC単位で一意に決められる情報

識別可能な実行範囲で要求された場合は、実行開始前に現在の詳細テストケース入力から具体的なTC識別子集合へ解決し、今回の実行母集団として固定します。`test-execution`自身は正式TC IDを新規採番しません。単一TCでも入力側の一意識別子が必要です。今回の`TC識別子`は実行入力上の識別子であり、既存E2E成果物の`TC ID`とは別契約です。外部IDを既存E2Eの`TC ID`欄へ変換して書き込まず、既存`TC → E2E実装`対応が`TC ID`を持つ場合は、今回識別子と既存TC IDが同一TCを指すことを確認します。複数TCを一意に識別できない場合は該当範囲を実行開始前にブロックします。

実行開始後は今回のTC識別子集合を不変とし、母集団を暗黙にも明示要求への追随でも書き換えません。ユーザーが開始後にTC追加・除外または実行方式変更を求めた場合は、元成果物へ上書きせず別の`test-execution`成果物 / versionとして開始します。元成果物は開始時に固定した集合と途中までの結果を履歴として保持します。

詳細テストケースには少なくとも、実行に必要な前提条件・手順・期待結果が存在することを確認します。TCに`事後状態 / 後処理`が定義されている場合も実行契約として扱います。`qa-workflow`内で期待結果を設計・変更する責任は`test-case-design`に残します。一方、外部成果物やユーザー直接入力で既に明示された期待結果は今回のTC実行契約としてそのまま利用できますが、`SPEC`や製品期待挙動の正本へ自動昇格しません。期待結果が欠落・曖昧・矛盾している場合は自力で補完せず、`test-case-design`または`question-analysis`へ戻します。

テストケース入力元のrevisionまたは内容同一性情報は、利用可能な場合に記録します。PR #11等によりTC Machine Entityの`content_fingerprint`が既存契約として利用可能なら再利用し、`test-execution`専用のhash機構を追加しません。外部成果物やユーザー直接入力で内容同一性情報が存在しなくても今回の実行自体は可能ですが、`未提供 / 未確認`として記録し、後からcurrentな実行証拠として再利用する際はTC内容の鮮度を別途確認します。永続参照のない入力を履歴再利用の根拠として自動昇格させません。

### 現スコープの実行方式

正規値は次の2つにします。

- `AI直接操作`
- `自動実行`

`AI直接操作`は、利用可能なbrowser / computer操作能力を使ってAIが実対象UI上でTC手順を実施・観測できる場合の方式です。

`自動実行`は、既存Playwright E2Eを`e2e-test-execution`で実行して得た検証済み実行結果を利用し、TCの期待結果と実測結果を対応付ける方式です。本変更ではAPI / DB等の専用runnerや新しい実行方式を追加しません。

「自動実行」を理由に`test-execution`自身がPlaywright commandを直接組み立てません。

実行方式はTC単位で決めます。ユーザーが方式を指定した場合はその指定を優先します。指定がなく、currentな`TC → E2E実装`対応があり、そのE2EがTC判定に必要な期待結果を十分検証していることをcurrentなE2E実装成果物・有効なreview結果等から確認でき、今回の対象環境で安全に実行できる場合にだけ`自動実行`を使用します。それ以外でAI直接操作が安全に成立する場合は`AI直接操作`を使用します。

`自動実行`を選ぶための`TC → E2E実装`対応が欠落・陳腐化している場合は、repoから対応を推測せず既存`coverage-analysis`（対象: `TC → E2E実装`）へ戻します。対応先E2EがTCの期待結果を十分検証しているか確認できない場合は`adversarial-review`（対象: `E2E実装`）へ戻します。十分な検証のためにE2Eコード変更が必要でも、ユーザー要求または現在のworkflow範囲にコード実装・更新が含まれる場合だけ`e2e-test-implementation`へ進みます。実行だけが要求されている場合はコード変更を暗黙許可せず、必要なE2E実装変更を理由に該当範囲を`ブロック中`とします。ユーザーが`自動実行`を明示した場合も勝手にAI直接操作へ切り替えません。どちらの方式も成立しないTCは開始しません。同一成果物内で両方式を混在できます。

混在時は`test-execution`が固定TC識別子集合と各TCの実行方式を正本として保持します。AI直接操作subsetは`test-execution`自身が実施し、自動実行subsetだけを`e2e-test-execution`へ委譲します。委譲中は`test-execution`を未完了のまま保持し、runner結果または必要な`e2e-test-result-analysis`が揃った後に同じ`test-execution`へ再開して未処理subsetと全TC結果を統合します。TCごとの開始状態・cleanupを満たせる限りsubset間の固定実行順序は設けませんが、同じTC識別子を複数方式で暗黙に実行しません。

`自動実行`を実施した後に、失敗回避やPASS取得を目的として同じTCを自動的に`AI直接操作`で再実行しません。方式変更による再実行は、ユーザー要求または明示した診断目的がある場合だけ別実行として扱います。

ユーザーが今回の新規実行を要求している場合、過去の`test-execution`成果物だけで実行済み扱いにしません。過去結果の確認・分析・報告だけが要求されている場合は、既存成果物を再利用できます。

## 3. AI直接操作の実行契約

`references/guidance.md`で次の順序を固定します。

1. 対象TC、対象環境、URL / originを確認する
2. 使用するアカウント / role、認証方法、開始状態、テストデータ、TCに定義された事後状態 / 後処理を確認する
3. TC自身の後処理とは別に、実行時に発生させる副作用について許可範囲と最大回数を確認し、必要な安全cleanup対象 / 方法を確認する。副作用なしの場合も明示する。再試行も最大回数へ含め、実際の実施回数を記録する
4. browser / computer操作能力が対象操作を実施できるか確認する
5. 必須の安全条件を確認できないTCは実行を開始せず`未実行`とし、必要な条件が解消するまで該当範囲をworkflow上`ブロック中`とする
6. TCごとに開始状態を再確認し、前TCが残した状態を暗黙前提にしない
7. TCの手順順序を維持して操作する。副作用操作の結果が不明な場合は、対象状態を確認してから再試行可否を判断し、結果を確認できないまま同じ操作を盲目的に繰り返さない。安全に状態確認できず重複副作用の可能性が残る場合は`判定不能`または必要範囲をworkflow上`ブロック中`として停止する
8. TCが要求する観測点で実測結果を取得する
9. 期待結果と実測結果を比較する。期待結果との不一致が確定し、その後の手順前提が成立しない場合は無理に後続操作を続けない
10. TC単位の状態を確定する
11. TCに定義された事後状態 / 後処理を実施・確認する。実行時cleanupと重なる処理を二重実行しない
12. 必要な実行時cleanupと残存状態をTC判定とは別に確認する
13. 実在する場合だけ証跡参照を記録し、未確認事項を記録する

TC手順にない探索的な操作を、PASSを得るために追加しません。診断目的の追加操作が必要な場合は正式TC実行と区別します。

## 4. 自動実行の実行契約

Playwright経路では既存Skillを利用します。

```text
新しいTC実行要求
  ↓
test-execution
  ↓ TC識別子集合・実行方式を固定
自動実行subset
  ↓ currentな今回runがない
e2e-test-execution
  ├─ 正常run ─────────────────→ test-executionへ再開
  └─ 異常 / 未実行 / run-level error / cleanup問題
        ↓
     e2e-test-result-analysis
        ├─ 追加実行不要 ───────→ test-executionへ再開
        └─ 追加実行必要
             ↓
          e2e-test-execution
             ↓
          既存E2E異常routingを再適用
```

既存`e2e-test-execution` / `qa-workflow`のrouting契約を維持します。異常、未実行、run-level error、cleanup失敗 / 未確認を、本変更だけを理由に`e2e-test-result-analysis`から迂回させません。

`test-execution`が利用するのは、`e2e-test-execution`が検証済みとして記録したrunner事実と、異常経路では`e2e-test-result-analysis`の分析結果です。自動実行結果をTC判定へ使用する前に、TC実行要求の対象条件と`e2e-test-execution`が記録した対象URL / origin、Playwright project、必要なrole / 認証条件、テストデータ / 開始状態、version / build等のうちTC判定へ影響する項目が一致するか、差異が結果へ影響しないことを確認します。取得不能な値は推測せず制約として残します。

自動実行subsetを委譲する前に、TCごとの対応から必要なlogical primaryを解決します。複数TCが同じlogical primaryへ対応する場合、`test-execution`の追跡表では各TCとの対応を保持しますが、1つの`e2e-test-execution`へ渡すlogical primary集合は一意化し、同じlogical primaryをTC数だけ重複実行しません。また、対象URL / origin、Playwright project、role / 認証、開始状態 / テストデータ、setup、許可する副作用、cleanup等を同一runで両立できないTCは、安全に同一preflight契約を共有できる最小限の集合へ分け、複数の`e2e-test-execution`成果物として実行します。新しいbatch runnerやrun registryは追加しません。

`e2e-test-result-analysis`が不足証拠の取得を目的に追加runを要求した場合は、そのrunが正式TC実行条件を維持した再実行か、診断目的で条件を変えたrunかを区別します。診断runは原因分析の証拠として参照できますが、診断runだけで正式TC結果をPASSへ置き換えません。TC判定へ使うrunは今回TCの正式実行条件へ適用可能であることを確認します。

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

runner異常、認証失敗、setup failure等により対象TC自体が開始されていない場合はTCを`未実行`とし、再開に必要な条件が未解決ならSkill / workflowを`ブロック中`として扱います。対象TCは開始されたが必要な期待結果を観測できずPASS / FAILを確定できない場合は`判定不能`とします。cleanup問題は確定済みTC結果を書き換えず、cleanup状態とSkill / workflow完了条件へ反映します。

assertion結果等から期待結果と実測結果の差を確認できる場合だけ、TCの`FAIL`判定へ利用します。Playwrightの`failed`というstatusだけを根拠に製品期待結果の不一致と断定しません。run全体PASS、`TestCase.outcome() = expected`、最終retry PASSも単独ではTCの`PASS`根拠にしません。

自動実行では、最低限`今回TC識別子 → 既存TC ID（存在時のみ） → E2E実装参照 → logical primary → E2E実行成果物参照 → resolved primary TestCase → 実行結果 / 観測証拠`を辿れることを要求します。既存`TC → E2E実装`対応を利用する場合は、その対応が参照する既存TC IDと今回TC識別子が同一TCを指すことを確認し、外部IDを既存TC IDとして書き換えません。実行開始前に、固定した今回TC識別子集合の自動実行subsetから今回必要なE2E実装参照とlogical primaryを解決し、各`e2e-test-execution`へ渡すlogical primary集合を一意化します。1 TCが複数のE2E実装 / resolved primaryへ対応する場合も、TCの期待結果を判定するために必要な対応先をすべて確認します。dependency / teardown等のrunner上必要な実行は既存契約へ委ねますが、要求外のprimary testを「ついでに」追加しません。runner入口の制約で追加primaryが避けられない場合は、その実行範囲と副作用を開始前に確認します。retry attemptは別TCとして数えません。既存`TC → E2E実装`対応がある場合はそれを正本として再利用し、raw結果側の任意TC IDだけに依存しません。

TCを`PASS`にするには、currentなE2E実装がそのTCのPASS判定に必要な期待結果を検証していることを、現在有効なE2E実装成果物、`adversarial-review`（対象: `E2E実装`）の結果、または同等の確認済み事実から確認できることを要求します。根拠は対象E2E実装参照だけでなく、その判断対象となったE2E実装revision / working treeへ追跡できるようにします。`adversarial-review`を根拠に使う場合は、review成果物がどのE2E実装revision / working treeを対象にしたか追跡でき、現在の実装変更後に`要再検証`が残っていない等、そのreviewがcurrentなE2E実装へ適用できることを確認します。現行`adversarial-review`成果物だけでこの対応を再現できない場合は、E2E実装review時の対象revision / working treeを記録する最小の出力契約を追加します。単体`test-execution`でreview鮮度を確認できない場合は、古いreviewだけをPASS根拠にせず現在のE2E実装を再reviewします。runがPASSでも必要な期待結果の検証またはreview鮮度を確認できない場合はTCを`判定不能`とします。期待結果専用の新しいID体系やcoverage用途は追加しません。

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

TCに定義された`事後状態 / 後処理`と、実行時の安全cleanupはTC結果と別軸です。TCの期待結果をすべて満たした後で後処理またはcleanupに失敗した場合、TC結果は`PASS`のまま保持し、残存状態により`test-execution` / workflowを完了させません。元TCの後処理と実行時cleanupが同じ処理を要求する場合は一度だけ実施し、どちらの契約を満たしたか追跡します。Playwright runner管理cleanupは`e2e-test-execution`の既存責務を維持します。

## 6. 出力Asset

`skills/test-execution/assets/output-template.md`を正規出力として追加します。

### 実行情報

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 |  |  |
| テストケース入力元 / 成果物参照 |  |  |
| TC revision / content identity |  |  |
| 今回の実行対象TC識別子集合 |  |  |
| 環境 / URL / origin |  |  |
| 実施環境 / 対象条件 |  |  |
| version / build ID |  |  |
| 実行日時 |  |  |
| 実行方式概要 | AI直接操作 / 自動実行 / 混在 |  |
| repo revision / E2E code revision |  |  |
| テスト対象資料参照 |  |  |

テスト対象資料を利用していない場合は`未使用`等の明示状態を使用します。`TC revision / content identity`を取得できない場合は空欄にせず`未提供 / 未確認`等を記録します。

### AI直接操作の実行前条件

AI直接操作を使用するTCだけ記録します。

| TC識別子 | origin | アカウント / role | 開始状態 / テストデータ | 副作用の許可範囲 | 最大回数 | 安全cleanup対象 / 方法 | 確認結果 |
| --- | --- | --- | --- | --- | ---: | --- | --- |

必須条件を確認できないTCは操作を開始せず`未実行`とします。この表はPlaywright runnerのpreflightを複製するものではありません。

### AI直接操作の副作用実績

副作用操作を実施したAI直接操作TCだけ記録します。再試行も`実施回数`へ含めます。

| TC識別子 | 操作 | 最大回数 | 実施回数 | 実施結果 | 残存状態 / 備考 |
| --- | --- | ---: | ---: | --- | --- |

`実施回数`が`最大回数`を超えた成果物は契約違反として完成扱いしません。

### TC実行結果

| TC識別子 | 実行方式 | 状態 | 期待結果 | 実測結果 | 判定根拠 | 実行結果参照 / 証跡 |
| --- | --- | --- | --- | --- | --- | --- |

実行方式の正本はTC実行結果表の`実行方式`列とし、複数方式が混在してもrun全体に1方式を強制しません。`TC revision / content identity`は既存のrevision / fingerprint契約を優先し、独自hashを新設しません。

自動実行を利用する場合は次の対応表も出力します。実行開始前に解決した今回のE2E実装参照 / logical primary集合と、実際にresolved / 実行されたprimaryを比較できるようにします。

### 自動実行対応

| TC識別子 | 既存TC ID（存在時のみ） | E2E実装参照 | E2E実装revision / working tree | logical primary | E2E実行成果物参照 | resolved primary TestCase | 利用区分 | 期待結果検証根拠 | 実行結果 / 観測証拠 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 手順・観測結果

| TC識別子 | 手順 / 観測点 | 操作 | 期待結果 | 実測結果 | 状態 / 備考 |
| --- | --- | --- | --- | --- | --- |

全TCで全手順を冗長に複製することを目的にしません。ただしPASS / FAIL判定や再現に必要な観測点は追跡できるようにします。

### 未実行・判定不能

| TC識別子 | 状態 | 理由 | 必要な情報 / 対応 | 再開先 |
| --- | --- | --- | --- | --- |

`状態`は`未実行 / 判定不能`だけを使用します。Skill / workflow上の`ブロック中`はこの表へTC結果として混ぜません。

### TC事後状態・後処理

| TC識別子 | 事後状態 / 後処理 | 実施結果 | 残存状態 | 根拠 |
| --- | --- | --- | --- | --- |

元TCに定義がない場合は`対象なし`とします。実行時cleanupと同じ処理を二重実行しません。

### 実行時cleanup・残存状態

| 対象 | 状態 | 内容 | 根拠 |
| --- | --- | --- | --- |

実行時cleanupの成功 / 失敗 / 未確認はTCのPASS / FAILと独立して記録します。Playwright runner管理cleanupは`e2e-test-execution`成果物を正本とします。

### 集計

| 状態 | 件数 |
| --- | ---: |
| PASS |  |
| FAIL |  |
| 未実行 |  |
| 判定不能 |  |

集計は実行開始前に固定した今回のTC識別子集合を母集団としてTC単位で行い、自動実行のretry attempt数をTC件数へ加算しません。結果表から要求TCが欠落している、要求外TCが混入している、または同じTC識別子が複数方式で暗黙に重複実行されている場合は成果物を完成扱いしません。

永続的な証跡参照が存在しないAI直接操作では架空のURL / artifact参照を作りません。`実測結果`と`判定根拠`は必須とし、`実行結果参照 / 証跡`は実在する参照がある場合だけ記録します。TC判定に不要な個人データ・機密情報を成果物や証跡へ転載しません。

`自動実行対応`の`利用区分`は`TC判定`または`診断のみ`とし、診断runを正式TC判定の唯一の根拠にしません。複数の`e2e-test-execution`へ分割した場合も、各TCがどのE2E実行成果物へ対応したか追跡できるようにします。

### 最終出力の自己検証

最終出力前に`SKILL.md` / guidanceの出力契約を成果物自身へ再適用します。少なくとも、開始前に固定したTC識別子集合とTC実行結果表の集合が一致し、欠落・要求外・不正重複がないこと、実行方式と結果状態が正規値であること、自動実行TCが既存TC ID（存在時のみ）・E2E実装・E2E実行成果物・logical / resolved primary・期待結果検証根拠へ追跡できること、診断runだけを正式結果へ昇格していないこと、後処理 / cleanup状態をTC結果へ混ぜていないことを確認します。明白かつ局所的で新しい領域判断を必要としない契約違反だけを最大1回修正し、TC、期待結果、対応E2E、実測結果を推測で補完しません。`evals/deterministic/validator.py`はruntimeで呼び出さず評価専用とします。

### 既存実行結果の再利用

過去の`test-execution`成果物は履歴事実として保持します。今回の新規実行要求を過去結果で代替しません。過去結果の確認・分析・報告、または現在の判断材料として再利用する場合は、元TC内容、対象version / build、実施環境 / 対象条件、自動実行ではE2E実装と対応runが今回の判断へ適用可能か確認します。変更や不明点があれば古い結果をcurrentなPASS証拠にせず`要再検証`として扱います。履歴成果物自体を書き換えません。

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
- `skills/adversarial-review/SKILL.md` / `references/guidance.md` / `assets/output-template.md` / 関連eval（E2E実装review時に対象E2E実装revision / working treeを追跡できる最小変更）

`e2e-test-execution` / `e2e-test-result-analysis`の既存異常routingは変更しません。TC判定に必要なtrace情報が既存成果物で不足することを実装時に確認した場合だけ、既存raw result contractを壊さない最小の参照情報を追加します。
