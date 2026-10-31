# Eval Input

今後のテスト設計のためにUI仕様理解packageからartifact modeで要求を作成する。文中に`AC-001`、`AC-002`、`SPEC-001`のIDと要約は示されますが、current Machine Entityのpayload、content fingerprint、Authority / Scope dependencyは入力されていません。これらの要約をcurrent entityとして扱わず、artifact modeの参照条件を満たすと確認できるまで要求生成をblockしてください。

## Current Acceptance Criteria

- AC-001: ログイン成功時にダッシュボードへ遷移する。
- AC-002: メールアドレス未登録時のエラー文言は仕様で確定していない。

## Current Effective Authority

- SPEC-001: 利用者はメールアドレスとパスワードでログインできる。

## Project Risk

- RISK-001: 認証失敗時に不適切な画面状態となるリスク（中）。

## 要求化方針

- AC-001の成功後遷移と入力受理責務は、意味上異なる場合に分割する。
- AC-002の期待文言は未確定のため、推測で要求化しない。
- ACの接続だけでAuthorityのclosure済みと判断しない。

# Output format

Use the Skill's `assets/output-template.md` as the required output format.
