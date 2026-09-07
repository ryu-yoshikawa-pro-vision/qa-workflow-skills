# 決定論的Assertion一覧

## qa-workflow
- `WF-D001` ワークフロー全体状態の許可値
- `WF-D002` Skill名が正規Skill名
- `WF-D003` Skill状態の許可値
- `WF-D004` 完了時にブロック中 / 実行中を残さない
- `WF-D005` 完了時に要再検証を残さない
- `WF-D006` fixtureに基づく開始Skill
- `WF-D007` fixtureに基づく最終Skill
- `WF-D008` fixtureに基づく利用Skill
- `WF-D009` ワークフロー状態テーブル必須
- `WF-D010` 部分完了（ブロック中あり）にはブロック中Skillが必要
- `WF-D011` ブロック中状態にはブロック中Skillが必要
- `WF-D012` ワークフローSkill行の一意性
- `WF-D013` fixtureに基づくワークフロー全体状態
- `WF-D014` fixtureに基づくSkill状態

## spec-analysis
- `SPEC-D001` 分析項目ID形式
- `SPEC-D002` IDと分類整合
- `SPEC-D003` ID一意性
- `SPEC-D004` SRC参照存在
- `SPEC-D005` 現在有効な仕様根拠の参照存在
- `SPEC-D006` 仕様根拠種別
- `SPEC-D007` 仕様根拠関係
- `SPEC-D008` 関連仕様根拠の存在
- `SPEC-D009` 撤回 / 置換済みDecisionを現在有効な仕様根拠として利用しない
- `SPEC-D010` 現在有効な仕様根拠ID / 種別整合、INF / UNK禁止
- `SPEC-D011` fixtureで必須の分析項目 / 現在有効な仕様根拠の存在
- `SPEC-D012` 正本の必須テーブル存在
- `SPEC-D013` fixtureに基づく承認済みASM整合
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
- `QUESTION-D009` fixture承認情報との整合
- `QUESTION-D010` fixtureに基づく分類
- `QUESTION-D011` 正本の必須テーブル存在
- `QUESTION-D012` 質問行必須フィールド
- `QUESTION-D013` ブロック中範囲必須フィールド
- `QUESTION-D014` 仮定候補必須フィールド
- `QUESTION-D015` fixtureで必須の承認済みASM存在
- `QUESTION-D016` fixtureに基づく回答後正規化先

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
- `RISK-D010` 正本の必須テーブル存在
- `RISK-D011` fixtureで必須のプロダクトリスク存在 / 値一致
- `RISK-D012` 技法行必須フィールド
- `RISK-D013` テスト可能性行必須フィールド
- `RISK-D014` fixtureで必須の技法存在
- `RISK-D015` fixtureで必須のテスト可能性値

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
- `TR-D010` 最高リスク優先度継承 / override理由
- `TR-D011` 正本の必須テーブル存在
- `TR-D012` fixtureで必須のテスト要求存在
- `TR-D013` 扱い対象の上流IDとfixture既知集合の整合
- `TR-D014` fixtureで必須の上流テスト要求接続
- `TR-D015` fixtureに基づく上流項目の扱い

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
- `TCN-D014` fixture Pairwise因子 / 値整合
- `TCN-D015` 成立可能な値ペアの2-wise 100%カバレッジ
- `TCN-D016` fixture状態遷移から実在カバレッジ項目への閉鎖
- `TCN-D017` fixtureに基づくBVA値
- `TCN-D018` Pairwise生成組合せの未知因子禁止
- `TCN-D019` Pairwise生成組合せの未知値禁止
- `TCN-D020` Pairwise生成組合せの禁止制約違反禁止
- `TCN-D021` Pairwise生成組合せの必要因子欠落禁止
- `TCN-D022` 正本の必須テーブル存在
- `TCN-D023` fixtureで必須のテスト条件 / カバレッジ項目存在
- `TCN-D024` カバレッジ項目必須フィールド
- `TCN-D025` 明示カバレッジ項目の仕様根拠参照整合
- `TCN-D026` Pairwise生成組合せのカバレッジ項目ID実在性
- `TCN-D027` Pairwise生成組合せのカバレッジ項目ID一意性
- `TCN-D028` Pairwise生成組合せtoken構造 / 因子重複
- `TCN-D029` テスト要求の扱い対象IDとfixture既知集合の整合

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
- `TC-D010` 最高CI優先度維持 / override理由
- `TC-D011` 番号付き期待結果と根拠対応 / fixtureに基づく仕様根拠対応
- `TC-D012` 正本の必須テーブル存在
- `TC-D013` fixtureで必須のテストケース存在
- `TC-D014` 扱い対象の上流IDとfixture既知集合の整合
- `TC-W001` 曖昧期待結果語WARNING
- `TC-W002` 他ケース依存らしき記述WARNING

## coverage-analysis
- `COV-D001` graph外未知ID
- `COV-D002` 独立再計算したギャップの認識
- `COV-D003` 下流不存在をブロック中へ誤分類しない
- `COV-D004` fixture graph孤立ノード認識
- `COV-D005` fixtureに基づく修正対象存在 / 修正Skill一致
- `COV-D006` 修正Skillが正規Skill名
- `COV-D007` 正本の最低必須カバレッジマトリクス存在

## adversarial-review
- `REV-D001` REV ID形式
- `REV-D002` ID一意性
- `REV-D003` 重大度
- `REV-D004` 処置
- `REV-D005` 対象成果物参照
- `REV-D006` 修正先が正規SkillまたはProject Context / 仕様決定
- `REV-D007` 致命的 + 残存リスク受容禁止
- `REV-D008` 重大 + 残存リスク受容の承認参照 / fixture照合
- `REV-D009` 重大度別件数整合
- `REV-D010` fixtureに基づく決定論的欠陥 / 指定属性検出
- `REV-D011` 正本の必須テーブル存在
- `REV-D012` 指摘必須フィールド
- `REV-D013` 指摘概要の重大度許可値
- `REV-D014` 指摘概要の重大度一意性
