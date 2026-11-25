# QAワークフロー利用者マニュアル

[共通運用契約](qa-workflow-operating-contract.md)と[Skill別マトリクス](qa-workflow-artifact-matrix.md)の利用者向け入口。全Skillを毎回実行する必要はない。

## 初回だけ決めること

Agentへ対象製品、repo/branch、依頼目的、既存仕様・QA成果物の場所を伝える。既存Project Contextがあれば利用し、初回正式書込み前に不足項目・配置維持案を確認する。

<!-- dprint-ignore -->
| 項目 | 利用者の対応 | 再確認 |
| --- | --- | --- |
| 対象・情報源 | repo/branch、仕様書、デザイン、既存TC等の入口と優先順位 | 変更時 |
| QA目的 | 重要業務、対象範囲、品質目標、レベル/タイプ | 目的変更時 |
| 保存・編集 | 正本の場所、provider、編集可能範囲、承認policy | 変更時 |
| 進行 | continuous（既定）またはgated | 任意 |
| 実行環境 | URL、role、認証取得方法、データ準備、許可操作・上限・cleanup | 実行が必要な場合と条件変更時 |
| 継続QA | Regression方針、knowledge root、外部Issue先等 | 必要時 |

秘密情報の実値をProject Contextや回答フォームへ貼らない。保存先未設定でも独立読取分析は可能だが正式保存はできない。

## 依頼例

以下は自然言語の例でありCLIコマンドではない。

- 初回設計：「対象機能Aの仕様から詳細TCまで作成。既存Project Contextと成果物を優先しcontinuousで進めて。仕様ブロッカーは質問して。」
- 観点のみ：「既存TRを利用してTCNとCIを更新。ケース作成や実行は不要。」
- 変更影響：「PR #123の差分を現在の仕様とTCに照合し、影響scopeだけ再分析して。」
- 再開：「前回のworkflow refを再開して。未解決質問と最後に完了した工程から続けて。」
- E2E実行のみ：「既存Playwrightの対象testを合意済み環境で実行し、結果とcleanupを報告して。」
- 探索：「機能Aの失敗回復を30分のtimeboxで探索。許可済み操作だけ実施して。」
- 統合報告：「承認済み計画と今回のRunを集計し、終了基準・未実行・残存リスクを報告して。」

PRやrelease検知、定期起動は呼出し側の仕組みが必要。Skill自体は監視を開始しない。

## 質問に答える

AgentはQ ID、根拠、影響、未回答時の扱い、再開先を示す。複数質問のHTMLフォームが必要な場合は入力後にMarkdown出力をAgentへ返す。Markdownや対話で直接回答してもよい。

<!-- dprint-ignore -->
| 回答 | 例 | Agent側 |
| --- | --- | --- |
| 仕様更新 | Q-001：仕様書を改版した（参照、版） | SPECとして再分析 |
| 正式決定 | Q-002：正式挙動はAと決定する | DECへ正規化 |
| 暫定仮定 | Q-003：今回のscopeに限りAと仮定することを承認 | ASMへ正規化 |
| 保留 | Q-004：確認中、未確定 | ブロッカーなら該当scopeのみ停止 |

回答と承認は別。承認の真正性が必要な操作では案件の認証済み承認経路を利用する。

## 保存・承認・人間編集

正式保存時はAgentが提示する操作・scope・保存先branch・before revision・差分を確認し、必要な承認だけを明示する。Git既定方式では対話同意後に認証済みアカウントで通常pushし、activity APIのactor/before/afterと保存内容を確認する。push成功だけで承認済みとはならない。認証・provider不足ではblocked。

continuousでは各TR/TCN/TC工程ごとに進行指示を出す必要はない。gatedでは成果物確認後に修正または次工程への進行を指示する。進行指示は保存・副作用の包括許可ではない。

人間が編集する場合は、Agentに編集可能な正本参照・元revision・scope・作業用branch/copyを示させる。許可されたMarkdown等だけ編集し、差分と根拠を提出する。canonical root、MANIFEST、CHANGELOG、Machine Entity、標準heading/file名を直接変更しない。新規IDを手入力で確定させず、行削除だけで廃止にしない。ownerレビューと必要承認後に正式writerで反映。競合時は編集案を保全する。

## 中断・再開・結果確認

再開時は既存workflow refまたは成果物の場所を指定（Agentが一意に解決できる場合は不要）。入力revision同一なら完成済み成果物を再利用し、変更scopeだけ再実行する。外部操作結果不明時は元実行・保存結果・cleanup・claim/予約を確認するまで同じ操作を再実行しない。

報告で対象build・環境・母集団・実行済み/未実行・PASS/FAIL・判定不能・cleanup・残存risk・保存状態を確認する。

<!-- dprint-ignore -->
| 状態 | 利用者が確認すること |
| --- | --- |
| 完了 | 要求scopeと必要検証・cleanup・保存要求を充足。リリース承認とは別 |
| 部分完了 / blocked | 完了済み範囲、未完了理由、必要な回答・権限・再開先 |
| unverified / stale | owner verifier・currentness・保存/承認証拠不足。正式完了ではない |
| draft / 未保存 | 正本未更新。必要な保存先・承認を設定 |

必要時は権限者が欠陥候補のIssue操作、リスク受容、改善採用、引継ぎ受領、リリース判断を行う。現行の未接続provider・未登録owner等は[改善一覧](../reports/2026-11-25_qa-workflow-operating-improvements.md)と[PR #22の残存制約](../implementation/pr22/merge-decision-2026-11-14.md)を参照。
