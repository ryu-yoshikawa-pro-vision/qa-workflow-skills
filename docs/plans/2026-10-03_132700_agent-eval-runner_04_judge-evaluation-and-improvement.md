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

### 確認済み正解データの再審査

`approved`は特定revisionでの独立確認を意味し、将来も常に正しいという保証ではない。実Agent成果物が規範仕様に沿った合理的な別解なのに不合格となる、期待判定と規範が矛盾する、仕様変更で根拠が失効する、評価者の判断が合理的に割れる場合は、**正解データ自体の疑義**として扱う。

1. 分析Agentは、該当case / criterion・元の期待rating・原成果物・規範仕様pathとfingerprint・別解の根拠・承認履歴を付けて再審査候補を作成できる。ただし、Agentの異議・自己評価や単なる低ratingだけで期待判定を変更しない。
2. 独立した根拠のある疑義が認められたcase・criterionは、現行検証で`review_pending`として扱い、Judgeの検証済み根拠やSkill自動修正の許可に利用しない。元の`approved`版を上書きせず、依存しないcriterion・改善案件は継続する。
3. 人間が規範仕様・合理的な別解・期待ratingの許容範囲・`evaluable`を照合する。合理的な不一致を単一labelへ強制しない。確定できなければレビュー待ちとする。直接確認できる事実は既存の決定論的検査を利用してよい。
4. 継続利用・修正・除外の判断、確認者、根拠を承認履歴に記録する。修正するなら**新しい正解データrevision**を承認し、旧revisionは保持する。Judgeへ都合よく合わせる自動緩和はしない。関連Judgeを新revisionで独立検証し、Skillの修正前後を比較する場合は両方を**同一の新Evaluator・正解データrevisionで再実行・再採点**する。

再審査は既存`judge-validation/review-pending/`で扱う。DB・全件手動再採点は追加しない。

## Judgeの独立評価

- 固定Evaluator revision（prompt・rubric・Reference・runtime）、実効Judge model/profile、確認済み正解データのrevision / fingerprintを記録する。既存semantic runtimeを使い、Judge応答JSONと`normalize_judge_response()`の結果を保存する。
- `approved`事例に対する重要欠陥の**見逃し**、正常例の**誤検出**、`evaluable=false`による判定回避、根拠不一致、独立反復時の重大な判定揺れをcriterion別に検証する。既存の`pass / needs_review / fail`の意味や算出式は変更しない。
- 人間確認済み正解と重要な食い違いがあれば当該criterionのJudgeはSkill自動修正に利用不可とする。正常例・違反例など必要な正解データ不足、反復時の矛盾、profile未検証、実行エラーでも同様。判断できる別criterionまで一律無効にしない。
- 判定不能は`judge_unverified`とし、**既存graderの`attempt_status`とは別の改善許可状態**に記録する。評価結果の保存は続行するが、該当criterionを根拠にSkill自動修正しない。
- 検証時の仕様・入力・正解データの問題とJudge prompt / rubricの問題を区別し、期待判定自体の疑義は[再審査](#確認済み正解データの再審査)へ回す。重要判定が反復で矛盾したときは追加の成功試行や多数決で検証済みに戻さず、全試行・根拠を保存してレビュー待ちとする。追加試行は既存の実行上限内で原因調査に限定する。

## Judgeの改善

1. Judgeと確認済み事例の不一致、または実評価結果の独立した規範根拠との矛盾を収集する。Agentが問題の原因仮説・根拠・影響criterion・変更候補を分析する。
2. Agentが`rubric.json`・`reference.md`・Judge promptの**候補差分**を隔離領域で作る。規範仕様・確定済み期待判定・固定Evaluator原本・Skillを変更しない。
3. 現行Judgeと候補Judgeを同じ承認済み事例で検証する。**候補生成前**に調整用と独立検証用のcase ID・revision・fingerprintを固定する。独立検証用事例の入力・期待判定・事例別結果はJudge改善Agentへ渡さず、制御側・人間が評価する。独立検証の失敗を改善Agentへ繰り返し開示して調整させない。重大な見逃し・誤検出・判定揺れ・他criterionの回帰を検査する。隔離が破れた場合は未使用事例で再検証するかレビュー待ちにする。
4. 誤判定の原因が不明、独立検証用の事例が不足、改善が不成立、規範仕様や期待判定の変更が必要な案件は`review_pending`へ保存する。改善が確認された候補も自動採用しない。正式な採用は人間が判断する。
5. 採用したJudge変更は新しいEvaluator revisionとして固定する。Skill修正前後を比較する場合は**旧Skillと新Skillを同じ新Evaluatorで両方再実行・再採点**し、異なるJudge revisionで得た過去の合否を直接比較しない。

**SkillとJudgeを同時に変更して改善効果を結論付けない。** Judgeが未検証のcriterionに依存するSkill修正は停止してレビュー待ちにする。一方、Judge検証が成立した別criterionに依存する独立案件は処理を継続する。残りがすべて未検証Judgeに依存するときは全体を停止する。依存・停止・再開の条件は[Skill改善Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)に従う。人間が正式承認した基準を新しい評価に使うことと、実行中の評価基準をAIに書き換えさせることは別である。

## 保存・実装境界

- 確認済み正解データの正本はEvaluator-onlyのGit管理fixture / manifestでrevision固定する。候補は原本と分離する。データの承認・失効・更新理由を記録する。
- 出力rootの`judge-validation/result.json`へEvaluator / Judge / 正解データのfingerprint、criterion別の検証可否、不一致根拠を保存する。`judge-validation/proposals/`へ変更候補、`judge-validation/review-pending/`へ不明点・要確認・判断理由を保存する。秘密や安全化できない生ログを保存しない。
- 新規の最小入口`scripts/skills/evals/agent/judge_validation.py`を置く。既存Judge subprocess・executorとsemantic normalizerを再利用して検証と候補作成を行い、`improve.py`が検証済み結果を参照する。改善Agentへの入力は調整用事例と安全化された判定根拠に限定し、独立検証用の期待判定・根拠を渡さない。
- 正解データの変更権限とJudge改善案の作成権限を分離する。独立検証用の入力・期待判定・事例別結果を改善Agentのworkspace・prompt・診断に渡さず、Evaluator-only領域の読取拒否をnegative testで確認する。公開資料のモデル事前学習への混入まで防げたと主張しない。Judge候補の自動push、PR作成、merge、自動採用、自動学習はしない。通常CIで外部LLMを呼ばない。

## テストと完了条件

- AI生成の未確認候補を正解として使用できず、承認・根拠・revisionが不整合なら検証済みとしない
- 正常例の誤検出・重大欠陥の見逃し・Judgeの判定揺れ・`not_evaluable`への逃避を判別でき、重要判定の矛盾を多数決で検証済みに戻さない
- 正しい別解の不当な不合格・期待判定と規範の矛盾・合理的な評価相違を再審査へ回し、影響範囲のみ待機させて承認済み新revisionで再検証できる
- 正解データがない、失効した、profile変更や判定不一致があるcriterionでは依存するSkill自動修正だけが待機し、独立案件を継続できる。残案件すべてが待機なら全体停止し、レビュー待ち理由と依存関係が保存される
- 調整用と独立検証用事例の事前固定・隔離をテストし、入力・期待判定・事例別結果がAgentに漏れない。漏えい時は独立検証済みとしない
- Judgeの候補変更を同じ確認済み事例で評価し、比較結果を保存し、採用前に固定Evaluator / Skill / 正解データを変更しない
- Judgeを改訂したら旧Skillと新Skillの両方を同じEvaluator revisionで採点し、以前の結果を改善の証拠として混ぜない
- 実Codex smokeで確認済みfixtureを使ったJudge検証、Agentによる改善案の作成・独立検証・レビュー待ちへの振分けまで確認する。十分な実事例がなく改善を実証できなければ、その未達を別途報告する

対象は明示的なSkill利用による出力品質と固定workflow。native Skill trigger精度、全Skillへの正解データ充足保証、Judge自動採用、汎用Judge学習基盤は対象外。

## 研究根拠と採用判断

- [EvalGen (2024)](https://arxiv.org/abs/2404.12272)：人間の判定とAI生成評価基準の照合、criteria drift → 改訂には独立確認とrevisionを必要とする。
- [Validating LLM-as-a-Judge Systems in the Absence of Gold Labels (2025)](https://arxiv.org/abs/2503.05965)：合理的な判定不一致 → 単一labelの強制を避ける。
- [RubricBench (2026)](https://arxiv.org/abs/2603.01562)：専門家基準とモデル生成rubricの差 → AI生成案を独立検証する。
- [VeriFine (2026)](https://arxiv.org/abs/2610.08761)：Judgeと改善対象の別ループ → SkillとJudgeの改訂・比較を分離する。原研究はロボット等でありAgent Skillsへの効果を直接実証しない。
- [OpenAIのSWE-bench Verifiedに関する調査 (2026)](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)：人間が確認した評価にも正しい解を拒否するテストやデータ汚染がある → `approved`でも根拠のある疑義は再審査する。

研究は設計判断の根拠であり、本リポジトリの改善効果や特定の正答率を保証しない。
