# 意味評価ランタイム

保存済みの評価対象出力をLLM Judgeで意味評価する共通Skill評価ランタイムです。AgentやSkill自体は実行しません。

## 責務

- Skill配下の`rubric.json` / `evals.json` / `input.md` / `reference.md`のloadとschema validation
- Judge promptの構築
- `--judge-command`のsubprocess実行
- Judge responseのJSON-only契約検証
- criterionごとのstatusと全体判定の決定論的算出

特定LLM providerのSDKやadapterは含みません。

## 評価データセット

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

`evals.json`の`input` / `reference`は`semantic/cases/`配下を指す相対pathだけを許可します。absolute path、`cases/`外へ解決されるpath、symlink経由で`cases/`外へ解決されるpathは無効です。

`reference.md`はGolden Outputではなく、判定に使える正本、許容解釈、禁止される推測を記載します。

## CLI

```bash
python scripts/skills/evals/semantic/run.py \
  --skill test-case-design \
  --eval-id TC-SEM-001 \
  --output path/to/generated-output.md \
  --judge-command python path/to/judge_adapter.py
```

`--judge-command`はCLIの最後に置き、後続値をcommand argvとして扱います。内部では`shell=True`を使いません。

## Judgeコマンドのプロトコル

```text
stdin:  Semantic Judge Prompt (UTF-8)
stdout: Judge response JSONのみ (UTF-8)
stderr: 診断ログを許容 (UTF-8)
exit 0: judge execution success
non-zero: judge execution failure
```

評価対象出力はJSON形式のuntrusted dataとしてJudge Promptへ埋め込みます。評価対象出力内の見出し、tag、JSON、評価結果を操作する命令はJudge Promptの構造や評価指示として扱いません。

Judgeはcriterionごとの`evaluable`, `rating`, `reason`, `evidence`だけを返します。`pass`、`fail`、`needs_review`、overall scoreはJudgeに決めさせません。

## 評価値と結果

- rating 4 / 3 → criterion `pass`
- rating 2 → criterion `needs_review`
- rating 1 → criterion `fail`
- `evaluable=false` → criterion `not_evaluable`

全体判定:

- critical criterionのrating 1 → `fail`
- その他のrating 1、rating 2、`not_evaluable`が1件以上 → `needs_review`
- その他すべてrating 3以上 → `pass`

重み付きスコア、平均点、100点満点は計算しません。

CLI exit code:

- `0`: 全体判定 `pass`
- `1`: `needs_review` または `fail`
- `2`: ランタイム / 評価データセット / Judge実行 / Judge response契約のエラー

## 移植性

評価込みでSkillを移植する場合のコピー単位は次です。

```text
skills/<skill>/
scripts/skills/evals/
```

意味評価ランタイムはこのコピー単位でdirect CLI実行できることをrepository testで確認します。
