# テスト設計成果物レビュー Probes

このreferenceは、Product Risk、Test Requirement、Test Condition / Coverage Item、Low-Level Test Caseを反証レビューする場合だけ読みます。

工程固有の詳細ルールは各担当SkillをSingle Source of Truthとします。

## Product Risk / テスト分析

主に次を疑います。

- Project RiskをProduct Risk評価へ混ぜていないか
- Riskに仕様 / 変更 / 依存等の根拠があるか
- 根拠不足を理由に発生可能性を不当に低くしていないか
- Risk levelが設計深度へつながっているか
- 低Riskを対象責務の無言削除理由にしていないか
- Riskや一般論から未定義の製品期待を創作していないか

Risk Matrixや採点ルールの詳細は`test-analysis`を正本とします。

## Test Requirement

主に次を疑います。

- Current Effective Authorityへ追跡できる検証責務になっているか
- 上流記載の単なる言い換えになっていないか
- 対象内Authority / Product RiskがTest Requirementまたは妥当なDispositionへ閉じているか
- Product Riskや実装から期待挙動を創作していないか
- 無関係な責務を過剰統合していないか
- 具体条件 / 手順へ早すぎる具体化をしていないか

粒度・分割・閉鎖の詳細は`test-requirement-design`を正本とします。

## Test Condition / Coverage Item

主に次を疑います。

- Test RequirementがTest Conditionまたは妥当なDispositionへ閉じているか
- 候補母集団を識別せず恣意的に候補を省略していないか
- 採用しない候補に根拠付きDispositionがあるか
- 技法名だけでCoverage Criteriaを定義した扱いにしていないか
- Coverage Itemの具体性が不足していないか
- Product Riskや仮説から未定義の期待挙動を創作していないか
- Test Caseの実行手順へ先回りしていないか

BVA / Pairwise / 状態遷移等の技法固有Coverageルールは`test-condition-design`を正本とし、本referenceでは再定義しません。

## Low-Level Test Case

主に次を疑います。

- ケース単体で開始者 / 開始状態、準備、操作、入力 / 選択、PASS条件を判断できるか
- Coverage Item / 内包Test ConditionがTest Caseまたは妥当なDispositionへ閉じているか
- 別ケースの実行結果へ暗黙依存していないか
- 期待結果が観測可能か
- PASS / FAIL判定に使う期待結果がCurrent Effective Authorityへ追跡できるか
- Product Risk / 実装 / 既存Test Case / 一般慣習から未定義Oracleを創作していないか
- 許可されていない観測手段を勝手に追加していないか
- 無関係な目的を1ケースへ過剰統合していないか
- 正式用語ではなくAI独自ラベルを作っていないか

Low-Level具体性、case分離 / 統合、Oracle具体化の詳細は`test-case-design`を正本とします。
