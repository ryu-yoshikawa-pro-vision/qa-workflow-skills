# 専門QA判断・責務適正化・実Agent評価

## 目的・対象

OPS-11・18と全OPSの受入。自律的なQA判断・必要な活動の選択・知識の再利用・欠陥予防・評価を、実際のQA作業で改善する。共通原則に従い、専門外管理処理と重複を削減し、必要な意味判断・決定論的処理・実証拠を残す。01〜04の変更を評価する。評価のための新しい汎用基盤を作らない。

## 現状と維持する契約

- `EVALS.md` の仕様適合、trigger、決定論的出力、意味評価、workflow integrationの評価層を利用する。39 Skill・227件の決定論的出力評価データの構造検証、87 routing fixtureは実Agent発火や生成品質の証明ではない。
- `EVALS.md` の効率比較は `scripts/skills/evals/workflow_efficiency.py` が実測済みJSONを比較する。Agentの起動は行わない。同一scenarioで同じproduct commit/source revisions/scope/QA目的/独立期待基準/test set/environmentを使い、baseline・candidateそれぞれ独立2試行以上を必要とする。品質・安全未PASS、必要試行不足、比較不能は実証済み改善としない。
- #40の検証記録は実Agent縦断、正式trigger、独立Semantic Judge、実運用root・共有writer、既存owner一意性、3構成比較の未達を残している。過去の#22効率比較・人間レビュー/承認時間の対象外も書き換えない。

## 実装1 QA専門判断の改修

共通原則の内容を担当Skillへ反映する。Skillの説明を増やすこと自体を改善としない。既存の適切な記述とHelperは利用し、不足する判断・処理だけ置き換える。

<!-- dprint-ignore -->
| 改善目的 | 対象と具体的な処理 | 維持する境界・確認例 |
| --- | --- | --- |
| 過去合意からの判断 | `spec-analysis/references/authority-resolution.md` とguidance、`question-analysis`、`project-context`、`test-case-design` の根拠選択を接続。有効なSPEC/DEC/承認済みASMを適用範囲・例外・優先順位で選び、複数根拠から期待を導出する | 判断ごとのDEC/ASM新規発行・再承認を要求しない。別機能への適用範囲外、失効、相互矛盾は調査/質問。実装や仮説を正式期待へ昇格しない |
| 必要な知識の利用・蓄積 | `qa-knowledge` のlookup/entry currentness、03のA/B自律起動、各分析Skillの参照条件を更新。過去欠陥・環境・テストデータ・類似機能の知識を必要時に利用 | 全entryの読込・毎回A/Bを強制しない。適用範囲が異なる知識を正式仕様扱いしない |
| 活動・テストレベル・方式 | `test-analysis/references/guidance.md`、`test-architecture-design` のlevel優先・方式選択、`qa-workflow` のroutingを改修。明示指定・承認済み割当を優先。未指定の場合はQA目的・リスク・対象の構造・テスト可能性から静的/コンポーネント/統合/システム/受入等を選ぶ | システムテスト既定は他に判断根拠がない場合のfallbackとする。API/batch/非機能を理由なく外さない。観点のみ依頼に詳細TCを強制せず、詳細TCが必要なら省略しない |
| テスト技法・観点 | `test-analysis/scripts/technique_candidates.py`、`test-condition-design` の技法選択・適用・materialize、`test-requirement-design` / `test-case-design` / `coverage-analysis` を利用する。QA目的・Risk・仕様・対象から必要な技法・深度・条件を選ぶ | 全技法・item×conditionの全組合せを一律要求しない。既存のformal applicability/Disposition・同値分割、境界値、decision table等の決定論的処理、stable CI/TC ID、必要coverageを維持 |
| テストオラクル・観測 | `test-analysis` のテスト可能性、`test-architecture-design` の測定/環境、`test-case-design` の期待結果、実行・独立レビューの契約を見直す。独立した期待値計算、入出力関係、状態遷移、権限、非同期完了、永続状態を必要時に観測 | 実装と同一の誤りを期待側へ複製しない。絶対値不明なら有効な関係を根拠にメタモルフィック技法を検討。観測不能をPASSにしない |
| 欠陥予防と回帰資産 | `defect-management`、`regression-testing`、`test-analysis`、`qa-knowledge`、`coverage-analysis`、`adversarial-review` を接続し、欠陥の原因仮説・実条件・類似箇所からRisk・観点・方式・回帰選定を再評価 | 元結果・正式欠陥状態を書き換えない。継続PASSだけで重要回帰テストを削除しない。廃止仕様・重複・検出力不足など具体的根拠がある場合のみ変更 |
| Agent活動の改善 | `test-evaluation` の案件活動評価と `EVALS.md` のSkill評価を区別。反復質問、設計漏れ、誤った一般化、不要工程、機械処理の失敗を実活動で特定し、原因に応じて案件正本/Knowledge/Skill/Helper/評価資産へ反映 | 採用・実施・効果測定を区別。案件の知識更新でSkill改修完了を主張しない。Skillが自分自身を無断変更する仕組みは作らない |

### 判断事例を実際の評価に追加する条件

既存fixture/rubricで不足する場合だけ、次の対比を追加・更新する。過去の権限合意を新機能に適用する/できない、複数仕様を組み合わせる/競合する、適用scope外・失効・未確定、同じ質問の再発行、必要な質問の欠落、類似欠陥の観点化、観測不能、方式選択、変更されたテスト集合で品質が低下するケース。期待判断は対象の実仕様・有効なDEC/ASM・独立した期待基準を人間または独立評価者が先に定める。Agent生成結果をそのまま正解にしない。

## 実装2 全39 Skill・Helperの責務適正化

01の39行を対象一覧として利用する。実装時に各SKILL.mdと必要なreference、呼出し元/先、Helper・validator、テスト・fixture・配布条件を確認する。各改修Planの処理ごとに維持・削除・既存手段への委譲・必要な外部責務を決める。別の恒久台帳や追加承認gateは作らない。

- `qa-workflow/scripts/artifact_graph.py` のContext parse、fixed-root scan、baseline/history、SQLite workflow state、WCAG確定、claim/reservationを01〜04の責務へ整理する。QA固有の要求・依存・再開・完了を維持する。既存成果物から復元できるstateは削除する。大きなファイルであることだけで再分割しない。
- `project-context` は01の意味管理を残し、案件探索・配置合意・Provider選択の不要な呼出しを削る。単体利用で必要なDEC/ASM・Context更新は維持する。
- `qa-workflow`、`spec-analysis`、`question-analysis`、`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`adversarial-review` の共通自己検証記述を確認する。各Skillの出力品質・責務境界は維持し、同じ手順の重複・長い説明を整理する。機械的な採番・形式違反は既存validatorの局所修正で対応する。最大1回の自動修正制約は、実評価で必要な修正を妨げる場合に限り、改善しない反復を停止する契約へ変更する。無制限反復や他ownerの判断代行は許可しない。変更した場合はEVALSと該当fixtureを同期する。
- 9個の `runtime_contract.py` は現行単体配布の理由があり、複製だけを理由に共通外部依存へ置換しない。変更時は既存同期方法と `test_runtime_portability.py`、`test_context_runtime_transport.py` の同一性・単体利用を確認する。依存関係の管理を利用者へ移さない。
- SKILL.mdは選択条件・責務・必要な入出力・手順に集中し、工程固有の詳細は必要なreferenceへ置く。必要な安全/品質判断の参照が実際のAgentで読まれることをtrigger/実利用で確認する。共通reference化で単体配布が壊れる場合は必要な同梱を維持する。
- #40のA/Bの専門責務と既存state/保存を利用する。統合・分割・廃止は後述の3構成比較で品質・効率・利用性を確認して判断する。必要な履歴・owner handoff・開始要求・反例/Authorityの保証を削らない。比較未達だけで現行2 Skillの優劣を断定しない。

## 検証1 決定論的テスト・CI

改修前HEAD、実行時のPython/Node/Agent client、対象branch、依存バージョンと検証範囲を記録する。各詳細Planで指定したruntimeテストを必要な変更ごとに実行し、変更前後の契約差を確認する。次のコマンドは独立して実行する。既存workflowが要求する環境・追加手順は各 `.github/workflows/*.yml` の現行定義に従う。

<!-- dprint-ignore -->
| 検証 | コマンド/手順 | 期待 |
| --- | --- | --- |
| formatter/lint | `python scripts/format_tracked.py check` | pinned Ruff/dprintの整形・検査成功 |
| 差分空白 | `python .github/check_patch_whitespace.py` | diff契約適合（CI環境で必要なrefを使用） |
| formatter回帰 | `python -m unittest discover -s tests -p 'test_format_tracked.py' -v` | PASS |
| CI空白回帰 | `python -m unittest discover -s tests -p 'test_ci_patch_whitespace.py' -v` | PASS |
| CI安全契約 | `python -m unittest discover -s tests -p 'test_ci_security_contract.py' -v` | PASS |
| Agent Skills仕様 | `skills-ref validate` を各 `skills/<name>` へ実行 | 全現行Skill成功 |
| 回答フォームPython | `python -m unittest discover -s skills/agent-answer-form/tests -v` | PASS |
| 回答フォームNode | `node --test skills/agent-answer-form/tests/form.test.cjs` | PASS |
| フォーム生成 | `python skills/agent-answer-form/scripts/build_form.py --input skills/agent-answer-form/assets/questionnaire_template.json --validate-only`、別途許可一時dirへの `--output` 生成 | 各成功、既存出力領域外へ書込なし |
| 決定論runner | `python -m unittest discover -s scripts/skills/evals/deterministic/tests -v` | PASS |
| 決定論評価資産 | `python -m unittest discover -s tests/skills/evals/deterministic -v` | PASS |
| runtime全suite | `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` | PASS、失敗を隠さない |
| Semantic dataset | `python scripts/skills/evals/semantic/validate.py` | PASS |
| Semantic runner | `python -m unittest discover -s scripts/skills/evals/semantic/tests -v` | PASS |
| Semantic回帰 | `python -m unittest discover -s tests/skills/evals/semantic -v` | PASS |
| trigger契約 | `python -m unittest discover -s tests/skills/evals/trigger -v` | PASS |
| 開発用保護 | `.github/workflows/codex-harness.yml` の既存検証 | Hook/execpolicy/安全契約の回帰なし |

`requirements-dev-lint.txt` / `requirements-dev-evals.txt` とworkflow指定のpinnedツールを使う。実評価の外部LLMをCIへ組み込まない。全5 workflow（Code Quality、Validate Agent Skills、Validate Deterministic Output Evals、Validate Semantic Output Evals、Codex Harness）の最新HEADでsuccessを確認する。実行不能は理由・対象条件を記録し、loopback等の制約を安全機構の回避で解消しない。限定環境で再試験する場合は元suiteの結果と分ける。

## 検証2 実Agentによる改修前後の評価

### 環境と役割

現行baselineはmain `003bbc7...` の実装（#41の方針文書を参照するが未実装の契約を実行させない）。candidateは改修後の固定commit。各試行の対象repository、source revision、build、データ・初期状態、Agent client/version、model、利用可能なtool、許可範囲、出力rootを記録する。利用するAgent clientは全Skillを同時に利用できる状態にする。対象Skillだけをロードした診断試験を正式trigger評価に算入しない。

実務Agentは新しいsessionでQAを実行し、実装Agentは出力を改善するための改修を担当する。評価者は元の仕様・期待・観測と出力を独立に確認する。実装Agentの自己採点だけで完了としない。許可された隔離環境として `qa-training-store`（Scenario Shop）等を候補にし、対象製品のコード・仕様をread-onlyのQA対象にする。テストデータreset、認証、実行副作用、外部送信には許可済み手段を使用する。実環境・Agent・外部送信の許可がなければその試行は未実施/blocked。別の許可済み環境でも同等の品質/安全基準で評価する。製品修正でテストを通さない。

### 実施するQA活動

<!-- dprint-ignore -->
| 活動 | 入力と進め方 | 確認する成果 |
| --- | --- | --- |
| 初回QA | 対象機能、仕様・コード、許可作業先、必要成果物のみを自然言語で依頼 | 不要な設定質問なし、適切な開始Skill、仕様・観点・TC・根拠、必要保存 |
| 同一入力再依頼 | 同じ成果物rootと同じQA目的・版で別session/Agent | 同じ正本・合意、不要再質問/再生成なし、必要なcurrentness |
| 局所コード変更 | 対象scopeと関連sourceを固定し、許可された既存変更revisionを利用 | 変更影響、不要再生成なし、該当scopeの回帰・再設計 |
| 外部仕様改版 | 製品commitを維持し、許可された仕様の改版を入力 | 仕様根拠の変更/失効、適切な局所再検証 |
| 中断・再開 | 質問提示後または成果物保存後に別sessionで再開 | 部分回答・旧フォーム・正本・必要stateからの再開、二重実行なし |
| 横断分析 | 過去の観察・決定・反例がある複数機能、明示無効/未指定/補助/必須を対比 | 必要な自律起動、直接参照で足りる場合は起動なし、反例・例外・失効、#40の保存と再開 |
| 実行・報告 | 既存TC、E2E、非E2E、Regression、Explorationの必要な組合せ | raw、初回FAIL、retry、cleanup、欠陥候補、統合報告、母集団・終了判定 |
| 直接利用・人間編集 | 単体Skill、指定なし/指定あり、既存配置・形式、Markdownの許可編集 | 専用ハーネス不要、必要時だけ質問、旧資産互換、形式と意味の保証 |

最初から各工程の詳細手順をプロンプトで教えない。通常の依頼を出して、Skill選択・判断・実成果物・質問・承認・失敗を観察する。危険な操作が必要な試行では実行許可を明示し、必要条件を省略させない。改修前の失敗を意図的に補正してbaselineに混入させない。単一製品だけに過適合しないよう、同じQA原則を適用できる別機能・資料構造・許可済み製品のholdoutを用意する。

### 評価手順

1. 実際のAgent行動ログ、Skill読み込み証拠、生成成果物、元source、質問/回答、実行結果を許可先に保存する。token/費用など取得不能な指標は未測定理由を記録し、0としない。秘密・生の個人情報は評価資料へ送信しない。
2. EVALS.mdのtrigger評価に従い、全Skill同時利用・独立context、train/validationの分離、原則3試行/query、正例・負例の既存閾値を利用する。追加2 Skillを含む変更したtriggerは正式評価を行う。最終holdoutを学習・指示調整へ流用しない。
3. 生成済み成果物を既存deterministic runnerへ渡す。固定fixtureの自己検証を実Agentの採点と混同しない。期待値は独立に算出し、決定論的技法、ID、依存fingerprint、scope、保存・実行証拠を確認する。
4. 既存Semantic runnerへ実生成成果物と独立Judgeを渡す。例えば `python scripts/skills/evals/semantic/run.py --skill test-case-design --eval-id TC-SEM-001 --output <実生成成果物> --judge-command python <許可済みjudge_adapter.py>`。EVALSの現行CLI・exit codeに従う。Judgeは仕様根拠・誤判断・必要な質問漏れ・過剰質問・技法選択・成果物品質を評価し、機械検証を置換しない。実Agent/Judgeへの外部送信承認がなければ実行しない。
5. [#40の基本設計](2026-11-25_123000_context-rule-synthesis_design.md) §13.2と[Plan 03](2026-11-25_123000_context-rule-synthesis_03_validation.md) §2〜4の複合受入を実施する。導入前・A/Bを統合した1 Skill・2 Skillの3構成を同条件で比較する。各構成×5scenario×独立2試行以上（計30試行以上、スモークは別）と、別feature/別workflow/蓄積前後/新規反例/重複質問の補助評価（各構成最低2回）を実施する。同一試行集合で導入前vs1、導入前vs2、1vs2の比較を作る。採用基準は#40 Plan 03 §4の数値・絶対条件をそのまま用いる（必要質問誤省略等0件、品質改善、重複質問削減、最大入力token・総token・時間・request/Skill回数の上限）。比較前に導入前実測値で上限を固定し、後から緩めない。比較用1 Skillは同等の意味・保存・再開能力を持たせる。未選定構成は隔離workspaceに置き、現行登録へ先に反映しない。選定条件を満たさない2 Skillを1 Skillへ統合する場合は元Planの採用条件・全責務・3 kind・必要な保証を維持する。局所unit testで正式構成選定を代替しない。
6. 失敗時は、対象製品の仕様不足、Agent判断、Skillの記述・発火、routing、Helper、環境、評価期待の誤りを切り分ける。実問題の原因に対応する層だけ修正する。確認できないものを推測で変更しない。改修したら該当試行と関連回帰を別sessionで再実施する。

## 検証3 効率・利用負担の測定

`scripts/skills/evals/workflow_efficiency.py --input <recorded-trials.json>` を既存 `qa-workflow-efficiency-v1` 契約で利用する。`initial_qa`、`unchanged_request`、`local_code_change`、`external_spec_revision`、`interrupted_resume` の5scenarioをbaseline/candidateで各独立2試行以上実施する。各scenario内で product commit/source revisions/scope/QA goal/expectation/test set/environmentを揃える。Agent構成を記録し、Skill改修効果を比較する場合は同じ構成で比較する。複数Agent間の比較を同一試行に混ぜない。

既存指標の作業時間、Skill呼出し・再起動、利用者確認/承認、再分析、retry、再利用/再生成、token/request/costを測定し、品質・機能・安全・追跡性の独立評価を先に判定する。保存漏れ、再入力負担、不要な技術用語による質問は実活動の証拠で確認する。人間レビュー・承認時間の新規測定は過去の対象外と区別して計測方法・母集団を合意する。比較不能値はnullと理由を保持する。

同一テスト集合での効率比較と、方式・テスト集合自体を改善した場合の比較を分ける。後者は同じQA目的・検証責務・リスク・独立品質/安全基準で評価する。既存比較器のtest_set_ref一致条件を破って数値を改善扱いしない。既存の案件QA評価と独立品質結果で成立する場合は比較器を新設・改修しない。必要な不足が実証された場合のみ比較契約を変更する。

## 横断受入 AT-01〜25

各行は元のATの目的と実施先。関連詳細Planの個別テストと実Agent評価を利用し、同じ検証を重複しない。既存#40テストで確認済みの機械条件は関連変更時に回帰し、実運用・実Agentの受入は別に行う。

<!-- dprint-ignore -->
| AT | 実施先 | 最終受入 |
| --- | --- | --- |
| 01 | 01、02 | 指定/既存規則優先、指定なしは許可作業先と標準。案件探索・初回配置承認なし |
| 02 | 01、03 | 既存ref・ID・有効な権限を維持し再利用 |
| 03 | 01〜03 | 依頼された範囲の分析〜TC、根拠・正本・必要保存・検証 |
| 04 | 02 | 仕様ブロッカーの部分保存、該当scopeのみ停止、保存状態の正しい説明 |
| 05 | 02、03 | 部分回答、旧回答/保留、仕様と実行条件の区別、影響範囲再開 |
| 06 | 02、03 | 別session/Agentで成果物・必要stateから継続、未保存を復元と誤認しない |
| 07 | 03、05 | 同一入力・有効な根拠再利用、不要再質問/再生成なし |
| 08 | 03、05 | 外部資料を含む改版・入力完全性、影響scopeのみ再検証 |
| 09 | 01、02 | 通常人間編集・正式変更/生成領域の区別、無断上書きなし |
| 10 | 02、04 | 独立作業と共有競合を区別、混線・二重実行なし |
| 11 | 02、04 | 保存/副作用結果不明の照合、盲目的な再試行なし |
| 12 | 01〜03 | 依存部分保存の整合が成立するまで下流current不可 |
| 13 | 01、03 | 重複正本の誤選択・新規作成なし |
| 14 | 01、02、03 | アクセス不能を不存在にしない、必要な操作だけblock |
| 15 | 02、03 | 承認対象変更・失効・開始後除外。元要求を保持し未承認除外を拒否 |
| 16 | 01、04 | 機密証跡・一時物・必要履歴、任意/必須保存の区別 |
| 17 | 03、04 | 必須要求漏れ検出、横断分析の自律起動、無効尊重、独立補助の制約と必要依存の区別 |
| 18 | 04 | FAILを含む実行完了、合否・母集団・cleanup・終了基準の分離 |
| 19 | 01、03 | 別Agentで同じ正本・命名・配置、別scope/Run衝突なし |
| 20 | 01〜03 | 単発読取・レビュー・調査で不要保存・設定・承認なし |
| 21 | 01〜05 | 直接利用・移植性、案件/Provider管理不要、決定論的品質と許可境界維持 |
| 22 | 05 | 改修前後の読込・質問・管理・再生成削減、QA品質・安全維持 |
| 23 | 02 | 許可済み通常自動保存、通常内容承認の採用、正式意味の保全 |
| 24 | 01、02 | 専用ハーネスなし、指定あり/なし・有効既存規則を利用 |
| 25 | 全詳細 | 必要な保証と単体利用を維持し、不要なCAS/基盤/Helper/複製/承認を削減 |

## リスクと未達の扱い

- Agentの出力は非決定的なため、独立試行・holdout・評価元固定を維持する。fixture成功、CI成功、既存Skillの数・行数削減だけで利用性・品質向上を証明しない。
- 外部Agent・Judge・本番root・共有writer・実owner接続の未設定/未認可は対象範囲を具体的に記録する。利用者が別途必要条件を合意しない限り実行しない。該当する受入は未実施/blockedでありPASSにしない。
- 正式な構成比較が現行2 Skillの統合等を示す場合、実際に変わる責務・依存・成果物の契約と回帰範囲を利用者へ提示して決定する。必要な変更を未達のまま完了扱いしない。

## 完了条件

全18 OPSの目的・必要条件を満たし、AT-01〜25の適用される受入、変更箇所の独立validation、CI、実Agent品質・効率比較を確認する。必要な未達は状態を明示する。不要・対応済み・外部責務・実際に使わない接続は理由を記録し、元の目的を維持して重複実装しない。現行正本・Skill・Helper・評価資産を同期し、不要になった記述や処理を除去する。実装記録には基準/最終commit、変更した契約、独立検証結果、実測結果・比較不能、残存課題と実行環境を記載する。新しい評価台帳や過剰な共通gateは追加しない。
