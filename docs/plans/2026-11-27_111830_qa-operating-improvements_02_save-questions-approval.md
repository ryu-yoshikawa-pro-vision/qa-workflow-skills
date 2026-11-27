# 保存・質問・承認・継続の改修

## 目的・対象範囲

OPS-01〜04・06・18。成果物作成は必要な時点で保存し、通常保存や工程進行を都度承認で止めない。未確定の仕様・リスク受容・必要な操作許可を区別し、回答後は影響範囲だけ再開する。01の配置・正本形式を前提とする。共有資源の実操作は04、完了判定は03。

## 現状・維持する契約

- `question-analysis` の `references/guidance.md` L60〜99は期待挙動のSPEC/DEC/ASMへの正規化を中心とする。Q ID・UNKNOWN・分類・再開先は既存 `question_ids.py` と出力templateを維持する。
- `agent-answer-form` の `scripts/build_form.py`、`references/json-format.md` はフォームID・質問ID・定義hashで回答を分離する。旧HTMLによる未回収回答の復元、v3/v4等の互換、外部通信なしを維持する。
- `qa-workflow/references/guidance.md` の進行モードは利用者明示 > Context Section 10 > continuous。`test-item-analysis` / `test-condition-analysis` のSave and resumeはprovider CAS・approval policy・独立readbackを要求する。計画3 Skillは保存・承認provider未接続を草案とする。`test-evaluation` は改善採用・受領の認証済み確認を要求する。
- `workflow_runtime.py` の `_exclusion_confirmed()` は常にFalse。`excluded_by_approval` は現在の完了契約では未確定になる。#40の指定root・通常create/read/list/history、条件付き更新、実owner handoffの結果不明時の停止は維持する。

## 実装1 保存対象と時点

各ownerのSKILL.mdと必要なreferenceで、成果物作成依頼（分析・設計・更新・実行・計画・知識の作成）と、単発の相談・読取・レビュー・調査を区別する。前者は明示の非保存指定がなければ必要成果物を自動保存する。後者は原則対話回答、継続利用・保存依頼がある時だけ保存。任意rawは保存対象の既定に含めない。

<!-- dprint-ignore -->
| 契機 | 保存する内容 | 注意点 |
| --- | --- | --- |
| 担当工程完了時 | 作成・更新した正本、必要な根拠・参照 | 既存と同一なら書き直さない |
| 必要な質問の提示前 | 作業済み部分、質問ID/元質問、影響、必要な候補 | 正式採用済みの意味は変更しない。単発対話質問に永続化を強制しない |
| 回答反映後 | 回答の原文または必要な記録、担当ownerの反映結果、未解決範囲 | 反映に必要な承認・権限を確認し、未確定は区別 |
| 中断時 | 継続に必要で未保存の変更・再開先 | 強制終了など実行できない状況で保存を保証しない |
| 次工程引継ぎ前 | 下流が実際に使う成果物と必要な参照 | 依存する部分保存が未確定なら該当下流の採用を止める |

未承認の追加内容は既存の候補欄、草案、または既存ownerの候補形式に記録する。承認済み仕様を候補で上書きしない。草案の正式採用を禁止するが保存は妨げない。既存成果物で再開可能な情報をworkflow stateへ再度書かない。workflow stateが必要な場合は既存envelopeと `unresolved`、`handoffs`、`requested_scopes` 等を用い、参照・未解決理由・再開先など復元できない内容に限定する。

## 実装2 保存経路の改修

01の指定解決と既存OS/sandbox権限を利用する。既存のファイル操作・標準機能を優先する。通常の文書保存に新しい汎用保存adapterや認証hostを追加しない。保存と内容承認を別に判定する。

<!-- dprint-ignore -->
| 対象コード/契約 | 改修内容 | 維持する保証 |
| --- | --- | --- |
| `project-context/scripts/project_context.py` の `persist_prepared`、`artifact_store.py`、`git_artifact_store.py` | 通常ローカル保存で既存書込権限を利用できるようにする。指定された厳密契約・既存Git/SQLite正本の経路は利用可能なまま残す | 必要な条件付き更新、旧revision、認可。既存storeを一括削除しない |
| `feature-analysis/scripts/feature_registry.py` の `persist_snapshot`、`analyze`、`candidate_handoff` | 承認を必要としない台帳候補・分析結果の通常保存と、正式な再分類・retire等の判断を分離する。既存Git source検証・source inventoryを維持 | FEAT ID、変更履歴、Git sourceの真正性、再分類承認、現在性 |
| `test-item-analysis/scripts/item_candidates.py`、`test-condition-analysis/scripts/condition_candidates.py`、双方の `candidate_support.py` とSave and resume | write preconditionから一律の保存承認・provider前提を外し、既存環境で候補を保存する経路を接続。候補schema、validator、既存論理refを利用 | stable ITEM/COND ID、履歴、根拠、B snapshotの完全性、共有更新時の競合防止 |
| `test-requirements-analysis/scripts/qa_requirement_runtime.py`、`test-architecture-design/scripts/architecture_runtime.py`、`test-management/scripts/management_runtime.py` | 01の新規Markdown正本・既存JSON互換と接続し、草案の保存を可能にする。内容の確定・計画承認は保存の条件ではなく、正式採用の条件にする | ownerのvalidate/impact/completion、必要な計画母集団・承認対象の束縛 |
| `e2e-test-selection/scripts/selection_contract.py`、`qa-knowledge/scripts/knowledge_runtime.py` | 通常保存の不要な承認を外し、既存schemaと選定/entryの同一性・currentnessを維持。改善承認に由来する更新は該当承認を保持 | 同一entry競合、replacement・履歴・既存refの一貫性、選定理由 |
| `regression-testing/scripts/regression_runtime.py`、`exploratory-testing/scripts/exploratory_runtime.py`、`test-reporting/scripts/reporting_runtime.py`、`defect-management/scripts/defect_runtime.py`、`test-evaluation/scripts/evaluation_runtime.py` | Run/Activity/Session・報告・欠陥候補・改善記録を許可先へ保存。元結果の再判定、既存snapshot更新、外部Issue作成は通常保存と分離 | immutable結果/報告、安定ref、必要履歴・実行証拠、外部認可 |
| `spec-analysis` / `ui-target-analysis` の既存 `ui_target_package.py`、`human_editing.py` | 専用writerを必要とするpackageだけ適用。通常Markdownへ一律拡大しない | packageの生成領域・ID・scope・履歴・atomic境界 |
| `scripts/context_artifact_store.py`、`scripts/context_artifacts.py`、`context_workflow_state.py` | #40の保存実装を利用する。stateの要求追加・完了は03の契約に従い、通常QA文書に3 kindの制約を広げない | immutable batch、関連候補の同一保存境界、runの再開・必要なhistory |

表にないownerも01のマトリクスの保存要否に従い、既存契約に含まれる一律承認・外部設定依存を除く。QAの判断・採番・構造検証を削らない。

### 既存ownerの保存入口

- project-context は prepare_create/prepare_sections/prepare_update/prepare_ids の意味検証を通し、通常文書は生成した候補を許可済み既存ファイル操作で保存・確認する。persist_prepared の厳密保存は指定済み契約に限定する。旧DEC/ASMを失わない。
- feature_registry の analyze/candidate_handoff は候補検証・引継ぎに利用する。code sourceを正式台帳へ反映する persist_snapshot は実Git列挙・reconcile_git_coverage・HEAD/前回source照合と履歴・再分類認可を維持し、通常新規/通常更新だけ保存承認を不要にする。未検証候補を正式台帳へ直接書かない。
- item/condition は既存候補helperでID・履歴・親子・依存を検証して保存する。新規・隔離した通常更新は実ファイル操作、共有更新は既存storeの条件付き更新。e2e-test-selection は selection_contract の validate/impact と現行revision digest、qa-knowledge は既存entryのvalidate/lookup/create/update/revalidationを通す。推定で履歴やIDを再生成しない。
- 計画3 Skillは01の形式別validate/readback/impact/completionを利用し、草案保存と正式承認を分ける。regression/exploration/reporting/defect/evaluation は各runtimeの生成・検証済み成果物を既存schemaで保存する。Runやimmutable snapshotは同一identityに異なる内容を書込まない。report_snapshot の実readbackを維持する。UI package、A/B、実行rawの専用writerは引き続き使用する。
- 新しい共通保存APIを作らず、既存writerの実行前検証と実書込み/結果確認を分ける。必要な認可・意味検証を無効化して通常保存を実現しない。

単独作業の新規文書は既存の通常ファイル保存と結果確認。新規作成時は対象確認を行い既存正本を上書きしない。既存文書の非破壊更新は対象・差分・必要履歴を確認する。共有writer、同一IDのcreate、実行副作用、正式snapshotや必要な過去revisionの再取得が関係する経路では既存の原子的作成・条件付き更新・履歴・必要なreadbackを利用する。単一writerであることを根拠なく仮定しない。既存標準操作で必要な保証が成立しない場合はその操作だけblockし、独立した分析を続行する。必要な保存技術は利用者へ選択させず、不足する具体的な場所・許可・運用条件のみ確認する。

保存状態は、確認済み成功=保存済み、今回の書込なしが確認済み=未保存、書込後の確認不能=保存結果不明。内容承認やcurrentnessとは別に扱う。結果不明時は実保存先から結果を再取得して確認し、盲目的に再書込みしない。依存する複数成果物の部分保存は実際に保存したref/revisionと対応を確認し、必要な依存整合が取れるまで下流をcurrentとしない。無断rollback・別正本生成はしない。

## 実装3 質問と回答の正規化

`skills/question-analysis/SKILL.md`、`references/guidance.md`、`assets/output-template.md` を改修する。質問の前に、Authority、既存DEC/ASM、質問/回答、Knowledge、許可された仕様・コードを調査し、専門QA判断で解消できるものを質問しない。質問する場合は既存分類とQ IDを使い、根拠・必要な判断・影響・回答なしの処理・反映先・再開先を明示する。単一の質問に必要な情報をまとめ、回答を待つ範囲だけを停止する。

<!-- dprint-ignore -->
| 回答の意味 | 正式反映先 | 再開条件 |
| --- | --- | --- |
| 権威ある仕様の提示・更新 | spec-analysis のSPEC/Authority | 仕様ref/revision・適用範囲確認 |
| 仕様決定 | spec-analysis / DEC正本owner | 有効な明示決定と範囲 |
| 暫定的な期待挙動 | ASM正本owner | 明示承認。SPEC/DECを上書きしない |
| QA目的・対象/対象外・品質目標 | test-requirements-analysis | 依頼者の有効な判断。必要時に計画・方式へ影響を渡す |
| 方式、環境、実行分担 | test-architecture-design / test-management | 方式/計画の必要な正式確定、対象条件 |
| URL・データ・実行条件・保存先 | 該当ownerの実行条件またはContextの意味情報、呼出し側の作業条件 | 実際の利用可否と必要権限を確認 |
| 外部書込、破壊的操作の許可 | 操作owner | 実操作に必要な権限・対象・上限を確認。対話回答は認可そのものではない |
| 保留・曖昧回答・拒否 | 元質問の状態 | 影響scopeのみ未解決/停止 |

question-analysisは回答の意味・反映先・再開先を判断し、他ownerの正本を直接変更しない。担当ownerが正式反映し、qa-workflowが意味が変わる最も早い担当scopeから再開する。部分回答で解決済みの質問を再発行しない。既存質問一覧の現行未解決と必要な過去回答履歴を分離する。全回答をDEC/ASMへ変換しない。一般の実行条件や保存先に仕様Authority IDを付与しない。

## 実装4 回答フォームと質問履歴

`agent-answer-form/SKILL.md`・`references/json-format.md`・`scripts/build_form.py`・既存Node/Pythonテストを使用する。単発質問は通常対話/Markdown。複数の独立質問をまとめる方が効率的な場合にフォームを利用する。質問の採否・仕様決定・進行制御をフォームSkillに追加しない。

- 質問JSONのQ IDは元質問のID。assets/form.js の exportMarkdown でフォームIDと各回答のQ ID・既存 q._definitionHash を自動出力する。コピー・保存の両経路に同じ情報を含め、build_form.py が埋め込む実定義と照合する。フォームIDが一致しても定義hashが異なる質問は保留する。旧出力は元フォーム・対象scope・Q ID・定義を一意に対応付けられる場合のみ利用し、不明な回答だけ再確認する。hashは意味対応の識別であり本人性の証明ではない。利用者にhash入力やJSON/HTML整合検証を求めない。
- 定義変更前のHTML・元JSON・元質問は未回収回答の回収に必要な間保持する。現行のlocalStorage v4/v3契約を維持し、旧HTMLを同じブラウザ・保存領域で開けば旧回答を回収できることを実テストする。元JSONから旧HTMLを再生成する方法で同等の保存領域/キーが確実に利用できることを実証できる場合だけ保管を簡素化する。再生成が成立しない場合は旧HTML保管を継続する。
- 質問の意味変更、表示番号のみ変更、部分回答、保留、推奨未選択、古い定義、未保存、複数form、別scope、秘密情報を検証する。回答回収不能を「未回答だった」と推定しない。未保存の候補は現在の対話で返すが別sessionの復元保証をしない。

## 実装5 内容承認・進行・対象外

通常の内容承認は依頼者の明示判断と、対象となる実成果物/決定/適用範囲の記録で成立する。回答者が正式な決裁権限を持たない場合、組織の決裁契約や外部操作権限が必要な場合は該当経路を維持する。人間の明示承認を通常Git pushや専用認証サービスと結び付けない。既存の有効な厳密契約が指定された経路には引き続き従う。

- `qa-workflow/SKILL.md`、`references/guidance.md` の進行モード、`assets/project-context-template.md` Section 10、routing fixtures、運用文書を同期。既定continuous、利用者が明示したgatedのみ有効。既存Section 10に値があっても無条件に進行を停止しない。利用者が現在の依頼で既存運用を明示適用した場合は、その明示条件として扱う。gatedは指定境界だけ停止し、仕様承認と混同しない。
- 関連ownerの内容承認recordは対象・承認内容・必要なscope・根拠/変更影響を保持する。複数判断は関連性があり一緒に回答できる場合だけ集約し、部分承認・保留・拒否を正しく扱う。承認に影響する意味・適用範囲・期限の変更は再判断する。候補の自動保存や意味不変の表示編集のみで承認を取り消さない。
- `test-requirements-analysis`、`test-architecture-design`、`test-management` の既存validatorは承認recordと意味/対象の束縛を検証するが、利用者本人性や組織認可を証明するものではない。通常の内容承認では実際の利用者回答を正本または既存質問回答記録へ結び付け、認証済み権限が必要な経路だけ実証拠を確認する。`test-evaluation` の改善採否・受領も同じ境界で変更する。元実績を変更しない。
- 必須scopeの開始後除外は、元要求の保存を維持し、依頼者が明示した変更、対象scope・根拠・範囲・依存/副作用の影響を既存のQA要求・計画・質問回答またはworkflowの必要な記録に保持する。元依頼の完了と、変更後の依頼の完了を区別する。元要求を削除せず、縮小時は03の別workflow_refへ引き継ぐ。`_exclusion_confirmed` はFalseを維持する。03の実装に従い、通常の依頼範囲変更と厳密な正式品質保証scopeの除外を区別する。#40の必須要求・attempt/runの履歴は消さない。

## 実装6 結果不明からの再開

qa-workflowの既存state・成果物refを優先し、`artifact_graph.py` の `create_workflow_state` / `read_workflow_state` の旧JSON互換と既存SQLite state / baseline bindingを03の選択条件に従い必要時に利用する。通常の文書継続は保存済み正本と未解決質問で足りる場合stateを作らない。実副作用・共有writer・#40必須分析・formal WCAGなど独立した実証明が必要な場合は既存のstate保存境界を維持する。#40のhandoff intentは永続的な外部反映だけに使い、通常対話質問へ追加しない。実結果不明時のowner lookupと再試行は04。

再開時は、①現在依頼と保存済み要求・scope、②現行未解決Qと元定義・回答、③担当ownerの正式反映ref/revision（回答受領だけでは反映済みにしない）、④最も早い影響工程と保存・実行状態の順で照合する。成果物と質問記録から復元できない引継ぎだけ既存stateの unresolved/handoffs に保持する。部分保存や回答後中断では反映済みownerを再実行せず、未反映先だけ再開する。未保存・結果不明・現在採用不可を区別し、別sessionで復元不能ならその範囲を明示する。03の元要求と全体完了を保持する。

## 検証・完了条件

- 既存 `test_question_ids.py`、`test_project_context_ids.py`、`test_project_context_owner.py`、`test_pr24_artifact_store.py`、`test_pr24_git_artifact_store.py`、`test_feature_registry.py`、`test_cross_owner_feature_to_candidates.py`、`test_test_item_condition_analysis.py`、`test_f_owner_verifier_registration.py`、`test_owner_scope_resume.py`、`test_qa_workflow_baseline.py`、`test_workflow_runtime.py`、`test_context_workflow_state.py` とフォームのPython/Nodeテストを変更箇所に応じ個別実行する。
- AT-04/05/06/07/09/10/11/12/14/15/20/23/24/25。回答前中断、部分回答、古い回答、実行条件回答、承認済み意味の保全、通常保存の承認不要、明示gated、結果不明・部分保存、旧HTML復元を比較する。
- 通常利用で保存技術や不要な承認の質問が発生せず、指定・厳密な運用・外部認可は維持され、許可済み自動保存と別Agent再開が成立する。未承認の意味変更・偽の権限・未回収回答誤適用・開始時必須scopeの無断縮小が拒否されることを確認して完了。
