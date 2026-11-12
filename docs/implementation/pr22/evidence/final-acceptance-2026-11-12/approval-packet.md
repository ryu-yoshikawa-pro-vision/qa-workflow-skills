# PR #22 承認事項：横断接続の契約案と意味評価の判断案（2026-11-12）

利用者の決定（契約案・判断案を提示し、承認を得てから実装する）に基づく確認資料。各項目の「推奨」は提案であり、承認されるまで実装しない。rubricを結果に合わせて緩める変更は提案しない。

## A. 横断接続の契約案

共通方針：**変換は出力側（producer）のownerが持つ**。入力側（consumer）の既存契約と検証は変えず、producerが「consumerの契約どおりの入力」を組み立てる関数を持つ。G→H（`regression_source_execution()`）と同じ形にそろえる。保存先からの読み戻しが必要な値は、Git providerのreadback結果から取る。

### A-1. B（feature-analysis）→ D（test-item-analysis、test-condition-analysis）

- **現状**：Dは`{snapshot, analysis}`と`feature_ref{owner, scope, artifact_ref, revision, content_hash}`を検証する。Bの`persist_snapshot()`はこの組を返さない。storeの戻り値は`sha256`とstore revision（`r<N>`）で、名前も意味も異なる。
- **推奨**：`feature_registry.py`に`candidate_handoff(store_readback, snapshot, analysis)`を追加する。対応は次のとおり。
  - `owner="feature-analysis"`、`scope`＝`project_ref`、`artifact_ref`＝snapshotの`artifact_ref`
  - `revision`＝snapshotの`artifact_revision`（論理revision）、`content_hash`＝`snapshot_sha256`
  - storeのrevision（Gitのcommit SHA）は`storage_revision`として別に返し、Dの`revision`へ混ぜない
  - readbackした本文のhashが`snapshot_sha256`と一致しない場合は拒否する
- **検証**：Bの実`persist_snapshot()`→readback→`candidate_handoff()`→Dの`materialize`を通すテスト。hash不一致、stale、未保存の拒否例を含める。

### A-2. B → C（ui-target-analysis）

- **現状**：`human_editing.py::_feature_index`は、feature ref／revisionが空でないことしか確認せず、B成果物を読まない。
- **推奨**：Cは`_feature_index`の入力に、A-1と同じ`feature_ref`とsnapshotを受け取る。`feature_scope_refs[].feature_id`がsnapshotに存在し（`FEAT-`形式）、`content_hash`が一致することを確認する。存在しない機能IDや古いrevisionは拒否する。
- **検証**：Bの実snapshotを使ったテスト。既存の人間編集8ケースの`FEATURE-001`等のfixture IDは、Bの`FEAT-`形式へ更新する。

### A-3. D → E（正式設計 `formal-design-v1`）

- **現状**：D自身のdata contract（L55）が「D→E adapterは無い」と記録している。Eはitemを`TI-*`、sourceを`{ref, revision, currentness}`で受ける。Dはitemを`ITEM-*`、sourceを`{owner, scope, artifact_ref, revision, content_hash}`で出す。conditionはどちらも`COND-*`。
- **推奨**：Dの候補は正式設計ではないので、**Eの`TI-*`はEが採番したまま**にし、Dの候補は「根拠source」として渡す。D側に`formal_design_sources(candidate_artifact, impact_result)`を追加し、次の形を返す。
  - `source_refs`：`{ref: "<D artifact_ref>#ITEM-001", revision: <D content_hash>, currentness: current|stale}`。currentnessはDの既存`impact`操作の結果から決める。
  - condition候補：`{condition_ref: COND-xxx, source_ref: "<D artifact_ref>#COND-xxx"}`
  - EのitemはEが`{item_ref: TI-xxx, source_ref: "<D artifact_ref>#ITEM-xxx"}`として採用する。採用の判断はEが行い、自動で採用しない（Plan「正式TCNへの根拠付き採用」）。
- **E側の変更**：`source_ref`の`#ITEM-`／`#COND-`付きrefを受理することだけ。
- **検証**：Dの実`materialize`→`formal_design_sources()`→Eの`validate_formal_design`→coverageを通すテスト。Dがstaleのとき、Eの該当itemが要再検証になる例を含める。

### A-4. e2e-test-selection → e2e-test-inspection（→実装・実行）

- **現状**：下流3 Skillに選定結果の読み手が無い。
- **推奨**：`e2e-test-inspection`がselection（`E2ESEL-xxx`＋revision）を受け取った場合は、次のとおり扱う。
  - `selection_contract.py validate`で検証し、`decision=selected`の候補だけを対象にする
  - 「対象決定」表の決定根拠に、selection refとrevisionを記録する
  - selectionがstaleまたは未検証のときは、対象決定をblockedにする
  - TC直接指定、既存E2Eの実行、有効な既存選定の再利用は、従来どおり選定なしで開始できる
  - 実装・実行はinspectionの対象を引き継ぐだけなので、変更しない
- **検証**：実`selection_contract`出力→inspectionのvalidatorのテスト。not_selected、deferred、stale selectionの拒否を含める。

### A-5. I（exploratory-testing）→ J（defect-management）

- **現状**：Jの欠陥候補は`source_kind`、`run_ref`、`result_ref`、`scope_ref`、`environment_ref`、`symptom`、`target`、`result_finalized`、`cause`、`expected_result`、`evidence`を要求する。Iのhandoffはこれを持たず、読み手も無い。
- **推奨**：`exploratory_runtime.py`に`defect_candidate_source(handoff, session)`を追加する。対応は次のとおり。
  - `source_kind="Finding"`、`owner_skill="exploratory-testing"`
  - `run_ref`＝`session_ref@session_revision`、`result_ref`＝`finding_ref`
  - `scope_ref`＝charterのscope、`environment_ref`＝sessionの環境条件、`target`＝sessionの対象build／source revision
  - `cause`：investigationで確定していなければ`unconfirmed`
  - `expected_result`：`source_refs`に仕様Authorityがあればそれを使い、無ければ欠落のまま渡す。Jは既存規則（DEF-D005）で「未成熟→`spec-analysis`／元ownerへ戻す」と判定する
- **検証**：Iの実handoff→投影→Jの`assess_candidate`のテスト。成熟、未成熟（期待結果の根拠なし）、原因未確定の例を含める。

### A-6. G／H／I → J（test-reporting）

- **現状**：Jのrecordは`{unit, unit_ref, result_ref, state∈{PASS, FAIL, 未実行, SKIP, 判定不能, blocked}, build_ref, environment_ref, source_revision, executed_at, result_finalized, cleanup_status}`。各producerからこの形への投影が無い。
- **推奨**：各producerに`reporting_records()`を追加する。元結果は変えず、集計用の読み取り投影だけを行う。
  - **G**（`kind`＝`component`／`api`／`batch`／`nonfunctional`等、`unit=test`）：個別test結果の`passed`→PASS、`failed`→FAIL、`skipped`／`todo`→SKIP、計画にあるが報告に無いもの→未実行、収集不完全→判定不能、runがblocked→blocked。`result_finalized`と`cleanup_status`は`regression_source_execution()`と同じ判定を使う。
  - **H**（`kind=regression`、`unit=tc_route`）：route結果が実行済みで結果確定ならsource resultを状態へ写像する（PASS／FAIL、`runner_pass`→PASS、`runner_fail`／`observed_FAIL`→FAIL）。未実行→未実行、blocked→blocked。写像できないsource resultは判定不能。Activity状態（`完了`等）は集計状態にしない。
  - **I**（`kind=exploration`、`unit=session`）：sessionの完了→PASS相当にはしない。session単位の状態は`判定不能`（PASS／FAILが無い方式）とし、Findingは`unit=finding`の記録として渡す。Jの既存規則のとおり、Findingは集計率に含めない。
- **検証**：G、H、Iの実出力→`build_snapshot()`のテスト。未取得、部分取得、旧revision、重複の検出を含める。

### A-7. Plan 04 §1 owner verifier（承認済み：実装する）

承認済みなので、設計だけ共有する。

- workflow_runtimeに`OWNER_VERIFIERS`を追加し、対象Skillごとに検証入口を登録する。
- 検証の流れ：Git providerから成果物を読み戻す → 内容hashが宣言revisionと一致 → owner Skillの本番validate（例：`item_candidates.py validate`、`selection_contract.py validate`、`reporting_runtime`の再計算）を実行 → source currentnessを確認。すべて満たしたscopeだけ完了扱いにする。
- 本番validateを持たないF 3 Skill（Markdownのみ）は、eval validatorに「保存済み成果物から導いた既知source」を渡す形で登録するか、未登録のまま残すかを、実装時に改めて確認する。

## B. 意味評価の未解決11件の判断案

事実の出典：`evidence/semantic-2026-11-10/semantic-evidence-v12.tar.gz`、各Skillの`evals/semantic/cases`、SKILL.md、references、scripts（行番号はHEAD `ce78b4ea`）。

| Case                                  | 何が起きているか                                                                                                                                                                                                                                                       | 推奨                                                                                                                                                                                                                                                                                                    | 変更するもの                                                                                    |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| RISK-SEM-002（test-analysis）         | referenceは「表示・主要遷移」というE2E候補の重点を期待する。一方、現行契約ではE2E選定は`e2e-test-selection`へroutingする（SKILL.md:17）。referenceがE2E選定の旧契約のまま残っている                                                                                    | **fixture側の修正**。referenceを「Product Riskと重点を示し、E2E選定は`e2e-test-selection`へ送る」に更新する。SEM-RISK-004はそのまま評価する                                                                                                                                                             | `test-analysis/evals/semantic/cases/case-002/reference.md`                                      |
| RISK-SEM-005（test-analysis）         | Skillの正本（guidance:49「統計的確率ではなく代理指標」）とcandidateは一致している。Judgeは発生率の定量データを求めた。referenceは入力に無い「運用プロファイルがある」を前提にしている                                                                                  | **Skillは変えない**。referenceの前提を入力に合わせて直し、「Likelihoodは代理指標で定性的に判断し、発生率は要求しない」を明記する。rubricは変えない                                                                                                                                                      | `case-005/reference.md`                                                                         |
| E2E-SEL-SEM-003（e2e-test-selection） | 入力は「TI-003はcurrent」と書くが、TI-003自身のrevisionが無い。正本（guidance:9）はtest itemごとにrevisionを要求するので、candidateのblockedは正本どおり                                                                                                               | **正本を維持（TI-003自身のrevisionが必要）**。入力fixtureにTI-003のsource行とrevisionを追加し、referenceの「TI-003を追加」が成立する入力にする                                                                                                                                                          | `e2e-test-selection/evals/semantic/cases/case-003/input.md`                                     |
| COV-SEM-002（coverage-analysis）      | 入力にTR／TCN／CIが無い監査で、candidateがTCだけのQA graphを作り、孤立と判定した。fixtureは同じ`TC-101`をAuthority IDとTC IDに兼用している                                                                                                                             | **guidanceを明確化**：「監査入力に無い上流層を推測でQA graphへ追加しない。上流未提供は孤立ではなく判定不能として記録する」。runtimeは変えない。fixtureのID兼用を解消する                                                                                                                                | `coverage-analysis/references/guidance.md`、`case-002/input.md`                                 |
| TC-SEM-001（test-case-design）        | fixtureのCI Machine Entityに必須の`scope_refs`が無い（`case_structure.py`が拒否する）。candidateはfingerprintを1桁写し間違えた                                                                                                                                         | **fixtureを修正して再評価**：`scope_refs`を追加し、fingerprintを再計算する。Skillとrubricは変えない                                                                                                                                                                                                     | `test-case-design/evals/semantic/cases/case-001/input.md`                                       |
| TC-SEM-002（test-case-design）        | 入力のAuthorityはIDもrevisionも無い散文だけ。正本（SKILL.md:12）は「Authority refが空なら完成扱いしない」                                                                                                                                                              | **正本を維持（散文のAuthorityはcurrentな仕様根拠ではない）**。入力にAuthority ID／revisionを追加し、referenceの「TC化」が成立する入力にする                                                                                                                                                             | `case-002/input.md`                                                                             |
| TCN-SEM-004（test-condition-design）  | **本当の矛盾**。runtimeと旧Plan（03:135）は「lifecycle sequenceにentityの全適用operationを含める」、Skill reference（coverage-techniques:83）とsemantic referenceは「指定sequence後の状態関係を項目化する」。Orderの`get`（読み取り）がsequenceに無いためblockedになる | **案C**：lifecycle sequenceに必須とするのは**状態を変えるoperation（C／U／D）だけ**にし、R（読み取り）はmatrixのcellでcoverする。状態の一貫性という目的に合い、変更も最小になる。代替案：A（現行runtimeを維持し、referenceをblocked期待へ変更）、B（指定sequenceだけで閉じ、全operationの要求をやめる） | `crud_matrix.py`、Plan 03:135、`coverage-techniques.md:80`、CRUD runtimeのテスト                |
| TCN-SEM-008（test-condition-design）  | 入力は全因子pairwiseとsubsetの3-wiseを明示的に要求した。candidateとruntimeは別criterionとして両方を追跡した。Judgeは3-wiseの射影に含まれるpairを重複とした                                                                                                             | **明示要求されたstrengthは別criterionとして保持**し、射影による重複の削減はTC組成（test-case-design）で行うことを`coverage-techniques.md:91`に明記する。rubricは変えない。fixtureにchild model keyを追加する                                                                                            | `coverage-techniques.md`、`case-008/input.md`                                                   |
| TCN-SEM-012（test-condition-design）  | candidateが`=`を`version_range`に写し間違えた。fixtureにtargetのdigestが無い。runtimeの`version_range`は片側だけの範囲（`>= 2.0`）を表せない                                                                                                                           | **runtimeを拡張**し、`version_range`の片側境界を許可する。fixtureにdigestを追加して再評価する。あわせて、記録上「SEM-TCN-004はneeds_review」となっている誤記を直す（保存結果はpass）                                                                                                                    | `test_data_requirements.py`／`runtime_contract.py`、`case-012/input.md`、E記録とsemantic README |
| TCN-SEM-013（test-condition-design）  | 正本（coverage-techniques:126、`materialize_coverage.py`）は「merge後のrequirementの交差が空ならmerged CIを拒否する」と明記している。candidateは「仕様がない」としてblockedにした                                                                                      | **Skillは変えない**（candidateの逸脱）。fixtureに別model Cのcurrentnessを追加して再評価する                                                                                                                                                                                                             | `case-013/input.md`                                                                             |
| TCN-SEM-014（test-condition-design）  | 入力にテスト要求が無く「target closureとmodel completionを評価」だけを求めた。rubricはTCN／CIの作成を必須とする                                                                                                                                                        | **fixtureにテスト要求を追加**し、closureをTCN／CIで表す入力にする。referenceに閉鎖の表し方を追記する。rubricは変えない。代替案：closureだけの依頼ではTCN／CIを作らない（rubricの適用範囲を狭める変更になるため非推奨）                                                                                  | `case-014/input.md`、`reference.md`                                                             |

### 再評価の進め方

承認後、修正したcaseだけを現行HEADで再生成・再採点する。候補生成もJudgeもHaiku 5.5で行い、別session・別contextに分ける。独立性が限定的であることを結果に明記する。過去のrun結果は上書きせず、新しいrunとして記録する。
