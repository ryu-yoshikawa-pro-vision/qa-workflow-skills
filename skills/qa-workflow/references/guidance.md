# QAワークフロー オーケストレーション詳細

## 目的

複数QA Skillを成果物ベースでルーティングし、開始点、再利用、ブロック中 / 再開、変更伝播、修正先、ワークフロー全体状態を管理します。

工程固有の判断規則は担当Skillを正本とし、本ガイダンスへ複製しません。

## 入力

必須:

- ユーザー要求
- 要求する最終成果物
- 識別可能な対象範囲

利用可能なら情報源、既存QA成果物、案件コンテキスト、進行モード、既知のブロック中 / 残存リスク / `要再検証`状態、正本一覧も使います。

情報源や既存QA成果物がまだないこと自体は`qa-workflow`の起動を妨げません。担当Skillへルーティング後、そのSkillの必須入力を満たさない範囲をブロック中として扱います。

## ランタイム前提

全体ワークフローでは、repositoryの全Skillが同一のAgentクライアント上で利用可能であることを前提とします。

- `qa-workflow`
- `spec-analysis`
- `question-analysis`
- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`
- `adversarial-review`
- `e2e-test-inspection`
- `e2e-test-implementation`
- `e2e-test-execution`
- `e2e-test-result-analysis`
- `e2e-test-reporting`
- `test-target-inspection`
- `test-execution`
- `regression-testing`
- `exploratory-testing`
- `qa-knowledge`

Agent Skills Specificationは共通Skill-to-Skill呼び出しAPIを規定しません。本ワークフローは、Agentクライアントが必要なSkillを追加で読み込み / 利用できる実装で動作することを前提とします。

必要Skillを利用できない場合は、そのSkillの責務を別Skillへ肩代わりさせず、必要範囲をブロック中として扱います。

## 工程固有ロジックの正本

| 工程固有ロジック                                            | 担当Skill                    |
| ----------------------------------------------------------- | ---------------------------- |
| 案件Project Context / 成果物配置・編集方針の合意            | `project-context`            |
| 製品機能ID / 情報源母集団 / 開発差分分類                    | `feature-analysis`           |
| 現在有効な仕様根拠の解決                                    | `spec-analysis`              |
| UI構造・画面・操作・状態・遷移、human editing               | `ui-target-analysis`         |
| 不明点分類 / 回答正規化                                     | `question-analysis`          |
| QA要求 / 品質目標 / 合意状態                                | `test-requirements-analysis` |
| テストレベル・タイプ・方式・環境の全体設計                  | `test-architecture-design`   |
| QA計画 / 開始・終了基準 / 進捗・差異 / プロジェクトリスク   | `test-management`            |
| プロダクトリスク / リスクマトリクス / 設計深度              | `test-analysis`              |
| テスト要求粒度 / 上流閉鎖                                   | `test-requirement-design`    |
| テストアイテム候補                                          | `test-item-analysis`         |
| テスト条件候補                                              | `test-condition-analysis`    |
| カバレッジ基準 / カバレッジ項目 / テスト技法                | `test-condition-design`      |
| 詳細テストケース / 期待結果の根拠の具体化                   | `test-case-design`           |
| E2E自動化対象の選定・理由・履歴                             | `e2e-test-selection`         |
| 生きたテスト対象のUI情報・ふるまい収集 / 管理               | `test-target-inspection`     |
| AIによる詳細TC実行・期待結果比較・結果記録                  | `test-execution`             |
| 非E2E testware実装・静的 / 軽量検証                         | `testware-implementation`    |
| 非E2E testware runner・実行結果・cleanup                    | `testware-execution`         |
| カバレッジ / 閉鎖性 / ギャップ                              | `coverage-analysis`          |
| 独立レビュー / 重大度                                       | `adversarial-review`         |
| E2E対象、repo / 実対象の事実、実装可能性、安全条件          | `e2e-test-inspection`        |
| Playwright E2Eコード変更、静的 / 軽量検証                   | `e2e-test-implementation`    |
| 実行安全確認、準備、Playwright実行、構造化結果、cleanup     | `e2e-test-execution`         |
| 実行事実からの原因分析、追加証拠要求、修正routing           | `e2e-test-result-analysis`   |
| 検証済み結果の人間向け報告                                  | `e2e-test-reporting`         |
| Regression baseline / membership / Run selection / Activity | `regression-testing`         |
| Charterに沿った探索・owner不明hypothesisの実対象調査        | `exploratory-testing`        |
| QA knowledge candidate triage / entry lifecycle / lookup    | `qa-knowledge`               |
| 欠陥候補 / 外部Issue引継ぎ / 修正確認依頼                   | `defect-management`          |
| 計画母集団に基づく統合報告snapshot                          | `test-reporting`             |
| QA活動の評価・改善の効果測定                                | `test-evaluation`            |
| ルーティング / ブロック中 / 再開 / 変更伝播 / 完了          | `qa-workflow`                |

### 現在有効な仕様根拠への依存

製品期待挙動の現在有効な仕様根拠が必要な場合は、`spec-analysis`の有効成果物を使用します。

既存`spec-analysis`成果物が対象範囲の現在有効な仕様根拠を十分に解決していない、古い、または競合を残している場合は`spec-analysis`へ戻します。

`qa-workflow`自身は、SPEC / DECISION / ASMの優先関係、バージョン選択、情報源優先順位、仕様根拠の競合解消を行いません。

Project ContextのSection 12 / 13が案件の決定事項・仮定の正本ownerである場合、DEC / ASMのstable IDと履歴は`project_context_ids.py`でmaterialize / validate-historyします。別の正本ownerが明示されている場合はProject Contextへ複製・再採番しません。runtime-v1からの移行順序、UI target package migration、scope ownership normalizationの次工程は`migration_preflight.py`のstatusと`cutover_next_action`を正本とし、Agentがartifact versionやscope readinessから再判断しません。

### その他の工程固有ロジックへの依存

- プロダクトリスクの採点が必要 → `test-analysis`
- テスト要求の粒度判断が必要 → `test-requirement-design`
- BVA / Pairwise / 状態遷移等の具体カバレッジ判断が必要 → `test-condition-design`
- テストケースの期待結果の根拠 / 具体性判断が必要 → `test-case-design`
- カバレッジ判定が必要 → `coverage-analysis`
- 重大度付き独立レビューが必要 → `adversarial-review`

currentな画面名称・到達方法・操作可能性・観測可能性が必要なら、必要範囲を`test-target-inspection`で実対象確認してから設計Skillへ戻します。既存のテスト対象資料は補助情報として再利用できますが、資料やrepoだけで今回のcurrentnessを判定せず、実対象の挙動を期待結果の仕様根拠にしません。詳細TCの実操作・比較が要求された場合だけ`test-execution`へ進みます。

## 成果物チェーン

```text
現在有効な仕様根拠
  ↓
テスト要求
  ↓
テスト条件
  ↓
カバレッジ項目
  ↓
テストケース
  ↓
カバレッジ分析
```

プロダクトリスクは深度・優先度の横断入力です。反証レビューは各成果物層に適用できます。

## testware / E2E要求時の分岐

すべてのSkillを固定順に実行しません。要求成果物と有効な成果物から必要な依存だけを選びます。

- 生きたテスト対象の情報収集・更新・鮮度確認だけが必要 → `test-target-inspection`
- 設計前にcurrentな対象情報が必要 → `test-target-inspection` → 必要な設計Skillへ戻る
- `test-item-analysis` / `test-condition-analysis`は候補分析だけを担当し、正式な要求・条件設計は`test-requirement-design` / `test-condition-design`へrouting
- 非E2Eのtestware implementation / runner execution → `testware-implementation` / `testware-execution`
- 詳細TCをAIが今回runとして実行・観測 → `test-execution`
- どの業務経路・機能をE2E自動化するかの選定 → `e2e-test-selection`。再利用できるcurrent選定結果がなければ選定し、選定済み対象だけを`e2e-test-inspection`へ渡す。TC直接指定、既存E2E実行のみ、有効な選定結果がある場合は選定を再実行しない
- repoへ残すPlaywright E2Eのinspection / 実装 / 正式runner実行 → 既存の`e2e-test-inspection` / `e2e-test-implementation` / `e2e-test-execution`

- 詳細TCからE2E実装: `e2e-test-inspection` → `e2e-test-implementation` → `adversarial-review`（対象: `E2E実装`） → `coverage-analysis`（対象: `TC → E2E実装`）
- TCなしの明示E2E対象 / 既存E2E更新: 確認済みinspection情報がなければ `e2e-test-inspection` → `e2e-test-implementation`。E2E対象選定が要求されない限り`test-analysis`を必須にせず、TC生成のためだけに`test-case-design`へ戻さない
- 既存E2Eの実行だけ: `e2e-test-execution`から開始できる。実行安全条件を確認できない場合だけinspectionへ戻す
- 設計からE2E実行: 既存の設計経路 → `e2e-test-inspection` → `e2e-test-implementation` → E2E実装のreview / coverage → `e2e-test-execution`
- 実行異常、未実行、run-level error、cleanup失敗 / 未確認、明示分析要求がある場合: `e2e-test-result-analysis`。正常runかつ分析要求なしなら省略できる
- 追加実行が必要な場合: result-analysisはPlaywrightを直接起動せず、仮説・取得証拠・範囲を示して`e2e-test-execution`へ戻す
- 確定済み結果の報告だけ: `e2e-test-reporting`から開始できる。reportingは原因再判定や仕様再解釈をしない

`e2e-test-inspection`、`e2e-test-implementation`、`e2e-test-execution`等のPlaywright固有契約は各Skillを正本とし、本Skillへ複製しません。

## 状態と完了

状態表の一意性はSkill名ではなく`(Skill, 対象 / 実行範囲)`で判定します。複数用途Skillの正規対象は次です。

| Skill                | 正規対象 / 実行範囲                                  |
| -------------------- | ---------------------------------------------------- |
| `test-analysis`      | `テスト分析` / `E2E対象選定`（旧成果物の読取互換）   |
| `coverage-analysis`  | `テスト設計` / `TC → E2E実装` / `E2E実装 → 実行結果` |
| `adversarial-review` | `テスト設計成果物` / `E2E実装`                       |

単一用途Skillの対象欄は空欄にできます。開始Skill、最終Skill、`question-analysis`回答後の再開Skillが複数用途Skillなら対象 / 実行範囲も必須です。

追加した複数用途Skillの正規対象:

| Skill                  | 正規対象 / 実行範囲                                                |
| ---------------------- | ------------------------------------------------------------------ |
| `regression-testing`   | `baseline / membership` / `Run計画` / `Run結果更新` / `履歴参照`   |
| `exploratory-testing`  | `exploration` / `investigation`                                    |
| `qa-knowledge`         | `triage` / `create / update` / `revalidation` / `lookup / history` |
| `usability-inspection` | `general` / `scoped` / `formal-handoff`                            |

単独baseline、Regression membership、Run計画、履歴参照だけなら`regression-testing`から開始できます。manual / E2E実行まで要求されたRegressionは`qa-workflow`が全体を追跡し、`regression-testing`と既存execution Skillを接続します。変更影響候補 / Product Riskは`test-analysis`、Regression Run selectionは`regression-testing`の責務です。

Explorationは未知領域のCharterベース探索、Investigationは既存ownerで解けないsymptom / hypothesisの実対象検証に限ります。current UI収集、既知TC実行、E2E failure分析は既存ownerへ直接送ります。

`qa-knowledge`はknowledge lifecycle要求の入口です。既存knowledgeを入力に使うだけならgatewayにせず、candidateが仕様 / Risk / current UI / formal designへ属する場合は正本ownerへ戻します。

要求された成果物 / workflowの担当Skillが自身の完了条件を満たし、対象scopeに未解決の`ブロック中` / `要再検証`がなく、必要な追跡性とcurrentness確認が閉じている場合に完了できます。実操作を含む場合は、必要なcleanupとunresolved stateも閉じていることを確認します。全E2E結果のPASSは共通条件ではありません。

工程固有の完了条件は担当Skillを正本とし、`qa-workflow`へ複製しません。要求内容に応じ、次を条件付きで確認します。

- 新規・改修のテスト設計を要求する場合だけ、仕様根拠、Risk、TR、TCN、TC、coverage等の該当契約を要求します。
- E2Eを要求する場合だけ、E2E実行・分析・報告・cleanupの該当契約を確認します。
- Regressionは`regression-testing`、Exploration / Investigationは`exploratory-testing`、QA Knowledgeは`qa-knowledge`の完了条件を正本とします。
- 案件配置・機能ID・QA要求・方式・計画・E2E選定・欠陥・統合報告・活動評価は各担当Skillの完了条件を正本とします。`workflow_runtime.py`にowner verifierが登録されていないscopeは`unverified_scopes`として残り、workflow全体を完了にしません。

要求された分析・報告と安全なcleanupが完了し、追加修正が要求されていなければ、FAILを含む実行結果でも完了できます。

## 共通の扱い

### `対象外`

ユーザー、案件コンテキスト、または現在有効な対象範囲から外れる根拠がある場合に使用します。低プロダクトリスクだけを理由に使用しません。

### `別テストレベル`

現在レベルでは適切に検証できず、より適切なテストレベルを説明できる場合に使用します。

### `残存リスク`

対象範囲内だが意図的に未カバーとする場合に使用します。理由、関連プロダクトリスク、未カバー内容を明示します。

### `ブロック中`

必要な仕様根拠、重大な矛盾、必須入力不足等により、妥当な設計判断を確定できない範囲に使用します。

工程固有の扱い（例: `成立不能`、`重複`）の詳細条件は担当Skillを正本とします。

## 継続管理workflowのproduction helper checkpoint

Project Contextの`qa.workflow_state_root`はworkflowごとのpersisted stateとhelperが導出するclaimのrootです。Regression ActivityやExploration Sessionの汎用history rootではありません。既存のRegression / Session artifactはProject Contextの「既存QA成果物」欄または要求で渡されたdirect ref / 明示rootから解決します。入口が与えられていないhistoryは推測せず未解決として扱います。

### workflow開始 / resume

継続管理workflowの決定論的処理はqa-workflow package内の`scripts/artifact_graph.py`を使います。

1. `parse_project_context`でProject Context stable keyをparseし、`validate_required_context_fields`で今回必要なkeyを検証します。
2. Project Contextの`qa.workflow_state_root`からworkflow state rootを解決します。値が未設定または解決できない場合は継続をblockします。
3. persisted workflowのresumeでは`canonical_state_path` / `read_workflow_state`でstateをcanonical pathから取得します。初回保存は`create_workflow_state`のatomic create-if-absent結果を確認します。
4. workflow snapshotで記録した`used_fields`だけを`compare_used_context`でcurrentness比較します。Project Context全体revision差だけで未使用fieldをstaleにしません。
5. 必要なfixed-root scanは`scan_fixed_root`を使い、scan failure / truncationをcomplete扱いしません。state更新前は`state_update_decision`でnative atomic conditional write capabilityをgateします。

### UIテスト対象分析

UI構造・画面・操作・状態・遷移を分析し、継続利用する`ui-target-v1` packageを作成・更新する要求は`ui-target-analysis`から開始します。単一表に収まる小規模な対象でも、継続利用・更新する目的があれば独立packageを使います。package作成や構造理解だけが要求されている場合、`test-analysis`以降へ自動進行しません。`ui-target-analysis`は既存writerとhelperを利用し、single writer、history、migration、`ui-target-v1`互換性を維持します。期待仕様、Authority、US / UC / Behavior / AC、UNKNOWNの正本は`spec-analysis`です。UI構造、画面観測、repository factを期待仕様のAuthorityへ昇格しません。

- packageに未解決事項があり回答整理も要求された場合は`question-analysis`へ進みます。正式回答は対応するUNKNOWN IDを保持して記録し、`spec-analysis`へ戻ってcurrent UNKNOWNとpackageを更新してから後続を再開します。暫定回答を正式なDECISIONへ昇格しません。
- packageが既にあり、不明点への回答を反映する要求は、`question-analysis`の解消処理後に`spec-analysis`で期待仕様を更新し、`ui-target-analysis`で必要なUI packageを再開します。回答済み論点は根拠がcurrentな間は再質問しません。
- repository調査は補助入力として`spec-analysis`のRepository確認へ記録し、UI構造の分析は`ui-target-analysis`へ渡します。repository factを仕様Authorityへ昇格したり、implementation gapを仕様変更として扱ったりしません。
- current live UIの表示・到達性・実画面状態を観測する要求は`test-target-inspection`へ進みます。repositoryを読むだけの調査はこのSkillへrouteしません。
- 保存済みFigma / screenshot等の画面資料をbrowser操作なしでUI/UX評価する要求は`usability-evaluation`へ進みます。live browserで使用性、focus、responsiveを観測する要求は`usability-inspection`へ進みます。WCAG 2.xと適合レベルを指定したformal評価は`wcag-conformance-evaluation`へ進みます。
- UI仕様理解packageが完成しても、テスト設計が不要ならそこで終了します。ready scopeとblocked scopeが混在する場合、packageの`scope_readiness[].blocking_unknown_ids[]`だけを`question-analysis`へ渡し、独立してreadyなscopeの進行をUNKNOWN総数だけで停止しません。

### WCAG formal evaluation state

WCAG canonical Plan provenanceとreport完了には、`register-wcag-evaluation-plan`、`read-wcag-evaluation-state`、`finalize-wcag-report` operationを使います。この既存のWCAG固有経路は`qa.workflow_state_root`配下のlocal SQLiteを利用します。workflow stateのSQLite更新時にはrevision履歴を同じtransactionで保存し、`read_sqlite_workflow_state_revision(root, workflow_ref, revision_token)`で旧revisionを取得します。revision 1から連続する履歴がない旧DBは`historical_revision_available=false`です。新規DBには最初のhistory revisionを同一transactionで記録し、記録済みのrevisionが一つでも欠落した場合はreadback／CASをblockします。旧DBに履歴がない場合は移行開始時のcurrent revisionからのみ履歴を保持し、欠落した古いrevisionを作成しません。履歴はあるが開始revisionを証明できない旧DBは、不完全な履歴を安全な移行と推測せず更新を停止します。対応する原子性は単一hostのlocal filesystemのみであり、汎用QA成果物や共有リソースの保存先としてSQLiteを採用したことにはなりません。network filesystem、複数host、未設定root、DB破損、transaction / lock failureではblockedとします。

登録は既存WCAG evaluation ownerが確定した評価入力、scope決定とevidence refs、selected sample / variation / processおよびsource artifact refsを引き継ぎます。caller提供Planだけから正本を作らず、同じevaluation revisionの対象縮小を拒否します。SQLite state revisionはWCAG evaluation revisionとは別です。WCAG `close-report`が返すのはunresolved candidateであり、generation fingerprint一致だけではclosure証明になりません。QA workflowはdeclared runtime dependencyの`result_fingerprint`とcandidate envelope全体を照合します。Machine Runtime freshness検証はその依存fingerprintを独立に取得したcurrent runtime rowと比較します。このcurrent rowを使うfreshness検証を通らない同一generationのpayload / 工程入力差し替えは、staleとして扱います。照合済みcandidateに含まれる有限な工程入力を、QA workflowはcurrent recordから取得したPlan・結果に結合し、既存`close_report()`を再実行してWCAG-EM工程とaccessible outputのcomplete状態を確認します。その後、期待SQLite revisionでCAS更新し、別connectionから再読込して完了を返します。ただし、現行`finalize-wcag-report`はcurrent Machine Runtime rowを独立取得せず、callerが用意したdependency metadataとcandidateの一致を確認するだけです。metadataも自己作成できる直接呼び出しは完了を偽装でき、ownerが独立してcurrent rowを結び付ける取得契約が残っています。これは既存のgeneric workflow / handoff CASを置き換えず、SQLite recordの存在だけでowner承認を証明しません。

### mutable operation開始直前

1. owner execution contractに同一operation identity向けatomic pre-start claimまたはidempotent startがあるか確認し、ある場合はowner contractを利用します。
2. owner contractがなければ`claim_mutable_operation(workflow_state_root, workflow_ref, operation_ref, operation_details=...)`を使います。`operation_details`には`owner_skill`、`scope_ref`、`operation_type`、`target_ref`、`source_revisions[]`、`artifact_revisions[]`、`expected_revision`、`approval_ref`、`permission_scope`、`resume_owner`を入れます。source／成果物のrevisionは操作前にownerの正本から確定し、秘密情報の実値は渡しません。helperは`qa.workflow_state_root`配下の`claims/<canonical identity digest>.json`へatomic create-if-absentで記録し、独立readbackを照合してから`may_start=true`を返します。`operation_details`なしの3引数呼出しは`operation_details_required`でblockします。旧3引数呼出しが作成したclaimは別セッションで読取互換として保持しますが、再実行は許可しません。
3. 別セッションでの再開時は、保存時の`claim_revision`を保持して`read_mutable_operation_claim(..., expected_claim_revision=...)`で独立読戻しします。`status=current`でも`may_start=false`であり、元ownerの実開始・実保存・cleanupを再取得するまで同じoperation identityの副作用を再実行しません。revision不一致は`conflict`、欠落・改ざん・読取権限不足は`blocked`です。
4. claimが重複・改ざん・読戻し不一致・保存失敗になった場合は、同じoperation identityを再実行せず`blocked`にします。`recover_claim()`はprovider-nativeの条件付き解放を実行しません。現状は実行・cleanup証拠の真偽とclaim revisionを検証する接続がないため、開始前の中断でも`claim_release_provider_not_connected`で停止します。実ownerの保存済み状態と条件付き解放を接続するまで、`may_start`を復旧させません。claimは承認主体の認証や遠隔providerのCASを代行しません。

### shared resource使用前

resource ref、workflow間のisolation条件、利用するreservation provider、認可・解放条件をProject Contextの実施環境 / 対象条件欄で確認します。`qa.reservation_root`は場所を示すだけで、保存先のnative CASや予約・解放能力を保証しません。

1. 実際にworkflowごとに分離されたresourceなら`isolated=True`を指定し、reservationは`not_required`です。分離が未確認ならこの扱いにしません。
2. 選定済み外部providerで取得したreservationのrefとrevisionを、元providerの保存状態から独立に取得して照合します。現時点で共通helperの`reserve_shared_resource(external_reservation=..., external_reservation_acquired=True, external_reservation_revision=...)`は、その文字列だけでは所有者を証明できないため`external_reservation_readback_required`でblockします。返したref／revisionは検証待ちの情報であり、`reserved`やresource使用許可ではありません。正式なproviderの取得・readback・認可・cleanupは各ownerの実装に残します。
3. provider未選定で`reserve_shared_resource(..., native_atomic_conditional_release=True)`を呼んでも`reservation_provider_not_selected`で停止します。SQLiteや旧JSONへ自動的に予約を作成しません。既存の予約ファイルやDBを削除・自動移行しません。
4. `release_shared_resource()`はowner／cleanup／revisionの基本条件を確認する判定helperであり、外部providerでの原子的解放ではありません。確認フラグだけで実解放を許可せず、未接続の場合は`reservation_release_provider_not_connected`を返します。実行ownerが保存した元結果とcleanupを独立取得したうえで、選定したproviderの条件付き解放・再読込を実施してください。その経路がない場合はresourceを使用せず`blocked`にします。

### current完了直前 / current成果物再利用直前

利用したProject Context stable keyとsource dependency revisionを、`compare_used_context`を含む既存currentness契約で再確認します。変更・欠落・曖昧さ・helper failureをLLMで補わず、影響範囲を`unresolved` / `blocked` / `要再検証`へ戻します。

## 開始点

要求成果物を作るために必要な、最も早い担当Skillから開始します。

例:

- 仕様整理だけ → `spec-analysis`
- 有効な仕様分析がありテスト重点を決める → `test-analysis`
- 有効なテスト条件 / カバレッジ項目がありケースだけ作る → `test-case-design`
- 成果物チェーンの抜け・閉鎖性を見る → `coverage-analysis`
- 成果物を重大度付きで独立レビューする → `adversarial-review`
- 新規案件・成果物配置の変更 → `project-context`
- PR / merge / release / 資料改版から機能IDと変更分類を更新する → `feature-analysis`
- QA活動の目的・品質目標を定める → `test-requirements-analysis`。有効なQA要求があり方式だけ決める → `test-architecture-design`。有効な要求・方式があり計画・進捗だけ扱う → `test-management`
- E2E自動化対象を選ぶ → `e2e-test-selection`
- FAIL / Finding / Observationから欠陥候補・外部Issue引継ぎを扱う → `defect-management`
- 確定済みの複数方式の結果を計画母集団に照らして横断報告する → `test-reporting`。E2E結果だけの人間向け報告は`e2e-test-reporting`
- QA活動を評価し改善の効果を確認する → `test-evaluation`

常に`spec-analysis`から開始しません。

## 既存成果物の再利用

既存成果物は次を軽量確認して再利用します。

1. 現在の対象範囲に適合する
2. 関連上流成果物に対して陳腐化していない
3. 担当Skillの意味上の出力契約を満たす
4. 後続判断に必要な追跡情報がある
5. `要再検証` / ブロック中のまま利用可能扱いされていない

工程固有の妥当性が疑わしい場合は、詳細規則を`qa-workflow`で再評価せず担当Skillへ戻します。

### 開始時の既存成果物確認と再開

依頼を受けたら、担当Skillへ進む前に次を順に行います。

1. 既存のworkflow stateと成果物の置き場（保存先、`qa-state/`など）を最初に読みます。何も無いときだけ新規に開始します。
2. 入力revisionの比較には`scripts/input_revision.py`を使います。`python3 <Skill>/scripts/input_revision.py compare --root <入力のroot> --state <保存先>/input-revisions.json <対象path...>`で比べ、helperが使える場合は自前の補助scriptを書きません。`record`の`--state`は`input-revisions.json`という名前で、保存先（`qa-state/`など）の中に置きます。保存先の外へファイルを書きません。
3. `status`が`same`なら、保存済み成果物を**再利用**し、再生成しません。stateへ「再利用（入力revision同一）」と今回の確認を記録して終えます。
4. `changed`・`added`・`removed`なら、そのpathに依存する成果物だけを`要再検証`にして再実行し、他は再利用します。再利用と再実行の別をstateへ記録し、実行後に`input_revision.py record`で記録を更新します。`no_record`なら新規として扱い、完了後に`record`で記録します。
5. 前回が途中で中断していれば、stateが示す最後に完了した工程の次から再開し、完了済みの工程を最初からやり直しません。中断した事実、再開した工程、引き継いだ成果物をstateへ記録します。

## 既定フロー

```text
spec-analysis
  ↓
question-analysis
  ↓
test-analysis
  ↓
test-requirement-design
  ↓
test-condition-design
  ↓
test-case-design
  ↓
coverage-analysis
  ↓
adversarial-review
```

これは依存関係を理解するための既定経路です。要求成果物と有効な既存成果物に応じて途中から開始・終了できます。

## 進行モード

### `continuous`

既定モード。現在Skillの成果物が次工程へ利用可能で、局所ブロッカーがなければ要求成果物まで継続します。非ブロッカーは可視化したまま進めます。

### `gated`

ユーザーまたは案件コンテキストが指定した場合に使用します。現在Skillの成果物を提示した時点で停止し、次Skillを自動実行しません。

優先順位:

1. ユーザーの明示指示
2. 案件コンテキスト
3. `continuous`

## 不明点・矛盾のルーティング

どの工程でも、下流成果物の妥当性を阻害する未解決事項を発見した場合は`question-analysis`へ送れます。

分類自体は`question-analysis`を正本とし、`qa-workflow`は返されたブロック中範囲、継続可否、再開先をワークフロー状態へ反映します。

一部範囲だけがブロック中なら、妥当性を維持できる他範囲は継続します。

## 修正ルーティング

カバレッジ分析 / 反証レビュー等で欠陥を見つけた場合は、最も早い責任Skillへ戻します。

- 仕様モデル / 現在有効な仕様根拠 → `spec-analysis`
- 不明点 / 仮定 / 期待結果の根拠不明 → `question-analysis`
- プロダクトリスク / テスト重点 → `test-analysis`
- テスト要求 → `test-requirement-design`
- テスト条件 / カバレッジ基準 / カバレッジ項目 → `test-condition-design`
- テストケース → `test-case-design`
- カバレッジ判定自体 → `coverage-analysis`
- E2E対象選定の価値判断 → `e2e-test-selection`。旧`test-analysis`成果物のE2E選定表は既存記録として`test-analysis`（対象: `E2E対象選定`）で読み取り、新規選定には使わない
- currentな実対象UI情報・テスト対象資料の鮮度 → `test-target-inspection`
- E2E対象選定後のrepo構造、Playwright設定、実装可能性、安全条件 → `e2e-test-inspection`
- Playwright E2E実装 → `e2e-test-implementation`
- E2E実装レビュー → `adversarial-review`（対象: `E2E実装`）
- TC → E2E実装追跡 → `coverage-analysis`（対象: `TC → E2E実装`）
- 詳細TCの今回run条件、preflight、実行不足、TC後処理 / cleanup → `test-execution`
- 既存repo Playwright E2Eのrunner実行条件、状態準備、cleanup → `e2e-test-execution`
- E2E実行結果の原因分析 / 証拠不足 → `e2e-test-result-analysis`
- 確定済み結果の報告 → `e2e-test-reporting`
- QA目的・品質目標・合意状態 → `test-requirements-analysis`
- テストレベル・タイプ・方式・環境・データの割当 → `test-architecture-design`
- 計画・開始 / 終了基準・予定母集団・差異・プロジェクトリスク・是正処置 → `test-management`
- 欠陥候補の成熟度・外部Issue照合・修正確認依頼 → `defect-management`。再実行・判定は元の実行Skillへ戻す
- 複数方式の横断集計・取得完全性 → `test-reporting`。元結果の再判定はしない
- QA活動の評価・改善の採用 / 効果測定 → `test-evaluation`。採用された改善の正本改版は各正本ownerへ戻す
- 機能ID・情報源母集団・開発差分分類 → `feature-analysis`
- Project Contextの配置・編集方針・stable key → `project-context`

レビューSkill自身や`qa-workflow`が担当層を直接再設計しません。

## 上流変更の伝播

上流成果物の意味が変わった場合は、影響する下流成果物を`要再検証`として扱います。

1. 変更した最も早い成果物を特定する
2. 直接・間接に依存する下流の影響範囲を特定する
3. 影響範囲だけを担当Skillへ戻す
4. 担当Skillで再検証・必要修正する
5. カバレッジ確認が要求される場合は`coverage-analysis`を再実行する
6. 独立レビューが要求される場合は意味が変わった範囲を`adversarial-review`で再確認する

無関係な下流成果物まで全再生成しません。

## WCAG observation handoff

`wcag-conformance-evaluation` がformal sample / criterion / procedureに必要なlive browser evidenceを要求した場合、persistent handoffとresumeをこのSkillが所有します。formal Skillから `usability-inspection` のscriptやassetをimport / 実行せず、inspectionへtyped required scopeを渡してください。Browser/session ownerは `usability-inspection` です。同じsessionの操作を並行させません。

`state.handoffs` は既存 `workflow_ref / schema_version / state` envelopeに追加するpayloadだけです。既存の `artifact_graph.py` のworkflow identity、claim、reservation、CAS helperを利用します。production local filesystemのexact-content revisionはCAS tokenではありません。storageがnative atomic conditional write/releaseを提供しない場合はbrowserを開始せずblockedにします。canonical repository E2EのSQLite CAS providerはtest専用です。

handoff identityはorigin artifact/revisionとartifact-local handoff refの組です。`operation_ref`、expected observation集合、current result集合、lineage、close readinessはhelperが導出します。開始順はpending CAS → mutable-operation claim → canonical順resource reserve → in-progress CAS → browser開始です。owner resultはimmutable evidence refとcleanup状態を持ち、read-onlyに返します。started operationを同じidentityでbrowser再実行しません。再観測時はformal ownerが新handoff refと`retry_of_handoff_ref`をmaterializeします。

結果をresumeへ返す前に、origin currentness、expected/returned集合、duplicateまたはsupersedes lineage、cleanup、reservation releaseを確認し、close-ready → closed CAS → state reread → resume decisionの順を守ります。release/CAS失敗や不一致はblockedへ閉じ、再browser実行で隠しません。開始前failureでもownerの実行・cleanupと条件付きclaim解放の経路が未接続なら`claim_release_provider_not_connected`をexpected safe blockとして保持します。

## ワークフロー全体状態

- `完了`: 対象スコープ内にブロック中と`要再検証`が残らず、要求成果物の完了条件を満たす
- `部分完了（ブロック中あり）`: ブロック中以外は完了しているが、対象スコープ内に局所ブロック中が残る
- `ブロック中`: ブロック中により要求成果物について意味のある完了範囲を確定できない

## 全体ワークフロー完了条件

要求された成果物 / workflowについて次を満たしたとき`完了`です。

- 要求された成果物 / workflowの担当Skillが、自身の完了条件を満たしている
- 対象scopeに未解決の`ブロック中` / `要再検証`が残っていない
- 必要な追跡性が閉じている
- 必要なcurrentness確認が完了している
- 実操作を含む場合、必要なcleanupとunresolved stateが閉じている

要求内容に応じて、次の条件を追加します。

- 新規・改修のテスト設計を要求する場合だけ、必要な仕様根拠、Risk、TR、TCN、TC、coverage等の契約を確認します。
- E2Eを要求する場合だけ、必要なE2E実行・分析・報告・cleanup契約を確認します。primary / resolved TestCase / retry attemptも混同しません。
- Regressionは`regression-testing`、Exploration / Investigationは`exploratory-testing`、QA Knowledgeは`qa-knowledge`の完了条件に従います。各Skillのdomain完了条件を本Skillへ複製しません。

重大度の詳細条件や残存リスク受容条件は`adversarial-review`を正本とします。

## 品質ゲート

- オーケストレーション以外の工程固有ロジックを再定義していない
- 要求成果物に対して適切な開始Skillを選んでいる
- 有効な既存成果物を不要に再生成していない
- 必要Skillの欠如を別Skillで肩代わりしていない
- ブロック中を必要以上に全体へ広げていない
- 修正を最も早い責任Skillへ戻している
- 上流修正後の影響下流だけを`要再検証`している
- 完了判定が成果物の存在だけでなく状態・閉鎖性・各担当Skillの契約を見ている
- E2E固有の判断を`qa-workflow`へ複製していない

## 出力前自己検証

最終出力前に、実際に利用した入力が本Skillの入力契約を満たし、入力・仕様根拠・判断状態に停止条件へ該当する未解決状態がないか確認します。あわせて、生成したオーケストレーション成果物へ本Skillの出力契約と既存の品質ゲートを再適用します。品質基準は本ガイダンスの既存定義を正本とし、自己検証専用のルーブリックやチェックリストを別定義しません。

確認対象は開始Skill、既存成果物の再利用、ブロック中 / 再開、変更伝播、修正ルーティング、ワークフロー完了判定など、本Skillが所有するオーケストレーション契約に限ります。他Skillの工程固有ロジックを再評価・再設計しません。

1. 実際に利用した入力が入力契約を満たし、停止条件へ該当する未解決状態がないか確認する
2. 生成したオーケストレーション成果物が出力契約と既存の品質ゲートを満たしているか確認する
3. 明白かつ局所的で、新しい工程固有の判断を必要としないオーケストレーション契約違反だけを最大1回修正する
4. 修正後は修正箇所を含めて最終確認する。解消に新しい仕様根拠、上流判断、他Skillの工程固有ロジックが必要な場合は自力で補完せず、既存の停止条件・ブロック中・ルーティングに従う
5. 最終確認後も本Skill自身のオーケストレーション契約違反が残り、既存の停止条件・ブロック中・ルーティングに該当しない場合は、2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わない。現在残っている契約上の制約だけを明示する

既存の`ブロック中`定義を自己検証の未解消ローカル違反へ広げません。自己検証の実行経緯、修正回数、修正前状態、PASS / FAIL等の評価ログは通常成果物へ出力せず、現在有効な状態と未解消の契約上の制約だけを返します。
