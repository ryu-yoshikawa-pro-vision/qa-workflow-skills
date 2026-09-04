# Agent Skills Eval方針

このリポジトリでは、Skillの設計レビューだけでなく、実際にSkillが適切なユーザー要求で発火するかをTrigger Evalで確認します。

## Trigger Evalの目的

YAML frontmatterの`description`は、AgentがSkillをロードするか判断する主要な情報です。Trigger Evalでは、各Skillについて次を確認します。

- Skillが必要な要求で発火するか（should-trigger）
- 隣接Skillや別作業が必要な要求で誤発火しないか（should-not-trigger）
- 明らかに無関係なnegativeではなく、語彙や目的が近いnear-missを正しく区別できるか

Trigger EvalはQA成果物の内容品質を評価するものではありません。出力品質Evalは別途`evals/evals.json`等で追加します。

## 配置

各Skill配下に固定のtrain / validation queryを持ちます。

```text
skills/<skill-name>/evals/trigger/
├── train_queries.json
└── validation_queries.json
```

9 Skillすべてについて、1 Skillあたり20 queryを用意します。

- train: 12件（should-trigger 6 / should-not-trigger 6）
- validation: 8件（should-trigger 4 / should-not-trigger 4）

合計180 queryです。

## Query形式

```json
[
  {
    "query": "この変更で何を重点的にテストすべきか、Product Riskを評価して整理してください。",
    "should_trigger": true
  },
  {
    "query": "このCoverage Itemを実施手順と期待結果のあるケースにして。",
    "should_trigger": false
  }
]
```

## 重点near-miss

特に次の境界を重点確認します。

- `spec-analysis` ↔ `question-analysis`
  - 仕様モデルを作るのか、未解決論点の停止 / 継続判断をするのか
- `test-analysis` ↔ `test-requirement-design`
  - テスト重点・深度を決めるのか、検証責務を要求化するのか
- `test-requirement-design` ↔ `test-condition-design`
  - 何を保証するかを定義するのか、条件・Coverageへ具体化するのか
- `test-condition-design` ↔ `test-case-design`
  - Coverage Itemまで設計するのか、実行手順と期待結果まで具体化するのか
- `coverage-analysis` ↔ `adversarial-review`
  - 成果物チェーンのCoverage / 閉鎖性を見るのか、成果物自体をCold Reviewして重大度判定するのか
- `qa-workflow` ↔ 個別Skill
  - 複数工程のルーティングが必要なのか、単一Skillの成果物だけを要求しているのか

## 実行方法

実際のAgent clientへ対象Skillを登録し、各queryを独立したclean contextで実行します。

### 発火判定

Skillが発火したかは、回答内容から推測しません。

Agentの実行ログ、tool call history、verbose output等から、対象Skillの`SKILL.md`が実際にロードされたかを確認します。

### 実行回数

モデル挙動の非決定性を考慮し、各queryを既定で3回実行します。

```text
trigger_rate = 対象Skillが発火した回数 / 3
```

既定閾値は`0.5`です。

- `should_trigger: true` → `trigger_rate > 0.5`でPASS
- `should_trigger: false` → `trigger_rate < 0.5`でPASS

Agent clientの性質に応じて閾値を変更する場合は、全Skillへ同じ基準を適用し、変更理由を記録します。

## Description最適化ループ

1. 現在のdescriptionをtrain / validationの両方で実行する
2. trainの失敗だけを原因分析する
3. should-trigger失敗ならdescriptionが狭すぎないか確認する
4. should-not-trigger誤発火なら隣接Skillとの境界が曖昧でないか確認する
5. 個別queryの語句をdescriptionへ足すのではなく、失敗の一般カテゴリを表現する
6. descriptionを修正してtrainを再実行する
7. validationは汎化性能の確認に使い、validation結果へ合わせてdescriptionを調整しない
8. 最終版はvalidation pass rateで選ぶ

train / validationのqueryは、比較可能性を維持するため、description調整中に入れ替えません。

## 現在の状態

- 9 Skill分のTrigger Eval dataset作成済み
- 1 Skillあたり20件、合計180件
- train / validation固定分割済み
- 現時点ではdescriptionの最適化は未実施
- Agent client上での実Trigger Eval実行結果は未取得

Trigger Evalを実行して失敗傾向を確認するまでは、queryに合わせてdescriptionを書き換えません。
