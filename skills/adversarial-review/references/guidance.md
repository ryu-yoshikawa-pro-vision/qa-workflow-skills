# 反証レビュー 詳細判断基準

## 目的

QA成果物を肯定するためではなく、**誤り・抜け・過剰・根拠不足・追跡性欠陥**を見つけるためにレビューします。

対象:

- 仕様分析
- 不明点・矛盾分析 / Assumption管理
- テスト分析
- Test Requirement
- Test Condition / Coverage Item
- ローレベルTest Case
- Coverage Analysis

## レビュー姿勢

- 生成時の意図・説明を正当化根拠にしない
- 権威ある情報源と成果物から判断を再構成する
- 「一般的には必要」を理由に欠陥を作らない
- 実在するProduct Risk、仕様、Coverage Criteria、ケース実行性へ結び付けて指摘する
- 好みと欠陥を分ける

同一AIが自己レビューする場合も、生成時の推論を引き継いで正当化せずCold Reviewとして上流根拠から再判定します。

## 重大度

### `致命的`

成果物が重大に誤ったQA判断 / 実行を導き、修正なしで安全に利用できない。

例: 期待結果が権威ある仕様と逆、主要業務責務が大規模欠落、Oracle創作、追跡関係破綻。

**処置は`修正済み`または`Blocked`のみです。残存リスク受容だけで利用可能状態にしません。**

### `重大`

Coverage、追跡性、実行可能性、Oracle信頼性を実質的に弱め、通常は利用前に修正すべき。

処置は`修正済み`、権限を持つユーザー / ステークホルダーが明示的に`残存リスクとして受容`、または`Blocked`です。

### `軽微`

実在する品質問題だが、全体妥当性への影響は限定的。

### `提案`

現在の欠陥ではない任意改善。

重大度は好みや修正工数ではなく成果物利用時の影響で決めます。

## 成果物別プローブ

### 仕様分析

- `SPEC` / `DECISION` / `INFERENCE` / `UNKNOWN`を混同していないか
- IDが分類と一致しているか
- `DEC-xxx`をCanonical Registryと別IDで重複管理していないか
- 情報源優先順位を正しく適用しているか
- 実装・既存テストを仕様Authorityへ昇格していないか
- 重要ルール、状態、フロー、制約が欠落していないか
- 正式用語を独自名称へ置換していないか

### 不明点・Assumption

- 本来Blockerの事項を`要確認` / `仮定可能`へ下げていないか
- 最終PASS条件が未承認Assumptionへ依存していないか
- AI自身の判断で`ASM-xxx`を`承認済み`にしていないか
- 承認済みAssumptionがCanonical Registryへ一意に記録されているか
- 解決済み事項を再質問していないか
- Blocked範囲を必要以上に広げていないか
- 再開先Skillが適切か

### テスト分析

- Product Riskだけをリスク評価へ使っているか
- Risk Matrixを正しく適用しているか
- 影響度4を低リスク扱いしていないか
- リスクレベルが設計深度へ接続されているか
- 一般的QAチェックリストを根拠なくスコープ化していないか
- テストレベル / 観測方法が要求に合っているか

### Test Requirement

- 上流根拠へ追跡できるか
- Specificationの言い換えだけでなく検証責務になっているか
- Product Riskや実装から期待挙動を創作していないか
- 無関係な責務を過剰統合していないか
- 優先度を理由なく下げていないか

### Test Condition / Coverage Item

- 候補母集団を識別せず恣意的に項目を省略していないか
- 除外・削減候補にDispositionと理由があるか
- 適用技法にCoverage Criteriaがあるか
- Coverage Itemの明示 / 内包判断が一意か
- BVAの具体項目が採用方式に合うか
- Pairwiseを名乗る2-wise保証があるか
- Error Guessingを完全網羅と表現していないか
- 不要な条件軸 / 全組合せを追加していないか

### ローレベルTest Case

各重要ケースについて、開始者 / 開始状態、準備、操作、入力 / 選択、PASS条件を確認します。

さらに:

- 別ケースの暗黙状態へ依存していないか
- 正式用語を使っているか
- 期待結果が観測可能か
- 重要期待結果ごとに`SPEC` / `DECISION` / `承認済み ASM`へ一意に追跡できるか
- Product Risk / 実装 / 既存テストを未定義Oracleにしていないか
- 許可されていないDB / API / ログ観測を要求していないか
- 必要Coverage Itemがケースへ落ちているか
- 優先度を理由なく下げていないか
- 重複または過剰統合がないか

### Coverage Analysis

- 件数比較を意味上のCoverageとして扱っていないか
- Coverage Criteriaと候補Dispositionを確認しているか
- 重要Coverage ItemがDispositionされているか
- 下流成果物不存在を未カバーではなくBlockedと誤判定していないか
- 高Product Risk Gapを見落としていないか
- 不十分なTest CaseをCoverage済みと誤認していないか

## 機能固有の欠陥プローブ

仕様・Product Riskに関連する場合だけ、リロード、二重操作、セッション切れ、複数タブ、空値、境界、特殊文字 / IME、権限変更、状態復旧、日時境界、互換性等を検討します。

一覧に存在するという理由だけで「抜け」と判定しません。

## 修正責務

指摘は最も早い責任層へ戻します。

- 仕様モデル → `spec-analysis`
- 不明点 / Assumption / Oracle不明 → `question-analysis`
- Product Risk / テスト重点 → `test-analysis`
- Test Requirement → `test-requirement-design`
- Test Condition / Coverage Criteria / Coverage Item → `test-condition-design`
- Test Case → `test-case-design`
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

## 品質ゲート

- 指摘が権威ある情報源・Product Risk・Coverage Criteria等の根拠を持つ
- 好みを欠陥として報告していない
- 一般的チェックリストを機械適用していない
- `致命的` / `重大`の影響説明が具体的
- `致命的`を残存リスク受容だけで完了させていない
- `重大`の残存リスク受容に明示的な承認がある
- 修正先が最も早い責任Skillになっている
- 本Skill自身が他層成果物を書き換えていない
- 修正後の再レビュー範囲が妥当

本Skillは正式なISTQB / ISOのインスペクション手順そのものではなく、このワークフロー向けの反証レビューです。
