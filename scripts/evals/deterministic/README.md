# Deterministic Output Eval

Canonical `assets/output-template.md`（`qa-workflow`はWorkflow State template）を使って生成されたMarkdownを、Python標準ライブラリだけで機械評価します。

## Scope

ERRORは、ID形式、重複、参照整合、required fields、allowed values、Risk Matrix、fixture-backed closure、Pairwise、重大度/処置Invariant、Workflow state invariant等、決定論的に判定できる契約に限定します。

誤検知し得るものはWARNING、意味解釈が必要な品質はSemantic Output Evalの対象です。

## Architecture

```text
scripts/evals/deterministic/
├── run.py
├── markdown_parser.py
├── result.py
├── common.py
├── validators/
│   └── <9 skill validators>
└── tests/
    ├── test_deterministic.py
    ├── test_false_pass_regressions.py
    └── test_cli_integration.py
```

共通層はMarkdown table解析、ID抽出、重複・allowed values・required fields、共通graph計算、Pairwiseの組合せ数学、結果集計を担当します。Disposition、Closure、Pairwise Output構造、Review、Workflow状態等のSkill固有ルールは各validatorに置きます。

## CLI

単一case:

```bash
python scripts/evals/deterministic/run.py \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --output path/to/generated-output.md
```

全case:

```bash
python scripts/evals/deterministic/run.py \
  --skill all \
  --output-root path/to/saved-outputs
```

all modeではmanifestに定義された全Outputを要求します。Agent APIを呼び出す機能は持ちません。

## Result

JSONで`status`, `summary`, `assertions`を返します。WARNINGは全体failへ直結しません。独自weighted scoreは計算しません。

評価契約の正本は`EVALS.md`、Assertion IDの正本は`ASSERTIONS.md`です。
