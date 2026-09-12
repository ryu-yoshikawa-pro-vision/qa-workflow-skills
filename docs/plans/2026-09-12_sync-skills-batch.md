# Skill同期バッチ実装Plan

## 目的

`qa-workflow-skills` の `skills/` 配下にあるAgent Skillを、環境変数で指定したローカルのSkillルートへ安全に一方向同期できるWindowsバッチを追加する。

主な利用先は `qa-training-store/.agents/skills/` を想定するが、同期先パスは固定しない。

同期先に存在する固有Skillは保持し、`qa-workflow-skills` 側に存在するSkillだけを更新する。

## 対象ブランチ

`feat/sync-skills-batch`

## 既存実装との関係

- Skillの正本は `skills/<skill-name>/` にある。
- `README.md` では、Skillを利用する場合は `skills/<skill-name>/` をコピーする運用を案内している。
- `scripts/skills/` には評価用処理があるが、Skill同期用スクリプトはない。
- `qa-training-store/.agents/skills/` にはリポジトリ固有Skillが存在するため、同期先Skillルート全体をミラーしてはならない。
- PR #9ではSkill追加を予定しているため、同期対象Skill名は固定しない。

## 実装方針

### Windowsバッチを追加する

追加するファイル:

```text
scripts/skills/sync-skills.cmd
```

同期先は環境変数 `QA_WORKFLOW_SKILLS_SYNC_TARGET` から取得する。

cmd.exe:

```bat
set "QA_WORKFLOW_SKILLS_SYNC_TARGET=C:\work\qa\qa-training-store\.agents\skills"
scripts\skills\sync-skills.cmd
```

PowerShell:

```powershell
$env:QA_WORKFLOW_SKILLS_SYNC_TARGET = 'C:\work\qa\qa-training-store\.agents\skills'
.\scripts\skills\sync-skills.cmd
```

コマンドライン引数による同期先指定は追加しない。同期先の指定方法は環境変数へ一本化する。

バッチ自身はユーザー環境変数を永続設定・変更しない。

### 同期元の解決

同期元はカレントディレクトリではなく、`sync-skills.cmd` 自身の配置場所を基準に `qa-workflow-skills/skills/` を解決する。

リポジトリルート以外から実行しても同じ同期元を参照できるようにする。

### 同期対象Skillの検出

`skills/` 直下のディレクトリのうち、`SKILL.md` を持つものを同期対象とする。

```text
skills/*/SKILL.md
```

Skill名をバッチへハードコードしない。

### Skill単位で同期する

各Skillを次の単位で同期する。

```text
qa-workflow-skills/skills/<skill-name>/
  ↓
%QA_WORKFLOW_SKILLS_SYNC_TARGET%/<skill-name>/
```

Windows標準の `robocopy` を使用し、各Skillディレクトリを個別に `/MIR` する。

制約:

- `%QA_WORKFLOW_SKILLS_SYNC_TARGET%` 全体へ `/MIR` しない。
- `/MIR` は `%QA_WORKFLOW_SKILLS_SYNC_TARGET%/<skill-name>/` にだけ適用する。
- 同名Skill内では、同期元から削除されたファイル・ディレクトリも同期先から削除する。
- 同期元に存在しない同期先固有Skillは変更・削除しない。
- 同期元からSkillディレクトリ自体が削除・名称変更された場合、同期先の旧Skillディレクトリは自動削除しない。

Skill Packageは `skills/<skill-name>/` 配下をそのまま同期し、`SKILL.md`、`references/`、`assets/`、`scripts/`、`evals/` 等を個別に除外しない。

## 安全確認

コピー開始前に次を確認し、満たさない場合は非0で終了する。

- `QA_WORKFLOW_SKILLS_SYNC_TARGET` が定義され、空でない。
- 同期元 `skills/` が存在する。
- 同期先ディレクトリが既に存在する。
- 同期先が同期元 `skills/` と同一ではない。
- 同期先が同期元 `skills/` 配下ではない。
- `SKILL.md` を持つ同期対象Skillが1件以上ある。

同期先ディレクトリはバッチ側で自動作成しない。

パスに空白が含まれても動作するよう、パスは引用符付きで扱う。

環境変数の末尾 `\` の有無は同じ同期先として扱えるよう、比較・結合に必要な範囲だけ正規化する。

## `robocopy` の終了コード

`robocopy` の終了コードは次のように扱う。

```text
0〜7  : 成功
8以上 : 失敗
```

`ERRORLEVEL >= 8` の場合は対象Skill名を表示して非0終了する。

1 Skillの同期に失敗した場合は、その時点で処理を終了し、後続Skillは同期しない。

## 出力

標準出力には最低限次を表示する。

- 同期元Skillルート
- 同期先Skillルート
- 同期中のSkill名
- 同期失敗時のSkill名
- 正常終了時の同期件数

独自ログファイルは追加しない。

## README更新

`README.md` に次を追加する。

- Windows用同期スクリプトの実行方法
- 環境変数 `QA_WORKFLOW_SKILLS_SYNC_TARGET` の設定例
- 同期先には `.agents/skills/` 等のSkillルートを指定すること
- 同期先固有Skillは保持されること
- 同名Skillは `qa-workflow-skills` を正本として更新されること
- 同期元からSkill自体を削除しても、同期先の旧Skillは自動削除されないこと
- Skill一覧は動的検出されること

## 変更対象

```text
scripts/skills/sync-skills.cmd
README.md
```

新しい依存関係は追加しない。

## 検証

Windowsの一時ディレクトリを使い、少なくとも次を確認する。

1. `QA_WORKFLOW_SKILLS_SYNC_TARGET` が未設定または空の場合、コピーせず非0終了する。
2. 存在しない同期先、同期元 `skills/` 自身、またはその配下を指定した場合、コピーせず非0終了する。
3. 空白を含むパスと末尾 `\` の有無の両方で同期できる。
4. `SKILL.md` を持つ全Skillが同期される。
5. 同期先固有Skillが削除・変更されない。
6. 同名Skill内の追加・変更・削除が再同期で反映される。
7. 環境変数を別の既存Skillルートへ変更すると、同期先を切り替えられる。
8. `robocopy` が8以上を返した場合、非0終了し後続Skillを同期しない。

リポジトリ側では次を確認する。

- 既存のAgent Skills仕様・構造検証が通ること
- `git diff --check` が通ること

今回変更しないSkill本文、validator、意味評価データに対する追加の手動評価は必須にしない。既存CIで実行される検証はそのまま維持する。

## 実装順序

1. `scripts/skills/sync-skills.cmd` を追加する。
2. 環境変数、同期元、同期先の安全確認を実装する。
3. `SKILL.md` を基準にSkillを動的検出する。
4. Skill単位の `robocopy /MIR` と終了コード判定を実装する。
5. Windowsの一時ディレクトリで同期・再同期・失敗時の挙動を確認する。
6. `README.md` を更新する。
7. 既存のSkill構造検証と `git diff --check` を実行する。

## 対象外

- `qa-training-store` 側の変更
- Git操作の自動化
- clone / pull
- 双方向同期
- macOS / Linux対応
- PowerShell版の別実装
- Skill version管理
- manifest / marker fileによる所有管理
- 同期元から削除されたSkillディレクトリの自動削除
- `scripts/skills/evals/` 共通評価ランタイムの同期
- Loop Engineering / Graph Engineering用の実行・評価・知見蓄積基盤

## 完了条件

- 環境変数で指定した既存Skillルートへ、`qa-workflow-skills/skills/` の全Skillを動的に同期できる。
- 同期先固有Skillを削除・変更しない。
- 同期対象の同名Skill内は同期元と一致する。
- 同期元 `skills/` またはその配下への誤同期を拒否する。
- `robocopy` の終了コード8以上を成功扱いしない。
- 空白を含むWindowsパスで動作する。
- Skill追加時にバッチ側のSkill一覧修正を必要としない。
- READMEから設定方法と上書き範囲を判断できる。
