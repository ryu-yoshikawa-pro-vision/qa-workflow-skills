---
name: test-target-inspection
description: 生きたテスト対象を確認し、今回必要な範囲のUI情報・現在のふるまい・確認条件をテスト対象資料として収集または更新する。資料の鮮度確認、画面・状態・操作反応の記録、必要な視覚観測が必要なときに使用する。
---

# テスト対象資料の確認・管理

## 実行契約

1. 詳細な確認手順が必要な場合は `references/guidance.md` を読み、currentness、安全、保存、証跡、副作用の契約に従います。
2. 今回確認する範囲、実対象への入口または同等の識別情報、既存資料・保存先（ある場合）を受け取ります。
3. 今回利用・更新する範囲は、生きた実対象へ到達して確認します。repository、仕様、Page Object等の情報だけでcurrentとしません。
4. 実対象で観測した挙動は観測事実として記録し、仕様Authorityやテストの期待結果へ昇格しません。
5. 表示条件が比較可能な場合だけ既存資料の「変更なし」「削除確認」を判断します。version / buildの変更だけで比較不能にせず、取得不能だけで一律「確認不能」にしません。
6. DOM / accessibility tree等で判断できない視覚状態は、現在利用中のbrowserから取得した画像で確認します。画像からrole、accessible name、DOM状態、仕様を推測しません。
7. ARIA snapshotは後続比較に価値があり、安全かつ現在の手段で安定して取得・保存できる必要範囲だけ任意保存します。snapshot差分だけで下流成果物を更新しません。
8. POM / Page Object / fixture / helperは対象repoで確認でき、後続に有用な場合の任意参照です。作成・変更しません。
9. 永続保存はユーザーまたは案件が指定した保存先だけで行い、条件付き更新がない共有保存先を自動上書きしません。案件固有資料やsnapshotを本repoへcommitしません。
10. 状態を変える操作やcleanupを要する観測は、許可された副作用scope、1回の定義、最大回数、cleanup条件に従います。
11. 必要な実対象確認ができない範囲は「未確認」または「確認不能」とし、要求範囲が満たせない場合はブロック中と再開条件を示します。

## 主な成果物

`assets/output-template.md`を正規形として、対象範囲、確認条件、画面・UI要素・状態・操作反応、視覚情報、任意の構造証跡、鮮度、未確認範囲、副作用、更新区分、保存結果を記録します。今回観測したふるまいと仕様上の期待結果を分離します。

## 責務境界

- 詳細テストケースの設計: `test-case-design`
- AIによるTCの実操作・合否判定・報告: `test-execution`
- 仕様Authorityの解決: `spec-analysis`
- Playwright E2E固有の実装前inspection: `e2e-test-inspection`
- Page Object / fixture / helper / 永続E2E実装: `e2e-test-implementation`
- workflow routing、再開、変更伝播: `qa-workflow`

テスト対象資料は後続設計の補助情報です。仕様の根拠にはしません。
