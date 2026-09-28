# Expected semantic contract

LLMはflow全体の意味的な懸念を評価できること。一方、business rule自体の仕様上のPASS / FAILやexpected resultをusability-inspection / usability-evaluationが再定義せず、必要ならtest-execution等の既存ownerへroutingすること。Authorityがないbusiness ruleを創作しないこと。

## 8. trigger eval

positive例:

- このWeb画面を実際に触ってユーザビリティ上の問題を確認 - この機能のUI / UXを実画面で検査 - mobile Webで表示崩れと操作性を確認 - keyboard / focus / error表示を確認 - target sizeなどをWCAG基準で確認 - touch操作を確認 - mobile device profileで操作性を確認 - この操作のfeedback速度を実測 - このflowを実際に操作して使い勝手を確認

negative例:

- WCAG 2.2 AA conformance evaluationを実施 → wcag-conformance-evaluation - このDialog patternが妥当かレビュー → usability-evaluation - このscreenshotをUI pattern knowledgeで評価 → usability-evaluation - このTCを実行 → test-execution - current UI一覧を更新 → test-target-inspection - 自由に未知の不具合を探索 → exploratory-testing

## 9. repository integration

実装時の最新mainへ合わせて、

- CANONICAL_SKILLS - MULTI_USE_SKILL_TARGETS - qa-workflow routing - workflow-state-template - project-context-template - README.md - EVALS.md - ASSERTIONS等のSkill一覧 - validate-skills workflow - trigger / deterministic / semantic datasets

を更新します。

件数は最新mainから再計算します。

## 10. portable設計

- Markdown + Skill-local validatorを基本とする - runtime時の外部Webアクセスを必須にしない - browser automation frameworkを新設しない - performance measurement serviceを新設しない - RUM serviceを新設しない - vector DB / graph DBを追加しない - project固有browser stateをSkill packageへ保存しない
