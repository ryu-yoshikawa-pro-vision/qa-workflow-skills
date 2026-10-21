# Execpolicy rules

このディレクトリの `.rules` が、現在有効なCodex CLI execpolicyの正本です。[2026-10-03の導入Plan](../../docs/plans/2026-10-03_173600_formatter-lint_execpolicy-rules.md)は当時の記録であり、現在のrulesとの全文一致は要求しません。

`.codex/rules/20-risky-prompt.rules`は、`git push`を除く既存の高影響Git / GitHub CLI操作を引き続き`prompt`に分類します。安全な通常pushはexecpolicyで`no_match`になりますが、それだけでは安全性を保証しません。通常pushの可否は`PreToolUse` Hookがrepository、現在のbranch、remote、refspec、実効Git設定を確認して決めます。

静的に判別できる危険なpushはexecpolicyで`forbidden`とし、引数配置など実行時の条件はHookが拒否します。通常command用の`allow` ruleはありません。

実Codexランタイム受入では、fresh sessionの`/hooks`でHookの登録・信頼・有効状態を確認し、実際のcommand経路でHook配送を確かめます。契約テストだけでは受入を完了できません。詳細は[通常push許可Plan](../../docs/plans/2026-10-21_001018_codex-normal-push-policy.md)と[安全境界の説明](../../docs/reference/codex-safety-harness.md)を参照してください。
