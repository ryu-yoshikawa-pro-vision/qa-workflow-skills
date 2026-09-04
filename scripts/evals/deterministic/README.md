# Deterministic Output Eval

Canonical `assets/output-template.md`（`qa-workflow`はWorkflow State template）を使って生成されたMarkdownを、Python標準ライブラリだけで機械評価します。

## Scope

このgraderがERRORとして扱うのは、ID形式、重複、参照整合、allowed values、Risk Matrix、fixture-backed closure、Pairwise 2-wise coverage、重大度/処置Invariant、Workflow state invariant等、決定論的に判定できる契約です。

曖昧語や他ケース依存らしき表現など、誤検知し得るものはWARNINGです。仕様内容の妥当性、Blocker分類、Oracleの意味的正しさ、網羅性の十分性などはSemantic Output Evalへ残します。

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
    └── test_deterministic.py
```

共通層はMarkdown table解析、ID抽出・一意性、参照確認、allowed values、Disposition、graph closure、Pairwise組合せ、結果集計を担当します。Skill固有の契約だけを各validatorへ置きます。

## CLI

単一case:

```bash
python scripts/evals/deterministic/run.py \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --output path/to/generated-output.md
```

複数case:

```bash
python scripts/evals/deterministic/run.py \
  --skill all \
  --output-root path/to/saved-outputs
```

all modeでは`<output-root>/<skill>/<eval-id>.md`を評価します。Agent APIを呼び出す機能は持ちません。

## Result

JSONで`status`, `summary`, `assertions`を返します。WARNINGは全体failへ直結しません。独自weighted scoreは計算しません。
