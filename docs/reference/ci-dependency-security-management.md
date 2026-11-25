# CI依存関係とGitHub security設定の調査

調査日: 2026-11-25
対象main: `a37b15508dadd17ac0228ac896badb71d6a8f2c7`
関連Plan: [GitHub Actionsの最小権限化と依存関係のセキュリティ管理整備](../plans/2026-11-25_011800_ci-security-hardening.md)

## 調査範囲と確度

調査対象は、5つのGitHub Actions workflow、そこから起動するscripts/tests、Python requirements、Dependabot、dprint CLI/plugin、skills-ref、Codex CLI、GitHub側のsecurity設定である。mainのコード、PR #22・#36・#37 metadata、GitHub Actions runs、main ruleset、GitHub公式仕様を照合した。

GitHub app接続ではmainのworkflow runs・ruleset・repository metadataは取得できた一方、code scanning / Dependabot alerts、Dependency graph内容、SettingsのSecurity and analysis / Actions permissions、Dependabotのupdate job・config errorは許可対象外だった。依頼者の指示によりgh CLIも利用し、PR #39のhead 62f443b27968369784ab69fe4008ed514b17bda1の全5 workflowとCodeQL aggregate / Analyze checksがsuccessであることを確認した。依頼者が同日にUIで確認した設定・Dependency graph 15 referencesは提供された背景情報として記録し、今回のCLI直接確認とは区別する。

## 現在のCI経路とGitHub token権限

| Workflow                         | 発火条件                       | `uses`                                            | install / test経路                                                                                           | 現状と必要権限                                                                                               |
| -------------------------------- | ------------------------------ | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `code-quality.yml`               | PR、main push                  | `checkout@v4`, `setup-python@v5`, `setup-node@v4` | Ruff / dprint、formatter契約test、patch whitespace、security config回帰test、tracked file check              | workflow-level `contents: read`を維持。PR branchでeval requirementsをinstallしてsecurity config testを追加。 |
| `codex-harness.yml`              | PR、main push                  | `checkout@v4`, `setup-python@v5`, `setup-node@v4` | Codex CLI、Node Hook syntax、`tests/codex`、Git URL版skills-ref、開発Skill validation。Linux / Windows job。 | workflow-level `contents: read`あり。変更不要。                                                              |
| `validate-skills.yml`            | PR、main push、manual dispatch | `checkout@v4`, `setup-python@v5`, `setup-node@v4` | Git URL版skills-ref、全Skill validation、eval構造、form/trigger/semantic tests                               | `contents: read`を明示する。                                                                                 |
| `deterministic-output-evals.yml` | PR、main push、manual dispatch | `checkout@v4`, `setup-python@v5`                  | PyYAML、deterministic/runtime/semantic scripts・tests                                                        | `contents: read`を明示する。                                                                                 |
| `semantic-output-evals.yml`      | PR、main push、manual dispatch | `checkout@v4`, `setup-python@v5`                  | semantic dataset validation・tests                                                                           | `contents: read`を明示する。                                                                                 |

5 workflow全体で、Actions参照は`checkout@v4`が5件、`setup-python@v5`が5件、`setup-node@v4`が3件。workflow/呼出先を確認し、`GITHUB_TOKEN`や`secrets`の参照、GitHub CLI/API呼出、repositoryへのGit書き込み、artifact upload/download、workflow dispatch、issue/PR/comment/status更新は見つからなかった。ローカルGitを読むformatter helperや、fixtureでGit操作を試す契約testsは、GitHub repositoryへの書込み経路ではない。

したがって、3対象にはworkflow-level `permissions: contents: read`を設定する。`permissions`を明示すると列挙されないscopeは`none`になる。`contents: read`はcheckout等のrepository読み取りに限定され、job単位の書込みpermissionは不要である。

### 現行mainのCI・ruleset確認

main HEAD `a37b155…`への2026-11-24 pushに対する5 workflowは全てsuccess。Codex HarnessのLinux / Windows jobもsuccessし、両方のCLI出力は`codex-cli 0.172.0`。CodeQL default-setup runもsuccessした。

| Workflow / scan                     |        run ID | URL                                                                                     |
| ----------------------------------- | ------------: | --------------------------------------------------------------------------------------- |
| Code Quality                        | `45431363663` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363663 |
| Codex Harness                       | `45431363456` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363456 |
| Validate Agent Skills               | `45431363902` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363902 |
| Validate Deterministic Output Evals | `45431363541` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363541 |
| Validate Semantic Output Evals      | `45431363728` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363728 |
| CodeQL default setup                | `45431362292` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431362292 |

`gh ruleset view 24843922`でactive `protect-main`がdefault branchに適用されることを確認した。bypass不可で、PR、required linear history、`validate` / `deterministic-output-evals` / `semantic-output-evals`の3 required statusを設定。required approving review countは0、required review thread resolutionは有効、strict status checksは無効。CodeQL、Code Quality、Codex Harnessはrequired statusではない。PR #39のhead `62f443b27968369784ab69fe4008ed514b17bda1`ではCodeQL aggregate checkおよびAnalyze (actions / javascript-typescript / python) がsuccess。mainのscan successも確認済みだが、main上のalertのOpen/Closed状態は別途未確認。

`gh repo view`ではrepository visibilityがpublic、default branchが`main`、`isSecurityPolicyEnabled`がfalseであることを確認した。security policy文書の有効化判断は今回のscope外で、設定変更は行っていない。

## 依存関係一覧

| 依存関係                     | 用途 / 現在のversion                                                                | version正本                                                              | Dependency graph / Dependabot                                                                            | 優先度                          |
| ---------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ------------------------------- |
| Ruff                         | Python lint/format、`0.16.8`                                                        | `requirements-dev-lint.txt`                                              | pip manifest。依頼者が15件のgraph内で1 referenceを確認。pip security updates対象。                       | P1: CI直接依存                  |
| PyYAML                       | Deterministic Eval validation、`6.0.3`                                              | `requirements-dev-evals.txt`                                             | pip manifest。依頼者が15件のgraph内で1 referenceを確認。pip security updates対象。                       | P1: CI直接依存                  |
| GitHub Actions               | checkout `v4`、setup-python `v5`、setup-node `v4`                                   | 各workflowの`uses`                                                       | workflow manifest。依頼者確認のgraphに13 references。Actions security updates対象。                      | P1: CI直接依存                  |
| dprint CLI                   | Code Quality formatter、npm global `0.55.2`                                         | workflow / README / `scripts/format_tracked.py`                          | npm manifest/lockfileなし。依頼者確認のgraphにない。                                                     | P2: CI formatter                |
| dprint plugins               | 5つのremote Wasm plugins、各version+SHA-256                                         | `dprint.json`                                                            | raw URL形式は依頼者確認のgraphにない。Dependabot ecosystemでのURL追跡は確認できず、対象外とする。        | P2: dprint実行時依存            |
| skills-ref                   | Agent Skills validation、upstream commit `69ef37e9424c0a7ea9dd2293b559e43ec8176379` | workflow内Git URL                                                        | Python manifest外。依頼者確認のgraphにない。Git SHAをDependabotがpip security-update対象にするか未確認。 | P2: CI validator                |
| Codex CLI                    | Codex Harness Linux/Windows、`@latest`。main run上の実行version `0.172.0`           | `codex-harness.yml`のinstall command。`codex --version`をrun logへ記録。 | npm manifest/lockfileなし。依頼者確認のgraphにない。                                                     | P2: 安全ハーネスの現行CLI互換性 |
| Python / Node / runner image | Python `3.11`、Node `24`、`ubuntu-latest` / `windows-latest`                        | setup actionとGitHub runner image                                        | language package依存ではなく、上記workflowのActionとは別にDependabot manifestでは管理されない。          | P3: provider-managed            |

### Dependabotの更新周期と開発依存の自動却下

`.github/dependabot.yml`のGitHub Actions / pip両entryは`schedule.interval: weekly`と`open-pull-requests-limit: 0`を使う。GitHub公式仕様で`schedule`は通常のversion updatesを確認する周期を定める。`open-pull-requests-limit: 0`は通常のversion-update PRを無効にする一方、security updatesには適用されない。security updateは脆弱性advisoryから生じるDependabot alertにより起動し、weekly scheduleはsecurity updatesの実行周期を定めない。Settings上のsecurity updates toggleは別に有効である必要があり、現況は未確認。

GitHubのdevelopment-scoped low-impact presetは、`ecosystem:npm`および`scope:development`のalert metadataとGitHubが定める脆弱性条件を満たしたnpm開発依存のalertを自動却下する。RuffとPyYAMLはpip ecosystemのため、このpresetの対象外である。依頼者の前回UI確認ではpresetはEnabledだったが、現在値は未確認。別のcustom auto-triage ruleや手動却下の有無も取得できておらず、このpresetの適用範囲からは推定しない。

### Ruff

| 項目                                 | 記録                                                                                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 正式名 / 用途                        | Ruff。repository内tracked Pythonのlint/import/format。                                                                                     |
| 現在のversion / 正本                 | `0.16.8`。唯一pinは`requirements-dev-lint.txt`。version表示とlint/import/formatは共通script経由。Ruff対象fileがある処理前にpinを照合する。 |
| Dependency graph                     | 依頼者がmainのgraphで認識済み1件を確認。pipのrequirements manifestで宣言。                                                                 |
| Dependabot alerts / security updates | pip manifest対象。通常のversion-update PRはlimit 0。npm開発presetの対象外。toggleの最新状態は未確認。                                      |
| 現在のリスク                         | npm向けpresetはRuffに非適用。別ruleや手動却下の有無は未確認。                                                                              |
| 推奨対応 / 変更先                    | pin正本はrequirements、実行入口は共通scriptとする。                                                                                        |
| 検証                                 | pin / CLI照合の回帰test、Code Quality CI。                                                                                                 |
| 優先度                               | P1。CI lint直接依存。                                                                                                                      |
| 未確認                               | graphの現行画面・alert状態、auto-dismissの現在値、最新Dependabot status。                                                                  |

### PyYAML

| 項目                                 | 記録                                                                                                                               |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| 正式名 / 用途                        | PyYAML。Deterministic Output Evalがeval YAMLを読み込む。                                                                           |
| 現在のversion / 正本                 | `6.0.3`。`requirements-dev-evals.txt`。`EVALS.md`の有効な導入例はversionを直接記載していた。今回、例をmanifest installへそろえる。 |
| Dependency graph                     | 依頼者がmainのgraphで認識済み1件を確認。Dependabot docsはpipの`.txt` manifestを対象とする。                                        |
| Dependabot alerts / security updates | pip security-only config対象。通常PRはlimit 0。npm開発preset対象外。状態未確認。                                                   |
| 現在のリスク                         | 明示pinはある。lockfileではないため、推移依存の完全な固定はrequirementsだけでは保証しない。                                        |
| 推奨対応 / 変更先                    | 既存requirementsを正本とし、`EVALS.md`から同versionの直接指定を除く。PyYAMLのversionは変更しない。                                 |
| 検証                                 | requirements参照、Deterministic Eval validation/test、YAML parse。                                                                 |
| 優先度                               | P1。CI validation直接依存。                                                                                                        |
| 未確認                               | graphの現行表示、依存関係の完全なtransitive snapshot、alerts。                                                                     |

### GitHub Actions

| 項目                                 | 記録                                                                                                                            |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| 正式名 / 用途                        | `actions/checkout@v4`、`actions/setup-python@v5`、`actions/setup-node@v4`。checkout、Python 3.11、Node 24環境。                 |
| 現在のversion / 正本                 | workflowの`uses`。checkout 5 references、setup-python 5、setup-node 3。                                                         |
| Dependency graph                     | 依頼者がgraphで5+5+3=13 referencesを確認。GitHub Actions workflowはGitHubがmanifestとして読む。                                 |
| Dependabot alerts / security updates | Actions ecosystemが有効。alertsとsecurity updatesはsecurity feature toggleにも依存。security PRは通常version-update limitと別。 |
| 現在のリスク                         | `v4` / `v5` major tag参照はCI sourceで固定SHAではない。今回のversion変更対象外。                                                |
| 推奨対応 / 変更先                    | 現行GitHub Actions security-only entryを維持し、security update PRはreviewと全CIを通してからmerge。SHA pinningは別途判断する。  |
| 検証                                 | YAML parse、Dependabot config、PR上の全workflow run。                                                                           |
| 優先度                               | P1。全PR CIの実行コード。                                                                                                       |
| 未確認                               | graph現在値、alert counts、自動更新設定エラー、workflow dependency lockfile導入有無（repo内にlockfileはなし）。                 |

### dprint CLI

| 項目                                 | 記録                                                                                                                                                                                                                                                    |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 正式名 / 用途                        | dprint CLI。Code Quality workflowと`format_tracked.py`がtracked Markdown/JSON/YAML/TOML/JS等を整形・検査する。                                                                                                                                          |
| 現在のversion / 正本                 | `0.55.2`。workflow global npm install、README、`DPRINT_VERSION`照合に記載。`scripts/format_tracked.py`はCLI versionが一致しないとformatter実行前に停止する。                                                                                            |
| Dependency graph                     | package.json / package-lockがなく、inline `npm install --global dprint@0.55.2`はstatic manifestではない。依頼者確認済みgraphにない。                                                                                                                    |
| Dependabot alerts / security updates | npm ecosystemでmanifest+lockfileを導入すればregistry packageを管理できる見込み。現状はnpm manifestがないので設定追加だけでは追跡できない。                                                                                                              |
| 現在のリスク                         | 直接CLI versionは固定・実行時照合されるが、repoにnpm-resolved tree / lockfileがなく、CLI npm packageの依存metadataとCIに実際に入ったpackage treeは保存されない。README/workflow/Python constantで固定値を複数管理。                                     |
| 推奨対応 / 変更先                    | 別実装としてroot `package.json` / `package-lock.json`のdevDependencyへ同じdprint versionを一度だけ宣言し、CIは`npm ci`へ移す案が最も有力。dprintのversion guardは残し、manifestの値から期待versionを導出する。npm Dependabot entryはlimit 0を追加する。 |
| CI/ローカル互換性                    | `npm ci`とlocal `node_modules` CLIの解決をWindows, Linux, WSL2で試す。GitHub ActionsでPATHへlocal binを安全に追加するか、formatter helperをlocal binary解決に対応させる必要がある。現在のglobal install方法とREADME CLI利用手順を同時に移す。           |
| 検証                                 | Linux/Windows/WSL2で同じCLI version、`format_tracked.py check`, `test_format_tracked.py`, formatterの全対象diff、Code Quality CIを比較する。version mismatchがformatter file write前に失敗する既存testを保持・拡張する。                                |
| 優先度                               | P2。CI/ローカルで実行するformatterだが、直接version checkがある。                                                                                                                                                                                       |
| 未確認                               | npm registry上のdprint `0.55.2` packageの正確なtransitive/optional package tree、現在のinstall先ごとのbinary依存関係。manifest化前にnpm lock生成と`npm ls --all`で確定する。                                                                            |

### dprint plugins

| Plugin                  | 取得元 / version                                     | 記載checksum                                                       |
| ----------------------- | ---------------------------------------------------- | ------------------------------------------------------------------ |
| TypeScript / JavaScript | `plugins.dprint.dev/typescript-0.96.1.wasm`          | `9c52244de2c25a33addc7ddacff4443234a2dc4b5d3f34131262d1e0df35007c` |
| JSON                    | `plugins.dprint.dev/json-0.23.0.wasm`                | `3e1f1b7c1427df6bd8981a11aaa2c466fde8d1115e9dde4c652130458539443c` |
| Markdown                | `plugins.dprint.dev/markdown-0.22.1.wasm`            | `4906fbb038977732aae0e216e4b0b957e2722f8d79282660ccb36d27dd051f17` |
| TOML                    | `plugins.dprint.dev/toml-0.8.0.wasm`                 | `69cb40cba5e8a53560ccea7fdced073a55d04eb05492f0d9b877f916b976945d` |
| Pretty YAML             | `plugins.dprint.dev/g-plane/pretty_yaml-v0.6.0.wasm` | `40a2fdda7040317eb1b23520f3a00769a5571eedb049c4ca9175c1b9eeba01ae` |

| 項目                   | 記録                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用途 / 現在のversion   | `dprint.json`で各pluginをformat対象に接続。前表の各versionを使用。                                                                                                                                                                                                                                                                                                                                                                |
| version正本            | `dprint.json`のremote URL。`@`以降にchecksumを持つ。                                                                                                                                                                                                                                                                                                                                                                              |
| Dependency graph       | URL+Wasmはnpm/pip/action manifestではなく、現在のgraphが認識したとは確認できない。GitHub Dependabotがdprint plugin URLを直接更新するecosystem対応も確認できない。                                                                                                                                                                                                                                                                 |
| Integrity / 脆弱性管理 | dprint公式仕様はURL checksumがfile SHA-256で、不一致時に失敗することを示す。dprint公式はWasm pluginをsandboxedと説明する。Checksumは取得物の改ざん検出に役立つが、脆弱な正規版をalertするものではない。                                                                                                                                                                                                                           |
| 推奨対応 / 変更先      | checksum付きURL pinを保持。将来はdprint公式に掲載のnpm packages（`@dprint/typescript`, `@dprint/json`, `@dprint/markdown`, `@dprint/toml`, `dprint-plugin-yaml`）をpackage-lockに含める案を検討できる。unversioned `npm:` plugin specifierでlockfileをsource of truthにする機能がdprint docsにある。ただし現行CLI `0.55.2`での互換性・同一Wasm bytes・設定形式・plugin対応versionはこの調査では試していないため、今は変更しない。 |
| 検証                   | 互換性PoC後、現行CLIでconfig load、すべてのtracked formatter targetのbefore/after output、`format_tracked.py check`, `test_format_tracked.py`, Windows/Linux/WSL2 CIを確認する。plugin version updateはformat diffを必ずreviewする。                                                                                                                                                                                              |
| 優先度                 | P2。CIで多数のtracked textを処理。digest pinとWasm sandboxが緩和要素。                                                                                                                                                                                                                                                                                                                                                            |
| 未確認                 | URL pluginのGraph/Dependabot alert support、現在のCLIでnpm specifier/lockfile利用可能か、npm tarball integrityと現行URL Wasm bytesの一致、pluginごとの公開advisory。                                                                                                                                                                                                                                                              |

### skills-ref

| 項目                                 | 記録                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 正式名 / 用途                        | Agent Skills upstream repository `agentskills/agentskills` subdirectory `skills-ref`。Validate Skills workflowとCodex Harness Linux jobで`skills-ref validate`を使う。                                                                                                                                                                                                            |
| 現在のversion / source pin           | Git commit `69ef37e9424c0a7ea9dd2293b559e43ec8176379`、subdirectory `skills-ref`。両workflowで同一のcommit SHA。                                                                                                                                                                                                                                                                  |
| 直接/間接依存関係                    | pinned commitの`skills-ref/pyproject.toml`ではproject version `0.1.0`、Python `>=3.11`、直接runtime dependencies `click>=8.0`、`strictyaml>=1.7.3`。PEP 517 build dependencyは`hatchling`。これらruntime/build dependenciesのtransitive versionsはlockfile/constraintがなく、install時に解決される。upstream sourceを見るとdev-only `pytest`/`ruff`はCI実行には宣言されていない。 |
| Dependency graph                     | 現状requirements manifestにはなくworkflow shellでVCS installするため、依頼者確認graphでは未認識。pip graphがGit VCS requirementをどこまで記録するかは、GitHub公式docsで明確に保証されている形式を確認できなかった。                                                                                                                                                               |
| Dependabot alerts / security updates | GitHub repo SHA・依存名とPython package versionをgraphに載せる経路が未確立なので、現状はalert / updateを受けると保証できない。requirements `.txt`へ移す場合も、VCS URL・commit pinのDependabot対応は実 graph/update jobで検証が必要。                                                                                                                                             |
| 現在のリスク                         | immutable commitでソース再現性はあるが、upstream修正を自動追跡しない。transitive PyPI dependenciesとbuild backendはfloatし、現在のworkflow installを完全には再現できない。                                                                                                                                                                                                        |
| 推奨対応 / 変更先                    | upstream repository + immutable SHA方針を維持し、upstream advisory/release/commitを人手reviewしたうえでSHA更新を専用PRで行う。requirements fileへの移行はDependabotがVCS pinとsecurity fixesをどう扱うかを小さな検証で確認後に判断する。別PyPI packageやbranch/`latest`へ切替えない。                                                                                             |
| 検証                                 | SHA更新PRはPython 3.11の両install path、全Skill `skills-ref validate`、開発Skill validationと対象CIを実行。VCS manifest案はDependency graph表示、Dependabot config/update job、ロック/解決versionも確認する。                                                                                                                                                                     |
| 優先度                               | P2。全SkillのCI validator。SHA固定でsourceは再現可能だが、security updatesの自動経路はない。                                                                                                                                                                                                                                                                                      |
| 未確認                               | GitHub graphがGit URL依存を認識するか、Dependabotがcommit pinをsecurity update PRへ変更できるか、CI実行時のclick/strictyaml/hatchlingとそのtransitive version。                                                                                                                                                                                                                   |

> PyPIの`skills-ref`名のpackageに切り替える案は採用しない。upstream repository issueでは、PyPI packageの公開者はupstreamではなく、upstream maintainersはその公開packageを管理していないと明記されている。

### Codex CLI

| 項目                                 | 記録                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 正式名 / 用途                        | `@openai/codex`をCodex Harness Linux/Windows jobでinstallし、Hook/execpolicy/config/launcherの安全contractを現在のstable CLIで確認する。                                                                                                                                                                                                                                                                                   |
| 現在のversion / 正本                 | `npm install --global @openai/codex@latest`。main run `45431363456`の両jobで`codex-cli 0.172.0`を`codex --version`出力へ記録。sourceのversion pinは意図的にない。                                                                                                                                                                                                                                                          |
| 依存関係                             | workflow sourceはnpm packageを直接install。GitHub Actions logにはCLI versionを記録するが、`npm ls -g --all`やpackage tree/SBOM、lockfileは記録しない。npm pageは`0.172.0`を`0 Dependencies`として表示するが、CIで得られるinstalled files/treeやOS別package内容をrun artifactに保存する契約はない。                                                                                                                         |
| Dependency graph                     | root npm manifest/lockfileがなく、shell global installからstatic npm manifestは作られない。依頼者確認のgraphにない。                                                                                                                                                                                                                                                                                                       |
| Dependabot alerts / security updates | graph entryなしでは自動alert/updateを受ける保証がない。latest tagはsecurity vulnerability response経路と同じではない。                                                                                                                                                                                                                                                                                                     |
| 現在のリスク                         | Harnessが利用するCode CLIは毎回変わり得る。run logsでCLI versionを遡れるが、transitive package treeを再構築する情報が残らない可能性がある。latest使用はCLIの将来互換を試すための明示契約。                                                                                                                                                                                                                                 |
| 推奨対応 / 変更先                    | `latest`は維持。将来管理する場合は、実際に解決したLinux/Windows package snapshot（npm graphまたはSBOM）を生成してdependency submission APIで提出する方法を検討する。GitHub docsはAPI submissionがmanifestsで捉えられないbuild dependenciesもgraph化できるとし、GitHub Actions submission例ではrepository `contents: write`が必要。submissionは専用jobに隔離し、最小job-level permission、別途security reviewを必要とする。 |
| 検証                                 | `@latest` installとversion outputを継続、Linux/Windows両jobで安全Harness contractsを実行。submission案はsnapshotのpackage identity/version、2 OSの重複・相違、graph表示、既知advisoryの扱い、`contents: write`を専用job外へ漏らさないことを確認。                                                                                                                                                                          |
| 優先度                               | P2。security harnessの実CLIだが、`@latest`は目的上の意図的設計。                                                                                                                                                                                                                                                                                                                                                           |
| 未確認                               | 古いrun logsのretention、current workflow run以外での実際のnpm package tree、dependency snapshot APIでの複数OS snapshotのUI表示とadvisory correlation。                                                                                                                                                                                                                                                                    |

### Python / Node / GitHub runner toolchains

- Workflowsは`actions/setup-python@v5`でPython `3.11`、`actions/setup-node@v4`でNode `24`、`ubuntu-latest` / `windows-latest` hosted imagesを選ぶ。Python/Node patch buildsとhosted image software updateはGitHub/setup actions側で管理されるため、このrepositoryのDependabot manifest dependencyではない。
- Main/PR CIはtoolchain updatesの実証手段であり、current image contentsはper-run log/runner image release notesで確認する。
- 新しいruntime manifestやDocker imageは今回追加しない。Hosted runner release notes、setup action announcementsを別途監視する。

## GitHub repository security settings

| 設定 / state                                             | 2026-11-25に取得できた内容                                                                                                                                                                              | UI確認方法 / 次の対応                                                                                                                                                                                         |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dependency graph                                         | 依頼者の同日確認ではON。今回APIでは未確認。                                                                                                                                                             | [Dependency graph](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/network/dependencies)でRuff/PyYAML/Actionsおよび新manifestを検索。                                                          |
| Dependabot alerts                                        | 依頼者確認はOpen 0 / Closed 0。現行値未確認。                                                                                                                                                           | [Dependabot alerts](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/security/dependabot)でOpen/Closed数とauto-dismissed queryを確認。                                                          |
| Dependabot security updates                              | 依頼者確認ではON。現在値未確認。                                                                                                                                                                        | [Security analysis settings](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/settings/security_analysis)のDependabot security updatesを確認。                                                  |
| Grouped security updates                                 | 依頼者確認ではOFF。現在値未確認。                                                                                                                                                                       | 同Settingsのgroupingを確認。依頼ではOFFを推奨。                                                                                                                                                               |
| Automatic dependency submission                          | 依頼者確認ではDisabled。現在値未確認。PythonはGitHub docs上Dependabot graph jobsが自動submissionに優先し、dependency graphを有効にすればPython graph jobが使われる。                                    | 同Settingsで設定値を確認。今回変更しない。                                                                                                                                                                    |
| Malware alerts / dismiss malware alerts                  | 前回malware alerts OFF、dismiss package malware alerts Disabledとの申告。最新値未確認。推奨はMalware alerts ON、dismiss Disabled。                                                                      | Security analysis settingsで両方を確認。                                                                                                                                                                      |
| Dismiss low-impact dev-scoped alerts                     | 前回Enabledとの申告。現況未確認。presetは条件を満たすnpm dev alert向け。Ruff/PyYAMLはpipのため対象外。                                                                                                  | 設定とcustom ruleをUI確認。今回変更しない。                                                                                                                                                                   |
| Auto-triage rules                                        | 現在のrule一覧にアクセス不可、最新値未確認。                                                                                                                                                            | [Dependabot alerts](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/security/dependabot)からRulesを開き、auto-dismiss/ignore設定を確認。Alert listの`resolution:auto-dismissed` filterを確認。 |
| Secret Protection / push protection                      | 依頼者の推奨状態はON。今回未確認。                                                                                                                                                                      | Security analysis settingsからSecret Protection、push protectionを確認。                                                                                                                                      |
| CodeQL analysis                                          | main HEAD `a37b155…`のCodeQL default-setup run `45431362292`はsuccess。Alerts状態は未確認。                                                                                                             | [Code scanning alerts](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/security/code-scanning)でAlert #1/#2/#3の状態を確認。                                                                   |
| Main ruleset / required checks                           | APIでactive `protect-main`を確認。PR、linear history、required statuses 3件: `validate`, `deterministic-output-evals`, `semantic-output-evals`。CodeQL, Code Quality, Codex Harnessはrequiredではない。 | [protect-main](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/rules/24843922)。Review後にsecurity checkをrequiredにする判断は今回のscope外。                                                  |
| Default `GITHUB_TOKEN` permission                        | GitHub app allowlistからActions permission settings endpointを取得できず未確認。                                                                                                                        | [Actions settings](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/settings/actions)のWorkflow permissionsを確認。workflowごとのexplicit permissionsはこの設定を上書きして絞る。               |
| Branch ruleset code scanning gate                        | Rulesetでrequired statusにCodeQL checkがないことを確認。                                                                                                                                                | 将来CodeQL required statusをmerge gateとするかをowner判断で別途決定。                                                                                                                                         |
| Private vulnerability reporting                          | 未確認。                                                                                                                                                                                                | [Security advisories](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/security/advisories)とSecurity analysis settingsで確認。                                                                 |
| Dependabot config / manifest errors / recent update jobs | alerts/update APIが接続allowlist外で未確認。                                                                                                                                                            | [Dependabot update runs](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/network/updates)とSecurity and quality画面でfile parse/config error、最近のpip/GitHub Actions jobを確認。             |

GitHub app接続によるGETでは`/code-scanning/alerts`および`/dependabot/alerts`が許可endpointでないとして拒否され、main branch protectionは403となった。rulesetとrepository metadataは読み取り専用の`gh ruleset` / `gh repo` subcommandで確認できたが、code scanning / Dependabot alerts、Dependency graph、Security settingsには許可された読み取り専用subcommandがなく未確認。Repository safety harnessが`gh api`を禁止するため実行していない。画面で確認する場合はPR作成者またはrepository adminが上表のURLを開き、設定値・Alert件数・更新job・manifest errorを記録する。

## GitHub公式仕様と一次情報

- [CodeQL query: Workflow does not contain permissions](https://codeql.github.com/codeql-query-help/actions/actions-missing-workflow-permissions/): repository/org default token permissionを利用するworkflowに対し、workflow/job levelの最小権限を明示する推奨。
- [GitHub Actions workflow syntax: permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions): workflow-level/job-level設定、未指定scopeが`none`になる挙動、`contents: read`の意味。
- [Configuring Dependabot security updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates): `open-pull-requests-limit: 0`、`directory`、`target-branch`条件。
- [Dependabot pull requests](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-pull-requests): security updatesはadvisory-triggeredであり、version updateの`schedule`による周期ではない。
- [GitHub preset rule criteria](https://docs.github.com/en/code-security/reference/supply-chain-security/criteria-for-preset-rules): development-scoped low-impact presetが`ecosystem:npm` / `scope:development`等を満たすnpm alertに適用される条件。
- [Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference): `open-pull-requests-limit`はversion updates向けでsecurity updateは別limit、pip/GitHub Actions ecosystems。
- [How the dependency graph recognizes dependencies](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-graph-data)と[Dependabot supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories): manifest/lockfile、pip `.txt`、GitHub Actions workflow recognition。Static graphはlockfileがないとresolved transitive dependencyを完全に固定しない。
- [Using dependency submission API](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/use-dependency-submission-api): build-time dependency snapshotを追加できる。submissionをGitHub Actionsから実施する場合の必要permissionを個別設計する。
- [dprint configuration: plugins](https://dprint.dev/config/) / [dprint plugin catalog](https://dprint.dev/plugins/): URL SHA-256 checksum、npm specifier/package-lock利用、WASM plugin方式。
- [Pinned skills-ref source manifest](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/skills-ref/pyproject.toml): CIで使うcommitのversion/runtime/build dependencies。
- [upstream clarification on the unrelated PyPI package](https://github.com/agentskills/agentskills/issues/355): upstream contributorは、PyPI上の同名packageがupstream管理下にないと明記。
- [Codex CLI npm package](https://www.npmjs.com/package/@openai/codex): package identity/install経路。CIで実際に導入したversionはActions job logの`codex --version`を正とする。

## 推奨する後続優先度

1. 今回のPRをmerge後、mainの全CI/CodeQL scan、Alert #1〜#3の自動解消、Dependency graph・Dependabot error・security update toggleを確認する。low-impact開発依存のauto-dismissやMalware alerts等もRepository ownerがUIで確認する。
2. dprint CLIをpackage.json/package-lockへ移す小さなcross-platform PoCを行う。`DPRINT_VERSION`照合をmanifestから導出し、既存CI/ローカル契約とformat bytesを維持できることを確認する。
3. dprint pluginsをnpm lockfile管理へ移す場合、dprint `0.55.2` compatibilityとformat output equivalenceを確認し、npm ecosystemをsecurity-onlyにする。remote URL+SHA pinは検証完了まで保持する。
4. skills-refのupstream SHAを維持し、advisory/release監視とreview済みSHA更新を運用する。VCS requirements化はGitHubの実graph/update対応を先に検証する。
5. Codex CLIは`latest`を継続し、次の管理強化はLinux/Windowsそれぞれの実解決tree/snapshotを記録・submissionする案を別途設計する。submission permissionと2 OSのsnapshot相関を含むため、今回のRead-only workflowに安易に追加しない。
6. Python/Node toolchain、hosted imageはGitHub/setup actionsのrunner image release notesから変更影響を追う。

## マージ後の受入条件

- mainの5 workflowが新main HEADでsuccess。Codex Harness Linux/Windows両jobを確認。
- 修正後mainのCodeQL scan完了後、Alert #1/#2/#3が該当workflow行の修正として解消。manual dismissはしない。
- Dependency graphでRuff / PyYAML / GitHub Actionsが認識済みで、pip entry追加によるmanifest読み取りerrorがない。
- Dependabotに設定errorがなく、通常version-update PRはlimit 0で作成されず、security updatesはSettingsで有効。
- GitHub Security and analysis settingsのauto-dismiss、malware、Secret Protection/push protection、private reportingとActions token defaultをownerが確認。未達項目は未達として記録。
- 脆弱性がないことによってsecurity update PRが作られない場合は正常。動作確認用に脆弱versionを導入しない。
