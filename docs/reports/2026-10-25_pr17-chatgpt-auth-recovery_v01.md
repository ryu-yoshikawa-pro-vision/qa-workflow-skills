# PR #17 WSL2・ChatGPT認証更新調査 追補

- **確認日:** 2026-10-25
- **Repository:** `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- **PR:** [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)
- **Branch:** `feat/agent-eval-runner`
- **確認HEAD:** `51496102c604dee9807c2a8eeaa42a49605eb180`
- **基礎報告:** [`2026-10-25_pr17-chatgpt-auth-recovery_v00.md`](2026-10-25_pr17-chatgpt-auth-recovery_v00.md)

この追補は、通常のWindows PowerShellからのWSL診断結果を記録する。v00の認証設計調査、テスト結果、残留リスクを置き換えない。

## 通常ユーザーPowerShellでの結果

ユーザーが提示した出力では、`whoami.exe`は`mycomputer\sella`を返した。

- `wsl.exe --version`: exit 0。WSL `3.0.3.0`、kernel `6.18.54.1-1`、Windows `10.0.19045.7807`。
- `wsl.exe --status`: exit 0。既定distributionは`Ubuntu`、既定WSL versionは2。
- `wsl.exe --list --verbose`: exit 0。`Ubuntu`と`docker-desktop`の両方が`Running`、version 2。
- 実際の一覧に表示された名前を使った`wsl.exe -d Ubuntu --exec /bin/true`: exit 0。

この結果から、通常ユーザー`sella`のPowerShellではUbuntuを起動し、Linux commandを実行できることを確認した。v00で`wsl --status`と`--list --verbose`が失敗したのは、WSL全体またはUbuntuの停止ではなく、少なくともこのCodex実行環境との実行context差である。

## Codex実行環境との比較

同じCodex sessionから`wsl.exe -d Ubuntu --exec /bin/true`を実行すると、`Wsl/Service/E_ACCESSDENIED`となり、終了コードは`-1`だった。出力encodingの不一致で表示は崩れたが、エラー分類は読み取れた。v00で記録したCodex process identityは`MYCOMPUTER\codexsandboxoffline`で、通常PowerShellの`sella`とは異なる。

確認できた範囲では、WSL/Ubuntuは通常ユーザーcontextで実行可能だが、Codexの制限されたWindows identityからはWSL serviceが拒否する。token・service境界の詳細な原因までは特定していない。WSL、service、distribution、Windows securityの設定変更や停止操作は行っていない。

## 次の確認と未達事項

ユーザーが通常PowerShellから実行した読み取り専用確認では、WSL identityは`sella`、kernelは`6.18.54.1-microsoft-standard-WSL2`、既定`python3`は3.12.3だった。

- `/home/sella/src/qa-workflow-skills-pr17-smoke-792b1c8e1addb09f`はHEAD `58074531f4b2854757dbf3353138998f1972ba33`のclean checkout (`HEAD (no branch)`)。
- `/home/sella/src/qa-workflow-skills-pr17-clean-20261023`はcleanだがHEAD `2e5005865c437e9aa701504d18186071f27a0343`。
- `/home/sella/src/qa-workflow-skills`、`...pr17-linux-34715bf-20261024`、`...validation-20261023`には既存変更・未追跡ファイルがある。内容を変更せず保持した。
- 依頼に記載された`/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final/package/runtime-manifest.json`は存在しなかった。

現PR head `5149610...`とsmoke checkout `5807453...`の間で、`codex_wsl2_bwrap_launcher.py`およびそのimport先`codex_docker_launcher.py`に差分はない。したがってこのclean ext4 checkoutから既存の`verify_runtime()`を呼ぶことはruntime asset自体の照合には使えるが、現在のHEADに対する正式なfresh isolation evidenceの代替にはならない。固定runtime manifestの別の所在、Python 3.11環境、`verify_runtime()`の結果はまだ未確認である。Codex実行環境からWSLを起動できないため、次に通常PowerShellからruntime manifestの所在とPython 3.11の有無を読み取り専用で確認する。認証fileは読まず、model/API requestも送らない。

WSL command起動確認だけでは、次の受入条件は成立しない。

- 現行clean checkoutからの`verify_runtime()`成功
- fresh isolation evidenceと15件のrequired checks
- 合成認証markerによるAgent/Judge/Repair shellの認証store読み取り拒否
- 認証更新の永続化と別process間競合の安全な処理
- ChatGPT login状態
- `TC-OUT-001`の実Agent評価再開条件

認証状態の確認、再login、モデルAPI呼び出し、Agent/Judge/Repair起動は行っていない。`authentication_shell_visible_risk=true`を維持する。変更範囲は本追補のみで、v00に記録したテスト結果は今回再実行していない。
