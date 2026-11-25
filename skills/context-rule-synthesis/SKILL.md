---
name: context-rule-synthesis
description: 複数workflowのcontext-signal-batch、既存候補、仕様Authority、回答・調査・Knowledgeを横断して共通法則と差異条件を分析し、候補とcontext-synthesis-runの作成・更新・再評価・再開を行う。候補は仮説であり正式仕様・Product Risk・テスト期待結果の正本ではない。単一sourceから中立signalを抽出する場合はcontext-signal-auditへ渡す。
---

# Context Rule Synthesis

異なるworkflowで得た観察から再利用可能な仮説と差異条件をまとめ、必要な追加調査・質問・既存ownerへの局所handoffを管理します。候補はAuthorityではありません。候補の未解決自体はworkflow全体を失敗させませんが、必須分析、保存、認可、必要handoffの証明が欠ければscopeは未完了です。

## 実行手順

1. `references/guidance.md`と`references/data-contract.md`を読みます。`assets/candidate-example.json`と`assets/run-example.json`は構造例です。
2. 開始時の`workflow_ref`、対象ref/content hash、要求scope・観点・調査条件・環境、現行Authority・取得可否等から`operation_input`を固定し、`workflow_operation_id` / `run_identity`を再計算できる形で保持します。自己更新、後から追加した根拠、時刻、無関係なHEAD/tokenはidentityに混ぜません。
3. 実行環境が渡す指定root内のlistと軽量projectionから必要本文だけを選択取得します。scopeが異なるという理由だけで候補を落としません。機械tag不一致や一覧取得不能は無関係の証明ではありません。
4. snapshotへ検索root・条件・取得完全性・直接参照した全ref/revision/hash・Authority fingerprint・取得不能/除外範囲を記録します。取得不能を空検索と扱いません。
5. sourceの独立性、訂正batch、適用scopeを照合してから、共通則と差異条件、独立仮説、支持/反例/未観察/判定不能/対象外を区別します。反例原因を特定できなければ`unclassified`を保持します。
6. 有効SPEC/DEC/承認済みASM、回答、Knowledge、implementation evidenceと照合し、`references/guidance.md`のrouting表に従います。観察数、候補score、実装推論で有効仕様を上書きしません。
7. 全候補の予定payload・hash・base revision/hash・関連候補前提・書込metadataを含む`in_progress` runの保存を依頼し、信頼済み境界の独立readbackを確認します。read-only調査は予定保存前に実行できます。質問・外部課題・他owner成果物などの副作用前にはhandoff intentをpendingで保存します。
8. 条件付き保存、readback、既存ownerの冪等性は決定論的な保存/owner境界で確認します。競合後は再readbackと意味的重複確認が必要です。Skillは保存技術や認証方式を選びません。異なるrefへのCAS、事前検索、commit metadata、AIのreadback申告を重複防止や認証の証拠にしません。
9. 保存済み予定から再開し、既保存分を当時のrevision/readbackで照合します。予定・metadata・前提が変わるなら新operation idで再計画します。run完了後のcurrentness/adoptionは、履歴上の完了と分けて最新候補・Authorityから判定します。
10. すべての予定、readback、必要handoff、完全性を確認した後にrunを完了します。0件の場合も今回の検索を証明するrunを保存します。helper/provider/認可hostが未接続なら正式保存・完了はblockedのまま、独立して可能な読み取り・分析・owner調査は継続します。

## 判断境界

- SPEC/DEC/Authorityの正本は`spec-analysis`、Product Risk/正式重点は`test-analysis`、質問正本は`question-analysis`、QA knowledge正本は`qa-knowledge`、Finding/外部Issueは`defect-management`が担当します。
- 実装観察のみは`INFERENCE`として保持し、正式仕様・PASS/FAILへ昇格しません。未承認回答だけで候補を解決・却下しません。
- 同一観察の再取得、同じcomponent/document由来のsignal、訂正前後のsignalを独立根拠として重複計上しません。
- mergeが安全にできない場合、候補を無理に統合せず独立保持します。分割先へ正式根拠・解決結果を範囲再評価なしに継承しません。
- 信頼済みreadback証拠のないfixture成功を正式完了としません。実行環境の保存境界が未接続の場合、別の保存先へ切り替えません。

## リソース

- 検索、推論、Authority、routing、handoff、鮮度: `references/guidance.md`
- batch/candidate/run schema・identity・完了: `references/data-contract.md`
- 候補例: `assets/candidate-example.json`
- run例: `assets/run-example.json`
- 共通pure contract helper: `skills/project-context/scripts/context_artifacts.py`
- 単一sourceのsignal抽出: `skills/context-signal-audit/SKILL.md`
