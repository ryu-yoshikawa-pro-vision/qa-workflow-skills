---
name: test-case-design
description: Test ConditionとCoverage Itemを、第三者が迷わず実施できるローレベルTest Caseへ変換するSkill。前提条件、テストデータ、手順、観測可能な期待結果、Current Effective Authority、独立性を明確にしたテスト項目書を作るときに使用する。
---

# ローレベルテストケース設計

## 実行契約

1. 実行前に `references/guidance.md` を読み、ケース粒度、独立性、Oracle、統合 / 分離、停止条件、品質ゲートに従います。
2. 出力するすべてのケースは単体で、開始者 / 開始状態、準備対象、操作、入力 / 選択、合格条件を判断できる具体度にします。
3. 完成済みケースの期待結果はCurrent Effective Authorityへ追跡します。未承認INFERENCE、Product Risk、実装、既存テスト、一般慣習だけでOracleを確定しません。
4. 多段手順では、次操作の成立条件またはPASS / FAIL判定に必要な中間結果を該当手順番号と対応付けます。
5. 別ケースの独立性や再実行性へ影響する場合だけ、事後状態 / 後処理を明示します。
6. 必要なユーザー・データ・状態・環境は原則準備可能として設計しますが、既知の準備不能条件はケース化しません。
7. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
8. 他Skillを参照するときはCanonical Skill名を使用します。
9. 最終出力前に、実際に利用した入力が本SkillのInput Contractを満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成した成果物へ本Skill自身のOutput Contract・品質ゲートを適用して自己検証します。明白かつ局所的で新しいDomain判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。不足仕様や不明なOracle、未解決AuthorityをSelf-Validationの名目で創作・補完せず、Low-Level完了基準を含む既存契約を正本として扱います。Authority不足、上流判断不足、他SkillのDomain Logicが必要な問題は既存の停止条件・Blocked・routingに従います。最終確認後も本Skill自身の契約違反が残り、既存の停止条件・Blocked・routingに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。Self-Validationの経緯や修正回数は出力しません。

## インターフェース

- **Input**: 対象Test Condition、必要なCoverage ItemまたはCoverage Item内包済みの具体Test Condition、期待挙動を判断できるCurrent Effective Authority。
- **Function**: Test Condition / Coverage Itemを、第三者が単独実施してPASS / FAILを判断できるローレベルTest Caseへ変換し、ケース化しない項目は明示Dispositionへ閉じます。
- **Output**: 安定ID、目的、関連Test Condition / Coverage Item / Test Requirement、前提条件、テストデータ、実施手順、具体的期待結果、Current Effective Authority、必要時の事後状態を持つローレベルTest Caseを作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
