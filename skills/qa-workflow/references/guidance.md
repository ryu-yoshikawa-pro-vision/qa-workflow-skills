# QA Workflow Orchestration詳細

## 目的

複数QA Skillを成果物ベースでroutingし、開始点、再利用、Blocked / 再開、変更伝播、修正先、Workflow全体状態を管理します。

工程固有の判断規則は担当SkillをSingle Source of Truthとし、本ガイダンスへ複製しません。

## 入力

必須:

- ユーザー要求
- 要求する最終成果物
- 識別可能な対象範囲

利用可能なら情報源、既存QA成果物、案件コンテキスト、進行モード、既知のBlocked / 残存リスク / `要再検証`状態、Canonical Registryも使います。

情報源や既存QA成果物がまだないこと自体は`qa-workflow`の起動を妨げません。担当Skillへrouting後、そのSkillの必須入力を満たさない範囲をBlockedとして扱います。

## Runtime前提

フルワークフローでは次の9 Skillが同一Agent client上で利用可能であることを前提とします。

- `qa-workflow`
- `spec-analysis`
- `question-analysis`
- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`
- `adversarial-review`

Agent Skills Specificationは共通Skill-to-Skill invocation APIを規定しません。本Workflowは、Agent clientが必要なSkillを追加ロード / 利用できる実装で動作することを前提とします。

必要Skillを利用できない場合は、そのSkillの責務を別Skillへ肩代わりさせず、必要範囲をBlockedとして扱います。

## Domain LogicのSingle Source of Truth

| Domain Logic | 担当Skill |
| --- | --- |
| Current Effective Authorityの解決 | `spec-analysis` |
| 不明点分類 / 回答正規化 | `question-analysis` |
| Product Risk / Risk Matrix / 設計深度 | `test-analysis` |
| Test Requirement粒度 / 上流閉鎖 | `test-requirement-design` |
| Coverage Criteria / Item / テスト技法 | `test-condition-design` |
| Low-Level Case / Oracle具体化 | `test-case-design` |
| Coverage / 閉鎖性 / Gap | `coverage-analysis` |
| Cold Review / 重大度 | `adversarial-review` |
| routing / Blocked / 再開 / 変更伝播 / 完了 | `qa-workflow` |

### Current Effective Authority依存

製品期待挙動のCurrent Effective Authorityが必要な場合は、`spec-analysis`の有効成果物を使用します。

既存`spec-analysis`成果物が対象範囲のCurrent Effective Authorityを十分に解決していない、古い、または競合を残している場合は`spec-analysis`へ戻します。

`qa-workflow`自身は、SPEC / DECISION / ASMの優先関係、version選択、情報源優先順位、Authority競合解消を行いません。

### その他Domain Logic依存

- Product Riskの採点が必要 → `test-analysis`
- Test Requirementの粒度判断が必要 → `test-requirement-design`
- BVA / Pairwise / 状態遷移等の具体Coverage判断が必要 → `test-condition-design`
- Test CaseのOracle / 具体性判断が必要 → `test-case-design`
- Coverage判定が必要 → `coverage-analysis`
- 重大度付きCold Reviewが必要 → `adversarial-review`

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

Product Riskは深度・優先度の横断入力です。反証レビューは各成果物層に適用できます。

フルワークフローでは、対象範囲内の上流項目を無言で消しません。各担当Skillが定義する下流成果物または妥当なDispositionへ閉じていることを、Workflow全体状態として確認します。

## 共通Disposition

### `対象外`

ユーザー、Project Context、または現在有効な対象範囲から外れる根拠がある場合に使用します。低Product Riskだけを理由に使用しません。

### `別テストレベル`

現在レベルでは適切に検証できず、より適切なテストレベルを説明できる場合に使用します。

### `残存リスク`

対象範囲内だが意図的に未カバーとする場合に使用します。理由、関連Product Risk、未カバー内容を明示します。

### `Blocked`

必要Authority、重大な矛盾、必須入力不足等により、妥当な設計判断を確定できない範囲に使用します。

工程固有Disposition（例: `成立不能`、`重複`）の詳細条件は担当Skillを正本とします。

## 開始点

要求成果物を作るために必要な、最も早い担当Skillから開始します。

例:

- 仕様整理だけ → `spec-analysis`
- 有効な仕様分析がありテスト重点を決める → `test-analysis`
- 有効なTest Condition / Coverage Itemがありケースだけ作る → `test-case-design`
- 成果物チェーンの抜け・閉鎖性を見る → `coverage-analysis`
- 成果物を重大度付きでCold Reviewする → `adversarial-review`

常に`spec-analysis`から開始しません。

## 既存成果物の再利用

既存成果物は次を軽量確認して再利用します。

1. 現在の対象範囲に適合する
2. 関連上流成果物に対して陳腐化していない
3. 担当Skillの意味上の出力契約を満たす
4. 後続判断に必要な追跡情報がある
5. `要再検証` / Blockedのまま利用可能扱いされていない

工程固有の妥当性が疑わしい場合は、詳細規則を`qa-workflow`で再評価せず担当Skillへ戻します。

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

これは依存関係を理解するための既定経路です。要求成果物と有効な既存成果物に応じて途中から開始・終了できます。

## 進行モード

### `continuous`

既定モード。現在Skillの成果物が次工程へ利用可能で、局所Blockerがなければ要求成果物まで継続します。非Blockerは可視化したまま進めます。

### `gated`

ユーザーまたは案件コンテキストが指定した場合に使用します。現在Skillの成果物を提示した時点で停止し、次Skillを自動実行しません。

優先順位:

1. ユーザーの明示指示
2. 案件コンテキスト
3. `continuous`

## 不明点・矛盾のrouting

どの工程でも、下流成果物の妥当性を阻害する未解決事項を発見した場合は`question-analysis`へ送れます。

分類自体は`question-analysis`を正本とし、`qa-workflow`は返されたBlocked範囲、継続可否、再開先をWorkflow状態へ反映します。

一部範囲だけがBlockedなら、妥当性を維持できる他範囲は継続します。

## 修正routing

Coverage Analysis / Adversarial Review等で欠陥を見つけた場合は、最も早い責任Skillへ戻します。

- 仕様モデル / Current Effective Authority → `spec-analysis`
- 不明点 / Assumption / Oracle不明 → `question-analysis`
- Product Risk / テスト重点 → `test-analysis`
- Test Requirement → `test-requirement-design`
- Test Condition / Coverage Criteria / Coverage Item → `test-condition-design`
- Test Case → `test-case-design`
- Coverage判定自体 → `coverage-analysis`

レビューSkill自身や`qa-workflow`が担当層を直接再設計しません。

## 上流変更の伝播

上流成果物の意味が変わった場合は、影響する下流成果物を`要再検証`として扱います。

1. 変更した最も早い成果物を特定する
2. 直接・間接に依存する下流の影響範囲を特定する
3. 影響範囲だけを担当Skillへ戻す
4. 担当Skillで再検証・必要修正する
5. Coverage確認が要求される場合は`coverage-analysis`を再実行する
6. Cold Reviewが要求される場合は意味が変わった範囲を`adversarial-review`で再確認する

無関係な下流成果物まで全再生成しません。

## Workflow全体状態

- `完了`: 対象スコープ内にBlockedと`要再検証`が残らず、要求成果物の完了条件を満たす
- `部分完了（Blockedあり）`: Blocked以外は完了しているが、対象スコープ内に局所Blockedが残る
- `Blocked`: Blockedにより要求成果物について意味のある完了範囲を確定できない

## Full Workflow完了条件

対象範囲について次を満たしたとき`完了`です。

- `spec-analysis`で必要なCurrent Effective Authorityが解決済み
- 対象内の上流Authority / Product Risk / Test Requirement / Test Condition / Coverage Itemが、担当Skillの契約に従って下流成果物またはDispositionへ閉じている
- 各担当Skillの最低品質条件を満たす
- 必要な追跡性がある
- 出力Test Caseが`test-case-design`のLow-Level完了条件を満たす
- 必要なCoverage Analysis / Adversarial Reviewが完了している
- `要再検証`が残っていない
- 対象スコープ内にBlockedが残っていない
- `adversarial-review`で利用停止が必要な未処置指摘が残っていない

重大度の詳細条件や残存リスク受容条件は`adversarial-review`を正本とします。

## 品質ゲート

- Orchestration以外のDomain Logicを再定義していない
- 要求成果物に対して適切な開始Skillを選んでいる
- 有効な既存成果物を不要に再生成していない
- 必要Skillの欠如を別Skillで肩代わりしていない
- Blockedを必要以上に全体へ広げていない
- 修正を最も早い責任Skillへ戻している
- 上流修正後の影響下流だけを`要再検証`している
- 完了判定が成果物の存在だけでなく状態・閉鎖性・各担当Skillの契約を見ている

## 出力前自己検証

最終出力前に、実際に利用した入力が本SkillのInput Contractを満たし、入力・Authority・判断状態に停止条件へ該当する未解決状態がないか確認します。あわせて、生成したOrchestration成果物へ本SkillのOutput Contractと既存の品質ゲートを再適用します。品質基準は本ガイダンスの既存定義を正本とし、Self-Validation専用のrubricやチェックリストを別定義しません。

確認対象は開始Skill、既存成果物の再利用、Blocked / 再開、変更伝播、修正routing、Workflow完了判定など、本Skillが所有するOrchestration契約に限ります。他SkillのDomain Logicを再評価・再設計しません。

1. 実際に利用した入力がInput Contractを満たし、停止条件へ該当する未解決状態がないか確認する
2. 生成したOrchestration成果物がOutput Contractと既存の品質ゲートを満たしているか確認する
3. 明白かつ局所的で、新しいDomain判断を必要としないOrchestration契約違反だけを最大1回修正する
4. 修正後は修正箇所を含めて最終確認する。解消に新しいAuthority、上流判断、他SkillのDomain Logicが必要な場合は自力で補完せず、既存の停止条件・Blocked・routingに従う
5. 最終確認後も本Skill自身のOrchestration契約違反が残り、既存の停止条件・Blocked・routingに該当しない場合は、2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わない。現在残っている契約上の制約だけを明示する

既存の`Blocked`定義をSelf-Validationの未解消ローカル違反へ広げません。Self-Validationの実行経緯、修正回数、修正前状態、PASS / FAIL等の評価ログは通常成果物へ出力せず、現在有効な状態と未解消の契約上の制約だけを返します。
