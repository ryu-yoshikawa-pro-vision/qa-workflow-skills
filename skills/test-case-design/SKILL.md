---
name: test-case-design
description: テスト条件とカバレッジ項目を、第三者が迷わず実施できる詳細テストケースへ変換するSkill。前提条件、テストデータ、手順、観測可能な期待結果、現在有効な仕様根拠、独立性を明確にしたテスト項目書を作るときに使用する。
---

# 詳細テストケース設計

## 実行契約

1. 実行前に`references/guidance.md`を読み、ケース粒度、独立性、期待結果の根拠、統合 / 分離、停止条件、品質ゲートに従います。
2. 出力するすべてのケースは単体で、開始者 / 開始状態、準備対象、操作、入力 / 選択、合格条件を判断できる具体度にします。
3. 完成済みケースの期待結果は現在有効な仕様根拠へ追跡します。未承認`INFERENCE`、プロダクトリスク、実装、既存テスト、一般慣習だけで期待結果の根拠を確定しません。
4. 多段手順では、次操作の成立条件またはPASS / FAIL判定に必要な中間結果を該当手順番号と対応付けます。
5. 別ケースの独立性や再実行性へ影響する場合だけ、事後状態 / 後処理を明示します。
6. 必要なユーザー・データ・状態・環境は原則準備可能として設計しますが、既知の準備不能条件はケース化しません。
7. 既定出力形式が必要な場合は`assets/output-template.md`を使用します。
8. 他Skillを参照するときは正規Skill名を使用します。
9. 最終出力前に、実際に利用した入力が本Skillの入力契約を満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成した成果物へ本Skill自身の出力契約・品質ゲートを適用して自己検証します。明白かつ局所的で新しい領域固有の判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。不足仕様や不明な期待結果の根拠、未解決の仕様根拠を自己検証の名目で創作・補完せず、詳細テストケース完了基準を含む既存契約を正本として扱います。仕様根拠不足、上流判断不足、他Skillの領域固有ロジックが必要な問題は既存の停止条件・ブロック中・ルーティングに従います。最終確認後も本Skill自身の契約違反が残り、既存の停止条件・ブロック中・ルーティングに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。自己検証の経緯や修正回数は出力しません。
10. currentなテスト対象資料があれば、UI名称・到達方法・具体手順・観測可能性の補助情報として任意に使えます。currentnessは`test-target-inspection`が生きた実対象で確認し、資料上の観測挙動を期待結果の仕様根拠にしません。

## 決定論的runtime dispatch

`case_structure`は、currentなTCN / CIと現在有効な仕様根拠から、独立して実施できるテストケース構造を生成します。ケースID、coverage item、test data requirement、前提・手順・観測・期待結果・根拠をstable IDで追跡し、秘密値を出力へ複製しません。semantic itemが不足するケースは実行可能ケースとしてcompleteにせず、未解決・ブロック中・対象外の扱いを保持します。

Machine Runtime Input / Resultは入力・model・generation・implementation fingerprintとupstream Entity fingerprintを持ち、`runtime_status=ok`かつ`result_status=ready`、`freshness_status=current`、`deterministic_generated=true`の結果だけを通常のケース生成へ使います。実行時のPASS / FAILはケース設計の期待結果を置き換えません。

### 最終runtime evidence gate

最終成果物の直前にSkill-local `scripts/runtime_contract.py`の`operation=verify_runtime_evidence`へ、実際に使用したcanonical normalized inputとcandidate成果物全文、固定booleanの`partial_rerun`を渡します。full buildでは`partial_rerun=false`かつ`previous_artifact_markdown=null`、partial rerunではscope外primary Entityの有無にかかわらず`partial_rerun=true`と同一成果物系列の直前artifact全文を渡します。Disposition-onlyのscope外Entityもpreviousから検証するためです。判定やprevious Entity配列を手組みしません。返却`valid=true`の場合だけ完成として返し、`valid=false`は既存の最大1回の局所修正・最終確認契約へ統合し、未解決なら完成扱いしません。

## インターフェース

- **入力**: 対象テスト条件、必要なカバレッジ項目またはカバレッジ項目内包済みの具体テスト条件、期待挙動を判断できる現在有効な仕様根拠。
- **処理**: テスト条件 / カバレッジ項目を、第三者が単独実施してPASS / FAILを判断できる詳細テストケースへ変換し、ケース化しない項目は明示した扱いへ閉じます。
- **出力**: 安定ID、目的、関連テスト条件 / カバレッジ項目 / テスト要求、前提条件、テストデータ、実施手順、具体的期待結果、現在有効な仕様根拠、必要時の事後状態を持つ詳細テストケースを作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
