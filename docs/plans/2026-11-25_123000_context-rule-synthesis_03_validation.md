# 評価・実装順序・受入

親: [実装Plan](2026-11-25_123000_context-rule-synthesis.md)。[01](2026-11-25_123000_context-rule-synthesis_01_storage-and-contracts.md)・[02](2026-11-25_123000_context-rule-synthesis_02_skills-and-workflow.md)に従う。

## 1. 実装タスクと依存関係

- [x] 基準commitでCI・テストbaseline、PR #38/#39/#17との差分、保存/認可境界、既存ownerの保存/CAS/照合点を記録。実運用root・共有writer・owner一意性の未確認範囲は依存条件として分離し、通常root保存をhost未選定扱いで停止していない。[検証記録](../implementation/pr40/verification.md)
- [x] 既存runtimeの要求scope・再開テストで仮target→実ref、複数batch/run、凍結済み記録と元要求の対応、64 KiB超の保存本文の搬送・再開を検証し、必要最小限の共通変更を決める。3成果物のサンプル・data-contract・identity/validate/impact/completion helperと機械契約テストを実装し、既存canonical規則に合わせた。[検証記録](../implementation/pr40/verification.md)
- [x] 指定rootを受け取る3 kindのdirectory store、list/history、相対ref、条件付き保存、独立readback、Aのimmutable batch、Bのrun保存・state記録・再開を既存ファイル/SQLite操作へ接続。隔離ローカルfilesystemの実保存先で作成、競合、履歴、symlink拒否、再開を確認した。実運用root・共有writer能力の確認は別途未完了であり、特定Provider拡張は要求しない。[検証記録](../implementation/pr40/verification.md)
- [ ] 2 Skillの本文/参照/assetを実装し、A/Bの相互責務、横断検索、既存owner routingを接続。追加調査と質問、既存Knowledge/Authority再利用を実Agentで確認。
- [ ] workflow routing/state/owner verifier・runtime_contractコピー、README/EVALS、各registryを同期。無効/補助/必須/単体と既存再開・依存伝播を検証。
- [ ] trigger/deterministic/semantic/runtime/実provider・実Agent、各構成のスモークテスト後に3構成の正式比較を実施。結果に応じて本採用構成を決定し、最終構成で全受入を確認する。

純粋helper・Skill本文・評価セットの設計は並行可。identity/保存契約とscope/owner契約を共有してから接続する。全タスクは同一branchで完結し、依頼されていない別PR作成・製品変更を行わない。

### 実施状態

このチェックリストの項目は複数の必須条件をまとめている。部分実装や一部unit testだけではチェック済みにしない。2026-11-26のローカル作業では保存・owner contract・runtime state・runtime transportの対象suite 62件がPASSし、65,535/65,536/65,537 byteの3 kindを実保存からowner verifier、workflow_runtime完了、凍結結果のdownstream再開まで検証した。repository deterministic suiteは675件PASS、新規2 Skillのdeterministic output runnerは各1 eval・計6 assertions PASS、semantic datasetは39 Skill/227 cases・14 tests PASS、trigger contractは17件PASS、deterministic runnerは12件PASS、ci_handoffは28件PASS。継続レビューの回帰は6 suite・116 testsがPASSし、Ruff check/format、py_compileもPASS。CIで指摘された64 KiB統合fixtureの要求scope欠落を修正したhead `46fc0aaf`では、runtime全suite 1,509 tests（227.544秒）がPASSし、GitHub Actions 5 workflowすべてsuccess。ローカルdprint集約checkは今回対象外のtracked file 18件のline-ending差でexit 20だったが、CI Code QualityはPASS。今回の最新変更を含む全runtime suiteは1,513 tests中1,512件がPASSし、`test_real_local_http_status_200_with_wrong_body_fails` 1件がsandboxのloopback bind拒否でerrorとなった。同テストは127.0.0.1だけを使う隔離実行でPASSしたが、全suiteはPASS扱いしない。変更後CIを確認する。最新の証拠は[検証記録](../implementation/pr40/verification.md)を参照する。

通常root保存に専用認証hostは要求しない。隔離ローカルfilesystemで3 kindの実保存、list/read/history/条件付き更新/readback、A/B stateのSQLite永続化・再開を実測した。実運用rootは未指定であり、共有writer/複数host、既存ownerの外部一意性、外部認可は未確認。実Agent縦断受入、正式trigger評価、独立Semantic Judge、3構成比較は未実施である。既存trigger runnerはClaude Code専用であり、Claudeは使用しない。先行するCodex CLI target-only positive smokeは各Skill 1件のみで正式評価ではなく、repository Hook/execpolicyも未確認。Codex等の外部サービスへのrepository data送信許可は未確定のため、formal evaluationを実行しない。各基本設計13.2項目の証拠と状態は[PR #40検証記録](../implementation/pr40/verification.md)に記録し、複合受入は未完了のままとする。

2026-11-26の再レビューではin_progress登録時の未確定candidate readback、関連candidateの保存境界precondition、workflow stateのartifact-root binding、全runを統合する最終completion gate、history symlink pathの副作用を再確認した。ローカル修正後にstore 12件、workflow state 12件、contract 14件、owner verifier 4件、runtime transport境界1件の計43 testsがPASSし、中断点からの再開も確認した。単体QA workflowの既存処理を保つためcompletion adapterをcontext scopeがある場合だけ読み込み、依存不足は当該scopeのみblocking issueとする。GitHub Actionsのruntime全suiteは`7a23afdf`で1,504 tests PASS、後続のdocs同期head `af7b1615`も5 workflowすべてsuccess。実Agent/ownerを介した受入、共有writer/外部owner一意性、実運用rootの認可は未実施で、局所テストで代替していない。詳細は[検証記録](../implementation/pr40/verification.md)。

2026-11-26の継続再レビューで、従来の最終gateがB run群中心で、開始時A/B要求集合とruntime最終scope集合を一体で検証していない点を修正した。現行gateは永続stateの開始要求ごとにAの最新attemptまたはBのrequest groupを照合し、A batch/B runの実scope・root/revision/hash readback・owner verifier記録を確認して、mapped artifact scope集合をruntime最終required scope集合と完全一致させる。runtimeからB要求group全体が欠落するケース、最終scope集合の省略・過剰、開始時要求とのruntime契約不一致、必須要求に含まれない補助context scopeがworkflow stateを持たないケースの回帰を追加した。CIで指摘された64 KiB統合fixtureの古い開始scope契約を修正し、Aの完了attempt、Bのrun参照、target batchのoperation input/snapshot/provider readbackをつないだ。`test_context_runtime_transport` 5件、`test_context_workflow_state` 17件、`test_runtime_portability` 3件、`test_workflow_runtime` 26件、`test_owner_scope_resume` 41件、`test_integration_required_scopes` 24件の計116件が個別にPASS。Ruff check/format、py_compileもPASS。CIで一度失敗したfixtureを修正したhead `46fc0aaf`はruntime 1,509 testsとGitHub Actions 5 workflowすべてsuccess。これらは局所回帰であり、設計13.2 Eの全複合受入や実Agent受入を完了扱いにしない。実Agent・外部評価・実運用root/owner検証は未実施で、局所テストで代替していない。詳細は[検証記録](../implementation/pr40/verification.md)。

2026-11-26の最終継続では、最終runtime inputからA/Bの要求scopeとnested state参照がすべて落ちる場合に備え、必須context workflowがoptionalな`context_workflow_state_root`を独立fieldで渡す契約を追加した。root anchorがあれば最終入力の他context fieldが全欠落しても既存stateを読み未完了とし、root anchorなしの通常単体runtimeを許容する。凍結済みv2 inputのresume schemaへanchorの後方互換を追加した。A start source/range/observation condition、B start source/investigation conditions/requested scopeへの後続attempt/run対応、split runの不足coverageを回帰化した。`test_context_workflow_state.py` 21件、`test_context_runtime_transport.py` 5件、`test_runtime_portability.py` 3件、`test_workflow_runtime.py` 26件、store 12件、contract 14件、owner verifier 4件、owner scope resume 41件、required scope integration 24件を各suite個別に実行し計150件PASS。py_compileと現環境Ruff 0.15.2のcheck/format checkもPASS。repository pin Ruff 0.16.8とdprintはローカルで未実行。全runtime suite 1,513 tests中1,512件がPASSし、sandboxがloopback socketを拒否した1件は隔離loopback許可実行でPASSしたため、suite総合結果はenvironment-limited errorでありPASSではない。GitHub Actionsの変更後結果はpush後に確認する。外部formal trigger/Judge/実Agent/3構成比較は未実施であり、承認済み送信範囲を越えて実行しない。

## 2. テストの配置と受入マトリクス

[共通原則](../reference/qa-skill-design-principles.md) PRN-01〜08・Q01〜08を確定前提とする。許可済みroot内の通常保存は都度承認不要、内容承認・破壊的変更・必要な外部操作は別。特定ハーネスは必須でなく、直接利用でも必要入力・権限があれば実行する。通常保存に専用認証基盤・独自CAS・分散lockを一律要求しない。実際の共有/競合条件に応じて必要な保証だけ確認する。既存ownerの正式判断・安全制約は維持する。

許可済み通常保存・質問/回答保存が個別承認なしで成立、未承認候補をAuthorityへ昇格させない、直接利用・保存先未指定でも可能な分析を継続することを確認する。専用認証hostや新汎用防御機構の存在を合格条件にしない。

既存 tests/skills/runtime/test_pr24_artifact_store.py、test_pr24_git_artifact_store.py、test_owner_verifier_registry.py、test_owner_scope_resume.py、test_integration_required_scopes.py、test_workflow_runtime.py、test_workflow_efficiency.py、test_question_ids.pyを拡張または既存パターンに沿う新規テストに分割。tests/skills/evals/deterministic/test_context_rule_contracts.py等、Skill-local eval validator/fixtureは既存manifest方式。ファイル名は実装時に調整可。実際のprovider保存経路を通す統合テストを含め、モックの成功だけで受入としない。

### A. 不変ログ・identity・状態（設計13.2 A）

- [ ] Aの失敗→正常再実行、既知partial→完全取得のbatch identity非衝突、未知partialは保存しない、complete 0件と未実行を区別、保存成功/readback失敗→既存batch reuse。同じsource/rangeを別workflow/観点で使用してimmutable metadataが書換わらない。
- [ ] 4種identityとbatch/run派生identity再計算、signal hash/直接source ref、canonical bytes/top-level ref、project/root境界、意味条件・極性・要求scope/調査条件の違い、検索タグ追加不変。
- [ ] 7状態＋解決/鮮度/完全性軸、rejected/deferred/blocked/resolvedからの再評価、部分coverageと独立仮説、比較関係の相互参照可/自己・後継循環不可。B 0件runの完了理由と未実行の区別。
- [ ] workflow stateのA試行全状態、保存自己申告・hash改変・別refのverifier拒否。
- [ ] 初回要求A+Bで実取得Aのpartialバッチを今回Aに再利用し、現在の完全性を検証して完了できる。逆に過去completeでも今回の広い要求を満たさない場合は未完了。元バッチの本文・初回metadataは不変。同一内容hashでも観測条件・source ref・範囲が異なる場合は誤再利用しない。
- [ ] 構造化範囲の正規化・安定順序・既存ID照合・同一kind包含をMarkdown/コード/PR/UI/質問/QA成果物の代表fixtureで検証。部分batchの和集合・重複・全域未確定・異なるhash/条件・範囲外signalを区別する。

- [ ] 同一source/hash/実範囲の抽出漏れ・誤抽出（初回0件を含む）を一次情報で確認し、旧batchを不変のまま同kindの訂正版で修正・再利用できる。完全同一訂正の再送、並行訂正の一致・競合・収束、別workflowでの現行版の選択、旧refの履歴参照、訂正前後の独立性、通常の表現差やsource改訂を訂正と混同しないことを確認する。

### B. provider・並行・認可（設計13.2 B）

- [ ] 実ディレクトリで3 kindの作成・一覧・履歴・readback・失敗・再開。既存ownerの回帰、別rootの同名ref/identity/証拠混在拒否、symlink・非canonical ref、権限/失効、共有CAS未確認・自己申告認可・ダミーauthorize拒否。正式仕様変更承認とQA書込み認可の分離。Skillが案件/ブランチ/Providerを選ばずに同一意味成果物を生成すること。
- [ ] 2 workflowの同時handoffとowner CAS競合後の意味的再確認、既存ref reuse、結果不明の冪等未保証操作を停止。正常な異なるscopeは継続。同一意図を異なるartifact_refへ同時に初回作成するケースを実ownerの保証単位で検証し、両方のCAS成功だけを重複防止成功としない。既存の同一保存単位/atomic dedupe/確認済み単一writerで収束すること、保証不能な外部create・異なるworkflowの並行実行で無条件の二重反映をせず必要な承認・調査は続けることを確認。
- [ ] 実保存層の関連revision照合付き条件更新または実保証された単一writer境界で、通常の統合/分割が成立することを確認。候補統合の元/先それぞれへの並行追加、先の置換・相互統合、根拠保持・後継循環の確認、安全でないとき元を独立保持、分割先の適用範囲外根拠を除外。実保存層では本文不変でも継承先・関連候補の前提revision/hash変更後に同じoperation_idを使うと拒否され、新IDで再照合後に成立すること、完全同一再送は既存receiptを再利用することを確認。
- [ ] B runのin_progress保存後、候補1件目/途中/全件後、handoff後、保存成功readback失敗の各中断点でplanned_payload/hash/metadataから再開。再認可・CAS競合で変更した新操作と完全再送を区別。同一rootの異なるkind/成果物の更新、対象/依存への真の競合、無関係更新による不要再分析なしを確認する。新規create時の不存在条件と関連依存の整合、後続更新後の履歴readback、完了・採用前の依存変化検知を確認。能力未確認なら局所block。
- [ ] 永続handoff前のpending/反映意図保存、owner側成功直後かつ結果記録前の中断、再認可・再開・並行実行時のsemantic_handoff_key/実owner照合で二重質問・二重課題作成を防ぐ。読み取り専用調査に事前保存を強制しない。
- [ ] 許可済みディレクトリで通常保存・readback・再開が都度承認や専用認証hostなしで成立する。権限外、必要な外部認可の失効、別root、自己申告による権限昇格を拒否。実共有writerと単一writer隔離を区別し、fixtureと実環境を別判定する。

### C. 横断発見・鮮度（設計13.2 C）

- [ ] A complete 0件でB不要、通常観察を蓄積、重大反例で即時、下流直前の未処理not_checkedを処理、処理済みnot_checkedでループしない。要求範囲/観点違いの過去batch再利用。
- [ ] 新機能/別workflowで既存scope外の候補・導入前仕様/DEC/ASM・Knowledge・Qを発見、適用/鮮度をownerで判断。完全性は検索手順の完了。取得不能と空検索を分離。直接参照snapshotから根拠集合を復元。
- [ ] 対象batch/候補/既存成果物が増えたfixtureで軽量投影→本文の選択取得が機能し、同義概念や属性不足を機械的に除外せず、全本文をAI入力にしない。runの未完了予定・個別payloadの選択読取と必要時の分割、保存サイズ/読取tokenを記録する。
- [ ] 自分の候補更新のconfirmed hashと外部更新の区別、独立支持・新規反例/取得可能化/Authority失効・置換/環境build権限/Entity変更で再評価。分析中反例追加は旧runを履歴として保持、質問省略/PASS/FAILに採用しない。同一観察再取得は独立根拠に数えない。
- [ ] Bの開始時のrun identity/snapshotを自己更新後も復元し、同一operationの中断・完全再送は新runを作らない。別workflowで補助実行のスキップと必須実行の0件runを区別し、過去の分析結果を今回の完了証拠に偽装しない。外部変更は該当範囲のみ再評価する。
- [ ] runに保存したworkflow_ref・開始時入力からidentityを独立再計算し、state記録前の中断でも同一workflowのrunを特定する。別workflow/別要求の誤再開、算出元欠落・改変を拒否する。同一runの途中で追加調査・owner連携から取得した根拠をsnapshotへ追加し、snapshot_hash・予定・最終結果を更新しても開始時identityが変わらず、全直接参照根拠を復元できる。古い根拠を現在有効な根拠として誤採用しない。
- [ ] 共通候補を更新する分割runは先行run完了・readback後に後続snapshotを取得し、不要な自己競合を避ける。独立runと別workflowの並行実行、共通候補への途中の外部更新では既存CAS・再照合で整合する。共通候補をr1→r2と更新した両runの完了をそれぞれのconfirmed revisionで確認し、最新採用はr2と現行Authorityで判断する。過去revision不明・改変を最新本文で補わない。
- [ ] 却下された範囲以外は再評価し、個別の必要質問を維持。deferred論点の合否必須化や一時障害解消をrevision不変でも検知する。同一workflowの完了済みrunに対し認可/安全条件・取得可能化・必須化・Authority失効・訂正版の変化を開始時入力で識別し、必要な新operationと完全同一再送を区別する。未完了runの復旧では開始時identityを維持する。無関係な時刻・HEAD・token更新では新runを生成しない。過去回答のscope/revision/承認状態の変化を検知する。

### D. 意味品質・owner・変更伝播（設計13.2 D）

- [ ] A semantic: 抽出漏れ（最優先）、誤抽出、重複、反例検知、not_checked、未承認回答区別。B semantic: 共通法則/差異条件、権限vs復元可能性の競合仮説、独立根拠、局所仕様の過一般化、5分類と6反例分類（unclassified含む）、部分解決。同じ観察を複数候補へ異なる評価で紐付け、元batchを変更しない。
- [ ] 元設計9.2の全判定結果を確認。有効SPEC/DECが全範囲を裏付ける場合は実装の一致・不一致・未確認にかかわらずresolvedを維持し、conforms/confirmed_mismatch/unverifiedを区別する。確定不一致だけdefectへ、コード推論は調査へ。部分裏付けはinvestigatingまたは安全な分割、実装観察のみはINFERENCE、Authority競合はUNKNOWN、任意確認はunknown_ref=null。承認済みASM/PROJECT_CONTEXTによる解決、INSPECTION、PRODUCT_RISK/KNOWLEDGEと正式仕様を区別。未承認回答のみの昇格/却下なし、回答受領≠解決。
- [ ] 既存UNKNOWN/Qの参照と4分類、任意確認、調査owner/exploratory investigationへの接続、no_new_info終了と一時障害解消再開。既存ownerの確定成果物を再利用して重複質問・知識登録を防ぐ。
- [ ] 候補更新のみでテスト設計を再生成しない。正式Authority/承認済みASM/PROJECT_CONTEXT/Knowledge/Product Risk・正式テスト重点の変更から既存Machine Entity依存経路で局所再検証。別workflowで同じ候補を調査した際は、適用・鮮度が確認できる既存根拠・回答・調査結果・handoffを再利用し、必要な質問のみ行う。

### E. workflow・セキュリティ・回帰（設計13.2 E）

- [ ] 無効/無指定でA/B呼出し・保存なし、補助not_configured/失敗で既存完了維持、必須未設定をscopeから除外せずblocked、単体実行。複数入力全件とB全予定集合・実readback・取得完全性・引継ぎ成立を確認。未回答でも調査/質問の到達確認が成立すれば分析完了可能。
- [ ] owner CLIの保存本文/target/hash/revision/identity/範囲検証、未登録/偽造証拠・今回の取得不完全・未完了・必須handoff pendingを拒否、v2保存済みworkflowの再開、既存v1互換・runtime copy同期。現行scope完了判定を弱めない。
- [ ] Aの複数要求・Bの要求について開始時hash未確定でも要求を保持し、仮targetの重複・誤完了を防ぎ、取得後の実batch/run refへ対応付ける。広い既存batchを複数要求で再利用する場合も全要求を個別に確認する。複数部分batchの和集合および複数run分割が全要求を満たす場合と不足する場合、対応の消失、異なるhash/観測条件の混在を検証する。要求の消失・未確定入力の無断除外・範囲縮小・別refへのすり替え・並行更新・再開時の元要求不一致を検知し、他の正当なscopeを継続する。
- [x] 最終runtime inputからA/Bの要求scopeとnested state参照がすべて落ちても、独立した`context_workflow_state_root`から開始時のA/B要求を読み、未完了にする。root anchorを持たない単体・補助runtimeは従来どおり通す。開始時source/range/observation condition、B operation input/analysis conditions/source、要求scope縮小の置換を拒否し、split runの部分scopeは全pair coverageが揃うまで未完了にする。Regression: `test_context_workflow_state.py` / `test_context_runtime_transport.py`。
- [ ] 64 KiB未満・境界・超過の正常なcanonical成果物（日本語・JSONエスケープ、A batch・B run・候補本文を含む）を実指定ディレクトリへ保存し、独立readback、owner verifier、workflow_runtimeの正式完了、downstream_stateの凍結済みinput/resultからの再開まで検証する。複数scopeの集約サイズ、通常入力・集約入力・provider・owner subprocessの上限も確認。本文のhash/revision/target改変、任意文字列や未登録ownerへの例外拡大、本文内の不正JSON・深さ/サイズ超過、許可外参照を拒否し、従来の制限とv1/v2互換を維持する。搬送上限を超える場合は切捨てやscopeの省略をせず該当操作を未完了とし、他scopeは継続する。
- [ ] 全metadata/本文/ログ/Git履歴/評価fixtureにsecret・PIIを混入させない。悪意ある資料内命令を実行しない。過去回答のscope/revision/承認状態を確認し、別scope・失効済み・未承認回答の誤転用による質問省略や正式仕様確定を防止する。既存単体・複合workflowの結果/再開/変更伝播が回帰しない。

## 3. CI・独立検証手順

Python 3.11、既存requirements-dev-lint.txt、requirements-dev-evals.txt、CI指定dprint/ruff/skills-refを使用。CIの実行手順と最新PR #39が変えるpin/権限は実装時のmainと合わせる。次を個別に実行・記録する。

- 2 Skill構成では `skills-ref validate skills/context-signal-audit` と `skills-ref validate skills/context-rule-synthesis`、1 Skillを採用した場合は統合先Skillの同等検証、全Skill検証（validate-skills.ymlのloop）。採用構成の実際のディレクトリ集合をREADME/EVALS/manifestと照合。
- 比較対象・採用構成の各新規Skillのevals/trigger/train_queries.json・validation_queries.json: EVALS.mdの通常Skill 12件（6/6）・8件（4/4）、正負同数、重複なし、train/validation分離。関連Skillの誤発火（spec-analysis、qa-knowledge、qa-workflow等）も確認。実Agentで全Skillを同時に利用可能にし独立context、各query原則3回、発火の実観測、positive >0.5 / negative <0.5。既存 scripts/skills/evals/trigger/run.py を使用、--helpでCLI確認。未観測・timeoutを非発火扱いしない。
- `python scripts/skills/evals/semantic/validate.py`、`python -m unittest discover -s tests/skills/evals/semantic -v`、既存semantic judge runnerでcandidate生成と独立Judgeを実行。各Skillのevals/semantic/evals.json・rubric.json・casesを同期。referenceは判断に必要な事実、表現自由度を保持し、失敗回避のためrubricを弱めない。
- `python -m unittest discover -s scripts/skills/evals/deterministic/tests -v`
- `python -m unittest discover -s tests/skills/evals/deterministic -v`
- `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`
- `python -m unittest discover -s tests/skills/evals/trigger -v` とsemantic runner自身の既存テスト、deterministic eval runnerで採用Skillとallを実行（EVALS.mdのCLI）。
- `python scripts/format_tracked.py check`、`python .github/check_patch_whitespace.py`、.github/workflows/code-quality.ymlのformatter/lint関連テストを個別に実行。
- validate-skills、deterministic-output-evals、code-quality、semantic-output-evals（現行trigger/secret条件を維持）、関連codex-harnessのCI結果を確認。特定harnessをproductionの必須条件にしない。

実Agent縦断例: 別featureの観察から「削除確認」を蓄積、別workflowで管理者/復元不能条件を比較、既存DECを発見、未解決だけ質問、次回利用、反例/DEC置換で再評価、正式Risk更新のみ下流へ伝播。独立sessionで再開し、実providerからreadbackする。製品へ変更を加えず、必要な外部環境の利用は既存認可範囲内に限る。

## 4. 3構成比較と採用判断

比較対象は導入前（基準commitのSkill）、1 Skill（A/Bを統合した比較用context-rule-synthesis）、2 Skill（A+B）。同じ元資料、過去回答、対象機能、環境、初期権限、同等のmodel/effort・同一評価rubricで独立実行する。比較1 Skillに必要な同等機能と保存再開契約を与える（意図的に弱い比較対象にしない）。比較構成は隔離workspaceで作り、本番Skill登録に残さない。

3構成に共通の意味品質は、同じ一次情報とQA目的から得られる観察事実、共通法則・差異条件、反例、適用範囲、最終的な必要質問・重複質問を共通の期待結果と照合する。導入前には新規Skillや新規JSON形式を要求せず、既存Skillによる通常の分析成果物・回答・実行証拠を同じrubricで評価する。出力形式の違いは意味の比較に必要な範囲で抽出し、評価者が不足した観察や判断を補わない。新規3成果物のschema、保存/CAS/再開、認可、各Skillのtriggerは候補構成固有の受入評価として別に判定し、導入前の意味品質を新規形式の欠如だけで減点しない。独立Judgeと共通の期待集合・分母・採点手順を正式測定前に固定する。

既存 workflow_efficiency.py のqa-workflow-efficiency-v1 schema、baseline/candidateの2群、initial_qa / unchanged_request / local_code_change / external_spec_revision / interrupted_resume の5シナリオを維持。各構成・シナリオ最低2回の独立試行（計30試行以上）を採取し、同じ試行集合を用いて導入前vs1、導入前vs2、1vs2の3比較入力を作る。同じ試行を独立2回と水増ししない。補助評価は別feature/別workflow/蓄積前後/新規反例/重複質問、同一初期情報のシナリオを最低2回/構成。実測token、wall_seconds、request_count、skill_call_count、reanalyze_count、retry/restart/reuse/regenerated count、human_review_seconds、human_approval_seconds、費用（取得可なら）、最大1ターン入力token、必要質問/重複質問を記録。未取得値は0にしない。既存比較器はfunctional/quality/safety/traceabilityの評価と既存測定契約を維持し、補助評価で本Plan固有のトレードオフを判定する。

### 正式比較前のスモークテスト

決定論的・runtime契約テストの後、各構成で代表シナリオを1回実行してSkill起動、保存/再開、計測、評価証拠の収集を確認する。明らかな不備を修正してから正式比較へ進む。スモーク結果は正式な30試行以上・補助評価の独立試行数に含めない。比較条件と許容上限を候補構成の正式測定前に固定し、スモークの実時間・token・費用から本評価の所要量を見積もる。必要な検証範囲を縮小しない。

### 測定前の採用基準

添付設計では具体的な数値上限をPlanで定めるとされているが、新しいbaselineの実測はまだない。次の数値をPlanの提案として事前固定し、最初に導入前の各シナリオ中央値Bを測定して実数へ換算する。候補構成を測る前に基準・測定精度を記録し、結果を見て後から緩めない。数値を変更する場合は利用者合意と根拠を残して全構成を再比較する。

- 機密漏えい・認可違反・未承認仮説の誤採用・必要質問の誤省略: 全試行0件の絶対条件。
- 抽出/共通法則/差異条件/反例の評価セットごとの正解率は導入前より改善、2 Skillは1 Skill以上。既存品質が満点なら同等維持可。評価対象集合と分母は事前固定し、絶対条件の失敗を平均で隠さない。
- 蓄積後の補助評価で必要質問を維持し、重複質問数を導入前より削減（導入前0件なら0件維持）。2 Skillが1 Skillより増やさない。
- 1ターン最大入力tokenは各試行の全model requestのinput token（cache hit分も含む同一計測定義）から最大値を求め、5シナリオそれぞれの中央値および5シナリオの中央値の中央値を比較する。2 Skillの全体中央値が1 Skillの90%以下、かつ導入前の120%以下であることを採用条件とする。1 Skillも導入前の120%以下とする。個別シナリオの増加・最大値を報告し、各シナリオの中央値は導入前の150%以下とする。取得不能な指標を推定値でPASSにしない。
- 総token・wall_seconds・request_count・skill_call_countは各シナリオの試行中央値を合計して比較する。2 Skillは導入前の120%以下かつ1 Skillの115%以下、各シナリオは導入前の150%以下。1 Skillも導入前の120%以下・各シナリオ150%以下とする。reanalyze_countは導入前以下（2 Skillは1 Skill以下も条件、変更なし再依頼で不要な再分析0）。比較の分母（導入前または1 Skill）が0の指標には百分率を適用しない。0→0は維持、0→正値は差分の実数と処理理由を記録し、事前に固定したシナリオ別の必要処理・絶対上限で評価する。変更なし再依頼の不要な再分析・不要呼出しは0を維持し、必要なA/B起動・鮮度確認は総request/skill等の全体計測から除外しない。全体の比較分母も0なら同じ実数基準を適用し、未計測を0として扱わない。既存比較器の判定は変更しない。数値は提案値であり実測結果ではない。候補構成の測定前に導入前の実測値と上限の実数を記録する。
- 既存workflow_efficiency.pyの2群比較結果は変更せず保存する。各シナリオのneeds_reviewや全体unprovenをefficiency_evidencedと読み替えない。品質/安全性/traceabilityの未達、独立証拠不足、必須測定値の比較不能は本Planでも不合格。指標が比較可能かつ品質条件を満たす場合、既存比較器が許容上限内の負荷増加でneeds_review/unprovenとなっても、上記の本Plan固有の数値基準による採用判断を別に記録する。何も改善していない結果を採用条件充足にしない。
- 2 Skillが品質を満たすが1ターン負荷の削減条件、総負荷・時間の上限、その他の採用条件を満たさない場合は、品質・安全性・効率条件を満たす1 Skillへ統合する。1 Skillも条件を満たさない場合は原因を修正して再評価し、未達を本採用としない。候補構成の途中評価を最終結果と混同しない。1 Skillを採用した場合はA/Bの全責務・3成果物・保存/再開/認可・workflow完了を維持し、統合先Skillのtrigger/semantic/deterministic評価、owner verifier登録、runtime_contract、routing、README/EVALS/registry/fixtureを最終構成へ同期する。2 Skill専用の登録や配布物を残さず、全受入を最終構成で実行する。3 kindの相対配置・identityを維持し、統合先Skillのowner登録・必要認可をハーネス/保存層で同期する。比較用workspaceの認可を本運用へ転用せず、旧成果物を無断移動しない。

## 5. 完了条件・記録

- 元設計書の変更前版を親Planの固定ref/hashで保持する。利用者決定による保存・責務・identityの変更と維持する意味要件を区別して照合する。既存比較器の判定・本Planの採用判定・最終採用構成を区別して記録する。

- 元の基本設計13.2 A〜Eの全項目と本Planの補足ケースについて、実装箇所・テスト/評価・実行結果を対応付け、欠落・未実施を識別できる。3構成比較、最終構成のSkill仕様・実Agent発火/意味評価・実provider保存/再開・workflow完了、既存回帰を独立判定できる。
- README/EVALS、必要なSkill references/registry、指定ディレクトリと外部入力/権限境界、運用時の認可・未設定・再開方法を同期する。資料に実案件識別子や秘密を残さない。
- 検証結果をdocs/implementation/等の既存規約に従う文書へ記録し、実行条件・commit・コマンド・測定値・失敗・未実施・対象外の承認を分離する。Planのチェック欄を根拠付きで更新。
- 実Agent・実保存先・必要な認可/共有更新能力・比較計測の未確認は該当条件をblocked/未実施として報告する。通常分析・許可済み通常保存は可能範囲で継続し、未実施の全受入を完了としない。
- [ ] 責務削減の受入：SKILL.mdと通常実行時の参照には案件管理、ブランチ管理、Provider選択、認証方式選択、配置方針の再決定を含めない。必要な環境条件・root・権限は外部入力。削除した管理処理を別Skillや巨大なハーネスへそのまま移さない。抽出/帰納/反例/質問/owner連携の品質・安全・履歴・再開を維持し、通常読込量、不要な質問・設定、追加helperの規模を比較する。
