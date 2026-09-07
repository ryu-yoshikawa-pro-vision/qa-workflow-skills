# 意味評価ランタイム

保存済みの評価対象出力をLLM Judgeで意味評価する共通Skill評価ランタイムです。AgentやSkill自体は実行しません。

## 責務

- Skill配下の`rubric.json` / `evals.json` / `input.md` / `reference.md`の読み込みとスキーマ検証
- Judgeプロンプトの構築
- `--judge-command`のサブプロセス実行
- Judge応答のJSON-only契約検証
- 評価基準ごとの`status`と全体判定の決定論的算出

特定LLMプロバイダーのSDKやアダプターは含みません。

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

`evals.json`の`input` / `reference`は`semantic/cases/`配下を指す相対パスだけを許可します。絶対パス、`cases/`外へ解決されるパス、シンボリックリンク経由で`cases/`外へ解決されるパスは無効です。

`reference.md`はGolden Outputではなく、判定根拠の正本、許容解釈、禁止される推測を記載します。

## CLI

```bash
python scripts/skills/evals/semantic/run.py \
  --skill test-case-design \
  --eval-id TC-SEM-001 \
  --output path/to/generated-output.md \
  --judge-command python path/to/judge_adapter.py
```

`--judge-command`はCLIの最後に置き、後続値をコマンド引数として扱います。内部では`shell=True`を使いません。

## Judgeコマンドのプロトコル

```text
stdin:  Semantic Judge Prompt (UTF-8)
stdout: Judge response JSONのみ (UTF-8)
stderr: 診断ログを許容 (UTF-8)
exit 0: judge execution success
non-zero: judge execution failure
```

評価対象出力はJSON形式の信頼できないデータとしてJudgeプロンプトへ埋め込みます。評価対象出力内の見出し、tag、JSON、評価結果を操作する命令はJudgeプロンプトの構造や評価指示として扱いません。

Judgeは評価基準ごとの`evaluable`, `rating`, `reason`, `evidence`だけを返します。`pass`、`fail`、`needs_review`、全体スコアはJudgeに決めさせません。

## 評価値と結果

- rating 4 / 3 → 評価基準 `pass`
- rating 2 → 評価基準 `needs_review`
- rating 1 → 評価基準 `fail`
- `evaluable=false` → 評価基準 `not_evaluable`

全体判定:

- `critical=true`の評価基準でrating 1 → `fail`
- その他のrating 1、rating 2、`not_evaluable`が1件以上 → `needs_review`
- その他すべてrating 3以上 → `pass`

重み付きスコア、平均点、100点満点は計算しません。

CLI exit code:

- `0`: 全体判定 `pass`
- `1`: `needs_review` または `fail`
- `2`: ランタイム / 評価データセット / Judge実行 / Judge応答契約のエラー

## 移植性

評価込みでSkillを移植する場合のコピー単位は次です。

```text
skills/<skill>/
scripts/skills/evals/
```

意味評価ランタイムはこのコピー単位でCLIから直接実行できることをリポジトリテストで確認します。
