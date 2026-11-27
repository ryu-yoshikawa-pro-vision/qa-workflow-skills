# QAワークフロー運用上の改善候補

基準: main 003bbc7a32bf5b4605696564a9254dd5053ccf5f（2026-11-27、PR #40統合後）。旧baselineの全37 Skillと追加2 Skill、主要reference・runtime、[PR #22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md)を静的に照合した。以下は合意済みの改善方針と残存する改善・受入候補であり、実装指示・承認済みPlan・現行契約の変更ではない。優先度は暫定（P0: 安全・誤完了、P1: 継続性・運用負担、P2: 接続・効率）。案件別保存先という設計自体は欠陥ではない。新Skill・中央台帳・汎用storage frameworkは前提としない。

## 確定前提と適用範囲

[共通原則](../reference/qa-skill-design-principles.md)（PRN-01〜09、Q01〜12）が設計の正本。利用者合意済みであり、再承認不要。OPS-18を先に適用し、Skill・Runtime・validator・Helper・呼出し側の不要な責務・過剰防衛を削減する。以下の「現状」は統合後の実装・制約と調査結果、「改善」「受入」は達成すべき目的と残る対応である。現行の未改修契約を文書だけで解消したことにしない。PR #40統合後の実装証拠に基づき、対応済みの再実装や不要になった受入を除く。PRN-09に従い関連コード・Skill・文書・テスト・設定を同期する。QA活動の基本原則と専門QA判断の改善候補も参照する。

追加調査（2026-11-26）: mainの全37 SKILL.md、主要Runtime・Helperの関数・完了条件、[PR #40](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/40)の追加2 Skill・保存/再開コード・検証記録（調査時点968629b、4eebeab）を照合した。全呼出し元・全reference・schema・評価fixture・実Agent比較は未確認。2026-11-27のPR #40統合後はmain 003bbc7a32bf5b4605696564a9254dd5053ccf5fを基準に、追加2 Skill・owner登録・保存/再開・要求scope契約を再照合した。最終head 58fed44の5 CI成功、runtime 1,516 tests PASSは[検証記録](../implementation/pr40/verification.md)とPR本文の報告であり、実Agent縦断・正式trigger・独立Semantic Judge・実運用root/共有writer・既存owner横断一意性・3構成比較は未完了。全18 OPSの目的を維持して再評価した。明確な契約差は改修し、既存経路の受入・実測が主目的のものは利用結果に基づいて必要な修正を行う。実装済み部分は再実装しない。具体的な変更方法は後続Planで確定する。

## A. 質問・承認・checkpoint

### OPS-01 質問前後と工程引継ぎの永続化 (P1)

対象: qa-workflow、question-analysis、agent-answer-form、各設計owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)はstate・再利用・再開を、[question guidance](../../skills/question-analysis/references/guidance.md)はQ ID・回答正規化を規定する。#40は横断分析の開始要求・attempt・run・handoffの再開を実装済み。通常QA工程の質問提示直後・回答反映後・工程間の自動保存と回答種別ごとの正式反映には残存差分がある。

改善: Q09で成果物作成依頼を原則保存対象とし、明示の非保存指示を優先する。Q02の5契機（処理完了、質問前、回答反映後、中断、引継ぎ前）で必要な成果物だけ自動保存する。通常QAの保存・質問・回答・再開契約を改修し、#40の専用runを一般の質問に強制しない。Q ID、根拠、停止scope、再開先、完了成果物参照は既存成果物から取得できるものを重複保存しない。専用stateは必要情報が復元できない場合だけ利用する。単発相談・レビュー・調査は原則対話回答。再利用価値のある知識のみ、許可済み保存先に自律保存する。明示非保存・無効指定と機密保護を尊重し、任意蓄積のために通常回答を止めない。保存時点はQ02に従う。Q ID・元質問定義・根拠・回答の対応を保持し、保存不能でも質問・候補・安全な再開情報を返す。未承認変更は承認済み内容と区別する（OPS-02）。

受入: 質問提示直後の中断・別session再開、部分回答・保留、保存未設定/失敗、source改版を試験し、解決済み論点・完了済み工程の反復と未保存の成功表示を防ぐ。仕様回答と実行条件・操作許可への回答を区別し、不要なDEC/ASM発行、他ownerの無断更新、利用者への形式検証要求を防ぐ。改版前の質問と回答の照合、旧フォームからの未回収回答の復元、保存不能時の復元範囲の明示を確認する。

具体的な確認箇所: [question-analysis guidance](../../skills/question-analysis/references/guidance.md)の回答正規化（期待挙動のSPEC/DEC/ASM）と再開先判断を照合する。製品仕様への回答は権威ある仕様・正式決定・承認済み仮定として扱い、実行URL、データ準備、保存先、操作許可、QA計画・方式等の回答は意味に応じて担当ownerの成果物または必要な実行条件へ反映する。全回答にDEC/ASMを発行せず、question-analysisは分類・回答の意味・反映先・再開先を判断し、正式反映は担当owner、工程再開はqa-workflowが担当する。agent-answer-formは質問JSON・HTML・回答Markdownの対応、Agent/Helperは採番・形式・回答照合を担当し、利用者には判断と回答だけを求める。Q IDを維持し、同じ質問本文や承認状態をworkflow stateへ重複記録する必要性を評価する。回答前の中断、部分回答、質問の意味変更、保存失敗から再開できる最小限の情報を残す。フォーム生成Skillに質問採否・仕様判断・進行制御を追加しない。PR #40のhandoff intentや試行stateとの接続はOPS-06/18で確認し、質問を対話提示するだけの操作に外部副作用用の永続化を強制しない。

### OPS-02 承認要求の集約と進行許可の分離 (P1)

対象: qa-workflow、project-context、question-analysis、計画・保存・実行owner。

現状: continuous/gated、開発連動QA Planの旧Q06配置合意、Git既定承認方式は既存。複数成果物の提示単位・部分承認の横断保証は未確認。#40の通常保存は都度承認不要だが、既存ownerの保存承認と案件コンテキストによるgated指定は残る。

改善: 許可済み通常保存は都度承認なしとする。候補・回答の記録と内容の正式承認、工程進行、操作認可、破壊的変更を区別する。正式決定・仮定採用・承認済み仕様の意味変更・必要な外部操作は既存の有効な承認単位でまとめる。利用者の指定・既存規則を優先し、指定がなければ標準契約で進行する。必要時は保存先・形式・運用上の指定の有無だけ確認し、既知の条件を再質問しない。既存の候補欄・文書構造を優先し、別draftや承認状態管理を一律新設しない。計画等の正式確定・リスク受容が必要な場合は維持する。Q10に従い通常の内容承認は依頼者の明示判断で成立する。Q11のcontinuousを既定としgatedは明示指定時のみ。案件単位の進行設定を要求しない。必要な内容承認・操作認可では対象scope/ref/revision・差分・権限・失効条件を確認する（OPS-04）。

受入: 許可済み通常保存が承認待ちで停止しない、承認済み仕様と未承認変更候補が混在しても前者の意味を保全し後者を正式採用しない、通常の明示承認は追加認証なしで採用、別権限者が必要な判断・外部操作では必要な確認を維持。既定continuousと明示gated、必要承認の拒否・保留・有効性に影響する変更を確認する。

具体的な確認箇所: [qa-workflow guidance](../../skills/qa-workflow/references/guidance.md)の進行モード優先順位は利用者の明示指定、案件コンテキスト、continuousであり、[Project Context template](../../skills/qa-workflow/assets/project-context-template.md) Section 10にも設定がある。Q11への変更では両方と関連fixtureを同期し、明示gatedの停止境界、必要な仕様質問・内容承認・操作許可は維持する。案件設定の廃止を理由に既存の承認済み内容や履歴を削除しない。

## B. 保存・承認・完了証拠

### OPS-03 必要な保存・更新保証の適正化 (P0)

対象: project-context、feature-analysis、test-item-analysis、test-condition-analysis、計画3 Skill、ui-target-analysis、qa-workflow。

現状: [project-context](../../skills/project-context/SKILL.md)には明示選択local/Git provider、候補ownerにはwrite preconditionがあり、計画3 Skillには正式保存・承認providerへの依存が残る。#40の3 kindの通常保存・履歴・条件付き更新は局所実装・検証済み。

改善: 利用者の指定・既存契約を優先し、指定がなければ許可済み作業先と標準契約を利用する。保存技術は内部処理として扱い、利用者には技術方式の選択を求めず、判断・操作が必要な不足だけ説明する。既存ファイル操作・Helperを優先し、通常の単独保存は結果確認、更新は対象・必要内容の保全を基本とする。共有更新・履歴再取得・後続の正本検証・外部操作に実際に必要な場合だけ条件付き保存、一意性、revision/hash、独立readback等を要求する。必要な能力不足は該当操作のみblockし、汎用保存層や全owner接続を目標にしない。保存・内容承認・currentnessは分離し、保存状態は[共通運用契約](../reference/qa-workflow-operating-contract.md)に従う。結果不明時は実保存先を照合する。依存する複数成果物の部分保存は必要な参照と内容/revisionを確認し、成立まで該当下流の採用を保留する。個別CASを一括整合とせず、無断rollback・別正本作成を避ける。過去対象外は自動解除しない。

受入: 単独新規/更新の保存・失敗時報告・承認済み内容の保全。実共有更新が必要な経路では同一revisionの競合、create-if-absent、結果不明、必要履歴とreadbackを確認する。外部操作は必要権限・失効・再実行防止を確認。fixtureだけで未検証の遠隔先を保証しない。依存する部分保存と結果不明からの再開を確認する。

具体的な確認箇所: project-contextの[artifact_store.py](../../skills/project-context/scripts/artifact_store.py)（SQLite・認可・履歴・条件付き更新）、[git_artifact_store.py](../../skills/project-context/scripts/git_artifact_store.py)（Git正本・commit SHA条件付き更新・認可）、feature-analysisのpersist_snapshot、test-item-analysis / test-condition-analysisのwrite precondition、e2e-test-selectionの保存済み成果物証拠、qa-knowledgeのcreate-if-absent / CAS、regression-testingのActivity / Suite保存を確認する。これらを通常の単独保存・非破壊的更新へ一律要求する必要性を評価し、共有writer、同一identityの競合、旧revisionへの追跡、依存する複数成果物の更新で実際に必要な保証は残す。ui-target-analysisの専用writer・生成領域・履歴制約は一般文書に拡大しない。既存storeは他ownerの利用・互換性があるため、project-contextの責務削減だけを根拠にファイル全体を削除しない。

PR #40の[PR本文・検証記録への導線](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/40)では、指定rootで3 kindの通常create/read/list/history、ext4での条件付き更新、9pでの通常保存継続と条件付き更新の局所blockを報告している。専用認証hostを通常保存に要求しない方針は既に反映されているため再実装しない。共有writer・実運用rootの権限・既存ownerをまたぐ一意性・実Agent受入は別に再評価する。新しい汎用storage layerの追加は前提としない。

### OPS-04 必要な内容承認・操作認可・対象外判定 (P0)

対象: qa-workflow、project-context、計画3 Skill、defect-management、test-evaluation。

現状: [保存・承認契約](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)には対話同意・通常push・activity照合があるが、excluded_by_approvalの真正性照合が未定義。F 3 Skillのvalidatorは本人性を証明しない。

改善: Q10を適用し、通常の仕様決定・仮定採用・QA方針等は依頼者の明示回答・承認を採用する。決定内容・対象・必要な適用範囲を記録し、別権限者・組織決裁・対象外採用やリスク受容に別の承認契約がある場合・外部操作に必要な権限がある場合だけ既存経路で確認する。通常保存は許可範囲で自動化し、専用認証host・操作別承認/認可発行を一律要求しない。AIの自己申告や依頼者にない権限の推定を認可の証拠にしない。必要な承認は形式validatorや編集提出だけで成立させず、承認対象のbuild/revision・失効条件を必要範囲で扱う。

受入: 通常の明示承認で内容判断が成立し、保留・曖昧回答・AI推定は承認にならない。別権限者・組織決裁・外部操作に必要な主体・対象・有効権限を確認し、承認に影響する変更・失効・権限不明は該当判断/操作をblockする。未承認除外で完了分母を縮小しない。通常保存は個別承認不要。#40の通常保存・外部handoffの認可境界は利用し、既存ownerの内容承認と操作認可の分離・途中除外を改修する。

具体的な確認箇所: [workflow_runtime.py](../../skills/qa-workflow/scripts/workflow_runtime.py) の _exclusion_confirmed は承認照合未定義のため常にFalseを返す。これは現行の安全契約であり単純なバグではない。元依頼で最初から対象外の範囲と、必須scopeを後から除外する判断を区別し、通常のQA範囲決定は依頼者の明示判断と適用範囲の記録を利用できる契約に改める。正式品質保証範囲や組織の終了基準に影響する除外は必要な権限者・承認経路を確認する。無条件Trueや形式的なapproval_refだけでの除外は禁止する。defect-managementの外部Issue操作に必要な認可は残し、test-evaluationの改善採用・引継ぎ確認に専用認証済みサービスが必要な場合と通常の明示判断で足りる場合を区別する。計画3 Skillの内容承認と保存を分離し、承認未確定の草案を保存できるようにする。認可を要する操作まで対話回答だけで許可しない。

### OPS-05 QA品質・完了検証契約の適正化 (P0)

対象: qa-workflow/scripts/owner_verifiers.py とproject-context、feature-analysis、ui-target-analysis、defect-management、test-evaluation等。

現状: 登録済み9 Skillはtest-item-analysis、test-condition-analysis、e2e-test-selection、test-reporting、test-requirements-analysis、test-architecture-design、test-management、context-signal-audit、context-rule-synthesis。既存runtime-v2 rootは別経路。未登録scopeはunverified_scopes。計画3 Skillの実運用検証は未確認。追加2 Skillは開始時の要求・成果物root・実batch/run・owner検証と最終scopeを照合する契約を実装済み。ただし未指定時は起動しない現行契約のため、自律起動には改修が必要。

改善: owner verifier・Runtime・validator・schema・metadataを利用目的、誤りの影響、再利用・完了証拠の必要性から棚卸しする。横断分析はAgentが依頼目的・必要性から選択し、明示的な無効指定を尊重する。依頼達成に必要な分析は必須として開始前に要求を登録し、独立した補助分析は既存完了を妨げない。元依頼の必須工程と、必須成果物が依存する補助工程、依存しない独立した補助工程を区別する。独立した補助工程の未検証・保存不能はその工程の制約として報告し、必要な成果物の完了を一律に妨げない。必須成果物が利用する根拠・依存・実行安全に影響する場合は必要な検証を維持し、必須scopeを補助扱いに変更して完了分母を縮小しない。既存の意味品質・追跡性・必要検証を維持し、通常の単発分析は適切な出力検証、継続成果物や実行・正式完了の証明は必要な参照/実証を確認する。全owner登録、全成果物のcanonical JSON化、保存証拠一律要求を目標としない。不要な契約は該当Planで明示的に置換し回帰を確認する。開始/完了時の要求集合・入力母集団と証拠の対象・実行・根拠の対応を確認する。requested_scopes、workflow_ref、owner登録・保存証拠形式は現行の実現手段であり、必要な保証を保つ代替手段は対象Planで特定する。

受入: 元依頼の必須scopeと必要な意味・形式・依存検証を満たす。保存が要求されない単発分析を保存証拠不足で誤停止しない。保存・再利用・実行証明が必要な経路では改変、別scope、stale、偽証拠を拒否し、変更したruntime-v2/owner契約の回帰なし。必須工程完了・独立補助工程未検証では要求の完了と補助工程の制約を別に報告し、必須成果物が依存する補助工程の根拠不足や未解決の副作用がある場合は影響scopeを未完了とする。必須scope・入力列挙の漏れ、承認不明の除外、依存する部分保存を確認する。

具体的な確認箇所: [runtime_contract.py](../../skills/qa-workflow/scripts/runtime_contract.py)のRUNTIME_V2_SKILL_ROOTSは6 Skill、OWNER_VERIFIED_SKILLSは9 Skill（統合後の39 Skill中、残り24 Skillはこの2集合の登録外）。[owner_verifiers.py](../../skills/qa-workflow/scripts/owner_verifiers.py)のverifyと[workflow_runtime.py](../../skills/qa-workflow/scripts/workflow_runtime.py)の_buildは未登録の非runtime-v2 scopeをunverified_scopesとし、unsupported_skill_verifierをblocking issueにする。24 Skillに個別検証機能がないという意味ではなく、このRuntimeの登録区分である。現行_buildはunrequested_scopesを識別してもscopes全体を検証し、未登録・検証失敗をblocking issueとするため、独立した補助工程が全体完了を妨げ得る（[統合後の現行コード](../../skills/qa-workflow/scripts/workflow_runtime.py)、[guidanceの要求集合](../../skills/qa-workflow/references/guidance.md)）。追加2 Skillの補助/必須モードと開始要求の照合は既に実装されているため再実装しない。必要な依存・副作用の確認を除外せず、残る汎用完了検証で要求の完了と補助工程の結果を分離する方向を検討する。必要な成果物・scopeが実際に満たされたかという意味上の完了条件を先に定め、単発・非保存の仕様分析やレビューに保存本文hashやowner登録を要求しない経路を検討する。永続成果物の再利用、決定論的技法、正式報告、実行・承認・cleanupなどはそれぞれの必要な検証を残す。未登録を無条件に完了扱いせず、全owner追加や共通JSON schema新設も目的としない。runtime-v2のAuthority→TR→TCN/CI→TCの追跡、scope ownership、fingerprint/currentness、局所再検証、coverageの閉鎖性と独立反証を維持する。登録集合・verifierの契約を変更する場合は再開、未検証・stale・別scope証拠・必須scope欠落の否定試験と関連評価を同期する。

## C. 実行安全・継続管理

### OPS-06 必要な副作用・共有資源の実行安全 (P0)

対象: qa-workflow、各実行owner。

現状: claimの原子的作成・読戻しはあるがrecover_claimの安全な条件付き解放と外部reservation実readback/releaseは未接続。結果不明時は再実行不可。#40は候補更新・関連前提の照合とrun再開を局所実装済みで、実owner横断の一意性・共有writerは未確認。

改善: 案件全体の一律排他ではなく、実際に競合する成果物・環境・共有資源・操作を単位として判断する。読み取り専用の独立した分析や分離済みの作業に、共有状態の変更がないことを確認できる場合は案件単位の排他や予約を要求しない。実際に重複実行・共有資源の競合・結果不明が問題となる操作に限り、既存ownerの冪等開始、実開始/結果/cleanup取得、必要予約を利用する。通常の単独文書保存にclaim・予約・排他基盤を追加しない。既存の案件単位の並行制約を実際の競合・隔離単位に改める。既存claim・予約・復旧処理は呼出し経路と実リスクを確認して維持/削減し、未接続の機構を完成させること自体を目標としない。必要保証未確認は該当操作のみblockする。claimを認可・CASの証明としない。PR #22の同一案件の並列実行に関する現行制約は改修と必要な受入まで維持する。

受入: 実行・副作用が関係する経路で、必要な二重受付防止、開始前中断、結果不明、cleanup、権限、共有時の隔離・解放競合を確認する。結果不明で有害な操作は盲目的に再実行しない。同一案件の独立分析、分離された書込み、同一正本への競合更新、共有テストユーザー・データへの実操作を区別し、必要な分離または競合制御だけを確認する。

具体的な確認箇所: [artifact_graph.py](../../skills/qa-workflow/scripts/artifact_graph.py)のclaim_mutable_operation / read_mutable_operation_claim / recover_claim / reserve_shared_resource / release_shared_resourceの呼出し元、test-execution / e2e-test-execution / testware-execution / exploratory-testing / usability-inspectionのpreflight・副作用上限・cleanup契約を調べる。読み取り専用操作、単独文書保存、実際の共有資源操作・外部更新を区別し、既存ownerの冪等開始や実行環境の隔離で足りる場合は重複claimを要求しない。実行結果不明・共有writer・必要な隔離が未確認の場合は従来のblockを維持し、必要性がなく安全に置換・削除できる経路では未接続機構の実装を追加しない。単に復旧機能を無効化して再実行を許す変更は行わない。testware-implementationの隔離作業・許可差分・条件付きGit反映はコード変更の安全契約であり、通常QA文書保存の簡素化を理由に解除しない。

### OPS-07 実行・証跡・報告の横断受入 (P1)

対象: test-execution、e2e-test-*、testware-*、regression-testing、exploratory-testing、defect-management、test-reporting。

現状: 各ownerはraw結果・分析・報告・cleanupを分離するが実provider経由の横断受入に未達が残る。

改善: 既存経路で実行前条件→raw結果→分析→欠陥候補→統合報告を必要な対象・実行環境で検証する。隔離された許可済み環境（Scenario Shop等）で現行Skillから実AgentによるQAを開始し、元の受入条件に不足する経路を改修する。初回FAILや予定母集団を書き換えない。完了・保存・承認・合否・取得完全性・終了基準・リリース判断は[共通運用契約](../reference/qa-workflow-operating-contract.md)の判定軸に従う。元依頼と予定母集団・宣言scopeを対応付け、欠落sourceを0件としない。母集団不明の直接報告は全体率・終了判定undetermined。新実環境の範囲は別途合意する。

受入: 未実行、判定不能、FAIL、retry、収集不全、cleanup未確認、修正確認と別目的Regression、証跡保護、外部Issue未認可拒否。FAILを含む完了、scope漏れ、計画なし、部分保存を確認する。

具体的な確認箇所: e2e-test-inspectionとe2e-test-executionの実効設定・安全条件の重複取得、test-executionの実行前YAMLと最終Markdownへの保持、e2e-test-reportingとtest-reportingの元結果・集計参照、regression-testingのActivity/Runと実行owner結果の重複記録を調べる。currentな確認結果を再利用できる場合は再調査・再保存を減らすが、実開始直前の環境・権限・副作用・cleanup確認、実行前条件の固定、rawと分析の分離、初回FAIL・retry・母集団の追跡を失わない。E2E固有報告と計画母集団による統合報告は目的が異なり、同じ値を表示することだけでSkill統合を判断しない。

## D. 文書整合・接続・効率

### OPS-08 WCAG closureガイダンスの旧記述 (P1)

対象: skills/qa-workflow/references/guidance.md §WCAG formal evaluation state（統合後main L278）、skills/qa-workflow/SKILL.md、skills/qa-workflow/scripts/workflow_runtime.py の _execute_and_finalize_wcag_report（L245以降）。

確認した差異: guidanceは現行finalize-wcag-reportがcaller提供dependency metadataとcandidateを照合するだけでcurrent rowを独立取得しないと記載。一方SKILL.mdはQA runtimeでcurrent stateを取得し公式WCAG close-reportを内部実行・CAS保存・独立readback後に完了する契約。コードもread-wcag-evaluation-stateを内部実行し、取得結果からWCAG runtimeを実行、_record_wcag_report_runtime_execution、finalize_wcag_reportを呼ぶ。旧説明は少なくとも現行owner内部実行経路と一致しない。

改善: 現行コード・schema・否定試験と照合してguidance更新。特権DB writer、複数host、認可や意味判断まで保証すると解釈しない。今回の静的確認は攻撃経路全体の実証ではない。現行の正規owner内部実行経路に合わせて局所修正する。実Agent評価を前提とせず、既存テストと照合して修正する。

受入: 偽造candidate/metadata拒否、owner内部実行、CAS conflict、履歴欠損、closure不完全、独立readbackを確認し文書とコード・テストを一致させる。

### OPS-09 QAコンテキスト・人間編集の受入 (P1)

対象: project-context、feature-analysis、ui-target-analysis、spec-analysis、qa-workflow。

現状: project-contextには案件探索・初期化・配置合意・Provider管理が残る。#40は指定rootを外部から受ける方式を実装済み。通常文書の人間編集と正式保存の横断受入には未達が残る。

改善: QA目的・用語・業務制約・DEC/ASMなどの意味管理と人間編集の受入に集中する。既存template・writerで必要なQA情報の不足確認・有効な判断の再利用を検証。案件初期化・配置決定をSkillから除外し、既存作業環境・指定入力・有効な既存規則を使う。指定がない場合は標準契約を利用し、QAに必要な情報の発見・理解・更新は担当Skillに残す。通常のMarkdown編集は許可範囲・必要な差分確認を基本とし、特殊な生成領域・ID・正式仕様変更だけ該当ownerの制約を適用する。配置・発見はOPS-14/15、移行はOPS-17で扱う。正式判断が必要な編集は提出と採用承認を分離する。通常編集にUI package固有のwriter・作業branch等を適用しない。直接改変時は編集案と元revisionを保全し、無断復旧しない。過去対象外（開発連動QA Planの旧Q06等）の再検証は別途合意する。

受入: 許可済み通常文書の編集・保存、既存正本再利用、正式意味変更/機械生成領域等の必要な制約、正本の競合・不明・アクセス不能時の保全、局所変更伝播。案件探索・配置承認を要求しない。

具体的な確認箇所: [project-context/scripts/project_context.py](../../skills/project-context/scripts/project_context.py) のdiscover、prepare_create、prepare_placement、placementとProject Context templateのSection 10/14/16を照合する。prepare_placementは案件名、owner、対象ref、revision、approval ref/revision、編集範囲、feature index refを照合し配置判断を記録する現行経路。Q07とOPS-14の方針に沿って案件探索・初回配置合意・Provider管理を除外し、QA目的・用語・業務ルール・環境制約・DEC/ASMの意味管理、必要なfieldの再利用と変更影響は維持する。既存正本・ID・履歴を壊さず、直接指定のコンテキストを使う経路で不要な初期化を求めない。独立Skillの存廃は管理責務を除いた後に評価する（OPS-18）。

### OPS-10 外部起動・製品CI接続 (P2)

対象: 呼出し側、qa-workflow、feature-analysis、CI handoff。

現状: PR/merge/release/資料改版の起動は呼出し側責務。実成果物取得・承認元未選定なら製品CI統合はblocked。

改善: 呼出し側が起動・入力/結果受渡しを管理し、既存ci_handoff.pyは必要な場合に利用する。直接依頼と外部起動の双方で必要な入力・結果受渡しを整備し、実接続先が決まっていない監視・起動基盤は実装しない。Skillに案件運用・監視基盤・CI Agent起動を新設しない。指定されたrepo・branch・commit・PR差分等のQA情報源の取得・意味分析は必要なSkillの責務とし、Git管理・案件運用とは区別する。過去対象外のrelease通し・実環境/CI接続の再受入は案件選定後に別途合意する。sample CIの分類・列挙対象（JSON等）の制約を一般化しない。

受入: 実際に必要とされる外部起動・資料変更・結果受渡しの経路について、変更元revision/build、未分類差分、必要成果物欠落を確認する。未設定とfailを区別。使用しない起動方式・接続を新設しない。source revision・build・母集団の確認と未取得の区別。

### OPS-11 効率と運用負荷の実測 (P2)

対象: qa-workflow、EVALS.md、呼出し側。

現状: PR #22効率比較はunproven、同一入力再依頼等の悪化と安全/品質未達を保持。#40の正式trigger・独立Semantic Judge・3構成比較・実Agent縦断も未実施。

改善: 今回の正式実Agent評価はCodexで行う。他clientは移植性・代表経路を確認し、明示指定がない限りハーネス・モデルの選定・比較・最適化を対象にしない。現行実装で改修前の実Agent利用・評価を開始し、既知の契約差の改修と並行して進める。別sessionのAgentによる実成果物・行動を評価し、原因に応じて担当Skill・Helper・案件知識・評価資産へ反映する。変更目的に応じて必要な指標・検証範囲を選ぶ。workflow全体の効率改善を評価する場合は、初回、同一入力再依頼、変更、外部資料改版、中断再開の既存比較条件で質問数、不要再生成、保存漏れ、所要時間、費用/token、品質・安全を測る。人間の作業・待ち時間、質問/承認回数、再開時の再入力も必要に応じて測る。人間レビュー・承認時間は過去比較で対象外承認済みのため、新規測定では計測法・比較母集団・範囲を別途合意し過去測定値に混入させない。

受入: 局所変更は必要な回帰検証と変更目的に対応する効果を確認する。workflow全体の効率改善は既存比較器の契約に従い、独立試行、同条件・品質/安全PASS、測定不能の明示を維持する。局所検証だけで全体の効率改善を実証したとしない。介入削減のため承認や品質を弱めない。

具体的な測定候補: 同じ要求・情報源・Agent・利用可能ツールで、読み込んだSKILL.md/reference、入力/output token、tool呼出し、質問・承認・設定、重複生成・保存、再開時の再入力、所要時間を既存評価経路で比較する。SKILL.mdの文字数やコード行数は読み込み負荷の調査手掛かりに留め、実測値の代用や固定削減目標にしない。専門品質・必要なトレーサビリティ・安全・再開を維持した場合だけ効率改善と評価する。PR #40の局所runtime回帰・filesystem試験をAgent発火・意味評価・構成比較の受入と混同しない。

## E. 成果物の標準配置・命名・発見

追加調査: main 197f1e0e1abe870b0cc793355e7abf73bf241d87 と同一のSkill・Helperを対象に、PR #41の調査時点で全37 SkillのSKILL.md、主要reference、関連Plan、一部保存helperを静的確認した。成果物の論理schema、保存先root、物理配置、命名、永続化能力は別々に評価する。既存配置を優先する[開発連動QA Planの旧Q06（配置契約）](../plans/2026-11-07_122247_development-qa-traceability.md)は維持する。以下は指定root配下の標準相対配置案。旧案件別配置判断は撤回し、既存配置への互換対応が必要なら外部境界で行う。現行実装の固定パス仕様ではない。

### OPS-12 標準ディレクトリ構造と保存粒度 (P1)

対象: 全成果物owner、既存Helper、ハーネスとの入力境界。

現状: [Project Context template](../../skills/qa-workflow/assets/project-context-template.md)のSection 14は既存成果物の場所・範囲・鮮度を記録し、Section 16には一部rootのstable keyがある。#40の3 kindは固定相対配置済み。新規案件全体の標準配置と案件・機能・scope・Run単位の保存粒度は未統一。特に計画、設計、質問、レビュー、報告は内容の形式と物理配置が別である。

改善: 指定root配下の標準相対配置を定義する。最終Skill構成の成果物についてowner、正本形式、保存要否、論理scope、保存粒度、標準相対path、例外、既存writerとの対応を明確にする。共通条件や機能横断成果物を機能別に複製しない。利用者指定・有効な既存配置を優先し、指定がなければ許可済み作業先と標準相対配置を使う。案件別の配置決定・初回配置承認を要求しない。39 Skillのマトリクスを起点に保存対象・非対象を含めて標準を確定する。以下は相対配置の検討案であり、必要なディレクトリだけ作る。共通成果物、機能/scope、共通条件、論点、Workflow、Run、Attempt、Entry、Snapshotの論理粒度を区別する。論点単位のID管理は1論点1ファイルを意味しない。正本・派生表示物・raw・履歴と必要な一体更新境界、既存固定名・保存不要・未接続を担当ownerごとに整理する。標準path採用は別途合意する。

```text
<指定成果物root>/
├── context/          # QA前提 / DEC / ASM
├── features/         # 機能台帳
├── specifications/   # 仕様分析 / ui-target/ / テスト対象資料
├── questions/        # Q / 質問定義・回答履歴 / 必要な旧フォーム
├── planning/         # QA要求 / 方式 / 計画
├── analysis/         # Risk / ITEM / COND候補
├── design/           # TR / TCN・CI / TC
├── reviews/          # coverage / adversarial review
├── automation/       # E2E選定 / E2E inspection / E2E・非E2E実装参照
├── execution/        # 直接TC / E2E / 非E2EのRun・結果参照 / E2E結果分析
├── regression/       # baseline / run / activity
├── exploration/      # charter / session / finding
├── knowledge/        # 既存entry形式
├── cross-context/    # PR #40の指定rootとして利用する配置案
│   ├── context-signal-batch/
│   ├── context-rule-candidate/
│   └── context-synthesis-run/
├── defects/          # 欠陥候補 / 外部Issue参照
├── usability/        # 評価 / 観測 / WCAG
├── reports/          # E2E報告 / 統合報告 / QA活動評価
└── state/            # 必要な永続stateのみ。ハーネス側で別rootに分離可
```

実テストコードは対象repoの既存構成、機密raw証跡・高頻度state・一時作業物は外部指定の安全な領域を利用できる。管理対象の正式成果物はディレクトリで分類・発見する。保存技術による別論理配置をSkillに設計させない。物理rootや案件名を意味identityにしない。

受入: 外部指定rootから同一相対配置を解決し、別session/agentでも一致。最終Skill構成について保存対象・非対象・粒度・例外を説明可能。既存ui-target-v1、knowledge entry、state、runnerの必要な形式・安全契約を維持し、必要な場所だけ生成する。

### OPS-13 成果物の命名規則と正本・表示物の識別 (P1)

対象: 全成果物owner、qa-workflow、project-context。

現状: [ui-target-v1](../../skills/spec-analysis/references/ui-test-target-analysis.md)は標準file群、[knowledge](../../skills/qa-knowledge/references/data-contract.md)はentry-ref.md、[artifact_graph.py](../../skills/qa-workflow/scripts/artifact_graph.py)はUUID.json・digestによるsnapshot等、[testware runner](../../skills/testware-execution/scripts/runner.py)はmanifest.json・attempt log等を規定する。一方、多くの計画・設計・報告ownerのテンプレートは出力内容を規定するが、共通の保存ファイル名は確認できない。

改善: 指定の形式・命名・履歴規則を優先し、指定がなければ標準を用いる。人間向け正本は読みやすい構造化文書を優先し、機械処理・再現性・検証上の具体的な必要性がある部分だけJSON等を採用する。既存の固定名・安定ID、必要なRun/Attempt・根拠履歴を維持。pathだけで意味同一性を推測せず、必要な参照・revision/hashを用いる。全成果物の二形式化、版番号、履歴複製、Runtime都合だけのmetadataを削減する。質問定義・元質問・回答履歴を対応付け、定義変更前の旧HTMLは未回収回答の復元に必要な間保全する。現行フォームは旧HTMLを同じブラウザ・保存領域で開いて旧回答を回収する契約である。元定義からの再生成で同じ復元が成立する場合に限り、HTML保全の簡素化を検討する。命名変更で論理ID・履歴・依存を失わない。

受入: 同一成果物の再依頼は既存正本を解決し、異なるscope・Run・attemptは衝突しない。正本と表示物・draftの誤認を拒否。大文字小文字、禁止文字、path traversal、名前衝突、既存固定名との互換性を実際のファイル操作条件で必要範囲を検証。改版前後の質問定義と回答の対応、旧回答の誤適用防止、必要な復元を確認する。

具体的な確認箇所: test-requirements-analysis、test-architecture-design、test-managementは現行のcanonical JSON packetを正本としMarkdownを描画物とする。人間の編集・利用が中心のQA要求・方式・計画はQ04に従い構造化Markdown等の正本が成立するか、機械集計用の母集団・状態と意味情報を分離する必要があるかを検討する。JSON正本の一律廃止は決めず、既存のvalidate_readback / impact / completion_check、managementのbuild_snapshot、test-reportingの参照と履歴・承認状態を確認する。形式変更が必要な場合も同じ意味情報を二重正本化したり不要な変換基盤を増やしたりしない。Machine Entity・実行raw・機械状態・#40の3 kindなど機械処理に適した形式は維持する。計画3 Skillの正本形式は利用者の編集性と必要な機械検証を両立する具体的な変更案を比較し、既存JSON validatorの都合だけで決めない。既存資産の移行はOPS-17に従う。

### OPS-14 外部指定root・相対ref解決 (P1)

対象: 全成果物owner、決定論的保存Helper、外部入力境界。

現状: Section 16にはqa.workflow_state_root、qa.knowledge_root、qa.feature_artifact_root、qa.reservation_root等がある。その他の成果物は主にSection 14や明示refに依存し、標準配置と案件別設定の横断解決規則が不足する。#40の指定root・root相対refは対応済み。専用stable keyのないこと自体を欠陥とせず、必要な既存契約を維持する。

改善: root・許可入力ref・操作可否は既存Agent環境・呼出し元・直接指定から取得し、利用者指定または標準相対pathを既存Helper・標準操作で解決する。指定がなければ許可済み作業先を利用し、必要な場所や許可を判断できない場合だけ確認する。既に指定された作業先、Agentが利用可能な標準ファイル操作、OS・sandbox等の既存権限で成立する場合はそれを利用する。新たなroot登録・Provider設定・案件識別・専用ハーネスは不要。保存が必要で場所や許可が不明な場合だけ確認する。外部責務は必要な入力・実行条件の供給と実際の権限管理に限り、既存環境で足りない場合だけ対応を検討する。案件探索・配置/Provider選択・専用stable key・初回配置承認は不要。重複・アクセス不能を不存在とみなさず、該当する新規作成・更新だけ停止する。旧配置との互換/移行は必要時に外部側で判断する。旧Project Context bootstrap案は撤回する。Section 12/14/16の運用設定解決は呼出し側の責務とし、QAに必要な意味情報は指定入力から取得する。

受入: 直接指定/ハーネス経由、専用ハーネスなしの既存Agent環境・許可済み作業先、保存先未指定の分析継続、必要時のみ場所確認、許可外/重複/アクセス不能/別root同名refの区別。許可済み通常保存は個別承認不要。競合・履歴・外部認可等は該当する経路だけ必要保証を確認する。

### OPS-15 保存済み成果物の発見・再利用 (P1)

対象: qa-workflow、project-context、feature-analysis、全成果物owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)は既存state・input revisionの再利用、[project-context guidance](../../skills/project-context/references/guidance.md)は許可範囲の列挙と候補判定を定めるが、全ownerの正本発見と重複検出の共通受入は未確認。#40はbatch再利用・軽量projection・候補のcurrentness・内容不変時のrun再利用を実装済み。[input_revision.py](../../skills/qa-workflow/scripts/input_revision.py)はファイル全体のSHA-256で変更を検知し、[runtime_contract.py](../../skills/qa-workflow/scripts/runtime_contract.py)は正規化入力・Entity単位のfingerprintを扱う。候補欄のみの変更でpath依存の再検証が広がる可能性があるが、全経路の影響は未確認。

改善: 外部指定root/許可direct ref、owner、scope、artifact identity、必要な保存revision・source依存・既存stateを使って発見・currentnessを確認する。必要時の範囲限定探索は既存ownerの許可範囲・完全性・型検証に従い、無制限の再帰探索やpath/ファイル名だけの推定を避ける。重複・一覧取得不全・不明参照は明示し、新規作成や自動選択を止める。通常QAでは既存Knowledge・成果物を直接参照し、必要に応じて横断分析を自律起動する。既存検索・再利用契約を活用し、新たな全成果物検索基盤を前提としない。入力revisionだけでなく、入力母集団、実際に利用したContext field、依存source/ownerのcurrentness・scope・意味契約を必要範囲で確認する。input_revision.pyのsameだけで再利用しない。ファイル全体の変更検知と利用した仕様・論理要素の変更を区別する。未承認候補の保存で承認済みの意味が変わらない場合は、既存のEntity単位fingerprintや依存関係、質問・回答正本を活用して再検証範囲を判断する。保存時のrevision・競合保証はOPS-03、root入力・ref解決はOPS-14で扱う。

受入: 別agent/sessionから同一正本を発見、変更なしの再依頼で不要再生成なし、部分改版では影響scopeのみ再検証。重複・欠落・stale・読取不能・列挙打切りを区別し、既存正本を保全する。OPS-01/03/05と接続する。未列挙入力・外部資料の改版、未使用Contextの変更、別workflow混在を確認する。未承認候補・質問のみの保存で利用中の承認済み根拠や論理要素が変わらない場合は無関係な下流成果物を再生成せず、正式仕様・利用中の根拠が変わった場合は影響scopeを再検証する。

### OPS-16 永続成果物・一時作業物・機密証跡の分離 (P0)

対象: qa-workflow、project-context、agent-answer-form、test-target-inspection、各実行・評価owner。

現状: [test-target-inspection](../../skills/test-target-inspection/references/guidance.md)は指定先・秘密情報の保存制約、[testware-execution](../../skills/testware-execution/references/guidance.md)はrepo外の保護された成果物先を定める。agent-answer-formはSkill外作業dirを使用する。#40は機密の保存制約・root外書込み拒否を実装し、局所テスト済み。全owner横断の保存区分・保持・cleanup・共有範囲は未統一。

改善: 正本、再生成可能な派生物、再開に必要なdraft、短期一時物、raw実行証跡、機密証跡を区別する。指定・既存規則と実行環境から保存可否、許可root、アクセス範囲、保持・cleanup方針、必要な参照期限を確認し、指定がなければ安全な標準処理を選ぶ。必要な保存条件が判断できない場合だけ確認する。rawの無断保存・共有を禁止し、安全な要約/参照のみを渡す場合も元証跡の取得可能性を偽らない。必要な保存ができない、または保存結果を確定できない場合はOPS-03の定義に従って確認済みの保存状態と完了条件への影響を明示する。正式成果物、継続作業、保護証跡、テストコードは論理区分とし、物理root/provider追加を前提としない。Skill指示とsandbox/hook/OS/provider権限は別である。ARIA snapshotは任意保存で、保存要求時のみ完了条件となる。中間保存は正式承認を代替しない。旧HTML・質問定義・未回収回答の復元に必要な記録はOPS-01/13に従って保全する。

受入: secretを含む証跡、安全な保存先なし、誤ったroot、別Runの証跡、保持期限切れ、一時物cleanup失敗、再開に必要な候補の保全を確認する。既存runnerの保護領域と安全契約を維持し、正式履歴をcleanupで削除しない。PR #22の指定領域外補助script書込み事例を含め、root外書込み・symlink等の逸脱、任意/必須証跡の差を隔離環境で確認する。

### OPS-17 既存配置との互換性・変更管理 (P1)

対象: project-context、qa-workflow、全成果物owner。

現状: 開発連動QA Planの旧Q06は既存配置優先、初回合意、物理分割の必要性判断、無断移動禁止を定める。標準案導入時に既存案件の混在構成・個別overrideを横断検証する必要がある。

改善: OPS-12〜15の設計・受入条件として、指定された既存配置・成果物をそのまま利用できるようにする。標準化のみを理由に既存正本を移動・改名・分割・再保存しない。独立した移行・互換性管理基盤は前提とせず、残る具体的な互換性問題だけを修正する。移行が必要ならSkill外の作業として対象・旧新ref・依存・履歴・権限・互換読取・条件付き切替・rollback・レビュー範囲を別途合意する。既存writer/schemaを尊重し二重正本を作らない。OPS-09の人間編集受入と接続。配置変更と人間編集採用を区別し、owner別schema・生成領域・ID・履歴を保全する。

受入: 許可済み既存成果物の無変更再利用、別rootの同名ref分離、未承認移行拒否、必要な外部移行時の競合・失敗、旧revision参照・rollback。標準構造が既存データ消失・二重正本・ID変更を生まないことを示す。実際に移行する場合は新旧参照・部分失敗・複数owner参照整合を確認し、条件不成立なら自動切替・無断rollbackしない。

## F. Skill責務の適正化（最優先）

### OPS-18 Skill・Runtime・Helperの責務適正化 (P0)

対象: 全Skill、既存Helper、qa-workflow、project-context、実行環境との境界。

現状: 成果物分類、案件識別・探索、配置合意、保存技術、認証・競合管理が専門QAの判断と混在し、読み込み量・ユーザー確認・重複契約を増やし得る。#40では追加2 Skillの案件・保存方式管理を除外し、既存state・owner検証へ接続済み。既存Skillには残る管理責務がある。

改善: 共通原則を最初に適用する。全39 Skillに加えRuntime・validator・Helper・呼出し側の契約を確認し、利用者の指定がない場合でも標準で直接利用できることを前提に、維持/既存手段への委譲/必要な外部責務/削除に分類する。QA固有の質問・根拠・結果は担当owner、質問への回答の意味・反映先・再開先の判断はquestion-analysis（OPS-01）、次工程・再開・要求された成果物の完了判断はqa-workflow（OPS-05）、必要な実行環境管理は呼出し側（OPS-06/14）。既存成果物で復元可能な情報の重複state、必要性のない保存証拠/validator/metadataを削減する。project-contextの存廃はQA専門責務から判断する。既存保証は必要性を評価し、変更する契約・回帰範囲を対象Planで明示する。不要な管理は別層に移さず削除する。必要な外部責務も既存Agent環境・OS権限・標準機能・明示指示で成立するなら専用機構を要求しない。機械的に確定できる処理は既存Helper・標準機能を優先する。単純な一覧取得や通常のファイル保存だけのために新しいHelperを追加せず、既存手段では不足する具体的なQA上の保証がある場合だけ追加を検討する。決定論的技法、ID割当、参照・構造検証等の必要な処理は維持する。Q12に従い実装不要・対応済み・外部責務・受入のみ等を再評価し、必要な対応と受入に絞る。

受入: 実際に変更する責務・契約について、(1) 専門外処理・重複の削減理由、(2) 直接利用を含む必要な実行条件でQA品質・根拠追跡・再開が維持されること、(3) 実リスクに応じた必要な保存・権限・履歴・競合・完了検証、(4) 変更目的に対応する読込・質問・設定・重複処理等の削減効果を必要な範囲で確認する（OPS-11）。全ownerに同一のCAS・保存証拠・state・専用検証基盤を要求しない。未確認は未確認と記録する。

具体的な確認箇所（調査revisionの実装に基づく候補）:

- qa-workflow: [artifact_graph.py](../../skills/qa-workflow/scripts/artifact_graph.py)にはProject Context parse、fixed-root scan、local baseline/history、SQLite workflow state、WCAG評価状態・報告確定、claim/reservationの処理がある。[workflow_runtime.py](../../skills/qa-workflow/scripts/workflow_runtime.py)と合わせて呼出し元ごとに必要な保証を確認し、QA固有の進行・依存・停止/再開・完了と、案件管理・保存技術・実行環境の処理を分ける。WCAG固有の正式評価の保証は必要な担当境界に残す。ファイルの大きさや責務混在だけで全体削除・別Helperへの全移管を決めない。
- project-context: OPS-09/14の責務削減後、共通QA目的・用語・DEC/ASM・業務制約の意味管理に独立した専門手順が必要か確認する。共通文書の直接参照で同等の意味管理が成立する場合は独立Skillの必要性を再評価する。所有者・参照・再開・既存資産の互換性を確認せず削除しない。
- 共通自己検証: qa-workflow、spec-analysis、question-analysis、test-analysis、test-requirement-design、test-condition-design、test-case-design、coverage-analysis、adversarial-reviewの9 Skillで、出力前の入力/停止条件確認、局所的な契約違反の最大1回修正、再確認、責務外への越境禁止が類似記述になっている。共通部分を短く整理できるか確認し、各Skill固有の品質条件と仕様根拠を創作しない条件は維持する。[EVALS.md](../../EVALS.md)の現行最大1回制約は目的（無限修正・責務越境の防止）に照らして必要性を評価する。採番・形式等の機械的な違反は既存手段で修正・確認する。自Skillの専門責務内の判断・修正と、他ownerの判断が必要な問題の引継ぎを区別し、根拠不足は必要な質問・局所停止とする。改善しない反復は停止し残る違反を報告する。回数増加や無制限修正を目的とせず、変更する場合はEVALS.md・関連Skill・評価資産を同期する。共通reference化は単体配布・直接利用・読み込み経路で利用可能な場合に限り、新たな生成frameworkを前提にしない。
- Runtime契約と段階的詳細化: test-analysis、test-requirement-design、test-condition-design、test-case-design、coverage-analysis、qa-workflowの共通envelope・verify_runtime_evidence等の繰返しを確認し、実際の重複とSkill固有のpartial rerun、previous artifact、current_structure_state等を区別する。現行は9 Skill（spec-analysis、test-analysis、test-requirement-design、test-condition-design、test-case-design、coverage-analysis、qa-workflow、usability-inspection、wcag-conformance-evaluation）にruntime_contract.pyを配置し、[test_runtime_portability.py](../../tests/skills/runtime/test_runtime_portability.py)で9コピーのバイト一致と代表7 Skillの単体実行を検証している。単体配布のための複製と不要な処理重複を区別し、各Skillで使われない処理や専門外の処理、変更時の同期負担を調べる。既存の一致検証・単体実行検証を優先し、他Skillやrepository全体の常時参照を必須にしない。新しい生成・配布基盤は前提としない。qa-workflow、test-condition-design、usability-evaluation、usability-inspection、wcag-conformance-evaluation等の長い手順では、発火・責務・必要入力・安全上の必須条件をSKILL.mdに残し、該当時だけ必要な詳細を読む構造を検討する。正式WCAG評価のsampling・観測・closure、ブラウザ操作の安全、既存テスト技法と参照検証を削らない。
- 専門Skillの分割: test-requirements-analysisとtest-requirement-design、test-item-analysisとfeature-analysis、test-condition-analysisとtest-condition-design、coverage-analysisとadversarial-review、test-executionとE2E実行、e2e-test-reportingとtest-reporting、usability-evaluationとusability-inspection、regression-testingとtest-managementは、現行定義上は異なる専門責務を持つ。名称や処理の類似だけでは統合・削除の根拠にならない。全37 Skillと追加2 Skillの定義を確認した段階では安全に削除できるSkillは特定していない。Skill数を削減目標にしない。
- PR #40: context-signal-auditの単一sourceの中立観察・不変batch・訂正、context-rule-synthesisの独立根拠/反例/差異条件・仮説・handoffは維持する。統合後の実装ではcontext-synthesis-runに予定payload、base revision/hash、related candidate前提、handoff intentを保持し、PR #40の skills/qa-workflow/scripts/context_workflow_state.pyで開始要求、試行、run mapping、完了を扱い、workflow_runtime.pyの_verify_context_synthesis_workflow_stateが照合する。成果物から確実に復元できる情報の二重管理があるか確認する。一方、開始時の要求範囲、0件runと未実行の区別、別run混入防止、関連候補の同一保存境界での条件確認、外部handoffの結果不明からの再開など、成果物単体では証明できない情報や現在の必要保証は残す。通常保存の改善済み部分はOPS-03を参照し、未完了の実owner受入は維持する。

受入の追加ではなく既存AT-21/22/24/25等への具体化として、実際に変更する呼出し経路と契約、除去・維持・委譲する理由を確認する。既存テストで十分な場合は新たな重複試験を要求しない。各具体候補は該当OPSとQ12に従って最新baselineで再判定する。

### QA活動の判断・継続改善

[QA活動の基本原則](../reference/qa-skill-design-principles.md#qa活動の基本原則)を既存Skillの判断に反映する。2026-11-26にPR #41の50f37f4とPR #40の4eebeabを基準に、ISTQB・IVECと主要Skill契約を照合した結果、次の不足または見直し候補を抽出した。既存OPSとの関係を示し、同じ処理や受入を別要件として重複させない。統合後の追加2 Skillに既にある処理を利用し、残る不足と必要な検証を対象Planへ反映する。現行の有効な契約や安全条件は改修まで維持する。

- **合意からの自律判断（OPS-01/02/04/09/18）**: [question-analysisの判断順序](../../skills/question-analysis/references/guidance.md#判断順序)は既存回答・有効な仕様・承認済み仮定の確認を定め、[test-case-design](../../skills/test-case-design/references/guidance.md#複数期待結果複数仕様根拠の対応)は複数根拠による期待結果を許容する。spec-analysisは既存の有効なルールを組み合わせ、適用範囲・例外に照らして今回の判断を導出できるようにする。導出結果は必要な根拠参照で表し、個々の判断の新規DEC/ASM登録や再承認を要求しない。question-analysisはその判断で解決できない重要な論点のみを質問へ送る。テスト技法・観測・リスク評価・調査・設計は依頼されたQA活動の専門判断として担当Skillが行う。正式仕様の決定・変更、利用者の対象範囲変更・リスク受容、実操作の許可とは区別する。仮説は調査・観点生成に使えるが、未確定の期待挙動を正式仕様として採用しない。根拠: CTFL §1.4〜1.5、IVECデザイナー §4.1.1〜4.1.2。
- **知識の参照・蓄積・横断分析（OPS-09/15/18）**: [qa-knowledge](../../skills/qa-knowledge/references/guidance.md)はcurrent entryを読むだけならgatewayとしない。[現行の横断コンテキスト分析](../../skills/qa-workflow/references/guidance.md#横断コンテキスト分析)は無効・未指定時に追加2 Skillを起動しない。改修後は未指定でもAgentが必要性を判断して起動し、明示的な無効指定は尊重する。毎回の起動・全知識の読み込みは要求しない。通常のQAでも、担当Skillが共通処理・類似機能・過去の合意・欠陥・関連Knowledgeを必要な範囲で参照できることを確認する。既存知識の参照を横断分析モードや新規保存の条件にしない。再利用価値のある観察は担当成果物または必要時のcontext-signal-auditへ、横断的な法則候補・反例分析が必要なときはcontext-rule-synthesisへつなぐ。根拠: IVECデザイナー §4.1.1・4.1.3、CTFL §1.3〜1.4。
- **活動・方式・テストレベルの選択（OPS-05/18）**: [qa-workflow](../../skills/qa-workflow/SKILL.md)は要求成果物に応じた開始点を選べる。[test-analysis](../../skills/test-analysis/references/guidance.md#テストレベル)と[test-architecture-design](../../skills/test-architecture-design/references/guidance.md#レベル割当と競合)は明示指定・承認済み割当がない場合にシステムテストを既定とする。目的・リスク・テスト可能性から静的テスト、コンポーネント、統合、システム、受入、探索等の必要な活動を選べるか、現行既定値・下流の依存を確認する。必要な場合は既定値の適用条件を見直す。明示指定・承認済み方式を尊重し、既存の検証分担と必要なカバレッジを維持する。相談・レビュー・観点設計に不要な詳細TCを強制せず、詳細TCが必要な依頼では既存の実行可能性・品質を維持する。方式判断は担当Skill、工程選択はqa-workflowとし、固定手順・全工程の完了証明を目的化しない。根拠: CTFL §1.3〜1.4・§2.2・§3、IVECアーキテクト §4.2.5〜4.2.9、デザイナー §4.2.2。
- **期待結果と観測方法（OPS-05/07/18）**: [test-case-design](../../skills/test-case-design/references/guidance.md#現在有効な仕様根拠--期待結果の根拠)は期待結果と仕様根拠の対応を、[test-analysis](../../skills/test-analysis/references/guidance.md#テスト可能性)は観測可能性を定める。方式・分析・ケース設計で、対象に適した判定手段を選ぶ。例えば独立した期待値計算、仕様に基づく入出力関係、非同期完了の観測、永続状態・権限の確認などを必要時に利用し、対象実装と同じ誤りを期待値側に持ち込まない。絶対値が得られない場合は有効な関係を根拠とした既存メタモルフィック技法等を検討する。既存の実行・独立レビュー・assertion検証で判定の妥当性を確認し、観測不能をPASSとしない。根拠: CTAL-TA v4.0（テスト技法）、IVECデザイナー §4.2.3〜4.2.5。
- **欠陥予防・テスト資産の有効性（OPS-09/15/18）**: [defect-management](../../skills/defect-management/references/guidance.md)は原因分析を実行ownerへ戻し、[regression-testing](../../skills/regression-testing/references/guidance.md#run-selection--currentness)はリスク・過去Finding・Knowledgeを利用する。欠陥原因・発生条件・関連機能から必要なリスク再評価、設計変更、再利用知識を担当ownerへつなぐ。共通原因の仮説と確認済み欠陥は区別する。廃止仕様、重複検証、新たなリスク、検出力不足など具体的な理由がある場合は、既存テストの選択・方式・設計を見直す。重要な回帰防止テストをPASS継続だけで削除しない。根拠: CTFL §1.3（早期テスト・欠陥の偏在・テストのすり減り）、CTAL-TA（欠陥予防）、IVECデザイナー §4.2.7、アーキテクト §4.3。
- **Agentの活動方法の改善（OPS-11/18）**: [test-evaluation](../../skills/test-evaluation/references/guidance.md#責務境界)は案件QA活動の評価を担当し、Skill自体の評価は[EVALS.md](../../EVALS.md#評価レイヤー)に分離している。この境界を維持する。活動中に同じ質問・設計漏れ・誤った一般化・不要工程・機械処理の誤り等を発見したら、原因に応じて案件の既存知識・計画・設計へ反映するか、Skill・Helper・評価資産の改善候補として既存開発経路へ引き渡す。影響を受ける担当ownerが必要な変更を行い、次回の活動や既存回帰評価で効果を確認する。局所的な教訓は既存成果物や開発記録へ反映し、Skill改修は既存の開発権限・レビュー・評価に従う。根拠: CTAL-TM v3.0（テストプロセス改善）、IVECアーキテクト §4.3.4〜4.3.9。

**受入の整理（OPS-05/11/18、AT-21/22/25）**: [EVALS.md](../../EVALS.md)の既存意味評価・実Agent評価・決定論的出力評価から目的に合うものを利用する。次のケースは既存fixture・rubricで不足するものだけを補う。

- 同一質問の再利用、新機能への有効な共通ルール適用、複数根拠からの導出、例外・適用範囲外・失効・仕様競合、必要な質問、類似欠陥の観点利用を対比し、正しい自律判断・誤判断・必要な質問漏れを評価する。不要質問の削減だけを成果にしない。
- 目的に合う活動・方式選択、必要なカバレッジ・観測・品質・安全の維持、不要工程の省略、教訓の次回利用を確認する。決定論的生成・必要な形式/参照・実行証拠は既存の仕組みで評価し、専門判断の妥当性は意味評価・実Agent結果で確認する。
- [既存の効率比較](../../EVALS.md#qa-workflowの効率比較pr-22aの評価基盤)は同一test_set_ref等を要求する。同一テスト集合での実行効率は現行契約で比較する。テスト集合や方式自体を変更する改善は、同じQA目的・検証責務・リスク・独立した品質/安全基準で評価し、同一テスト集合比較の結果と混同しない。既存比較で成立するかを先に確認し、不足する場合のみ比較契約を改修する。

公式参照: [ISTQB CTFL v4.0.1](https://istqb.org/certifications/certified-tester-foundation-level-ctfl-v4-0/)、[CTAL-TA v4.0](https://istqb.org/certifications/certified-tester-advanced-level-test-analyst/)、[CTAL-TM v3.0](https://istqb.org/certifications/certified-tester-advanced-level-test-management-ctal-tm-v3-0/)、[CT-GenAI v1.1](https://istqb.org/certifications/gen-ai/)（生成結果評価・AI固有リスクの公式概要）、[IVEC v3.2.0](https://www.ivia.or.jp/item43/item38)（テスター・デザイナー・アーキテクトの関連章）。シラバス全文や全評価fixtureの網羅照合、CT-GenAI本文全体、実Agentによる改善効果は未確認。ここでの受入は後続改修の候補であり、完了済みの実証結果ではない。

### 責務再評価の扱い

各OPSの改善・受入本文を実装検討の入口とし、別の責務再評価表を正本にしない。共通原則とOPS-18を優先して削減・維持・委譲を判断する。

### PR #40統合後の確認（必要なOPSに適用）

参照: [PR #40](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/40)、[PR #38](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/38)、[PR #39](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/39)、[PR #17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)。PR #40の設計は利用者決定により指定ディレクトリ・責務縮小へ改訂済み。対象PRは参照のみとし変更しない。旧kind別branch案は採用しない。

<!-- dprint-ignore -->
| ID | 着手前の確認 | OPS |
| --- | --- | --- |
| PRE-01 | 統合後の登録構成は39 Skill、runtime-v2 root 6、owner verifier 9。README・成果物マトリクス同期済み。正式比較による最終構成選定はPRE-11 | 05/12/18 |
| PRE-02 | PR #38/#40の実保存・承認/認可境界、自己申告と認証の区別 | 02/03/04 |
| PRE-03 | #40の指定root・3 kind配置は実装済み。全Skillの標準配置と利用者指定・既存配置の優先を整備 | 12/13/14/18 |
| PRE-04 | 3 kindの固定相対配置・不変batch・候補・runの履歴を維持 | 12/13/17 |
| PRE-05 | 質問前の自己解決、対話提示と永続的質問発行を区別 | 01/02 |
| PRE-06 | #40の横断検索・既存Knowledge lookupを再利用。その他の成果物発見・変更影響はOPS-15で確認 | 15 |
| PRE-07 | #40の補助/必須・単体・要求scopeの局所検証済み。未指定時の自律起動と汎用完了判定は改修・受入 | 05/07 |
| PRE-08 | #40の過去完了と現在採用の分離は局所実装済み。通常QAの再利用・実利用を確認 | 05/15 |
| PRE-09 | semantic handoff keyと実owner一意性・結果不明からの再開 | 01/06 |
| PRE-10 | #40の64 KiB等の本文搬送境界は局所検証済み。関連変更時の回帰・実Agent入力負荷を確認 | 03/05/12/15 |
| PRE-11 | PR #40の品質・構成比較・効率baselineと責務削減指標 | 11/18 |
| PRE-12 | 実評価ランナー・CIの最新統合状況、旧未達/対象外 | 07/10/11 |
| PRE-13 | 全18 OPSの目的・現状・対応を統合後に再評価済み。具体的な変更経路・削減可否は関連Planで精査 | 全18件 |

PR #40はmainへ統合済み（PRE-01）。追加2 Skillの保存・要求照合・再利用の実装済み部分は各OPSで区別した。全18 OPSの目的・残存差分を再評価した（PRE-13）。具体的な変更経路・削減可否と他のPREは関連Planで確認する。PRE全件の完了を一律の着手条件にしない。本PRは文書のみを対象とする。未検証の操作は未検証のままとし、必要な安全条件は回避しない。既存資産の移行は別作業であり無断実施しない。Q12に従い必要な改善と受入が完了して目的を満たすことを終了基準とし、不要・責務外・対応済みの理由を既存Planへ記録する。必要な未対応・未検証を不要扱いしない。新しい管理台帳を作らない。

## 実装順序と受入候補

過去のレビューで必要と判断した改善・受入は各OPS本文に統合済み。経緯は[PR #41](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/41)を参照する。

### 実装目的別の整理（既存OPSを維持）

OPS-18を全改修の判断基準とし、01〜06・09・12〜16・18の明確な契約差を解消する。08は局所文書修正、07・11は既存経路で実Agent評価と必要な改修、10は必要な外部接続、17は12〜15の設計・受入条件として扱う。現行baselineの実Agent利用・評価は先行し、既知の問題の改修と並行する。次の5領域は計画の分類であり、新しい管理単位・独立実装・強制順序を作るものではない。

<!-- dprint-ignore -->
| 領域 | 対象OPS | 目的 |
| --- | --- | --- |
| A 責務削減・適正化 | 18 | Skill・Runtime・validator・Helperの不要責務を削減 |
| B 成果物管理 | 09/12/13/14/15/16/17 | 必要な相対配置・形式・命名・発見・人間編集・保護・互換性 |
| C 質問・保存・継続 | 01/02/03/04/06 | 自動保存、必要な内容承認・再開、実リスク相応の安全 |
| D QA品質・完了検証 | 05/07/08 | 意味品質、必要な検証・完了、既存文書との整合 |
| E 外部接続・効率評価 | 10/11 | 必要な接続・改善効果の評価 |

各領域で必要な依存条件だけを確認する。旧Phase全体の完了を後続の一律前提としない。OPS-16の必要な保護と現行の安全制約は全領域で維持し、未改修のblocked条件を回避しない。新Skill・中央DB・中央mutable manifest・全成果物統一schema・全Skill専用key・汎用storage framework・一律配置移行は前提としない。

### 横断受入シナリオ候補

既存Deterministic Test・Semantic Evaluation・実Agent評価を必要範囲で再利用する。以下は各OPSの受入を組み合わせるシナリオ候補であり、独立した追加受入ゲートではない。該当変更・実リスクに応じて既存試験でカバー済みのものは重複実施せず、必要な入力・根拠・結果・未達だけ記録する。

<!-- dprint-ignore -->
| ID | シナリオ | 期待する受入結果 | 関連OPS |
| --- | --- | --- | --- |
| AT-01 | 初回の実行環境 | 指定・既存配置を優先、指定なしは許可済み作業先と標準配置、不要な案件探索・配置再質問なし | 09/12/14/18 |
| AT-02 | 既存成果物利用 | 許可済みroot・ID・有効権限を維持、不要再質問なし | 09/14/17/18 |
| AT-03 | 初回テスト設計 | 必要scopeの分析〜TC、正本・参照・必要保存検証 | 03/05/12/13 |
| AT-04 | 仕様ブロッカー | 許可中間保存、または確認済みの保存状態（未保存・保存結果不明等）を明示、該当scopeだけ停止 | 01/02/16 |
| AT-05 | 部分回答 | 根拠currentな回答scopeのみ再開、旧回答/保留を誤承認せず、仕様と実行条件等の回答を担当先へ反映 | 01/02/13 |
| AT-06 | 別Agent再開 | 保存済み成果物・必要時のみstateから再開先取得、未保存候補は復元保証なし | 01/15/18 |
| AT-07 | 変更なし再依頼 | 母集団・依存・currentness確認、有効合意再利用、不要再生成なし | 02/05/15 |
| AT-08 | 一部仕様改版 | 外部資料含む入力完全性、影響scopeのみ再検証 | 05/15 |
| AT-09 | 人間編集 | 通常編集は簡素、正式変更/生成領域のみ必要owner制約、無断上書きなし | 09/17 |
| AT-10 | 並行Workflow・共有資源 | 独立した分析・分離作業と実競合を区別し、共有時だけ必要な競合/予約保証を確認、未確認操作をblock、混線なし | 06/16 |
| AT-11 | 保存後の結果不明 | 必要な実保存/操作結果を照合、盲目的再試行なし | 03/04/06 |
| AT-12 | 依存する複数成果物の部分保存 | 必要な参照整合確認まで依存する下流current不可 | 03/12/15 |
| AT-13 | 正本重複 | 無断選択・新規作成なし、未解決明示 | 14/15 |
| AT-14 | アクセス不能 | 不存在と区別し正式保存block | 03/14/15 |
| AT-15 | 承認対象の変更・失効・必須scope除外 | 承認の対象・意味・有効性に影響する変更では旧承認の誤再利用を拒否。開始後の必須scope除外は有効な明示承認と必要な権限に基づき判定し、未承認除外を拒否 | 02/04 |
| AT-16 | 機密証跡 | 未許可領域書込み/公開なし、任意・必須保存区別 | 16 |
| AT-17 | 必須scope宣言漏れ・補助工程 | 必須scopeと依存の不足を検出、未指定でも必要な横断分析を選択、明示無効を尊重、独立補助工程の未検証で不要な全体停止なし、誤完了なし | 05/07 |
| AT-18 | FAILを含む実行 | 合否・母集団・cleanup・終了基準・workflow完了を独立判定 | 07 |
| AT-19 | 異なるAgentで同一依頼 | 同じ指定・既存規則または標準で同一正本・配置・命名、別scope/Run衝突なし | 12/13/14/15 |
| AT-20 | 単発読取・レビュー・調査 | 対話回答を基本とし、再利用価値のある知識だけ許可範囲で自律保存。明示非保存を尊重、不要な保存・配置承認なし | 01/02/12 |
| AT-21 | 責務境界・移植性 | 異なる外部実行条件でも案件/成果物branch/Provider管理なく（指定repo等の情報源分析は可）同じ要求・入力に対する意味契約と必要品質を満たす。決定論的処理と確定済み仕様・判断の一貫性を維持し、許可外操作を拒否 | 18 |
| AT-22 | 責務削減と回帰 | 実Agentの改修前後で専門外判断・読込・不要質問・重複管理削減、既存QA品質・安全・履歴維持 | 11/18 |
| AT-23 | 成果物作成・通常保存・内容承認 | 明示の非保存指示がなければ許可範囲で自動保存、依頼者の明示内容承認を採用、必要時のみ追加権限確認、既存承認済み意味を保全 | 01/02/03/04/18 |
| AT-24 | 直接Skill利用 | 特定ハーネスなし、指定・既存規則優先、指定なしは許可済み作業先・標準契約、必要時だけ保存・形式・運用の指定を確認 | 12/14/18 |
| AT-25 | 最小構成 | 実リスク相応の防御・検証・形式・履歴、利用者に不要な保存技術の選択を求めず、不要なCAS/専用基盤/Helper/複製/承認なし、単体利用を維持 | 03/05/06/11/13/18 |

上記は未実施の受入候補。具体的な相対path・必要最小の外部契約・実環境・過去対象外の再検証範囲は後続Planで確定する。共通原則の再承認は不要。過去のPR #22の未達・対象外・検証結果を上書きしない。Q11の既定continuous/明示gatedとQ12の必要性・終了判定は関連OPSの既存受入に統合する。
