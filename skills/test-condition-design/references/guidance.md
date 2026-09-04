# テスト観点・条件設計 詳細判断基準

## 目的

Test Requirementを、**どの条件・観点で検証するか**へ展開し、適用するテスト技法ごとにCoverage Criteriaと具体的なCoverage Itemを定義します。

実行手順を含むTest Caseへは先回りしません。

## 入力

必須: 何を検証するかが明確なTest Requirement、または同等の成果物。

利用可能なら仕様分析、`test-analysis`、不明点・矛盾分析、案件コンテキスト、Product Risk、状態モデル / 業務ルール、`SPEC` / `DECISION` / `承認済み ASM`も使います。

## Oracle Authority

Test Condition / Coverage ItemはTest Requirement、`SPEC`、`DECISION`、`承認済み ASM`、Product Risk分析、案件範囲 / 検証方法から導きます。

Product Risk、エラー推測、テスト仮説、実装情報は候補生成には使えますが、未定義の期待結果を確定するAuthorityにはできません。

## Coverage設計の基本順序

AIが都合よく候補を省略しないよう、複数候補を持つ技法・仕様構造では次の順で判断します。

1. 仕様・Test Requirementから候補母集団を識別する
2. Coverage Criteriaを定義する
3. Coverage Criteriaを満たす具体Coverage Itemを採用する
4. 候補を除外・削減する場合は、対象外 / 別テストレベル / 残存リスク / 成立不能 / 重複等のDispositionと理由を残す

候補母集団を識別せず、最初から「重要なものだけ」を恣意的に選びません。

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

次をすべて満たす場合だけ独立Coverage Item IDを省略できます。

- Test Condition自体が1つの具体条件を一意に表す
- 必要Coverage要素が1つだけ
- Test Condition → Test Caseの対応だけで十分性を判断できる

「境界」「状態」「権限」などの抽象ラベルだけでは内包済みとみなしません。

## 技法ごとの既定判断

### 同値分割

適用条件: 複数値が同じ挙動になると判断できる場合。

1. 仕様から意味の異なる有効 / 無効Partition候補を先に識別する
2. 対象範囲内の各Partitionを原則1つ以上カバーする
3. 除外するPartitionは理由をDispositionする

「重要ではない」とだけ判断して候補を消しません。

### 境界値分析

適用条件: 順序付け可能な値で、挙動が境界で変わる場合。

- 通常は2-value BVAを既定とする
- 境界実装リスクが高い、過去不具合がある、境界ロジックが複雑、または境界両側の差をより強く確認する必要がある場合は3-value BVAを使う
- 2-valueでは、各境界について境界値と、隣接Partition側の最も近い値をCoverage Itemにする
- 3-valueでは、各境界について境界値と、その両側の最も近い値をCoverage Itemにする
- 値の最小刻み / 精度が仕様やデータ型から決められない場合は、架空の「±1」を作らず、意味のある隣接値を決められるか確認する
- 最小 / 最大のどちらを扱うかは仕様上存在する境界に従う

例: 上限100で整数の場合、2-valueは100 / 101、3-valueは99 / 100 / 101。

2-value / 3-valueの採用理由と具体Coverage Itemを明示します。未定義の数値境界を創作しません。

### デシジョンテーブル

適用条件: 複数条件の組合せで結果が決まり、列挙漏れや矛盾が起きやすい場合。

1. 条件と結果から実行可能ルール候補を識別する
2. 実行可能な各ルールを原則Coverage Itemとする
3. 成立しない組合せは成立不能としてDispositionする
4. Product Risk等で削減する場合は未カバー理由を明示する

### 状態遷移

適用条件: 現在状態とイベントで挙動が変わる場合。

1. 仕様上の状態と遷移候補を先に識別する
2. 対象範囲内の各重要状態と主要有効遷移をCoverage対象にする
3. 対象外にする状態 / 遷移は理由を残す
4. 無効遷移は仕様、Product Risk、過去不具合等の根拠があるものだけ追加する

全無効遷移を機械生成しません。

### Pairwise / 組合せ

適用条件: 複数の独立軸があり、全組合せが大きすぎ、相互作用リスクが説明できる場合。

- Factor / Value候補と制約を先に明示する
- Pairwiseと表現する場合は、成立可能な全Value Pairが少なくとも1ケースへ含まれることを、ツール出力または明示的なPair Coverage確認で検証できること
- 制約で成立しないPairは除外理由を残す

全2-wise Coverageを確認できない場合はPairwiseと呼ばず「代表組合せ」と表現します。

### エラー推測

過去不具合、実装複雑性、既知プラットフォーム挙動、ドメイン固有失敗等の根拠がある場合に使います。

Coverage Criteriaは**選択した失敗仮説を検証すること**です。技法全体の完全網羅とは表現せず、採用仮説と根拠を残します。

### シナリオ / ユースケース

業務フローや複数画面・状態をまたぐ意味のある経路を確認する場合に使います。

1. 仕様上の主経路、代替経路、例外経路候補を識別する
2. 主経路をカバーする
3. 仕様またはProduct Risk上必要な代替 / 例外経路をカバーする
4. 除外する経路は理由を残す

## Product Riskによる深度調整

`test-analysis`のリスクレベルを使用します。

- 高: 選択技法のCoverage Criteriaを原則満たし、重要な境界 / 状態 / 権限 / エラー・復旧を積極的に検討する
- 中: 基本Coverageを満たし、追加観点は根拠があるものに限定する
- 低: 主挙動を代表するCoverageを確保し、一般的エッジケースを機械追加しない

リスクレベルだけを理由に未定義挙動を追加しません。

## 優先度継承

Test Condition / Coverage Itemは関連Test Requirementの最も高い優先度を既定で引き継ぎます。優先度を下げる場合は、対象外、別レベル、重複Coverage等の理由を明示します。

## 手順

1. 対象Test Requirement、テストレベル、Product Risk、対象外、未解決事項を確認する
2. 挙動を変える条件軸を特定する
3. 問題構造に合う技法だけを選ぶ
4. 候補母集団を識別する
5. Coverage Criteriaを定義する
6. Coverage Itemを採用し、除外 / 削減候補をDispositionする
7. 正常 / 異常 / 復旧は仕様・Product Riskに関連するものだけ検討する
8. 組合せ爆発・重複を抑制する
9. Test Requirement・上流根拠への追跡性を確認する

Coverage Item ID例: `TCN-001-CI01`。

## 意味上の出力契約

各重要Test Conditionについて次を表現します。

- 安定ID（例: `TCN-001`）
- 観点 / 条件
- 関連Test Requirement / 上流根拠
- 関連Product Risk / 優先度
- 適用技法
- Coverage Criteria
- Coverage Item（必要時）
- Oracle Authority
- 除外 / 削減 / 統合候補のDispositionと理由
- テストレベル / 観測方法

## 停止条件

次の場合、影響範囲をBlockedとします。

- Test Requirementの意味が曖昧で条件へ展開できない
- 期待挙動を未承認推論で補完しないと条件を作れない
- 重要な状態 / 権限 / 境界定義の矛盾が未解決
- Coverage Criteriaを定義するために不可欠な仕様がない

低リスクの追加観点が不明、任意Error Guessing仮説が不足、全組合せが巨大という理由だけでは停止しません。

## 品質ゲート

- 各重要Test Requirementが少なくとも1つのTest Conditionへ展開されている
- 複数候補を持つ技法で候補母集団を識別している
- 除外・削減候補にDispositionと理由がある
- 適用技法にCoverage Criteriaがある
- Coverage Itemの明示 / 内包判断が基準に従っている
- BVAの具体Coverage Itemが2-value / 3-value規則に従っている
- Pairwiseと呼ぶ場合に2-wise保証の証拠がある
- Error Guessingを完全網羅と表現していない
- Product Riskから未定義Oracleを創作していない
- 一般的QA観点を機械的に追加していない
- 実行手順へ先回りしていない
- 優先度を理由なく下げていない

## 次の担当Skill

- 不明点・期待挙動不明 → `question-analysis`
- ローレベルTest Case設計 → `test-case-design`
