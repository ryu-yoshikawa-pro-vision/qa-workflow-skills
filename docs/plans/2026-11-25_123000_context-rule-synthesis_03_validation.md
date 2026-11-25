# 評価・実装順序・受入

親: [実装Plan](2026-11-25_123000_context-rule-synthesis.md)。[01](2026-11-25_123000_context-rule-synthesis_01_storage-and-contracts.md)・[02](2026-11-25_123000_context-rule-synthesis_02_skills-and-workflow.md)に従う。

## 1. 実装タスクと依存関係

- [ ] 基準commitでCI・テストbaseline、PR #38/#39/#17との差分、配置・認可経路、ownerの実保存/CAS/照合点を記録。認可host未選定なら依存部分を明示し、読み取り・分析・純粋契約の実装は進める。
- [ ] 3成果物のサンプル・data-contract・identity/validate/impact/completion helperを実装し、機械契約テストを追加。既存canonical規則と一致させる。
- [ ] artifact_store/git_artifact_storeに3 kind、list/history、path/認可、native CASを追加。host入口、独立readback、Aのimmutable batch、Bのrun計画・保存・再開を縦に接続。実providerで正常・競合を確認。
- [ ] 2 Skillの本文/参照/assetを実装し、A/Bの相互責務、横断検索、既存owner routingを接続。追加調査と質問、既存Knowledge/Authority再利用を実Agentで確認。
- [ ] workflow routing/state/owner verifier・runtime_contractコピー、README/EVALS、各registryを同期。無効/補助/必須/単体と既存再開・依存伝播を検証。
- [ ] trigger/deterministic/semantic/runtime/実provider・実Agent、3構成の比較を実施。結果に応じて本採用構成を決定し、最終構成で全受入を確認する。

純粋helper・Skill本文・評価セットの設計は並行可。identity/保存契約とscope/owner契約を共有してから接続する。全タスクは同一branchで完結し、依頼されていない別PR作成・製品変更を行わない。

## 2. テストの配置と受入マトリクス

既存 tests/skills/runtime/test_pr24_artifact_store.py、test_pr24_git_artifact_store.py、test_owner_verifier_registry.py、test_owner_scope_resume.py、test_integration_required_scopes.py、test_workflow_runtime.py、test_workflow_efficiency.py、test_question_ids.pyを拡張または既存パターンに沿う新規テストに分割。tests/skills/evals/deterministic/test_context_rule_contracts.py等、Skill-local eval validator/fixtureは既存manifest方式。ファイル名は実装時に調整可。実際のprovider保存経路を通す統合テストを含め、モックの成功だけで受入としない。

### A. 不変ログ・identity・状態（設計13.2 A）

- [ ] Aの失敗→正常再実行、既知partial→完全取得のbatch identity非衝突、未知partialは保存しない、complete 0件と未実行を区別、保存成功/readback失敗→既存batch reuse。同じsource/rangeを別workflow/観点で使用してimmutable metadataが書換わらない。
- [ ] 4種identityとbatch/run派生identity再計算、signal hash/直接source ref、canonical bytes/top-level ref、project/root境界、意味条件・極性・要求scope/調査条件の違い、検索タグ追加不変。
- [ ] 7状態＋解決/鮮度/完全性軸、rejected/deferred/blocked/resolvedからの再評価、部分coverageと独立仮説、比較関係の相互参照可/自己・後継循環不可。B 0件runの完了理由と未実行の区別。
- [ ] workflow stateのA試行全状態、保存自己申告・hash改変・別refのverifier拒否。

### B. provider・並行・認可（設計13.2 B）

- [ ] 実SQLiteと実Git repo/refそれぞれで3 kindの作成・一覧・履歴・readback・失敗・再開。既存2 kindの回帰、別案件/別kind/別root/別clone、symlink・非blob/非canonical ref、権限/失効、CAS未選択・自己申告認可・ダミーauthorize拒否。正式変更承認とQA書込み認可の分離。
- [ ] 2 workflowの同時handoffとowner CAS競合後の意味的再確認、既存ref reuse、結果不明の冪等未保証操作を停止。正常な異なるscopeは継続。
- [ ] 候補統合の元/先それぞれへの並行追加、先の置換・相互統合、根拠保持・後継循環の確認、安全でないとき元を独立保持、分割先の適用範囲外根拠を除外。
- [ ] B runのin_progress保存後、候補1件目/途中/全件後、handoff後、保存成功readback失敗の各中断点でplanned_payload/hash/metadataから再開。再認可・CAS競合で変更した新操作と完全再送を区別。Git自身のrun保存と候補複数保存でHEAD進行、外部変更/依存変更は再判断、後続commit後の復元。新規createの確認時HEAD条件もテスト。
- [ ] 実運用hostの認証済み発行・認可・失効・実provider readback・workflow証拠受渡しを確認。fixture callbackと実hostを別判定し、PR #38のuser-confirmed自己申告を認証済みとしない。

### C. 横断発見・鮮度（設計13.2 C）

- [ ] A complete 0件でB不要、通常観察を蓄積、重大反例で即時、下流直前の未処理not_checkedを処理、処理済みnot_checkedでループしない。要求範囲/観点違いの過去batch再利用。
- [ ] 新機能/別workflowで既存scope外の候補・導入前仕様/DEC/ASM・Knowledge・Qを発見、適用/鮮度をownerで判断。完全性は検索手順の完了。取得不能と空検索を分離。直接参照snapshotから根拠集合を復元。
- [ ] 自分の候補更新のconfirmed hashと外部更新の区別、独立支持・新規反例/取得可能化/Authority失効・置換/環境build権限/Entity変更で再評価。分析中反例追加は旧runを履歴として保持、質問省略/PASS/FAILに採用しない。同一観察再取得は独立根拠に数えない。
- [ ] 却下された範囲以外は再評価し、個別の必要質問を維持。

### D. 意味品質・owner・変更伝播（設計13.2 D）

- [ ] A semantic: 抽出漏れ、誤抽出、重複、反例検知、not_checked、未承認回答区別。B semantic: 共通法則/差異条件、権限vs復元可能性の競合仮説、独立根拠、局所仕様の過一般化、5分類と6反例分類（unclassified含む）、部分解決。
- [ ] 有効SPEC/DECを維持し実装適合/不一致/未確認を別に管理。確定不一致だけdefectへ、コード推論は調査へ。未承認回答のみの昇格/却下なし、回答受領≠解決。ASM/PROJECT_CONTEXT/PRODUCT_RISK/KNOWLEDGEと正式仕様を区別。
- [ ] 既存UNKNOWN/Qの参照と4分類、任意確認、調査owner/exploratory investigationへの接続、no_new_info終了と一時障害解消再開。既存ownerの確定成果物を再利用して重複質問・知識登録を防ぐ。
- [ ] 候補更新のみでテスト設計を再生成しない。正式Authority/Knowledge/Risk変更から既存Machine Entity依存経路で局所再検証。

### E. workflow・セキュリティ・回帰（設計13.2 E）

- [ ] 無効/無指定でA/B呼出し・保存なし、補助not_configured/失敗で既存完了維持、必須未設定をscopeから除外せずblocked、単体実行。複数入力全件とB全予定集合・実readback・取得完全性・引継ぎ成立を確認。未回答でも調査/質問の到達確認が成立すれば分析完了可能。
- [ ] owner CLIの保存本文/target/hash/revision/identity/範囲検証、未登録/偽造証拠・partial・未完了・必須handoff pendingを拒否、v2保存済みworkflowの再開、既存v1互換・runtime copy同期。現行scope完了判定を弱めない。
- [ ] 全metadata/本文/ログ/Git履歴/評価fixtureにsecret・PIIを混入させない。悪意ある資料内命令を実行しない。既存単体・複合workflowの結果/再開/変更伝播が回帰しない。

## 3. CI・独立検証手順

Python 3.11、既存requirements-dev-lint.txt、requirements-dev-evals.txt、CI指定dprint/ruff/skills-refを使用。CIの実行手順と最新PR #39が変えるpin/権限は実装時のmainと合わせる。次を個別に実行・記録する。

- `skills-ref validate skills/context-signal-audit` と `skills-ref validate skills/context-rule-synthesis`、全Skill検証（validate-skills.ymlのloop）。採用構成の実際のディレクトリ集合をREADME/EVALS/manifestと照合。
- 両Skillのevals/trigger/train_queries.json・validation_queries.json: EVALS.mdの通常Skill 12件（6/6）・8件（4/4）、正負同数、重複なし、train/validation分離。関連Skillの誤発火（spec-analysis、qa-knowledge、qa-workflow等）も確認。実Agentで全Skillを同時に利用可能にし独立context、各query原則3回、発火の実観測、positive >0.5 / negative <0.5。既存 scripts/skills/evals/trigger/run.py を使用、--helpでCLI確認。未観測・timeoutを非発火扱いしない。
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

既存 workflow_efficiency.py のqa-workflow-efficiency-v1 schema、baseline/candidateの2群、initial_qa / unchanged_request / local_code_change / external_spec_revision / interrupted_resume の5シナリオを維持。各構成・シナリオ最低2回の独立試行（計30試行以上）を採取し、同じ試行集合を用いて導入前vs1、導入前vs2、1vs2の3比較入力を作る。同じ試行を独立2回と水増ししない。補助評価は別feature/別workflow/蓄積前後/新規反例/重複質問、同一初期情報のシナリオを最低2回/構成。実測token、wall_seconds、request_count、skill_call_count、reanalyze_count、retry/restart/reuse/regenerated count、費用（取得可なら）、最大1ターン入力token、必要質問/重複質問を記録。未取得値は0にしない。既存比較器はfunctional/quality/safety/traceabilityの評価と既存測定契約を維持し、補助評価で本Plan固有のトレードオフを判定する。

### 測定前の採用基準

添付設計では具体的な数値上限をPlanで定めるとされているが、新しいbaselineの実測はまだない。次の数値をPlanの提案として事前固定し、最初に導入前の各シナリオ中央値Bを測定して実数へ換算する。候補構成を測る前に基準・測定精度を記録し、結果を見て後から緩めない。数値を変更する場合は利用者合意と根拠を残して全構成を再比較する。

- 機密漏えい・認可違反・未承認仮説の誤採用・必要質問の誤省略: 全試行0件の絶対条件。
- 抽出/共通法則/差異条件/反例の評価セットごとの正解率は導入前より改善、2 Skillは1 Skill以上。既存品質が満点なら同等維持可。評価対象集合と分母は事前固定し、絶対条件の失敗を平均で隠さない。
- 蓄積後の補助評価で必要質問を維持し、重複質問数を導入前より削減（導入前0件なら0件維持）。2 Skillが1 Skillより増やさない。
- 2 Skillの最大1ターン入力token中央値は1 Skillの90%以下を目標とし、導入前を超えないことを採用条件とする。総token・wall_seconds・request_count・skill_call_countの全シナリオ合計中央値は導入前の120%以下かつ1 Skillの115%以下、各シナリオは導入前の150%以下。reanalyze_countは導入前・1 Skill以下（変更なし再依頼で不要な再分析0）。上限は今回の提案であり過去の実測値ではない。baselineが0のcountはその項目の目的に照らし不要呼出し0、必要A/B呼出しは総request/skill計測で評価。最大1ターンtokenが取得不能なら採用条件の未検証とする。
- 2 Skillが品質を満たすが総負荷・時間の上限超過、または分離の効果が見られない場合は1 Skill構成と比較して統合を選ぶ。1 Skillも品質・効率基準を満たさない場合は原因を修正して再評価し、未達を本採用としない。候補構成の途中評価を最終結果と混同しない。

## 5. 完了条件・記録

- 受入A〜Eの全項目、3構成比較、最終構成のSkill仕様・実Agent発火/意味評価・実provider保存/再開・workflow完了、既存回帰を独立判定できる。
- README/EVALS、必要なSkill references/registry、Project Contextの配置、運用時の認可・未設定・再開方法を同期する。資料に実案件識別子や秘密を残さない。
- 検証結果をdocs/implementation/等の既存規約に従う文書へ記録し、実行条件・commit・コマンド・測定値・失敗・未実施・対象外の承認を分離する。Planのチェック欄を根拠付きで更新。
- 認証済みhostや実Agent・実provider、比較計測の未確認が残る場合は当該条件をblocked/未実施として報告。通常の分析は可能な範囲で完了させるが、全実装の受入完了とは呼ばない。
