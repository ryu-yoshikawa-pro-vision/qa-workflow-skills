# 決定論的Assertion一覧

## qa-workflow
- `WF-D001` ワークフロー全体状態の許可値
- `WF-D002` Skill名が正規Skill名
- `WF-D003` Skill状態の許可値
- `WF-D004` 完了時にブロック中 / 実行中を残さない
- `WF-D005` 完了時に要再検証を残さない
- `WF-D006` フィクスチャに基づく開始Skill
- `WF-D007` フィクスチャに基づく最終Skill
- `WF-D008` フィクスチャに基づく利用Skill
- `WF-D009` ワークフロー状態テーブル必須
- `WF-D010` 部分完了（ブロック中あり）にはブロック中Skillが必要
- `WF-D011` ブロック中状態にはブロック中Skillが必要
- `WF-D012` ワークフローSkill行の一意性
- `WF-D013` フィクスチャに基づくワークフロー全体状態
- `WF-D014` フィクスチャに基づくSkill状態
- `WF-D015` ワークフロー状態表の対象 / 実行範囲列
- `WF-D016` 複数用途Skillの対象 / 実行範囲値
- `WF-D017` 開始 / 最終Skillの対象 / 実行範囲値

## spec-analysis
- `SPEC-D001` 分析項目ID形式
- `SPEC-D002` IDと分類整合
- `SPEC-D003` ID一意性
- `SPEC-D004` SRC参照存在
- `SPEC-D005` 現在有効な仕様根拠の参照存在
- `SPEC-D006` 仕様根拠種別
- `SPEC-D007` 仕様根拠関係
- `SPEC-D008` 関連仕様根拠の存在
- `SPEC-D009` 撤回 / 置換済みの決定事項を現在有効な仕様根拠として利用しない
- `SPEC-D010` 現在有効な仕様根拠ID / 種別整合、INF / UNK禁止
- `SPEC-D011` フィクスチャで必須の分析項目 / 現在有効な仕様根拠の存在
- `SPEC-D012` 必須テーブルの存在
- `SPEC-D013` フィクスチャに基づく承認済みASM整合
- `SPEC-D014` 分析項目必須フィールド
- `SPEC-D015` 現在有効な仕様根拠の必須フィールド
- `SPEC-D016` 情報源必須フィールド
- `SPEC-D017` SRC ID形式
- `SPEC-D018` SRC ID一意性

## question-analysis
- `QUESTION-D001` Q ID形式
- `QUESTION-D002` Q ID一意性
- `QUESTION-D003` 分類の許可値
- `QUESTION-D004` 正規化先の許可値
- `QUESTION-D005` 再開Skill
- `QUESTION-D006` ブロッカーとブロック中範囲の整合
- `QUESTION-D007` 仮定状態
- `QUESTION-D008` ASM ID
- `QUESTION-D009` フィクスチャ承認情報との整合
- `QUESTION-D010` フィクスチャに基づく分類
- `QUESTION-D011` 必須テーブルの存在
- `QUESTION-D012` 質問行必須フィールド
- `QUESTION-D013` ブロック中範囲必須フィールド
- `QUESTION-D014` 仮定候補必須フィールド
- `QUESTION-D015` フィクスチャで必須の承認済みASM存在
- `QUESTION-D016` フィクスチャに基づく回答後正規化先
- `QUESTION-D017` 複数用途Skillの再開対象 / 実行範囲値
- `QUESTION-D018` フィクスチャに基づく再開Skill / 対象整合

## test-analysis
- `RISK-D001` RISK ID形式
- `RISK-D002` ID一意性
- `RISK-D003` プロダクトリスク必須フィールド
- `RISK-D004` 影響度 / 発生可能性 1..4
- `RISK-D005` 4x4リスクマトリクス再計算
- `RISK-D006` 仕様根拠 / 変更 / 依存参照
- `RISK-D007` テスト可能性の許可値
- `RISK-D008` 技法の許可値
- `RISK-D009` プロジェクトリスクらしき語のWARNING
- `RISK-D010` 必須テーブルの存在
- `RISK-D011` フィクスチャで必須のプロダクトリスク存在 / 値一致
- `RISK-D012` 技法行必須フィールド
- `RISK-D013` テスト可能性行必須フィールド
- `RISK-D014` フィクスチャで必須の技法存在
- `RISK-D015` フィクスチャで必須のテスト可能性値
- `RISK-D016` E2E対象選定テーブル必須
- `RISK-D017` E2E対象選定の技術非依存フィールド

## test-requirement-design
- `TR-D001` TR ID形式
- `TR-D002` ID一意性
- `TR-D003` 仕様根拠参照
- `TR-D004` プロダクトリスク参照
- `TR-D005` 優先度
- `TR-D006` 必須フィールド
- `TR-D007` 扱い
- `TR-D008` 扱いの理由
- `TR-D009` 仕様根拠 / リスクのテスト要求または扱いへの排他的閉鎖
- `TR-D010` 最高リスク優先度継承 / 優先度変更理由
- `TR-D011` 必須テーブルの存在
- `TR-D012` フィクスチャで必須のテスト要求存在
- `TR-D013` 扱い対象の上流IDとフィクスチャ既知集合の整合
- `TR-D014` フィクスチャで必須の上流テスト要求接続
- `TR-D015` フィクスチャに基づく上流項目の扱い

## test-condition-design
- `TCN-D001` TCN ID形式
- `TCN-D002` CI ID形式
- `TCN-D003` TCN ID一意性
- `TCN-D004` CI ID一意性
- `TCN-D005` CI親TCN整合
- `TCN-D006` テスト要求 / 仕様根拠 / リスク参照
- `TCN-D007` TCN必須フィールド
- `TCN-D008` TCN優先度
- `TCN-D009` CI優先度
- `TCN-D010` テスト要求の扱い
- `TCN-D011` カバレッジ候補の扱い
- `TCN-D012` 扱いの理由 / 重複カバー先整合
- `TCN-D013` テスト要求のテスト条件または扱いへの排他的閉鎖
- `TCN-D014` フィクスチャのPairwise因子 / 値整合
- `TCN-D015` 成立可能な値ペアの2-wise 100%カバレッジ
- `TCN-D016` フィクスチャ状態遷移から実在カバレッジ項目への閉鎖
- `TCN-D017` フィクスチャに基づくBVA値
- `TCN-D018` Pairwise生成組合せの未知因子禁止
- `TCN-D019` Pairwise生成組合せの未知値禁止
- `TCN-D020` Pairwise生成組合せの禁止制約違反禁止
- `TCN-D021` Pairwise生成組合せの必要因子欠落禁止
- `TCN-D022` 必須テーブルの存在
- `TCN-D023` フィクスチャで必須のテスト条件 / カバレッジ項目存在
- `TCN-D024` カバレッジ項目必須フィールド
- `TCN-D025` 明示カバレッジ項目の仕様根拠参照整合
- `TCN-D026` Pairwise生成組合せのカバレッジ項目ID実在性
- `TCN-D027` Pairwise生成組合せのカバレッジ項目ID一意性
- `TCN-D028` Pairwise生成組合せtoken構造 / 因子重複
- `TCN-D029` テスト要求の扱い対象IDとフィクスチャ既知集合の整合

## test-case-design
- `TC-D001` TC ID形式
- `TC-D002` ID一意性
- `TC-D003` 優先度
- `TC-D004` 詳細テストケース必須フィールド
- `TC-D005` 上流 / 仕様根拠参照
- `TC-D006` 期待結果の仕様根拠存在
- `TC-D007` CI / 内包TCNのテストケースまたは扱いへの排他的閉鎖
- `TC-D008` 扱い
- `TC-D009` 扱いの理由
- `TC-D010` 最高CI優先度維持 / 優先度変更理由
- `TC-D011` 番号付き期待結果と根拠対応 / フィクスチャに基づく仕様根拠対応
- `TC-D012` 必須テーブルの存在
- `TC-D013` フィクスチャで必須のテストケース存在
- `TC-D014` 扱い対象の上流IDとフィクスチャ既知集合の整合
- `TC-W001` 曖昧期待結果語WARNING
- `TC-W002` 他ケース依存らしき記述WARNING

## coverage-analysis
- `COV-D001` グラフ外の未知ID
- `COV-D002` 独立再計算したギャップの認識
- `COV-D003` 下流不存在をブロック中へ誤分類しない
- `COV-D004` フィクスチャのグラフ孤立ノード認識
- `COV-D005` フィクスチャに基づく修正対象存在 / 修正Skill一致
- `COV-D006` 修正Skillが正規Skill名
- `COV-D007` 最低必須カバレッジマトリクスの存在
- `COV-D008` TC → E2E実装対応表必須
- `COV-D009` TCごとのE2E扱い / 実装参照整合
- `COV-D010` 既存カバレッジマトリクスでE2E実装 → 実行結果を追跡可能
- `COV-D011` E2E実装から実行結果への追跡整合
- `COV-D012` TCなし経路のTC ID創作禁止

## adversarial-review
- `REV-D001` REV ID形式
- `REV-D002` ID一意性
- `REV-D003` 重大度
- `REV-D004` 処置
- `REV-D005` 対象成果物参照
- `REV-D006` 修正先が正規Skillまたは案件コンテキスト / 仕様決定
- `REV-D007` 致命的 + 残存リスク受容禁止
- `REV-D008` 重大 + 残存リスク受容の承認参照 / フィクスチャ照合
- `REV-D009` 重大度別件数整合
- `REV-D010` フィクスチャに基づく決定論的欠陥 / 指定属性検出
- `REV-D011` 必須テーブルの存在
- `REV-D012` 指摘必須フィールド
- `REV-D013` 指摘概要の重大度許可値
- `REV-D014` 指摘概要の重大度一意性
- `REV-D015` E2E実装参照一覧必須
- `REV-D016` E2E実装参照の安定性 / 期待値整合

## e2e-test-inspection
- `E2E-INSP-D001` 必須inspectionテーブル
- `E2E-INSP-D002` TC扱いの許可値
- `E2E-INSP-D003` TC ID形式
- `E2E-INSP-D004` 安定参照の一意性
- `E2E-INSP-D005` freshness fact必須フィールド
- `E2E-INSP-D006` 安全条件の必須フィールド
- `E2E-INSP-D007` 実行可能性 / 依存関係の必須フィールド
- `E2E-INSP-D008` フィクスチャで期待するinspection事実
- `E2E-INSP-D009` フィクスチャで期待する実装参照
- `E2E-INSP-D010` フィクスチャで期待するTC ID
- `E2E-INSP-D011` TCなし経路のTC ID創作禁止
- `E2E-INSP-D012` 事実の確認元表示

## e2e-test-implementation
- `E2E-IMPL-D001` 必須実装テーブル
- `E2E-IMPL-D002` TC扱いの許可値
- `E2E-IMPL-D003` TC ID形式
- `E2E-IMPL-D004` 実装参照の一意性
- `E2E-IMPL-D005` 実装参照のrepo-relative性
- `E2E-IMPL-D006` test file / title path必須
- `E2E-IMPL-D007` 実装前の状態事実必須フィールド
- `E2E-IMPL-D008` 静的 / 軽量検証結果の許可値
- `E2E-IMPL-D009` 検証失敗理由
- `E2E-IMPL-D010` フィクスチャで期待する実装参照
- `E2E-IMPL-D011` フィクスチャで期待するTC ID
- `E2E-IMPL-D012` TCなし経路のTC ID創作禁止
- `E2E-IMPL-D013` 実行禁止 / 未実行の明示

## e2e-test-execution
- `E2E-EXEC-D001` 必須実行テーブル
- `E2E-EXEC-D002` effective settingsの必須フィールド
- `E2E-EXEC-D003` run statusのraw factと必須run項目
- `E2E-EXEC-D004` run結果の確認元 / raw fact区分
- `E2E-EXEC-D005` current run artifact参照
- `E2E-EXEC-D006` logical primary参照の一意性
- `E2E-EXEC-D007` resolved primary参照の一意性
- `E2E-EXEC-D008` logical / resolved件数整合とresolved 0件の理由
- `E2E-EXEC-D009` resolved primaryごとの結果 / 理由
- `E2E-EXEC-D010` retry attemptの構造化
- `E2E-EXEC-D011` primary attempt参照
- `E2E-EXEC-D012` cleanup状態の許可値
- `E2E-EXEC-D013` cleanup未成功を完了扱いしないこと
- `E2E-EXEC-D014` TCなし経路のTC ID創作禁止
- `E2E-EXEC-D015` フィクスチャで期待するlogical件数
- `E2E-EXEC-D016` フィクスチャで期待するresolved件数
- `E2E-EXEC-D017` フィクスチャで期待するretry attemptのstatus / 番号保持

## e2e-test-result-analysis
- `E2E-AN-D001` 必須分析テーブル
- `E2E-AN-D002` 実行事実・参照・cleanupの保持
- `E2E-AN-D003` 判定状態の許可値
- `E2E-AN-D004` 再現性の許可値 / 原因との分離
- `E2E-AN-D005` 追加実行の直接実行禁止とexecution routing
- `E2E-AN-D006` 修正routing先の許可値
- `E2E-AN-D007` フィクスチャで期待する実装参照
- `E2E-AN-D008` TCなし経路のTC ID創作禁止
- `E2E-AN-D009` cleanup未確認の明示
- `E2E-AN-D010` 追加実行依頼の目的 / 仮説 / 範囲 / owner

## e2e-test-reporting
- `E2E-REPORT-D001` 必須報告テーブル
- `E2E-REPORT-D002` environment必須フィールド
- `E2E-REPORT-D003` run raw factの確認元 / 区分
- `E2E-REPORT-D004` logical primary参照の一意性
- `E2E-REPORT-D005` primary件数・開始数・未実行理由の整合
- `E2E-REPORT-D006` resolved primary参照の一意性
- `E2E-REPORT-D007` primary outcomeの許可値
- `E2E-REPORT-D008` retry attemptの分離
- `E2E-REPORT-D009` E2E実装から実行結果への追跡
- `E2E-REPORT-D010` cleanup状態
- `E2E-REPORT-D011` TCなし経路のTC ID創作禁止
- `E2E-REPORT-D012` フィクスチャで期待するlogical件数
- `E2E-REPORT-D013` フィクスチャで期待するresolved件数
- `E2E-REPORT-D014` cleanupのフィクスチャ整合
- `E2E-REPORT-D015` retry発生時の初回 / retry履歴保持
- `E2E-REPORT-D016` フィクスチャで期待する初回 / retry履歴
