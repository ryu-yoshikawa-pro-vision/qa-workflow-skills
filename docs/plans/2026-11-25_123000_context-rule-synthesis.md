# 横断的法則性抽出・コンテキスト補完 実装Plan

- 基準: main `a37b15508dadd17ac0228ac896badb71d6a8f2c7`（2026-11-25確認、添付「QAワークフロー 詳細設計書：横断的法則性抽出・コンテキスト補完（基本設計確定版）」と一致）
- 実装branch: `feat/context-rule-synthesis`
- 状態（2026-11-26）: 実装commit `e5643535`と検証記録/Plan同期commit `480033d2`をPR #40へpushし、両commitでValidate Agent Skills、Deterministic Output Evals、Semantic Output Evals、Code Quality、Codex Harnessの5 workflowすべてがsuccess。通常root保存・list/read/history・条件付き更新、独立readback、A/B stateの永続化・再開を既存filesystem操作とSQLite providerへ接続し、隔離rootで実テストした。受入全体は未完了。実運用rootと共有writer/外部owner接続は未指定・未確認だが、通常保存に専用認証hostは不要で、これを理由にローカル作業を止めない。正式trigger、実Agent縦断、独立Judge、3構成実測は未実施。Codex等の外部評価サービスへrepository由来データを送る許可範囲を確認中のため、当該評価は保留。実績と13.2対応は[PR #40検証記録](../implementation/pr40/verification.md)を参照し、残件を完了扱いしない。
- [元の基本設計書](2026-11-25_123000_context-rule-synthesis_design.md)の1〜14章を対象とする。付録は保存のみで実装対象外。添付原文は[保存時commitの文書](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/799b776b4708a3b97aa6a6fc018212d00ac15d09/docs/plans/2026-11-25_123000_context-rule-synthesis_design.md)（SHA-256: 727e784d2faf8741a2f5a199515c060d3abb174658296ac3dbb992ac018270d0、Git blob: ec436defa085308b90cd7688d375c5730ecb55c5）で保持する。直前の書式整形版（Git blob: c642c87948acf8e8da0f756f849761d596b17de3）は履歴に保持する。今回の利用者決定により保存・責務・identityに関する設計を変更した。原文・旧設計は履歴参照とし、変更後の基本設計と詳細Planを実装の正本とする。詳細な例・表・JSON例も実装・検証の参照先とする。
- 本Planは基本設計の具体化。以下のレビューで合意した具体化は原文の対応箇所より優先する。他の設計要件は省略しない。

## 利用者決定：責務の適正化（最優先）

2026-11-25 利用者決定：成果物は指定ディレクトリで統一管理する。Skillに案件識別・探索・切替・保存先決定・Provider選択・ブランチ管理・認証方式選択を持たせない。必要な案件境界・root・実行条件・権限はハーネスが入力として提供し、不要な管理は移管せず削除する。SkillはQAの意味判断、成果物の意味・形式・相対配置、必要な質問・引継ぎに集中する。Helperは決定論的識別・検証・保存を担当する。ハーネスの特定製品への依存、新しい汎用管理基盤、既存案件の移行は本PRの対象外。

既存の安全性、正式仕様のAuthority、履歴、根拠、実readback、冪等性、scope完全性は維持する。実保存境界の能力不足は局所blockedとし、分析そのものは可能な範囲で継続する。新規3成果物の正本は指定ディレクトリ内のcanonical JSONとし、案件IDを意味的identityや本文必須fieldにしない。別rootの同一相対refは同一成果物とみなさない。保存先をまたぐ共有・移行は対象外。

## 確定した共通前提（Q01〜08）

[共通原則](../reference/qa-skill-design-principles.md) PRN-01〜08・Q01〜08を確定前提とする。許可済みroot内の通常保存は都度承認不要、内容承認・破壊的変更・必要な外部操作は別。特定ハーネスは必須でなく、直接利用でも必要入力・権限があれば実行する。通常保存に専用認証基盤・独自CAS・分散lockを一律要求しない。実際の共有/競合条件に応じて必要な保証だけ確認する。既存ownerの正式判断・安全制約は維持する。

新規3成果物のcanonical JSONは現行verifier・不変batch・機械的再開との整合から採用候補として維持する。人間向けの短い要約を返し二重正本を作らない。より単純な形式で同じ品質・再開・検証を満たせる場合のみ根拠を記録し比較する。処理完了・質問前・回答後・中断・引継ぎの必要分を自動保存する。対話質問の提示と永続的handoffを区別する。

## 目的

複数機能・セッション・workflowの観察から暗黙ルール、不変条件、差異条件を発見し、次回のQAで既存知識・回答・根拠を横断利用する。追加調査を先に行い、必要な質問は残しながら重複質問と読み込み負荷を減らす。候補は第二のAuthorityにしない。

## Planの構成

- [01 保存・認可・データ契約](2026-11-25_123000_context-rule-synthesis_01_storage-and-contracts.md): ディレクトリ契約、identity、保存・中断再開、並行整合。
- [02 Skill・workflow・owner連携](2026-11-25_123000_context-rule-synthesis_02_skills-and-workflow.md): A/Bの責務、横断発見、帰納、質問、完了判定。
- [03 評価・実装順序・受入](2026-11-25_123000_context-rule-synthesis_03_validation.md): 検証マトリクス、3構成比較、完了条件。

詳細文書は各担当領域の実装契約。本書は共通方針と依存順序の正本。個々の関数名・ファイル分割は実装で調整してよい。根拠のある変更はPlanへ理由を記録し、目的・必須要件は無断で縮小しない。

## 原設計からの具体化・変更

- 取得完全性は初回保存と今回要求で分離。構造化範囲と複数batchの照合、元要求と実成果物scopeの対応を定義する。鮮度フラグはrevalidation_requiredに統一。確認済みの抽出漏れ・誤抽出は同じkindの不変訂正版で補正し、旧版は履歴として保持する（01 §2・3、02 §4・5）。
- 成果物の分類・保存・発見は指定root配下のkindディレクトリで統一。旧kind別branch案と案件単位のSkill判断は撤回する。保存層の実revisionと対象/依存内容hashは分離し、安全な条件付き更新・create-if-absent・履歴・独立readbackを要求する。別成果物間の原子性を推測しない。再送fingerprintの変更は新operation_id、handoffは実ownerの一意性保証を確認（01 §1・4、02 §3）。
- Bはworkflow_refとidentity算出元の開始時入力をrunに保持する。実行中に取得した根拠はsnapshotへ追加し、開始時入力と分ける。本文不変での再評価は実際の関連条件・取得状態の変化を開始時入力に含め、過去の実行完了は当時のrevision、現在の採用は最新根拠で検証する。永続的handoffの前に反映意図を記録し、共通候補を更新する分割runは直列を基本とする。全文planned_payloadは復元用に維持し、helperによる選択読取・必要時の範囲分割で負荷を抑える（01 §2〜4、02 §3・4）。
- 許可root・実行権限・必要保存能力を既存環境で確認し、通常保存は自動化する。専用認証hostを一律の着手条件にしない。正式仕様判断と必要な外部操作は既存ownerの承認/認可に従う。64 KiBのJSON文字列上限と本文搬送・再開の整合を実装初期に検証し必要経路だけ修正（01 §1、02 §5、03 §1・2）。
- 効率評価は導入前比120%の最大入力token上限と2 Skillの対1 Skill削減を両立させ、既存比較器の判定と本Planの採用判定を分離する。正式比較前にスモークテストを行う。基準値0の指標は実数で扱い、意味品質は共通の期待結果で比較する。1 Skill採用時はkindの相対配置を維持しowner登録・認可を必要範囲で同期する（01 §1、03 §4）。

## 設計要件と検証の対応

以下の節番号は[元の基本設計書](2026-11-25_123000_context-rule-synthesis_design.md)の番号。設計書と対応するPlanを併読し、設計13.2の全項目をPlan 03の受入結果へ対応付ける。Planの要約だけを理由に詳細な例外・状態・入力フィールドを省略しない。

- 1.1〜1.3、2、3.1〜3.2: 親Planの目的・対象・方針、03 §4・5（構成比較と対象外の維持）。
- 4.1〜4.2、5.1〜5.3: 02 §1〜5、01 §2・3、03 A・C・E（入出力、起動、モード、要求集合・完了）。
- 6の全11手順: 02 §3、01 §3・4、03 C・D（取得、独立性、複数仮説、5分類、意味条件、Authority、反例6分類、過去回答・却下、owner分類、調査、保存）。
- 7.1〜7.5: 01 §2〜4、02 §5、03 A・B・E（4種identity、3成果物、完全性、7状態、関係、予定・readback）。
- 8.1〜8.4: 01 §1・4、02 §3・4、03 B・C・D・E（4層経路、共有CAS、再開、2段階検索、新機能、変更伝播）。
- 9.1〜9.2: 02 §3の調査ルーティングと全判定結果、01 §3・4、03 B・D（no_new_info、再開、owner・質問・冪等性）。
- 10、11: 親Planの対象・順序、01 §4、02 §1・5、03 §1〜3（変更範囲、全異常系、並行処理と再開）。
- 12: 01 §1・5、02 §3〜5、03 B・D・E（認可、全データ保護、回答転用）。
- 13.1〜13.3: 03 §2〜5（A〜E全チェック、CI、3構成、補助評価、採用条件）。
- 14: 親Planの着手条件、01 §1、02 §3、03 §4（確定済みの契約と実環境依存の確認を区別）。
- 付録: 別課題。今回の実装・評価に追加しない。

## 現行実装の確認

- [artifact_store.py](../../skills/project-context/scripts/artifact_store.py): LocalArtifactStoreのKINDSはproject-context/feature-inventory。SQLiteの履歴・current・receipt、BEGIN IMMEDIATE、authorize、revision CASを再利用可能。再送fingerprintにexpected revisionとmetadataを含む。
- [git_artifact_store.py](../../skills/project-context/scripts/git_artifact_store.py): _identityにも独立した2種制限。_assert_ownerはpathの最終変更commitの件名・案件trailerを検査。_head / writeはbranch HEAD、update-refの旧SHAをnative CASに使う。same_operationはHEADのmessageを見るため後続commit後は独立readbackが必要。現行providerはローカルrefであり遠隔共有CASを自動保証しない。
- [project_context.py](../../skills/project-context/scripts/project_context.py): persist_preparedはproject-context専用、CLIのhandleには認証済み保存入口がない。prepare_placementでSection 12/14の方針を扱い、外部の信頼済み認可が必要。
- [owner_verifiers.py](../../skills/qa-workflow/scripts/owner_verifiers.py): _stored_owner_artifactはcanonical JSON文字列、hash、target、owner CLIのvalidate/validate_readbackを照合する。providerを自ら読まない。[runtime_contract.py](../../skills/qa-workflow/scripts/runtime_contract.py)のOWNER_VERIFIED_SKILLSと登録集合が一致する。workflow_runtimeのscopeはskill/target/execution_rangeで識別し、非runtime-v2 ownerのcurrent_structure_stateはnull。downstream_stateの再開契約も維持。
- [runtime_contract.py](../../skills/qa-workflow/scripts/runtime_contract.py)のstrict_loadsは通常入力2 MiB、集約入力16 MiB、個別JSON文字列64 KiB。verify_runtime_evidenceの例外はartifact_markdown/previous_artifact_markdownのトップレベル文字列のみ。downstream_state.pyの_check_treeにも64 KiB制限がある。両保存providerの本文上限は16 MiB、owner_verifiers._run_ownerの出力上限は8 MiB。保存できるサイズと完了・再開で搬送できるサイズは異なる（02 §5）。
- [qa-workflow](../../skills/qa-workflow/SKILL.md)は要求集合v2、局所blocked、既存入力revision再利用を持つ。補助工程は要求scopeに加えない。workflow stateはworkflow_refごとの既存envelope、local exact-content tokenだけではCASではない。
- [knowledge_runtime.py](../../skills/qa-knowledge/scripts/knowledge_runtime.py)にはread_root_entries、scan_knowledge_root、lookup/lookup_root、compare_currentness、plan_create/update/replacementがある。lookupはscope一致が必要。既存Knowledgeの適用規則は緩めない。
- [workflow_efficiency.py](../../scripts/skills/evals/workflow_efficiency.py)は5シナリオ、2群のschema。最大1ターン入力token・重複質問の計測は別評価にする。

## 並行PRと認可の着手条件

[PR #38](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/38)（確認head d7b691b40fefe3bf84ccd7c57d4b5a2fbb5b89d7）のuser-confirmed保存mode、artifact_host.py、既存ownerの保存契約を確認する。これは既存実装の調査対象であり、旧kind別branch構造を新Skillへ継承しない。user-confirmedは呼出し側の確認記録であって認証ではない。既存ownerを無断変更せず、接続に必要な場合だけ境界で変換する。PR #39のCI最小権限・formatter規約、PR #17の評価契約も最新統合結果で確認する。

通常のローカル保存は許可済みroot・実行権限・既存ファイル操作で成立させる。共有更新・外部操作など必要時のみ追加保証を実環境で確認し未確認は該当操作のみblock。user-confirmed自己申告やfixture callbackを実認証の証拠にしないが、通常保存に認証済みhost専用接続を必須としない。分析・対話質問・構造検証・評価は継続可。既存ownerの正式仕様変更承認は維持する。

## 対象・変更境界

新規2 Skill（context-signal-audit、context-rule-synthesis）と3成果物、指定ディレクトリへの最小保存接続、qa-workflowのrouting・state・owner verifier、必要なownerとの接続、README/EVALS・評価・回帰検証を対象とする。添付設計の比較に基づき1 Skillとの実測を行い、品質・効率条件で最終構成を決める。評価用の1 Skill構成は本番3つ目のSkillとして配布しない。

対象外: 新Authority、DEC/ASMの別正本、別DB・embedding・中央index・独自CAS・分散transaction・全体lock・常駐監視・特定harness強制・rootを越える共有・既存保存方式の全面移行・案件管理・ブランチ管理、別課題の専門テストSkill、既存製品の変更。

## 実装方針

- AIには観察・仮説・根拠の意味評価・表現ゆれ・調査要否・owner判断を任せる。語彙の固定辞書、強制的な仮説件数、全成果物の毎回読み込み、固定retry数、機械的な信頼度点数を新設しない。
- helperはidentity、保存構造、範囲、CAS、readback、鮮度差分など機械的に確定できる項目を担当。通常入力の不足は未確認として扱い、影響部分のみ停止する。権限境界・根拠消失・必須完了の虚偽は許容しない。
- 既存ownerと標準ライブラリを優先。Skill単体配布を維持し、production helperはevalsに置かない。必要な依存Skillと非接続時の動作を明記する。全Skillへの重複規則追加は行わない。
- 無指定で無効。新規3 kindや不要なstate欄を事前作成しない。既存形式・配置を無断移行しない。rootや機能有効化は外部から渡される条件で解決する。

## 実装順序

1. 最新差分、指定root・認可/保存境界、既存CI baseline、ownerの意味的冪等照合を確認。既存runtimeによる仮target・複数batch・再開、64 KiB超の成果物本文の受渡しとサイズ上限の検証を最初に行い、比較条件を事前固定。
2. 3成果物のcanonical契約、identity、純粋検証・fixture、指定ディレクトリの列挙/履歴/条件付き保存入口を実装。既存helperを優先し、能力未確認なら接続部分のみ保留。
3. Aの抽出・不変バッチとworkflow試行state、Bの検索・帰納・候補/run保存・再開を接続。
4. 既存ownerへの調査/質問/確定知識のhandoff、鮮度・変更伝播、workflowの補助/必須/単体実行・verifierを接続。
5. 評価・ドキュメント・実provider/Agent受入・全回帰、各構成のスモークテスト後に3構成の正式比較を実施。結果による構成変更も本branchで検証する。

03の受入条件すべてを独立に確認する。計測不能・未接続・失敗はPASSにしない。既存の未達はbaselineと今回の差を区別して報告する。現時点では独立helper/owner/transport契約・Skill文書と評価fixture・一部runtime変更を実装し、host依存・実Agent・Judge・構成比較は未完了。最新結果を検証記録に同期し、全受入が終わるまで本Planを完了にしない。
