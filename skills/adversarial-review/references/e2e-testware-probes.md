# E2E testwareレビュー用プローブ

対象範囲が`E2E実装`の場合だけ読みます。一般的なプロダクトコードPRレビューやPlaywright lint runnerの代替にはしません。

## 確認すること

- 詳細TCがある場合、E2E実装の操作・観測・期待結果が元TCの検証目的と期待結果を維持している
- TCがない場合、明示されたE2E対象、inspectionで確認済みの期待挙動、現在有効な仕様根拠と一致している
- E2Eコード上のassertionを仕様根拠の代替にしていない
- 存在しないlocator、fixture、helper、Page Object、URL、API、データ準備方法を推測していない
- 既存spec / fixture / helper / Page Objectを無視した重複実装がない
- 固定時間待機や脆弱なlocator、テスト間依存、共有データ依存が必要以上にない
- 開始状態、テストデータ、cleanupがinspectionの事実・許可範囲と整合する
- secret、cookie、token、認証状態、個人データをコードや通常ログへ埋め込んでいない
- 指定外origin、未許可のデータ削除、メール、決済、権限変更などの副作用を起こさない

## ルーティング

- E2Eコードやfixtureの問題 → `e2e-test-implementation`
- inspection事実の不足 → `e2e-test-inspection`
- TC / 仕様根拠 / 期待結果の問題 → その意味が変わる最も早い責任Skill
- TC → E2E実装の追跡不足 → `coverage-analysis`（対象: `TC → E2E実装`）

lint、typecheck、test discovery等の実行は`e2e-test-implementation`の結果を参照し、本Skill自身がrunnerとして再実行しません。
