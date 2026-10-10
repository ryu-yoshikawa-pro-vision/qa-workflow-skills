# Judge評価・改善Plan

[親Plan](./2026-10-03_132700_agent-eval-runner.md)のJudge独立評価・改善を定義する。[Skill改善Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)と[固定対象評価Plan](./2026-10-03_132700_agent-eval-runner_02_qa-training-store-integration-eval.md)を補完する。既存の`semantic/prompt_builder.py`、`result.py`、`rubric.json`、`reference.md`とEvaluator-only fixtureを再利用する。新しいJudge採点方式・Agent runtime・DBは作らない。

## 目的と責務

SkillとJudgeをそれぞれ独立に検証・改善する。**Judge自身の判定だけを正解として、そのJudgeを検証したりSkillを自動修正したりしない。**

- 規範仕様（Authority）、既存Skill契約：正しさの一次根拠。Agentが勝手に変更しない。根拠が不明・矛盾ならレビュー待ち。
- `rubric.json`、`reference.md`、Judge prompt：Agentが初期案・改善案を作ってよい**変更可能な評価基準**。人間による重要部分の確認と独立検証を経て新Evaluator revisionとして採用する。
- Judge用正解データ：対象成果物、criterion ID、期待rating（単一値または許容範囲）、`evaluable`、根拠となる仕様箇所・fingerprint、確認者または決定論的な確認方法を持つ評価事例。Judgeと同一のLLMの自己申告だけで正解を確定しない。
- Skill改善Agent：検証済みJudgeの該当criterionに限り自動修正の判断材料として使う。未検証の判定は記録しても自動修正には使わない。

## 初期作成と正解データの管理

1. 対象Skill、既存`rubric.json`・`reference.md`・`evals.json`・target仕様・criterion IDとcritical指定を列挙する。既存基準を無条件に生成し直さない。
2. Agentが規範仕様の該当箇所を引用して、評価基準の不足・曖昧さ、正常例・重大違反例・軽微な不備・判断不能例、期待評価と修正案を提案する。根拠が存在しない期待動作は追加しない。
3. 提案した評価事例を`proposed`、仕様矛盾等で判断できないものを`review_pending`、独立した確認済みのものを`approved`として管理する。各事例には安定したcase ID・criterion・期待rating範囲・根拠path/hash・確認履歴を保存する。`approved`への変更には人間による判定と根拠の確認、または対象事実を直接検証できる既存の決定論的検査の証拠を必要とする。AIの提案・同意だけでは承認しない。
4. 人間による確認は重大・新規・判断が割れる事例を優先する。残りはAIによる候補生成、機械検証、抽出レビューを許すが、未確認例は合否判定の正解データに算入しない。
5. Judge改善に使用する確認済み事例と、改善Agentから期待判定・根拠を隠す**独立検証用事例**を分ける。評価対象Skillの実行環境にも両方の正解データを公開しない。既存fixtureを再利用し、不要な重複を増やさない。

`reference.md`はGolden Outputではなく、仕様に基づく判定根拠である。正解データも全文一致を要求しない。criterionの意味に応じて期待ratingの許容範囲を使う。仕様revision変更で根拠が失効した場合は、該当事例を自動的に`approved`として流用せず、再確認待ちにする。

## Judgeの独立評価

- 固定Evaluator revision（prompt・rubric・Reference・runtime）、実効Judge model/profile、確認済み正解データのrevision / fingerprintを記録する。既存semantic runtimeを使い、Judge応答JSONと`normalize_judge_response()`の結果を保存する。
- `approved`事例に対する重要欠陥の**見逃し**、正常例の**誤検出**、`evaluable=false`による判定回避、根拠不一致、独立反復時の重大な判定揺れをcriterion別に検証する。既存の`pass / needs_review / fail`の意味や算出式は変更しない。
- 人間確認済み正解と重要な食い違いがあれば当該criterionのJudgeはSkill自動修正に利用不可とする。正常例・違反例など必要な正解データ不足、反復時の矛盾、profile未検証、実行エラーでも同様。判断できる別criterionまで一律無効にしない。
- 判定不能は`judge_unverified`とし、**既存graderの`attempt_status`とは別の改善許可状態**に記録する。評価結果の保存は続行するが、該当criterionを根拠にSkill自動修正しない。
- 検証時の仕様・入力・正解データの問題と、Judge prompt / rubricの問題を区別する。期待判定が誤っていた可能性は人間へ回し、Judgeに合わせて無断で正解データを変更しない。

## Judgeの改善

1. Judgeと確認済み事例の不一致、または実評価結果の独立した規範根拠との矛盾を収集する。Agentが問題の原因仮説・根拠・影響criterion・変更候補を分析する。
2. Agentが`rubric.json`・`reference.md`・Judge promptの**候補差分**を隔離領域で作る。規範仕様・確定済み期待判定・固定Evaluator原本・Skillを変更しない。
3. 現行Judgeと候補Judgeを、同じ承認済み評価事例で独立検証する。調整に使用した事例だけでなく、改善Agentに未公開の独立検証用事例でも比較する。重大な見逃し・誤検出・判定揺れ・他criterionの回帰を確認する。
4. 誤判定の原因が不明、独立検証用の事例が不足、改善が不成立、規範仕様や期待判定の変更が必要な案件は`review_pending`へ保存する。改善が確認された候補も自動採用しない。正式な採用は人間が判断する。
5. 採用したJudge変更は新しいEvaluator revisionとして固定する。Skill修正前後を比較する場合は**旧Skillと新Skillを同じ新Evaluatorで両方再実行・再採点**し、異なるJudge revisionで得た過去の合否を直接比較しない。

**SkillとJudgeを同時に変更して改善効果を結論付けない。** Judgeが未検証のcriterionに依存するSkill修正は停止してレビュー待ちにする。一方、Judge検証が成立した別criterionに依存する独立案件は処理を継続する。残りがすべて未検証Judgeに依存するときは全体を停止する。依存・停止・再開の条件は[Skill改善Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)に従う。人間が正式承認した基準を新しい評価に使うことと、実行中の評価基準をAIに書き換えさせることは別である。

## 保存・実装境界

- 確認済み正解データの正本はEvaluator-onlyのGit管理fixture / manifestでrevision固定する。候補は原本と分離する。データの承認・失効・更新理由を記録する。
- 出力rootの`judge-validation/result.json`へEvaluator / Judge / 正解データのfingerprint、criterion別の検証可否、不一致根拠を保存する。`judge-validation/proposals/`へ変更候補、`judge-validation/review-pending/`へ不明点・要確認・判断理由を保存する。秘密や安全化できない生ログを保存しない。
- 新規の最小入口`scripts/skills/evals/agent/judge_validation.py`を置く。既存Judge subprocess・executorとsemantic normalizerを再利用して検証と候補作成を行い、`improve.py`が検証済み結果を参照する。改善Agentへの入力は調整用事例と安全化された判定根拠に限定し、独立検証用の期待判定・根拠を渡さない。
- 正解データを変更する権限とJudge改善案を作る権限は分離する。Judge候補の自動push、PR作成、merge、自動採用、自動学習はしない。通常CIはfake Judgeによる配線・拒否契約だけ検証し、外部LLMは呼ばない。

## テストと完了条件

- AI生成の未確認候補を正解として使用できず、承認・根拠・revisionが不整合なら検証済みとしない
- 正常例の誤検出・重大欠陥の見逃し・Judgeの判定揺れ・`not_evaluable`への逃避を判別できる
- 正解データがない、失効した、profile変更や判定不一致があるcriterionでは依存するSkill自動修正だけが待機し、独立案件を継続できる。残案件すべてが待機なら全体停止し、レビュー待ち理由と依存関係が保存される
- Judge改善用事例と独立検証用事例の隔離をテストし、独立検証用の根拠がAgentに漏れない
- Judgeの候補変更を同じ確認済み事例で評価し、比較結果を保存し、採用前に固定Evaluator / Skill / 正解データを変更しない
- Judgeを改訂したら旧Skillと新Skillの両方を同じEvaluator revisionで採点し、以前の結果を改善の証拠として混ぜない
- 実Codex smokeで確認済みfixtureを使ったJudge検証、Agentによる改善案の作成・独立検証・レビュー待ちへの振分けまで確認する。十分な実事例がなく改善を実証できなければ、その未達を別途報告する

対象は明示的なSkill利用による出力品質と固定workflow。native Skill trigger精度、全Skillへの正解データ充足保証、Judge自動採用、汎用Judge学習基盤は対象外。
