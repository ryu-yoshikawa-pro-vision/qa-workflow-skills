---
name: coverage-analysis
description: Specification、Test Requirement、Test Condition、Coverage Item、Test Caseの追跡関係と意味上のカバレッジを分析し、未カバー・孤立・重複・根拠不足を検出するSkill。テスト設計が必要範囲を十分にケースへ落とせているか確認するときに使用する。
---

# カバレッジ分析

## 実行契約

1. 実行前に `references/guidance.md` を読み、比較モード、追跡性、Coverage Criteria充足、Disposition、停止条件、品質ゲートに従います。
2. ケース件数やリンク数だけでカバレッジを判断せず、意味上の対応を確認します。
3. 選択技法のCoverage Criteriaと必要Coverage Itemが実際に満たされているか確認します。
4. ローレベルケースがCoverage Evidenceとして使える最低限の具体性とOracle根拠を持つか確認します。詳細なケース品質レビューは `adversarial-review`（反証レビュー）へ委ねます。
5. ギャップを発見しても本Skill自身が他層成果物を再設計せず、`qa-workflow`を介して最も近い担当Skillへ戻します。
6. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
7. 他Skillを参照するときはCanonical Skill名を使用します。

## 出力

カバレッジ範囲、追跡マトリクス、Coverage Criteria充足状況、未カバー / 孤立 / 重複 / 根拠不足、Coverage ItemのDisposition、推奨修正先を示します。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
