# GitHub Actionsの最小権限化と依存関係のセキュリティ管理整備

## Goal

PR #22・#36・#37反映後の`main`を基準に、CodeQLの`actions/missing-workflow-permissions` Alert 3件を最小権限設定で解消し、Dependabotのpip security-only方針を明示する。Ruffの固定バージョンの正本をrequirementsファイルにそろえ、CI依存関係の管理可否・リスク・後続対応を記録する。

PR #22で導入されたQA workflow、Skill、runtime、validator、評価基盤、安全ハーネス、CIの発火条件・検証範囲・バージョンを変えない。実装、ローカル検証、レビュー、指摘修正、再検証、作業branchへのpush、新規PR作成まで行う。mainへのmergeは行わない。

## Current state

### GitとPR

- repository: `/mnt/c/Users/ryu-yoshikawa/Documents/qa-workflow-skills`
- 作業branch: `fix/ci-security-hardening`
- 開始HEAD: `a37b15508dadd17ac0228ac896badb71d6a8f2c7`
- fetch後の`origin/main`: `a37b15508dadd17ac0228ac896badb71d6a8f2c7`。開始HEADと一致。
- 開始時のtracked / untracked working treeに変更なし。
- origin: `https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills.git`
- PR #22はmerge commit `a37b155…`、PR #36は`2fccab195e3cc68f175d7d380e2378816ec9ef1d`、PR #37は`9c5fa06f277439d365b9df87d6d45909d79a1bf5`でmerge済み。各PRのbase/head/merge commitをGitHub接続から確認した。PR #37の既存Planは履歴記録として変更しない。
- GitHubのbranch検索では`main`を確認し、`fix/ci-security-hardening`のremote refはまだ見つからなかった。local branchを作業対象とし、push時にremote branchを作成する。

### mainのworkflow / CodeQL / ruleset

`.github/workflows/`には5件あり、main HEAD `a37b155…`上の直近push runはすべてsuccess。CodeQL default setupのrunもsuccess。

| Workflow / scan | run | URL |
| --- | ---: | --- |
| Code Quality | `45431363663` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363663 |
| Codex Harness | `45431363456` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363456 |
| Validate Agent Skills | `45431363902` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363902 |
| Validate Deterministic Output Evals | `45431363541` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363541 |
| Validate Semantic Output Evals | `45431363728` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431363728 |
| CodeQL (dynamic default-setup workflow) | `45431362292` | https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/45431362292 |

- `code-quality.yml`と`codex-harness.yml`にはworkflow-level `contents: read`がある。ほかの3 workflowには明示`permissions`がない。
- 5 workflowはPR、main push、必要に応じて`workflow_dispatch`で動く。Actions参照は`actions/checkout@v4`（5か所）、`actions/setup-python@v5`（5か所）、`actions/setup-node@v4`（3か所）。
- Workflowに`GITHUB_TOKEN`、`secrets`、GitHub CLI/APIの利用、GitHubへの書き込み、artifact upload/downloadは見つからない。workflow内のPython/Nodeテストやformatter helperも確認し、GitHub repositoryへ書き込む処理は見つからない。したがって追加3件は`contents: read`で足りる。
- Active ruleset `protect-main`は`~DEFAULT_BRANCH`を対象とし、required statusは`validate`、`deterministic-output-evals`、`semantic-output-evals`。required linear historyとPR経由を要求する。CodeQL、Code Quality、Codex Harnessはrequired statusに含まれない。
- 直近main CodeQL run成功は確認したが、Alert #1〜#3の現時点のOpen/Closed状態、PR上のscan result、CodeQLとrulesetのrequired-check連携は別に確認する。

### Dependencies / GitHub security settings

- 現行`.github/dependabot.yml`はGitHub Actions ecosystemのみで、weekly、`open-pull-requests-limit: 0`。
- `requirements-dev-lint.txt`は`ruff==0.16.8`、`requirements-dev-evals.txt`は`PyYAML==6.0.3`。提供された2026-11-25のGitHub UI確認では両方がDependency graphに認識済み。
- `README.md`にRuff `0.16.8`が直接記載され、`ruff.toml`にも`required-version = "==0.16.8"`がある。CIのインストール元はrequirementsファイル。Ruffの二重pinをなくしながら実行時照合を保つため、formatter helperがrequirementsのpinを読み取る。
- `EVALS.md`の有効な開発手順にもPyYAMLの固定値を直接`pip install`する例がある。
- 現行CIにworkflow permissionsとDependabot security-only設定を固定する回帰testはない。既存PyYAMLを使う小さな`unittest`をCode Quality jobに加えれば、全workflowのroot permissionsとDependabot entryを検査できる。別test基盤は不要。
- npm manifest/lockfileは存在しない。dprintはworkflowでglobal npm install、Codex CLIはHarness workflowで`@latest`をglobal install、skills-refはworkflow内のGit URLでinstallされている。dprint pluginは`dprint.json`のURL+SHA-256 pin。
- 依存関係の詳細なマトリクスは[CI依存関係・GitHub security設定調査](../reference/ci-dependency-security-management.md)に記録する。
- GitHub接続でmainのrun、ruleset、repo metadataは取得できたが、Code scanning alerts、Dependabot alerts/security-update設定、Dependency graph manifest一覧、auto-triage、malware alerts、Secret Protection / push protection、default `GITHUB_TOKEN` permissions、private vulnerability reporting、Dependabot設定エラー/更新jobはAPI toolの許可対象外で最新値を取得できなかった。これらは未確認のまま記録し、GitHub UIの確認先を調査文書とPRに記載する。GitHub settingsやAlert状態は変更しない。

## Existing contracts

- PR #22のQA Skill群、workflowの起動条件、CI検証、runtime/state、artifact形式、traceability、validator、Deterministic / Semantic / Trigger Evalの期待値を維持する。
- Codex Harnessの`@latest`利用と実行version記録、安全機構、Codex CLIを固定versionへ変更しない契約を維持する。
- Ruffは`0.16.8`、PyYAMLは`6.0.3`、dprintは`0.55.2`のままとする。Action参照やPython/Node runner versionも更新しない。
- Ruffの実行前version照合を維持する。期待値は`requirements-dev-lint.txt`から読み、二つ目の固定値を持たない。
- dprint CLIの厳密なversion照合を削除しない。pluginのURLとchecksum、formatter対象契約を変えない。
- Dependabot security updatesはGitHub側toggleが有効であることを前提とする別機能。`open-pull-requests-limit: 0`は通常のversion-update PRを止める設定として利用し、security updateを止める設定とは扱わない。`target-branch`、auto-merge、根拠のないignore/groupを追加しない。
- セキュリティ修正以外のGitHub UI設定、Alert、rulesetは変更しない。
- PR作成後、mainへmergeしない。既存PR #10/#17/#22のbranchや変更には触れない。

## Scope

### Included

- `.github/workflows/validate-skills.yml`
- `.github/workflows/deterministic-output-evals.yml`
- `.github/workflows/semantic-output-evals.yml`
- `.github/dependabot.yml`
- `README.md`
- `EVALS.md`（PyYAML install例をrequirements manifest参照にそろえる）
- `ruff.toml`（requirements fileを唯一のRuff version pinにするため、同じ値の`required-version`重複を除く）
- `scripts/format_tracked.py`と`tests/test_format_tracked.py`（requirements pinに基づくRuff CLI照合と回帰test）
- `tests/test_ci_security_contract.py`と`.github/workflows/code-quality.yml`（security config regression testをCode Quality jobに追加）
- 本Planと`docs/reference/ci-dependency-security-management.md`
- 新規test基盤を追加せず、既存requirementsとunittest runnerを使う。

### Excluded

- dprint、plugin、skills-ref、Codex CLI、Action、Pythonの依存version更新やinstall方式変更。
- npm manifest/lockfile、dependency-submission workflow/API、automatic dependency submission、新規security scannerの導入。
- GitHub Settings、ruleset、Dependabot alerts、auto-triage、CodeQL検出設定の変更。
- Alertのmanual dismiss、CI検証削除や緩和、QA仕様・テスト期待値の変更。
- PRのmerge/close、release/tag、default branchへの直接commit/push。

## Risks and assumptions

### Verified facts

- CodeQL query `actions/missing-workflow-permissions`は明示permissionsのないworkflow/jobでrepository/org defaultを使う状態を指摘し、workflow/job levelに必要最小限のpermissions設定を推奨する。
- `contents: read`はActions checkout/readで必要な範囲を許可し、workflow-levelで残りの`GITHUB_TOKEN` scopesを無効にする。3対象の呼出経路にGitHub write処理や別API権限はない。
- GitHub公式Dependabot仕様では`open-pull-requests-limit: 0`はversion-update PRを無効化し、security updatesは別の固定limitで動く。security update向けのconfigではmanifest位置を`directory`に指定し、`target-branch`を使わない。
- GitHub dependency graphは対応manifest/lockfileまたは依存関係submissionを読み取る。npmやpipのshell install行、remote WASM URLだけをmanifestと同等に扱わない。
- dprint公式仕様はplugin URLのchecksumをSHA-256として検証すること、およびWASM pluginがsandboxedであることを説明している。dprint CLI 0.55.2の現在の固定値照合は既存契約として維持する。

### Assumptions / unresolved

- GitHub UI上のsecurity設定とalertsは依頼文にある2026-11-25確認結果が共有されているが、当turnの接続では再取得できない項目がある。これらは最新verified factとして扱わず、未確認とする。
- GitHubがPR head上でCodeQL scanを実行するかはPR後にrun/check suiteを確認する。Alertがmainから解消されたと確定できるのはmergeとmain再scanの後。
- Dependency graphにRuff/PyYAML/Actions以外が現在表示されるかはUI上で再確認できない。以前の15 referenceはuser-supplied baselineとして扱う。
- User-provided work branch名のlocal branchは存在し、開始時にclean。remote branchはまだ存在しないため、最初のpushで作る。

### Risks

- YAML parse successだけではGitHub Actions/Dependabot schemaの妥当性を証明しない。対象設定を構造・意味両方で検査し、CIとCodeQL結果も確認する。
- pipとGitHub Actionsのsecurity-only設定がsourceにあっても、Repository settingのsecurity updates toggleがOFFなら自動PRは届かない。UIでのtoggle確認をmerge後受入に残す。
- shell経由でのみ取得するCI依存関係はDependency graphとDependabotのcoverage外に残る。変更せず、対応可否・検証条件を調査文書に分離して記載する。

## Implementation order

1. Plan・repository/PR状況・対象workflow・install path・呼出スクリプト・テスト・公式GitHub仕様を確認する。確認済みfactと取得不能項目を区別する。
2. 依存関係調査文書を追加し、dprint CLI/plugins、skills-ref、Codex CLI、Actions、Python dependencies、runner/toolchainのgraph/Dependabot可否、リスク、推奨案、検証、優先度、未確認事項を記録する。
3. 対象3 workflowにworkflow-level `permissions: contents: read`を`on`と`jobs`の間へ追加する。ほか2 workflowは現在の設定のままにする。既存回帰testがないため、YAML 1.1の`on` boolean coercionを避けつつ、Dependabotの整数設定も検査できるPyYAML SafeLoaderを用い、全5 workflowのroot/job permissionsとDependabot entryを検査するunit testを追加する。既存Code Quality jobで実行し、`requirements-dev-evals.txt`からPyYAMLを供給する。
4. Dependabotの既存GitHub Actions entryを維持したままpip entryを追加し、両方をweekly / `open-pull-requests-limit: 0`とする。
5. Ruff `0.16.8`の唯一のpinを`requirements-dev-lint.txt`にし、READMEと有効なPython導入例から重複pinを除く。formatter helperはrequirementsのpinと実行CLIを照合し、既存のfail-fast契約を保つ。dprintのversion check、version、pluginsは変えない。
6. READMEに依存関係の正本、security-only方針、security update PRのreview/CI必須を追記する。既存説明と重複させない。
7. 独立したローカルvalidationを実施する。失敗が変更起因ならbounded repairを行い該当validationと全体diff reviewを再実施する。
8. Code Review Skillとrepository review契約でbase `main`、Plan、全diff、呼出経路、CI、testをレビューする。外部review serviceは起動しない。
9. 変更ファイルだけをstageし、Plan順序・review・検証が完了した後に作業branchへcommit/push。base `main`の新規PRを作成する。
10. PR最新HEADの全workflow/job/step、Codex Harness Linux/Windows、CodeQL checkを確認する。CI結果、workflow URL、対象HEAD、review修正、未確認事項をPlanとPR本文へ反映する。mainにはmergeしない。

## Validation

### ローカル

各commandを独立して実行・判定し、aggregate exit codeだけでPASSにしない。

- Formatter: `python scripts/format_tracked.py check`
- Lint: `python scripts/format_tracked.py ruff-check`
- Formatter契約（Ruff / dprint version照合、target選択、実行引数）: `python -m unittest discover -s tests -p 'test_format_tracked.py' -v`
- CI security config契約: `python -m unittest discover -s tests -p 'test_ci_security_contract.py' -v`
- patch whitespace契約: `python -m unittest discover -s tests -p 'test_ci_patch_whitespace.py' -v`
- YAML: 全5 workflowとDependabot設定をPyYAML等で読み込み、GitHub Actionsの`on`がstring keyとして保持されること、permissions階層、ecosystem/limit/不要な設定の不存在を個別に確認する。
- 関連CI: `tests/codex`、trigger/semantic/deterministic eval、runtimeの各workflow既存コマンドを実施。Codex HarnessのWindows特有launcherをローカルで再現できない部分はPR Windows jobで受入する。
- Skills: PR #22後の全Skillにofficial `skills-ref validate`を実行する。外部GitHub sourceの既存SHAを維持する。
- 差分: `git diff --check`。変更前後でworkflow triggers、Action/Python/Node version、dependency versions、QA/Eval expectationsを比較する。

### GitHub PR

- PR head SHAに対する全workflowを確認する。期待される5 workflowはCode Quality、Codex Harness (Linux/Windows両job)、Validate Agent Skills、Validate Deterministic Output Evals、Validate Semantic Output Evals。構成が変わっていればPR headの実workflowを正とする。
- PR headのCodeQL check/analysisを取得可能な範囲で確認する。main CodeQL Alertの解消済み判定とは区別する。
- 新しいPRをmain baseで作成し、mergeしない。

### Blocked / deferred

- GitHub API接続が拒否するsecurity/settings endpointは未確認として記録し、確認URL・UI filter・手順を提示する。APIの権限拒否を迂回しない。
- Alert #1〜#3のmainでの修正済み表示、修正後mainのCodeQL再scan、Dependabot settings/graph read errorの解消確認はmerge後に行う。今回の作業中に完了扱いしない。
- Validation commandが実行不能な場合、理由・影響・PRで代替できる確認先を残す。失敗をskip/削除/緩和でPASS扱いしない。

## Completion criteria

- PR #22・#36・#37が最新`main`に含まれること、base SHA、clean start stateを確認済み。
- CodeQL Alert #1〜#3に対応するworkflowへ`contents: read`を追加し、ほかのworkflow/job permissionsとGitHub write経路に矛盾がない。
- 既存GitHub Actions security-only設定を維持し、pipをsecurity-onlyに追加。auto-merge、target-branch、ignore、groupsを追加しない。
- Ruff `0.16.8`と他すべてのdependency versionは不変で、Ruff pinをrequirements fileに一本化し、requirements由来の照合を維持。dprintの照合と現行挙動を維持。
- dprint、各plugin、skills-ref、Codex CLI、GitHub Actions、Python/npm、runner/toolchainsの調査結果を、確度と未確認を分けて記録。
- READMEと必要な開発文書を更新。PR #37のhistorical Planを改変しない。
- YAML・format・lint・対象テスト・`git diff --check`を独立実行し、全てsuccessまたは明示的な未確認理由が記録される。
- Code reviewで重大なin-scope findingが残らず、必要な修正後のvalidationを再実行済み。
- 作業branchの最新PR HEADで必要なworkflow/job/step結果を確認し、PR本文とPlanに結果を反映。
- PRを作成済みでmainにmergeしていない。main merge後のCodeQL Alert解消確認・全main CI・GitHub設定受入項目を未完了として明示。

## Implementation and local review record

### Implementation state

- Target branch `fix/ci-security-hardening`は開始時に`main`と同じ`a37b15508dadd17ac0228ac896badb71d6a8f2c7`で、working treeはcleanだった。PR #22・#36・#37はmainに含まれ、変更着手前のmain CI 5件とCodeQL runはsuccess。実装中にGitHub APIでmainを再確認し、SHAは変わっていない。
- 3対象workflowに`contents: read`を追加。全5 workflowとDependabot設定を検査する回帰testをCode Quality jobへ追加。Actionsとpipを週次、通常version-update limit 0で設定。
- Ruffの唯一のpinを`requirements-dev-lint.txt`にし、formatter helperが同ファイルからexpected versionを読み、各Ruff操作の前にCLIを照合する。READMEと`EVALS.md`のPython導入例をrequirementsへ統一。依存version、workflow trigger、QA/eval contractは変更していない。
- `docs/reference/ci-dependency-security-management.md`に依存関係管理可否・リスク・優先度・推奨対応・検証・未確認事項とGitHub security UI確認先を記録。

### ローカルvalidation

| 検証 | 結果 |
| --- | --- |
| `test_ci_security_contract.py` | PASS。5 workflowの`contents: read`とjob override不存在、Dependabot ecosystemと整数0を検証。 |
| `test_format_tracked.py` | PASS。11 tests。Ruff mismatchがformat/import-fix実行前に停止するtestを追加。 |
| `test_ci_patch_whitespace.py` | PASS。3 tests。 |
| Deterministic shared runtime tests | PASS。12 tests。 |
| Semantic dataset validation / shared tests / repository tests | PASS。37 skills・210 cases、27 tests、14 tests。 |
| Trigger dataset tests | PASS。17 tests。 |
| agent-answer-form Python tests / validate-only | PASS。15 tests、2問の検証。 |
| agent-answer-form Node tests | PASS。Node test runnerで成功。workflowの`python`実行名に合わせるため、`/tmp`に一時symlinkを置きPython 3.12を使用。 |
| 変更Python filesへの直接Ruff lint/format診断 | PASS。ただしlocal Ruff `0.15.2`でありrequired `0.16.8`そのものの結果ではない。 |
| `python3 scripts/format_tracked.py ruff-check` / `check` | BLOCKED。local CLIが`0.15.2`のため、requirements由来の厳密なversion guardが`expected ruff 0.16.8`で停止。dprintもlocal未導入。 |
| Deterministic repository tests | 671 tests中、4 fail・1 error。loopback bindがsandboxに拒否され、`/tmp/.git` markerをancestorと判定するSQLite state testsがblockedになった。 |
| Runtime unit/integration tests | 1,455 tests中、10 fail・10 errors。確認した主因は同じloopback / `/tmp/.git`制約と、Python 3.12 JSON parserが1,100階層配列を受理する差。 |
| Codex Harness tests | 58 tests中1 fail、Windows-only 8 tests skipped。testがignored local `.agents/skills`の3 directoryもrepository-ownedとして数えるため。checkout CIには含まれないignored filesで、移動・削除はしていない。 |

`python3.11`、`skills-ref`、`dprint`、`actionlint`はlocalに無い。従ってexact Ruff/dprint formatter、official `skills-ref validate`、Windows transportとGitHub Actions schema/CodeQLはPR CIで確認する。個別test結果をaggregate exit codeで置き換えず、上記のlocal環境由来failureに対してテストや期待値は変更していない。最終staged diffの`git diff --cached --check`は終了コード0。

### Internal code review

- Code Review Skillに従い、Plan、base `main`、全変更、workflow呼出経路、Ruff formatter path、CI/tests、QA仕様を照合。workflow trigger / install version / evaluation expectation / runtime contractは不変で、workflow write処理・job-level permissionはない。
- reviewで、最初のsecurity testがBaseLoaderによりinteger `0`とquoted stringを区別できない点を確認し、`on`をstringに保つSafeLoaderへ改めてnative integer `0`を検査するよう修正。修正後のsecurity contract testsとlocal Ruff診断は再実行しPASS。
- 現在、in-scope actionable findingは残っていない。外部review serviceは起動していない。

### PR / GitHub verification pending

- `main`は`a37b15508dadd17ac0228ac896badb71d6a8f2c7`で再確認済み。remote `fix/ci-security-hardening` refは存在しないため、明示対象ファイルのみcommitし通常pushで作成する。
- PR作成、最新PR HEADの全workflow/job/step、CodeQL PR check、PR本文更新は未完了。PR作成後に記録する。
- CodeQL alertの現在のstatus、Dependency graphの現在値、Dependabot config/job errors、repository security settingは接続のendpoint allowlist/権限により未確認。mainでのalert解消、main再scan、GitHub UI受入はmerge後項目として残す。
