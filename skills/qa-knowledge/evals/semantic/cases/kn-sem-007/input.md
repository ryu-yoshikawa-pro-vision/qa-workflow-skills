# Eval Input

checkoutの`staging`向けknowledgeをlookupします。同じrootに、別scope `project:billing`のentryで依存configの現在revisionを取得できないものがあります。また別のentryは、`identity.scope_refs`が`project:checkout`なのに直下の`scope_refs`が`project:billing`で、`entry_ref`のhashだけは一致しています。
