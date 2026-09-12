---
name: e2e-test-inspection
description: Playwright E2Eの実装前に対象repo・workspace・既存E2E・実対象を調査し、E2E対象、実装に必要な事実、実装可否、安全条件、既存E2Eとの関係を確定するSkill。コード変更やE2E実行をせず、inspection相当情報が必要なときに使用する。
---

# E2E対象inspection

## 実行契約

1. 詳細判断が必要な場合は最初に`references/guidance.md`を読み、確認元・鮮度・安全境界・推測抑制の契約に従います。
2. 詳細テストケース、ユーザーが明示したE2E対象、更新対象の既存E2E実装参照のいずれかと対象repo / workspaceを入力にします。
3. TCあり経路ではTC IDと期待結果を保持します。TCなし経路では対象説明やrepo-relative test path + title pathで識別し、TC / TC IDを創作しません。
4. コード変更もPlaywright実行も行いません。repo構造・既存E2E・設定・実対象の事実を確認し、実装へ渡す事実と未確認範囲を分離します。
5. 実対象URLやbrowser操作能力がない場合でも、可能なrepo / workspace確認は継続し、実対象に依存する範囲だけを`未確認`または`ブロック中`にします。
6. 指定URLは主たる対象originの識別であり、別origin、削除、メール、決済、権限変更等の包括許可ではありません。必要な副作用は許可根拠と範囲を確認します。
7. Playwright設定は新規設計せず、対象testへ効くconfig / project / file / fixture / hook / setup / teardown / reporter / artifact / cleanupの実効事実を確認します。
8. branch / commit / working tree、対象URL / origin、実対象確認日時、取得できるversion / build ID、主要事実の確認元と鮮度を成果物へ残します。secret、cookie、token、storageStateの値は記録しません。
9. 最終出力前に、対象決定を最低1行、各行の識別子・決定根拠・扱いを確認します。実装・実行に影響する事実も最低1行以上で、内容・確認元・影響を空欄にしません。存在を確認できないlocator、fixture、helper、URL、API、データ準備方法を推測しません。

## 調査範囲

- Playwright導入、package manager、既存実行入口、config、project、spec、fixture、helper、Page Object、locator方針
- 認証、storageState、データ / 状態準備、runner管理setup / cleanup、run外処理、reporter、trace / screenshot / video / HTML report
- baseURL、絶対URL navigation、webServer、retries、repeatEach、workers、parallel / serial、共有アカウント / server-side data
- 必要時の実対象到達、画面・経路、実在locator、非同期状態、期待結果の観測、role、test data、version / build

## 出力

`assets/output-template.md`を基本形として、E2E対象の決定根拠、TC（存在時のみ）、実装参照、確認元・鮮度、実効設定、開始状態、準備 / cleanup、外部origin、副作用許可、証跡保護、既存E2E関係、実装可否、ブロック理由を記録します。

## 次の担当

- 実装可能な対象 → `e2e-test-implementation`
- 自動化価値そのものの再判断が必要 → `test-analysis`（対象: `E2E対象選定`）
- 仕様の期待結果が未確定 → `question-analysis`
- 実行条件・cleanup・高リスク副作用上限が未確認 → `e2e-test-execution`へ直接進めず、確認可能な範囲をブロックします。
