---
name: agent-answer-form
description: エージェントがまとめた複数の確認事項をJSONで定義し、人間がオフラインHTMLで回答してMarkdownをコピー・保存できるフォームを生成する。人への質問票やQAの未解決質問一覧を回答フォームとして渡す依頼で使用する。
compatibility: Python 3.9以上。追加ライブラリ不要。
---

# 回答フォーム生成

確認事項をJSONで定義し、共通テンプレートから単一HTMLを生成する。質問の意味判断、質問IDの採番、回答の承認・正規化、QAワークフローの停止・再開は担当しない。

## 手順

1. 複数の質問をフォームで渡す必要がある場合だけ使用する。質問自体が未整理なら先に担当Skillで整理する。単発の簡単な質問ではフォームを必須としない。
2. assets/questionnaire_template.json の構造と references/json-format.md を参照して、Skill外の作業ディレクトリに質問JSONを作成する。同梱内容は動作確認用の**ダミー**であり、実際の質問へ流用しない。
3. question-analysis の成果物を入力するときは、既存の安定質問ID（例: Q-001）を questions[].id にそのまま入れる。回答者の判断に必要な根拠・前提・影響範囲を `context` に反映し、元の質問成果物（関連UNKNOWN、正規化先、再開先を含む）は維持する。回答文から新しい仕様根拠や承認済み仮定を生成しない。
4. 選択肢や推奨案を表示する場合は、情報源や既存の決定に基づく内容だけを使う。推奨案は自動選択せず、未回答や「保留」を承認とみなさない。秘密情報を回答フォームに含めない。
5. Skillディレクトリは読み取り専用とし、作業ディレクトリで次を実行する。<Skillの配置先> を実際のSkillパスに置き換える。

   ```bash
   python "<Skillの配置先>/scripts/build_form.py" --input "./questions.json" --validate-only
   python "<Skillの配置先>/scripts/build_form.py" --input "./questions.json" --output "./answer-form.html"
   ```

6. JSON検証とHTML生成が成功したことを確認し、可能な環境ではブラウザで回答・保留・コピー・Markdown出力も動作確認する。生成したHTMLと質問JSONを依頼者へ渡す。
7. 回答が返された場合は元の質問IDと照合し、元の担当Skillへ引き渡す。QAの回答の分類・正規化・再開先判断は question-analysis と qa-workflow の既存契約に従う。本SkillだけでQA工程を再開しない。

## 制約

- 質問の差し替えはJSONの編集と再生成で行い、HTML・JavaScript・Pythonを質問ごとに編集しない。
- 生成するHTMLは質問JSONと処理を内包し、外部通信しない。回答はブラウザ内に保存される場合があるため、機密情報を記入しない。
- 質問IDや選択肢の意味を変更したときは、保存済み回答の再利用が適切か確認する。
- 専用のサーバー、DB、外部ライブラリ、QA runtimeや成果物グラフを追加しない。

## 検証

```bash
python -m unittest discover -s "<Skillの配置先>/tests" -v
```
