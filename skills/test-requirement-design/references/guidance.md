# テスト要求設計 詳細判断基準

## 目的

仕様分析とテスト分析から、**何を検証・保証する必要があるか**をTest Requirementとして定義します。

Test Requirementはこのワークフロー固有の中間成果物であり、Current Effective AuthorityとTest Conditionの間で検証責務を安定させ、AIが条件やケースへ早すぎる具体化をするのを防ぎます。

## 入力

必須:

- 対象範囲のCurrent Effective Authority
- テスト対象範囲

利用可能なら`test-analysis`のProduct Risk / テスト重点、案件コンテキスト、不明点・矛盾分析、テストレベル / 観測方法も使います。

## Current Effective Authority

Test Requirementが製品の期待挙動を含む場合、対象スコープで解決済みのCurrent Effective Authorityへ追跡します。

Current Effective Authority候補は次です。

- 現在有効な`SPEC`
- 状態が`有効`の`DECISION`
- 有効な`SPEC` / `DECISION`で未定義の隙間を補う`承認済み ASM`

Product Risk、実装、既存テスト、一般的慣習、未承認`INFERENCE`は単独で期待挙動を確定するAuthorityにはできません。`撤回` / `置換済み`Decisionを現在の根拠へ使いません。

## 抽象度

Test Requirementは「何を検証するか」を表します。

含める:

- 検証対象の挙動 / ルール / 品質責務
- 期待される成立条件の意味
- Current Effective Authority
- Product Risk / 優先度
- テストレベル / 観測方法

含めない:

- 具体的入力値の列挙
- 境界値の具体展開
- 組合せ表
- 実行手順
- テストケースの前提 / データ / Step

Test Requirementは上流記載の言い換えだけでは不十分です。「何を保証すればその上流責務が検証されたと言えるか」が独立して分かる検証責務へ変換します。

## 上流項目の閉鎖

フルワークフローでは、対象範囲内の上流項目を無言で消しません。

### Current Effective Authority

対象内の各Current Effective Authorityは、次のいずれかへ位置づけます。

- 1つ以上のTest Requirementへ接続
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

### Product Risk

対象内の各Product Riskも、次のいずれかへ位置づけます。

- 1つ以上のTest Requirementへ接続
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

Product Riskが低いことだけを理由に、Current Effective AuthorityまたはProduct Riskを下流から消しません。

Dispositionの意味は`qa-workflow`の共通Dispositionに従います。

## 分割・統合の判断

1つにまとめてよいのは、守るべき製品挙動、Current Effective Authority、失敗時の意味、テストレベルが同じ検証責務として扱える場合です。

異なる業務ルール、権限責務、状態 / ライフサイクル責務、期待挙動の意味、または追跡責務を持つ場合は分割します。ケース数削減のために無関係な責務を統合しません。

## 優先度

関連Product Riskがある場合は、その最も高いリスクレベルを既定優先度として引き継ぎます。案件固有の明示的重点がある場合はそれも考慮できます。

上流より優先度を下げる場合は、別テストレベル、重複責務等の理由を明示します。理由なく高い上流優先度を下げません。

## 手順

1. 対象範囲のCurrent Effective Authority、Product Risk、テストレベルを確認する
2. 「この上流責務が正しく実装されていると判断するために、何を保証する必要があるか」を検証責務として抽出する
3. 関連Product Riskを優先度・深度根拠として接続する
4. Test Requirementを作らないCurrent Effective Authority / Product Riskは共通Dispositionへ位置づける
5. 各Test Requirementが少なくとも1つのCurrent Effective Authorityへ戻れることを確認する
6. 対象内のCurrent Effective Authority / Product Riskに未処理項目がないことを確認する

## 意味上の出力契約

各Test Requirementに必要な情報:

- 安定ID（例: `TR-001`）
- 検証責務
- Current Effective Authority
- 関連Product Risk
- 優先度
- テストレベル / 観測方法

Test Requirementを作らない上流項目には、上流ID、種別、Disposition、理由が必要です。

## 停止条件

次の場合、影響要求をBlockedとします。

- 何を保証すべきかをCurrent Effective Authorityから決められない
- 期待挙動を未承認推論で埋めないと要求を書けない
- Current Effective Authorityが未解決
- 対象範囲そのものが特定できない

Product Riskが未評価でも上流責務自体が明確ならTest Requirement作成は可能です。その場合は優先度根拠の制約を明示します。

## 品質ゲート

- 各Test RequirementがCurrent Effective Authorityへ追跡できる
- 対象内の各Current Effective AuthorityがTest Requirementまたは明示Dispositionへ閉じている
- 対象内の各Product RiskがTest Requirementまたは明示Dispositionへ閉じている
- 上流記載の単なる言い換えではなく検証責務になっている
- Product Riskを期待挙動のAuthorityにしていない
- 未承認`INFERENCE`を完成済み要求の根拠にしていない
- 「何を検証するか」に留まり、具体条件 / 手順を先回りしていない
- 要求同士の重複・過剰統合がない
- Product Riskが低いという理由だけで上流項目を消していない
- 優先度にProduct Riskまたは明示的案件重点の理由があり、上流より下げる場合は理由がある

## 次の担当Skill

- 不明点・期待挙動不明 → `question-analysis`
- Test Condition / Coverage Item設計 → `test-condition-design`
