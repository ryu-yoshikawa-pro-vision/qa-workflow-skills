# 反証レビュー 基本ガイダンス

## 目的

QA成果物を肯定するためではなく、誤り・抜け・過剰・根拠不足・追跡性欠陥をCold Reviewし、重大度と修正先を示します。

成果物別の詳細プローブは対象成果物に応じたreferenceだけを読みます。

## 入力

必須:

- レビュー対象QA成果物

判定対象に応じて利用:

- Current Effective Authority
- Product Risk
- Coverage Criteria
- Canonical Registry
- 案件コンテキスト
- 前後QA成果物
- 既存の残存リスク / Blocked情報

必要根拠がない観点は断定せず、レビュー制約 / 判定不能として明示します。判定可能な範囲は継続します。

## レビュー姿勢

- 生成時の意図・説明を正当化根拠にしない
- 利用可能な上流根拠と成果物から判断を再構成する
- 「一般的には必要」を理由に欠陥を作らない
- 好みと欠陥を分ける
- 工程固有の詳細規則は担当SkillをSingle Source of Truthとする

同一AIが自己レビューする場合も、生成時の推論をそのまま引き継がずCold Reviewします。

## Domain Logic参照先

| 対象 | 詳細判断の正本 |
| --- | --- |
| Current Effective Authority / 仕様分類 | `spec-analysis` |
| 不明点 / Assumption / 回答正規化 | `question-analysis` |
| Product Risk | `test-analysis` |
| Test Requirement | `test-requirement-design` |
| Coverage Criteria / Item / 技法 | `test-condition-design` |
| Low-Level Test Case / Oracle | `test-case-design` |
| Coverage / Gap | `coverage-analysis` |
| 重大度 / Cold Review処置 | `adversarial-review` |

本Skillのprobeは「どこを疑うか」を示します。担当Skillの詳細アルゴリズムを別正本として複製しません。

## 重大度

### `致命的`

成果物が重大に誤ったQA判断 / 実行を導き、修正なしで安全に利用できない。

例: 期待結果が有効Authorityと逆、主要責務の大規模欠落、Oracle創作、追跡関係の重大破綻。

処置は`修正済み`または`Blocked`です。残存リスク受容だけで利用可能状態にしません。

### `重大`

Coverage、追跡性、実行可能性、Oracle信頼性等を実質的に弱め、通常は利用前に修正すべき。

処置は`修正済み`、権限を持つユーザー / ステークホルダーによる明示的な`残存リスクとして受容`、または`Blocked`です。

残存リスクとして受容する場合は承認参照を記録します。

### `軽微`

実在する品質問題だが、全体妥当性への影響は限定的。

### `提案`

現在の欠陥ではない任意改善。

重大度は好みや修正工数ではなく、成果物利用時の影響で決めます。

## 対象別reference

レビュー対象に応じて必要なreferenceだけを読みます。

- 仕様分析 / Current Effective Authority / 不明点 / Assumption → `authority-question-probes.md`
- Product Risk / Test Requirement / Test Condition / Coverage Item / Test Case → `test-design-probes.md`
- Coverage Analysis / 残存リスク → `coverage-probes.md`

複数成果物を横断レビューする場合は該当するreferenceを複数読みます。

## 機能固有の欠陥プローブ

リロード、二重操作、セッション切れ、複数タブ、空値、境界、特殊文字 / IME、権限変更、状態復旧、日時境界、互換性等は、仕様・Product Risk・既存失敗等の根拠がある場合だけ検討します。

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

`致命的` / `重大`修正後は影響範囲を再レビューします。修正が下流の意味・追跡関係を変える場合は`qa-workflow`の変更伝播へ戻します。

## 出力

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

判定できない範囲はレビュー制約として別途明示します。

## 品質ゲート

- 指摘が利用可能なAuthority・Product Risk・Coverage Criteria・成果物契約等の根拠を持つ
- 根拠不足の観点を断定していない
- 好みを欠陥として報告していない
- 一般的チェックリストを機械適用していない
- `致命的` / `重大`の影響説明が具体的
- `致命的`を残存リスク受容だけで完了させていない
- `重大`の残存リスク受容に明示承認と承認参照がある
- 修正先が最も早い責任Skillになっている
- 工程固有のDomain Logicを本Skillで再定義していない
- 修正後の再レビュー範囲が妥当

## 出力前自己検証

最終出力前に、本Skill自身のInput / Output Contract、停止条件、既存の品質ゲートをレビュー結果へ再適用します。品質基準は本ガイダンスと対象成果物に応じて利用した既存referenceを正本とし、Self-Validation専用のrubricやチェックリストを別定義しません。

確認対象は本Skill自身のレビュー出力契約に限ります。Self-Validationでレビュー結果そのものへ新しいSemantic Judgeを重ねたり、対象成果物を再度Cold Reviewしたりしません。

1. 自身の品質ゲートを満たしているか確認する
2. 明白かつ局所的で、新しいDomain判断を必要としない契約違反だけを最大1回修正する
3. 修正後は修正箇所を含めて最終確認する。最終確認で問題が残っても2回目の自動修正は行わない
4. 解消に新しいAuthority、上流判断、他SkillのDomain Logicが必要な場合は自力で補完しない
5. その場合は既存の停止条件・Blocked・routingに従う

Self-Validationの経緯、PASS表示、修正履歴は通常成果物へ出力せず、現在有効な最終状態だけを返します。
