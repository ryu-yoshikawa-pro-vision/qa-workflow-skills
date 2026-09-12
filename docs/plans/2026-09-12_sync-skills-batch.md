# Skill同期バッチ実装Plan

## 目的

`qa-workflow-skills` の `skills/` 配下にあるAgent Skillを、ユーザーが指定したローカルディレクトリへ安全に一方向同期できるWindowsバッチを追加する。

主な利用先は、兄弟ディレクトリとして配置した `qa-training-store/.agents/skills/` を想定する。

```text
workspace/
├─ qa-workflow-skills/
└─ qa-training-store/
   └─ .agents/
      └─ skills/
```

同期先に存在する `qa-training-store` 固有Skillを削除せず、`qa-workflow-skills` が管理するSkillだけを更新できることを必須とする。

## 対象ブランチ

`feat/sync-skills-batch`

## 現状

### `qa-workflow-skills`

- Skillの正本は `skills/<skill-name>/` にある。
- `README.md` では、Skillを利用する場合は `skills/<skill-name>/` をコピーする運用を案内している。
- `scripts/skills/` には評価用処理だけがあり、Skill配布・同期用のスクリプトはない。
- 現在の `main` は9 Skill構成である。
- PR #9 `feat/e2e-test-workflow` では5つのE2E Skill追加を予定しているため、同期スクリプトでSkill名を9件または14件へ固定しない。

### `qa-training-store`

`main` の `.agents/skills/` には現在、次のリポジトリ固有Skillがある。

- `android-native-local-validation`
- `code-review`
- `exploratory-qa`
- `feature-plan`
- `harness-improvement`
- `repair-loop`

現在の `qa-workflow-skills` のSkill名とは重複していない。

`.agents/skills/` 全体をミラーするとこれらを削除するため、同期対象ルート全体への `robocopy /MIR` は禁止する。

## 実装方針

### 1. Windowsバッチを追加する

追加候補:

```text
scripts/skills/sync-skills.cmd
```

実行例:

```bat
scripts\skills\sync-skills.cmd "C:\work\qa\qa-training-store\.agents\skills"
```

第1引数を同期先のSkillルートとして必須にする。`qa-training-store` 固有のパスはスクリプトへハードコードしない。

### 2. カレントディレクトリに依存しない

同期元は、実行時のカレントディレクトリではなく `sync-skills.cmd` 自身の配置場所から `qa-workflow-skills/skills/` を解決する。

これにより、リポジトリルート以外から実行しても同じ同期元を参照する。

### 3. Skill一覧を動的に検出する

同期対象は、`skills/` 直下のディレクトリのうち `SKILL.md` を持つものとする。

概念上は次の条件で列挙する。

```text
skills/*/SKILL.md が存在するディレクトリ
```

Skill名をスクリプトへ固定しない。

これによりPR #9のE2E Skillがマージされた後も、バッチ自体の修正なしで同期対象へ追加できる。

### 4. Skill単位で同期する

各同期元Skillについて、次の単位で同期する。

```text
qa-workflow-skills/skills/<skill-name>/
  ↓
<指定先>/<skill-name>/
```

Windows標準の `robocopy` を使用し、各Skillディレクトリを個別にミラーする。

重要な制約:

- `<指定先>` 全体には `/MIR` を適用しない。
- `/MIR` を使う場合は `<指定先>/<skill-name>/` に限定する。
- 同名Skill内で同期元から削除されたファイル・ディレクトリは同期先からも削除し、1 Skill単位では同期元と一致させる。
- 同期元に存在しない同期先固有Skillは変更・削除しない。

これにより `exploratory-qa` 等の `qa-training-store` 固有Skillを保持したまま、`qa-workflow-skills` のSkillだけを更新する。

### 5. Skill Package全体をコピーする

`README.md` の既存方針に合わせ、`skills/<skill-name>/` 配下を個別ファイル選択せず、そのまま同期する。

対象には現在の構成上、必要に応じて次が含まれる。

```text
SKILL.md
references/
assets/
scripts/
evals/
```

`evals/`だけを除外する独自配布形式は今回追加しない。

### 6. 同期先パスの安全確認を行う

次の場合はコピーを開始せず、エラー終了する。

- 第1引数がない。
- 同期元 `skills/` が存在しない。
- 指定された同期先ディレクトリが存在しない。
- 同期元に `SKILL.md` を持つSkillが1件もない。

同期先ディレクトリはバッチ側で自動作成しない。パス誤指定時に意図しない場所へSkillディレクトリを作成することを避ける。

パスに空白が含まれても動作するよう、すべてのパスを引用符付きで扱う。

### 7. 同名Skillは同期元を正本として更新する

同期先に同名Skillが存在する場合、そのSkillは `qa-workflow-skills` から同期する対象として扱い、同期元の内容で更新する。

現時点の `qa-training-store/.agents/skills/` には名前衝突はないが、将来同名Skillを同期先側で独自管理すると上書きされる。この挙動はREADMEへ明記する。

今回は同期元の所有情報を記録するmanifestやmarker fileは追加しない。

### 8. 同期元から削除されたSkillディレクトリは自動削除しない

今回のスクリプトは「現在同期元に存在するSkillを個別にミラーする」ことまでを責務とする。

以前同期したSkill自体が後から `qa-workflow-skills/skills/` から削除・名称変更された場合、同期先に残った旧Skillディレクトリを自動削除しない。

安全に削除するには「どの同期先Skillをこのスクリプトが所有しているか」を記録する仕組みが必要になるため、現在の要求だけを理由にmanifest管理を追加しない。

Skill削除・名称変更が実際に必要になった時点で、その要件に合わせて追加対応する。

### 9. `robocopy` の終了コードを正しく扱う

`robocopy` はコピー差分がある場合にも0以外を返すため、通常の `ERRORLEVEL 1` 判定をそのまま失敗扱いにしない。

`robocopy` の仕様に従い、正常・差分ありとして扱える終了コードと失敗コードを区別する。

失敗を検出した場合は対象Skill名を表示し、バッチ全体を非0終了する。

途中で1 Skillの同期に失敗した場合、後続Skillへ進んで部分同期を増やすのではなく、その時点で終了する。

## 出力

実行時には最低限、次を標準出力へ表示する。

- 同期元Skillルート
- 同期先Skillルート
- 同期中のSkill名
- 正常終了または失敗したSkill名
- 最終的な同期件数

詳細な独自ログファイルは作成しない。

## README更新

`README.md` にローカル同期方法を追加する。

最低限、次を記載する。

- Windows用スクリプトであること
- 実行例
- 第1引数には `.agents/skills/` 等の「Skillルート」を指定すること
- 同期先ルート全体は削除しないこと
- 同名Skillは同期元で更新されること
- 同期先固有Skillは保持されること
- 同期元からSkill自体を削除しても同期先の旧Skillは自動削除されないこと
- Skill一覧は動的検出されるため、将来追加されたSkillも対象になること

## 変更対象

実装時の主な変更対象は次とする。

```text
scripts/skills/sync-skills.cmd
README.md
```

追加の依存関係は導入しない。

## 検証

### Windowsでの動作確認

一時ディレクトリを同期先として、少なくとも次を確認する。

1. 引数なしで非0終了し、コピーを開始しない。
2. 存在しない同期先パスで非0終了する。
3. 空白を含む同期先パスへ同期できる。
4. `SKILL.md` を持つ全同期元Skillが同期される。
5. 同期先にあらかじめ置いた無関係なSkillディレクトリが削除・変更されない。
6. 同名Skill配下に追加した同期先だけの不要ファイルが再同期時に削除される。
7. 同期元Skillの変更内容が再同期時に同期先へ反映される。
8. 1 Skillの同期失敗時にバッチが非0終了する。

### リポジトリ既存検証

同期スクリプト追加によって既存Skill契約を変更しないことを確認するため、既存検証も実行する。

- Agent Skills仕様検証
- repository eval structure検証
- 既存の決定論的評価・意味評価で変更対象に関係する回帰がないこと
- `git diff --check`

Windowsバッチのためだけに、現時点では新しい汎用runnerや外部依存を追加しない。

## 実装順序

1. `scripts/skills/sync-skills.cmd` を追加する。
2. 引数、同期元、同期先の事前検証を実装する。
3. `SKILL.md` を基準にSkillを動的検出する。
4. Skill単位の `robocopy` 同期と終了コード判定を実装する。
5. 標準出力と最終終了コードを整える。
6. Windowsの一時ディレクトリで安全性と再同期を確認する。
7. `README.md` に利用方法と制約を追加する。
8. 既存Skill検証と `git diff --check` を実行する。

## 対象外

今回の変更では次を行わない。

- `qa-training-store` リポジトリ自体の変更
- `qa-training-store` のcommit / push
- Skill同期後のGit操作自動化
- GitHubからのclone / pull
- 双方向同期
- macOS / Linux用同期スクリプト
- PowerShell版の別実装
- Skill version管理
- commit SHAを同期先へ保存する仕組み
- 同期対象Skillの選択UIや設定ファイル
- 同期元から削除されたSkillの自動削除
- `scripts/skills/evals/` 共通評価ランタイムの同期
- Loop Engineering / Graph Engineering用の実行・評価・知見蓄積基盤

## 完了条件

- 指定した既存のSkillルートへ、`qa-workflow-skills/skills/` の全Skillを動的に同期できる。
- 同期先固有Skillを削除・変更しない。
- 同期対象の同名Skillは同期元と一致する。
- パス誤指定や `robocopy` 失敗を成功扱いしない。
- 空白を含むWindowsパスで動作する。
- PR #9等でSkillが追加されてもバッチ側のSkill一覧修正を必要としない。
- READMEだけで実行方法と上書き範囲を判断できる。
