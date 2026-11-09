# Reference

適用範囲が確実に異なるbilling entryの依存取得不能だけではcheckoutの有効entryの利用を止めません（診断情報のみ）。`identity`と直下の`scope_refs` / `kind`が一致しないentryは`entry_ref`が正しくても受理せず、自動修正・再採番・別scopeへの流用をせず、適用範囲を判断できないため検索を`incomplete`にして正本ownerへ戻します。別sessionへは`read_entry`で得たentry revisionをentry本体と別に引き継ぎ、本体へ書き込みません。
