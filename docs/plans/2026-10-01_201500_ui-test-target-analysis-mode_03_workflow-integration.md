# UIテスト対象分析モード: workflow integration

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

この文書はquestion-analysisとqa-workflowの統合契約を正本とします。

## 1. question-analysis変更

### 1.1 目的

mode packageのUNKNOWNを、回答反映のたびに再質問・再採番せず継続管理できるようにします。

既存のブロッカー / 要確認 / 仮定可能 / 提案・任意分類は変更しません。

### 1.2 SKILL.md

必要最小限の追加:

- 入力がspec-analysisのUNK-xxxを持つ場合、そのstable IDを保持する
- 回答済み論点を新しい質問IDだけで別論点化しない
- 回答反映で複数仕様fileが変わる場合でも、Authority正規化後はspec-analysisへ戻す
- versioned UI target packageの差分反映責務はspec-analysisであり、question-analysis自身がpackageを編集する責務を持たない

### 1.3 references/guidance.md

「回答の正規化」を次で補強します。

- 元UNKNOWN IDを保持する
- 暫定回答と正式回答を区別する
- 暫定回答が後で正式DECISIONへ変わっても同じUNKNOWN lineageを使う
- 「回答が不明」は回答履歴として残してもUNKNOWNは解消しない
- 正式回答で解消したUNKNOWNはcurrent unknownから除外し、spec-analysisでcurrent Authorityのstable IDを`解消先ID`へ記録する
- 解消済み事項を、根拠がcurrentな間は再質問しない
- 後続更新で`解消先ID`のAuthorityが置換・失効しても別current Authorityが同じ論点を解消している場合は、同じUNK lineageの`解消先ID`を新しいcurrent Authorityへ更新する
- 解消根拠がなくなった場合、同一論点か新しい競合かをLLMが判断する。同一論点なら同じUNK IDを`現在有効か=Yes`へ戻して再openし、新しい競合なら旧UNKNOWNをresolved historyとして維持してnew UNKを作る
- UNKNOWNのopen / resolved / reopenに伴う`現在有効か`、`解消先ID`、CHANGELOG eventの形式整合はdeterministic helperが検証し、同一論点かどうかの意味判断は行わない

### 1.4 assets/output-template.md

既存Q-xxxを廃止しません。

次の列を追加します。

- 関連UNKNOWN ID

さらに、同じquestion-analysis成果物へmachine-readableな使用済みID台帳を追加します。

```markdown
## 質問ID履歴

| ID |
| --- |
```

`不明点 / 質問一覧` はcurrent未解決質問だけを持ち、templateはheader-onlyにして `Q-001` の例示rowを実データとして残しません。`質問ID履歴` はcurrent / resolvedを問わず、その成果物系列で一度でも使用したQ IDを重複なし昇順で保持します。新規Qのsemantic identity / reuse判断はLLM、newと決めた後の番号決定と履歴union生成は `question_ids.py` が担当します。

spec-analysis由来の論点ならUNK-xxxを記録し、質問単位のQ-xxxと仕様UNKNOWNを追跡できるようにします。mode packageからquestion-analysisへ進む場合は `ui_target_package.py inspect` の `current_unknown_ids[] / resolved_unknown_ids[]` を正規handoffとし、Agentが09から集合を手作業で再構築しません。

値は空欄または1件以上の `UNK-xxx` とし、複数参照は `<br>` 区切りに固定します。QとUNKが意味的に対応するかはLLMが判断し、`question_ids.py validate-links` は形式・存在・duplicateだけを検証します。新しいUNKNOWN registryは作りません。

### 1.5 Skill-local deterministic helper

新規に `skills/question-analysis/scripts/question_ids.py` を追加します。UNKNOWN参照検証だけの別wrapperは作りません。

stdin / stdout JSON、operation名、failure、size limit、sort順等の正確なCLI契約は `_06_package-schema-and-helper-contracts.md` を正本とします。

公開operationは次の2つだけです。

- `materialize`: LLMが確定した質問semantic rowからnew Q IDを内部採番し、current `不明点 / 質問一覧` と `質問ID履歴` を同時生成する
- `validate-links`: current Q tableの `関連UNKNOWN ID` について、`UNK-xxx`形式、current known UNKNOWNへの存在参照、同一Q内duplicate、resolved-only参照を検証する

Qの次番号計算と質問ID履歴unionは `materialize` 内部関数とし、`next-id / build-history` の公開operationは作りません。QとUNKの意味的対応、質問文、回答後の正規化先、reuse / newの意味判断は行いません。Q-999使用済み時は既存3桁ID契約を勝手に拡張せず `id_space_exhausted` でblockedします。

spec-analysisからquestion-analysisへ進む順序は次に固定します。

1. repository / source更新やresolver失効をspec-analysisが先に評価する
2. LLMがsame-UNK reopenかnew UNKかを判断し、UI target packageのcanonical 09 / 07へ反映する
3. `ui_target_package.py inspect` を再実行し、更新後の `current_unknown_ids[] / resolved_unknown_ids[]` を取得する
4. question-analysisはこのcurrent UNKNOWN集合だけを使ってcurrent Qを作る

resolved-only UNKをquestion-analysisへ先に渡してからreopenする順序は禁止します。これにより `question_ids.py validate-links` のresolved-only参照拒否とsame-ID reopenを両立させます。

question-analysis成果物の更新順は次に固定します。

1. LLMがcurrentに残す質問のsemantic identityをreuse / newで判断し、質問文・分類・UNKNOWN対応等の意味fieldを `question_ids.py materialize` inputへ渡す
2. helperがprevious current Q + previous historyからreuse / new Q IDを解決し、current `不明点 / 質問一覧` と `質問ID履歴` の2 sectionをcanonical生成する
3. helper返却の `artifact_markdown` をquestion-analysis完成成果物として使用する

通常経路ではAgent / LLMがQ IDをrowへ書き込み、`<br>` escapeやID昇順、previous履歴unionを手作業で組み立てません。採番と履歴unionは`materialize`内部関数としてrepository unit testから直接検証し、focused CLI operationは追加しません。

### 1.6 deterministic eval

既存 `skills/question-analysis/evals/deterministic/validator.py` も同じ外部契約を独立に評価します。

- fixtureに `known_unknown_ids` がある場合、参照UNKNOWNがその集合に含まれること
- fixtureに `expected_related_unknowns` がある場合、Q IDごとの関連UNKNOWN集合が完全一致すること
- spec-analysis由来でない質問は関連UNKNOWN ID空欄を許可する
- 既存Q-xxx、分類、再開Skill、runtime identity等の契約は変更しない

eval validatorはproduction helperをimportしてexpectedを作りません。既存QUESTION output fixtureの少なくとも1件へUNKNOWN mappingと`質問ID履歴`を追加し、repository unit testで未知UNK / 誤mappingのfalse-pass regressionを追加します。さらに `Q-001解消 → current質問0件 → 新規質問` で `Q-002` が割り当てられ、Q-001を再利用しない回帰を追加します。deterministic output case数を増やす必要はありません。

## 2. qa-workflow変更

### 2.1 routing

次の要求をspec-analysisのUI target modeへroutingします。

- テスト設計前の対象理解を、後続工程で再利用する継続成果物として整理したい
- 複数資料からPAGE / MODAL / STATE、業務ルール、不明点を統合したい
- 既存UI target packageを更新したい
- 不明点回答をpackageへ反映したい
- 「テスト対象分析」「対象理解を固める」等が主目的で、テスト観点 / ケースへまだ進まない

単なる「Markdownで出して」という形式要求だけではmodeへrouteしません。単発要約やAuthority解消だけなら通常spec-analysisを使います。

基本経路:

spec-analysis(UI target mode)
→ `ui_target_package.py inspect` の `scope_readiness[] / ready_scope_ids[] / blocked_scope_ids[]` を確認
→ blocked scopeは `scope_readiness[].blocking_unknown_ids[]` だけをquestion-analysisへ渡す。current UNKNOWN全件をAgentがfilterしない
→ 回答正規化後、spec-analysis(UI target mode)を差分更新
→ 独立したready scopeはblocked scopeの回答待ちだけを理由に停止しない
→ ユーザー要求が仕様理解までならcurrent packageを返す
→ テスト分析も要求されている場合、`ready_scope_ids[]` が1件以上なら全件を `build-machine-evidence(scope_ids=ready_scope_ids)` へ渡し、helperが1つのcanonical batch handoffへunion / dedupeしてtest-analysisへ進む。`ready_scope_ids=[]` なら空batchを作らずtest-analysis以降をdispatchせず、workflowをblockedとして回答待ち / resume先だけ保持する

### 2.1a ready → blocked → ready の下流ライフサイクル

既にTR / TCN / model / CI / TCまで生成済みのscopeが一時的にblockedへ遷移した場合、blocked scopeに属する旧Machine Entityを通常のactive carry-forwardとして残しません。一方、semantic deletionとして `deleted` にもしません。

UI target canonical downstreamではscope ownershipを次へ固定します。

- `build-machine-evidence(scope_ids=ready_scope_ids)` はready scopeのcompact `scope_index[]` を返す
- TRDのLLMは各current TRへ `scope_refs[]` を明示する。値はcurrent ready `scope_index[].scope_id` のsubsetとし、UI target artifact workflowでは1件以上必須
- TCNは参照TR、modelは親TCN、CIは親TCN / model、TCは参照TCN / CIから `scope_refs[]` を決定論導出する。Agentが下流scopeを再判断しない
previous downstreamのidentityは既存workflow stateへ次のmachine-owned fieldを1件だけ追加して固定します。新しいregistry / handoff typeは作りません。

```json
"last_completed_qa_workflow_artifact": {
  "artifact_ref":"...",
  "artifact_revision":"...",
  "artifact_sha256":"<lowercase-64-hex>"
}
```

初回は`null`です。`workflow_ref`は既存のopaque UUIDをそのまま使い、qa-workflow runtime-v2のMachine Runtime InputとResult payloadにも保存します。qa-workflow artifactがcurrent runtime verificationを通過して保存され、保存先がexact `artifact_revision` のhistorical refetchを提供できることを既存 `artifact_graph.verify_historical_revision()` で確認した後だけ、workflow stateをCAS更新してbindingを差し替えます。blocked / unresolved runでは差し替えません。

処理順を次に固定します。

1. `ui_target_package.py inspect` からcurrent `ready_scope_ids[] / blocked_scope_ids[]` を取得する
2. `ready_scope_ids=[]` なら `build-machine-evidence(scope_ids=[])` を呼ばず、test-analysis / TRD / TCD / TC / coverage-analysis / qa-workflow runtimeをdispatchしない。workflow stateはblockedを保持し、`last_completed_qa_workflow_artifact` は更新しない
3. ready scopeが1件以上あり、workflow stateの `last_completed_qa_workflow_artifact` がnon-nullなら、qa-workflowは保存された `artifact_ref / artifact_revision` を使ってexact historical revisionをrefetchする。providerがhistorical refetchを提供しない、refetch不能、raw Markdown SHA-256がstateの `artifact_sha256` と一致しない場合はfail-closedする
4. qa-workflowはcurrent `workflow_ref`、current workflow state record、`blocked_scope_ids[]`、refetch済みprevious qa-workflow Markdownを `skills/qa-workflow/scripts/downstream_state.py` へ渡す。state bindingがnullならMarkdownもnullだけを許可し、bindingがnon-nullならMarkdown必須とする
5. `downstream_state.py` はstate envelopeの `workflow_ref`、previous qa-workflow Machine Runtime Input内の `workflow_ref`、current `workflow_ref` のexact一致を要求する。別workflow artifact、1世代古いartifact、binding不一致、previousありなのにnullをrejectする
6. helperはqa-workflow root pairを**historical integrity用のfrozen runtime-v2規則**で検証する。保存Input / Result schema、pair identity、input / model / generation fingerprint、dependency、Machine Entity content fingerprint、保存済み `current_runtime_units[]` と `workflow_scopes[].current_structure_state` の自己整合を検証するが、保存された `runtime_implementation_fingerprint / generator_implementation_fingerprint` と現在disk上の実装fingerprint一致は要求しない。historical integrity PASSをcurrent / freshとは扱わない
7. helperが検証済みInputからprevious current TR / TCN / model / CI / TC EntityとTRD / TCD / TCのprevious `current_structure_state` を内部抽出し、Entityの `content.scope_refs[]` とblocked Scope ID集合の積集合だけで `active → inactive` 対象を決める。Authority共有、名称、同一PAGE、runtime dependency等からscope所属を推測しない
8. helperは `inactive_tr_ids[] / inactive_tcn_ids[] / inactive_model_keys[] / inactive_ci_ids[] / inactive_tc_ids[]` に加え、各root runtimeへ保存するmachine-owned `inactive_tr_history[] / inactive_tcn_history[] / inactive_model_history[] / inactive_materialize_history[] / inactive_tc_history[]` をcanonical sortして返す。Agent / LLMはprevious snapshot、ID集合、historyを手作業でfilter / 復元しない
9. TRD / TCD / TCのv2 generatorとTCD current structure stateは該当IDを `active → inactive` へ遷移させ、inactive IDをcurrent Machine Entity / current runtime unit / carry-forward projectionへ含めない。同時に各root payloadへlast-active Entity historyを保存し、TCDはlast successful materializeのCI ID / target mapping / semantic mapping / expected-result-root stateも履歴化する
10. ready scope全件は1 batchでtest-analysis → TRD → TCD → TC → coverage-analysis → qa-workflowへ進める。current qa-workflow artifactがcomplete / currentとして保存された時だけ上記bindingを更新する。inactive履歴そのものをfreshness blocking issueにしない
11. blocked scopeが再びreadyになった場合、inactive IDとmachine-owned last-active historyを再利用候補として保持する。LLMはTR / TCN / model / TCのhistoryをsemantic identity比較に使い、同一なら既存IDをreuseして `active` へ戻す。CIは`inactive_materialize_history[]`からprevious mapping inputを決定論的に復元して同じIDをreuseする。意味が変わった場合は旧inactive IDを `deleted` にしてnew IDを発行する
12. `deleted` はterminalであり、block解除を理由に復帰させない

`scope_refs[]` がready / blocked双方を含むcross-scope Entityは、1つのcurrent Entityをscopeごとに部分利用できないため保守的にinactive対象とします。ready側だけで成立する別identityへ分割する必要があるかはLLMが意味判断し、helperが旧Entityの内容やscope_refsを自動縮退させません。

全scopeがblockedの期間は新しいdownstream runtime artifactを作らないため、その期間の一時状態を別snapshotへ永続化しません。後で1件以上のscopeがreadyへ戻った最初のdownstream runで、変更されていない `last_completed_qa_workflow_artifact` とその時点のcurrent `blocked_scope_ids[]` からinactive集合を再導出します。

v1 cutover直後のdownstreamにはUI target Scope IDが存在しないため `scope_refs=[]` です。UI target package migration時点で既存active downstreamが1件以上あり、そのscope ownershipが未確立なら、最初のownership normalizationは **全current scopeがreadyの時だけ** 実行します。全scopeを `scope_index[]` に含めたTRD→TCD→TC更新で既存active downstream全件へ `scope_refs[]` を付与し、coverage-analysis / qa-workflowまでcurrentにした後でpartial readinessを有効にします。ownership baseline前に1件でもblocked scopeがある場合は `scope_ownership_baseline_required` でfail-closedし、ready scopeだけへ旧IDを推測割当しません。downstream未作成の新規UI target workflowはこのone-time migration gateを通さず、最初からready scopeだけでpartial progressionできます。

### 2.2 gated mode

ユーザーが「1手順ずつ」「理解を確認してから」「ファイル出力前に確認」等を指定した場合、既存gated modeを使います。

mode固有の新しいmodeは作りません。

### 2.3 test-target-inspection routing

次の場合だけtest-target-inspectionへ進めます。

- currentな実画面の表示名 / 到達可否が必要
- 仕様資料だけでは現在UI状態を判断できない
- userが実画面のcurrent観測を要求
- repository情報ではなく実対象の観測が必要

repositoryを読むだけの調査をtest-target-inspectionと呼びません。

### 2.4 repository調査

repository事実が必要で、AIエージェントがrepositoryを利用できる場合は補助入力として収集できます。

ただし:

- repo factはAuthorityではない
- spec-analysis packageの08へ分離
- 実装差分はquestion-analysisへ不要な仕様質問として戻さない
- Authority上の期待挙動が明確なら差分として記録する

特定のrepository接続方式、connector、tool名はSkill契約へ固定しません。

### 2.5 routing fixture

PR #14後の61 routing fixtureをbaselineとして、次の2ファイルを必ず同時に更新します。

- `skills/qa-workflow/evals/deterministic/routing_cases.json`
- `skills/qa-workflow/evals/deterministic/routing_candidate_outputs.json`

expected routingからcandidate outputを自動生成せず、既存契約どおり独立fixtureとして保持します。

次の8 caseを追加します。

1. 「小規模でも今後のテスト設計で継続利用する対象理解を整理」→ spec-analysis UIテスト対象分析モード。単一表に収まる規模でも継続利用目的を優先する
2. 「既存仕様理解packageへ不明点回答を反映」→ question-analysis解消後spec-analysis mode resume
3. 「current実画面を見て対象資料を更新」→ test-target-inspection
4. 「仕様書とrepoを比較して期待仕様を整理」→ spec-analysis mode。repo差分をAuthority化しない
5. 「仕様理解だけで止めたい」→ test-analysisへ自動進行しない
6. 「保存済みFigma / screenshotをUI/UX観点で評価」→ usability-evaluation
7. 「live browserで使いやすさ / focus / responsiveを検査」→ usability-inspection
8. 「WCAG 2.x / level指定でformal適合性評価」→ wcag-conformance-evaluation

routing fixtureはPR #14後の61件から8件追加して69件になる想定です。ready / blocked scopeの部分進行はrouting caseのexpected metadataでも固定し、current UNKNOWNが存在するだけで全scopeを停止するcandidateを不正とします。実装開始時にStep 0で現在値を再確認し、追加数が変わらなければEVALS.md / docs/PROJECT_CONTEXT.md / routing件数を保持するrepository contractを69へ同期します。READMEにrouting件数を持つ場合のみ同様に更新します。

### 2.6 DEC / ASMの正本ownerとdefault Project Context採番

question-analysisが回答を正式 `DECISION` または承認済み `ASM` へ正規化する場合、ID ownerは案件で実際に指定されている決定事項 / 仮定の正本です。UI target package側では採番しません。

Project ContextのSection 12 / 13が正本ownerであるdefault経路では、新規 `skills/qa-workflow/scripts/project_context_ids.py` を使います。

- `## 12. 確定事項（決定事項の正本一覧）` → `DEC-xxx`
- `## 13. 仮定（仮定の正本一覧）` → `ASM-xxx`

LLMは回答の意味、DECISION / ASMの区別、既存identityのreuse / new、決定内容、関係、影響範囲、ASM承認可否を判断します。Project Contextがownerの場合、newと判断した後の番号だけhelperがprevious + candidate Project Contextの全状態rowから既知最大番号+1で返します。撤回 / 置換済みrowも使用済みID履歴として残し、番号再利用を許可しません。

案件で別の決定事項 / 仮定の正本一覧が明示されている場合はそのownerを維持し、Project Contextへ複製・再採番しません。owner側にdeterministic ID allocatorがあればそれを使い、ownerがIDを確定できない状態ではLLMが番号を推測せず正本登録をblockedとして扱います。任意schema向けgeneric allocatorは追加しません。

`skills/qa-workflow/assets/project-context-template.md` を正本ownerとして使う場合、Section 12 / 13はheader-onlyへ変更し、現在の `DEC-001` / `ASM-001` 例示rowを実データとして残しません。

Project Context ownerの更新では、LLM / stakeholderがreuse / new、決定内容、状態遷移等の意味fieldを `project_context_ids.py materialize` へ渡します。helperがprevious + candidate全状態rowからnew IDを内部採番し、previous IDを保持したSection 12 / 13をcanonical生成します。`validate-history` は既存Project Contextの履歴整合を独立確認するproduction validationとして残します。採番だけの`next-id` operationは追加しません。row順、決定内容、状態遷移の意味はhelperで判断しません。

exact CLI契約は `_06_package-schema-and-helper-contracts.md` を正本とします。

### 2.6a runtime-v1 downstreamが残る場合の順序

既存workflowにruntime-v1のdownstream artifactが存在する場合、UI target packageへのmigrationを先に行いません。依存グラフ順を次に固定します。

1. runtime-v1 downstreamを検出したら通常semantic update / partial rerunへ入らない
2. spec-analysisは `_09` のfrozen v1 Authority projectionでcurrent v2 Authority Entityを再生成する。canonical v1 Authority blockが使えない場合は通常spec-analysis semantic rerunでcurrent baselineを作る
3. test-analysisは保存v1 inputのintegrity + current v2 Authority整合を確認してdependent runtime → rootをfull rerunする。保存inputを使えない場合は通常test-analysis rerunへ戻る
4. `_09` のSkill-local cutover helperでTRD → TCD → TCをsemantic不変のままruntime-v2 / entity-state-v2へfull rebuildする
5. coverage-analysisをcurrent v2 TR / TCN / CI / TC / runtime evidenceからfull rerunする
6. workflowで必要なusability-inspection / wcag-conformance-evaluationを各Skillのintegrity + currentness契約に従ってv2再生成し、必要な再観測を完了する
7. qa-workflowを最後にcurrent v2 Entity / runtime evidenceから再生成し、v2 baselineのvalidate / freshness / final gateを成立させる
8. v2 baseline成立後に既存spec-analysis成果物をUI target packageへmigrationしてACを生成し、requirement-structure-v2を通常semantic updateとして再実行する
9. AC / Authority変更でstaleになったTCD → TC → coverage-analysis → qa-workflow等を通常の依存順で再実行する

`UI target migration済み + runtime-v1 downstreamあり + v2 baseline未成立` の組合せはblockedです。新しいqa-workflow専用wrapperは作らず、既存routing / runtime evidence version確認でこの順序を守ります。既存v1 downstream artifactがない場合は、直接UI target package migrationへ進めます。

### 2.7 downstream machine handoff

UI target modeから後続テスト設計へ進む場合、spec-analysis成果物のMachine Entity / normalized inputをAgentがMarkdownから再構築しません。

`ui_target_package.py build-machine-evidence(scope_ids=null)` が返すpackage-global evidenceはcanonical package自身のMachine Entity section検証に使い、ready scopeのfull handoffを重複して含めません。下流canonical pathでは `inspect.ready_scope_ids[]` 全件を `scope_ids[]` として1回渡し、helperがscopeごとの `_06 §9.3` reachabilityを内部適用した後、1つのbatchへ統合します。

batch handoffは次を持ちます。

- `scope_ids[]`: current `ready_scope_ids[]` とexact一致するcanonical sort済み集合
- ready scope unionのspec-analysis canonical `normalized_skill_input`
- ready scope unionのAuthority / current Acceptance Criterion Machine Entities
- union / dedupe済みexpected entity identities

helperはAuthority / AC / Machine Entityをstable identityでdedupeし、共有Authorityを1件へ統合します。同一identityのcanonical contentがscope間で不一致ならfail-closedします。Agent / LLMがscope別payloadをmergeしません。blocked scope由来のAuthority / ACはbatchへ含めません。scope所属row・明示stable ref・UI構造parentだけを辿るexact reachabilityは `_06 §9.3` を正本とし、名称・同一PAGE・同一Scope・Authority本文から関連を推測しません。

既存test-analysis / test-requirement-design runtimeは `artifact:*:all` の1 runtime unitを維持します。`artifact:analysis_entities:all` と `artifact:requirement_structure:all` はready scope全件を1 requestへ集約するroot unitのため、本PRでaggregate runtimeへ分類し、各entrypointを `run_cli(..., aggregate=True)` とします。qa-workflowはbatch handoffから各root runtimeへ実際に渡すcanonical stdin JSON bytesを構成した後に16 MiB上限を事前検査し、2 MiBを超えても16 MiB以下なら1回の`:all`実行で処理します。16 MiBを超える場合はruntimeを起動せず後続を `limit_exceeded` でblockedにします。scope単位の個別run、ready scope subsetだけの`:all`実行、Agent merge、silent truncate、auto splitで回避しません。その他の通常runtime generatorは既存2 MiB上限を維持します。

ユーザー要求が仕様理解packageまでならspec-analysisの完了条件で終了し、test-analysis / test-requirement-designを起動しません。この場合、AC→TR / Disposition closureはpackage単体の完了条件ではありません。

test-requirement-designへ到達した場合は `requirement-structure-v2` を使用します。**UI target packageからのcanonical workflowは `input_mode=artifact`** とし、top-level `acceptance_criteria[]` はready scope batch handoffのcurrent AC集合をそのままTRD inputへ渡します。blocked ACはbatch / `acceptance_criteria[]` / Machine Entity集合へ含めません。AgentがMarkdownから再構築しません。artifact modeではAC Entity集合とのexact一致とAC / Authority dependencyを要求し、AC本文・親chain・linked package item変更のfreshnessを保証します。

direct modeはUI target artifactを使わない独立呼出しとして同じ `acceptance_criteria[]` schemaでknown AC集合を明示できます。各TRの意味対応だけをLLMが `acceptance_refs[]` として判断し、known ID / closureを検証します。参照AC Entityが無いdirect runではAC semantic cross-run freshnessを保証せず、存在しないMachine Entity / fingerprintを合成しません。

このhandoffの追加はrouting caseを増やしません。既存workflowの選択結果に対するmachine data受け渡し契約です。
## 3. Agent Skillsとしての利用前提

今回のmodeは既存Skillと同じAgent Skills構造で提供します。

qa-workflow経由でUI target packageをcreate / updateする場合も、write coordinationは `ui_target_package.py materialize` のpackage-local契約へ一本化します。PR #14の `claim_mutable_operation()` / `reserve_shared_resource()` / `release_shared_resource()` はこの経路で使いません。updateは `inspect → semantic quality gate → materialize(previous_snapshot=<inspect snapshot>)`、createは `semantic quality gate → materialize(previous_snapshot=null)` とし、createへ事前`inspect`を要求しません。materializeは固定sibling lock fileへprocess-scoped OS lockを取得した後、MANIFEST receiptによる同一requestの既適用判定、update snapshot照合またはcreate target不存在 / 空確認、staging / backup recovery、commitを順に行います。commit成功後にprocessが停止しても、同じrequestを再実行すればreceiptから前回の割当結果を返してmutationを再適用しません。別request / stale snapshot /一意に復旧できないfilesystem状態はfail-closedします。qa-workflowはこのpackage固有transactionを複製せず、通常のrouting / resumeで同じsemantic requestを再構成できない場合は新しい変更として黙って続行せず再分析へ戻します。

- entry pointはskills/spec-analysis/SKILL.md
- 詳細規則はreferences/ui-test-target-analysis.md
- package templateはassets/ui-test-target-analysis/
- qa-workflowは必要なSkillへroutingする
- question-analysisは回答正規化とresume情報を返し、新規Qの番号はquestion_ids.pyで決定する
- qa-workflowはProject Context Section 12 / 13が実際の正本ownerの場合だけproject_context_ids.py materializeでnew DEC / ASMの番号決定とSection 12 / 13 serializationを行い、previous ID削除をvalidate-historyで拒否する。別ownerが明示されている場合はそのownerが発行するcanonical `DEC-xxx / ASM-xxx` lifecycleを維持し、Jira / ADR等のowner固有IDをauthority_idへ流用しない

AIエージェントは利用環境で提供される通常のSkill読み込み機構に従います。

今回の実装では次を追加しません。

- 特定AI製品向けbootstrap
- GitHub connector固有手順
- remote Skill loader
- 新しいSkill-to-Skill API
- 全22 Skillを一括読み込みするruntime

## 4. PR #14成果物のAuthority扱い

usability-evaluation finding、usability-inspection observation / measurement、wcag-conformance-evaluation result / report / EARLは、そのままSPEC / DECISION / approved ASMへ昇格しません。

- 既存Authorityとの一致 / 差分を対象理解packageへ補助evidenceとして記録できる
- 仕様変更が必要ならquestion-analysis / stakeholder decisionへ送る
- project contextでformal WCAG requirement自体がAuthorityとして明示されている場合はrequirementをAuthorityとして扱えるが、評価結果そのものは仕様へ自動変換しない

## 5. README更新

READMEへ、UIテスト対象分析modeがspec-analysisの条件付きmodeであることと、詳細契約の参照先を簡潔に追記します。通常spec-analysisを置換しないことも明記します。

特定AI製品の利用手順は追加しません。

## 6. 変更しないもの

- qa-workflowのPR #14後22 Skill前提
- skill-to-skill API不存在の説明
- question-analysisの分類4種
- DECISION / ASMの意味判断と、案件で明示された決定事項 / 仮定の正本owner
- test-target-inspectionのlive target currentness契約
- runtime / artifact graph
- qa-knowledge lifecycle
- Regression / Exploration routing
- E2E Skill群

## 7. 完了条件

- mode requestがspec-analysisへrouteされる
- 不明点回答後に同じUNKNOWN lineageでspec-analysisへ戻り、question-analysisの関連UNKNOWN IDはSkill-local helperと独立deterministic evalの双方で構造検証される
- new Q / DEC / ASMのsemantic identityはLLMが判断する。Q番号はquestion-analysis helper、Project ContextがDEC / ASM ownerの場合はqa-workflow helper、別ownerの場合はそのownerのdeterministic allocatorで番号を決定し、owner未採番時にLLM hand-numberingへfallbackしない
- 仕様理解だけの要求でtest-analysisへ勝手に進まず、AC→TR / Disposition closureをpackage単体の完了条件にしない
- current UIの対象情報観測要求だけtest-target-inspectionへ分岐する
- 保存済みUI資料のUX評価はusability-evaluation、live usability検査はusability-inspection、formal WCAG適合性評価はwcag-conformance-evaluationへ分岐する
- modeが既存Agent Skills構造でAIエージェントから利用できる
- 特定AI製品向けintegrationを追加していない
