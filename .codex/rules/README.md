# Execpolicy rules

このディレクトリの `.rules` が、現在有効なCodex CLI execpolicyの正本です。[2026-10-03の導入Plan](../../docs/plans/2026-10-03_173600_formatter-lint_execpolicy-rules.md)は当時の記録であり、現在のrulesとの全文一致は要求しません。

`.codex/rules/20-risky-prompt.rules`は、通常の`git commit`、`git pull`、`git fetch`、`git push`を`prompt`対象から除外し、それ以外の既存高影響Git / GitHub CLI操作は従来どおり`prompt`に分類します。`git commit --amend`の標準形式は`.codex/rules/30-destructive-forbidden.rules`で`forbidden`にし、引数順序を含む最終判定はHookが行います。通常commit・pull・fetch・pushの`no_match`だけでは安全性を保証しません。

Hookは通常commitを、作業branch上の明示メッセージ付き対応形式に限って許可します。fetchは構成済み名前付きremoteのremote-tracking ref更新に限り、protected local refへの直接更新、force/refmap/stdin形式、判定不能なrefspec、削除先をremote-tracking namespaceに限定できないprune設定、無効化されていないsubmodule再帰を拒否します。pullは保護branch上では拒否し、`--ff-only`、実効`pull.ff=only`、または`pull.ff`未設定時の実効`merge.ff=only`が明示されている場合だけ許可します。未設定時のGit既定動作には依存せず、fast-forward-onlyを保証できないrebase・no-ff・squash等の引数や実効設定を拒否します。通常pushの可否は既存のremote、refspec、protected branch、実効Git設定の検査で決めます。

静的に判別できる危険なpushはexecpolicyで`forbidden`とし、引数配置など実行時の条件はHookが拒否します。通常command用の`allow` ruleはありません。

実Codexランタイム受入では、fresh sessionの`/hooks`でHookの登録・信頼・有効状態を確認し、実際のcommand経路でHook配送を確かめます。契約テストだけでは受入を完了できません。詳細は[通常push許可Plan](../../docs/plans/2026-10-21_001018_codex-normal-push-policy.md)と[安全境界の説明](../../docs/reference/codex-safety-harness.md)を参照してください。
