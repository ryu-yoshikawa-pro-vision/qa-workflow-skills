# 決定論的出力評価

正本となる`assets/output-template.md`（`qa-workflow`はワークフロー状態テンプレート）を使って生成されたMarkdownを、Python標準ライブラリだけで機械評価します。

## 対象範囲

ERRORは、ID形式、重複、参照整合、必須フィールド、許可値、リスクマトリクス、fixtureに基づく閉鎖性、Pairwise、重大度 / 処置の不変条件、ワークフロー状態の不変条件など、決定論的に判定できる契約に限定します。

誤検知し得るものはWARNING、意味解釈が必要な品質は意味評価の対象です。

## 構成

```text
skills/<skill-name>/evals/deterministic/
└── validator.py

scripts/skills/evals/deterministic/
├── run.py
├── loader.py
├── markdown_parser.py
├── result.py
├── common.py
├── ASSERTIONS.md
├── README.md
└── tests/
    ├── test_loader.py
    └── test_markdown_parser.py

tests/skills/evals/deterministic/
├── test_deterministic.py
├── test_false_pass_regressions.py
├── test_closure_exclusivity.py
├── test_cli_integration.py
├── test_repository_integration.py
└── test_runtime_portability.py
```

Skill固有の扱い、閉鎖性、Pairwise出力構造、レビュー、ワークフロー状態などの評価ルールは、各Skillの`evals/deterministic/validator.py`に置きます。共通層はrunner、validator loader、Markdown table解析、ID抽出、重複・許可値・必須フィールド、共通graph計算、Pairwiseの組合せ数学、結果集計を担当します。

`scripts/skills/evals/deterministic/tests/`は共通ランタイム固有test、`tests/skills/evals/deterministic/`はqa-workflow-skills固有のvalidator・CLI・integration testを保持します。

`loader.py`は既存の`skills/*/evals/output/evals.json`を出力評価対象の正本としてSkillを発見し、同じSkillの`evals/deterministic/validator.py`をファイルシステム上のパスからloadします。Skill名にハイフンが含まれていても通常のPython package importへ変換しません。対象Skillのvalidator欠落、module load失敗、`validate` callable欠落はエラーとし、暗黙にスキップしません。

Skill配下のvalidatorは`scripts.skills.evals.deterministic.common`、`markdown_parser`、`result`を共通評価ランタイムとして再利用します。Skillを利用するだけなら`skills/<skill-name>/`のみでよく、評価も含めて移植する場合は`skills/<skill-name>/`と`scripts/skills/evals/`を一緒にコピーします。後者はこのリポジトリ独自の共通Skill評価ランタイムであり、Agent Skills Specificationの必須構造ではありません。

## CLI

単一ケース:

```bash
python scripts/skills/evals/deterministic/run.py \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --output path/to/generated-output.md
```

全ケース:

```bash
python scripts/skills/evals/deterministic/run.py \
  --skill all \
  --output-root path/to/saved-outputs
```

`all`モードではmanifestに定義された全出力を要求します。Agent APIを呼び出す機能は持ちません。

## 結果

JSONで`status`, `summary`, `assertions`を返します。WARNINGは全体failへ直結しません。独自の重み付きスコアは計算しません。

評価契約の正本は`EVALS.md`、Assertion IDの正本は`ASSERTIONS.md`です。
