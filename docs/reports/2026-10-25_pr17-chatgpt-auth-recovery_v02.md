# PR #17 固定Codex runtime照合結果

- **確認日:** 2026-10-25
- **Repository:** `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- **PR:** [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)
- **Branch:** `feat/agent-eval-runner`
- **照合時PR HEAD:** `aab7c5e74d63abd9071507001221140344bfd2f0`
- **前回報告:** [`2026-10-25_pr17-chatgpt-auth-recovery_v01.md`](2026-10-25_pr17-chatgpt-auth-recovery_v01.md)

## 実行環境

通常のWindows PowerShellから`Ubuntu` WSL2を起動し、clean ext4 smoke checkoutから既存`verify_runtime()`を呼び出した。使用checkoutは`/home/sella/src/qa-workflow-skills-pr17-smoke-792b1c8e1addb09f`、HEAD `58074531f4b2854757dbf3353138998f1972ba33`でworking tree clean。WSL identityは`sella`、kernelは`6.18.54.1-microsoft-standard-WSL2`。

このcheckoutと照合時PR HEADのGit差分は既存のreport追加だけで、`codex_wsl2_bwrap_launcher.py`およびimport先`codex_docker_launcher.py`を含むsource/test treeに差分はない。runtime検査に使ったPythonは`3.12.3`。WSLにはPython `3.11.17`も存在するが、PyYAML `6.0.3`の有無はまだ確認していない。

`verify_runtime()`には、次のruntime rootを明示した。

```text
/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final
```

manifestはこのroot直下の`runtime-manifest.json`にある。前回は`runtime-final/package/runtime-manifest.json`の有無を確認していたため、package directory内には見つからなかった。

## 結果

`verify_runtime()`は終了コード0で成功した。報告された値:

- Codex CLI: `codex-cli 0.163.0`
- Package version: `0.163.0-linux-x64`
- Package SHA-512: `bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3`
- Codex binary SHA-256: `399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215`
- Bundled bwrap version: `bubblewrap built for Codex`
- Bundled bwrap SHA-256: `77360cb751ccedc5971391444ac86a8a33c15b04d6b4a6fe45f5d25496e62c4c`
- Machine: `x86_64`

上記は既存固定runtimeのmanifest・binary・version照合結果である。fresh profile/evidence、15件のisolation checks、Agent/Judge/Repair modeの本番launcher検証、認証の永続化・process間排他を証明しない。

## 認証・実評価の状態

認証状態確認の`--auth-status-only`は、Python 3.11.17/PyYAML確認と合わせて通常PowerShellから実行するよう依頼中で、結果は未取得。`auth.json`の本文/hash/tokenを読まず、login/logout、refresh、model API、Agent/Judge/Repair起動は行っていない。`authentication_shell_visible_risk=true`を維持する。

したがって、`TC-OUT-001`の実Agent評価再開条件はまだ成立していない。v00/v01に記録したauth persistenceの欠落可能性、process間refresh競合、agent shellからのcredential読み取りリスクに対する安全な設計も未確立である。
