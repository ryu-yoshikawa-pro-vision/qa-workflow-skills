# 計画成果物の形式・承認

## 位置付け

test-requirements-analysis、test-architecture-design、test-managementの保存・編集・承認・下流参照を01〜03と一体で改修する。既存canonical JSONを扱う各owner runtime、owner_verifiers.py、test-reportingの集計入力を利用する。

## 形式と必要な情報

指定・既存正本を優先し、未指定は人間向け通常Markdown、機械処理が主用途ならJSON。一つの正本とし、Markdownに専用JSON block、escape、固定列、全fieldの完全round-tripを要求しない。既存v1 JSONのschema・ID・履歴・過去承認を旧契約で読み取る。新規JSONは既存schemaを優先し必要な意味変更に限りowner固有の版を追加する。

<!-- dprint-ignore -->
| 担当 | 必要な意味情報 |
| --- | --- |
| QA要求 | QA目的、品質目標、対象期間・範囲、成功条件、要求ID・根拠、制約、未解決、承認・下流参照 |
| 方式 | 要求/対象別レベル・タイプ・方式・環境・データ・分担・制約、割当ID、選択理由、根拠、未解決、承認範囲、影響 |
| 計画 | 対象build・環境・期間、計画項目・担当・資源・順序、予定source/母集団、終了基準、実績取得、project risk、差異・是正処置、承認 |

Markdownは既存output-templateの自然な日本語見出し・表を用い、必要な根拠・ID・適用範囲を明示する。機械処理に必要な値だけ実正本から取得し既存validatorへ渡す。欠落・曖昧なら該当機械処理を未確定とし推測補完しない。通常文書の作成・編集は止めない。機械集計の計画母集団・実績snapshotは既存形式で保持し同一内容を恒久同期しない。

## 承認済み内容・候補・現在の採用

保存と承認は別。通常内容承認は実回答、対象、内容、適用範囲、必要な期限を記録する。正式決裁・リスク受容・操作認可が必要なら実権限を確認する。保存やhashを承認としない。

承認対象は要求の目的・scope・成功条件・根拠、方式の割当・選択理由・共有制約と根拠、計画の対象・予定母集団・基準・計画項目・リスク対応方針等の実際の意味。表示変更、実績追記、別候補だけで承認を失効させない。方式のassignment_ids単位の部分承認を維持し、無関係な割当を変更しても失効させず、共有制約・根拠の変更が及ぶ割当は再評価する。既存content_fingerprintの意味を無断変更しない。

必要な承認時の内容は既存Git履歴、正式決定・回答、当時の必要な版で保持する。全履歴・固定SHA snapshot directoryを要求しない。現在草案、過去の承認済み内容、下流が現在使える内容を区別し、承認された範囲だけ採用する。必要な旧版取得不能・根拠失効なら該当採用のみ保留し編集原文を残す。無断復元・上書き・全面再承認なし。

## 既存機械処理との接続

qa_requirement_runtime.py、architecture_runtime.py、management_runtime.pyのvalidate/readback/impact/completion_check、managementのbuild_snapshot、owner_verifiers._stored_owner_artifact/_verify_requirements/_verify_architecture/_verify_management、reporting_runtimeの計画参照を照合する。JSONは既存機械検証を使用。Markdownは実根拠・承認・意味項目を担当Skillが確認し、機械集計・構造検証が必要な範囲だけ正規化入力にする。自己申告で機械処理を代替しない。

sourceの実revision変更を検知し、利用した意味・承認・適用条件の変化を担当ownerで判断する。旧JSONの数値revision・保存bytes hash・意味fingerprintを区別し、通常保存にprovider revisionを新設しない。既存validatorの制限・必要な下流検証を維持する。取得不能な機械入力は局所的に不足を示す。

## レベル選択

architectureの既存level_priority行に specialist_levels（既存level enumの集合）、specialist_reason（文字列またはnull）を追加する。assignmentsには selection_reason（文字列またはnull）を追加し、selection_basisとdecisionに「QA専門判断」を許容する。明示/承認済みが両方存在して異なる場合は既存の未確定・競合解決を維持する。それ以外は explicit_levels > approved_levels > 根拠あるspecialist_levels > default_levels。選ばれなかった集合を削除しない。specialist_levelsが空ならspecialist_reasonはnull、選択時は理由と実basis_source_idsを必須とし、source取得・QA要求の必要承認を確認する。割当集合が選択集合と一致し各assignmentのbasisがdecisionと一致することを_validate_prioritiesで検査する。selection_reasonはQA専門判断時必須、他はnull可。既定外を選んだことだけで_check_approvalを要求しない。実際に正式な承認済み方式を変える、組織決裁/対象外/リスク受容を要する時は旧承認範囲と新しい判断を照合する。旧v1のlevel enum・既定比較・承認は旧契約で検証する。必要な意味変更に限りowner固有の版を追加する。API等のenumを無断改名せず、レベル・タイプ・方式の区別を05と照合する。

## 検証

既存3 owner verifier、cross-owner reporting、owner registry、runtime portability、依存/currentnessテストを利用する。通常Markdown編集、指定JSON・旧v1読取/更新、必要機械入力の欠落・曖昧さ・不正型、計画母集団・終了基準、部分承認・別割当・共有制約、表示変更と意味不変、旧承認版取得不能、草案と現在採用、権限・根拠失効、必要な過去版、保存失敗を対比する。全形式round-trip・共通parserの実装を受入条件にしない。01/02/05のATで実保存・編集・既存JSON利用を確認する。
