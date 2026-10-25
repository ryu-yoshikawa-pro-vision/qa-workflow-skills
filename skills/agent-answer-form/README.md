# HTML回答フォーム生成Skill

エージェントから利用者へ渡す複数の質問をJSONで定義し、回答をMarkdownで回収できる単一HTMLを生成します。Python 3.9以上、外部ライブラリ不要です。

- SKILL.md: 作業手順とQA Skillとの責務境界
- assets/questionnaire_template.json: **ダミー質問**。実務の質問内容として使わない
- assets/form_template.html、assets/form.js: 変更不要な共通UI
- scripts/build_form.py: JSONの検証・HTML生成
- references/json-format.md: JSON仕様
- tests/: 回帰テスト
- evals/trigger/: リポジトリのSkill発火評価

作業ディレクトリへ質問JSONを作り、Skillを変更せず次で検証・生成します。

```bash
python "<Skillの配置先>/scripts/build_form.py" --input "./questions.json" --validate-only
python "<Skillの配置先>/scripts/build_form.py" --input "./questions.json" --output "./answer-form.html"
```

完成したHTMLでは、回答状況の自動表示、保留チェック、単一・複数選択、自由記述、検索、記入済みまたは全問のMarkdown直接コピー・保存ができます。コピー失敗時だけ確認画面から手動コピーします。ブラウザの保存機能は環境依存です。保存時は質問定義を質問単位で照合し、意味が変更された質問の回答だけを復元しません。旧形式の回答は自動復元せず、旧版HTMLと保存領域を保持します。

QAの場合、question-analysis が質問を判断し Q-xxx を割り当てます。本Skillは表示・回収だけを担当します。返却された回答は question-analysis の契約に従って処理してください。
