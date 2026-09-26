# Project Context

## 現在の責務

このリポジトリは、QA工程を担当するAgent Skill群と、その仕様適合・発火・決定論的出力・意味評価・workflow評価を管理する。`qa-workflow`が開始Skill、再利用、停止・再開、修正routingを判断し、工程固有の意味判断は担当Skillが行う。

## PR #11 のruntime契約

`docs/plans/2026-09-18_170000_deterministic-test-technique-automation.md`と参照先の分割Planを正本とする。Python標準ライブラリだけで動作するSkill-local scriptが、LLMで正規化されたJSONをstdinから受け、stdoutへ1件のruntime envelopeを返す。runtime unitを持つSkillは`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`qa-workflow`の6つで、`spec-analysis`は`runtime_contract.py`と`authority_entities.py`でAuthority Machine Entityだけを生成する。

各対象Skillは同一内容の`scripts/runtime_contract.py`を同梱する。canonical JSON、strict decode、exact number、入力・model・generation fingerprint、Machine Entity、target stable ID、freshness、`verify_runtime_evidence`をこのSkill-local helperが所有する。技法固有generatorは同Skillのhelper以外をimportしない。実行時のinterpreter command名やtimeout APIはSkill契約へ固定しない。

## 主な実装面

- `skills/test-analysis/scripts/`: context、risk matrix、technique selection、change impact、environment requirements
- `skills/test-requirement-design/scripts/`: TR structureとID state
- `skills/test-condition-design/scripts/`: TCN structure、各Coverage generator、test data、materialize
- `skills/test-case-design/scripts/`: TC structureとstable CI展開
- `skills/coverage-analysis/scripts/`: traceabilityとfreshness
- `skills/qa-workflow/scripts/`: workflow scope内のruntime / Entity集合、stale伝播、完了条件
- `tests/skills/runtime/`: runtime unit、CLI、EP縦断、全script hand-written fixture、round-trip、freshness回帰

## 評価・検証

trigger datasetは14 Skill合計328件、semantic datasetは合計51件（`test-analysis=7`、`test-condition-design=14`、`adversarial-review=8`、その他11 Skill=各2）を固定する。runtime CIは7 Skillのcompile、shared deterministic eval、repository deterministic eval、runtime unit、semantic dataset validationを実行する。repository内のruntime / deterministic / semantic dataset / trigger / compile / `skills-ref validate`相当はPR #11実装と同時に回帰確認済みである。PR #11の追加・更新semantic caseは、既存`semantic/run.py`のrunner protocolへ外部Judge commandを接続して24件を実評価し、24/24 PASSを確認した。実Agent runtime smokeは`test-analysis`と`test-condition-design`を各1件、Python 3.11 runtime起動、stdout envelope、Machine Entity / runtime result採用、Markdown保存・再読込、preflight、current script再実行まで確認した。ローカルの通常レイアウトPython 3.11.9でもPlan指定のcompile / runtime unit / deterministic / semantic / workflow評価をPASSした。

## 既知の環境差

checkoutには標準run初期化script・artifact sanitizer・`gh` CLIが元来存在しないため、未配置の実行補助は検証報告で明示する。CIの正本interpreterはPython 3.11であり、通常のローカル検証はPython 3.12、PR #11最終検証は一時配置した通常レイアウトPython 3.11.9で実行した。embeddable Python 3.11は`._pth`分離によりSkill-local importを解決できず、runtime unitの直接subprocess実行には使用しなかった。
