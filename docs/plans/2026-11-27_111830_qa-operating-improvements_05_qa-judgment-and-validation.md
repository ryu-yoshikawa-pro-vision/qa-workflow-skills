# 専門QA判断・責務適正化・実Agent評価

## 目的・対象

OPS-11・18と全OPSの受入。自律的なQA判断・必要な活動の選択・知識の再利用・欠陥予防・評価を、実際のQA作業で改善する。共通原則に従い、専門外管理処理と重複を削減し、必要な意味判断・決定論的処理・実証拠を残す。01〜04の変更を評価する。評価のための新しい汎用基盤を作らない。

## 現状と維持する契約

- `EVALS.md` の仕様適合、trigger、決定論的出力、意味評価、workflow integrationの評価層を利用する。39 Skill・227件の決定論的出力評価データの構造検証、87 routing fixtureは実Agent発火や生成品質の証明ではない。
- `EVALS.md` の効率比較は `scripts/skills/evals/workflow_efficiency.py` が実測済みJSONを比較する。Agentの起動は行わない。同一scenarioで同じproduct commit/source revisions/scope/QA目的/独立期待基準/test set/environmentを使い、baseline・candidateそれぞれ独立2試行以上を必要とする。品質・安全未PASS、必要試行不足、比較不能は実証済み改善としない。
- #40の検証記録と過去の#22効率比較は当時の結果として保持する。#40の構成比較・実運用受入は今回の完了条件にしない。

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

### テストレベル選択の既存validatorとの整合

test-analysisのlevel既定は専門判断の根拠がない場合に限りシステムテストとする。architecture_runtime.py の BASES/DECIDED_DECISIONS/DECISION_BY_BASIS、PRIORITY_KEYS、ASSIGNMENT_KEYS、_validate_priorities、割当のbasis_source_ids検証、completion_check/_check_approval を06のレベル選択契約に合わせる。level_priority に専門判断によるlevel集合と理由を追加し、明示・有効な承認済み方式との競合を隠さず、これらがない場合は根拠ある専門判断、最後に既定値の順とする。正式な機械処理用JSONのQA専門判断の割当には実根拠のsource IDと理由を要求する。通常相談・初期調査・Markdownでは実際に確認した仕様・コード等の参照と判断理由を用い、ID未発行だけで既定値に戻さない。機械処理が必要になったときは既存schemaに従って実sourceを識別し、根拠を捏造しない。選択理由のenumだけ追加して完了としない。承認済み方式/正式scope変更、組織決裁、リスク受容に必要な承認は維持し、単なる既定との差は承認理由にしない。旧JSON・旧enum・旧承認証拠の過去検証は維持。既存levelの「コンポーネント」「API」「システム」「受入」「別レベル」を維持し、統合テストは対象に応じAPIまたは別レベル（具体的な統合対象をmethodで記す）、静的テスト・探索は活動/方式であり独自levelを新設しない。data-contract、template、handoff、test-analysis/TR/TCN/TC、owner verifier、fixtureを同期する。

### 判断事例を実際の評価に追加する条件

既存fixture/rubricで不足する場合だけ、次の対比を追加・更新する。過去の権限合意を新機能に適用する/できない、複数仕様を組み合わせる/競合する、適用scope外・失効・未確定、同じ質問の再発行、必要な質問の欠落、類似欠陥の観点化、観測不能、方式選択、変更されたテスト集合で品質が低下するケース。期待判断は対象の実仕様・有効なDEC/ASM・独立した期待基準を人間または独立評価者が先に定める。Agent生成結果をそのまま正解にしない。

## 実装2 全39 Skill・Helperの責務適正化

01の39行を対象一覧として利用する。実装時に各SKILL.mdと必要なreference、呼出し元/先、Helper・validator、テスト・fixture・配布条件を確認する。各改修Planの処理ごとに維持・削除・既存手段への委譲・必要な外部責務を決める。別の恒久台帳や追加承認gateは作らない。

- artifact_graph.py、workflow_runtime.py、context_workflow_state.py、owner_verifiers.py、downstream_state.pyを03・04へ変更する。SQLite state・全revision・汎用予約・保存gateを削減し、Context parse、QA要求、安定ID、依存、必要機械検証・再開を維持する。
- `project-context` は01の意味管理を残し、案件探索・配置合意・Provider選択の不要な呼出しを削る。単体利用で必要なDEC/ASM・Context更新は維持する。
- `qa-workflow`、`spec-analysis`、`question-analysis`、`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`adversarial-review` の共通自己検証記述を確認する。各Skillの出力品質・責務境界は維持し、同じ手順の重複・長い説明を整理する。機械的な採番・形式違反は既存validatorの局所修正で対応する。最大1回の局所自己修正は現時点では維持する。根拠不足・他owner判断は局所修正ではなく担当工程へ戻し、再実行は原因解消後に行う。実評価で制約が不適切と確認された場合は、対象違反・停止条件・必要な反復上限を根拠付きでPlan変更として合意し、EVALSと該当fixtureを同期する。
- 9個の `runtime_contract.py` は現行単体配布の理由があり、複製だけを理由に共通外部依存へ置換しない。変更時は既存同期方法と `test_runtime_portability.py`、`test_context_runtime_transport.py` の同一性・単体利用を確認する。依存関係の管理を利用者へ移さない。
- SKILL.mdは選択条件・責務・必要な入出力・手順に集中し、工程固有の詳細は必要なreferenceへ置く。必要な安全/品質判断の参照が実際のAgentで読まれることをtrigger/実利用で確認する。共通reference化で単体配布が壊れる場合は必要な同梱を維持する。
- #40の現行2 Skill構成、A/Bの専門責務、3 kindのJSON、根拠を維持し、保存・stateを02・03で簡素化する。構成比較・統合候補の実装・最終選定は対象外。必要なhandoff・開始要求・反例/Authorityを削らない。

### 変更対象の判断

01の39行に対し、次の担当別変更を実施する。全Skillへの機械処理追加や全referenceの書換えは要求しない。既存記述がこの契約を満たしていれば維持し、その根拠と実際の変更箇所を既存実装記録へ記す。

<!-- dprint-ignore -->
| Skill群 | 改修内容・維持する責務 |
| --- | --- |
| qa-workflow、project-context | 01〜04の配置管理削減・必要入力・進行/要求/再開/完了。ContextのQA意味管理を保持 |
| feature-analysis、spec-analysis、ui-target-analysis | 01・02の正本/保存、合意からのAuthority判断。Git差分・UI packageの実検証を維持 |
| question-analysis、agent-answer-form | 02の自己解決・回答反映・識別。フォームに仕様判断を持たせない |
| test-requirements-analysis、test-architecture-design、test-management | 01・02の正本・通常保存と承認、方式自律選択。母集団・根拠・終了基準を維持 |
| test-analysis、test-item-analysis、test-condition-analysis、test-requirement-design、test-condition-design、test-case-design、coverage-analysis、adversarial-review | 01・02の保存・03の局所再検証・05の技法/根拠。機械生成・独立レビュー・ID/coverage/Dispositionを維持 |
| e2e-test-selection、e2e-test-inspection、e2e-test-implementation、e2e-test-execution、e2e-test-result-analysis、e2e-test-reporting | 01〜04の選定・実効設定・実装・実行・結果・報告を再利用し重複確認を削減。コード権限・raw/初回結果を維持 |
| test-target-inspection、test-execution、testware-implementation、testware-execution | 01〜04の保存・許可・実行/隔離/cleanup。観測と実行証拠・コード保護を維持 |
| regression-testing、exploratory-testing、qa-knowledge、context-signal-audit、context-rule-synthesis | 01〜04の既存ref/履歴、局所再利用・横断自律起動。A/Bの不変batch・候補・run・根拠と再開を維持 |
| defect-management、test-reporting、test-evaluation | 02・04の候補/承認・実結果連携、05の活動改善。正式欠陥・母集団・終了判断・効果測定を区別 |
| usability-evaluation、usability-inspection、wcag-conformance-evaluation | 01・03・04の資料評価/実観測/正式評価の区別、保護証跡と専用closure維持。WCAGの旧説明を修正しSQLite依存を解消 |

各変更は対象SKILL.md・該当reference・template・既存Helper/validator・呼出し元・必要fixtureを同時更新する。共通化は実際の重複のみ。

全39 Skill・99スクリプトの関連コード走査に基づき、02〜04の対象関数・呼出し元、SKILL.md/reference/template、fixture・rubricを同期する。別の共通API、履歴サービス、JSON DB、中央indexへ置換しない。9個のruntime_contract.pyと2個のcandidate_support.pyのコピー整合・単体利用は維持する。決定論的技法・Entity・coverage・UI package・実行raw・独立検証は管理機構削減を理由に削らない。

## 検証1 決定論的テスト・CI

SQLite履歴・専用store固有のテスト（test_pr24_artifact_store.py、test_pr24_git_artifact_store.py、test_sqlite_workflow_history.py）は、廃止する処理だけを検証するものは削除し、QA上必要な保証の検証は通常ファイル経路へ置き換える。汎用予約・全snapshot固有テストも同様に整理する。元要求漏れ、未承認正式変更、別root混入、過去根拠欠落、実行・cleanup、機密保護・path逸脱、安定ID・変更影響のテストは保存方式に依存しない結果検証として維持する。test_context_artifact_store.py、test_context_workflow_state.py、test_qa_workflow_baseline.py、test_shared_resource_contract.py、test_qa_operation_claim.py、test_e2e_selection_contract.py、test_test_item_condition_analysis.py、test_pr32_test_evaluation.py、WCAG・UI・非E2E・CI handoff回帰を確認する。

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

#40の検証記録では39 Skill・227 casesのdataset構造、runtime局所回帰153件、runner/contractテストを検証済み。実生成出力の評価とは区別する。既存評価資産で変更箇所を回帰し、Codexで自己解決・回答反映、元要求・過去完了と現在採用、知識再利用、本文読込量・必要根拠を評価する。実運用root・共有writerの実接続は対象外。

## 検証2 実Agentによる改修前後の評価

### 環境と役割

現行baselineはmain `003bbc7a32bf5b4605696564a9254dd5053ccf5f` の実装・当時の文書のみ（候補方針をbaselineのAgentに読ませない）。candidateは改修後の固定commit。各試行の対象repository、source revision、build、データ・初期状態、Agent client/version、model、利用可能なtool、許可範囲、出力rootを記録する。利用するAgent clientは全Skillを同時に利用できる状態にする。対象Skillだけをロードした診断試験を正式trigger評価に算入しない。

実務Agentは新しいsessionでQAを実行し、評価者は固定仕様・期待・観測と出力を独立に確認する。入力は本リポジトリの既存eval cases、routing fixture、runtime/integration fixtureとする。必要な横断シナリオは既存fixtureを組み合わせ、一時ディレクトリで保存・再開・改版・実行を検証する。外部製品・実案件・実サービスの実接続を要求しない。fixtureを正解に合わせて変更しない。

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

通常の依頼を出してSkill選択・判断・成果物・質問・承認・失敗を観察する。baselineへ候補方針を混入させない。実行条件・必要な許可を明示し、既存の異なる機能・資料構造の未使用caseをholdoutにする。 評価開始前に許可済み保存先・配置・通常保存の許可、仕様質問への回答、操作権限を既存case/rubricまたは実施記録に固定する。同じ質問には改修前後で同じ最小限の回答を返し、実際の質問・回答・承認回数を計測する。初回依頼に候補方針や追加手順を混入させない。旧契約の管理質問も実際に回答して進めるが、未許可操作を許可したり認証・provider証拠を捏造したりしない。実際の制約で完走不能なら未完了・比較不能の理由を記録する。

### 実行条件の固定と独立した期待結果

試験入力はリポジトリ内の仕様・入力・期待結果・観測・テストfixtureから選ぶ。初回、変更なし、局所変更、仕様改版、中断再開は同じ既存fixtureの固定版・初期状態・scope・目的・独立期待で比較する。依頼は通常の自然言語とし、実操作はfixtureが許可する範囲で実行する。必要な観点・質問・不要質問・禁止操作・期待観測を既存case/rubricまたは実施記録に固定し、出力から正解を逆算しない。

実Agent評価は利用者指定のCodex。全39 Skillを同時に利用可能な隔離workspaceで、選択条件・入出力・連携を変更したSkillと影響するSkillの既存validation queryを原則3回ずつ独立sessionで実行し、EVALSの正例 >0.5、負例 <0.5 とholdout条件を維持する。全Skillの既存構造検証・trigger契約テストは維持する。変更と無関係な正式queryの全面再評価は必須にしない。既存trigger/run.pyのClaude Code経路は変更しない。Codex実ログで発火を確認し、必要な取得・集計だけ既存runnerへ局所追加する。回答文やtarget-only smokeで正式発火を代用しない。他clientは既存単体利用・配布・移植性テストで確認し、外部clientの実運用受入やモデル/ハーネス比較を要求しない。

### 評価手順

1. 実際のAgent行動ログ、Skill読み込み証拠、生成成果物、元source、質問/回答、実行結果を許可先に保存する。token/費用など取得不能な指標は未測定理由を記録し、0としない。秘密・生の個人情報は評価資料へ送信しない。
2. EVALS.mdのtrigger評価に従い、全Skill同時利用・独立context、train/validation分離、原則3試行/query、既存閾値を用いる。変更・影響Skillの正例/負例と未使用holdoutを確認する。全Skillの構造・routing回帰は維持する。
3. 生成済み成果物を既存deterministic runnerへ渡す。固定fixtureの自己検証を実Agentの採点と混同しない。期待値は独立に算出し、決定論的技法、ID、依存fingerprint、scope、保存・実行証拠を確認する。
4. 既存Semantic runnerへ実生成成果物と独立Judgeを渡す。例えば `python scripts/skills/evals/semantic/run.py --skill test-case-design --eval-id TC-SEM-001 --output <実生成成果物> --judge-command python <許可済みjudge_adapter.py>`。EVALSの現行CLI・exit codeに従う。Judgeは仕様根拠・誤判断・必要な質問漏れ・過剰質問・技法選択・成果物品質を評価し、機械検証を置換しない。実Agent/Judgeへの外部送信承認がなければ実行しない。
5. 現行A/B 2 Skillの変更に関係する#40の既存case・rubric・回帰を利用し、観察事実・根拠・反例・範囲・必要質問・自律起動・保存/再開・要求充足を評価する。構成比較のための1 Skill候補や導入前構成は作らない。
6. 失敗時は、対象製品の仕様不足、Agent判断、Skillの記述・発火、routing、Helper、環境、評価期待の誤りを切り分ける。実問題の原因に対応する層だけ修正する。確認できないものを推測で変更しない。改修したら該当試行と関連回帰を別sessionで再実施する。

今回の改修効果はmain 003bbc7と改修後commitの比較で確認する。過去の#40構成比較・最終選定・実運用受入は別目的であり対象外。既存評価結果と未実施記録を書き換えない。

## 検証3 効率・利用負担の測定

`scripts/skills/evals/workflow_efficiency.py --input <recorded-trials.json>` を既存 `qa-workflow-efficiency-v1` 契約で利用する。`initial_qa`、`unchanged_request`、`local_code_change`、`external_spec_revision`、`interrupted_resume` の5scenarioをbaseline/candidateで各独立2試行以上実施する。各scenario内で product commit/source revisions/scope/QA goal/expectation/test set/environmentを揃える。Agent構成を記録し、Skill改修効果を比較する場合は同じ構成で比較する。複数Agent間の比較を同一試行に混ぜない。

既存指標の作業時間、Skill呼出し・再起動、利用者確認/承認、再分析、retry、再利用/再生成、token/request/costを測定し、品質・機能・安全・追跡性の独立評価を先に判定する。保存漏れ、再入力負担、不要な技術用語による質問は実活動の証拠で確認する。人間レビュー・承認時間の新規測定は過去の対象外と区別して計測方法・母集団を合意する。比較不能値はnullと理由を保持する。

同一テスト集合での効率比較と、方式・テスト集合自体を改善した場合の比較を分ける。効率比較の5scenarioは既存fixtureから同じtest_set_refで成立する条件を実施前に選定し、実際に使用した集合が一致することを確認する。専門判断の改善を評価する試行ではテスト集合を固定して判断を妨げない。後者は同じQA目的・検証責務・リスク・独立品質/安全基準で評価する。既存比較器のtest_set_ref一致条件を破って数値を改善扱いしない。既存の案件QA評価と独立品質結果で成立する場合は比較器を新設・改修しない。必要な不足が実証された場合のみ比較契約を変更する。

既存比較器の efficiency_evidenced / needs_review / unproven をそのまま記録する。今回の目的達成は、独立functional/quality/safety/traceabilityが全てpassし、必要な質問・承認・保存・実行証拠の欠落や安全違反が0で、改修対象の不要質問/承認/設定・再入力・不要再分析について、baselineで問題があった項目の改善を実証することを条件とする。baselineが既に0件または必要処理のみの項目は同等維持を許容し、数値を減らすため必要処理を省かない。測定不能項目は未測定とし、必要な改善証拠が不足した項目は未達とする。変更なし再依頼の不要再生成は0。必要調査が増える等の合理的な負荷増があれば、各指標の中央値・最小・最大と原因、利用者負担・品質への効果を示し、比較器判定を変えず改善採否を別に記録する。実測不足・品質未達は採用不可。比較前に測定条件・許容する負荷増の根拠と採否条件を固定する。根拠のない固定削減率を新設せず、重大なトレードオフは利用者と合意する。今回の比較器と既存品質基準を適用する。

既存指標に加えて管理目的のHelper呼出し、保存の不要な停止、管理ファイル・保存手順数を実ログで確認する。独立試行は同じ初期状態、固定条件で行い失敗試行を除外しない。holdoutは改修用事例と分ける。今回の5scenario×改修前後×各2試行以上の既存条件と品質基準を維持する。ばらつきで採否が決まらない場合の追加試行条件・上限・判定基準を比較前に固定し、同じscenarioの改修前後へ同条件で追加する。初回を含む全試行で評価し、合格まで繰り返す運用にしない。上限内で判断できなければ該当効果は未実証とする。

## 横断受入 AT-01〜25

各行は元のATの目的と実施先。関連詳細Planの個別テストとリポジトリ内の実Agent評価を利用し、重複しない。既存#40テストで確認済みの機械条件は関連変更時に回帰する。実運用受入は含めない。

<!-- dprint-ignore -->
| AT | 実施先 | 最終受入 |
| --- | --- | --- |
| 01 | 01、02 | 指定/既存規則優先、指定なしは許可作業先と標準。案件探索・初回配置承認なし |
| 02 | 01、03 | 既存ref・ID・有効な権限を維持し再利用 |
| 03 | 01〜03、05 | 依頼された範囲の分析〜TC、根拠・正本・必要保存・担当Skillの必須機械検証 |
| 04 | 02 | 仕様ブロッカーの部分保存、該当scopeのみ停止、保存状態の正しい説明 |
| 05 | 02、03 | 部分回答、旧回答/保留、仕様と実行条件の区別、影響範囲再開 |
| 06 | 02、03 | 別session/Agentで継続。途中でstateが必要になっても元要求・完了済み・未解決を保持 |
| 07 | 02、03、05 | 同一入力・有効な根拠再利用、不要再質問/再生成なし。更新前の差分検証と更新後の現行検証を区別 |
| 08 | 01〜03、05 | 改版・入力完全性、空used_fieldsからのContext後発生成、共通制約/例外の変更、旧版取得不能時の現行根拠照合と必要部分のみ修正 |
| 09 | 01、02、06 | 通常人間編集・正式変更/生成領域の区別、無断上書きなし。内部IDがない一意な正本の編集、Markdown正本と派生機械入力の分離・検証 |
| 10 | 02、04 | 独立作業と共有競合を区別、混線・二重実行なし |
| 11 | 02、04 | 保存/副作用結果不明の照合、盲目的な再試行なし |
| 12 | 01〜03 | 依存部分保存の整合が成立するまで下流current不可 |
| 13 | 01、03、06 | 派生snapshotを正本候補から除外し、実際の重複正本の誤選択・新規作成なし。明示refと曖昧なidentityを区別 |
| 14 | 01、02、03 | アクセス不能を不存在にしない、必要な操作だけblock |
| 15 | 02、03、06 | 承認対象変更・失効・開始後除外。元要求、部分承認、過去採用と現在採用を区別 |
| 16 | 01、04 | URL query・DOM・console・trace・報告転載、保護rawのGit追跡・公開防止、一時物・必要履歴、任意/必須保存の区別 |
| 17 | 03、04、05 | 独立の要求集合との照合、単一sessionでも要求集合と実行結果の両方からの必須scope除外を検出。機械scope 0、専用検証未達、補助から必須への変更、自律起動・無効尊重、通常資料参照の不要起動なし |
| 18 | 04 | FAILを含む実行完了、合否・母集団・cleanup・終了基準の分離 |
| 19 | 01、03 | 別Agentで同じ正本・命名・配置、新規pathのNFCと既存実path、安全な日本語名・長いpath・短縮識別子衝突、別scope/Run衝突なし |
| 20 | 01〜03 | 単発読取・レビュー・調査は対話回答、再利用価値のある知識だけ許可範囲で自律保存。非保存・無効指定尊重、不要な設定・承認なし |
| 21 | 01〜05 | 変更・影響SkillのCodex評価、既存単体利用・配布・移植性検証。案件/provider管理不要、決定論的品質と許可境界維持 |
| 22 | 05 | 改修前後の読込・質問・管理・再生成削減、QA品質・安全維持。固定回答・質問/承認回数、同一test_set_refの効率比較、事前に固定した追加試行条件と全試行の採用 |
| 23 | 02 | 許可済み通常自動保存、通常内容承認の採用、正式意味の保全 |
| 24 | 01、02 | 専用ハーネスなし、指定あり/なし・有効既存規則を利用 |
| 25 | 全詳細 | 通常Markdown/JSON・直接利用、SQLite廃止、不要なCAS/全履歴/予約/Helper/複製/承認なし。通常相談・Markdownで根拠IDを強制せず、機械契約・品質・安全・旧成果物読取を維持 |

## リスクと未達の扱い

- Agentの出力は非決定的なため、独立試行・holdout・評価元固定を維持する。fixture成功、CI成功、既存Skillの数・行数削減だけで利用性・品質向上を証明しない。
- リポジトリ内評価資産による必要なCodex/Judge実行が不能・未認可なら未実施と記録する。外部実運用root・共有writer・実owner接続・別clientの運用受入は対象外であり、今回の未達条件にしない。
- 現行2 Skillを維持する。過去の構成比較は対象外であり、今回の完了をその比較結果に依存させない。

## 完了条件

全18 OPSの目的・必要条件を満たし、AT-01〜25の適用される受入、変更箇所の独立validation、CI、実Agent品質・効率比較を確認する。必要な未達は状態を明示する。不要・対応済み・外部責務・実際に使わない接続は理由を記録し、元の目的を維持して重複実装しない。現行正本・Skill・Helper・評価資産を同期し、不要になった記述や処理を除去する。実装記録には基準/最終commit、変更した契約、独立検証結果、実測結果・比較不能、残存課題と実行環境を記載する。新しい評価台帳や過剰な共通gateは追加しない。
