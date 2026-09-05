# Deterministic Assertion Catalog

## qa-workflow
- `WF-D001` Workflow全体状態 allowed values
- `WF-D002` Skill名がCanonical
- `WF-D003` Skill状態 allowed values
- `WF-D004` 完了時にBlocked / 実行中を残さない
- `WF-D005` 完了時に要再検証を残さない
- `WF-D006` fixture-backed開始Skill
- `WF-D007` fixture-backed最終Skill
- `WF-D008` fixture-backed利用Skill
- `WF-D009` Workflow状態テーブル必須
- `WF-D010` 部分完了（Blockedあり）にはBlocked Skillが必要
- `WF-D011` Blocked状態にはBlocked Skillが必要
- `WF-D012` Workflow Skill行一意性
- `WF-D013` fixture-backed Workflow全体状態
- `WF-D014` fixture-backed Skill状態

## spec-analysis
- `SPEC-D001` 分析項目ID形式
- `SPEC-D002` IDと分類整合
- `SPEC-D003` ID一意性
- `SPEC-D004` SRC参照存在
- `SPEC-D005` Current Effective Authority参照存在
- `SPEC-D006` Authority種別
- `SPEC-D007` Authority関係
- `SPEC-D008` 関連Authority存在
- `SPEC-D009` 撤回/置換済みDecisionのCurrent Authority利用禁止
- `SPEC-D010` Current Effective Authority ID / 種別整合、INF / UNK禁止
- `SPEC-D011` fixture-required分析項目 / Current Authority存在
- `SPEC-D012` Canonical必須テーブル存在
- `SPEC-D013` fixture-backed承認済みASM整合
- `SPEC-D014` 分析項目必須フィールド
- `SPEC-D015` Current Effective Authority必須フィールド
- `SPEC-D016` 情報源必須フィールド
- `SPEC-D017` SRC ID形式
- `SPEC-D018` SRC ID一意性

## question-analysis
- `QUESTION-D001` Q ID形式
- `QUESTION-D002` Q ID一意性
- `QUESTION-D003` 分類allowed values
- `QUESTION-D004` 正規化先allowed values
- `QUESTION-D005` 再開Skill
- `QUESTION-D006` BlockerとBlocked範囲整合
- `QUESTION-D007` Assumption状態
- `QUESTION-D008` ASM ID
- `QUESTION-D009` fixture承認情報との整合
- `QUESTION-D010` fixture-backed分類
- `QUESTION-D011` Canonical必須テーブル存在
- `QUESTION-D012` 質問行必須フィールド
- `QUESTION-D013` Blocked範囲必須フィールド
- `QUESTION-D014` 仮定候補必須フィールド
- `QUESTION-D015` fixture-required承認済みASM存在

## test-analysis
- `RISK-D001` RISK ID形式
- `RISK-D002` ID一意性
- `RISK-D003` Product Risk必須フィールド
- `RISK-D004` Impact/Likelihood 1..4
- `RISK-D005` 4x4 Risk Matrix再計算
- `RISK-D006` Authority/change/dependency参照
- `RISK-D007` Testability allowed values
- `RISK-D008` 技法allowed values
- `RISK-D009` Project Riskらしき語のWARNING
- `RISK-D010` Canonical必須テーブル存在
- `RISK-D011` fixture-required Product Risk存在 / 値一致
- `RISK-D012` 技法行必須フィールド
- `RISK-D013` Testability行必須フィールド
- `RISK-D014` fixture-required技法存在
- `RISK-D015` fixture-required Testability値

## test-requirement-design
- `TR-D001` TR ID形式
- `TR-D002` ID一意性
- `TR-D003` Authority参照
- `TR-D004` Product Risk参照
- `TR-D005` 優先度
- `TR-D006` 必須フィールド
- `TR-D007` Disposition
- `TR-D008` Disposition理由
- `TR-D009` Authority/Risk閉鎖
- `TR-D010` 最高Risk優先度継承 / override理由
- `TR-D011` Canonical必須テーブル存在
- `TR-D012` fixture-required Test Requirement存在
- `TR-D013` Disposition上流IDのfixture既知集合整合

## test-condition-design
- `TCN-D001` TCN ID形式
- `TCN-D002` CI ID形式
- `TCN-D003` TCN ID一意性
- `TCN-D004` CI ID一意性
- `TCN-D005` CI親TCN整合
- `TCN-D006` TR/Authority/Risk参照
- `TCN-D007` TCN必須フィールド
- `TCN-D008` TCN優先度
- `TCN-D009` CI優先度
- `TCN-D010` TR Disposition
- `TCN-D011` Coverage候補Disposition
- `TCN-D012` Disposition理由 / 重複カバー先整合
- `TCN-D013` TR閉鎖
- `TCN-D014` fixture Pairwise Factor/Value整合
- `TCN-D015` feasible pairの2-wise 100% coverage
- `TCN-D016` fixture状態遷移から実在Coverage Itemへのclosure
- `TCN-D017` fixture-backed BVA値
- `TCN-D018` Pairwise生成組合せの未知Factor禁止
- `TCN-D019` Pairwise生成組合せの未知Value禁止
- `TCN-D020` Pairwise生成組合せのforbidden constraint違反禁止
- `TCN-D021` Pairwise生成組合せの必要Factor欠落禁止
- `TCN-D022` Canonical必須テーブル存在
- `TCN-D023` fixture-required Test Condition / Coverage Item存在
- `TCN-D024` Coverage Item必須フィールド
- `TCN-D025` 明示Coverage Item Authority参照整合
- `TCN-D026` Pairwise生成組合せのCoverage Item ID実在性
- `TCN-D027` Pairwise生成組合せのCoverage Item ID一意性
- `TCN-D028` Pairwise生成組合せtoken構造 / Factor重複
- `TCN-D029` TR Disposition IDのfixture既知集合整合

## test-case-design
- `TC-D001` TC ID形式
- `TC-D002` ID一意性
- `TC-D003` 優先度
- `TC-D004` Low-Level必須フィールド
- `TC-D005` 上流/Authority参照
- `TC-D006` 期待結果Authority存在
- `TC-D007` CI/内包TCN閉鎖
- `TC-D008` Disposition
- `TC-D009` Disposition理由
- `TC-D010` 最高CI優先度維持 / override理由
- `TC-D011` 番号付き期待結果と根拠対応
- `TC-D012` Canonical必須テーブル存在
- `TC-D013` fixture-required Test Case存在
- `TC-D014` Disposition上流IDのfixture既知集合整合
- `TC-W001` 曖昧期待結果語WARNING
- `TC-W002` 他ケース依存らしき記述WARNING

## coverage-analysis
- `COV-D001` graph外未知ID
- `COV-D002` 独立再計算したGapの認識
- `COV-D003` 下流不存在をBlockedへ誤分類しない
- `COV-D004` fixture graph孤立ノード認識
- `COV-D005` fixture-backed修正対象存在 / 修正Skill一致
- `COV-D006` 修正Skill Canonical
- `COV-D007` Canonical最低必須カバレッジマトリクス存在

## adversarial-review
- `REV-D001` REV ID形式
- `REV-D002` ID一意性
- `REV-D003` 重大度
- `REV-D004` 処置
- `REV-D005` 対象成果物参照
- `REV-D006` 修正先がCanonical SkillまたはProject Context / 仕様決定
- `REV-D007` 致命的+残存リスク受容禁止
- `REV-D008` 重大+残存リスク受容の承認参照 / fixture照合
- `REV-D009` 重大度別件数整合
- `REV-D010` fixture-backed決定論的欠陥 / 指定属性検出
- `REV-D011` Canonical必須テーブル存在
- `REV-D012` 指摘必須フィールド
- `REV-D013` 指摘概要Severity allowed values
- `REV-D014` 指摘概要Severity一意性
