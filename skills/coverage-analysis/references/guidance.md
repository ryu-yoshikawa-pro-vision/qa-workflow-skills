# カバレッジ分析 詳細判断基準

## 目的

Current Effective Authority、Product Risk、Test Requirement、Test Condition、Coverage Item、Test Caseの意味上のつながりを確認し、**対象範囲内の項目が下流成果物または明示Dispositionへ閉じているか**を分析します。

ケース件数やリンク数だけでCoverageを判断しません。

## 入力

分析対象に応じて次を使います。

- Current Effective Authority
- Product Risk
- Test Requirement
- Test Condition
- Coverage Item
- Test Case
- 適用技法 / Coverage Criteria
- Coverage候補のDisposition
- 対象外 / 残存リスク / Blocked情報

## 分析モード

### Partial

ユーザーが指定した成果物間だけを比較します。

### Full Workflow

次の閉鎖性をすべて確認します。

1. Current Effective Authority → Test Requirement または明示Disposition
2. Product Risk → Test Requirement または明示Disposition
3. Test Requirement → Test Condition または明示Disposition
4. Test Condition → Coverage Item（明示時）またはTest Case（内包時）、あるいは明示Disposition
5. Coverage Item → Test Case または明示Disposition
6. Coverage候補 → Coverage Item または妥当な候補Disposition

必要に応じてCurrent Effective Authority → Test CaseのEnd-to-End追跡も確認します。

## Coverageの判断基準

### Current Effective Authority Coverage

対象範囲内の現在有効な仕様・決定・承認済み仮定について、Test Requirementへ意味上の対応があるか、または明示Dispositionがあるか確認します。

`撤回` / `置換済み`Decisionを現在有効な上流根拠として数えません。

IDがリンクされているだけで検証責務が意味を確認していなければCoverageとはみなしません。

### Product Risk Coverage

対象範囲内の各Product Riskについて、次を確認します。

- 1つ以上のTest Requirementへ接続されているか
- 接続先の優先度・設計深度へProduct Riskが反映されているか
- Test Requirementへ接続しない場合は、別テストレベル / 残存リスク / 対象外 / BlockedのDispositionがあるか

Product Riskが高いにもかかわらず未カバーまたは未受容の残存リスクとなっている場合は、重大なCoverage Gap候補として明示します。

### Test Requirement Coverage

各Test Requirementについて、Test Conditionへ展開されているか、または別テストレベル / 残存リスク / 対象外 / Blockedへ位置づけられているか確認します。

### Coverage Criteria充足

`test-condition-design`が定義したCoverage Criteriaと候補Dispositionを確認します。

- 同値分割 → 対象Partitionが採用または妥当なDispositionへ位置づけられているか
- 境界値 → 採用した2-value / 3-valueの具体項目があるか
- デシジョンテーブル → 実行可能ルールが採用または妥当なDispositionへ位置づけられているか
- 状態遷移 → 対象範囲内の全有効遷移がCoverage Itemまたは妥当なDispositionへ位置づけられているか
- Pairwise → 成立可能な全Value Pairが生成Coverage Itemへ含まれる2-wise保証があるか
- シナリオ → 主経路 / 必要代替・例外経路が採用または妥当なDispositionへ位置づけられているか

技法名が書かれているだけでは充足としません。

### Coverage候補Dispositionの妥当性

各候補Dispositionを、`qa-workflow`と`test-condition-design`の使用条件に照らして確認します。

特に次をGapとして扱います。

- 低Product Riskだけを理由に`対象外`へ送っている
- 根拠なく`成立不能`としている
- カバー先なしに`重複`としている
- 対象内の未カバー項目を理由なしに`残存リスク`へ送っている
- 設計可能な項目を便宜的に`Blocked`へ送っている

### Coverage Item Coverage

明示Coverage Itemは最終的に次のいずれかへ位置づけます。

- Test Caseでカバー
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

DispositionのないCoverage ItemはCoverage Gapです。

### Test CaseをCoverage Evidenceとして扱う最低条件

- どのTest Condition / Coverage Itemを確認するか分かる
- 実施可能な具体性がある
- PASS / FAILを判断できる期待結果がある
- PASS / FAIL判定に使用する各期待結果が、1件以上のCurrent Effective AuthorityまたはAuthority集合へ曖昧なく追跡できる

詳細なケース品質レビューは`adversarial-review`が担当します。

## Product Riskとの深度対応

高Product Risk領域では、選択技法のCoverage Criteria、境界 / 状態 / 権限 / エラー・復旧、Coverage削減理由を確認します。

低Product Risk領域では一般エッジケースの過剰展開を確認しますが、低リスクという理由だけで対象内項目がチェーンから消えていないことも確認します。

## 検出対象

### 未カバー

上流責務、Product Risk、Test Requirement、Coverage Item等に必要な下流検証または明示Dispositionがない。

期待される下流成果物が存在しないこと自体も未カバーとして判定可能です。

### 不正Disposition

Dispositionは存在するが、使用条件を満たさない。

### 孤立

下流成果物に上流根拠がない。

### 根拠不足

Test CaseやTest ConditionがCurrent Effective Authority / Test Requirement / Product Riskと意味的につながらない。

### 重複

複数ケースが同じ前提、操作、データ意味、期待結果を持ち、新しいCoverageを追加していない。

### 過剰

Product Riskや仕様根拠のない一般的エッジケース、全組合せ、非機能項目等が展開されている。

### 古い / 不整合

Current Effective Authorityと矛盾する成果物、または`要再検証`のまま残る成果物がある。

## 手順

1. 分析モードと対象範囲を定義する
2. Current Effective AuthorityとProduct Riskの対象集合を確定する
3. 各層のIDと上流 / 下流リンク、Dispositionを収集する
4. Authority / Product Risk → Test Requirementの閉鎖性を確認する
5. Test Requirement以降の各層が下流成果物または明示Dispositionへ閉じているか確認する
6. Coverage Criteriaと候補Dispositionの妥当性を確認する
7. Test CaseがCoverage Evidence最低条件を満たすか確認する
8. Product Riskに対する深度不足 / 過剰を確認する
9. Gap、不正Disposition、孤立、重複、根拠不足、不整合を分類する
10. 修正が必要な最も近い担当Skillを示す

## 修正ルーティング

本Skill自身が他層成果物を再設計しません。

- Current Effective Authority / 仕様モデル → `spec-analysis`
- Oracle / 不明点 / Assumption → `question-analysis`
- Product Risk / テスト重点 → `test-analysis`
- Test Requirement / 上流項目Disposition → `test-requirement-design`
- Test Condition / Coverage Criteria / Coverage Item / 候補Disposition → `test-condition-design`
- Test Case → `test-case-design`

ユーザーが「分析して修正まで」と依頼しても、`qa-workflow`を介して担当Skillへ戻します。

## 意味上の出力契約

- 分析範囲 / モード
- Current Effective Authority / Product Riskの閉鎖状況
- Coverage Matrix
- Coverage Criteria充足状況
- Coverage候補Dispositionの妥当性
- Coverage ItemのDisposition
- 未カバー / 不正Disposition / 孤立 / 根拠不足 / 重複 / 不整合
- Product Riskに対する深度不足 / 過剰
- 推奨修正先Skill
- 残存リスク / Blocked

## 停止条件

次の場合は、その比較範囲をBlockedとします。

- 必要ファイル / 情報へアクセスできず比較対象を読めない
- Current Effective Authorityを確定できない
- 成果物のID / 意味が壊れており、何と何を比較すべきか特定できない
- Coverage Criteria自体が未定義で十分性を判定できない

期待される下流成果物が単に存在しない場合はBlockedではなく未カバーです。

一部リンクだけ比較不能なら、他の比較可能範囲は継続します。

## 品質ゲート

- 件数だけでCoverageを判断していない
- IDリンクの存在だけでCoverage済みとしていない
- Current Effective AuthorityとProduct RiskがTest Requirementまたは明示Dispositionへ閉じている
- 各Test Requirement / Test Condition / Coverage Itemが下流成果物または明示Dispositionへ閉じている
- Coverage Criteriaと候補Dispositionの妥当性を確認している
- PairwiseではFactor / Value / Constraintと生成Coverage Itemに基づく2-wise保証を確認している
- 下流成果物不存在を正しく未カバーと判定している
- 不十分なTest CaseをCoverage Evidenceとして数えていない
- 高Product Risk Gapを見落としていない
- 低Product Riskを無言削除の理由にしていない
- Gapの修正先が最も近い責任Skillになっている
- 本Skill自身が他層成果物を再設計していない
