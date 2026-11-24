---
name: e2e-test-selection
description: UIを通すE2E自動化の価値、候補範囲、選定理由を技術非依存で判断する。「どの業務経路・機能をE2E自動化するか」「E2E候補の選定・優先度」を求められたら、自分で答える前に必ずこのSkillを読み込む。再利用可能なcurrent選定結果がない場合に使用する。TCを直接選ぶ、既存E2Eを実行する、Playwright実装可否を調べる依頼では使用しない。
---

# E2E対象選定

## 実行契約

1. `references/guidance.md`を読み、選定範囲、再利用、停止条件に従います。
2. 自動化価値の判断だけを行います。locator、fixture、Playwright設定、実装可否、実装コスト、テスト実行を選定根拠にしません。
3. `test-analysis`のProduct Risk、`test-requirement-design`のTR、`test-condition-design`のTCN／CI、`test-case-design`のTCを作成・複製しません。既存refを入力として追跡します。
4. TCが直接指定された経路、明示的にTCを伴わないE2E候補経路、既存E2Eの実行だけの経路を区別します。後二者をTCがあると偽装しません。
5. 候補集合を明示し、各候補を選定・不選定・保留・blockedのいずれかへ理由付きで閉じます。候補母集団、source currentness、根拠が不完全なら完成扱いしません。
6. 既存結果を改訂する場合はselection IDを保ち、revisionを増やし、現在の`change_reason`とrevision 1から直前revisionまでの全snapshotを残します。各snapshotはcandidate ID/key・decision・rationale、candidate別source refとそのrevision/currentness、scope・母集団状態、retirementを復元できる情報と、直前revisionの`revision_digest`を持ちます。digest欠落は推測再生成せず履歴をblockedにし、snapshotとdigestが不一致なら改変として拒否します。過去にretireしたcandidateと理由を後続履歴・現行結果から削除しません。candidate IDは同じcandidate_keyで維持し、IDを再利用しません。
7. 最終成果物は`assets/output-template.md`に従い、必要なら`selection_contract.py`でJSON契約を検証します。現在のsource revisionは呼出し側が`impact`へ渡す申告で、契約検証は現在revisionを取得しません。現在revisionを渡せない場合、または実保存先readbackを確認できない場合は、記録上のcurrentnessを実証済みと扱いません。

## インターフェース

- **入力**: 自動化目的、対象範囲、現在有効な仕様／業務根拠、feature/item/condition/Authority等のsource refとrevision、既存選定結果と履歴（ある場合）。
- **処理**: 候補ごとにUIを通したシステムレベル検証の価値、主要業務経路、反復確認価値、既存のより適切なテスト経路との重複を技術非依存で評価します。
- **出力**: selection ID・revision、現在revisionの`current_revision_digest`、対象scope、source refs、候補集合、各decisionと理由、未解決候補、履歴、停止・再開条件。

## ルーティング

- TCを直接指定: そのTCから既存E2E設計／実行経路へ進み、対象選定を再実行しません。
- TCを伴わずE2E自動化候補を明示: 必要な価値判断だけ選定します。
- 既存E2Eの実行だけ: 選定を作らず既存実行経路へ進みます。
- 選定が必要でcurrentな再利用結果がない: 本Skillを実行します。
- Playwrightや別技術の実装可否: `e2e-test-inspection`へ渡します。
- 新しいinspection事実で自動化価値が変わる: 影響候補だけ再選定します。

## 決定論的runtime dispatch

`scripts/selection_contract.py`はPython 3.11標準ライブラリのみを使用し、最大2 MiBのUTF-8 JSON objectを1つ受けてstdoutへ最大16 MiBのJSON envelopeを1つ返します。1文字列は64 KiB、JSON number token／展開値は4096桁、nesting depthは64までです。duplicate key、上限超過、非有限数、不正UTF-8、unpaired surrogateを構造化エラーで拒否します。検証済み候補・source revision・decision・履歴を`payload.selection_record`に保持し、現在revisionの`current_revision_digest`を返します。各過去snapshotは直前のruntime出力から得た`revision_digest`を必要とします。旧history rowは読めますが、decision・rationale・source snapshotまたはdigestを復元できないrowを含む選定は`blocked`とし、推測でsnapshotを補いません。revision digestはrecord内容の整合性値で、作成者や保存先の真正性は証明しません。契約検証は純粋関数で、外部保存、provider選択、approval、CAS、readbackを仮定しません。現在のsource revisionは、`{"operation":"impact","input":<保存selection>,"current_source_revisions":{"<ref>":"<revision>"}}`の`impact`で比較します。保存source refごとに現在revisionとref・revisionの完全一致で判定し、変更は`stale`、mapに無いrefは`unknown`（fail-closed）、全て一致は`current`です。保存側の`currentness`自己申告は判定に使わず、依存candidateを`impacted_candidate_ids`、他を`unaffected_candidate_ids`へ分けます。保存本文は変更しません。`impact`が判定するのは呼出し側が渡した現在revisionだけで、providerから独立取得した証拠ではありません。共有workflow runtimeへの登録（`qa-workflow`の`_verify_selection`が`current`以外を不可とします）と保存先Machine Entityの読戻し確認はA ownerとの受渡し対象です。

## リソース

- 判断基準: `references/guidance.md`
- 出力形式: `assets/output-template.md`
- JSON契約: `scripts/selection_contract.py`
