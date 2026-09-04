---
name: coverage-analysis
description: Current Effective Authority、Product Risk、Test Requirement、Test Condition、Coverage Item、Test Caseの追跡関係と意味上のCoverageを分析し、各層が下流成果物または明示Dispositionへ閉じているか、未カバー・不正Disposition・孤立・重複・根拠不足がないか確認するSkill。テスト設計全体の抜け・過剰・閉鎖性を確認するときに使用する。
---

# カバレッジ分析

## 実行契約

1. 実行前に `references/guidance.md` を読み、比較モード、追跡性、閉鎖性、Coverage Criteria充足、Disposition妥当性、停止条件、品質ゲートに従います。
2. ケース件数やリンク数だけでCoverageを判断せず、意味上の対応を確認します。
3. Current Effective Authority / Product RiskからTest Caseまで、各対象項目が下流成果物または明示Dispositionへ閉じているか確認します。
4. 選択技法のCoverage CriteriaとCoverage候補Dispositionが実際に妥当か確認します。
5. Test CaseがCoverage Evidenceとして使える最低限の具体性とOracle根拠を持つか確認します。詳細なケース品質レビューは `adversarial-review`（反証レビュー）へ委ねます。
6. ギャップを発見しても本Skill自身が他層成果物を再設計せず、`qa-workflow`を介して最も近い担当Skillへ戻します。
7. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
8. 他Skillを参照するときはCanonical Skill名を使用します。

## 出力

カバレッジ範囲、Authority / Product Riskの閉鎖状況、追跡マトリクス、Coverage Criteria充足、Coverage候補Disposition妥当性、Coverage ItemのDisposition、未カバー / 孤立 / 重複 / 根拠不足、推奨修正先を示します。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
