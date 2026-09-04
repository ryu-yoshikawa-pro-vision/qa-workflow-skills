# QA Workflow 詳細判断基準

## 目的

複数のQA Skillを成果物ベースでルーティングし、新規機能・変更機能・指定対象機能を、テスト実施者が迷わず実行できるローレベルテストケースまで落とし込みます。

本ガイダンスはルーティング、停止・再開、再利用、変更伝播、成果物チェーンの閉じ方、完了判断を定義します。各工程固有の分析・設計判断は担当Skillへ委譲します。

## 入力

必須:

- ユーザー要求
- 要求する最終成果物
- 識別可能な対象範囲

利用可能なら情報源、既存QA成果物、案件コンテキスト、進行モード、既知のBlocked / 残存リスク / `要再検証`状態、既存のCanonical Registryも使います。

情報源や既存QA成果物がまだないこと自体は`qa-workflow`の起動を妨げません。要求成果物に必要な担当Skillへルーティングした後、そのSkillの必須入力を満たさない範囲をBlockedとして扱います。

要求成果物が仕様分析、Test Requirement、Test Case、Coverage Analysis等の途中成果物である場合も、その成果物を最終成果物として扱えます。

## Function

要求成果物を作るための最も早い開始Skillを決め、既存成果物の再利用可否、Skillルーティング、Blocked / 再開、上流変更の伝播、修正ルーティング、Workflow全体状態と完了判定を制御します。工程固有のQA判断は担当Skillへ委譲します。

## 出力

- ユーザーが要求した最終QA成果物
- 必要に応じたWorkflow状態（`完了` / `部分完了（Blockedあり）` / `Blocked`）
- Blocked範囲と再開条件
- 残存リスク
- `要再検証`対象
- 必要な再開先 / 修正先Skill

## Canonical Skill名

- `spec-analysis`（仕様分析）
- `question-analysis`（不明点・矛盾分析）
- `test-analysis`（テスト分析）
- `test-requirement-design`（テスト要求設計）
- `test-condition-design`（テスト観点・条件設計）
- `test-case-design`（ローレベルテストケース設計）
- `coverage-analysis`（カバレッジ分析）
- `adversarial-review`（反証レビュー）

番号や実行順はSkill識別子として使用しません。

## フルワークフローの利用前提

フルワークフローを実行する場合は、`qa-workflow`と上記8個のQA Skillが利用可能であることを確認します。

要求成果物に必要なSkillが利用できない場合は、そのSkillが必要になる範囲をBlockedとして扱います。利用できないSkillの責務を別Skillへ無理に肩代わりさせません。

## 成果物チェーン

```text
Current Effective Authority
  ↓
Test Requirement
  ↓
Test Condition
  ↓
Coverage Item
  ↓
Test Case
  ↓
Coverage Analysis
```

Product Riskはテスト深度・優先度を決める横断入力としてTest Requirement以降へ追跡します。

Coverage Itemは`test-condition-design`の内部成果物です。反証レビューはどの成果物層にも適用できます。

## Current Effective Authority

製品の期待挙動を判断するときは、単に`SPEC` / `DECISION` / `承認済み ASM`を列挙するのではなく、対象スコープで現在有効なAuthorityを確定します。

1. Canonical Decision Registryから、状態が`有効`で対象スコープに適用される`DECISION`をすべてAuthority候補として識別する。既存`SPEC` / 旧`DECISION`を上書きしていない補足Decisionも候補に含める
2. 有効`DECISION`が既存Authorityと重なる場合は、補足 / 上書き / 置換関係、関連Authority、影響範囲から現在有効な内容を解決する。未定義領域を補足するDecisionは既存Authorityと共存できる
3. `SPEC`は、まず各情報源内で対象Version / Scopeに適用される現行版を版・更新時点から特定する
4. 現行版の`SPEC`候補間では案件固有の情報源優先順位を適用する。鮮度だけを理由に低優先度情報源を高優先度情報源より優先しない
5. `承認済み ASM`は有効な`SPEC` / `DECISION`で未定義の隙間だけを暫定的に補える
6. `ASM`が有効な`SPEC` / `DECISION`と競合する場合、`ASM`で上書きせず、正式な仕様更新または`DECISION`として解決する
7. 同一スコープで有効Authorityが競合し、Decision関係・情報源優先順位等で解決できない場合は`question-analysis`へ送り、影響範囲をBlockedとする

`DEC-xxx` / `ASM-xxx`の状態と関係はProject Contextまたは案件で明示されたCanonical Registryを正本とします。`spec-analysis`では解決済みAuthorityを正規化ビューとして明示します。

## 成果物チェーンの閉鎖原則

フルワークフローでは、対象範囲内の項目を無言で消しません。

### 上流Authority

現在有効で対象範囲内の各`SPEC` / `DECISION` / `承認済み ASM`は、次のいずれかへ位置づけます。

- 1つ以上のTest Requirementへ接続
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

### Product Risk

対象範囲内の各Product Riskは、次のいずれかへ位置づけます。

- 1つ以上のTest Requirementへ接続し、下流の深度・優先度へ反映
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

### Test Requirement以降

現在レベルで検証対象とした各Test Requirement、Test Condition、Coverage Itemは、次の下流成果物へ接続するか、明示Dispositionを持たせます。

Product Riskが低いことだけを理由に、対象内の上流項目を無言で削除しません。Product Riskは主にCoverageの深さ・優先度を調整します。

## 共通Disposition

### `対象外`

ユーザー、Project Context、または現在有効な上流スコープで対象外と判断できる場合だけ使用します。Product Riskが低いという理由だけでは使用しません。

### `別テストレベル`

現在のテストレベルでは適切に検証できず、より適切なテストレベルを説明できる場合に使用します。

### `残存リスク`

対象範囲内だが意図的に未カバーとする場合に使用します。理由、影響するProduct Risk、未カバー内容を明示します。

### `Blocked`

Authority不足、重大な矛盾、必要情報不足などにより、妥当な設計判断自体を確定できない場合に使用します。

工程固有のDisposition（例: `成立不能`、`重複`）は担当Skillが追加定義します。

## 開始点

要求された最終成果物を作るために必要な、最も早いSkillから開始します。

例:

- 仕様整理だけ → `spec-analysis`
- 有効な仕様分析がありテスト分析が必要 → `test-analysis`
- 有効な観点・Coverage Itemがありケースだけ必要 → `test-case-design`
- 既存成果物の抜け確認 → `coverage-analysis`
- 成果物の反証レビュー → `adversarial-review`

常に`spec-analysis`から開始しません。

## 既存成果物の再利用

既存成果物は次を軽量確認したうえで再利用します。

1. 現在の対象範囲に適合する
2. Current Effective Authorityに対して十分新しい
3. 情報源優先順位・Canonical Registryと矛盾しない
4. 担当Skillの意味上の出力契約を満たす
5. 後続判断に必要な追跡情報がある

後続判断を壊す不備がある場合は、その不備を修正できる最も近い担当Skillへ戻します。適合性確認だけを理由に成果物全体を再生成しません。

## 既定フロー

```text
spec-analysis
  ↓
question-analysis
  ↓
test-analysis
  ↓
test-requirement-design
  ↓
test-condition-design
  ↓
test-case-design
  ↓
coverage-analysis
  ↓
adversarial-review
```

これは依存関係を理解するための既定経路であり、全依頼で全Skillを実行する義務ではありません。

## 進行モード

### `continuous`

既定モード。現在Skillの品質ゲートを通過し、Blockerがなければ要求成果物まで継続します。非Blockerは可視化したまま進めます。

### `gated`

ユーザーまたは案件コンテキストが指定した場合に使用します。現在Skillの成果物を提示した時点で停止し、次Skillを自動実行しません。

優先順位:

1. ユーザーの明示指示
2. 案件コンテキスト
3. `continuous`

## 不明点・矛盾のルーティング

どのSkillからでも、期待挙動や設計判断に重大な不明点・矛盾を発見した場合は`question-analysis`へ送れます。

- 対象成果物の正しさを成立させない → Blocker
- 回答で設計が変わり得るが現在情報でも妥当な成果物を作れる → 要確認
- 最終Oracleを確定しない範囲で明示的仮定により安全に進められる → 仮定可能
- 任意改善 → 提案・任意

完成済みTest CaseのPASS / FAILが未承認仮定に依存する場合はBlockerです。

一部範囲だけがBlockedなら、妥当性を維持できる他範囲は継続します。

## 修正ルーティング

カバレッジ分析・反証レビューで欠陥を見つけた場合は、最も早い責任層へ戻します。

- 仕様モデル / Current Effective Authority → `spec-analysis`
- 不明点・Assumption・Oracle不明 → `question-analysis`
- Product Risk・テスト重点・技法選択 → `test-analysis`
- Test Requirement → `test-requirement-design`
- Test Condition・Coverage Criteria・Coverage Item → `test-condition-design`
- Test Case → `test-case-design`

`coverage-analysis`と`adversarial-review`は他層成果物を直接再設計しません。

## 上流変更の伝播

上流成果物の意味が変わった場合は、影響する下流成果物を`要再検証`として扱います。

1. 変更した最も早い成果物を特定する
2. 直接・間接に依存する下流成果物の影響範囲を特定する
3. 影響範囲だけを各担当Skillの品質ゲートで再検証し、必要なものだけ修正する
4. Coverage確認を要求されている場合は`coverage-analysis`を再実行する
5. 反証レビューまで要求されている場合は、意味が変わった範囲を`adversarial-review`で再確認する

無関係な下流成果物まで全再生成しません。

## Workflow全体状態

- `完了`: 対象スコープ内にBlockedと`要再検証`が残らず、完了条件をすべて満たす
- `部分完了（Blockedあり）`: Blocked以外の範囲は完了しているが、対象スコープ内に局所Blockedが残る
- `Blocked`: Blockedにより要求成果物について意味のある完了範囲を確定できない

局所Blockedがあっても他範囲の作業は継続できますが、対象スコープ内にBlockedが残るFull Workflowを無条件に`完了`とはしません。

## 完了条件

要求されたフルワークフローは、対象範囲について次をすべて満たしたとき`完了`です。

- Current Effective Authorityが解決されている
- 対象内の上流AuthorityとProduct RiskがTest Requirementまたは明示Dispositionへ閉じている
- 現在レベルのTest Requirement / Test Condition / Coverage Itemが下流成果物または明示Dispositionへ閉じている
- 各担当Skillの品質ゲートを満たす
- 必要な追跡性がある
- 出力されたすべてのTest Caseがローレベルで単独実施可能
- PASS / FAIL判定に使用する各期待結果が、1件以上のCurrent Effective AuthorityまたはAuthority集合へ曖昧なく追跡できる
- 必要なカバレッジ分析・反証レビューが完了している
- `要再検証`の対象が残っていない
- 対象スコープ内にBlockedが残っていない
- 反証レビューの`致命的`指摘がすべて修正済み
- `重大`指摘が修正済み、または明示的な承認根拠付きで残存リスクとして受容されている

`致命的` / `重大`指摘がBlockedとなっている場合、その範囲は利用停止できますが、対象スコープ内にBlockedが残るためWorkflow全体は`完了`にせず、Blocked範囲と再開条件を明示して`部分完了（Blockedあり）`または`Blocked`とします。

## 品質ゲート

- Skill参照がCanonical Skill名で一意か
- 要求成果物に必要なSkillが利用可能か
- Current Effective Authorityが競合したまま下流へ進んでいないか
- 対象内項目を低Product Risk等の理由で無言削除していないか
- Blockerを必要以上に全体へ広げていないか
- 修正を最も近い責任Skillへ戻しているか
- 上流修正後の影響下流を`要再検証`として再確認しているか
- 各Skillの責務境界を維持しているか
- 完了判定が成果物の存在だけでなく閉鎖性・品質ゲート・追跡性・Blocker状態を見ているか
