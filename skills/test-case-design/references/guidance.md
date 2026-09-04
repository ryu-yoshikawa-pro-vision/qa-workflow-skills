# ローレベルテストケース設計 詳細判断基準

## 目的

Test Condition / Coverage Itemを、**第三者がケース単体を読んで迷わず実施し、PASS / FAILを判断できるローレベルTest Case**へ変換します。

## 入力

必須:

- 対象Test Condition
- 必要なCoverage Item、またはCoverage Item内包済みの具体Test Condition
- 期待挙動を判断できるCurrent Effective Authority

利用可能ならTest Requirement、Product Risk / 優先度、案件コンテキスト、テストレベル / 観測方法、正式用語、既知制約も使います。

## ローレベル完了基準

**出力するすべてのTest Case**について、ケース単体から次を一意に判断できなければなりません。

1. 誰が / どの状態で開始するか
2. 何を準備するか
3. 何を操作するか
4. 何を入力 / 選択するか
5. 何が起きればPASSか

別ケース、口頭説明、暗黙知を読まないと重要部分を判断できる場合は未完成です。低優先度ケースもこの具体度を下げません。

## Current Effective Authority

完成済みTest Caseの期待結果は、対象スコープのCurrent Effective Authorityへ追跡します。

利用可能なAuthorityは次です。

- 現在有効な`SPEC`
- 状態が`有効`で対象スコープに適用される`DECISION`
- 有効な`SPEC` / `DECISION`で未定義の隙間を補う`承認済み ASM`

Product Risk、実装、既存Test Case、一般的UI慣習、未承認`INFERENCE`、テスターの常識は単独でCurrent Effective Authorityにしません。`撤回` / `置換済み`Decisionを現在の根拠へ使いません。

期待結果を決められない場合は`question-analysis`へ戻します。

### 複数期待結果の根拠

1ケースに複数の重要期待結果がある場合は、期待結果番号とCurrent Effective Authorityを対応付けます。

例:

- 期待結果1 → `SPEC-003`
- 期待結果2 → `DEC-002`

複数根拠を1セルへ並べるだけで、どの期待結果をどの根拠が支えるか不明な状態にしません。

## Coverage Item / Test Conditionの閉鎖

現在レベルで採用済みの各Coverage Itemは、次のいずれかへ位置づけます。

- 1件以上のTest Caseへ接続
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

Coverage Itemを独立表示せずTest Conditionへ内包している場合も、そのTest Conditionを同じようにTest Caseまたは明示Dispositionへ閉じます。

1つのTest Caseが複数Coverage Itemをカバーする場合は、すべてのCoverage Item IDを同じTest Caseへ関連付けます。複数項目を1ケースでカバーできること自体を`重複`Dispositionにはしません。

ケース化しない項目のDispositionは`qa-workflow`の共通Disposition条件に従います。Product Riskが低いことだけを理由に`対象外`へ送りません。

## テストデータ / 状態 / 環境

必要なユーザー、データ、状態、環境は原則として準備可能として設計します。

設計時点ですでに準備不能と分かる条件はケース化せず、妥当なDispositionへ位置づけます。実施時に初めて準備不能と分かった場合は、その時点で実施対象から除外または見直します。

## 優先度

Test Caseは、カバーするTest Condition / Coverage Item / Test Requirementの最も高い優先度を既定で引き継ぎます。

優先度を下げる場合は、別テストレベル、重複Coverage、対象外等の理由を明示します。複数Coverage Itemを1ケースへ統合した場合も最も高い優先度を失いません。

## 手順

### 1. ケース目的を明確にする

タイトル / 目的から何を確認するケースか一意に分かるようにします。

複数Coverage Itemを1ケースでまとめてよいのは、前提条件、操作経路、テストデータ区分、期待結果が実質的に同じ場合です。無関係な目的を1ケースへ詰めません。

### 2. 前提条件を明示する

必要なロール、初期状態、設定、既存データ、画面到達条件を記載し、別ケース実行後の状態を暗黙に前提にしません。

### 3. テストデータを具体化する

Coverage Itemを実行できる具体データへ変換します。準備方法を詳細な運用手順として設計する必要はありません。

### 4. 実施手順を書く

操作主体、画面 / 対象、操作、入力 / 選択を明確にします。「設定する」「確認する」「適切に操作する」等、対象や値が分からない表現を避けます。

### 5. 期待結果を書く

観測可能な結果を具体的に記載します。「正常」「正しく」「問題ない」「適切なメッセージ」等を具体結果の代わりに使いません。

UI中心のシステムテストでは原則UIから観測可能な結果を使い、案件で許可されていないDB / API / ログ観測を勝手にOracleへ追加しません。

### 6. 多段手順と期待結果・根拠を対応付ける

中間結果が次操作の成立条件または合否判定に重要な場合は、手順番号、期待結果番号、必要ならCurrent Effective Authorityを対応させます。

単なる画面遷移等、合否へ意味を持たない中間状態まで過剰に分解しません。

### 7. 事後状態 / 後処理を必要時だけ記載する

ケース実行後の状態が別ケースの独立性へ影響する、再実行の復旧が必要、作成データ / 設定変更が残る場合だけ明示します。

### 8. 正式用語を確認する

仕様・UIに正式名称がある場合はそれを使い、AI独自ラベルを作りません。

### 9. 重複を統合する

前提、操作、データ意味、期待結果が同一で、違いが説明列だけの場合は統合を検討します。関連Test Condition / Coverage Item IDを失わないようにします。

## ケース分離の判断

開始状態、操作経路、期待結果、失敗時の意味、独立性、挙動を変えるデータ区分が異なる場合は分離します。観点名が違うだけでは分離理由になりません。

## 意味上の出力契約

各Test Caseに必要な情報:

- 安定ID（例: `TC-001`）
- タイトル / 目的
- 関連Test Condition
- 関連Coverage Item（明示時）
- 関連Test Requirement
- 優先度
- 前提条件
- テストデータ
- 実施手順
- 期待結果
- 重要期待結果ごとのCurrent Effective Authority
- 必要時の事後状態 / 後処理

Test Caseへ展開しないCoverage Item / 内包Test Conditionには、上流ID、Disposition、理由 / 根拠が必要です。

## 停止条件

次の場合、影響ケースをBlockedとします。

- PASS条件を決めるCurrent Effective Authorityがない
- PASS条件が未承認Assumptionに依存する
- 前提状態や操作対象が重大に不明で具体手順を書けない
- 相反する期待挙動が未解決
- 必要Coverage Itemの意味が曖昧
- 観測手段がなくPASS / FAILを判断できない

データ準備方法が未確定という理由だけでは停止しません。

## 品質ゲート

- **出力したすべてのTest Case**がローレベル完了基準を満たす
- 現在レベルの各Coverage Item / 内包Test ConditionがTest Caseまたは明示Dispositionへ閉じている
- 別ケースの実行結果へ暗黙依存していない
- 開始者 / 開始状態、準備、操作、入力 / 選択、合格条件が明確
- 重要期待結果がCurrent Effective Authorityへ追跡できる
- 複数重要期待結果の根拠対応が一意
- Product Risk / 実装 / 既存テストから未定義Oracleを創作していない
- 観測できない結果を期待結果にしていない
- 1ケースで複数Coverage Itemをカバーする場合も関連IDをすべて保持している
- 統合後も関連IDと最高優先度を失っていない
- 正式用語を使っている
- 曖昧な「正常」「正しい」「適切」を具体結果の代わりに使っていない

## 次の担当Skill

- Current Effective Authority / 期待挙動不明 → `question-analysis`
- Coverage Item不足 / 条件不備 → `test-condition-design`
- Coverage確認 → `coverage-analysis`
