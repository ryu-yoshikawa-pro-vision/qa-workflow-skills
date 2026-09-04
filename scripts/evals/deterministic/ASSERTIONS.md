# Deterministic Assertion Catalog

## qa-workflow
- `WF-D001` Workflow全体状態 allowed values
- `WF-D002` Skill名がCanonical
- `WF-D003` Skill状態 allowed values
- `WF-D004` Blocked残存時に完了禁止
- `WF-D005` 要再検証残存時に完了禁止
- `WF-D006` fixture-backed開始Skill
- `WF-D007` fixture-backed最終Skill
- `WF-D008` fixture-backed利用Skill

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

## test-analysis
- `RISK-D001` RISK ID形式
- `RISK-D002` ID一意性
- `RISK-D003` 必須フィールド
- `RISK-D004` Impact/Likelihood 1..4
- `RISK-D005` 4x4 Risk Matrix再計算
- `RISK-D006` Authority/change/dependency参照
- `RISK-D007` Testability allowed values
- `RISK-D008` 技法allowed values
- `RISK-D009` Project Riskらしき語のWARNING

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
- `TR-D010` 最高Risk優先度継承

## test-condition-design
- `TCN-D001` TCN ID形式
- `TCN-D002` CI ID形式
- `TCN-D003` TCN ID一意性
- `TCN-D004` CI ID一意性
- `TCN-D005` CI親TCN整合
- `TCN-D006` TR/Authority/Risk参照
- `TCN-D007` 必須フィールド
- `TCN-D008` TCN優先度
- `TCN-D009` CI優先度
- `TCN-D010` TR Disposition
- `TCN-D011` Coverage候補Disposition
- `TCN-D012` Disposition理由 / 重複カバー先
- `TCN-D013` TR閉鎖
- `TCN-D014` fixture Pairwise Factor/Value整合
- `TCN-D015` feasible pairの2-wise 100% coverage
- `TCN-D016` fixture状態遷移closure
- `TCN-D017` fixture-backed BVA値

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
- `TC-D010` 最高CI優先度維持
- `TC-D011` 番号付き期待結果と根拠対応
- `TC-W001` 曖昧期待結果語WARNING
- `TC-W002` 他ケース依存らしき記述WARNING

## coverage-analysis
- `COV-D001` graph外未知ID
- `COV-D002` 独立再計算したGapの認識
- `COV-D003` 下流不存在をBlockedへ誤分類しない
- `COV-D004` fixture graph孤立ノード認識
- `COV-D005` fixture-backed修正Skill
- `COV-D006` 修正Skill Canonical

## adversarial-review
- `REV-D001` REV ID形式
- `REV-D002` ID一意性
- `REV-D003` 重大度
- `REV-D004` 処置
- `REV-D005` 対象成果物参照
- `REV-D006` 修正Skill
- `REV-D007` 致命的+残存リスク受容禁止
- `REV-D008` 重大+残存リスク受容の承認参照
- `REV-D009` 重大度別件数整合
- `REV-D010` fixture-backed決定論的欠陥検出
