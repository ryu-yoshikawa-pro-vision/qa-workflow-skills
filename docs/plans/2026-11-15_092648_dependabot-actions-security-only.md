# GitHub Actions の security-only 更新を設定する

## Goal

GitHub Actions の既知脆弱性に対する Dependabot security update PR を受け取れる構成案を作る。通常のversion update PRは発生させない。

## Current state

- 認証済みの既定ブランチ `main` は `78d8d394dc0d985b2b7aa60c656851fa07947398`。
- 既定ブランチに `.github/dependabot.yml` はない。GitHub Actionsのworkflowは5件あり、外部Action参照がある。
- PR #36 はPython開発依存manifestを提案中で、未merge。既定ブランチにはPython manifestがまだないため、このPRではGitHub Actions ecosystemのみ設定する。
- Dependabot security updatesのGitHub側toggleとalert状態は、この接続から確認できない。設定ファイルだけで有効化済みとは扱わない。

## Existing contracts

- ユーザー指示により、全repositoryはsecurity-only。通常のversion-update PRを作成しない。
- GitHubのDependabot security update仕様では、security updatesはversion updatesとは別の仕組みであり、`open-pull-requests-limit: 0`で該当ecosystemのversion update PRを停止できる。Actions対象は`package-ecosystem: github-actions`、`directory: /`、scheduleが必要で、security update設定に適用させるため`target-branch`は指定しない。
- 既存workflow、PR #36、既定ブランチ、repo settingsは変更しない。mergeしない。

## Scope

### Included

- `.github/dependabot.yml`にGitHub Actionsのentryを1件追加する。
- scheduleは必須項目としてweeklyを記録し、`open-pull-requests-limit: 0`により通常version-update PRを抑止する。
- YAMLと差分を検証し、作業branchからPRを作成する。

### Excluded

- Python ecosystemの追加。PR #36が既定ブランチに反映されてから別途設定する。
- GitHubのsecurity-update toggle、alerts、permissionsの変更。
- PRのmerge/close、既存workflowやActions参照の変更。

## Risks and assumptions

- GitHubのsecurity-update toggleは未確認であり、このPRだけではsecurity PRの実動作を証明しない。
- weeklyはDependabotのversion-update設定に必要な確認周期であり、open PR上限0で通常のversion-update PRを作らない。security updatesの個別動作は設定反映後に確認する。
- 既存PR #36と他のopen PRは本PRと対象ファイルが重ならない。

## Implementation order

1. `.github/dependabot.yml`をActions ecosystemのみで作成し、target-branchを指定しない。
2. YAML構文、ecosystem、directory、limit、scope-only diffを個別に検証する。
3. PRを作成し、最新headのCIを確認する。mergeしない。

## Validation

- YAML parserで構文を確認する。
- 生成されたdiffが計画どおりの設定と計画書だけであることを確認する。
- PR headのCI結果を記録する。未実施・失敗・pendingはPASSと区別する。
- Dependabot security update toggle、alerts、およびPR実動作の検証はT01/T09のアクセスが得られるまでblockedとして扱う。

## Completion criteria

- security-only設定を含む作業branchとOpen PRが存在する。
- YAML検証が成功し、最新PR headのCI結果が記録されている。
- mainへの反映とsecurity update実動作は完了扱いにしない。

## 実行記録

- 2026-11-15 09:26 JST: current `main` `78d8d394dc0d985b2b7aa60c656851fa07947398`からbranch `codex/security-actions-dependabot-20261115`を作成。
- 2026-11-15 09:27 JST: PyYAML 6.0.1 parse PASS。schema assertions PASS（Actions ecosystem、`/`、weekly、PR limit 0、`target-branch`なし）。`git diff --check` PASS。
- PR作成とPR-head CIは未実施。GitHub security-update toggle/alert状態は未確認。
