# PR #11 merge review: dependency and freshness follow-up

2026-09-24 JST、PR #11のmerge前レビューで残ったdirect mode Selection dependency、current Test Data Requirement consumption、CI dependency scopeの3点を修正し、ローカル検証結果を記録する。

## 開始状態

- branch: `feat/deterministic-test-technique-automation`
- local HEAD: `60014b1ba7588db2ab09b947c1c5212d45d73ee0`
- 開始時PR #11 head: `60014b1ba7588db2ab09b947c1c5212d45d73ee0`
- working tree: clean、差分なし
- PR state: OPEN、Ready for review
- 開始時点でPR headに紐づく既存Actionsは3 workflow success（Agent Skills run `35881084045`、Semantic Output Evals run `35881084030`、Deterministic Output Evals run `35881084062`）。これらは今回の未commit変更を検証する結果ではない。

## Plan照合

次のPlanを確認した。

- `_02_runtime-architecture-and-contracts.md`
- `_02_identity-materialize-and-workflow-contracts.md`
- `_03_artifact-processing-and-script-contracts.md`
- `_05_implementation-order-and-completion.md`

Planはdirect modeで前工程Machine Entityを強制せず、渡されたcurrent Entityだけをdependencyへ記録する。artifact modeは必要なcurrent Entityを完全解決する。またCIのsemantic dependencyは親TCN、Coverage所有model metadata、参照するcurrent test data requirement Entityである。Plan同士の矛盾は見つからず、Plan変更は行っていない。

## 修正

- `condition_structure.py`: modelの`selection_source=analysis`でもSelection dependencyの`require_all`を`input_mode=artifact`のみにした。direct modeではcurrent Selection Entityがmetadataに渡された場合だけdependencyへ保存し、ない場合はstructured `technique_selections[]`とstructure runtime generationで追跡する。`selection_key`必須、technique一致検証、artifact modeの完全解決、model freshnessは維持した。
- `materialize_coverage.py`: normalized test data requirementからMachine Entityを再生成する処理を削除した。各normalized requirementの`data_ref`に対応するcurrent TDR Entityを解決し、canonical contentと再計算したfingerprintを正規化済みrowと照合する。artifact modeのmissing Entity、内容差、row fingerprint不一致は`invalid_input`になる。Authority、source model、source runtimeをmaterializeから再解決せず、TDR Entity側のdependency chainに委ねる。
- CI Machine Entity: dependencyを各CIの親TCN、所有model、CIが明示参照するTDRへ限定した。runtime target CIはそのtargetのmodel metadataとannotationのTDR refsを使い、semantic item CIはitemのmodelとTDR refsを使う。Technique Selection、別model、別CI用のTDR、Authorityは追加しない。`runtime_dependencies[]`とmaterialize runtime粒度は変更していない。
- `runtime_contract.py`、Plan、Skill guidance、Semantic candidate / reference / rubricは変更していない。

## 回帰テスト

- `test_test_condition_structure.py`: direct + analysis Selection Entityなし、およびcurrent Selection EntityありをPASS確認。artifact modeのmissing Selectionは拒否し、current Selectionは受理する。参照Selection変更で対象modelがstale、無関係Selectionではcurrentの既存確認も維持した。
- `test_materialize_runtime.py`: 実際にtest-data-requirements generatorが生成したTDR Entityを使い、artifact modeのTDR missing、normalized content不一致、normalized fingerprint改ざんを拒否することを確認した。TDR EntityがAuthorityへ依存していてもmaterialize metadataへAuthorityを渡さず成功し、CIはTDRのcurrent fingerprintを参照する。
- `test_materialize_runtime.py`: 2つのCoverage modelを持つTCNでruntime target CIとsemantic item CIを検証した。runtime CIはTCN + 所有model + 参照TDR、semantic CIはTCN + 所有modelだけに依存し、別model / 未参照TDRは含まれない。
- freshness回帰では、参照model、親TCN、参照TDR、TDRが参照するAuthorityの変更だけが対象CIをstaleにすること、別model、無関係Authority、未参照TDRの変更は対象CIをstaleにしないことを`evaluate_entity_freshness()`で確認した。
- `test_ep_vertical_integration.py`: test data requirement generatorの実Machine Entityをmaterialize metadataへ渡し、materializeが同Entityを参照することを検証した。既存schema adapter → model-wide TDR → materialize経路も維持した。
- targeted command: `python -m unittest tests.skills.runtime.test_test_condition_structure tests.skills.runtime.test_materialize_runtime tests.skills.runtime.test_ep_vertical_integration -v` — **16 tests PASS**。

## 全ローカル検証

Python 3.11.5:

- 指定7 Skill script directoryの`compileall`: PASS
- `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`: **209 tests PASS**
- deterministic shared tests: **12 PASS**
- deterministic repository tests: **54 PASS**
- deterministic output dataset: **14 Skill / 28 case**（CIと同じmanifest validation経路）
- semantic dataset validator: **14 Skill / 51 case**
- semantic shared tests: **27件中25 PASS / 2 skip**。`test_symlink_escape_raises`と`test_cases_directory_symlink_escape_raises`はWindowsのsymlink privilege不足（WinError 1314）による既存skip。skip条件・production codeは変更していない。
- semantic repository tests: **4 PASS**
- trigger dataset tests: **1 PASS**。datasetは**14 Skill / 328 query**。
- pinned official `skills-ref`（CIと同じcommit `69ef37e9424c0a7ea9dd2293b559e43ec8176379`）: **14/14 PASS**
- 7個の`runtime_contract.py`はLF正規化後完全一致。SHA-256: `eb0c25eff743665c7eae5c8718259549b8551bcd1214401769662b216bc5cb37`
- Step 2.5 standalone、`qa-workflow` integration、Markdown round-trip、schema adapterからmaterializeまでのruntime integration: PASS（runtime suite内）
- `git diff --check`: PASS。GitはWindows working copyのLF-to-CRLF正規化warningを出したが、whitespace errorはない。

今回Skill guidance、semantic candidate、reference、rubric、eval fixtureを変更していないため、Semantic Judgeは再実行していない。前回のJudge結果を今回のruntime変更の検証証拠には使用していない。

## GitHub Actions / Git操作

- 今回のlocal revisionは未commitであり、pushしていない。このため今回の変更を含むGitHub Actionsは未実施であり、PASS扱いしない。
- 開始時のremote headに対する既存Actionsは上記のとおり成功していたが、今回の変更をカバーしない。
- commit、push、PR本文更新、merge、branch削除、PR / Issue closeは未実施。

## 状態

実装上の今回対象の未達: 0件。ローカル検証は完了。push禁止の指示に従い、最新変更に対するGitHub Actions確認は次のpush後工程として待機する。
