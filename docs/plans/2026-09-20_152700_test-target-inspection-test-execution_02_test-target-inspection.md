# テスト対象資料管理・テスト実行Skill追加Plan

## 1. 追加ファイル

```text
skills/test-target-inspection/
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

## 2. `SKILL.md`契約

`test-target-inspection`の目的は、**生きた実対象から現在のUI情報とふるまいを収集し、テスト対象資料として管理すること**です。

### 必須入力

- 今回確認する対象範囲
- 実対象へ到達するためのURL / 入口または同等の識別情報
- 実対象を観測できるbrowser / computer操作能力
- 既存テスト対象資料または保存先（存在する場合）

既存資料がある場合は、今回対象範囲のcurrentness確認を必須とします。既存資料がない場合は、今回対象範囲を新規収集します。

repo / workspace、仕様根拠、Page Object / fixture / helper等は補助入力です。実対象へ到達できない場合、repoだけで調査を継続することはできますが、その範囲をcurrentな実対象情報として完成扱いにしません。

## 3. 観測対象

最低限、今回必要な範囲で次を確認します。

### UI構造

- 画面 / 領域
- 到達経路
- UI要素
- role / accessible name / label / test id等の識別情報
- 操作可能 / disabled / readonly等の状態

### ふるまい

- click / input / selection等に対する反応
- 画面遷移
- modal / popup / drawer等の開閉
- loading / empty / error / success等の状態変化
- 非同期更新
- validation表示
- role / 権限、テストデータ、feature flag等による差異

### 視覚情報

DOM / accessibility tree等の構造情報だけで確認できない場合、または視覚状態自体が後続作業に必要な場合は画像を使います。

- 要素の重なり
- 文字・コンテンツの欠け / はみ出し
- レスポンシブ崩れ
- 表示位置 / サイズ
- 画像・アイコン
- canvas等の描画
- modal / popup等の視覚状態

画像だけでrole、accessible name、DOM状態、仕様を推測しません。構造情報と画像を必要に応じて併用します。

## 4. 調査手順

`references/guidance.md`では次の流れを基本とします。

1. 今回確認する対象範囲と保存対象を確定する
2. 既存テスト対象資料があれば読み込み、今回対象範囲の既存情報と鮮度を確認する
3. 実対象へ到達し、対象version / build、role / 権限、viewport、locale、feature flag、テストデータ等の確認条件を把握する
4. UI構造をDOM / accessibility tree等から確認する
5. 必要な操作を行い、状態変化・画面遷移・非同期挙動を確認する
6. 構造情報で判定できない視覚情報がある場合はscreenshot等を取得して画像として確認する
7. 既存資料がある場合は、今回対象範囲について実対象と比較し、各情報を`変更なし / 更新 / 削除確認 / 未確認 / 確認不能`へ整理する
8. 変更箇所だけ資料を更新し、変更なしの情報も今回確認済みとして確認日時 / version / build / 確認条件を更新する
9. 今回確認していない既存情報の鮮度を今回値へ上げない
10. 保存前に出力契約と参照整合を確認する
11. 永続更新時はSHA / revision / ETag等の条件付き更新を優先し、利用できない場合だけ保存直前に再読込・比較する
12. 保存後に確認可能なら再読込し、保存内容を確認する
13. 保存済み成果物参照、今回確認範囲、変更有無、未確認 / 確認不能範囲を返す

製品全体を毎回full scanしません。**今回利用・更新する範囲がcurrentかを実対象で確認する**ことを必須にします。

## 5. 出力Asset

`skills/test-target-inspection/assets/output-template.md`を正規出力として追加します。

### 確認情報

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 |  |  |
| 対象URL / origin |  |  |
| version / build |  |  |
| 確認日時 |  |  |
| role / 権限 |  |  |
| viewport |  |  |
| locale |  |  |
| feature flag |  |  |
| テストデータ条件 |  |  |
| 既存成果物参照 |  |  |
| 更新元revision / content identity |  |  |

### 画面 / 領域

| 対象キー | 画面 / 領域 | 到達経路 | 確認状態 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- |

### UI要素

| 要素キー | 対象キー | UI要素 | 識別情報 | 操作可能性 / 状態 | 確認状態 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 状態

| 状態キー | 対象キー | 状態 | 観測内容 | 到達条件 | 確認状態 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 操作・ふるまい

| 対象キー | 要素キー | 開始状態 | 操作 | 実対象の反応 / 遷移 | 到達状態 | 確認状態 | 確認条件 |
| --- | --- | --- | --- | --- | --- | --- | --- |

ここには仕様上の期待結果ではなく、実対象で現在観測したふるまいを記録します。

### 視覚情報

必要な場合だけ記録します。

| 対象キー | 要素キー / 状態キー | 確認観点 | 画像で観測した事実 | 画像参照 | 確認状態 | 備考 |
| --- | --- | --- | --- | --- | --- | --- |

画像参照自体を全行で必須にしません。構造情報だけで十分な事実へ不要なscreenshotを増やしません。

### データ・権限依存

| 対象キー | 要素キー / 状態キー | 条件 | 実対象で確認した差異 | 確認状態 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- |

### 既存テスト実装との対応（任意）

対象プロジェクトで既存POM / Page Object / fixture / helper等を使用しており、後続作業に有用な場合だけ記録します。

| 対象キー | 要素キー | 種別 | repo参照 | 関係 | 確認revision |
| --- | --- | --- | --- | --- | --- |

この表を作るためだけにrepoを調査しません。POM等の作成・更新も行いません。

### 未確認 / 確認不能

| 対象 | 状態 | 理由 | 後続への影響 |
| --- | --- | --- | --- |

### 今回の更新

既存成果物を更新した場合だけ必須とします。

| 対象種別 | 対象キー | 要素キー / 状態キー | 更新区分 | 内容 |
| --- | --- | --- | --- | --- |

`更新区分`は少なくとも次を扱います。

- `変更なし`
- `更新`
- `追加`
- `削除確認`

新規成果物では全行を`追加`として重複列挙しません。

## 6. キーと鮮度

`対象キー`、`要素キー`、`状態キー`は成果物内で一意かつ更新時に安定させます。

新規成果物では以下を使用します。

- `target-001`
- `element-001`
- `state-001`

既存資料に別の安定キー規則がある場合は維持します。表示名、route、locator等が変わっても同じ対象と判断できる場合はキーを維持します。

削除したキーを同じ更新処理で即再利用しません。削除済みキーの永久tombstone / registryは追加しません。

既存行を今回確認した場合だけ、その行の確認日時 / version / build / 確認条件を今回値へ更新します。確認していない行を成果物全体の更新日時だけでcurrent扱いにしません。

## 7. 永続更新

永続保存先はユーザーまたは案件が指定します。`qa-workflow-skills`リポジトリを案件固有資料の保存先にしません。

更新時は以下を守ります。

- 保存先が提供する条件付き更新を優先
- 途中変更があれば古い候補で上書きしない
- 任意形式文書を汎用的にmergeする新規frameworkを作らない
- 構造的に安全に更新できない場合は上書きせず更新不能範囲を返す
- 保存成功を確認できない場合は`更新済み`と表現しない

## 8. 安全と証跡

永続的な副作用が必要な観測では、対象origin、許可scope、最大回数、cleanup方法を確認します。確認できなければ操作しません。

trace / screenshot / page snapshot等はsecret・個人データ・機密情報を含み得るため、必要最小限だけ取得し、自動共有・commit・転載しません。

画像は判断手段として利用できますが、画像そのものの永続保存をSkill完了条件にはしません。安全な画像参照を保持できない場合は、画像から確認した観測事実だけを成果物へ記録します。

## 9. 後続Skillでの利用

currentな`test-target-inspection`成果物は、次で任意入力として利用できます。

- `test-case-design`: UI名称、到達経路、具体操作、観測可能性
- `test-execution`: 到達経路、UI要素、状態、視覚情報、データ / 権限依存
- `e2e-test-inspection`: 実対象情報の再利用

テスト対象資料は仕様Authorityではありません。後続Skillは期待結果の根拠として使用しません。

## 10. 実装時の主な変更先

- `skills/test-target-inspection/SKILL.md`
- `skills/test-target-inspection/references/guidance.md`
- `skills/test-target-inspection/assets/output-template.md`
- trigger / deterministic / semantic eval
- `qa-workflow`のrouting / state
- `test-case-design` / `e2e-test-inspection` / `test-execution`の任意入力契約

