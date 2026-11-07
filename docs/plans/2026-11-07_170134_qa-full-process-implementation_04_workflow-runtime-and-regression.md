# workflow runtime・Regression・セッション間引継ぎの実装契約

## 対象と正本

この文書は[QA全工程Plan](./2026-11-07_170134_qa-full-process-implementation.md)と[継続workflow Plan](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)に対して、**新設Skillを実際に検証・再利用できる状態にする仕組み**と**非E2EのRegression実行**を定義する。

- workflowの選択・局所停止・再開・変更伝播：既存`qa-workflow`。
- 仕様・Risk・TC・実行・計画・報告等の意味判断と正本：それぞれの担当Skill。
- Regression Baseline・Run・Activityの選定・追跡：既存`regression-testing`。
- 実行結果・cleanup・再実行可否の一次情報：各実行Skill。Regressionは元の結果を再採点しない。
- 実際の書込み・条件付き更新・操作復旧：[保存・承認の共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)と各成果物owner。

モデル・Agent製品・CLI・外部の起動／監視／通知機構はこの契約に含めない。新設Skillと既存Skillを一律のMachine Entity体系に移行することも要求しない。

## 1. 未登録Skillのworkflow完了を禁止する

### 現行の変更対象

- `skills/qa-workflow/scripts/runtime_contract.py::_default_expected_runtime_units()`は、現行のroot runtime unitを既存6 Skillに対して導出する。
- `skills/qa-workflow/scripts/workflow_runtime.py::_scope_rows()`は、`qa-workflow`自身以外のSkill名を固定対応一覧で制限しない。
- `workflow_runtime.py::_build()`の`can_complete`は、期待されたunit／Entityと実際の証拠を照合して決まる。
- `validate_current_structure_state()`のschema検証が成功した事実だけでは、未登録Skillの成果物を十分に確認できたことにならない。

### 完成形の契約

1. `qa-workflow`の扱えるSkillごとに、**担当owner・必要な検証入口・必要な成果物の参照・検証済み状態・source currentness・未完了の扱い**を定義する。ルーティング表への名前追加と完了検証への対応登録を別の操作として扱う。
2. 新Skillの検証は、**当該ownerの決定論的validator／既存runtime**を使う。`qa-workflow`は検証結果の参照、対象scope、入力と出力のrevision、現在性と依存、未解決・再開位置を照合する。新しい工程固有判断や全Skill共通の巨大schemaを`qa-workflow`に実装しない。
3. workflowに含むが検証契約を登録していないSkill／scopeは`unsupported`または`blocked`として扱い、**必須unitもEntityも0件であることを完了の根拠にしない**。すでに検証できた他scopeの結果は保持する。
4. 単独開始では、QA要求のみ、計画のみ、報告のみ、欠陥追跡のみ、非Web実行のみなど、**既存TR／TCN／CI／TCのscopeが0件でも**対象ownerの検証済み成果物によって完了できる。無関係な設計runtimeや仮のTCを作らない。
5. 有効な成果物が別Ownerから入力された場合も、発行元・source revision・検証結果と有効範囲を確認する。LLMの「検証済み」表記だけで検証結果を生成しない。
6. ownerの内部結果状態とworkflow全体状態を混同しない。ownerで完了していても、依頼scopeに必要な依存成果物・承認・cleanupが欠ける部分はworkflowで完了にしない。

### 最低限のhandoff項目

各ownerの既存成果物と検証出力から、次の情報を取得・照合する。項目が既存形式に存在する場合は再定義・再採番せず参照する。

- `owner skill`、`scope`、`input artifact refs/revisions`、`source refs/revisions`
- `output artifact ref/revision`、正本保存の確認と取得範囲
- 使用した`validator/runtime`と検証結果の参照・version、検証済みの対象
- `current`／`stale`／`blocked`／`unsupported`等の既存状態への対応と判断根拠
- 未完了の入力・依存、次の担当Skill、再開条件

既存のowner成果物のversion・識別形式を上書きする横断manifestを新設しない。各ownerの既存状態の意味は変更せず、`qa-workflow`側の判定への投影を検証する。

### 必須検証

- 未登録Skill・必要検証結果0件・空のcurrent evidenceを与えても`can_complete=true`にならない。
- 既存対応Skillと未登録Skillが混在するとき、前者のcurrent結果は保持し、後者だけ`blocked`になる。
- 計画のみ、報告のみ、欠陥のみ、非Web実行のみで、各ownerの検証結果があれば必要scopeだけ完了できる。
- 他workflow／旧source／旧承認の検証結果を流用できない。全Skill同時利用での誤発火・重複判断も検出できる。
- 既存6 Skillのruntime-v2／partial rerun／carry-forward／materializeと、現在の単独開始経路を回帰させない。

## 2. 非E2EをRegressionの正式required routeに含める

### 変更対象

- `skills/regression-testing/scripts/regression_runtime.py::validate_required_routes()`は、現行で`manual`と`e2e`のみを受理する。
- `skills/regression-testing/references/data-contract.md`とRun・Activityの検証・serializer・fixtureを同時に修正する。
- TCなしの補助testwareの`auxiliary_testware_refs`／`auxiliary_route_results`は既存の別経路として維持する。

### 完成形の契約

1. TCに対応する非E2Eの自動／runner実行は、既存`required_routes`に**`testware`経路**を追加して表す。既存の`manual`と`e2e`は意味・保存履歴・currentnessを維持する。
2. `testware`経路は、必要な`tc_ref`、`route_ref`、実testwareへの参照、実行owner、対象実装revisionと選択条件を持つ。結果はそのownerが返した実測・元結果・開始状態・最終確定・cleanup・証跡を参照する。
3. 同じTCに複数required routeがある場合は全required routeの開始／結果確定／cleanupを照合する。別TCのPASSや補助testwareのPASSによって未実行TCを完了にしない。
4. TCなしtestwareは既存の補助経路を使用する。補助経路にある件数を正式TCの実行件数へ加算しない。TCなしだけを根拠に架空のTCを作らない。
5. 既存Baselineのmember判定・全列挙・scope identity、Runの部分選択、Activityの状態・raw結果参照・未解決を保持する。route追加後も旧保存物を誤読・再採番しない。必要なversion移行と旧形式読取を検証する。
6. Regression Skillはrunnerを起動する責務を持たない。実行ownerは[テスト実行と品質契約](./2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)の方式選定に従って決め、選択Runの計画・要求route・実結果をRegressionへ渡す。

### 必須検証

- 固定`qa-training-store` commitで、TCに紐付いたVitestの選定→必要route→実開始→結果確定→Activityまでを通す。
- `manual`／`e2e`／`testware`の混在、複数route、部分Run、TCなし補助testware、skip／未実行、retry、runnerエラー、cleanup不全、旧sourceでの変更検出を検証する。
- 未確認のrunner結果、実開始前blocked、試行途中timeoutは`executed`／`完了`に誤変換しない。

## 3. セッション間の引継ぎと復旧

1. 同一Agentクライアントで全Skillを利用可能にした発火試験は維持する。これに加え、**別のセッションで同じsource／成果物を再読込して継続できること**を受入条件とする。
2. セッション間で受け渡すのは、ownerが保存した成果物参照・revision、依存source／承認、未完了範囲・担当・再開条件であり、LLMの非永続会話履歴は正本にしない。
3. 再開したセッションは、各ownerの保存済み状態と外部依存を再取得する。古い状態を引継ぎ文に引用しただけではcurrentとみなさない。
4. 必要Skillを利用できないセッションでは該当範囲を`blocked`とする。利用できる別のセッションが後で続行できればよく、自動Agent切替・常時監視機構は新設しない。
5. 保存途中・副作用中断の復旧は[保存・承認の共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)に従う。操作開始前に残す識別子、実保存の照合、状態不明の副作用の再試行禁止を受入で実証する。

### 必須検証

- 分析をセッションAで完了し、設計・実行をセッションBで実行して、同じ成果物ID・revision・Authorityを利用する。
- セッションAで一部scopeがblockedとなり、必要情報が追加された後、セッションBで該当scopeだけ再開する。
- 承認変更、source revision変更、欠落ref、取得権限拒否では安全に停止し、無関係なcurrent scopeを維持する。

## 完了条件

1. 未登録Skill・未検証のowner成果物がworkflow完了を発生させない。対応登録済みの新設Skillが、単独・複合両方で検証済み成果物として扱える。
2. RegressionのTCに紐付く非E2E実行が正式required routeに接続され、既存manual／E2E／TCなし補助経路の履歴・件数・状態が回帰しない。
3. 別セッションでも参照・現在性・停止理由から再開でき、Agent製品・モデル・CLIや外部自動起動を前提としない。
4. ownerの責務境界、source／artifact currentness、必要な完了証拠は、実コード・fixture・実Agent・実runnerで確認する。Planへの記載だけでは完了としない。
