# PR #11 partial rerun and runtime evidence follow-up

2026-09-24 JST、PR #11でPlan上すでに定義されているpartial rerunのMachine Entity carry-forwardと、standalone Skillの最終`verify_runtime_evidence` gateを確認・実装した記録。

## 開始状態

- branch: `feat/deterministic-test-technique-automation`
- local HEAD: `62048b7fd677ecd17ddb813de3b6ed40c4f24a85`
- 開始時PR #11 head: `62048b7fd677ecd17ddb813de3b6ed40c4f24a85`
- PR: OPEN、Ready for review、mergeable
- working tree: 対象の27ファイルに未commit変更あり。既存変更は破棄・上書きしていない。
- 開始時PR headのActionsは3 workflow success（Agent Skills `35936523849`、Semantic Output Evals `35936523884`、Deterministic Output Evals `35936523841`）。これらは今回の未commit差分を検証していない。

## 変更目的と範囲

### Partial rerun Machine Entity集合

- `runtime_contract.py`の固定projectionで、canonical normalized input、前回artifactのstrict検証結果、前回active/deleted ID state、`update_scope_*`、current runtime result、Entity ownershipからexpected identity集合を導出する。
- 前回artifactのMachine Entities block重複、Entity identity重複、entity schema / fingerprint / dependency schema、runtime input/result pair、full ID stateとの整合を検査する。不正なprevious artifactは`invalid_previous_artifact`として無効にする。
- 更新scope内はcurrent structure/materialize resultを正本にし、scope内で削除されたEntityとprevious deleted Entityはexpected集合へ戻さない。scope外のactive Entityだけをcarry forward候補にする。
- scope外Entityのcontent、fingerprint、semantic/runtime dependencyは変更しない。current runtime / Entity集合に対する`evaluate_entity_freshness()`でstaleをblockする。
- `workflow_runtime.py`と`traceability.py`はscopeのnormalized inputおよび`current_structure_state`から同じ固定identity projectionを使う。extra Entityは引き続きblocking issueとなり、stale Entityも完了を阻止する。
- aggregate structure runtime generationの変更で無関係なscope外Entityが一律staleになる再現を確認し、各producer runtimeのimplementation / contract / static-data情報と当該Entityのcanonical content fingerprintからentity-scoped runtime generationを導出する固定helperを追加した。generation mismatchを無視したり、carry-forward Entityの依存情報を書き換えたりはしていない。

### Standalone production最終gate

- `test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`qa-workflow`の6 Skill文書に、最終出力前のSkill-local `runtime_contract.py` / `operation=verify_runtime_evidence`実行を明記した。
- 実際のcanonical normalized inputとcandidate artifact全文を渡す。full buildは`previous_artifact_markdown=null`、partial rerunは同一成果物系列の直前artifact全文を渡す。
- `valid=false`を完成扱いせず、Agentがexpected runtime / Entity一覧、dispatch state、前回Entity配列を手組みしないことを明記した。`qa-workflow`ではこのgateと`workflow_runtime.py`の検証を別々に実施する。

## 変更ファイル

- 7 Skill-local `runtime_contract.py` copies
- `workflow_runtime.py`、`traceability.py`
- Entity-producing structure / materialize runtimeのscoped runtime dependency binding
- 6 runtime対象Skillの`SKILL.md`
- partial rerun、freshness、workflow/traceability projection、runtime evidence gateの回帰tests
- Plan、Semantic candidate/reference/rubric/fixture、trigger dataset、外部dependencyは変更していない。
- 直近のdirect Selection、current TDR consumption、CI dependency限定のsemantic規則は変更していない。隣接するproducerファイルはentity-scoped runtime generationを使用するためruntime dependency表現のみ変更した。

## 検証

Python 3.11.5:

- targeted partial rerun / evidence関連の7 runtime test modules: **73 PASS**（stage後に再実行）
- `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`: **222 PASS**
- 7 Skill script directoriesのcompileall: PASS
- deterministic shared: **12 PASS**
- deterministic repository: **54 PASS**
- deterministic dataset: **14 Skill / 28 case**
- semantic dataset: **14 Skill / 51 case**
- semantic shared: **27 tests中25 PASS / 2 skip**。Windows symlink privilege不足による既存skip。skip条件・production codeは変更していない。
- semantic repository: **4 PASS**
- trigger repository tests: **1 PASS**。trigger dataset: **14 Skill / 328 query**
- pinned `skills-ref validate`: **14/14 PASS**
- Step 2.5 standalone、Markdown round-trip、qa-workflow integration: PASS
- 7個の`runtime_contract.py`: LF正規化後完全一致。SHA-256: `E3137AAFFB2EF99613A7C81AECFB87B87761D99BC89B0A578814C66DF969345A`
- `git diff --check`: PASS
- Semantic Judgeは未実行。Semantic guidance / candidate / reference / rubric / fixtureを変更していないため。

## GitHub Actions / Git操作

- このRun Reportはcommit時点までのローカル検証を記録する。push後のActions結果はPR本文へ記録する。
- 現時点ではcommit / push前のため今回の差分に対するGitHub Actionsは未実施であり、PASS扱いしない。
- commit、push、PR本文更新、merge、branch削除、PR / Issue closeは本記録作成時点で未実施。

## 状態

実装およびローカル検証は完了。最新差分に対するGitHub Actionsはcommit / push後に確認する。
