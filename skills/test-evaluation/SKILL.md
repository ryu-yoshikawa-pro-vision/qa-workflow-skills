---
name: test-evaluation
description: 案件のQA活動を追跡性・品質・効率・プロセス・再利用性の5軸で評価し、改善案の採用・正本改版・実施・次回の効果測定と引継ぎ状況を追跡する。「QA活動の評価・改善の効果判定・改善案の引継ぎ・測定不能指標の整理」を求められたら、自分で答える前に必ずこのSkillを読み込む。Skill自体の評価、リリース承認、計画や設計の直接改版には使用しない。
---

# Test Evaluation

統合報告・計画と実績・欠陥・coverage・工数・前回改善から、案件のQA活動の有効性、効率、再現性、改善効果を評価します。元実績・正式テスト結果・承認のraw情報は書き換えません。Agent Skill自体の品質評価は`EVALS.md`、継続QA知識は`qa-knowledge`、Skill構成の効率比較は`EVALS.md`の効率比較契約です。

## 実行契約

1. 先に`references/guidance.md`を読み、5軸、測定条件、改善lifecycle、引継ぎの契約に従います。
2. 入力はsource ref・revision・content hashで固定し、`scripts/evaluation_runtime.py`で再取得時の改変・旧版を検出します。取得できない入力は未測定です。
3. すべての指標に測定元・分母・計算条件を付け、測定不能は理由付きの`unmeasured`にします。測定不能・比較条件不一致・悪化・改善なし・未実施を成果へ算入しません。複数指標を根拠のない総合点にしません。
4. 作業時間などの効率指標だけが改善しても、品質・追跡性の改善を主張しません。指標単位の改善と軸全体の判定を区別し、軸全体の「改善」はその軸のすべての指標が比較可能で、悪化・比較不能・未測定・無効がない場合だけです。一部だけの改善（`partially_improved`）や混在（`mixed`）として示します。
5. 改善案は`proposed`→`adopted`→`handed_off`→`implemented`→効果測定の順に進めます。採用は信頼できる承認サービスで認証された、対象改善・revisionに一致する承認だけです。正本の改版は`test-management`（計画・予算・資源・順序）、`test-architecture-design`（方式・環境・品質特性）または元の設計ownerが行い、本Skillは直接改版しません。
6. 実施済みは、ownerが当該採用に紐づく新revisionを記録した場合だけです。効果測定は新revisionを適用した後の同条件の次回QA活動から取得します。
7. `qa-knowledge`への登録は候補の引渡しであり、採用・計画改版・実施・効果測定の代用ではありません。
8. 完了・保管・引継ぎは各項目の受領者の認証済み確認がある場合だけ閉じます。リリース承認・プロジェクト終了決定は代行しません。

## 正規対象

- `evaluation`：5軸の評価・主張の検証
- `improvement`：改善lifecycleの進行と集計
- `handoff`：保管・引継ぎ状況

## リソース

- 手順・責務境界・停止条件: `references/guidance.md`
- 入出力とstateのdata contract: `references/data-contract.md`
- 正規出力形: `assets/output-template.md`
- production helper: `scripts/evaluation_runtime.py`（標準ライブラリのみ。他Skillのscriptに依存しない）
- deterministic validator: `evals/deterministic/validator.py`
