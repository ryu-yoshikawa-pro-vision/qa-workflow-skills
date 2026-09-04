# 反証レビュー 詳細判断基準

## 目的

QA成果物を肯定するためではなく、**誤り・抜け・過剰・根拠不足・追跡性欠陥**を見つけるためにレビューします。

対象:

- 仕様分析 / Current Effective Authority
- 不明点・矛盾分析 / Assumption管理
- テスト分析 / Product Risk
- Test Requirement
- Test Condition / Coverage Item
- ローレベルTest Case
- Coverage Analysis

## レビュー姿勢

- 生成時の意図・説明を正当化根拠にしない
- 権威ある情報源、Canonical Registry、成果物から判断を再構成する
- 「一般的には必要」を理由に欠陥を作らない
- 実在するProduct Risk、Current Effective Authority、Coverage Criteria、ケース実行性へ結び付けて指摘する
- 好みと欠陥を分ける

同一AIが自己レビューする場合も、生成時の推論を引き継いで正当化せずCold Reviewとして上流根拠から再判定します。

## 重大度

### `致命的`

成果物が重大に誤ったQA判断 / 実行を導き、修正なしで安全に利用できない。

例: 期待結果がCurrent Effective Authorityと逆、主要業務責務が大規模欠落、Oracle創作、追跡関係破綻。

処置は`修正済み`または`Blocked`のみです。残存リスク受容だけで利用可能状態にしません。

### `重大`

Coverage、追跡性、実行可能性、Oracle信頼性を実質的に弱め、通常は利用前に修正すべき。

処置は`修正済み`、権限を持つユーザー / ステークホルダーが明示的に`残存リスクとして受容`、または`Blocked`です。残存リスクとして受容する場合は、誰のどの承認に基づくかを追跡できる承認参照を記録します。

### `軽微`

実在する品質問題だが、全体妥当性への影響は限定的。

### `提案`

現在の欠陥ではない任意改善。

重大度は好みや修正工数ではなく成果物利用時の影響で決めます。

## 成果物別プローブ

### 仕様分析 / Current Effective Authority

- `SPEC` / `DECISION` / `INFERENCE` / `UNKNOWN`を混同していないか
- IDが分類と一致しているか
- `DEC-xxx`をCanonical Registryと別IDで重複管理していないか
- 対象スコープに適用される有効Decisionを、上書き有無に関係なくAuthority候補として確認しているか
- `撤回` / `置換済み`Decisionを現在のOracleにしていないか
- 有効Decisionの補足 / 上書き / 置換関係と影響範囲が追跡できるか
- `ASM`で有効な`SPEC` / `DECISION`を上書きしていないか
- 各情報源の現行版を特定した後に情報源優先順位を適用しているか
- 鮮度だけで低優先度情報源を優先していないか
- 実装・既存テストを仕様Authorityへ昇格していないか
- 同一スコープの有効Authority競合を未解決のまま下流へ流していないか

### 不明点・Assumption

- 本来Blockerの事項を`要確認` / `仮定可能`へ下げていないか
- 最終PASS条件が未承認Assumptionへ依存していないか
- AI自身の判断で`ASM-xxx`を`承認済み`にしていないか
- 正式挙動として確定した回答をAssumptionのまま残していないか
- 回答後の期待挙動が`SPEC` / `DECISION` / `承認済み ASM`へ正規化されているか
- 解決済み事項を再質問していないか
- Blocked範囲を必要以上に広げていないか

### テスト分析 / Product Risk

- Product Riskだけをリスク評価へ使っているか
- Risk Matrixを正しく適用しているか
- 判断材料不足だけを理由に発生可能性1へ下げていないか
- 影響度4を低リスク扱いしていないか
- リスクレベルが設計深度へ接続されているか
- 低Product Riskを上流責務の無言削除理由にしていないか
- 一般的QAチェックリストを根拠なくスコープ化していないか

### Test Requirement

- 各Test RequirementがCurrent Effective Authorityへ追跡できるか
- 対象内の各Current Effective AuthorityがTest Requirementまたは明示Dispositionへ閉じているか
- 対象内の各Product RiskがTest Requirementまたは明示Dispositionへ閉じているか
- 上流記載の言い換えだけでなく検証責務になっているか
- Product Riskや実装から期待挙動を創作していないか
- 無関係な責務を過剰統合していないか
- 優先度を理由なく下げていないか

### Test Condition / Coverage Item

- 現在レベルの各Test RequirementがTest Conditionまたは明示Dispositionへ閉じているか
- 候補母集団を識別せず恣意的に項目を省略していないか
- 採用しない候補にDispositionと理由があるか
- 低Product Riskだけを理由に`対象外`を使用していないか
- `成立不能`に仕様 / モデル / 制約の根拠があるか
- `重複`に具体的カバー先があるか
- 適用技法にCoverage Criteriaがあるか
- Coverage Itemの明示 / 内包判断が一意か
- BVAの具体項目が採用方式に合うか
- 状態遷移で対象範囲内の全有効遷移がCoverageまたは妥当なDispositionへ閉じているか
- Pairwiseを名乗る2-wise保証があるか
- Error Guessingを完全網羅と表現していないか

### ローレベルTest Case

**出力されたすべてのTest Case**について、開始者 / 開始状態、準備、操作、入力 / 選択、PASS条件を確認します。

さらに:

- 現在レベルの各Coverage Item / 内包Test ConditionがTest Caseまたは明示Dispositionへ閉じているか
- 別ケースの暗黙状態へ依存していないか
- 正式用語を使っているか
- 期待結果が観測可能か
- 重要期待結果ごとにCurrent Effective Authorityへ一意に追跡できるか
- Product Risk / 実装 / 既存テストを未定義Oracleにしていないか
- 許可されていないDB / API / ログ観測を要求していないか
- 優先度を理由なく下げていないか
- 重複または過剰統合がないか

### Coverage Analysis

- Current Effective Authority / Product RiskからTest Caseまでの各層が下流接続または明示Dispositionへ閉じているか
- Product Riskが下流へ接続されず消えていないか
- 件数比較を意味上のCoverageとして扱っていないか
- Coverage Criteriaと候補Dispositionの妥当性を確認しているか
- 下流成果物不存在を未カバーではなくBlockedと誤判定していないか
- 高Product Risk Gapを見落としていないか
- 不十分なTest CaseをCoverage済みと誤認していないか
- `要再検証`の成果物を最新成果物として数えていないか

## 残存リスクのレビュー

高Product Riskを意図的な未カバーとして`残存リスク`へ位置づける場合は、少なくとも`重大`候補として扱い、未カバー内容・影響・受容根拠を確認します。明示的な受容がない場合は処置済みとみなしません。

重大度が`致命的`に相当するかは、未カバーによる成果物利用時の影響で判断します。

## 機能固有の欠陥プローブ

仕様・Product Riskに関連する場合だけ、リロード、二重操作、セッション切れ、複数タブ、空値、境界、特殊文字 / IME、権限変更、状態復旧、日時境界、互換性等を検討します。

一覧に存在するという理由だけで「抜け」と判定しません。

## 修正責務

指摘は最も早い責任層へ戻します。

- Current Effective Authority / 仕様モデル → `spec-analysis`
- 不明点 / Assumption / Oracle不明 → `question-analysis`
- Product Risk / テスト重点 → `test-analysis`
- Test Requirement / 上流Disposition → `test-requirement-design`
- Test Condition / Coverage Criteria / Coverage Item / 候補Disposition → `test-condition-design`
- Test Case / Coverage ItemからTest Caseへの閉鎖 → `test-case-design`
- Coverage判定 → `coverage-analysis`
- 案件固有設定 / Canonical Registry → Project Context / 仕様決定

本Skill自身が他層成果物を再設計しません。

## 再レビュー

`致命的` / `重大`修正後は影響範囲を再レビューします。修正が下流の意味・追跡関係を変える場合は`qa-workflow`の変更伝播規則に従います。

## 意味上の出力契約

各指摘に必要な情報:

- 指摘ID
- 重大度
- 対象成果物 / ID
- 問題
- 根拠
- 影響
- 推奨修正先Skill
- 処置状態
- `重大`を残存リスクとして受容する場合の処置根拠 / 承認参照

## 品質ゲート

- 指摘がCurrent Effective Authority・Product Risk・Coverage Criteria等の根拠を持つ
- 好みを欠陥として報告していない
- 一般的チェックリストを機械適用していない
- `致命的` / `重大`の影響説明が具体的
- `致命的`を残存リスク受容だけで完了させていない
- `重大`の残存リスク受容に明示的な承認があり、承認参照を追跡できる
- 高Product Riskの未カバーを無処置で見逃していない
- 修正先が最も早い責任Skillになっている
- 本Skill自身が他層成果物を書き換えていない
- 修正後の再レビュー範囲が妥当

本Skillは正式なISTQB / ISOのインスペクション手順そのものではなく、このワークフロー向けの反証レビューです。
