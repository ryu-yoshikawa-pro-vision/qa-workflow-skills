# PR #17 ChatGPT login状態・WSL依存環境の確認結果

- **確認日:** 2026-10-25
- **Repository:** `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- **PR:** [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)
- **Branch:** `feat/agent-eval-runner`
- **確認時HEAD:** `19c06ab583f1e6db6946971ced7e958503d51505`
- **前回報告:** [`2026-10-25_pr17-chatgpt-auth-recovery_v02.md`](2026-10-25_pr17-chatgpt-auth-recovery_v02.md)

## Python / PyYAML

通常PowerShellから確認したWSLにはPython `3.11.17`がありますが、そのPythonでは`import yaml`が`ModuleNotFoundError`になった。`/home/sella`以下を一般的な`.venv` / `venv`の実行ファイルpathで読み取り専用検索した結果、既存venvは見つからなかった。したがって、固定依存を備えたPython 3.11環境からAgent suiteやprobeを実行できる状態ではない。新しいdependencyはinstallしていない。

## 認証状態確認

モデルAPIを呼ばない`--auth-status-only`を、固定runtime rootとclean ext4 smoke checkoutから実行した。`CODEX_HOME`環境変数は未設定で、launcherは既定の`/home/sella/.codex`を選択した。

出力された安全な分類値:

```text
authentication_check_status: rejected
authentication_method: not_logged_in
codex_cli_version: 0.163.0
runtime_digest_status: verified
status: rejected
auth_status_exit: 1
```

これは現在の既定storeについて、CLIがChatGPT login済みと判定しなかったことを示す。`refresh_token_reused`が今回の現在状態を引き起こしたかは確認できない。status commandは認証方式・状態だけを出力し、credential本文、token、auth file hashは出力・保存していない。モデルAPI、login、logout、refresh再試行は行っていない。

## 再ログイン判断と残る安全条件

今後の実Agent評価にはChatGPT loginが必要だが、再ログイン先となる安全なstoreをまだ指定できない。現launcherはattempt専用`CODEX_HOME`へ認証fileをcopyし、そのdirectoryをCodex shellから読める可能性が残る。永続storeのrefresh保存、別process間の排他、Agent/Judge/Repair shellからの読み取り拒否を証明する設計・合成testも未成立である。安全なstoreと実効隔離を確定する前に、既定`~/.codex`へのログインは案内しない。

また、Python 3.11/PyYAML 6.0.3の既存実行環境が見つからないため、Agent evaluation suite、fresh isolation probe、15件のrequired checksは実行していない。Python 3.12.3による`verify_runtime()`はv02記載のとおり成功したが、正式な評価suite実行条件を満たした意味にはならない。

今回もコード、profile、evidence、grader、rubricを変更していない。`authentication_shell_visible_risk=true`を維持し、実Agent評価再開条件は未成立である。
