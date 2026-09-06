---
name: test-requirement-design
description: Current Effective Authorityとテスト分析から、何を検証・保証すべきかというTest Requirementを定義するSkill。上流Authority・Product Riskへの追跡性を保ち、テスト観点や実行手順へ先回りせず検証責務を整理するときに使用する。
---

# テスト要求設計

## 実行契約

1. 実行前に `references/guidance.md` を読み、要求の抽象度、上流項目の閉鎖、分割・統合、追跡性、Current Effective Authority、停止条件、品質ゲートに従います。
2. Test Requirementは「何を検証するか」に留め、具体条件、組合せ、実行手順を書きません。
3. 期待挙動はCurrent Effective Authorityへ追跡し、Product Risk、実装、既存テスト、未承認INFERENCEだけで製品挙動を確定しません。
4. 対象範囲内のCurrent Effective Authority / Product Riskを、Test Requirementまたは明示Dispositionへ閉じます。
5. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
6. 他Skillを参照するときはCanonical Skill名を使用します。
7. 最終出力前に、実際に利用した入力が本SkillのInput Contractを満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成した成果物へ本Skill自身のOutput Contract・品質ゲートを適用して自己検証します。明白かつ局所的で新しいDomain判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。未解決AuthorityやProduct RiskをSelf-Validationの名目で再解釈せず、Test Condition設計へ越境しません。Authority不足、上流判断不足、他SkillのDomain Logicが必要な問題は推測補完せず既存の停止条件・Blocked・routingに従います。最終確認後も本Skill自身の契約違反が残り、既存の停止条件・Blocked・routingに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。Self-Validationの経緯や修正回数は出力しません。

## インターフェース

- **Input**: 対象範囲のCurrent Effective Authorityとテスト対象範囲。Product Risk / テスト重点、案件コンテキスト、テストレベル / 観測方法は利用可能な場合に補助入力とします。
- **Function**: 上流AuthorityとProduct Riskを、「何を検証・保証すべきか」という検証責務へ変換し、Test Requirementまたは明示Dispositionへ閉じます。
- **Output**: 安定したID、検証責務、Current Effective Authority、関連Product Risk、優先度、テストレベル / 観測方法を持つTest Requirementと、Test Requirementを作らない上流項目のDispositionを作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
