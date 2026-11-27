# 計画成果物の形式・承認の詳細契約

## 位置付け

[01](2026-11-27_111830_qa-operating-improvements_01_artifacts-and-context.md)の実装4、[02](2026-11-27_111830_qa-operating-improvements_02_save-questions-approval.md)の承認、[05](2026-11-27_111830_qa-operating-improvements_05_qa-judgment-and-validation.md)の方式選択を具体化する。独立した追加工程ではない。対象は既存 qa_requirement_runtime.py、architecture_runtime.py、management_runtime.py、owner_verifiers.py と実際の読取・引継ぎ・報告・fixture。新規汎用parser、専用保存基盤、別の中央承認台帳を作らない。

## 形式と版

既存v1のSCHEMA、exact-key検証、canonical JSONの読取・過去承認・歴史的fingerprintを維持する。v2の意味objectのschema値は test-requirements-analysis-v2、test-architecture-v2、test-management-plan-v2。Markdownが既定、利用者指定のJSONは同じv2意味objectをcanonical JSONで保存する。形式判別はファイル内容（厳密JSONのschema、またはMarkdown内の下記blockのschema）で行い、拡張子だけで判断しない。v1 JSONをv2として扱わない。

Markdownでは人間が編集する各項目を日本語見出し・表へ配置し、機械専用部分を末尾の一つの既存型JSON fenced blockに置く。区切りは行頭の `<!-- planning-artifact:start -->` と `<!-- planning-artifact:end -->`、その間に一個の `json` fenced block。block内はschema・owner・artifact_ref・scopeおよび下表の機械項目。本文の編集可能な値を再掲しない。既存Machine Runtime blockとは独立しており全Skill共通schemaにはしない。見出しは下表の日本語名、表の列は下表のfield名を識別子とする。既存日本語templateの説明を残し、data-contractとtemplateで同じ列を使用する。表の列はここで指定する順序、行は既存IDで照合する。通常の説明文は保存してよいが正式意味objectに取り込む範囲は指定見出しと表だけ。根拠として使う判断は該当欄に記載する。

単純な文字列は普通のMarkdown文字列とし、バックスラッシュは二重、縦棒はバックスラッシュでescape、改行は文字列 `\n` として記録する。escape解除は逆順の逐次走査（不明なescapeは拒否）。nullは空セル、空文字が許される型では `""`、真偽値は true/false、数値は既存型の10進表記。文字列としてそれらの値を保存する場合はJSONのquoted stringを用いる。配列や複合参照は原則、同じ見出しの子表または機械block内の行IDに結び付く機械項目へ配置する。配列要素に順序がある場合は既存順を保持、集合のみに既存canonical sortingを適用。既存v1の必須型・enum・上限・ID・参照検証を引き継ぐ。欠落/未知列・重複見出し/ID/キー・曖昧な型・生成領域改変・参照欠落は該当成果物を不採用とし、原文を保全して修正候補を返す。旧正本を勝手に復元しない。

## フィールド配置

下表の「本文」は見出し名（括弧内は意味objectのキー）と表の列を指定する。機械blockの行補助情報は `row_metadata` の配下を本文表のキー→既存行ID→指定機械フィールドとする。複合identityの場合は既存canonical JSONで表現したidentityをkeyにする。本文IDと一対一に照合する。元の意味objectの全fieldが本文・機械block・既存証拠・導出値のどれかに一意に対応することをfixtureで確認する。旧schemaの追加必須fieldが実コードにある場合は黙って削除せず、対応表に従い同じ責務の配置へ含め、根拠を記録する。

<!-- dprint-ignore -->
| owner・本文見出し | 本文の列／項目 | 機械block側 |
| --- | --- | --- |
| QA要求：目的 (purpose) | target_period、qa_purpose, quality_goals, in_scope, out_of_scope, success_conditions, basis（項目名＋値の表。target_periodはトップレベル、qa_purposeは一行、他は同じ項目名の複数行。空のout_of_scopeは行なし） | schema, owner, artifact_ref, revision, scope, status, sources, approval, downstream, history |
| QA要求：要求 (requirements) | requirement_id, statement, requester, scope, priority, state, basis, open_item_id | source_ref, source_revision |
| QA要求：未解決 (open_items) | item_id, requirement_id, owner, state, resume_condition | impact_scopeは文字列配列、本文item_idに結び付ける |
| 方式：要求対応 (requirement_coverage) | qa_requirement_ref（既存のref文字列）, coverage, exclusion_reason | assignment_ids（行keyはqa_requirement_ref） |
| 方式：割当 (assignments) | assignment_id, target_ref, target_kind, level, test_type, method, verification_responsibility, environment, data, runner_tool, automation, measurement, selection_basis, selection_reason, disposition, readiness, exclusion_reason | qa_requirement_ref, basis_source_ids, source_ids, approval_id, downstream_refs |
| 方式：レベル選択 (level_priority) | target_ref, decision, conflict_resolution, specialist_reason。各level集合は子表「区分・level」（target_ref, 区分, level） | 実sourceとの参照は割当のbasis_source_ids |
| 方式：制約 (constraints) | constraint_id, target_ref, quality_attribute, measurement_method, environment_data, readiness, remaining_constraint | assignment_ids, threshold_source_id |
| 方式：未解決 (open_items) | open_item_id, subject_ref, owner, state, resume_condition, exclusion_reason | schema, owner, artifact_ref, scope, sources, change_impacts, history, approval_evidence（既存外部証拠refを保持） |
| 計画：対象 (target) | build, environment, period（項目名・値） | schema, owner, artifact_ref, revision, scope, plan_version, planned_sources, history, approval, monitoring, readbacks |
| 計画：予定母集団 (planned_populations) | population_id, source_id, query_range, execution_unit, target_build, environment, required | 実績はreadbacks（actual/zero_check含む） |
| 計画：作業 (plan_items) | plan_id, qa_ref, architecture_ref, level_type, suite_order, owner, effort, resource | source_ids。qa_ref/architecture_refは既存のref文字列を本文に置く |
| 計画：基準 (criteria) | criterion_id, kind, criterion, scope | evidence_ref, judgment（実績） |
| 計画：リスク (project_risks) | risk_id, description, scope, response, owner | evidence_ref, state, state_evidence_ref, approver（実績・受容証拠） |
| 計画：是正 (corrective_actions) | action_id, finding_ref, scope, action, owner, due | state, result_ref, approver |
| 計画：差異 (differences) | difference_id, scope, difference, response, owner | evidence_ref, state, state_evidence_ref, approver |

方式の content_fingerprint は既存canonical意味objectからv2の計算契約で導出し、本文と二重に管理しない。architectureの承認証拠が既存の別ownerに存在する場合はその実ref/revisionで取得し、同じ記録の独立正本を作らない。計画のreadbacks/monitoringは既存形式で実取得し、終了判断に必要な当時のsnapshotを保持する。実績を人間向けに表示する場合は生成領域として明示し、正本入力として再解析しない。方式のレベル集合・QA要求のpurpose等の実際の型は既存validatorを維持する。既存refは文字列のまま保持し、別の表示用文字列を独立した意味値にしない。表の行IDは実fieldの一意キー（方式のrequirement_coverageはqa_requirement_ref、level_priorityはtarget_ref）を用いる。行順を保持する。列は上表に記載のfield名をそのままheaderとする。日本語の見出しは上表の「：」以降の名称を使用する。表示名の別名対応や任意のMarkdown表の解析は追加しない。方式の子表「レベル集合」の区分は explicit_levels / approved_levels / specialist_levels / default_levels / levels のいずれか。空集合は当該区分の行なし。該当ownerで適用されないrow_metadataキーは作らない。JSON指定時はrow_metadataへ分離せず既存packetの行objectへ戻す。

### 記載例（各ownerの本文抜粋）

以下は構造の例であり実案件の根拠・承認証拠ではない。省略した必須欄は実際のv2 fixtureで補い、既存v1 fixtureと同じ意味にしてround-tripを検証する。

QA要求:

```markdown
## 要求

| requirement_id | statement                  | requester | scope    | priority | state | basis    | open_item_id |
| -------------- | -------------------------- | --------- | -------- | -------- | ----- | -------- | ------------ |
| QAR-001        | 有効な権限だけで更新できる | 依頼者    | 商品更新 | 高       | 提案  | 対象仕様 | Q-001        |
```

方式:

```markdown
## レベル選択

| target_ref | decision   | conflict_resolution | specialist_reason               |
| ---------- | ---------- | ------------------- | ------------------------------- |
| QAR-001    | QA専門判断 |                     | 権限制約はAPIから独立確認できる |

### レベル集合

| target_ref | 区分              | level    |
| ---------- | ----------------- | -------- |
| QAR-001    | specialist_levels | API      |
| QAR-001    | levels            | API      |
| QAR-001    | default_levels    | システム |
```

計画:

```markdown
## 基準

| criterion_id | kind | criterion                                | scope    |
| ------------ | ---- | ---------------------------------------- | -------- |
| CRIT-001     | 終了 | 必須ケースの結果と未解決リスクを確認する | 商品更新 |
```

計画の機械blockの行補助例（説明用の抜粋）:

```json
{
  "schema": "test-management-plan-v2",
  "owner": "test-management",
  "row_metadata": {
    "criteria": { "CRIT-001": { "evidence_ref": null, "judgment": "未判定" } }
  }
}
```

## 承認対象と意味変化

保存内容hashは実UTF-8 bytesのSHA-256。保存revisionは既存保存手段の実版（必要なら既存exact-content token）を用い、意味objectのfingerprintと混同しない。承認対象は以下のprojectionを既存canonical JSONでhash化する。実際のowner・artifact_ref・scope、承認対象行ID、承認時revisionを必ず束縛する。承認record自身、history、表示、保存版、下流生成/集計だけの変化を除く。根拠が有効な同一意味と確認できないsource revision/hash変更は安全側で再評価する。

<!-- dprint-ignore -->
| owner | 承認対象のfield | 別途検証する実績・派生値 |
| --- | --- | --- |
| QA要求 | target_period、purpose全field、requirementsの全field（source_ref/revisionは実根拠と照合）、open_itemsの全field、sourcesの適用scope・取得条件・意味根拠 | status、approval、downstream、history。未解決から解決へは実回答・正式反映を照合 |
| 方式 | requirement_coverage全field、assignmentsのうち approval_id/downstream_refsを除く全field、level_priority全field（明示・承認済み・専門判断・既定・競合解決）、constraints/open_items全field、sourcesの適用scope・role・local_id・取得/承認状態・意味根拠 | approval_idと実approval evidence/assignment_idsの対応、downstream_refs、change_impacts、history。readinessの変化は該当制約/根拠を再確認 |
| 計画 | target、plan_version、planned_sourcesの意味根拠、planned_populations、plan_items全field、criteriaの criterion_id/kind/criterion/scope、project_risksの risk_id/description/scope/evidence_ref/response/owner、corrective_actionsの action_id/finding_ref/scope/action/owner/due、differencesの difference_id/scope/difference/evidence_ref/response/owner | readbacks、monitoring、criteriaのevidence_ref/judgment、risk/differenceのstate/state_evidence_ref/approver、actionのstate/result_ref/approver。実績・リスク受容・是正・終了判断は個別の実根拠と必要承認で検証 |

方式の既存assignment_ids承認範囲は維持する。v2承認は対象projection hashと承認時の保存revision、evidence_ref、approver、role、適用範囲・必要な期限を実記録で保持する。依頼者の通常内容承認は実回答に結び付ける。厳密な決裁・リスク受容の必要認可は既存ownerで確認し、hash一致を権限証明にしない。sourceの同一意味が確認できる場合だけ旧根拠の意味を採用し、取得不能/承認失効を同じ意味に丸めない。方式は実際に承認されたassignment集合を照合し、他割当の承認を流用しない。

## 承認済み内容の保全と現在の通常保存

- 初回正式承認を採用する前に、承認対象の当時の完全な内容が実既存履歴から再取得可能か確認する。履歴のない通常ファイルは、承認対象として提示した原文（承認record追加前の内容で、承認projectionが正式採用内容と同一であることを確認）を既存owner領域の履歴（既存履歴がなければ正本と同じdirectoryの .history/<論理ID>/<保存SHA256>.<元拡張子>）へimmutable保存し読戻す。承認recordにそのrefと保存hashを記録する。snapshot自身にそのsnapshotのhash/refを埋め込んで自己参照させない。v2の既存承認recordに content_fingerprint（意味projection SHA-256、方式では既存field）、approved_content_ref、approved_content_sha256 を追加する。既存revisionは当時の実版として維持する。approval_id/assignment_idsは方式の既存承認証拠契約、stateとexpiry_conditionは既存ownerの条件を使う。旧recordと混在させない。既存Git/保存先履歴で同等に取得できれば複製しない。全編集履歴は作らない。
- 利用者が正本を直接編集しても、前回承認済み内容は当時の履歴から読める。意味変更は候補として扱い、新しい本文を正式採用する前に当時の内容、変更差分、現在の根拠・適用範囲を確認する。旧承認が現在も有効な範囲だけ当時の内容を利用する。元根拠が失効していれば旧承認も採用不可。元版取得不能なら正式採用・依存再利用を該当範囲で保留し、編集原文を残す。無断上書き/自動復元/全面再承認は行わない。
- 旧v1 JSONの当時の承認・history検証は維持する。旧JSONの通常保存・草案・進行には02を適用する。既存v1を無断変換せず、旧形式で更新する場合はその旧schemaの意味・revision制約を守り、必要な内容承認だけ実回答で取得する。旧形式の改版でv2の表示不変承認・専門判断等の意味契約が必要な場合は、当該成果物のv2 JSON更新を必要な互換性確認と利用者の形式/運用指定の範囲で行う。既存ref・ID・過去版を維持し、旧形式厳守の指定があるなら旧形式のまま成立する手段を使う。成立しない具体的な意味条件のみ説明する。新規JSON指定はv2 JSONを使い、保存技術や追加認証を形式で強制しない。
- 各owner runtimeのvalidate/readback/impact/completion_checkとowner_verifiers._stored_owner_artifact、_verify_requirements/_verify_architecture/_verify_managementを形式別に接続する。実保存原文、readback、revision/hashを照合した後に意味objectで既存検証を行う。JSON再シリアライズ値をMarkdownの保存hashとしない。reporting_runtimeのplan revision/実際の計画ref・下流依存は、採用した意味と実保存版を区別し、再利用前にcurrentnessを確認する。既存16 MiB/8 MiB・64 KiB等の実搬送契約と単体利用を維持する。

## レベル選択のv2

architectureの既存level_priority行に specialist_levels（既存level enumの集合）、specialist_reason（文字列またはnull）を追加する。assignmentsには selection_reason（文字列またはnull）を追加し、selection_basisとdecisionに「QA専門判断」を許容する。明示/承認済みが両方存在して異なる場合は既存の未確定・競合解決を維持する。それ以外は explicit_levels > approved_levels > 根拠あるspecialist_levels > default_levels。選ばれなかった集合を削除しない。specialist_levelsが空ならspecialist_reasonはnull、選択時は理由と実basis_source_idsを必須とし、source取得・QA要求の必要承認を確認する。割当集合が選択集合と一致し各assignmentのbasisがdecisionと一致することを_validate_prioritiesで検査する。selection_reasonはQA専門判断時必須、他はnull可。既定外を選んだことだけで_check_approvalを要求しない。実際に正式な承認済み方式を変える、組織決裁/対象外/リスク受容を要する時は旧承認範囲と新しい判断を照合する。旧v1のlevel enum・既定比較・承認は旧契約で検証する。

## 検証

既存3 owner verifierテスト、cross-owner reporting、owner registry、runtime portability、依存/currentnessテストを利用する。全fieldのv1/v2意味等価、v2 JSON/Markdown round-trip、表の通常編集、escape/null/複合ref、重複・欠落・型エラー、機械block変更、旧形式の通常保存、承認されたassignment範囲、level_priorityの変更、基準文変更と実績更新、リスク対応方針と解決結果、表示変更と意味不変、元承認履歴欠落、過去版再取得、候補の不採用と正式採用、必要な権限・根拠の失効、旧JSONとの引継ぎ、部分保存と競合を対比する。実保存・人間編集も01/02/05のATに含め、固定fixtureだけで利用性を証明しない。
