# Project Context

## 現在の責務

このリポジトリは、QA工程を担当するAgent Skill群と、その仕様適合・発火・決定論的出力・意味評価・workflow評価を管理する。`qa-workflow`が開始Skill、再利用、停止・再開、修正routingを判断し、工程固有の意味判断は担当Skillが行う。

## PR #11で導入したruntime契約

現在も使われているruntime実装は、対象Skill内の`scripts/`と対応する`SKILL.md` / referenceを正本とする。Python標準ライブラリだけで動作するSkill-local scriptが、LLMで正規化されたJSONをstdinから受け、stdoutへ1件のruntime envelopeを返す。runtime unitを持つSkillは`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`qa-workflow`の6つで、`spec-analysis`は`runtime_contract.py`と`authority_entities.py`でAuthority Machine Entityだけを生成する。

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

### 現在の構成

現在のrepository eval datasetは19 Skill、trigger 428 query、deterministic output 38 case、semantic 72 caseです。`qa-workflow` routing fixtureは61件です。

`Validate Agent Skills`は19 Skillの仕様適合とrepository eval structureを確認し、trigger 428 query、semantic datasetを検証します。`Validate Deterministic Output Evals`はdeterministic output 38 caseとvalidator / test構成を確認し、共通・repository deterministic test、runtime test、semantic validationを実行します。compile対象のproduction scriptは`spec-analysis`、PR #11 runtime対象6 Skill、PR #13の`regression-testing` / `exploratory-testing` / `qa-knowledge`です。

### PR #11実装時の検証実績

PR #11の追加・更新semantic caseは、既存`semantic/run.py`のrunner protocolへ外部Judge commandを接続して24件を実評価し、24/24 PASSを確認しました。実Agent runtime smokeは`test-analysis`と`test-condition-design`を各1件、Python 3.11 runtime起動、stdout envelope、Machine Entity / runtime result採用、Markdown保存・再読込、preflight、current script再実行まで確認しました。ローカルの通常レイアウトPython 3.11.9でも、当時のPlan指定compile / runtime unit / deterministic / semantic / workflow評価をPASSしました。

## 既知の環境差

checkoutには標準run初期化script・artifact sanitizer・`gh` CLIが元来存在しないため、未配置の実行補助は検証報告で明示する。CIの正本interpreterはPython 3.11であり、通常のローカル検証はPython 3.12、PR #11最終検証は一時配置した通常レイアウトPython 3.11.9で実行した。embeddable Python 3.11は`._pth`分離によりSkill-local importを解決できず、runtime unitの直接subprocess実行には使用しなかった。
