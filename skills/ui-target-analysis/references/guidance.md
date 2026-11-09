# UI分析と責務境界

## 所有する情報

`ui-target-analysis`はUI構造、操作、画面表示状態、フォーカス・操作可能性、ナビゲーション、UIの変更履歴を所有します。現行`ui-target-v1`では主に次の箇所へ反映します。

- `00_scope_and_context.md`の`分析対象機能scope一覧`にあるUI操作判定
- `01_ui_structure_and_navigation.md`の`UI構造一覧`と`Navigation / Entry / Exit`
- `02_behavior_and_business_rules.md`の`UI操作一覧`

US、UC、Behavior、AC、業務ルール、仕様根拠、UNKNOWNの解決は`spec-analysis`のowner領域です。`03_fields_and_validation.md`、`04_flows_and_data.md`、`05_notifications_and_external_interactions.md`の期待値や業務意味も`spec-analysis`に戻します。UI側から必要な正本IDを参照できますが、対象行の内容を更新しません。

## Authorityと観測事実

- UI構造の存在・名称・到達方法は、使用したcurrent source refと取得revisionに紐付けます。
- screenshot、Figma、live UI、repository実装、usability finding、WCAG結果は、Project ContextでAuthorityと指定されない限り、期待仕様の正本ではありません。
- 画面上の観測結果と期待挙動が異なる場合、観測事実をUI packageへ残し、期待挙動の変更はAuthority owner・承認者へ戻します。
- 現在の`ui-target-v1`ではUI行のsource provenanceを独立列として保持しません。既存のAuthority参照をUI source refの代用にせず、source refは編集／レビューhandoff証拠に保持します。共有runtimeが証拠を保存できない場合は正式な外部接続をblockedにします。

## 分析手順

1. Project Contextから対象repository／source、revision、機能ID、scope、保存先、正本owner、承認済み編集範囲を確認します。
2. 現行packageは`ui_target_package.py inspect`で読取り、有効な`update_snapshot`とpackage versionを保持します。旧形式は`spec-analysis`へ渡して既存migration contractを使います。
3. UI sourceの確認範囲と未確認領域を記録し、PAGE、STATE、VIEW、STEP、MODAL、BROWSER-DIALOG、PANEL、POPOVER、GLOBAL UI、EXTERNAL、SHARED PAGEを意味に応じて分類します。分類不能な構造に仮IDを付けません。
4. 操作、対象構造、関係するScope、Authority refを確認します。構造が同じであることだけからUCや期待結果を推測しません。
5. 機能別参照が必要なら`feature-analysis`の実artifact ref／revisionと明示された`feature_id → scope_id`だけを使い、`human_editing.py feature-index`でcurrent packageから正本file・line・stable IDを導出します。
6. 変更後は`inspect`、`validate`、必要な`build-machine-evidence`を実行し、package version、Manifest、stable ID、参照、readiness、影響範囲を確認します。

## package互換性

`ui-target-v1`は単一package・単一writerの互換形式です。新Skillの論理owner導入だけを理由に、標準file、heading、table、prefix、stable ID、version、Manifest、CHANGELOG、Machine Entityを変更・分割しません。Authority/AC/UNKNOWNは`spec-analysis`をownerとし、UI Skillは参照・読取を続けます。旧`spec-analysis` UI modeは既存package・legacy・既存consumerの互換readerとして維持します。

既存packageが利用可能な場合、新packageや別のcanonical rootを作らず、ownerが必要なUI rowのみを更新します。実画面操作の確認は`test-target-inspection`、使いやすさは`usability-evaluation`／`usability-inspection`、正式WCAG評価は`wcag-conformance-evaluation`へ委譲します。
