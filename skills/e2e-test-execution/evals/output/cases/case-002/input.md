# E2Eテスト実行 deterministic case 002

`assets/output-template.md`を使い、TCなしの既存注文履歴E2Eを実行する。logical primaryがresolved 0件となる場合は未実行理由を残し、cleanup未確認を成功扱いにしない。

このcaseの実行領域には対象repository、Playwright設定・spec、対象URL、テストデータがありません。「既存注文履歴E2E」という説明だけから実行対象を解決しないでください。logical primaryの依頼を保持し、実行前preflightでresolved 0件・ブロック中とし、Playwrightを起動せず、run由来artifactやcleanup成功を作らないでください。
