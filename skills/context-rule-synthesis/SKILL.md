---
name: context-rule-synthesis
description: 複数workflowのcontext-signal-batch、既存候補、仕様Authority、回答・調査・Knowledgeを横断して共通法則と差異条件を分析し、候補とcontext-synthesis-runの作成・更新・再評価・再開を行う。候補は仮説であり正式仕様・Product Risk・テスト期待結果の正本ではない。単一sourceから中立signalを抽出する場合はcontext-signal-auditへ渡す。
---

# Context Rule Synthesis

異なるworkflowで得た観察から再利用可能な仮説と差異条件をまとめ、必要な追加調査・質問・既存ownerへの局所handoffを管理します。候補はAuthorityではありません。候補の未解決自体はworkflow全体を失敗させませんが、必須分析、保存、認可、必要handoffの証明が欠ければscopeは未完了です。

## 実行手順

1. `references/guidance.md`、`references/data-contract.md`、`assets/output-template.md`を読みます。`assets/candidate-example.json`と`assets/run-example.json`は構造例です。
2. 開始時の`workflow_ref`、対象ref/content hash、要求scope・観点・調査条件・環境、現行Authority・取得可否等から`operation_input`を固定し、`workflow_operation_id` / `run_identity`を再計算できる形で保持します。自己更新、後から追加した根拠、時刻、無関係なHEAD/tokenはidentityに混ぜません。
3. 実行環境が渡す指定root内のlistと軽量projectionから必要本文だけを選択取得します。scopeが異なるという理由だけで候補を落としません。機械tag不一致や一覧取得不能は無関係の証明ではありません。
4. snapshotへ検索root・条件・取得完全性・直接参照した全ref/revision/hash・Authority fingerprint・取得不能/除外範囲を記録します。取得不能を空検索と扱いません。
5. sourceの独立性、訂正batch、適用scopeを照合してから、共通則と差異条件、独立仮説、支持/反例/未観察/判定不能/対象外を区別します。反例原因を特定できなければ`unclassified`を保持します。
6. 有効SPEC/DEC/承認済みASM、回答、Knowledge、implementation evidenceと照合し、`references/guidance.md`のrouting表に従います。観察数、候補score、実装推論で有効仕様を上書きしません。
7. 全候補の予定payload・hash・base revision/hash・関連候補前提・書込metadataを含む`in_progress` runを`context_artifact_store.py`で指定rootに保存し、返却readback後に同一revisionを独立readbackします。read-only調査は予定保存前に実行できます。質問・外部課題・他owner成果物などの副作用前にはhandoff intentをpendingで保存します。
8. candidate createはcreate-if-absent、更新は`expected_revision`と`expected_content_hash`を同じ保存要求で条件確認し、統合・分割等で依存する候補がある場合は各`candidate_ref`・`expected_revision`・`content_hash`を`related_preconditions`として同じ更新要求へ渡します。依存の前提が保存境界で変わっていたら当該操作を止めて再照合します。historyから更新前revisionも再読取します。許可済み通常保存に専用認証hostは必要ありません。共有更新・外部操作・正式仕様変更は既存ownerの認可・承認・履歴・独立readbackを維持します。異なるrefへのCAS、事前検索、commit metadata、AIのreadback申告を重複防止や認可の証拠にしません。
9. 保存済み予定から再開し、既保存分を当時のrevision/readbackで照合します。予定・metadata・前提が変わるなら新operation idで再計画します。run完了後のcurrentness/adoptionは、履歴上の完了と分けて最新候補・Authorityから判定します。
10. すべての予定、readback、必要handoff、完全性を確認した後にrunを完了します。0件の場合も今回の検索を証明するrunを保存します。必須要求は最初のA/B実行前に`context_workflow_state.py build-request-scope`で開始時の全operation input・analysis scope・target batch refsからB要求契約と仮scopeを作り、A/B要求すべてと`context_request_contracts`をqa-workflowの既存stateへ登録します。開始時に未確定なA生成batchは、同一workflow・同一rootのrequired A attemptで保存されref/revision/hashを独立readbackできた後、その正確なsource/target refとしてB contractへ具体化できます。他の要求を実行済みでもstart contractと元`request_scope`を維持して再登録します。既存のsource、operation type、investigation conditions、analysis aspect/scope、environment/version conditionsを変えず、source置換やscope縮小、条件変更、確定済みversionの上書きは拒否します。後続runは各時点のcontract input/target refsをsnapshotに保持し、split runでの部分scopeは最終gateが全要求のsource×scopeとtarget batch coverageを覆う場合だけ完了として扱います。各run保存要求にはそのrunが対応する元`request_scope`を渡し、同一の開始要求を分割するB run groupには安定したrequest identityと各runの開始時input/target snapshotを保持します。
    - B scopeの`normalized_input.context_workflow_state`には呼出し側の`artifact_root`・`workflow_state_root`、元`request_scope(s)`、分割前の元`requested_operation_input`・`requested_scope`を渡します。Bのrun ref/revisionは`context_workflow_state.py`からqa-workflowの既存stateへ保存し、stateに同じ成果物rootのbindingを保持します。
    - A scopeも元`request_scope(s)`を保持し、attemptのbatch ref/revision/hashと担当rangeを保存成果物・owner verifier・実readbackへ結びます。同一最終scopeを複数元要求で共有する場合も各request identityをstateに残し、別batch/runや補助実行を要求充足に転用しません。
    - 途中runは未確定の`confirmed_result`をreadbackせずに登録でき、再開時は保存済みrunと開始時inputをexact revisionで読み直します。仮targetから実refへ具体化した後、qa-workflow最終runtimeには永続stateの対応で裏付けられた実scope集合を`requested_scopes`と`workflow_scopes`へ渡し、独立fieldの`context_workflow_state_root`も指定します。これにより最終runtimeからA/Bの要求・scope・nested state参照が全て欠落しても元要求を検出します。`completion-check-workflow`はA/B開始要求の全件、実scope、owner verifier記録、全current runの完了、snapshot・batch・候補・handoff・開始sourceの必要readbackをまとめて再確認します。`returned`は返却結果のreadbackを必要としますが、handoff成立を意味しません。通常の許可済みroot保存に専用認証hostは要求しません。必要な共有認可・外部owner証拠が未確認の場合は該当scopeだけを未完了にし、独立して可能な読み取り・分析・owner調査は継続します。

## 判断境界

- SPEC/DEC/Authorityの正本は`spec-analysis`、Product Risk/正式重点は`test-analysis`、質問正本は`question-analysis`、QA knowledge正本は`qa-knowledge`、Finding/外部Issueは`defect-management`が担当します。
- 実装観察のみは`INFERENCE`として保持し、正式仕様・PASS/FAILへ昇格しません。未承認回答だけで候補を解決・却下しません。
- 同一観察の再取得、同じcomponent/document由来のsignal、訂正前後のsignalを独立根拠として重複計上しません。
- mergeが安全にできない場合、候補を無理に統合せず独立保持します。分割先へ正式根拠・解決結果を範囲再評価なしに継承しません。
- 信頼済みreadback証拠のないfixture成功を正式完了としません。許可rootへの通常保存は`context_artifact_store.py`で実行し、共有更新・外部操作・正式仕様変更は各ownerの既存認可境界へ渡します。

## リソース

- 検索、推論、Authority、routing、handoff、鮮度: `references/guidance.md`
- batch/candidate/run schema・identity・完了: `references/data-contract.md`
- 候補例: `assets/candidate-example.json`
- run例: `assets/run-example.json`
- 出力形式: `assets/output-template.md`
- 共通pure contract helper: `scripts/context_artifacts.py`
- 指定rootの保存・list/read/history: `scripts/context_artifact_store.py`
- qa-workflow stateの試行・run参照: `skills/qa-workflow/scripts/context_workflow_state.py`
- 単一sourceのsignal抽出: `skills/context-signal-audit/SKILL.md`
