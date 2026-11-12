# QA成果物の保存・承認・集計・受入の共通契約

## 目的と適用範囲

この文書は[QA全工程の実装Plan](./2026-11-07_170134_qa-full-process-implementation.md)を補足する、保存先、権限、集計完全性、実Agent受入の詳細契約である。[Planインデックス](./2026-11-07_170134_qa-full-process-implementation_00_index.md)で担当を確認してから利用する。

対象はQA要求分析、アーキテクチャ、テスト管理、欠陥管理、統合報告、評価、および[非Web実装・実行](./2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)からの引継ぎ。製品機能一覧・item・共通条件候補の更新と製品CI接続は[開発連動QAのPlan](./2026-11-07_122247_development-qa-traceability.md)を正本とする。

共通の入力・検証条件を定める文書であり、同じデータを保存する新しい中央graph、共通mutable manifest、承認・集計の第二の正本は作らない。

## 1. 成果物保存と競合制御

### 保存前の確認

案件のProject Contextが示す保存先、権限と、参照先のowner／scopeを固定する。各書込みが必要とする操作と、providerが実際に保証する能力を事前に検証する。

- **新規成果物**：対象scopeと識別子が未登録であることを、保存先の原子的create-if-absent／同等の一意制約で保証する。
- **既存成果物更新**：保存前に取得したrevision tokenを条件として、保存先がatomic conditional write／transactionを提供することを確認する。`skills/qa-workflow/scripts/artifact_graph.py::state_update_decision()`は条件付き更新の必要性の判定であり、保存動作そのものではない。
- **履歴**：旧revisionの参照・再取得と、新revisionにおける変更前参照を保証する。今回のsnapshotだけで履歴を再現できない場合は、必要な履歴操作を停止する。
- **保存後**：書込み結果として返されたrevisionと独立再読込した内容・identityを照合する。衝突・古い応答・失敗後再試行を、単純な再書込みで成功扱いにしない。
- **複数成果物**：単一書込みのCASで、複数owner／複数ファイルの一括整合を保証したと見なさない。参照先revisionとcommit／snapshot境界を固定し、参照整合の確認が終わるまで下流のcurrentを成立させない。

### 実装するprovider接続の契約

Providerを案件別の選択肢に放置しない。実装時に使用する保存先をProject Contextまたは案件の正本で解決し、次の処理経路を実装・検証する。

1. `read_current(scope, ref)`相当：データと不透明なrevision・権限・取得可否を受け取る。
2. `create_if_absent(scope, artifact)`相当：保存先の原子的操作で一意な作成結果／既存競合を区別する。
3. `update_if_revision(scope, ref, expected_revision, artifact)`相当：providerの原子的条件付き更新を使い、競合／拒否／再試行可否を返す。
4. `read_revision(ref, revision)`相当：保持対象の過去revisionを取得できるか検証する。
5. `reread_after_write(ref)`相当：結果の内容、tokenと参照の一致を検証する。

関数名は論理I/Oの説明であり、新しい汎用storage frameworkのAPIを指定するものではない。既存`artifact_graph.py`、`workflow_runtime.py`と案件が既に利用している保存先のnative primitiveを先に調査し、必要なprovider固有の小さな接続だけを作る。

**受入条件**：少なくとも実装対象として宣言した保存先で、同一scope・同じexpected revisionを使う並行更新の片方だけが成功し、競合した側が旧currentを上書きしないことを実環境相当で示す。複数hostから同一成果物を更新する運用が必要なら、その共有保存先でも検証する。ローカルのSQLite transactionで確認した安全性を、GitHub／Drive等の遠隔保存先にも無条件に拡大しない。

保存先・権限・native CAS・過去revisionのどれかが必要なのに利用不能な場合は、**その保存・履歴操作をblocked**とする。読み取り済みで独立した分析は続行できる。無条件overwrite、read-compare-write、LLMの「更新成功」宣言、別場所への無承認退避で代用しない。

## 2. 承認・権限・外部Issueの更新

承認が必要な判断（QA対象外、要求・計画の確定、変更影響なし、リスク受容、外部Issueの更新など）は、承認文面だけでなく**信頼できるシステムから取得した権限と決定事実**を確認する。

- **承認対象**：操作種別、対象scope、成果物refとrevision／差分、対象build／source、例外・理由、承認時点、必要な有効期間、承認の失効条件を固定する。
- **承認主体**：案件の承認ポリシーへの参照・revisionと、信頼できるサービスが認証した操作者／許可された役割との対応を確認する。PRコメント、Issue本文、LLM生成の`approved`フィールドを単独の認可証拠にしない。
- **検証**：保存または外部更新の直前に対象revisionと権限を再確認する。後から承認内容／対象build／計画が変わった場合はその承認を自動再利用しない。
- **実行・監査**：許可済みの接続方式と最小権限で更新し、呼び出した操作、結果ref、取得したsource revision、失敗／競合、再試行・引継ぎを記録する。認証情報は本文や公開artifactに書かない。
- **未認可**：承認者が未設定、認証できない、対象が一致しない、権限不明なら該当更新を停止する。読み取り・提案・承認依頼は可能な範囲で実施できる。

### 本repositoryの既定承認方式（2026-11-12 利用者決定）

Git providerへ保存する案件では、次の手順を既定の承認方式とする。案件のProject Contextで別方式を合意した場合はそれに従う。

1. Agentは保存の前に、操作種別、scope、保存先ref／branch、期待する更新前revision、差分を利用者へ提示し、対話で明示的な同意を得る。
2. 同意後、保存先repositoryへのwrite権限を持つ利用者のGitHub認証済みアカウントで、通常pushする（force pushはしない）。保存先が更新前revisionから動いていればpushが拒否されるため、これを遠隔側の条件付き更新として扱う。
3. push後、GitHubのrepository activity API（`GET /repos/{owner}/{repo}/activity?ref=<ref>`）で、ref更新の実行者（`actor`）と前後SHA（`before`／`after`）を読み戻す。期待した更新前revision、保存したcommit、承認者として合意したアカウントがすべて一致した場合だけ、承認済み・保存済みとする。
4. **承認主体は、GitHubが認証したpush実行アカウント**とする。commitのauthor／committerは利用者側で任意に設定できるため、承認の証拠にしない。対話の同意記録だけ、またはLLMが生成した`approved`表記だけでは承認にしない。
5. activityの読み戻しに失敗した場合、実行者が一致しない場合、前後SHAが一致しない場合は、その保存を承認済みにせず、blockedとして再開条件を記録する。

### 欠陥管理との境界

`defect-management`が保管するのはQA側の欠陥候補・引継ぎ・外部Issue参照・修正確認依頼と結果だけ。外部Issueの正式status、優先度、担当、更新履歴の正本は案件のサービスに置く。

- 候補の重複照合は、同一元run／同一症状・scopeと外部Issueの検索を組み合わせる。検索結果だけで同一欠陥と断定しない。
- 登録・更新はサービスの認可・条件付き更新・冪等操作を利用できる範囲で行う。サービスに原子的な重複防止・条件付き更新がない場合、繰返し呼び出しで二重登録を起こし得る操作を自動再試行せず、照合と人間の再確認へ戻す。
- 外部Issueの状態変更通知だけで修正確認済みとしない。対象buildと有効TC／testwareを固定し、既存実行ownerへ再実行を依頼する。Regression対象の選定は`regression-testing`。
- 外部Issueへの書込み権限がない案件でも、QA側候補・読み取り・修正確認の依頼は利用可能な範囲で扱える。ただし外部更新の成功を表示しない。

## 3. 計画・モニタリング・統合報告の集計完全性

### 集計対象の母集団

`test-management`が所有する承認済み計画版、対象scope・期間、test level/type、対象build・環境、要求run／TC／testware、開始／終了基準、および想定source ownerの一覧を、集計の**計画上の母集団**とする。

- 対象の一覧には、一般TC、Playwright E2E、Regression、Exploration、API／バッチ／コンポーネント、非機能測定、**製品要求・設計・コードの静的レビュー／静的解析**、UI/UX・WCAG、正式Issue情報のうち対象となるものを含める。用途により件数単位（TC、logical primary、resolved TestCase、attempt、session、test item、欠陥候補等）を分ける。
- 各source ownerから実際に取得した範囲、snapshot／source revision、pagination／query filter／取得可否、実行状態、取得時点と出力したresult refsを記録する。予定にあるownerが欠落した場合は0件とみなさず、取得不完全にする。
- Reportのみを直接要求され、計画がない場合は明示された対象scopeと許可されたdiscovery rootsから母集団を作る。不明な母集団を自動的に「すべて発見済み」とせず、全体率と終了判定は`未確定`にする。
- 別build・別環境・別期間のrunは対象条件に適合するものだけ集計する。異なる試行・retry・選択Run・同一testwareを重複加算しない。
- テストの実開始と判定結果、報告の生成と承認、進捗率とPASS率は別の指標。実行結果のraw値を書換えず、集計時の読み取り単位を明示する。

### 集計判定と出力

`test-reporting`は予定対象と取得結果を照合し、対象の完全取得、source参照currentness、観測可能な元結果、cleanup、各終了基準について**独立に**閉鎖性を判定する。必要なsourceが欠ける場合は、取得済み部分の集計と未取得対象・不足数／範囲を同時に出し、全体の100%や全PASSを出さない。

`test-management`は計画対実績、予実差、プロジェクトリスク、是正処置の正本。報告側は参照してスナップショットを作り、計画を更新しない。`test-evaluation`は同じ測定条件を再解釈し、QA活動・改善の評価をするが、元実績や正式テスト結果を改変しない。

**受入シナリオ**：

- 計画にAPI実行が1件あるが、Playwright E2Eだけ取得できた場合はAPI実行を未取得とし、全体PASS率・完了判定を確定しない。計画された静的レビューの対象が5件で取得したFindingが0件でも、5件すべてのレビュー完了と取得完全性がない限り「指摘0件・完了」としない。
- 同じTCの複数retryや同じE2E runの`logical primary`と`attempt`を1つの分母へ二重加算しない。非E2Eではテストファイル・suite・個別テスト・TC・testware refを別単位とし、ファイルの成功から個別テストの実行を推定しない。
- 一部pagination失敗、read権限不足、外部Issueのstale read、終了条件の欠落、対象外build、過去revision、計画変更後の旧reportで、`complete`と終了判定を正しく分離する。
- sourceが0件で計画上も対象なしという正当な空集合と、sourceが取得できないため0件に見える状態を区別する。

## 複数成果物の途中停止・再開

[継続workflow・E2E受入Plan](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)の入口・source snapshotと一致する場合にだけ、関連する複数のowner成果物を組み合わせてcurrentと判定する。

1. `feature-analysis`→仕様／Risk→TR/TCN/CI/TC→実行→`test-reporting`の各書込みはowner別のnative CASで確定する。**単体のCASだけで全成果物の一括commitが成立したと扱わない**。
2. 中断直前の記録、全ownerの実保存ref・revision・content hash・入力source revision・依存関係を読戻し、**保存確定／保存状態不明／未開始**を分ける。保存済みでも依存する上流が旧版なら新しい横断報告をcurrentにしない。
3. 通信切断・crash後の再開で、status不明の副作用（Issue書込み、testware編集、実runnerの試行やcleanup）を無条件に再実行しない。ownerの元証跡・同一操作ID・現在状態を照合し、安全に再開可能な操作だけ進める。
4. 同一revisionの並行更新、PRのrebase、マージ後の基準変更、外部文書のみの改版、計画承認の失効、保存後の読戻し不一致、旧commit結果の遅延到着を独立fixtureと実保存先で検証する。旧currentを上書きせず、必要な範囲に`要再検証`／`blocked`と担当・再開条件を記録する。
5. 新しい中央mutable manifestや汎用storage frameworkを作ることを前提としない。既存`qa-workflow`のsource currentness／state／resume、各Skillの履歴契約と実保存先の原子操作を組み合わせて検証する。

### 操作開始前の永続的な記録と再開判定

成果物保存、外部Issue更新、testwareの書込み、実runnerの副作用を伴う操作は、**実操作の前に**既存workflow stateまたは当該ownerの永続化先へ、同じ処理を特定できる操作記録を確定する。新しい横断台帳や第二のartifact graphは作らない。

1. 記録には、workflow／owner／scope、操作の種類、対象ref／保存先、入力source・成果物revision、期待する更新前revision、必要な承認・許可範囲、安定したoperation identity、開始・実行／保存確認・再開条件を含める。秘密情報の実値は記録しない。
2. 作成前に`artifact_graph.py::claim_mutable_operation()`等の既存claim規則と保存先の原子的create-if-absent／CASを利用する。**同一operation identityを再受付した場合、前回の実保存状態を照合せず同じ副作用を再実行しない**。
3. 保存処理が成功して応答が消えた場合も、再起動後に対象ref／revision／内容hash・source依存を実保存先から照合して「保存確定」「競合」「状態不明」を判定する。保存先の照会権限不足を「未保存」と推測しない。
4. 実runner／外部API等で開始済み操作の結果が不明な場合、元のoperation identity、実開始・副作用・cleanupの証拠を持つownerへ戻し、**新しいattemptによる再実行が許可されるまでblocked**にする。
5. 複数owner更新は、各個別成果物の確認・依存revision照合が完了して初めて横断結果をcurrentとする。部分保存後に中断した場合は保存済み結果を再利用し、未保存または古い部分だけ再処理する。

### 実行後の記録を確定してから引き継ぐ

実行ownerはpreflight・実開始・各attemptの元結果・終了状態・診断・cleanupを**別々の事実**として記録する。実runnerが終了しただけで、結果の参照とcleanup状態が永続化されたとみなさない。

- runner実行後、元結果と結果保存先のref／revision・readbackを確認し、欠落や不一致を保存未完了として引き継ぐ。
- cleanupの実操作が完了していてもcleanup結果の保存が未確認なら、**実際にcleanupが済んだという証拠は残し**、workflowの引継ぎ・完了のみ未確定とする。
- 結果保存中・cleanup記録中・元runner終了直後の中断は、元のrun／attempt identityを再照会して復旧する。実行済みのテストを回復のために無条件に再実行しない。
- `test-reporting`／`regression-testing`／下流Skillは、実測値だけでなく元runの確認済み保存revision・結果最終確定・必要cleanupを照合する。

この契約を[workflow runtime・Regression契約](./2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)の別セッション再開と、[テスト実行・品質契約](./2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)の実行ownerに適用する。

## 製品CIとの成果物受渡し

ローカルAgentが生成した解析成果物を製品CIが取得する**方式は未決定**。案件ごとの実装時選定であり、Git commit・CI artifact・Drive等をこの共通契約の標準経路として固定しない。

Skillが提供するのはsource snapshot、成果物refs・content hash、承認revision、依存・欠落・currentness、決定論的に検証できる入力／出力まで。Agentを起動する指示・監視・通知・定期照合はSkill外。製品CIへ実接続する段階では、選択された受渡し経路の認証／権限・保存後readback・source／artifact／build一致・改ざん拒否・欠落時のfailを実証する。

未選定状態では実製品CIの受入を`blocked`とし、既に受渡し経路が設定されたCIで必須成果物が欠落／旧版の場合はfailする。未接続の状態を単にテスト対象外へ移して全体完了を宣言しない。

## 4. 実Agent受入・独立基準データ

工程ごとに入力fixture、独立した期待成果物、禁止される誤判定、評価方法、source revision、必要な実行環境を定義する。候補Agentの出力から正解や分母を作らない。

**代表ケースと期待結果**：

1. **要求分析・アーキテクチャ**：同一項目がコンポーネント／API／システムの複数レベルで対象。案件の明示指定／承認済みアーキテクチャ割当／`test-analysis`の既定システムテストの優先を検証し、後から割当が変わった場合は依存するTR／設計のみ再確認する。
2. **計画**：承認前案を承認済み扱いしない。計画revision変更後は旧承認で新計画を確定しない。計画対実績は未取得の実行を0件実施と混同しない。
3. **欠陥**：FAILだが原因未確定、既存Issue重複、外部更新権限なし、修正確認前のIssue close、旧buildでの誤再実行を検出する。
4. **集計**：TC／retry／Regression／E2E／探索／非Web実行の異なる単位を区別し、欠落source、部分取得、旧revision、異なるbuildによる偽100%を拒否する。
5. **評価**：作業時間だけが短縮したケースでは品質改善も達成したと推論せず、効果未測定と引継ぎ未完了を別々に残す。
6. **並行性とセキュリティ**：同一revisionの競合更新、旧承認、未信頼Issue本文に含まれる指示、外部更新の重複要求、保存失敗と再試行、秘密情報の混入を検証する。

評価は次を分ける。

- **形式／決定論的契約**：必須ref、ID、scope、revision、分母、数値・状態、競合・権限不足の機械検証。
- **意味品質**：根拠のある対象抽出、責務境界、テストレベル／欠陥の判断、誤った承認・期待結果を独立基準データと人間による確認で評価。
- **実Agent実行**：現行Skillと新Skillを実クライアントから起動し、正しいrouting・tool呼出し・保存・block・resume、意図しない外部操作の不在を証拠付きで確認。
- **実接続**：対象製品・保存先・外部Issue・非Web runner／計測ツールについて、宣言した環境での入出力・失敗・回復・権限を確認。利用不能な環境をfixture成功で代替しない。

受入には成功数の固定目標を先に置かず、[継続workflow・E2E受入Plan](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)のS1〜S17と各責務の重要な異常系・誤判定を含む独立caseを必要な範囲で追加する。**全current Skillを同じAgent上で利用可能として発火・競合を試験し、特定モデル／CLI／評価ハーネスを固定しない**。実施済み／未実施／SKIP／失敗を個別に示し、未実施項目を完了へ合算しない。

## 5. 検証と完了条件

- 対象として宣言した各保存先について、native create-if-absent、同時更新CAS、履歴再取得、独立再読込、権限拒否、失敗後の復旧を検証する。providerが未確定なら永続更新機能は未完成であり、全体の実装完了にしない。
- 承認対象のscope／revision／権限主体と失効を検証し、外部Issueへ無許可書込み・二重登録・改ざんされた承認の使用が発生しない。
- 計画上の母集団とsource inventoryの取得完全性、raw単位、retry、0件とunknown、別build、source遅延／欠落を検証する。
- 独立した期待結果を用いた実Agent経路、実runner／保存先／外部Issue接続、関連既存runtime・CI・移行・部分再実行を検証する。実行完了後・結果保存中・cleanup保存後の中断と再開、異なるセッションでのreadbackを必須ケースとする。
- 親Planと非Web実装・実行Planの全完了条件を満たした場合だけ、QA全工程の追加責務を完了と判定する。
