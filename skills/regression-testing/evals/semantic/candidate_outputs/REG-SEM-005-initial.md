# 回帰対応ルート

- TC-401はcurrentで有効なため、そのまま再利用します。FAILと観測証拠は実行元の値を保ち、回帰側で原因を再判定しません。
- 原因調査は`question-analysis`へ回し、期待結果の仕様authorityを確認します。TC-401の改修が必要かどうかは、その確認後に判断します。
- 修正後の確認は`qa-workflow`経由で既存の`test-execution`を使い、TC-401を再実行します。開始前にrequired routeを確定し、PR #12の契約で実際の開始を確認します。専用のfix-confirmation状態やartifactは作りません。
- Regression Activityには、元のFAILと証拠を実行元の参照情報付きで保持し、修正後の実行結果も別Activityとして記録します。

実行artifactやsource参照、修正結果が提示されていないため、Activityの更新と修正後の確認は未実施です。
