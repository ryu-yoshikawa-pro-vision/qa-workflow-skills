# テスト観点・条件設計 詳細判断基準

## 目的

Test Requirementを、**どの条件・観点で検証するか**へ展開し、適用するテスト技法ごとにCoverage Criteriaと具体的なCoverage Itemを定義します。

実行手順を含むTest Caseへは先回りしません。

## 入力

必須: 何を検証するかが明確なTest Requirement、または同等の成果物。

利用可能なら次も使います。

- 仕様分析
- `test-analysis`（テスト分析）
- 不明点・矛盾分析
- 案件コンテキスト
- Product Risk
- 状態モデル / 業務ルール
- `SPEC` / `DECISION` / `承認済み ASM`

## Oracle Authority

Test Condition / Coverage Itemは次から導きます。

- Test Requirement
- `SPEC`
- `DECISION`
- `承認済み ASM`
- Product Risk分析
- 案件範囲 / 検証方法

Product Risk、エラー推測、テスト仮説、実装情報は候補生成には使えますが、未定義の期待結果を確定するAuthorityにはできません。

## Coverage Criteria

選択した技法や仕様構造に対して、**何をカバーすればその観点を十分検証したと判断するか**を定義します。

技法名を記載しただけでCoverage済みとは判断しません。

## Coverage Item

Coverage Criteriaから導かれる、具体的にカバーすべき要素です。

### 独立表示が必須な条件

次のいずれかに該当する場合はCoverage Itemを明示します。

- 1つのTest Conditionを満たすために複数の具体値、同値クラス、ルール、状態、遷移、経路、組合せが必要
- 技法の充足状況を項目単位で確認しないと十分性を判断できない
- 1つのTest Caseが複数Coverage Itemをカバーする
- 1つのCoverage Itemを複数Test Caseで検証する
- 省略すると後続Coverage Analysisで何を確認済みか一意に判断できない

### Test Conditionへ内包してよい条件

次をすべて満たす場合だけ、独立Coverage Item IDを省略できます。

- Test Condition自体が1つの具体条件を一意に表す
- 必要Coverage要素が1つだけ
- Test Condition → Test Caseの対応だけで十分性を判断できる

「境界」「状態」「権限」などの抽象ラベルだけでは内包済みとみなしません。

## 条件軸の選択

要求ごとに、挙動へ実際に影響する軸だけを選びます。

候補:

- 入力クラス
- 境界
- ロール / 権限
- 状態
- データ有無
- 設定値
- 選択肢組合せ
- ライフサイクル段階
- エラー条件
- 復旧経路
- 操作順序 / 遷移
- シナリオ / 業務経路

形式を埋めるためだけに無関係な軸を追加しません。

## 技法ごとの既定判断

### 同値分割

適用条件: 複数値が同じ挙動になると判断できる場合。

Coverage Criteria:

- 仕様上意味のある各重要同値クラスを少なくとも1つカバーする
- 有効 / 無効クラスがある場合、対象範囲内で意味のあるクラスを明示する

「重要」は仕様、Product Risk、案件範囲で判断します。

### 境界値分析

適用条件: 挙動が境界で変わる場合。

既定:

- 通常は2値境界を基本とする
- 境界実装リスクが高い、過去不具合がある、境界ロジックが複雑、または境界直前 / 直後の差が重要なら3値境界を使う
- 最小 / 最大のどちらを扱うかは仕様上存在する境界に従う

2値 / 3値の採用を明示し、具体Coverage Itemを定義します。未定義の数値境界を創作しません。

### デシジョンテーブル

適用条件: 複数条件の組合せで結果が決まり、列挙漏れや矛盾が起きやすい場合。

Coverage Criteria:

- 仕様上実行可能な各ルールを原則カバーする
- 成立しない組合せは除外理由を残す
- Product Riskに基づきルールを削減する場合は未カバー理由を明示する

### 状態遷移

適用条件: 現在状態とイベントで挙動が変わる場合。

Coverage Criteria:

- 対象範囲内の重要状態をカバーする
- 主要な有効遷移をカバーする
- 無効遷移は仕様、Product Risk、過去不具合等の根拠があるものだけ追加する

全無効遷移を機械生成しません。

### Pairwise / 組合せ

適用条件: 複数の独立軸があり、全組合せが大きすぎ、相互作用リスクが説明できる場合。

Coverage Criteria:

- Pairwiseと表現する場合は、選択因子・値について全2因子組合せを満たすことを確認できる
- 制約で成立しない組合せは明示的に除外する

保証できない場合はPairwiseと呼ばず「代表組合せ」と表現します。

### エラー推測

適用条件: 過去不具合、実装複雑性、既知プラットフォーム挙動、ドメイン固有失敗等の根拠がある場合。

Coverage Criteriaは**選択した失敗仮説を検証すること**です。技法全体の完全網羅とは表現しません。採用仮説と根拠を残します。

### シナリオ / ユースケース

適用条件: 業務フローや複数画面・状態をまたぐ意味のある経路を確認する場合。

Coverage Criteria:

- 主経路をカバーする
- 仕様またはProduct Riskで重要な代替経路 / 例外経路をカバーする
- 業務目的・結果が異なる経路を区別する

## Product Riskによる深度調整

`test-analysis`のリスクレベルを使用します。

- 高: 選択技法のCoverage Criteriaを原則満たし、重要な境界 / 状態 / 権限 / エラー・復旧を積極的に検討する
- 中: 基本Coverageを満たし、追加観点は根拠があるものに限定する
- 低: 主挙動を代表するCoverageを確保し、一般的エッジケースを機械追加しない

リスクレベルだけを理由に未定義挙動を追加しません。

## 手順

1. 対象Test Requirement、テストレベル、Product Risk、対象外、未解決事項を確認する
2. 挙動を変える条件軸を特定する
3. 問題構造に合う技法だけを選ぶ
4. 各重要Test ConditionにCoverage Criteriaを定義する
5. 必要ならCoverage Itemを安定IDで明示する
6. 正常 / 異常 / 復旧は仕様・Product Riskに関連するものだけ検討する
7. 組合せ爆発・重複を抑制する
8. Test Requirement・Specificationへの追跡性を確認する

Coverage Item ID例: `TCN-001-CI01`。

## 組合せ抑制

次の場合は統合・削減を検討します。

- 同じ前提 / データ意味 / Oracleを持つ
- 追加しても新しい仕様責務・Product Risk・Coverage Itemを増やさない
- Pairwise等の技法でCoverageを維持したまま削減できる

削減によってCoverage Criteriaを満たせなくなる場合は削減しません。

## 意味上の出力契約

各重要Test Conditionについて次を表現します。

- 安定したID（例: `TCN-001`）
- 観点 / 条件
- 関連Test Requirement / Specification
- 関連Product Risk / 優先度
- 適用技法
- Coverage Criteria
- Coverage Item（必要時）
- Oracle Authority
- 除外 / 統合根拠
- テストレベル / 観測方法

## 停止条件

次の場合、影響範囲をBlockedとします。

- Test Requirementの意味が曖昧で条件へ展開できない
- 期待挙動を未承認推論で補完しないと条件を作れない
- 重要な状態 / 権限 / 境界定義の矛盾が未解決
- Coverage Criteriaを定義するために不可欠な仕様がない

低リスクの追加観点が不明、任意のError Guessing仮説が不足、全組合せが巨大という理由だけでは停止しません。

## 品質ゲート

- 各重要Test Requirementが少なくとも1つのTest Conditionへ展開されている
- 適用技法にCoverage Criteriaがある
- Coverage Itemの明示 / 内包判断が基準に従っている
- 境界値2値 / 3値の選択理由がある
- Pairwiseと呼ぶ場合に2-wise保証がある
- Error Guessingを完全網羅と表現していない
- Product Riskから未定義Oracleを創作していない
- 一般的QA観点を機械的に追加していない
- 実行手順へ先回りしていない
- 組合せ削減後もCoverage Criteriaを満たす

## 次の担当Skill

- 不明点・期待挙動不明 → `question-analysis`
- ローレベルTest Case設計 → `test-case-design`
