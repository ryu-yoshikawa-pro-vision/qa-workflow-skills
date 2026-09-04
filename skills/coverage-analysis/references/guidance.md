# カバレッジ分析 詳細判断基準

## 目的

Specification / Decision / Approved Assumption、Test Requirement、Test Condition、Coverage Item、Test Caseの意味上のつながりを確認し、**必要なものがケースまで落ちているか**を分析します。

ケース件数やリンク数だけでCoverageを判断しません。

## 入力

分析対象に応じて上流根拠、Test Requirement、Test Condition、Coverage Item、Test Case、Product Risk、適用技法 / Coverage Criteria、対象外 / 残存リスク / Blocked情報を使います。

## 分析モード

### Partial

ユーザーが指定した成果物間だけを比較します。

### Full Workflow

次の隣接リンクをすべて確認します。

- 上流根拠 ↔ Test Requirement
- Test Requirement ↔ Test Condition
- Test Condition ↔ Coverage Item（明示時）
- Coverage Item ↔ Test Case（明示時）
- Test Condition ↔ Test Case（Coverage Item内包時）

必要に応じて上流根拠 ↔ Test CaseのEnd-to-End追跡も確認します。

## Coverageの判断基準

### 上流根拠Coverage

重要な対象仕様・決定・承認済み仮定について、Test Requirementへ意味上の対応があるか確認します。IDがリンクされているだけで検証責務が意味を確認していなければCoverageとはみなしません。

### Test Requirement Coverage

各重要Test Requirementが十分なTest Conditionへ展開されているか確認します。

### Coverage Criteria充足

`test-condition-design`が定義したCoverage Criteriaと候補Dispositionを確認します。

- 同値分割 → 対象Partitionが採用またはDispositionされているか
- 境界値 → 採用した2-value / 3-valueの具体項目があるか
- デシジョンテーブル → 実行可能ルールが採用またはDispositionされているか
- 状態遷移 → 対象状態 / 遷移が採用またはDispositionされているか
- Pairwise → 全成立可能Pairの2-wise保証があるか
- シナリオ → 主経路 / 必要代替・例外経路が採用またはDispositionされているか

技法名が書かれているだけでは充足としません。

### Coverage Item Coverage

明示Coverage Itemは最終的に次のいずれかへ位置づけます。

- Test Caseでカバー
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

Dispositionのない重要Coverage ItemはCoverage Gapです。

### Test CaseをCoverage Evidenceとして扱う最低条件

- どのTest Condition / Coverage Itemを確認するか分かる
- 実施可能な具体性がある
- PASS / FAILを判断できる期待結果がある
- 重要期待結果に一意なOracle根拠がある

詳細なケース品質レビューは`adversarial-review`が担当します。

## Product Riskとの対応

高Product Risk領域では、選択技法のCoverage Criteria、重要境界 / 状態 / 権限 / エラー・復旧、Coverage削減理由を確認します。低Product Risk領域では一般エッジケースの過剰展開を確認します。

## 検出対象

### 未カバー

上流責務またはCoverage Itemに必要な下流検証がない。**期待される下流成果物が存在しないこと自体も未カバーとして判定可能です。**

### 孤立

下流成果物に上流根拠がない。

### 根拠不足

Test CaseやTest Conditionが上流根拠 / Test Requirement / Product Riskと意味的につながらない。

### 重複

複数ケースが同じ前提、操作、データ意味、Oracleを持ち、新しいCoverageを追加していない。

### 過剰

Product Riskや仕様根拠のない一般的エッジケース、全組合せ、非機能項目等が展開されている。

### 古い / 不整合

現在仕様・決定と矛盾する成果物が残っている。

## 手順

1. 分析モードと対象範囲を定義する
2. 対象IDと上流 / 下流リンクを収集する
3. 各リンクが意味上のCoverageになっているか確認する
4. Coverage Criteriaと候補Dispositionを確認する
5. 各重要Coverage ItemのDispositionを確認する
6. Test CaseがCoverage Evidence最低条件を満たすか確認する
7. Product Riskに対する深度不足 / 過剰を確認する
8. Gap、孤立、重複、根拠不足、不整合を分類する
9. 修正が必要な最も近い担当Skillを示す

## 修正ルーティング

本Skill自身が他層成果物を再設計しません。

- 仕様モデル → `spec-analysis`
- Oracle / 不明点 → `question-analysis`
- Product Risk / テスト重点 → `test-analysis`
- Test Requirement → `test-requirement-design`
- Test Condition / Coverage Criteria / Coverage Item → `test-condition-design`
- Test Case → `test-case-design`

ユーザーが「分析して修正まで」と依頼しても、`qa-workflow`を介して担当Skillへ戻します。

## 意味上の出力契約

- 分析範囲 / モード
- Coverage Matrix
- Coverage Criteria充足状況
- Coverage候補のDisposition妥当性
- Coverage ItemのDisposition
- 未カバー / 孤立 / 根拠不足 / 重複 / 不整合
- Product Riskに対する深度不足 / 過剰
- 推奨修正先Skill
- 残存リスク / Blocked

## 停止条件

次の場合は、その比較範囲をBlockedとします。

- 必要ファイル / 情報へアクセスできず比較対象を読めない
- 成果物のID / 意味が壊れており、何と何を比較すべきか特定できない
- Coverage Criteria自体が未定義で十分性を判定できない
- 現行仕様と成果物のどちらが有効か判断できない重大矛盾がある

**期待される下流成果物が単に存在しない場合はBlockedではなく未カバーです。**

一部リンクだけ比較不能なら、他の比較可能範囲は継続します。

## 品質ゲート

- 件数だけでCoverageを判断していない
- IDリンクの存在だけでCoverage済みとしていない
- Coverage Criteriaと候補Dispositionを確認している
- 重要Coverage ItemにDispositionがある
- 下流成果物不存在を正しく未カバーと判定している
- 不十分なTest CaseをCoverage Evidenceとして数えていない
- 高Product Risk Gapを見落としていない
- 低Product Risk領域を過剰展開していない
- Gapの修正先が最も近い責任Skillになっている
- 本Skill自身が他層成果物を再設計していない
