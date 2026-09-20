# テスト対象資料管理・テスト実行Skill追加Plan

## 1. 追加ファイル

```text
skills/test-execution/
├── SKILL.md
├── references/
│   └── guidance.md
├── assets/
│   ├── execution-plan-template.yaml
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

新しいbrowser automation frameworkは追加しません。

## 2. `SKILL.md`契約

`test-execution`の目的は、**人間が手動テストで操作するのと同じようにAIが実対象を操作し、詳細TCを実施して、その結果を報告すること**です。

単に既存の自動実行結果を集約するSkillにはしません。今回の実行要求では、AI自身が現在の実対象に対して操作・観測を行うことを基本とします。

### 必須入力

- 実行対象の詳細テストケース
- テストケース入力元を識別できる情報
- 今回実行するTC識別子集合または識別可能な実行範囲
- 実行対象環境を識別できる情報
- 実対象へ到達するためのURL / 入口または同等情報
- 利用可能な実行手段

TCは`qa-workflow`成果物、外部成果物、ユーザー直接入力のいずれでもよいものとします。

1つの`test-execution`成果物では1つのTC入力元 / snapshotを扱います。今回のTC識別子は入力側ですでに存在する一意識別子を使用し、正式TC IDを新規採番しません。

外部 / 直接入力TCの期待結果が不足・曖昧な場合は、実測に合わせて補完しません。入力元・ユーザーから解消できなければ該当TCを開始しません。

## 3. Given / When / Then構造の実行前YAML

実対象への操作を開始する前に、固定した各TCをGherkinの`Given / When / Then`構造へ整理し、YAMLとして保持します。

これはGherkin / Cucumberの新しい標準形式を定義するものではありません。元TCをAIが実行可能な形へ整理し、曖昧な前提・操作・期待結果・観測方法を操作開始前に表面化させるための中間成果物です。元TCを正本とし、YAMLは元TCの意味を追加・削除・変更しません。

`skills/test-execution/assets/execution-plan-template.yaml`は次の最小構造を持たせます。

```yaml
test_case_id: TC-001
title: 正しい認証情報でログインできる
scenario:
  given:
    - 未ログイン状態でログイン画面を表示している
    - 有効なテストユーザーが存在する
  when:
    - メールアドレスとパスワードを入力してログインする
  then:
    - expected: ダッシュボードが表示される
      observation:
        - accessibility_tree
        - image
unresolved: []
cleanup: []
```

契約は次のとおりです。

- `test_case_id`: 入力側ですでに存在するTC識別子をそのまま使う
- `title`: 元TCに存在する名称または意味を変えない短い表現
- `scenario.given`: 実行開始状態、前提条件、role、必要なテストデータ等を元TCから整理する
- `scenario.when`: AIが実施する操作を元TCの順序・意味を維持して整理する
- `scenario.then`: 期待結果と、その確認に必要な観測方法を整理する
- `unresolved`: 実行または合否判定に影響する未解決事項だけを列挙する。ない場合は空配列にする
- `cleanup`: 元TCまたは安全条件で必要な後処理だけを記録する。対象なしなら空配列にする

`observation`は今回の期待結果を確認する方法を示します。DOM / accessibility tree / image / Playwright assertion等、実際に利用可能な観測方法を記録し、元TCが視覚状態を要求する場合は必要に応じて`image`を含めます。観測方法を選べないこと自体が合否判定へ影響する場合は`unresolved`へ残します。

### 曖昧さの扱い

次のいずれかが実行または判定に必要なのに元TC・既存成果物・ユーザー提供情報から確定できない場合は、推測で埋めず`unresolved`へ記録します。

- 開始状態 / 前提条件
- 操作対象または操作内容
- 操作順序
- 期待結果
- PASS / FAILに必要な観測方法
- 安全に実行するための副作用条件 / cleanup

`unresolved`が空でないTCは実対象への操作を開始せず`未実行`とし、何を解消すれば開始できるかを報告します。他のTCを安全に実行できる場合は継続します。

曖昧さが実行や合否判定へ影響しない補足情報であれば、実行を止めるためだけに`unresolved`へ追加しません。

### 変換時に禁止すること

- 元TCにない期待結果を追加する
- 「正常に」「適切に」等の曖昧な期待結果を独自判断で具体化する
- 元TCにないテストデータ、role、アカウント、URLを推測する
- PASSを得やすくするために操作順序やUI経路を変更する
- YAMLを仕様Authorityまたは新しいTC正本として扱う
- YAML化を理由に正式TC ID、step ID、expectation ID等の新しい共通ID体系を追加する

今回の目的に不要な`Feature`、`Background`、`Scenario Outline`、`Examples`、tag等のGherkin / Cucumber全構文は実装しません。

## 4. 実行手段

実行手段はTCの属性ではなく、AIが今回の実対象を操作・観測するための手段です。

### Playwright MCP等の対話操作

利用可能でTCを実施できる場合は、Playwright MCP等の対話的なbrowser操作を基本にします。

AIはTCの手順に沿って、画面を確認しながら1操作ずつ進めます。

- navigation
- click
- input
- selection
- keyboard操作
- modal / popup等の操作
- 状態変化待機
- DOM / accessibility tree等の確認
- screenshot取得と画像確認

特定のtool名へSkill契約を固定せず、利用可能なbrowser / computer操作能力のうち、人間の操作に相当するUI操作を実施できる手段を使用します。Playwright MCPが利用可能な環境では優先的な実行手段として扱います。

### Playwright CLI / Playwrightコード

対話操作だけでは安定して実施できない場合、または現在TCの実行にコードが適する場合はPlaywright CLI / Playwrightコードを使用できます。

今回の実行だけに必要な一時的コードは`test-execution`内で生成・実行できます。

例:

- 複数データで同じ操作を繰り返す
- 一定の待機・観測を安定させる
- screenshotや必要なUI状態を取得する
- 対話操作では再現しにくい手順を今回TC用に実行する

一時コードは今回runの実行手段であり、将来の回帰テスト資産へ自動昇格させません。repoの保守対象E2Eとして残す場合は`qa-workflow`経由で`e2e-test-inspection` / `e2e-test-implementation`へroutingします。

既存 / 実装済みrepo E2Eを正式なrunner契約で実行する場合は、既存`e2e-test-execution`を使用できます。その場合も、最終的なTC単位の結果報告が要求されているなら`test-execution`へ結果を戻して報告します。

## 5. 人間の手動テスト相当の実行契約

`references/guidance.md`では次の流れを基本とします。

1. 今回実行するTC集合を固定する
2. 各TCの前提条件、手順、期待結果、事後状態 / 後処理をGiven / When / Then構造のYAMLへ整理する
3. YAMLの`unresolved`を確認し、実行または合否判定に影響する未解決事項があるTCは操作を開始せず`未実行`とする
4. 対象環境、URL / origin、role / アカウント、認証、テストデータ、開始状態を確認する
5. 副作用scope、最大回数、cleanup対象 / 方法を確認する
6. TCごとに開始状態を確認する
7. 人間がTCを実施するのと同じUI経路でYAMLの`scenario.when`を実施する
8. 各`scenario.then`の観測方法に従い、DOM / accessibility tree等から取得できる構造・意味情報を確認する
9. 視覚確認が必要な観測点ではscreenshot等を取得し、画像として確認する
10. 期待結果と実測結果を比較する
11. 後続手順の前提が崩れた場合は、PASSを得るために別経路へ勝手に迂回しない
12. TC結果を確定する
13. TCに定義された事後状態 / 後処理を実施・確認する
14. 実行時cleanupと残存状態を確認する
15. TC結果、実行前YAML、観測、証跡、未実行 / 判定不能理由、cleanupを報告する

TC手順にない探索操作を、PASSを得るために追加しません。診断目的で追加操作する場合は正式TC手順と区別します。

UI操作を避けるためにbackend API / DB等へ直接書き込んでTCを成立させません。TCまたはユーザー要求がAPI / DB操作自体を明示している場合は本Skillの現スコープ外として扱います。

## 6. 画像による判断

画像確認を補助的な証跡だけではなく、必要時の正式な観測手段として扱います。

使用する代表例:

- UI崩れ
- 要素の重なり
- 文字・コンテンツの欠け / はみ出し
- レスポンシブ表示
- 画像・アイコン
- canvas描画
- modal / popupの視覚的状態
- DOM / accessibility treeでは確認できない位置・サイズ・見た目

判定規則:

- TC期待結果が視覚状態を要求する場合は画像観測を判定根拠にできる
- 画像だけでrole、accessible name、ARIA状態等を推測しない
- accessibility固有の期待結果はaccessibility tree / role等の情報を使用する
- 画像と構造情報の両方が必要なら併用する
- 「なんとなくおかしい」だけでTCをFAILにしない
- TC期待結果外で見つけたUI崩れ等は`追加観測`として報告し、元TCの期待結果に関係しない限りTC結果を変更しない

pixel diff専用frameworkや画像差分専用Skillは追加しません。

## 7. TC結果状態

正規状態は次です。

- `PASS`: PASS判定に必要な期待結果をすべて観測し、すべて一致した
- `FAIL`: 有効な期待結果との不一致を1つ以上実測した
- `未実行`: TCの実行自体を開始していない
- `判定不能`: 実行は開始したが、必要な観測を完了できずPASS / FAILを確定できない

`ブロック中`はTC結果ではなくworkflow状態です。

1つ以上の期待結果で不一致を確認した場合は`FAIL`とします。後続操作が不能になって未観測項目が残っても、確認済みの不一致を`判定不能`へ弱めません。

不一致はないがPASSに必要な観測を完了できない場合は`判定不能`です。

## 8. 副作用・cleanup

副作用の最大回数は、ユーザーが許可した操作scope全体で管理します。同じscopeを複数TCが共有してもTCごとに上限をリセットしません。

結果不明な副作用操作は、状態確認なしに盲目的再試行しません。

次を分離します。

- TCに定義された事後状態 / 後処理
- 今回のAI操作に伴う実行時cleanup
- 既存repo E2Eを`e2e-test-execution`で動かした場合のrunner管理cleanup

cleanup失敗は確定済みTC結果を自動でFAILへ変更しません。ただし残存状態がある場合は実行報告とworkflow完了状態へ反映します。

## 9. 実行開始後の変更

実行開始後は今回のTC集合を変更しません。

ユーザーが途中でTC追加・除外または実行手段変更を求めた場合:

- 未開始TCは`未実行`として理由を残す
- 開始済みで判定未完了なら必要に応じて`判定不能`として理由を残す
- 必要なcleanupを実施する
- 旧成果物を履歴として閉じる
- 変更後要求は別の`test-execution`成果物 / versionとして開始する

## 10. 出力Asset

`skills/test-execution/assets/output-template.md`を正規出力として追加します。

### 実行情報

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 |  |  |
| テストケース入力元 / 成果物参照 |  |  |
| TC revision / content identity |  |  |
| 今回の実行対象TC識別子集合 |  |  |
| 環境 / URL / origin |  |  |
| version / build ID |  |  |
| role / アカウント |  |  |
| 実行日時 |  |  |
| 使用した実行手段 | Playwright MCP等 / browser操作 / Playwright CLI / 一時Playwrightコード / 既存E2E runner |  |
| テスト対象資料参照 |  |  |

### Given / When / Then構造の実行前YAML

固定した全TCについて、実対象への操作開始前に`execution-plan-template.yaml`と同じ構造で整理します。

元TCの正本参照とTC識別子から追跡できることを必須とします。`unresolved`が空でないTCは、その内容と再開条件を`未実行・判定不能`表にも反映します。

YAMLは最終報告にも含めるか、安全な成果物参照を示し、実行された内容が事前に整理した内容と対応することを確認できるようにします。実行後の観測結果をYAMLの期待結果へ上書きしません。

### 実行前条件

| TC識別子 | 開始状態 / テストデータ | 副作用scope | 最大回数 | cleanup対象 / 方法 | 確認結果 |
| --- | --- | --- | ---: | --- | --- |

### 手順・観測結果

| TC識別子 | 手順 / 観測点 | 操作 | 観測方法 | 期待結果 | 実測結果 | 状態 / 備考 |
| --- | --- | --- | --- | --- | --- | --- |

`観測方法`には必要に応じてDOM / accessibility tree / 画像 / Playwright assertion等を記録します。

全手順を冗長に複製する必要はありませんが、判定・再現に必要な操作と観測は追跡できるようにします。

### 視覚確認

画像を使用したTCだけ記録します。

| TC識別子 | 手順 / 観測点 | 確認観点 | 画像で観測した事実 | 画像参照 | 判定への利用 |
| --- | --- | --- | --- | --- | --- |

安全な画像参照を保持できない場合は、画像そのものを保存せず、確認した観測事実だけを記録できます。

### TC実行結果

| TC識別子 | 状態 | 期待結果 | 実測結果 | 判定根拠 | 証跡参照 |
| --- | --- | --- | --- | --- | --- |

### 未実行・判定不能

| TC識別子 | 状態 | 理由 | 必要な情報 / 対応 | 再開条件 |
| --- | --- | --- | --- | --- |

### 追加観測

TC期待結果とは別に発見したUI崩れや異常がある場合だけ記録します。

| TC識別子 | 観測内容 | 確認方法 | TC結果への影響 | 証跡 |
| --- | --- | --- | --- | --- |

### TC事後状態・後処理

| TC識別子 | 事後状態 / 後処理 | 実施結果 | 残存状態 | 根拠 |
| --- | --- | --- | --- | --- |

### 実行時cleanup・残存状態

| 対象 | 状態 | 内容 | 根拠 |
| --- | --- | --- | --- |

### 集計

| 状態 | 件数 |
| --- | ---: |
| PASS |  |
| FAIL |  |
| 未実行 |  |
| 判定不能 |  |

### 実行結果報告

最終出力は単なる内部成果物ではなく、ユーザーが判断できるテスト実行報告とします。

最低限、次を含みます。

- 実行対象と環境
- 実行したTC
- PASS / FAIL / 未実行 / 判定不能の集計
- FAILの実測内容と再現に必要な情報
- 未実行 / 判定不能理由
- 画像判断を使用した場合の観測内容
- TC外の追加観測
- cleanup / 残存状態
- 残るブロックや再実行条件

## 11. Playwrightコードと既存E2E Skillの境界

### 今回runだけの一時コード

`test-execution`で作成・実行できます。

- 今回TCだけを実施する
- repoの保守対象E2Eへ無断で追加しない
- 将来再利用できる品質へ仕上げることを完了条件にしない
- 実行後に不要な一時ファイルを残さない

### repoへ残すE2Eコード

ユーザー要求またはworkflow範囲に永続的なE2E実装が含まれる場合だけ、`qa-workflow`経由で既存Skillを使用します。

```text
e2e-test-inspection
  ↓
e2e-test-implementation
  ↓
e2e-test-execution
```

### 既存repo E2Eの実行

既存E2Eを正式なrunner契約で実行する場合は`e2e-test-execution`を正本とします。

`test-execution`がTC結果報告まで要求されている場合だけ、その実行結果をTCの期待結果と対応付けて報告します。

## 12. `test-target-inspection`の利用

currentな`test-target-inspection`成果物は任意入力として使用できます。

- 到達経路
- UI要素
- role / accessible name
- 現在の状態・ふるまい
- 非同期条件
- 視覚情報
- データ / 権限依存

資料と実対象が不一致の場合は資料を正として実対象を無視しません。今回の実測を保持し、資料管理が要求範囲に含まれる場合は`qa-workflow`経由で`test-target-inspection`へ更新を戻します。

## 13. `e2e-test-reporting`との境界

`test-execution`は一般的なTC実行結果の報告まで担当します。

`e2e-test-reporting`は、既存repo E2Eのrun / logical primary / resolved TestCase / attempt / raw status / cleanup等をPlaywright固有の形式で報告する必要がある場合だけ使用します。

一般的なTC実行報告のために`e2e-test-reporting`を必須化しません。

## 14. 実装時の主な変更先

- `skills/test-execution/SKILL.md`
- `skills/test-execution/references/guidance.md`
- `skills/test-execution/assets/execution-plan-template.yaml`
- `skills/test-execution/assets/output-template.md`
- trigger / deterministic / semantic eval
- 実行前YAMLの必須項目、Given / When / Then構造、`unresolved`と未実行判定の整合検証
- `qa-workflow`のrouting / state
- 必要な範囲の`test-target-inspection`連携
- 既存E2E Skillとの境界説明

既存`e2e-test-execution` / `e2e-test-result-analysis`のraw result契約は、本変更だけを理由に汎用化しません。

