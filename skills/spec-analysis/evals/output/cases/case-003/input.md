# Eval Input

今後のテスト設計で継続利用するUI仕様理解packageを作成してください。`ui-target-v1` の標準fileとstable IDを使い、仕様理解のみで終了します。test-analysisは開始しません。

## 情報源 SRC-001: 認証仕様

- 利用者はログイン画面でメールアドレスとパスワードを入力し、ログインを実行する。
- 成功時はダッシュボードへ遷移する。
- 認証失敗時はログイン画面に留まり、エラーを表示する。
- メールアドレスが未登録の場合の具体的なエラー内容は定義されていない。

## 期待

- UI操作、画面構造、User Story、Use Case、Behavior、Acceptance Criteriaをstable IDで関連付ける。
- 未定義のエラー内容はUNKNOWNとして保持する。
- 現在有効なAuthorityと標準package fileを追跡可能にする。

# Output format

Use the Skill's `assets/output-template.md` as the required output format.
