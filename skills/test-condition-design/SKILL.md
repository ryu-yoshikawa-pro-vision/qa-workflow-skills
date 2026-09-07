---
name: test-condition-design
description: Test Requirementを、どの条件・観点で検証するかへ展開し、同値分割、境界値分析、デシジョンテーブル、状態遷移、Pairwise、エラー推測、シナリオなどのCoverage CriteriaとCoverage Itemを定義するSkill。候補母集団とDispositionを管理し、テストケース設計前に必要Coverageを具体化するときに使用する。
---

# テスト観点・条件設計

## 実行契約

1. Test Requirementを「どの条件・観点で検証するか」へ展開し、実行手順は`test-case-design`へ委ねます。
2. 複数候補を持つ場合は候補母集団を先に識別し、Coverage Criteria、Coverage Item、採用しない候補のDispositionを明示します。
3. 期待挙動をProduct Riskやテスト仮説から創作しません。
4. Coverage設計の基本手順、閉鎖、Disposition、停止条件、最低品質は`references/guidance.md`に従います。
5. 同値分割、BVA、Decision Table、状態遷移、Pairwise、Error Guessing、Scenario等を実際に適用する場合だけ`references/coverage-techniques.md`を追加で読み、採用技法の規則を使います。
6. 既定出力形式が必要な場合は`assets/output-template.md`を使用します。
7. 他Skillを参照するときはCanonical Skill名を使用します。
8. 最終出力前に、実際に利用した入力が本SkillのInput Contractを満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成した成果物へ本Skill自身のOutput Contract・品質ゲートを適用して自己検証します。明白かつ局所的で新しいDomain判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。Self-Validationを理由にCoverage Strategyを根本から再設計したり、未定義の期待結果やOracleを追加したりしません。Authority不足、上流判断不足、他SkillのDomain Logicが必要な問題は推測補完せず既存の停止条件・Blocked・routingに従います。最終確認後も本Skill自身の契約違反が残り、既存の停止条件・Blocked・routingに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。Self-Validationの経緯や修正回数は出力しません。

## インターフェース

- **Input**: 何を検証するかが明確なTest Requirementまたは同等の成果物。Current Effective Authority、Product Risk、状態モデル / 業務ルール等は利用可能な場合に補助入力とします。
- **Function**: Test Requirementを検証条件へ展開し、問題構造に合う技法、Coverage Criteria、Coverage Item、採用しない候補のDispositionを定義します。
- **Output**: Test Condition、適用技法、Coverage Criteria、必要なCoverage Item、関連Test Requirement / Authority / Product Risk、優先度、Test RequirementとCoverage候補のDispositionを作ります。

## 基本停止条件

- Test Requirementの意味が曖昧で条件へ展開できない
- Current Effective Authorityを解決できない
- 未承認推論で期待挙動を補わないと条件を作れない
- Coverage Criteriaを定義するために不可欠な仕様がない

低リスクの追加観点が不明、任意Error Guessing仮説が不足、全組合せが巨大という理由だけでは停止しません。

## リソース

- Coverage設計の基本契約: `references/guidance.md`
- 技法固有のCoverage規則: `references/coverage-techniques.md`
- 既定出力形式: `assets/output-template.md`
