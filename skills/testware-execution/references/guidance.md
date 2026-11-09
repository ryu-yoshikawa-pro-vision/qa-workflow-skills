# 非E2E実行・診断ガイダンス

## 起点と方式

- ブラウザE2Eはe2e-test-execution、browser直接TC操作はtest-execution。API-only Playwright Test、Vitest、component、batch、event、非機能、許可された静的解析ツールは本Skill。
- 永続testwareの作成・更新はtestware-implementation。今回は実行のみなら作成を前提にしない。
- 永続testwareなしの非ブラウザTCでは、Given/When/Thenに相当する開始状態・操作・期待結果・観測方法・cleanupを事前固定する。実操作やraw結果から期待値を作り直さない。
- 仕様Authority、非機能閾値、測定条件が欠ければ該当判定は未確定とする。既存専門SkillのUI/UX、WCAG判定を非機能の一般合格として転用しない。

## Preflightと実runner

1. 対象repoとcommit、TCまたは明示testware ref、必要run、build、対象環境・権限、実行入口chain、設定、fixture/hook、データ準備・依存先を確認する。
2. scriptやpackage managerの入口とpre/post chainを読み、runner管理setup/teardownとrun外の準備・cleanupを区別する。静的解析も外部I/O・ファイル変更・秘密情報に関する権限を確認する。
3. 副作用はscope単位で最大回数とcleanupを記録する。実行状態不明のattemptも起こり得る副作用を消費したものとし、未確認なら再実行しない。共有資源のreservationは実providerのreadbackが必須で、単なるフラグやoperation claimでは代用できない。
4. 実runnerを開始したことをprocess/API等の証拠で確定し、runner stdout、machine-readable reporter、開始/終了、timeout、exit code、attemptをその実run refへ結び付ける。artifactの鮮度を検査し、旧runを採用しない。
5. reporterを自動変換して元runner statusを書き換えない。cleanup失敗は元のテストFAILへ書き換えず、対象runの安全な完了を別に制限する。

## Vitestの識別と完全性

- 固定source commit、repo相対path、suite／title path、実効filterと選択集合で個別testを照合する。ファイル移動や改名、同じtitle、パラメータ化testでは旧版へ自動対応しない。
- `contract.reconcile_vitest()`はVitest JSON reporterの選択集合を照合する。reporter中の絶対pathは渡された検証済みrepo rootとの一致を確認して正規化する。suite statusと個別assertion statusの矛盾・集計不一致は取得完全としない。
- selection_verifiedは実コマンドと列挙完全性の証拠があるときだけtrueとする。重複名の解決不能、missing、unplanned、partial selectionは全件取得・全PASSとしない。
- retry/attemptをJSON reporterが提供しない場合、attemptの取得完全性は不明と記録する。1件の最終statusを複数attemptへ捏造しない。raw passedはassertion品質やTC合格を証明しない。
- Vitestのtest-control境界を一般HTTP APIの受入証拠に使わない。独立HTTP fixtureと実製品の結果を分けて保管する。

## 直接観測・静的解析・診断

- 直接観測は各期待結果の実観測値・不一致・観測不能を保存する。HTTP 200でも本文が異なればFAIL。必要な副作用を観測できなければ判定不能。最初の実操作前に停止なら未実行。
- 静的解析は適用ルール/設定、対象ファイル、実ツールversion、raw出力、取得件数・未解析範囲を記録する。意味レビューの誤検出・仕様矛盾はadversarial-reviewに渡す。
- 診断はSUT/testware/fixture/environment/runner/仕様不明を原因候補とし、観測事実、仮説、反証、確度、次のownerを記録する。元runの判定と欠陥候補は分離する。
- 実装しただけのtestwareや独立fixtureのPASSは実製品runの証拠ではない。

## 下流の引継ぎ

H/Jが読む単位はrun ref＋source/build/testware revision、個別test path/title、任意の元TC ref、実効選択条件、attempt、raw evidence、取得完全性、cleanup、診断とする。保存providerのreadback revisionや承認はAの正式公開契約に従い、未接続ならblockedとする。A〜J成果物の実参照をつないだ全体受入はPR #22で行う。

## 実行CLIと独立検証の範囲

`python skills/testware-execution/scripts/runner.py --plan /path/to/run-plan.json --artifacts /outside/source/artifacts` で、事前に全コマンド連鎖とfixture・副作用を確認した単独対象を実行する。CLIは指定したcheckoutの固定HEADとclean状態を確認し、開始プロセス、終了コード、timeout、各attemptのstdout／stderr、任意のVitest JSON reporterとrun外cleanupを専用ディレクトリへ保存する。実runnerの成功と正式TCのPASSは別。実行前に止まった場合は証拠を捏造しない。

入力JSONは `repo_path`（絶対path）、`repo_revision`（Git HEAD SHA）、`runner_kind`（vitest／playwright-api／component／batch／event／nonfunctional／static）、`argv`、同値の `reviewed_argv`、`preflight`、任意の `timeout_seconds`・`attempts`・`cleanup_argv`・`reviewed_cleanup_argv` からなる。コマンドはshellを介さず起動する。Vitestでは、実reporterの出力pathを `{reporter_file}` としてrunnerコマンドに明示し、固定された `selected`、実選択を証明できる場合のみ `selection_verified`、実checkout rootを使用して照合する。CLIが製品テストや依存関係を自動導入することはない。

非ブラウザTCで出力の直接比較を行う場合、`direct_expectations` に `{"id":"exit_code","expected":0}`、`{"id":"stdout_json","expected":{"ok":true}}` 等を列挙する。これらの期待値は実行前の仕様Authority・TCに由来するものとし、stdoutのJSON／終了コードから取得した実測と比較する。異なる場合はraw終了コード0でも `observed_FAIL`、必須観測を取得できない場合は `observations_incomplete`。結果は元attempt・rawと区別する。外部サービス・DBの副作用を実際に観測できない場合、入力だけで観測済みとしない。

非機能は `runner_kind=nonfunctional` に `metric_criteria`（id、characteristic、unit、minimum／maximum）、`threshold_authority_ref`、`measurement_condition_ref`、確認済みの `measurement_conditions_verified` を渡し、実runnerのstdout JSONで得た数値だけを比較する。測定値不足は `判定不能`、閾値違反は `FAIL`。採用基準・計測条件を実測から推測しない。実採用のツール／計測・fixtureや条件の妥当性自体は別途レビューする。

`preflight` の確認済みbooleanは**承認や共有予約のprovider認証ではない**。本CLIはshared／外部副作用を常に拒否する。隔離checkoutはOSのサンドボックスではないため、未信頼コマンドの実行、未確認のpackage lifecycle、認証情報の利用、インターネット通信を安全化しない。全script chainの検査と実環境の許可・隔離・秘密情報保護は起動担当が行う。rawログには機密情報が含まれ得るため、自動commit・共有を禁止する。cleanupや試行状態が不明な場合は自動retryしない。

独立fixtureでのPython subprocess、Vitest形式の固定JSON、Git fast-forward競合試験は、固定qa-training-storeの実Vitest／API-only Playwright／バッチ・イベント・非機能計測の受入とは区別する。これらの本物のrunnerと実providerの検証は対象commit・必要な許可が確認できたときに行う。

## 実runnerの確認条件と取得完全性

- `preflight.external_side_effects` と `preflight.shared_resource` は省略せず真偽値で指定する。いずれかがtrueなら本CLIは認証済みproviderがないため実行を拒否する。任意subprocessに対する副作用回数をOSレベルで保証できないため、`side_effects` が空でない場合も `side_effect_limits_unenforceable` として開始しない。これは副作用上限機能を実装したという意味ではなく、providerが接続されるまでの安全な停止である。
- 実行前、各attemptの直前、cleanup後のcheckout HEADを確認する。終了後に別commitへ進んだ場合、作業ツリーがcleanでも `blocked_revision_changed` として元revisionの結果を完了扱いしない。ignored fileや外部状態についてはGit statusだけではcleanupを証明できないため、必要な環境では別の実証を要求する。
- run manifestには `source_ref/source_revision`、`build_revision`、`repo_revision`、`environment_ref`、`runner_ref`、任意の `testware_ref/testware_revision`・`tc_ref/tc_revision`、予定scopeと選択根拠、個別attempt、raw、cleanup、結果収集を保持する。argvにはsecretが含まれ得るためコマンド全体は書き戻さず、実argvのSHA-256を保存する。入力で宣言された選択根拠をrunner自身の認証済み根拠に昇格しない。下流へ渡す際に必要な識別子・version・選択根拠が未取得ならそのまま未検証とする。
- `direct_tc: true` は `direct_expectations` に加えて `tc_ref`、`tc_revision`、`expected_authority_ref` を必須とする。これらのない任意出力比較は `direct_observation_verdict` としてのみ記録し、正式 `tc_verdict` には昇格しない。通常のbatch等の終了コード0は、期待結果の比較がない場合、実runnerの正常終了だけを表す。非機能は `metric_criteria` と採用根拠・測定条件を必須とし、未指定なら開始前に拒否する。
- 静的解析の実行は `runner_kind: static` と `static_analysis`（`tool_ref`、`tool_version`、`rules_ref`、`config_ref`、`expected_paths`、許可された `accepted_exit_codes`）を必須とする。実ツール／既存の許可済みadapterがstdoutへJSON objectとして `findings_count`、`analyzed_paths`、空の `skipped_paths`、同じtool/version/rules/configを出力した場合だけ取得完全とする。未実行・欠損・toolのrawだけではFinding 0件としない。各種tool固有の出力をこのJSONへ適合させるadapterは別途対象toolに沿った検証を要する。
- `diagnosis_hypotheses` を指定した場合はrunの元観測と独立して原因候補・確度・証拠・次の担当を保持する。これは確定した製品欠陥でも元runの再採点でもない。

## 個別reporterの照合と実行結果

- 自動testwareでは終了コードだけで取得完全を宣言しない。`reporter_format`は`vitest-json`（Vitest／対応component）、`playwright-json`（Playwright API-only／対応component）、`case-json`（batch／eventの採用済みadapter）から選ぶ。未対応・欠落時はexit 0でも`outcome=incomplete`、`collection_verified=false`とする。
- reporterを使うrunには`testware_ref`・`testware_revision`・`runner_version`・`selected[]`・`selection_verified=true`・`selection_evidence_ref`・`planned_scope_ref`を必須とする。`selected`はrepo相対`path`・`title_path`と必要な`project_name`を持つ。選択の根拠は起動担当の宣言であり、このCLIによる認証済みprovider readbackではない。
- `vitest-json`は実起動引数に`{reporter_file}`を含める。Vitest 4のCLIは`vitest run --reporter=json --outputFile={reporter_file}`でJSONを書ける。suite・個別status・集計・選択集合の一致を照合する。
- `playwright-json`は公式`PLAYWRIGHT_JSON_OUTPUT_FILE`を子プロセスに設定する。CLIの`--reporter=json`、Playwright TestのAPI-only実行であること（ブラウザ利用のないテストコードとscript chain）を実行前に確認する。suite/spec/test/project・個別retry・global error・statsを照合する。
- `case-json`は採用済みbatch/event adapterが`{reporter_file}`へ固定schema `non-e2e-cases/v1`のJSONを出す。必須rootは`schema`、`source_revision`、`testware_revision`、`complete`、`results[]`。個別resultは`path`、`title_path`、`status`（passed/failed/pending/todo/skipped/timedOut/interrupted）、`attempt_results`（statusを保持する配列）。変換前の実ツールrawとadapterのrevisionも別に残す。
- source/testware revision、選択集合、個別statusの重複・欠落、未取得attempt、raw失敗と終了コード0の矛盾は完全としない。任意の`direct_expectations`だけを自動testwareの個別取得の代わりに使わない。正式直接TCは`direct_tc=true`とTC ref・revision・仕様Authority refを必要とする。
- 実装済みの個別reporterテストはPython subprocessで固定JSONを模擬生成した独立fixture。固定`qa-training-store`の実Vitest／Playwright／採用済みbatch・event実runを証明しない。
