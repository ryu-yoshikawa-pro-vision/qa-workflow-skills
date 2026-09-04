# Agent Skills Eval方針

このリポジトリでは、Agent Skillsの形式適合とは別に、Skillの発火・出力品質・Workflow全体挙動を段階的に評価します。

`evals/`、`EVALS.md`、train / validation分割はこのリポジトリ独自の開発・評価用拡張です。Agent Skills Specificationの必須標準ディレクトリではありません。

## 評価レイヤー

本リポジトリでは次を分離します。

1. **Spec Validation**: `SKILL.md` frontmatter / 命名規則等のAgent Skills仕様適合
2. **Trigger Eval**: `description`によるSkill選択・誤発火・routingの評価
3. **Output Quality Eval**: Skill利用時の成果物品質をbaselineと比較する評価（将来）
4. **Workflow E2E Eval**: `qa-workflow`から担当Skillへ遷移して要求成果物まで完了できるかの評価（将来）

Trigger EvalがPASSしてもOutput品質やWorkflow E2Eを保証しません。

## Trigger Evalの目的

YAML frontmatterの`description`は、AgentがSkillをロードするか判断する主要な情報です。Trigger Evalでは次を確認します。

- Skillが必要な要求で発火するか（should-trigger）
- 隣接Skillや別作業が必要な要求で誤発火しないか（should-not-trigger）
- 複数の近接Skillが利用可能な状態で正しいSkillへroutingできるか
- 明らかに無関係なnegativeではなく、語彙や目的が近いnear-missを区別できるか

## Canonical Mode

Canonical Trigger Evalは、**9 Skillすべてを同一Agent client上で同時に利用可能な状態**で実施します。

対象Skill:

- `qa-workflow`
- `spec-analysis`
- `question-analysis`
- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`
- `adversarial-review`

実行原則:

```text
9 SkillすべてをAgent clientへ登録 / 利用可能化
  ↓
各queryをclean contextで独立実行
  ↓
実際にロードされたSkillを実行ログ等で確認
  ↓
should_triggerと比較
  ↓
近接Skillを含むroutingの妥当性を確認
```

全9 Skillを同時に利用可能にする理由は、Trigger Evalの目的が対象Skill単独の発火能力だけではなく、**近接Skillが競合する実運用に近い条件で正しいSkillを選択できるか**を評価することだからです。

例:

```text
query: このテストケースを重大度付きでレビューして

期待:
- test-case-design: 発火しない
- adversarial-review: 発火する
```

`test-case-design`が発火しなかった事実だけではrouting成功とは判定しません。

## Diagnostic Mode

対象Skill単独、または限定したSkillだけをAgent clientへ登録して実行する方式です。

用途:

- 発火失敗の原因調査
- description単体の挙動確認
- 近接Skillとの競合切り分け
- Agent client固有のSkill discovery / loading問題の切り分け

Diagnostic Modeの結果は**Canonical Trigger Scoreとして扱いません**。Canonical Modeで失敗した理由を調査する補助評価です。

## Trigger評価概念

### Target Trigger

対象Skillが期待どおり発火 / 非発火したかを評価します。

既存datasetの`should_trigger`はこの評価に使用します。

```text
trigger_rate = 対象Skillが発火した回数 / 実行回数
```

既定では各queryを3回実行し、閾値を`0.5`とします。

- `should_trigger: true` → `trigger_rate > 0.5`でTarget Trigger PASS
- `should_trigger: false` → `trigger_rate < 0.5`でTarget Trigger PASS

閾値を変更する場合は同じ評価群へ一貫して適用し、理由を記録します。

### Unexpected Trigger

対象queryで、should-not-triggerである近接Skillや無関係Skillが誤ってロードされなかったかを確認します。

単一Skillの`trigger_rate`だけでなく、1実行で実際にロードされたSkill集合を記録できるAgent clientではUnexpected Triggerも評価します。

### Routing Correctness

複数Skill候補が利用可能な状況で、ユーザー要求に対して期待するSkillまたはSkill経路へroutingされたかを評価します。

現行datasetはSkillごとの`should_trigger`形式を維持します。完全なrouting runnerは今回実装しません。Canonical Modeでは、同一query実行時のロードSkill集合を観測し、Target TriggerとUnexpected Triggerを合わせてRouting Correctnessを判断できるよう記録します。

## Dataset配置

各Skill配下に固定のtrain / validation queryを持ちます。

```text
skills/<skill-name>/evals/trigger/
├── train_queries.json
└── validation_queries.json
```

現在のbaseline dataset:

- 1 Skillあたり20 query
- train: 12件（should-trigger 6 / should-not-trigger 6）
- validation: 8件（should-trigger 4 / should-not-trigger 4）
- 9 Skill合計: 180 query

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
- `test-analysis` ↔ `test-requirement-design`
- `test-requirement-design` ↔ `test-condition-design`
- `test-condition-design` ↔ `test-case-design`
- `coverage-analysis` ↔ `adversarial-review`
- `qa-workflow` ↔ 個別Skill

## 発火判定

回答内容から「発火したはず」と推測しません。

Agentの実行ログ、Skill loading log、tool call history、verbose output等から、対象Skillの`SKILL.md`が実際にロードされたかを確認します。Agent clientがSkill loadingを観測できない場合は、その制約を記録し、Canonical Trigger Scoreを確定したと扱いません。

各queryは独立したclean contextで実行します。前queryでロードされたSkillや会話履歴が次queryへ影響する状態を避けます。

## Description最適化ループ

現在のdescriptionをbaselineとして固定し、Trigger Eval結果を見る前に最適化しません。

1. 現在のdescriptionでCanonical Modeのtrain / validation baselineを取得する
2. trainの失敗を原因分析する
3. should-trigger失敗ならdescriptionが狭すぎないか確認する
4. should-not-trigger誤発火なら隣接Skillとの境界が曖昧でないか確認する
5. 個別queryの語句を足すのではなく、失敗の一般カテゴリを表現する
6. descriptionを修正してtrainを再実行する
7. validationは汎化性能確認に使用する
8. validationの個別queryへ過適合する修正は行わない
9. 最終候補をvalidation結果とrouting失敗内容で比較する

baseline比較可能性を維持するため、description最適化中は既存train / validation queryを不用意に入れ替えません。

## Final Holdout方針

現時点ではholdout queryをリポジトリへ追加しません。

Description選定完了後、train / validationの最適化に一度も使用していないfresh queryで最終generalization checkを行います。

目安:

- Skillごと、またはroutingリスクの高い重点Skillへ5〜10件程度
- train / validationの表現を単純に言い換えただけのqueryを避ける
- description最適化担当が事前に内容へ適合させない運用にする

真のholdout性を維持するため、datasetは別PRまたは最終評価直前に作成します。

## Baseline取得後のdataset拡張方針

既存180 queryはbaseline取得前に固定済みなので、明確なラベル誤りやSkill責務矛盾がない限り今回変更しません。

baseline取得後は別変更として、次の自然なユーザー表現を追加候補とします。

- 実運用由来の自然な依頼
- QA専門用語を使わない依頼
- 省略表現
- 曖昧な依頼
- 長い案件コンテキスト付き依頼
- 誤字・表記揺れ
- 暗黙的なSkill要求

追加時は既存baselineと混同しないようversion / 変更理由を記録します。

## Output Quality Eval（将来）

Trigger Evalとは別PRで扱います。候補:

```text
skills/<skill-name>/evals/evals.json
```

将来的にはwith-skill / without-skill比較、deterministic grader、必要に応じたLLM grader、token / duration / stability等を検討します。今回これらのrunnerやframeworkは実装しません。

## Workflow E2E Eval（将来）

`qa-workflow`のTrigger EvalだけではWorkflow全体の正しさを保証しません。次タスクでは実Agent client上で次を評価します。

- 正しい開始Skillを選べる
- 不要なSkillを通らない
- 既存成果物を再利用できる
- Blocked範囲だけ停止できる
- 上流変更時に影響範囲だけ`要再検証`へ戻せる
- 要求成果物で終了できる
- 個別SkillのDomain Logicを`qa-workflow`が肩代わりしない

Agent Skills Specificationは、Skill AからSkill Bを呼ぶ共通Skill-to-Skill APIを規定しません。本リポジトリのWorkflow E2Eは、**同一Agent client上で9 Skillすべてが利用可能で、Agentが必要なSkillを追加ロード / 利用できる環境**を前提として評価します。

特定Clientへの対応済みを事前に断定しません。Compatibilityは実Agent client上のE2E Evalで確認します。

## 現在の状態

- 9 Skill分のTrigger Eval dataset作成済み
- 1 Skillあたり20件、合計180件
- train / validation固定分割済み
- baseline取得前のためdescription未最適化
- Canonical Modeの実Trigger Eval結果は未取得
- holdout queryは未作成
- Output Quality Eval / Workflow E2E Evalは未実装
