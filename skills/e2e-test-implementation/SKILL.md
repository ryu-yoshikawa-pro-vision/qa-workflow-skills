---
name: e2e-test-implementation
description: inspectionで確認済みのE2E対象と事実を既存repo構造に沿ったPlaywright E2Eへ実装・更新し、静的・軽量検証とE2E実装参照を残すSkill。inspection相当情報があり、コード変更を要求されたときに使用する。
---

# E2Eテスト実装

## 実行契約

1. 詳細判断が必要な場合は最初に`references/guidance.md`を読み、既存構造の再利用・軽量検証・TCなし契約に従います。
2. 有効な`e2e-test-inspection`成果物または同等の確認済み情報と、詳細TC、明示E2E対象、既存E2E実装参照のいずれかを入力にします。
3. TCあり経路では元TCの期待結果を実装都合で変更しません。TCなし経路では明示対象・確認済み期待挙動・仕様根拠を使い、TC / TC IDを創作しません。
4. コード変更前にbranch、HEAD、working tree、変更予定ファイルとの競合、inspectionからのrepo構造差分を確認します。競合しない既存変更を一律に停止理由にしません。
5. 既存spec、fixture、helper、Page Object、config、locator方針を優先し、存在しない抽象化やURL・fixture・locatorを推測しません。
6. secret / 認証情報をコードへ埋め込まず、inspectionで確認したorigin・副作用・データ・cleanup制約を超えません。
7. 実装後は対象repoの既存verify / test validation / lint / typecheck / test discovery等から、実対象E2E、外部I/O、状態変更を含まない検証だけを実施します。安全性を確認できない検証や本実行はここで行わず、未実施理由を残します。
8. 実装対象とE2E実装参照はそれぞれ最低1件記録します。E2E実装参照は、既存識別子またはrepo-relative test path + Playwright title pathで保持します。project、repeat、retryは実行単位情報として分離します。
9. 静的検証失敗を成功扱いにせず、inspection差分・ブロック・`要再検証`を明示します。

## 実装しないこと

独自runner、reporter、retry framework、汎用Page Object / fixture framework、別test framework adapter、対象プロダクトCI基盤は追加しません。implementationは指定環境への本E2E実行を担当しません。

## 出力

`assets/output-template.md`を基本形として、1件以上の実装対象、TCまたは明示対象、変更 / 再利用ファイル、1件以上のE2E実装参照、branch / HEAD / working tree、静的・軽量検証結果、inspection差分、ブロック / `要再検証`を記録します。

## 次の担当

- E2E実装レビュー → `adversarial-review`（対象: `E2E実装`）
- TC → E2E実装追跡 → `coverage-analysis`（対象: `TC → E2E実装`）
- 指定環境での実行 → `e2e-test-execution`
- inspection事実不足 → `e2e-test-inspection`
