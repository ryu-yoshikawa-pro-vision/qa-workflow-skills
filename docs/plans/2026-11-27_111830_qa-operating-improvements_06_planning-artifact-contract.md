# 計画成果物の形式・承認

## 位置付け

test-requirements-analysis、test-architecture-design、test-managementの保存・編集・承認・下流参照を01〜03と一体で改修する。既存canonical JSONを扱う各owner runtime、owner_verifiers.py、test-reportingの集計入力を利用する。

## 形式と必要な情報

指定・既存正本を優先する。未指定で既存機械検証・下流集計を必要とする依頼はJSONを正本、人間向け文書だけなら通常Markdownを正本とする。Markdownに専用JSON block、escape、固定列、全fieldの完全round-tripを要求しない。既存v1 JSONのschema・ID・必要な過去承認を旧契約で読む。新規JSONは既存schemaを優先し、意味変更に必要な場合だけowner固有版を追加する。

<!-- dprint-ignore -->
| 担当 | 必要な意味情報 |
| --- | --- |
| QA要求 | QA目的、品質目標、対象期間・範囲、成功条件、要求ID・根拠、制約、未解決、承認・下流参照 |
| 方式 | 要求/対象別レベル・タイプ・方式・環境・データ・分担・制約、割当ID、選択理由、根拠、未解決、承認範囲、影響 |
| 計画 | 対象build・環境・期間、計画項目・担当・資源・順序、予定source/母集団、終了基準、実績取得、project risk、差異・是正処置、承認 |

Markdownは既存output-templateの自然な見出し・表を用い、必要な根拠・ID・適用範囲を明示する。人間向け文書だけの作成・編集・完了にJSON固有のvalidate_readbackや機械完了を要求しない。Markdown指定または後続依頼で機械処理が必要になった場合は、担当Skillが実正本からその処理に必要な既存schemaの入力を組み立て、該当validator・集計を実行する。欠落・曖昧な値は推測補完せず該当処理だけ未確定にする。JSON入力を生成しても既存Markdown正本を自動昇格・削除・置換しない。入力の保存は実行・報告の再現や下流参照に必要な場合だけ行い、参照元Markdownと利用時点を対応付けた機械入力snapshotとして扱う。保存先は実際に利用するRun・報告・機械処理の既存成果物領域とし、正本の既定pathとは区別する（例: 報告snapshot配下のplan-input.json）。参照元Markdownのrefと利用時点の版・機械入力refは既存の入力参照・依存記録等で対応付ける。厳密な既存schemaのJSONに未定義項目を加えない。機械入力は正本探索から除外し、別sessionでもMarkdownを正本として解決する。独立して更新する正本にせず、元の意味が変われば必要な入力を再生成・検証する。過去報告・実行が参照するsnapshotは上書きしない。正本形式の変更は利用者の指定に従う。恒久parser・二重正本・全項目同期は作らない。既存JSONの計画母集団・実績snapshotは維持する。

## 承認済み内容・候補・現在の採用

保存と承認は別。通常内容承認は実回答、対象、内容、適用範囲、必要な期限を記録する。正式決裁・リスク受容・操作認可が必要なら実権限を確認する。保存やhashを承認としない。

承認対象は要求の目的・scope・成功条件・根拠、方式の割当・選択理由・共有制約と根拠、計画の対象・母集団・基準・項目・リスク対応等の意味。architecture_runtime._check_approvalは現行でassignment_idsに加え成果物全体のcontent_fingerprint/expected_revisionを要求する。旧JSON証拠は旧契約で検証し、改修後は実際の回答・決定、対象割当ID、適用範囲と根拠に基づく承認を使う。無関係な別割当・表示・実績追記で失効させず、共有制約・根拠の変更が及ぶ範囲だけ再評価する。承認対象hashの別基盤を新設せず、既存content_fingerprintの意味も無断変更しない。

必要な承認時の内容は既存Git履歴、正式決定・回答、当時の必要な版で保持する。全履歴・固定SHA snapshot directoryを要求しない。現在草案、過去の承認済み内容、下流が現在使える内容を区別し、承認された範囲だけ採用する。必要な旧版取得不能・根拠失効なら該当採用のみ保留し編集原文を残す。無断復元・上書き・全面再承認なし。

## 既存機械処理との接続

qa_requirement_runtime.py、architecture_runtime.py、management_runtime.pyのvalidate/readback/impact/completion_check、managementのbuild_snapshot、owner_verifiers._stored_owner_artifact/_verify_requirements/_verify_architecture/_verify_management、reporting_runtime.build_snapshotのplan_ref/plan_revision/current_plan_revisionを照合する。JSONは実保存ファイルを読んで既存schemaの意味・必要構造検証を行い、provider証拠を捏造しない。必要に応じreadback契約から専用provider・保存承認を除く。Markdownの意味判断は担当Skillが行い、機械処理が必要な範囲だけ上記入力を作る。実際に使う計画の版・母集団を報告へ渡し、取得不能な値は未確定とする。

sourceの実revision変更を検知し、利用した意味・承認・適用条件の変化を担当ownerで判断する。旧JSONの数値revision・保存bytes hash・意味fingerprintを区別し、通常保存にprovider revisionを新設しない。既存validatorの制限・必要な下流検証を維持する。取得不能な機械入力は局所的に不足を示す。

## レベル選択

正式な機械処理用JSONでは、architectureの既存level_priority行に specialist_levels（既存level enumの集合）、specialist_reason（文字列またはnull）を追加する。assignmentsには selection_reason（文字列またはnull）を追加し、selection_basisとdecisionに「QA専門判断」を許容する。明示/承認済みが両方存在して異なる場合は既存の未確定・競合解決を維持する。それ以外は explicit_levels > approved_levels > 根拠あるspecialist_levels > default_levels。選ばれなかった集合を削除しない。specialist_levelsが空ならspecialist_reasonはnull、選択時は理由と実basis_source_idsを必須とし、source取得・QA要求の必要承認を確認する。割当集合が選択集合と一致し各assignmentのbasisがdecisionと一致することを_validate_prioritiesで検査する。selection_reasonはQA専門判断時必須、他はnull可。既定外を選んだことだけで_check_approvalを要求しない。実際に正式な承認済み方式を変える、組織決裁/対象外/リスク受容を要する時は旧承認範囲と新しい判断を照合する。旧v1のlevel enum・既定比較・承認は旧契約で検証する。必要な意味変更に限りowner固有の版を追加する。API等のenumを無断改名せず、レベル・タイプ・方式の区別を05と照合する。

通常のQA相談・初期調査・Markdown方式設計には、JSONのsource IDを必須としない。実際の仕様・コード・観測の参照と判断理由を示し、ID未発行を理由にシステムテストへ戻さない。根拠自体が不足する場合は暫定判断・未確定として区別する。後続の機械処理では実sourceを既存schemaで識別し、必要な根拠・承認を検証する。Contextや要求JSONをID取得だけの目的で作らない。

## 検証

既存3 owner verifier、cross-owner reporting、owner registry、runtime portability、依存/currentnessテストを利用する。通常Markdown編集、指定JSON・旧v1読取/更新、必要機械入力の欠落・曖昧さ・不正型、計画母集団・終了基準、部分承認・別割当・共有制約、表示変更と意味不変、旧承認版取得不能、草案と現在採用、権限・根拠失効、必要な過去版、保存失敗を対比する。全形式round-trip・共通parserの実装を受入条件にしない。01/02/05のATで実保存・編集・既存JSON利用を確認する。通常相談・MarkdownでID未発行の実根拠による専門判断、根拠自体の不足、後続の機械入力生成と正本の維持、必要snapshotの参照と再検証、機械JSONの不正・欠落source IDを対比する。 派生snapshotとMarkdownが共存する場合の正本探索、実際の重複正本、厳密な旧schemaへの未定義項目の混入、参照元と利用時点の照合、別sessionでの再開を確認する。
