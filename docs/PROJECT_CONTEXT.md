# Project Context

## 現在の責務

このリポジトリは、QA工程を担当するAgent Skill群と、その仕様適合・発火・決定論的出力・意味評価・workflow評価を管理する。`qa-workflow`が開始Skill、再利用、停止・再開、修正routingを判断し、工程固有の意味判断は担当Skillが行う。

## 現在のruntime契約

現在も使われているruntime実装は、対象Skill内の`scripts/`と対応する`SKILL.md` / referenceを正本とする。Python標準ライブラリだけで動作するSkill-local scriptが、LLMで正規化されたJSONをstdinから受け、stdoutへ1件のruntime envelopeを返す。shared `runtime_contract.py`は`spec-analysis`、`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`qa-workflow`、`usability-inspection`、`wcag-conformance-evaluation`の9 Skillに同一内容で置かれている。`spec-analysis`は`authority_entities.py`でAuthority Machine Entityを生成し、`usability-inspection` / `wcag-conformance-evaluation`は各Skill固有のruntime契約と合わせて使用する。

各対象Skillは同一内容の`scripts/runtime_contract.py`を同梱する。canonical JSON、strict decode、exact number、入力・model・generation fingerprint、Machine Entity、target stable ID、freshness、`verify_runtime_evidence`をこのSkill-local helperが所有する。技法固有generatorは同Skillのhelper以外をimportしない。実行時のinterpreter command名やtimeout APIはSkill契約へ固定しない。

## 主な実装面

- `skills/test-analysis/scripts/`: context、risk matrix、technique selection、change impact、environment requirements
- `skills/test-requirement-design/scripts/`: TR structureとID state
- `skills/test-condition-design/scripts/`: TCN structure、各Coverage generator、test data、materialize
- `skills/test-case-design/scripts/`: TC structureとstable CI展開
- `skills/coverage-analysis/scripts/`: traceabilityとfreshness
- `skills/qa-workflow/scripts/`: workflow scope内のruntime / Entity集合、stale伝播、完了条件
- `skills/test-target-inspection/`: current UI・対象資料の確認、revision付き更新
- `skills/test-execution/`: 詳細TCの今回run、実行事実・結果・cleanup記録
- `skills/regression-testing/scripts/`: baseline snapshot、membership、Run、Activity projection
- `skills/exploratory-testing/scripts/`: Charter、Session lifecycle、安全な実対象操作
- `skills/qa-knowledge/scripts/`: entry identity、lifecycle、currentness、CAS条件
- `skills/qa-workflow/scripts/artifact_graph.py`: Project Context stable key、workflow state、currentness、claim、reservation
- `tests/skills/runtime/`: runtime unit、CLI、EP縦断、全script hand-written fixture、round-trip、freshness回帰

## 評価・検証

### 実Agent評価ランナー

`scripts/skills/evals/agent/`は、固定Evaluatorと任意のSkill revisionを分離して、実Agent出力をdeterministic / semantic / workflow evaluatorへ渡す評価基盤です。`run.py`は単一caseとbatch、`qa_training_store.py`は固定QTS revisionの2-attempt workflow、`judge_validation.py`はJudgeのfixture検証、`improve.py`は根拠が確認された失敗に限る分析・候補修正・再評価を担当します。候補Skill package・sanitized targetはread-only Agent workspaceへ配置し、Judge / Reference / graderはAgentから隔離します。

Codex smokeでは`tools/codex_docker_launcher.py`がLinux Docker container内のAgentを起動します。受入imageはCodex CLI `0.163.0`とPython 3.11を含み、root filesystemとworkspaceをread-only、attempt outputだけをwrite可能にし、`/tmp`をtmpfsにします。Codexの認証は一時`CODEX_HOME`または環境変数で渡し、host homeをmountせずrun終了後に一時領域を削除します。launcherは`codex exec --json`のraw JSONLを保存せず、安全化したevent summaryと最終応答だけをrunnerへ渡します。

`tools/codex_judge_docker_launcher.py`はJudge専用の別container・別一時`CODEX_HOME`を使います。Judgeにはpromptをstdinで渡し、stdoutには最終Judge JSONだけを返します。Judge用の安全なevent summaryは`launcher-observations.json`に記録し、raw JSONLは保存しません。shell等のtool eventが検出されたJudge出力や、秘密値の安全化で候補出力が変化したattemptは採点に使わず、レビュー対象にします。通常CIはDockerや外部LLMを起動せず、fake Agent / Judgeの契約testを実行します。

live acceptanceではread-denial、source write-denial、Docker image ID / CLI / Python、Judge独立実行を個別に実証する必要があります。実行環境や未承認のJudge fixtureが不足するrunは成功扱いせず、独立して進められる検証と分けて記録します。

### 現在の構成

現在のrepository eval datasetは22 Skill、trigger 488 query、deterministic output 46 case、semantic 163 caseです。`qa-workflow` routing fixtureは69件です。

`Validate Agent Skills`はcurrent repositoryの22 Skillから仕様適合とeval structureを導出し、trigger datasetとsemantic datasetを検証します。`Validate Deterministic Output Evals`はcurrent manifestの46 deterministic output caseとvalidator / test構成を確認し、共通・repository deterministic test、runtime test、semantic validationを実行します。compile対象のruntime scriptはcurrent repositoryの`skills/*/scripts`から動的に導出されます。PR #16ではUI target modeのrepository projection、runtime / Entity lifecycle、AC traceabilityおよび8 routing boundaryを追加しています。

### PR #11実装時の検証実績

PR #11の追加・更新semantic caseは、既存`semantic/run.py`のrunner protocolへ外部Judge commandを接続して24件を実評価し、24/24 PASSを確認しました。実Agent runtime smokeは`test-analysis`と`test-condition-design`を各1件、Python 3.11 runtime起動、stdout envelope、Machine Entity / runtime result採用、Markdown保存・再読込、preflight、current script再実行まで確認しました。ローカルの通常レイアウトPython 3.11.9でも、当時のPlan指定compile / runtime unit / deterministic / semantic / workflow評価をPASSしました。

## 既知の環境差

checkoutには標準run初期化script・artifact sanitizer・`gh` CLIが元来存在しないため、未配置の実行補助は検証報告で明示する。CIの正本interpreterはPython 3.11であり、通常のローカル検証はPython 3.12、PR #11最終検証は一時配置した通常レイアウトPython 3.11.9で実行した。embeddable Python 3.11は`._pth`分離によりSkill-local importを解決できず、runtime unitの直接subprocess実行には使用しなかった。
