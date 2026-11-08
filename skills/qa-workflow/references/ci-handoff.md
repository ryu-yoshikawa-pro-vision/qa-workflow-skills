# 製品CI成果物受渡しの決定論的検証

`ci_handoff.py` は、製品CIから提供されたsource snapshotと検証済み成果物の期待値を、Agentの候補manifestと照合します。**保存先の選定や認証を代行しません。** この検証の`pass`はsource・差分分類・ファイル受渡しの整合性だけを意味し、意味品質・承認・実製品CI接続済みを意味しません。

## 入力と信頼境界

- `--expected`：製品CIが実際に取得したbase/head/build、全変更パス、完全な情報源一覧、許された差分分類、各ownerが保存した正本のref・revision・content hash、必要承認。**Agentの候補出力から作らない**。製品CIは別の権限ある経路から取得し、読み取り元が信頼できない場合は実行しない。
- `--manifest`：Agentが引き継ぐ候補JSON。source inventory、差分分類、成果物の参照と読込用相対パスを含む。候補を信頼済みexpectedとして複製しない。
- `--artifacts-root`：CIで取得・展開した成果物ディレクトリ。リンクと親ディレクトリ参照を拒否し、バイト列のSHA-256を独立に照合する。

どちらのJSONも`schema_version: qa-ci-handoff-v1`を持つ。必須項目は次の例で確認できる（値は独立fixtureであり実案件の認可を示さない）。

```json
{
  "schema_version": "qa-ci-handoff-v1",
  "source": {
    "repository": "owner/product",
    "base_sha": "1111111111111111111111111111111111111111",
    "head_sha": "2222222222222222222222222222222222222222",
    "build_ref": "build-12"
  },
  "source_inventory": [
    {
      "ref": "repo-source",
      "revision": "2222222222222222222222222222222222222222"
    }
  ],
  "changed_paths": ["src/a.ts"],
  "allowed_classifications": ["implementation", "specification"],
  "artifacts": [
    {
      "owner": "feature-analysis",
      "scope": "SCOPE-001",
      "artifact_ref": "feature-1",
      "revision": "rev-5",
      "sha256": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "source_refs": [
        {
          "ref": "repo-source",
          "revision": "2222222222222222222222222222222222222222"
        }
      ]
    }
  ],
  "required_approvals": []
}
```

manifestは`source`を同じ形で持ち、`source_inventory`を`{"complete": true, "entries": [...]}`で渡す。`changed_paths`の代わりに`changes: [{"path": "src/a.ts", "classification": "implementation"}]`、各成果物に`path`を含める。各ownerが作成したschema自体は変更せず、正本内容のhash・revisionを参照する。

```bash
python skills/qa-workflow/scripts/ci_handoff.py \
  --expected /trusted-ci/current.json \
  --manifest /handoff/candidate.json \
  --artifacts-root /handoff/artifacts
```

JSONの`status`は`pass`／`fail`／`blocked`。終了コードは0（受渡し整合）、1（不一致／blocked）、2（入力契約違反）。期待source、全変更集合、情報源revision、正本revision・hash、欠落、未分類を照合する。承認が必要な場合、**現在は認証済みprovider接続がないため常にblocked**となる。候補manifestの`approved`等を権限証拠にはしない。

各artifactの`source_refs[]`は1件以上が必須で、期待source inventoryのrevisionと照合します。受渡しファイルは上限16 MiBです。対応するPOSIX CIではrootからのdirectory descriptorを保持し、`O_NOFOLLOW`と`O_NONBLOCK`で通常ファイルのみを読み取ります。FIFO・symlink・root外参照を拒否し、競合なくファイルを開く機能がないWindows等の環境では`artifact_readback_failed`で停止します。`changed_paths`／`changes[].path`はPOSIXリポジトリの**比較キー**であり、バックスラッシュを含むファイル名も受理します。成果物読取りの`artifacts[].path`とは別の検証で、後者にバックスラッシュは許可しません。JSON入力の深いネストは不正入力として扱い、CLIの失敗レポートはUnicodeエスケープを用いて確実に出力します。変更履歴や承認対象の検証をhash照合で代替しません。承認が未接続でも旧HEAD・欠落・hash不一致等があれば`fail`、不一致がなく承認だけ未確認なら`blocked`です。

対象製品repositoryへこのCLIを接続するには、案件の保存先・取得方法・権限・信頼済みexpectedの生成元と承認確認方式の決定・実証が必要。未選定のため、現時点では製品CIの実接続は未検証である。
