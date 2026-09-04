# カバレッジ分析 詳細判断基準

## 目的

Specification、Test Requirement、Test Condition、Coverage Item、Test Caseの意味上のつながりを確認し、**必要なものがケースまで落ちているか**を分析します。

ケース件数やリンク数だけでCoverageを判断しません。

## 入力

分析対象に応じて次を使います。

- Specification
- Test Requirement
- Test Condition
- Coverage Item
- Test Case
- Product Risk
- 適用技法 / Coverage Criteria
- 対象外 / 残存リスク / Blocked情報

## 分析モード

### Partial

ユーザーが指定した成果物間だけを比較します。

例:

- Test Requirement ↔ Test Condition
- Test Condition ↔ Test Case
- Coverage Item ↔ Test Case

### Full Workflow

次の隣接リンクをすべて確認します。

- Specification ↔ Test Requirement
- Test Requirement ↔ Test Condition
- Test Condition ↔ Coverage Item（明示時）
- Coverage Item ↔ Test Case（明示時）
- Test Condition ↔ Test Case（Coverage Item内包時）

必要に応じてSpecification ↔ Test CaseのEnd-to-End追跡も確認します。

## Coverageの判断基準

### Specification Coverage

重要な対象Specificationについて、Test Requirementへ意味上の対応があるか確認します。

単にIDがリンクされていても、検証責務がSpecificationの意味を確認していなければCoverageとはみなしません。

### Test Requirement Coverage

各重要Test Requirementが、十分なTest Conditionへ展開されているか確認します。

### Coverage Criteria充足

選択技法ごとに、`test-condition-design`（テスト観点・条件設計）が定義したCoverage Criteriaを満たしているか確認します。

例:

- 同値分割 → 必要同値クラスがあるか
- 境界値 → 採用した2値 / 3値の必要項目があるか
- デシジョンテーブル → 対象ルールがDispositionされているか
- 状態遷移 → 重要状態 / 有効遷移が対象になっているか
- Pairwise → 2-wise保証が成立しているか
- シナリオ → 主経路 / 必要代替・例外経路があるか

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

Caseが存在するだけではCoverage Evidenceにしません。最低限次を満たす必要があります。

- どのTest Condition / Coverage Itemを確認するか分かる
- 実施可能な具体性がある
- PASS / FAILを判断できる期待結果がある
- 重要期待結果にOracle根拠がある

詳細なケース品質レビューは`adversarial-review`（反証レビュー）が担当します。

## Product Riskとの対応

高Product Risk領域について次を確認します。

- 選択した技法のCoverage Criteriaを原則満たしているか
- 重要境界 / 状態 / 権限 / エラー・復旧のギャップがないか
- Coverage削減に理由があるか

低Product Risk領域で一般エッジケースを過剰展開していないかも確認します。

## 検出対象

### 未カバー

上流責務またはCoverage Itemに下流検証がない。

### 孤立

下流成果物に上流根拠がない。

### 根拠不足

Test CaseやTest Conditionが、仕様 / Test Requirement / Product Riskと意味的につながらない。

### 重複

複数ケースが同じ前提、操作、データ意味、Oracleを持ち、新しいCoverageを追加していない。

### 過剰

Product Riskや仕様根拠のない一般的エッジケース、全組合せ、非機能項目などが展開されている。

### 古い / 不整合

現在仕様・決定と矛盾する成果物が残っている。

## 手順

1. 分析モードと対象範囲を定義する
2. 対象IDと上流 / 下流リンクを収集する
3. 各リンクが意味上のCoverageになっているか確認する
4. Coverage Criteriaを満たすCoverage Itemが存在するか確認する
5. 各重要Coverage ItemのDispositionを確認する
6. Test CaseがCoverage Evidenceとして最低条件を満たすか確認する
7. Product Riskに対する深度不足 / 過剰を確認する
8. Gap、孤立、重複、根拠不足、不整合を分類する
9. 修正が必要な最も近い担当Skillを示す

## 修正ルーティング

本Skill自身が他層成果物を再設計しません。

- Specification欠陥 → `spec-analysis`
- Oracle / 不明点 → `question-analysis`
- Product Risk / テスト重点 → `test-analysis`
- Test Requirement欠陥 → `test-requirement-design`
- Test Condition / Coverage Criteria / Coverage Item欠陥 → `test-condition-design`
- Test Case欠陥 → `test-case-design`

ユーザーが「分析して修正まで」と依頼しても、`qa-workflow`を介して担当Skillへ戻します。

## 意味上の出力契約

- 分析範囲 / モード
- Coverage Matrix
- Coverage Criteria充足状況
- Coverage ItemのDisposition
- 未カバー / 孤立 / 根拠不足 / 重複 / 不整合
- Product Riskに対する深度不足 / 過剰
- 推奨修正先Skill
- 残存リスク / Blocked

## 停止条件

次の場合は、その比較範囲をBlockedとします。

- 比較対象成果物が存在しない
- ID / 対応関係が壊れており意味上の比較ができない
- Coverage Criteria自体が未定義で十分性を判定できない
- 現行仕様と成果物のどちらが有効か判断できない重大矛盾がある

一部リンクだけが比較不能なら、他の比較可能範囲は継続します。

## 品質ゲート

- 件数だけでCoverageを判断していない
- IDリンクの存在だけでCoverage済みとしていない
- Coverage Criteriaの充足を確認している
- 重要Coverage ItemにDispositionがある
- 不十分なTest CaseをCoverage Evidenceとして数えていない
- 高Product Risk Gapを見落としていない
- 低Product Risk領域を過剰展開していない
- Gapの修正先が最も近い責任Skillになっている
- 本Skill自身が他層成果物を再設計していない
