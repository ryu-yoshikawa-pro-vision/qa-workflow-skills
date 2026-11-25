# 横断的法則性抽出・コンテキスト補完 実装Plan

- 基準: main `a37b15508dadd17ac0228ac896badb71d6a8f2c7`（2026-11-25確認、添付「QAワークフロー 詳細設計書：横断的法則性抽出・コンテキスト補完（基本設計確定版）」と一致）
- 実装branch: `feat/context-rule-synthesis`
- 状態: Plan作成済み・実装未着手。実装と受入を同一branchで行う。
- 添付設計の1〜14章を対象とし、付録の別課題は対象外。

## 目的

複数機能・セッション・workflowの観察から暗黙ルール、不変条件、差異条件を発見し、次回のQAで既存知識・回答・根拠を横断利用する。追加調査を先に行い、必要な質問は残しながら重複質問と読み込み負荷を減らす。候補は第二のAuthorityにしない。

## Planの構成

- [01 保存・認可・データ契約](2026-11-25_123000_context-rule-synthesis_01_storage-and-contracts.md): provider、identity、保存・中断再開、並行整合。
- [02 Skill・workflow・owner連携](2026-11-25_123000_context-rule-synthesis_02_skills-and-workflow.md): A/Bの責務、横断発見、帰納、質問、完了判定。
- [03 評価・実装順序・受入](2026-11-25_123000_context-rule-synthesis_03_validation.md): 検証マトリクス、3構成比較、完了条件。

詳細文書は各担当領域の実装契約。本書は共通方針と依存順序の正本。個々の関数名・ファイル分割は実装で調整してよい。根拠のある変更はPlanへ理由を記録し、目的・必須要件は無断で縮小しない。

## 現行実装の確認

- [artifact_store.py](../../skills/project-context/scripts/artifact_store.py): LocalArtifactStoreのKINDSはproject-context/feature-inventory。SQLiteの履歴・current・receipt、BEGIN IMMEDIATE、authorize、revision CASを再利用可能。再送fingerprintにexpected revisionとmetadataを含む。
- [git_artifact_store.py](../../skills/project-context/scripts/git_artifact_store.py): _identityにも独立した2種制限。_assert_ownerはpathの最終変更commitの件名・案件trailerを検査。_head / writeはbranch HEAD、update-refの旧SHAをnative CASに使う。same_operationはHEADのmessageを見るため後続commit後は独立readbackが必要。現行providerはローカルrefであり遠隔共有CASを自動保証しない。
- [project_context.py](../../skills/project-context/scripts/project_context.py): persist_preparedはproject-context専用、CLIのhandleには認証済み保存入口がない。prepare_placementでSection 12/14の方針を扱い、外部の信頼済み認可が必要。
- [owner_verifiers.py](../../skills/qa-workflow/scripts/owner_verifiers.py): _stored_owner_artifactはcanonical JSON文字列、hash、target、owner CLIのvalidate/validate_readbackを照合する。providerを自ら読まない。[runtime_contract.py](../../skills/qa-workflow/scripts/runtime_contract.py)のOWNER_VERIFIED_SKILLSと登録集合が一致する。workflow_runtimeのscopeはskill/target/execution_rangeで識別し、非runtime-v2 ownerのcurrent_structure_stateはnull。downstream_stateの再開契約も維持。
- [qa-workflow](../../skills/qa-workflow/SKILL.md)は要求集合v2、局所blocked、既存入力revision再利用を持つ。補助工程は要求scopeに加えない。workflow stateはworkflow_refごとの既存envelope、local exact-content tokenだけではCASではない。
- [knowledge_runtime.py](../../skills/qa-knowledge/scripts/knowledge_runtime.py)にはread_root_entries、scan_knowledge_root、lookup/lookup_root、compare_currentness、plan_create/update/replacementがある。lookupはscope一致が必要。既存Knowledgeの適用規則は緩めない。
- [workflow_efficiency.py](../../scripts/skills/evals/workflow_efficiency.py)は5シナリオ、2群のschema。最大1ターン入力token・重複質問の計測は別評価にする。

## 並行PRと認可の着手条件

[PR #38](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/38)（確認head d7b691b40fefe3bf84ccd7c57d4b5a2fbb5b89d7）はuser-confirmed保存mode、artifact_host.py、spec/question/test-analysis保存契約を追加中。artifact_host.pyは--user-confirmed-refを自己申告の確認記録として扱い、認証ではないと明記。これをqa_artifact_writeの証明に転用しない。STORE_KINDS一元化やbranch分割・CLIの構成は再利用候補。mainに未統合なので、本branchへの無断取り込みはしない。実装時に最新mainとPR #38の確定契約を照合し、同一変更を二重実装しない。依存が必要なら利用者と取り込み方法を決める。PR #39（CI権限）・#17（Agent評価runner）も競合箇所のみ確認。

現時点でmain内に実運用のqa_artifact_write発行主体・認証済みhost接続・失効照合は確認できていない。実装担当は01の手順で実hostを確認し、認可経路が成立するまで本番保存・正式完了を開始しない。認可に依存しないSkill本文、構造検証、読取可能な範囲の分析・評価fixture設計は進めてよい。保存不足を理由に分析全体を止めない。test fixtureでの認可成功を本番接続済みと報告しない。

## 対象・変更境界

新規2 Skill（context-signal-audit、context-rule-synthesis）と3成果物、既存provider拡張、qa-workflowのrouting・state・owner verifier、必要なownerとの接続、README/EVALS・評価・回帰検証を対象とする。添付設計の比較に基づき1 Skillとの実測を行い、品質・効率条件で最終構成を決める。評価用の1 Skill構成は本番3つ目のSkillとして配布しない。

対象外: 新Authority、DEC/ASMの別正本、別DB・embedding・中央index・独自CAS・分散transaction・全体lock・常駐監視・特定harness強制・案件間共有、別課題の専門テストSkill、既存製品の変更。

## 実装方針

- AIには観察・仮説・根拠の意味評価・表現ゆれ・調査要否・owner判断を任せる。語彙の固定辞書、強制的な仮説件数、全成果物の毎回読み込み、固定retry数、機械的な信頼度点数を新設しない。
- helperはidentity、保存構造、範囲、CAS、readback、鮮度差分など機械的に確定できる項目を担当。通常入力の不足は未確認として扱い、影響部分のみ停止する。権限境界・根拠消失・必須完了の虚偽は許容しない。
- 既存ownerと標準ライブラリを優先。Skill単体配布を維持し、production helperはevalsに置かない。必要な依存Skillと非接続時の動作を明記する。全Skillへの重複規則追加は行わない。
- 既存案件は無指定で無効。新規3 kindを作成しない、stateに不要な欄を要求しない。既存形式の移行は不要。既存providerを無断切替しない。

## 実装順序

1. 最新差分、配置・認可host、既存CI baseline、ownerの意味的冪等照合を確認。比較条件を事前固定。
2. 3成果物のcanonical契約、identity、純粋検証・fixture、providerの列挙/履歴/保存入口を実装。実host未接続なら接続部分のみ保留。
3. Aの抽出・不変バッチとworkflow試行state、Bの検索・帰納・候補/run保存・再開を接続。
4. 既存ownerへの調査/質問/確定知識のhandoff、鮮度・変更伝播、workflowの補助/必須/単体実行・verifierを接続。
5. 評価・ドキュメント・実provider/Agent受入・全回帰、3構成比較を実施。結果による構成変更も本branchで検証する。

03の受入条件すべてを独立に確認する。計測不能・未接続・失敗はPASSにしない。既存の未達はbaselineと今回の差を区別して報告する。今回のPlan作成ではコードやCI実行、実host認可、性能計測は行っていない。
