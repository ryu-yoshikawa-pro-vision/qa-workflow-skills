# カバレッジ分析 詳細判断基準

## 目的

Current Effective Authority、Product Risk、Test Requirement、Test Condition、Coverage Item、Test Caseの意味上のつながりを確認し、**対象範囲内の項目が下流成果物または明示Dispositionへ閉じているか**を分析します。

ケース件数やリンク数だけでCoverageを判断しません。

Coverage Criteria / Coverage Itemをどう設計するか、BVA / Pairwise / 状態遷移等の技法固有ルールは`test-condition-design`をSingle Source of Truthとします。本Skillではそれらを再定義せず、入力されたCoverage Criteriaと候補集合に対する充足・閉鎖性を評価します。

## 入力

### Partial

必須:

- 比較対象となるQA成果物
- その成果物について確認したい上流 / 下流関係、Coverage Criteria、またはDisposition判断基準

比較対象が1層だけでも、その層のCoverage CriteriaやDisposition妥当性を評価できる根拠があればPartial分析できます。

### Full Workflow

必須:

- 対象スコープで利用可能なCurrent Effective Authority、Product Risk、Test Requirement、Test Condition、Coverage Item、Test Case
- 適用技法 / Coverage Criteria
- Coverage候補と各層のDisposition情報

存在すべき下流成果物が欠けている場合は、入力不足として停止せず未カバー候補として扱います。

## Function

対象モードに応じて、各層の意味上の追跡関係、閉鎖性、Coverage Criteria充足、Disposition妥当性を確認し、未カバー・不正Disposition・孤立・重複・根拠不足・不整合を検出します。

## 分析モード

### Partial

ユーザーが指定した成果物間、Coverage Criteria、Dispositionだけを比較します。

### Full Workflow

次の閉鎖性を確認します。

1. Current Effective Authority → Test Requirement または明示Disposition
2. Product Risk → Test Requirement または明示Disposition
3. Test Requirement → Test Condition または明示Disposition
4. Test Condition → Coverage Item（明示時）またはTest Case（内包時）、あるいは明示Disposition
5. Coverage Item → Test Case または明示Disposition
6. Coverage候補 → Coverage Item または妥当な候補Disposition

必要に応じてCurrent Effective Authority → Test CaseのEnd-to-End追跡も確認します。

## Coverageの判断基準

### Current Effective Authority Coverage

対象範囲内の現在有効なAuthorityについて、Test Requirementへ意味上の対応があるか、または明示Dispositionがあるか確認します。

Current Effective Authority自体の解決正当性は`spec-analysis`を正本とします。本SkillでSPEC / DECISION / ASMの優先関係を再解決しません。

IDがリンクされているだけで検証責務が意味を確認していなければCoverageとはみなしません。

### Product Risk Coverage

対象範囲内の各Product Riskについて次を確認します。

- 1つ以上のTest Requirementへ接続されているか
- 接続先の優先度・設計深度へProduct Riskが反映されているか
- 接続しない場合は妥当なDispositionがあるか

Risk Matrixの採点自体は`test-analysis`を正本とします。

### Test Requirement Coverage

各Test RequirementがTest Conditionへ展開されているか、または妥当なDispositionへ位置づけられているか確認します。

### Coverage Criteria充足

`test-condition-design`が出力したCoverage Criteria、候補母集団、Coverage Item、候補Dispositionを入力として確認します。

- Coverage Criteriaを満たすCoverage Item / Test Case Evidenceがあるか
- 候補母集団の各対象候補が採用または妥当なDispositionへ閉じているか
- 技法名だけを書いてCoverage済みとしていないか
- Coverage Criteria自体が欠落・曖昧・不整合なら、CriteriaをこのSkillで再設計せず`test-condition-design`へ修正routingする

技法固有の「何をCoverage Criteriaとすべきか」は本Skillへ複製しません。

### Coverage候補Dispositionの妥当性

各候補Dispositionを、`qa-workflow`の共通Dispositionと`test-condition-design`の工程固有条件に照らして確認します。

特に次をGap候補として扱います。

- 低Product Riskだけを理由に`対象外`
- 根拠のない`成立不能`
- カバー先のない`重複`
- 対象内未カバーを理由なしに`残存リスク`
- 設計可能な項目を便宜的に`Blocked`

詳細条件の正本は担当Skillです。本Skillは成果物上の根拠と閉鎖状況を検査します。

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
- PASS / FAIL判定に使う期待結果がCurrent Effective Authorityへ追跡できる

Low-Level Case / Oracleの詳細品質は`test-case-design`、重大度付きCold Reviewは`adversarial-review`を正本とします。

## Product Riskとの深度対応

高Product Risk領域で設計深度が不足していないか、低Product Risk領域で根拠のない過剰展開がないかを確認します。

具体的なRisk採点・深度定義は`test-analysis`を正本とし、本Skillで再採点しません。

## 検出対象

### 未カバー

上流責務、Product Risk、Test Requirement、Coverage Item等に必要な下流検証またはDispositionがない。

期待される下流成果物が存在しないこと自体も未カバーとして判定できます。

### 不正Disposition

Dispositionは存在するが、担当Skillの使用条件を満たさない。

### 孤立

下流成果物に上流根拠がない。

### 根拠不足

Test CaseやTest Conditionが上流成果物と意味的につながらない。

### 重複

複数成果物が同じ検証責務を持ち、新しいCoverageを追加していない。

### 過剰

仕様・Product Risk・Coverage Criteria等の根拠がない検証が展開されている。

### 古い / 不整合

上流成果物と矛盾する、または`要再検証`のまま残る成果物がある。

## 手順

1. 分析モードと対象範囲を定義する
2. 上流Authority / Product Riskの対象集合を確認する
3. 各層のID、上流 / 下流リンク、Dispositionを収集する
4. Authority / Product Risk → Test Requirementの閉鎖性を確認する
5. Test Requirement以降の各層が下流成果物またはDispositionへ閉じているか確認する
6. 入力済みCoverage Criteriaの充足と候補Dispositionを確認する
7. Test CaseがCoverage Evidence最低条件を満たすか確認する
8. Product Riskに対する深度不足 / 過剰を確認する
9. Gap、不正Disposition、孤立、重複、根拠不足、不整合を分類する
10. 修正が必要な最も近い担当Skillを示す

## 修正routing

本Skill自身が他層成果物を再設計しません。

- Current Effective Authority / 仕様モデル → `spec-analysis`
- Oracle / 不明点 / Assumption → `question-analysis`
- Product Risk / テスト重点 → `test-analysis`
- Test Requirement / 上流Disposition → `test-requirement-design`
- Test Condition / Coverage Criteria / Coverage Item / 候補Disposition → `test-condition-design`
- Test Case → `test-case-design`

## 出力

- 分析範囲 / モード
- Authority / Product Riskの閉鎖状況
- Coverage Matrix
- Coverage Criteria充足状況
- Coverage候補Dispositionの妥当性
- Coverage ItemのDisposition
- 未カバー / 不正Disposition / 孤立 / 根拠不足 / 重複 / 不整合
- Product Riskに対する深度不足 / 過剰
- 推奨修正先Skill
- 残存リスク / Blocked

## 停止条件

次の場合、その比較範囲をBlockedとします。

- 必要ファイル / 情報へアクセスできず比較対象を読めない
- Current Effective Authorityを確定できないため上流集合を決められない
- 成果物のID / 意味が壊れており比較関係を特定できない
- Coverage Criteria自体が未定義で、十分性を判定する基準がない

期待される下流成果物が単に存在しない場合はBlockedではなく未カバーです。

## 品質ゲート

- 件数だけでCoverageを判断していない
- IDリンクの存在だけでCoverage済みにしていない
- 各層が下流成果物または妥当なDispositionへ閉じている
- 入力済みCoverage Criteriaの充足を確認している
- Coverage Criteriaを本Skillで再設計していない
- 下流成果物不存在を正しく未カバーと判定している
- 不十分なTest CaseをCoverage Evidenceとして数えていない
- 高Product Risk Gapを見落としていない
- 低Product Riskを無言削除の理由にしていない
- Gapの修正先が最も近い責任Skillになっている
- 本Skill自身が他層成果物を再設計していない
