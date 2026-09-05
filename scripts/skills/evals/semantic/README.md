# Semantic Output Eval Runtime

保存済みCandidate OutputをLLM Judgeで意味評価するShared Skill Eval Runtimeです。AgentやSkill自体は実行しません。

## 責務

- Skill配下の`rubric.json` / `evals.json` / `input.md` / `reference.md`のloadとschema validation
- Judge prompt構築
- `--judge-command`のsubprocess実行
- Judge responseのJSON-only contract検証
- criterion statusとoverall verdictの決定論的算出

特定LLM providerのSDKやadapterは含みません。

## Dataset

```text
skills/<skill>/evals/semantic/
├── rubric.json
├── evals.json
└── cases/
    ├── case-001/
    │   ├── input.md
    │   └── reference.md
    └── case-002/
        ├── input.md
        └── reference.md
```

`reference.md`はGolden Outputではなく、判定に使えるsource of truth、許容解釈、禁止される推測を記載します。

## CLI

```bash
python scripts/skills/evals/semantic/run.py \
  --skill test-case-design \
  --eval-id TC-SEM-001 \
  --output path/to/generated-output.md \
  --judge-command python path/to/judge_adapter.py
```

`--judge-command`はCLIの最後に置き、後続値をcommand argvとして扱います。内部では`shell=True`を使いません。

## Judge command protocol

```text
stdin:  Semantic Judge Prompt (UTF-8)
stdout: Judge response JSONのみ
stderr: 診断ログを許容
exit 0: judge execution success
non-zero: judge execution failure
```

Judgeはcriterionごとの`evaluable`, `rating`, `reason`, `evidence`だけを返します。`pass`、`fail`、`needs_review`、overall scoreはJudgeに決めさせません。

## Rating / Result

- rating 4 / 3 → criterion `pass`
- rating 2 → criterion `needs_review`
- rating 1 → criterion `fail`
- `evaluable=false` → criterion `not_evaluable`

Overall verdict:

- critical criterionのrating 1 → `fail`
- その他のrating 1、rating 2、`not_evaluable`が1件以上 → `needs_review`
- その他すべてrating 3以上 → `pass`

weighted score、平均点、100点満点は計算しません。

CLI exit code:

- `0`: overall verdict `pass`
- `1`: `needs_review` または `fail`
- `2`: Runtime / dataset / Judge execution / Judge response contract error

## Portability

Eval込みでSkillを移植する場合のコピー単位は次です。

```text
skills/<skill>/
scripts/skills/evals/
```

Semantic Runtimeはこのコピー単位でdirect CLI実行できることをrepository testで確認します。
