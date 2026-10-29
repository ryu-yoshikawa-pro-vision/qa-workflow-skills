# E2Eテスト実行 deterministic case 001

`assets/output-template.md`を使い、既存の安全確認済みlogin E2Eを1 logical primary / 1 resolved primaryとして実行する。retry attempt、run status、artifact鮮度、cleanupを分ける。

このcaseの実行領域には対象repository、Playwright設定・spec、対象URL、認証・テストデータがありません。「既存」「安全確認済み」という依頼文だけから`webServer`、spec名、実行結果を推測しないでください。logical primaryの依頼は保持し、実行前preflightでresolved 0件・ブロック中とし、Playwrightを起動せず、run由来artifactやcleanup成功を作らないでください。
