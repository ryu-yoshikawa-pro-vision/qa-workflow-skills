# 横断的法則性抽出・コンテキスト補完 実装Plan

- 基準: main `a37b15508dadd17ac0228ac896badb71d6a8f2c7`（2026-11-25確認、添付「QAワークフロー 詳細設計書：横断的法則性抽出・コンテキスト補完（基本設計確定版）」と一致）
- 実装branch: `feat/context-rule-synthesis`
- 状態: Plan作成済み・実装未着手。実装と受入を同一branchで行う。
- [元の基本設計書](2026-11-25_123000_context-rule-synthesis_design.md)の1〜14章を対象とする。付録は原文保存のみで実装対象外。原文（SHA-256: 727e784d2faf8741a2f5a199515c060d3abb174658296ac3dbb992ac018270d0）は変更しない。詳細な例・表・JSON例も実装・検証の参照先とする。
- 本Planは基本設計の具体化。以下の完全性、scope具体化、配置、採用条件は実装前レビューで明確化した契約とし、原文の曖昧な箇所より優先する。他の設計要件は省略しない。

## 目的

複数機能・セッション・workflowの観察から暗黙ルール、不変条件、差異条件を発見し、次回のQAで既存知識・回答・根拠を横断利用する。追加調査を先に行い、必要な質問は残しながら重複質問と読み込み負荷を減らす。候補は第二のAuthorityにしない。

## Planの構成

- [01 保存・認可・データ契約](2026-11-25_123000_context-rule-synthesis_01_storage-and-contracts.md): provider、identity、保存・中断再開、並行整合。
- [02 Skill・workflow・owner連携](2026-11-25_123000_context-rule-synthesis_02_skills-and-workflow.md): A/Bの責務、横断発見、帰納、質問、完了判定。
- [03 評価・実装順序・受入](2026-11-25_123000_context-rule-synthesis_03_validation.md): 検証マトリクス、3構成比較、完了条件。

詳細文書は各担当領域の実装契約。本書は共通方針と依存順序の正本。個々の関数名・ファイル分割は実装で調整してよい。根拠のある変更はPlanへ理由を記録し、目的・必須要件は無断で縮小しない。

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
- [qa-workflow](../../skills/qa-workflow/SKILL.md)は要求集合v2、局所blocked、既存入力revision再利用を持つ。補助工程は要求scopeに加えない。workflow stateはworkflow_refごとの既存envelope、local exact-content tokenだけではCASではない。
- [knowledge_runtime.py](../../skills/qa-knowledge/scripts/knowledge_runtime.py)にはread_root_entries、scan_knowledge_root、lookup/lookup_root、compare_currentness、plan_create/update/replacementがある。lookupはscope一致が必要。既存Knowledgeの適用規則は緩めない。
- [workflow_efficiency.py](../../scripts/skills/evals/workflow_efficiency.py)は5シナリオ、2群のschema。最大1ターン入力token・重複質問の計測は別評価にする。

## 並行PRと認可の着手条件

[PR #38](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/38)（確認head d7b691b40fefe3bf84ccd7c57d4b5a2fbb5b89d7）はuser-confirmed保存mode、artifact_host.py、spec/question/test-analysis保存契約を追加中。artifact_host.pyは--user-confirmed-refを自己申告の確認記録として扱い、認証ではないと明記。これをqa_artifact_writeの証明に転用しない。STORE_KINDS一元化やbranch分割・CLIの構成は再利用候補。mainに未統合なので、本branchへの無断取り込みはしない。実装時に最新mainとPR #38の確定契約を照合し、同一変更を二重実装しない。依存が必要なら利用者と取り込み方法を決める。PR #39（CI権限）はPlan作成後にmainへマージ済み（main 197f1e0e1abe870b0cc793355e7abf73bf241d87、PR #40作成時確認）。#17（Agent評価runner）も競合箇所のみ確認。基準設計のSHAと実装開始時のmainを区別する。

現時点でリポジトリ内に実運用のqa_artifact_write発行主体・認証済みhost接続・失効照合は確認できていない。実装着手前に01の確認手順を実hostのコード・設定で実施する。利用hostが不明の場合は依存する正式保存・完了経路のみ着手条件未充足とし、信頼境界の前提を利用者と確認する。認可に依存しないSkill本文、構造検証、読取可能な範囲の分析・評価fixture設計は進めてよい。保存不足を理由に分析全体を止めない。test fixtureでの認可成功を本番接続済みと報告しない。配置・共有境界・パス・owner照合の共通契約は01・02で定義済みとし、案件固有の値や外部サービスの能力は推測で設定しない。

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
