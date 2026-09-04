# QA Workflow 詳細判断基準

## 目的

複数のQA Skillを成果物ベースでルーティングし、新規機能・変更機能・指定対象機能を、テスト実施者が迷わず実行できるローレベルテストケースまで落とし込みます。

本ガイダンスはルーティング、停止・再開、再利用、変更伝播、完了判断だけを定義します。詳細な分析・設計判断は各担当Skillへ委譲します。

## Canonical Skill名

Skill参照には次のCanonical Skill名だけを使用します。

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

要求成果物に必要なSkillが利用できない場合は、そのSkillが必要になる範囲をBlockedとして扱い、利用可能な範囲だけで妥当性を保てる作業は継続します。利用できないSkillの責務を別Skillへ無理に肩代わりさせません。

## 成果物チェーン

```text
Source
  ↓
Specification / Decision / Approved Assumption
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

Coverage Itemは`test-condition-design`の内部成果物です。反証レビューはどの成果物層にも適用できます。

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

既存成果物は、次を軽量確認したうえで再利用します。

1. 現在の対象範囲に適合する
2. 現在の仕様・決定に対して十分新しい
3. 情報源優先順位・確定事項と矛盾しない
4. 担当Skillの意味上の出力契約を満たす
5. 後続判断に必要な追跡情報がある

1つでも後続判断を壊す不備がある場合は、その不備を修正できる最も近い担当Skillへ戻します。

適合性確認だけを理由に成果物全体を再生成しません。

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

Blockerは成果物単位・範囲単位で判断します。

- その不明点が対象成果物の正しさを成立させない → Blocker
- 回答で設計が変わり得るが、現時点でも妥当な成果物を作れる → 要確認
- 最終Oracleを確定しない範囲で明示的仮定により安全に進められる → 仮定可能
- 任意改善 → 提案・任意

完成済みTest CaseのPASS / FAILが未承認仮定に依存する場合は`仮定可能`ではなくBlockerです。

一部範囲だけがBlockedなら、妥当性を維持できる他範囲は継続します。

## 情報源の矛盾

1. 案件固有の情報源優先順位を確認する
2. 優先順位で解決できる場合は高優先度情報源を期待挙動として採用する
3. 低優先度側の矛盾証拠も保持する
4. 相互排他的な挙動を混ぜない
5. 解決できない重大矛盾は`question-analysis`へ送る

上位情報源で期待挙動が決まっている場合、低優先度の実装差分は仕様質問ではなく不具合・差分候補として扱います。

## 修正ルーティング

カバレッジ分析・反証レビューで欠陥を見つけた場合は、最も早い責任層へ戻します。

- 仕様モデル → `spec-analysis`
- 不明点・Oracle不明 → `question-analysis`
- Product Risk・テスト重点・技法選択 → `test-analysis`
- テスト要求 → `test-requirement-design`
- テスト観点・Coverage Criteria・Coverage Item → `test-condition-design`
- ローレベルケース → `test-case-design`

`coverage-analysis`と`adversarial-review`は他層成果物を直接再設計しません。

## 上流変更の伝播

上流成果物を修正し、その意味が下流成果物へ影響する場合は、影響する下流成果物を再検証前の状態として扱います。

1. 変更した最も早い成果物を特定する
2. 直接・間接に依存する下流成果物の影響範囲を特定する
3. 影響範囲だけを各担当Skillの品質ゲートで再検証し、必要なものだけ修正する
4. フルワークフローまたはカバレッジ確認を要求されている場合は`coverage-analysis`を再実行する
5. 反証レビューまで要求されている場合は、意味が変わった範囲を`adversarial-review`で再確認する

上流変更を理由に無関係な下流成果物まで全再生成しません。

## カバレッジ分析の必須リンク

フルワークフローでは、存在する次の隣接関係を確認します。

- Specification / Decision / Approved Assumption ↔ Test Requirement
- Test Requirement ↔ Test Condition
- Test Condition ↔ Coverage Item（明示時）
- Coverage Item ↔ Test Case（明示時）
- Test Condition ↔ Test Case（Coverage Item内包時）

必要に応じて上流根拠 ↔ Test CaseのEnd-to-End追跡も確認します。

重要なCoverage Itemは最終的に次のいずれかへ位置づけます。

- テストケースでカバー
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

## 完了条件

要求されたフルワークフローは、対象範囲について次をすべて満たしたとき完了です。

- 必要な成果物が存在する
- 各担当Skillの品質ゲートを満たす
- 必要な追跡性がある
- 重要なCoverage ItemがすべてDispositionされている
- テストケースがローレベルで単独実施可能
- 重要期待結果にOracle根拠がある
- 必要なカバレッジ分析・反証レビューが完了している
- 反証レビューの`致命的`指摘がすべて修正済み、またはBlockedとして利用停止されている
- `重大`指摘が修正済み、明示的に残存リスクとして受容、またはBlockedとなっている

重要なBlocked範囲が残る場合は、Blocked範囲と再開条件を明示し、無条件に完了とはしません。

## 品質ゲート

- Skill参照がCanonical Skill名で一意か
- 要求成果物に必要なSkillが利用可能か
- 不要な上流Skillを再実行していないか
- Blockerを必要以上に全体へ広げていないか
- 修正を最も近い責任Skillへ戻しているか
- 上流修正後の影響下流を再検証しているか
- 各Skillの責務境界を維持しているか
- 完了判定が成果物の存在だけでなく品質ゲート・追跡性・Blocker状態を見ているか
