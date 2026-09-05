# テスト観点・条件設計 基本ガイダンス

## 目的

Test Requirementを、**どの条件・観点で検証するか**へ展開し、Coverage Criteriaと具体的Coverage Itemを定義します。実行手順を含むTest Caseへ先回りしません。

技法固有の規則は`coverage-techniques.md`をSingle Source of Truthとします。

## 入力

必須: 何を検証するかが明確なTest Requirement、または同等の成果物。

利用可能ならCurrent Effective Authority、Product Risk、案件コンテキスト、状態モデル / 業務ルール、不明点・矛盾分析も使います。

## Current Effective Authority

期待挙動はTest Requirementが参照する解決済みCurrent Effective Authorityへ追跡します。

Product Risk、Error Guessing、テスト仮説、実装情報は候補生成に使えますが、未定義の期待結果を確定するAuthorityにはしません。

## Test Requirementの閉鎖

現在レベルの各Test Requirementは次のいずれかへ位置づけます。

- 1つ以上のTest Conditionへ展開
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

Product Riskが低いことだけを理由にTest Requirementを無言で削除しません。

## Coverage設計の基本順序

複数候補を持つ技法・仕様構造では次の順で判断します。

1. 仕様 / Test Requirementから候補母集団を識別する
2. Coverage Criteriaを定義する
3. Coverage Criteriaを満たす具体Coverage Itemを採用する
4. 採用しない候補はDispositionと理由を残す

候補母集団を識別せず、最初から「重要なものだけ」を恣意的に選びません。

## Coverage候補のDisposition

### `対象外`

ユーザー、Project Context、Current Effective Authorityの対象範囲から外れる根拠がある場合だけ使用します。低Product Riskだけを理由に使用しません。

### `別テストレベル`

現在レベルでは適切に検証できず、適切な別レベルを説明できる場合に使用します。

### `残存リスク`

対象内だが意図的に未カバーとする場合に使用します。未カバー内容、理由、関連Product Riskを明示します。

### `成立不能`

仕様、状態モデル、データ制約、業務ルール等から、その候補が成立しない根拠を示せる場合だけ使用します。

### `重複`

別のTest Condition / Coverage Itemで同じ検証責務を保証でき、具体的なカバー先を示せる場合だけ使用します。

### `Blocked`

期待挙動、条件、Authority等の不足により、候補の採否自体を妥当に判断できない場合に使用します。

## Coverage Item

Coverage Criteriaから導かれる、具体的にカバーすべき要素です。

### 独立表示が必要な場合

次のいずれかに該当する場合はCoverage Itemを明示します。

- 1つのTest Conditionを満たすために複数の具体値、Partition、ルール、状態、遷移、経路、組合せが必要
- 技法の充足状況を項目単位で確認しないと十分性を判断できない
- Test Condition → Test Caseだけでは何を確認済みか一意に判断できない

### Test Conditionへ内包してよい場合

次をすべて満たす場合だけ独立Coverage Item IDを省略できます。

- Test Condition自体が1つの具体条件を一意に表す
- 必要Coverage要素が1つだけ
- Test Condition → Test Caseの対応だけで十分性を判断できる

「境界」「状態」「権限」等の抽象ラベルだけでは内包済みとみなしません。

## 技法選択

問題構造に合う技法だけを選びます。技法名を付けること自体を目的にしません。

技法を採用した後、その技法固有の適用条件・既定Coverage・Coverage Item規則を確認する必要がある場合は`coverage-techniques.md`を読みます。

## Product Riskによる深度調整

`test-analysis`で決めたProduct Risk / 設計深度を入力として使用し、このSkillでRisk Matrixを再採点しません。

- 高: 選択技法のCoverage Criteriaを原則満たし、仕様 / Riskに関連する追加条件を積極的に検討
- 中: 基本Coverageを満たし、追加条件は根拠があるものに限定
- 低: 主挙動を代表するCoverageを確保し、一般エッジケースを機械追加しない

低リスクでCoverageを削減する場合も対象内候補を無言で消さず、妥当なDispositionへ位置づけます。

## 優先度継承

Test Condition / Coverage Itemは関連Test Requirementの最も高い優先度を既定で引き継ぎます。優先度を下げる場合は理由を明示します。

## 手順

1. 対象Test Requirement、テストレベル、Product Risk、対象外、未解決事項を確認する
2. Test Conditionへ展開しないTest RequirementをDispositionする
3. 挙動を変える条件軸を特定する
4. 問題構造に合う技法だけを選ぶ
5. 必要なら`coverage-techniques.md`の採用技法の規則を確認する
6. 候補母集団を識別する
7. Coverage Criteriaを定義する
8. Coverage Itemを採用し、採用しない候補をDispositionする
9. 組合せ爆発・重複を抑制する
10. Test Requirement / Current Effective Authorityへの追跡性を確認する

Coverage Item ID例: `TCN-001-CI01`。

## 出力

各Test Conditionについて次を表現します。

- 安定ID
- 観点 / 条件
- 関連Test Requirement / Current Effective Authority
- 関連Product Risk / 優先度
- 適用技法
- Coverage Criteria
- Coverage Item（必要時）

採用しないTest Requirement / Coverage候補にはDispositionと理由が必要です。`重複`の場合はカバー先も必要です。技法固有の追加証拠は`coverage-techniques.md`の規則に従います。

## 停止条件

次の場合、影響範囲をBlockedとします。

- Test Requirementの意味が曖昧で条件へ展開できない
- Current Effective Authorityを解決できない
- 期待挙動を未承認推論で補完しないと条件を作れない
- Coverage Criteriaまたは期待挙動の確定に必要な状態 / 権限 / 境界定義の矛盾が未解決
- Coverage Criteriaを定義するために不可欠な仕様がない

低リスクの追加観点が不明、任意Error Guessing仮説が不足、全組合せが巨大という理由だけでは停止しません。

## 品質ゲート

- 各Test RequirementがTest ConditionまたはDispositionへ閉じている
- 複数候補を持つ構造で候補母集団を識別している
- 採用しない候補に妥当なDispositionと理由がある
- `対象外`を低Product Riskだけの理由で使用していない
- `成立不能`に仕様 / モデル / 制約根拠がある
- `重複`に具体的カバー先がある
- 適用技法にCoverage Criteriaがある
- Coverage Itemの明示 / 内包判断が基準に従っている
- 採用技法がある場合、`coverage-techniques.md`の該当規則を満たしている
- Product Riskから未定義の期待結果を創作していない
- Test Caseへ先回りしていない
- 優先度を理由なく下げていない

## 次の担当Skill

- 不明点・期待挙動不明 → `question-analysis`
- Low-Level Test Case設計 → `test-case-design`
