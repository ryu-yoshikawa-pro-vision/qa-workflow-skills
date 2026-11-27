# 保存・質問・承認・継続の改修

## 目的・対象範囲

OPS-01〜04・06・18。成果物作成は必要な時点で保存し、通常保存や工程進行を都度承認で止めない。未確定の仕様・リスク受容・必要な操作許可を区別し、回答後は影響範囲だけ再開する。01の配置・正本形式を前提とする。共有資源の実操作は04、完了判定は03。

## 現状・維持する契約

- `question-analysis` の `references/guidance.md` L60〜99は期待挙動のSPEC/DEC/ASMへの正規化を中心とする。Q ID・UNKNOWN・分類・再開先は既存 `question_ids.py` と出力templateを維持する。
- `agent-answer-form` の `scripts/build_form.py`、`references/json-format.md` はフォームID・質問ID・定義hashで回答を分離する。旧HTMLによる未回収回答の復元、v3/v4等の互換、外部通信なしを維持する。
- `qa-workflow/references/guidance.md` の進行モードは利用者明示 > Context Section 10 > continuous。`test-item-analysis` / `test-condition-analysis` のSave and resumeはprovider CAS・approval policy・独立readbackを要求する。計画3 Skillは保存・承認provider未接続を草案とする。`test-evaluation` は改善採用・受領の認証済み確認を要求する。
- 現行のworkflow_runtime.pyの_exclusion_confirmed()は常にFalseで、excluded_by_approvalは未確定。#40の指定root・create/read/list/history・条件付き更新・外部handoff結果不明時の停止は現行契約であり、通常保存・要求管理は02・03で置換する。外部副作用の結果不明時の確認は維持する。

## 実装1 保存対象と時点

各ownerのSKILL.mdと必要なreferenceで、成果物作成依頼（分析・設計・更新・実行・計画・知識の作成）と、単発の相談・読取・レビュー・調査を区別する。前者は明示の非保存指定がなければ必要成果物を自動保存する。後者は原則対話回答。継続利用・保存依頼がある場合に加え、活動中に再利用価値のある知識（適用範囲・根拠のある判断、観察、反例、教訓）を発見した場合は、許可済み保存先で既存owner/Knowledgeまたは必要時A/Bへ必要分だけ保存する。単発成果物全文・raw・個人情報を便宜的に保存しない。非保存指定を優先し、任意の知識保存先が不明なら通常回答を止めず、保存先の設定を強制しない。任意rawは保存対象の既定に含めない。

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

01の指定解決と既存OS/sandbox権限で通常Markdown・JSONを作成・更新し、保存結果を確認する。既存正本を先に探し、更新前の対象・差分を確認する。機械writerの中断対策は既存の一時ファイル・置換処理を利用する。通常保存にCAS、専用認証callback、全revision、receiptを要求しない。単純なファイル置換を共有CASと呼ばない。

<!-- dprint-ignore -->
| 対象 | 改修内容 | 維持する保証 |
| --- | --- | --- |
| `project_context.py`、`artifact_store.py`、`git_artifact_store.py` | prepare系の意味検証結果を通常Markdownへ保存。persist_prepared、store型import、operation_id/approval_ref/approval_revision必須、read_revision/write依存・呼出しを除去し、不要になる専用store 2ファイル・設定・テストを削除 | DEC/ASM、既存文書・ID、正式な意味変更、必要参照、許可範囲 |
| `feature_registry.py` のpersist_snapshot/analyze/candidate_handoff | 通常JSON保存。store型・read_revision/write・保存承認引数・receiptを除去し、実ファイルの前回snapshotと照合。_authorize_reclassificationsを実際の正式再分類の判断・根拠へ接続。実Git inventory・reconcile_git_coverage・source照合を維持 | FEAT ID、根拠、母集団、正式再分類・retire |
| `item_candidates.py`、`condition_candidates.py`、双方のcandidate_support.py | materialize/_check_revision_gateから不要なprovider revision・保存権限・承認入力を除き、生成・検証と保存を分離。validate_readbackは必要な正本検証に限定 | ITEM/COND ID、親子、廃止・根拠、B snapshotの完全性 |
| 計画3 Skillのruntimeとowner verifier | 06の通常Markdown/JSON、草案保存と正式採用を分離 | 計画母集団・依存・承認対象・集計 |
| `selection_contract.py` | 全revision snapshot必須を廃止。現在の候補ID/key、既存retired ID/keyと理由を保持し、前回との照合でID再利用・key変更・理由消失を防ぐ。実装/実行が参照する版だけ既存履歴または必要な保存版で保全。旧JSON fixtureは旧契約で検証し、新しい意味契約は必要なowner固有版で区別 | 選定・実装・実行の追跡、currentness |
| `knowledge_runtime.py` | update_entry/plan_update/plan_replacementの通常CAS callback必須を撤廃。同一entryを更新し、統合・置換中断時は実際の関係entryを確認 | 適用条件・根拠・訂正・既存ref・currentness |
| regression/exploration/reporting/defect/evaluationの各runtime | Run/Activity/Session・報告・欠陥候補・改善記録を既存形式で保存。通常改善採否・受領は実際の依頼者/受領者の確認を使い、専用認証サービスを必須にしない | 実行結果・報告、母集団、採用/適用/効果測定、外部操作認可 |
| `ui_target_package.py`、`human_editing.py` | package固有writerと生成領域保護を維持し、不要なContext・provider条件を外す | 関連ファイル整合、安定ID、生成領域、必要な回復 |
| `context_artifact_store.py`、`context_artifacts.py`、`context_workflow_state.py` | 3 kindの通常JSON保存・取得。全更新履歴、複数ファイルlock、related_preconditions、receipt相当の重複情報を削減。03の要求・分析・再開を保持 | 不変観察batch、訂正、候補根拠、元要求、未完了、実handoff結果 |

既存規則を優先する。通常の同一正本は担当writerを一つにし、並行作業の出力先を分離して必要な結果を統合する。実際に共有する正本のみ既存Gitや運用による競合回避を行う。外部副作用・権限外操作は04の実認可を守る。保存・内容承認・現在性を別に判定する。保存結果不明は実保存先を読み、盲目的に再書込みしない。部分保存は実成果物と未保存依存を特定し、該当下流のみ採用保留。無断rollback・別正本化をしない。読取不能を不存在としない。

通常保存のrevision・hash・readback・receiptは一律必須にしない。製品/source版、機械生成・Entity依存のfingerprint、実行証拠、必要な正式結果の照合は別責務として維持する。表にないSkillは01・05に従う。専用保存API、共通認証host、JSON DB、全成果物CAS・全履歴・receiptは作らない。不要になった入口・契約・設定・テストを除く。

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

- qa-workflowのSKILL.md、guidance、Context Section 10、routing fixtureを同期する。既定continuous。現在の明示指定または既存の有効な利用者承認済みgated規則は指定境界で尊重する。旧実装の既定値や根拠不明の設定だけで停止しない。gatedと仕様承認を区別する。
- 関連ownerの内容承認recordは対象・承認内容・必要なscope・根拠/変更影響を保持する。複数判断は関連性があり一緒に回答できる場合だけ集約し、部分承認・保留・拒否を正しく扱う。承認に影響する意味・適用範囲・期限の変更は再判断する。候補の自動保存や意味不変の表示編集のみで承認を取り消さない。
- `test-requirements-analysis`、`test-architecture-design`、`test-management` の既存validatorは承認recordと意味/対象の束縛を検証するが、利用者本人性や組織認可を証明するものではない。通常の内容承認では実際の利用者回答を正本または既存質問回答記録へ結び付け、認証済み権限が必要な経路だけ実証拠を確認する。`test-evaluation` の改善採否・受領も同じ境界で変更する。元実績を変更しない。
- 必須scopeの開始後除外は元依頼と実際の変更指示・対象・理由・影響・必要権限を成果物または必要な再開記録に残す。03の現在の要求集合へ反映し、元依頼・過去完了・未解決副作用を消さない。正式品質保証scopeの縮小は必要な承認を守る。SQLite履歴・新v3を要求しない。旧v1/v2は当時の契約で読む。

旧JSONの読取時は当時の版・承認証拠を検証する。現在の通常保存、内容承認、進行は01・06の新運用を適用し、JSON形式だけを理由に専用認証・保存承認を要求しない。承認対象の変更を伴う場合は旧承認を改竄せず候補として保存し、06の必要な履歴・新承認を扱う。

## 実装6 結果不明からの再開

成果物refと質問回答を優先し、復元できない情報だけ通常JSONまたはMarkdownに保持する。機械baseline、A/B必須分析、正式WCAGも03・04の必要成果物を用い、SQLiteを開始・再開条件にしない。外部反映の結果不明時だけ必要なhandoff記録を用い、通常対話質問にclaimを追加しない。

再開時は、①現在依頼と保存済み要求・scope、②現行未解決Qと元定義・回答、③担当ownerの正式反映ref/revision（回答受領だけでは反映済みにしない）、④最も早い影響工程と保存・実行状態の順で照合する。成果物と質問記録から復元できない引継ぎだけ既存stateの unresolved/handoffs に保持する。部分保存や回答後中断では反映済みownerを再実行せず、未反映先だけ再開する。未保存・結果不明・現在採用不可を区別し、別sessionで復元不能ならその範囲を明示する。03の元要求と全体完了を保持する。

## 検証・完了条件

- 既存 `test_question_ids.py`、`test_project_context_ids.py`、`test_project_context_owner.py`、`test_feature_registry.py`、`test_cross_owner_feature_to_candidates.py`、`test_test_item_condition_analysis.py`、`test_f_owner_verifier_registration.py`、`test_owner_scope_resume.py`、`test_qa_workflow_baseline.py`、`test_workflow_runtime.py`、`test_context_workflow_state.py` とフォームのPython/Nodeテストを変更箇所に応じ個別実行する。
- AT-04/05/06/07/09/10/11/12/14/15/20/23/24/25。回答前中断、部分回答、古い回答、実行条件回答、承認済み意味の保全、通常保存の承認不要、明示gated、結果不明・部分保存、旧HTML復元を比較する。
- 通常利用で保存技術や不要な承認の質問が発生せず、指定・厳密な運用・外部認可は維持され、許可済み自動保存と別Agent再開が成立する。未承認の意味変更・偽の権限・未回収回答誤適用・開始時必須scopeの無断縮小が拒否されることを確認して完了。
