# Reference

結果不明のattemptはside-effect上限を消費した扱いです。session stateを確認せず再操作しません。必須cleanup未確認なので影響scopeをblocked / incompleteに保ち、安全完了と報告しません。
