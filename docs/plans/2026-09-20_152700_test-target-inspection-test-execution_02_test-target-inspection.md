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

既存Skillと同じPackage構成を使用します。新しい共通runtimeや依存関係は追加しません。

## 2. `SKILL.md` 契約

`description`は次の発火境界を識別できる内容にします。

- 実対象を確認し、テスト設計 / 実装 / 実行向けの参照資料を作成する
- 既存のテスト対象資料を実対象に合わせて更新する
- POM相当のUI構造・操作・状態情報を整理する
- Playwrightコード実装、E2E実装可否だけのinspection、TC作成、テスト実行では発火しない

### 必須入力

最低限、次を識別できることを要求します。

- 調査対象: 機能、画面、領域、ユーザー操作経路等
- 実対象またはrepo / workspaceのうち、要求された資料を作成できる確認元

更新要求では、既存のテスト対象資料またはその参照先を入力にします。

永続更新を要求された場合は、保存先と書込可能性を確認します。保存先不明時に独自の既定パスを作りません。

### 補助入力

利用可能な場合だけ使用します。

- 対象URL / origin
- browser / computer操作能力
- repo branch / commit / working tree
- version / build ID
- 既存Page Object / fixture / helper
- 関連するテストケース
- 現在有効な仕様根拠

仕様根拠は、テスト対象資料へ期待結果を転記するための必須入力にはしません。仕様と観測実装を比較する要求がある場合だけ参照し、両者を別事実として保持します。

## 3. 調査手順

`references/guidance.md`では次の順序を固定します。

1. 対象範囲と要求成果物を確認する
2. 既存テスト対象資料の有無と鮮度情報を確認する
3. repo / workspaceで既存Page Object、fixture、helper、route、UI識別方針等を確認する
4. 必要かつ操作可能な場合だけ実対象へ到達する
5. 対象画面 / 領域、UI要素、状態、遷移、データ / 権限依存、非同期状態を確認する
6. 既存資料と今回確認事実を比較する
7. 変更がある範囲だけ更新し、未確認範囲を推測で書き換えない
8. 確認元、確認日時、version / build、repo revision、未確認事項を記録する
9. 永続更新を要求され、保存先と書込能力がある場合だけ対象成果物を更新する
10. 更新後の成果物へ出力契約を再適用する

新規作成時も、調査範囲外の周辺画面まで網羅目的で追加しません。

## 4. 出力Asset

`skills/test-target-inspection/assets/output-template.md`を正規出力として追加します。

### 対象・鮮度

| 項目 | 値 | 確認元 | 確認日時 / revision |
| --- | --- | --- | --- |
| 対象名 / 範囲 |  |  |  |
| 対象URL / route |  |  |  |
| 確認環境 |  |  |  |
| version / build ID |  |  |  |
| repo branch / commit |  |  |  |
| 成果物参照 / 保存先 |  |  |  |

保存先がない場合は空欄にせず`未指定`等の明示状態を使用します。

### 画面・領域

| 対象キー | 画面 / 領域 | 到達方法 | URL / route | 確認状態 | 確認元 |
| --- | --- | --- | --- | --- | --- |

### UI要素

| 要素キー | 対象キー | 名称 | role / 種別 | 識別情報 | 操作 | 状態・表示条件 | 確認状態 |
| --- | --- | --- | --- | --- | --- | --- | --- |

`識別情報`には確認できた範囲でaccessible name、test id、label、既存locator等を記録できますが、Playwright selector文字列の生成を必須にしません。

### 状態・非同期動作

| 状態キー | 対象キー | 状態 | 発生条件 | 完了 / 終了条件 | 観測方法 | 確認状態 |
| --- | --- | --- | --- | --- | --- | --- |

### 操作・遷移

| 操作元 | 操作 | 条件 | 遷移先 / 観測結果 | 確認状態 |
| --- | --- | --- | --- | --- |

### データ・権限依存

| 対象 | 条件 | 影響 | 確認元 | 確認状態 |
| --- | --- | --- | --- | --- |

### 既存テスト実装との対応

| 対象 / 要素 | 種別 | repo参照 | 関係 | 確認状態 |
| --- | --- | --- | --- | --- |

`種別`には既存Page Object / fixture / helper / spec等、repoで実在を確認できたものを記録します。

### 未確認事項

| 対象 | 未確認内容 | 理由 | 後続への影響 |
| --- | --- | --- | --- |

### 今回の更新

| 対象 | 変更種別 | 変更内容 | 根拠 |
| --- | --- | --- | --- |

新規作成時は`新規`、既存更新時は`追加 / 更新 / 削除確認 / 変更なし`等、実装時にvalidatorと揃えた正規値を使用します。未確認のため消せない情報を`削除済み`とはしません。

## 5. 対象キーの扱い

新しい全リポジトリ共通ID体系は追加しません。

`対象キー`、`要素キー`、`状態キー`はテスト対象資料内で一意かつ更新時に安定していることを要求します。既存資料にキーがある場合は意味が同じ対象へ同じキーを維持します。

既存QA IDへ混ぜず、`scripts/skills/evals/deterministic/common.py`の`ID_PATTERNS` / `ALL_ID_RE`を今回の資料キーのためだけに拡張しません。

## 6. 更新原則

既存成果物を更新する場合は次を守ります。

- 今回確認できた範囲だけ更新する
- 未確認の既存項目を「存在しない」と推測して削除しない
- 意味が同じ対象のキーを不要に再採番しない
- repo / 実対象に存在しないPage Object、locator、fixture等を創作しない
- テンプレート外の人間記載内容を無関係に削除しない
- 構造が曖昧で安全に差分更新できない場合は、更新不能範囲を明示する

全対象の再生成を既定にしません。

## 7. `e2e-test-inspection`との関係

`e2e-test-inspection`は残します。

現在有効な`test-target-inspection`成果物がある場合は、次の実対象事実を再利用可能にします。

- 対象画面 / 経路
- 実在UI要素
- role / accessible name等
- 状態・非同期動作
- Page Object / fixture / helperのrepo参照
- version / build / 確認日時

ただし`e2e-test-inspection`自身が所有する次の判断は移しません。

- E2E対象の扱い
- Playwright実装可否
- config / project / test固有条件
- E2E固有の認証・setup / cleanup
- 副作用上限
- artifact / reporter条件

資料が古い、対象範囲が不足する、確認元が不明な場合は再利用せず、必要範囲だけ`test-target-inspection`へ戻せるようにします。

## 8. 実装時の主な変更先

新規Skill以外では最低限、次を対象にします。

- `skills/e2e-test-inspection/SKILL.md`
- `skills/e2e-test-inspection/references/guidance.md`
- 必要なら`skills/e2e-test-inspection/assets/output-template.md`
- `skills/qa-workflow/SKILL.md`
- `skills/qa-workflow/references/guidance.md`

既存`e2e-test-inspection`の正規output contractを不必要に壊さず、テスト対象資料参照は任意入力 / 利用時参照として追加します。