`ryu-yoshikawa-pro-vision/qa-training-store` の固定revision `84ce165493649550832731a60cf436f8ae29c56b` を対象に、Web版 Checkout / Payment の分析・設計workflowを実行してください。

現在有効な仕様根拠を確認し、必要なQA工程を `qa-workflow` で判断して、テスト分析からテスト設計、カバレッジ確認、反証レビューまで行ってください。`question-analysis` は実際に確認すべき不明点・矛盾がある場合だけ使います。E2E実装や実ブラウザ実行は今回の要求に含めません。

Product Code、既存Product Test、規範仕様、Skill、評価用設定を変更しないでください。現在のrepoと規範仕様から導出できない期待動作を追加しないでください。仕様の優先順位は `docs/spec/README.md` に従います。

正規QA成果物は `.qa-eval-output/` に個別Markdown fileとして保存してください。各成果物を `.qa-eval-output/artifact-index.json` の `artifacts[]` に登録し、各workflow工程の実行・再利用・省略・blocked・未完了判断を `routing[]` に登録してください。登録内容は自己申告なので、存在しない成果物を完了扱いしないでください。

`artifact-index.json` は `schema_version: 1`、`artifacts`、`routing` の3キーを持つJSON objectです。artifact行は `skill`、`kind`、`scope`、一意なASCII `artifact_id`、`.qa-eval-output/` 基準の相対 `path` を持ちます。routing行は `skill`、`scope`、`status`、理由、`artifact_ids` を持ち、statusは `executed`、`reused`、`skipped`、`blocked`、`incomplete` のいずれかです。

評価出力root以外には書き込まないでください。commit、push、PR作成、外部検索や追加MCP/toolの利用はしないでください。Evaluator側のReference、expected、rubric、graderを探索しないでください。

最終回答には実行した工程、成果物path、未完了・blocked事項を記載してください。最終回答はworkflow判断の証拠であり、正規QA成果物の代替ではありません。
