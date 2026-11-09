# UI ownerの人間編集と正式取り込み

## 編集前

1. `project-context`の有効なQ06合意から正本root、owner、編集権限、対象file・scope、feature参照、保存先の条件付き更新と承認規則を取得します。
2. `ui_target_package.py inspect`で有効なcurrent packageと`update_snapshot`を取得し、package version、payload hash、Manifest hash、source／artifact ref・revisionを保持します。
3. 正本から分離した承認済みworktree／copyでMarkdownを直接編集します。canonical rootを編集せず、MANIFEST、生成README metadata、CHANGELOG、Machine Entities、標準heading、file名を編集しません。
4. 人間編集とレビュー承認を別の行為として扱い、レビュー記録・編集者・根拠refを既存の許可された証拠先で追跡します。secret、PII、cookie、tokenを新たな証拠に複製しません。

## 差分の準備と更新

`human_editing.py prepare`は有効なbase package、current canonical package、作業copyを照合し、UI ownerのtable/prose差分だけを抽出します。作業copyは直接`inspect`してcurrent packageとして扱いません。入力にはsnapshotとレビュー情報を渡します。

```json
{
  "operation": "prepare",
  "package_root": "<current canonical package>",
  "base_root": "<validated copy of the source revision>",
  "edit_root": "<isolated human worktree or copy>",
  "previous_snapshot": {
    "package_version": "vNN",
    "payload_file_sha256": [{"path": "<payload path>", "sha256": "<sha256>"}],
    "manifest_sha256": "<sha256>"
  },
  "review": {
    "decision": "approved",
    "review_ref": "<existing review evidence ref>",
    "placement_agreement_ref": "<Project Context Q06 ref>",
    "change_summary": "<owner-reviewed summary>",
    "approved_change_keys": ["PAGE-001"],
    "evidence_refs": {"PAGE-001": ["<source ref>"]},
    "approved_retirements": [],
    "retirement_evidence_refs": {}
  }
}
```

例はhelperのlocal request shapeです。`review_ref`等の文字列は認証を意味せず、Aのruntimeが未登録の間は実承認・native CASの証拠になりません。helperは`status=ready`と既存writer向け`materialize_request`を返すだけで、writeを行いません。

- 既存IDは同じ意味を継続する場合だけ再利用します。未使用IDを人間が採番した新規行は拒否し、`@draft:<draft_key>`を受け取ってwriterに割り当てさせます。
- 行削除はretireに変換しません。削除意図、理由、承認ref、根拠refをIDごとに明示した場合だけ`retire_ids[]`へ渡します。
- `00`のUI操作判定、`01`のUI構造・Navigation、`02`のUI操作以外の変更、generated/control file、余分なfile、symlink、非canonical encodingは拒否します。
- Authority、AC、UNKNOWN、業務ルール、期待挙動の変更はUI差分に混ぜず`spec-analysis`へ渡します。
- 受理されるtable/prose差分以外に作業copyの編集があれば、部分採用せず対象差分を拒否します。worktreeは保存したままにします。

準備後は、意味上のsource、Authority参照、scope、stable ID、承認要否をownerが再確認し、返されたrequestだけを既存`ui_target_package.py materialize`に渡します。編集案のMANIFESTや生成物をcopyして正本を置換しません。確定後に`inspect`／`validate`／必要な`build-machine-evidence`を独立実行し、version、receipt、allocated／retired ID、無関係row、Manifest、Machine Entity、scope readiness、下流影響を確認します。

## 競合・失敗・再開

- canonical packageがMANIFEST不一致、invalid、symlink、currentness不明ならwriteを止めます。編集copyと元snapshotの証拠は保持し、自動修復・破棄をしません。独立の有効baselineと権限を確認できない場合はblockedです。
- 同じstable ID、関連ref、Scope、proseの意味上の依存が別更新と重なる場合は競合として停止します。独立したIDで依存refも重ならない更新は、current snapshotに対する再レビューが記録された場合だけ再baseできます。
- 同じbaseから同一差分が既に保存されている場合はcurrentをno-opで返し、IDを再採番しません。
- 保存または応答結果が不明な場合は、同一snapshot・同一request fingerprint・writer receiptを照合します。commit後の応答消失は同じrequestの再送とreadbackで判定し、新しいdraft keyで再適用しません。
- writerのpackage-local lockは同一local packageのwriter競合だけを扱います。remote保存先・別workspace・複数hostのCASではありません。保存先native CAS、revision履歴、承認主体の認証、独立readbackを共有runtimeで検証できなければ外部正式保存をblockedにします。

## 機能別導出索引

`feature-index`は実際の`feature-analysis` artifact ref・revision、明示的なfeature-to-Scope mapping、必要に応じてmaterialize後の`changed_ids`を受け取り、current UI package versionから正本path、section、line、stable ID、関連ref、今回変わったcurrent rowを導出します。mappingをpackageへ複製せず、feature名・path類似・画面名からscopeを推定しません。横断検証ではBの実成果物とmapping sourceを用い、独立fixtureを統合証拠に読み替えません。
