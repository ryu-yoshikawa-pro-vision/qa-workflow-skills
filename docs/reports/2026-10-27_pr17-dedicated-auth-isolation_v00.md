# PR #17 専用WSL2認証storeの実装・検証記録

## 判定

2026-10-27 JSTに、PR #17の基準HEAD `0e4722b1603884e30ff590659c03866f7470e5e4`から専用OS identityと永続認証storeを使うfail-closed経路を実装した。PR #17のGitHub stateはopen、base `main`、head `feat/agent-eval-runner`で、確認時のHEADは基準SHAと一致した。この基準HEADの5 GitHub ActionsはすべてSUCCESSだった。

実装treeの単体・repository suiteと固定runtime formal launcher integrationはPASSした。fresh schema 2 isolation evidenceは、この報告を含む変更をcommitしてcleanにした後、`.agent-eval-runs/pr17-auth-isolation-20261027T0031JST/isolation.json`へ新規生成する。以前のHEADの証拠は再利用しない。

専用OS userは未作成で、Codex source harnessによるrefresh/save/reloadも未実施である。よって認証refresh永続化と非協調process競合の受入条件は未達で、実Agent/Judge/Repairを開始できない。コード上の3つのauthentication unresolved/risk flagはtrueのまま維持する。

## 環境と権限

実WSL2環境はUbuntu 24.04.4 LTS、kernel `6.18.54.1-microsoft-standard-WSL2`、通常ユーザー`sella` UID/GID 1000、systemd `running`。専用`qa-agent-eval` user/groupは存在しなかった。`sella`にはsudo group membershipがあるが、非対話の`sudo -n -l`は`a password is required`で停止した。sudo認証を求めず、OS userや設定は変更していない。

通常ユーザーのhomeはmode 0750で、固定runtimeは`/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final`にowner `sella` / mode 0500、venvは同ユーザー所有だった。専用UIDからこれらへ直接アクセスできないため、実運用前にroot管理のruntime、clean source checkout、Python環境を別pathへ配置する必要がある。通常UID 1000ではCodex processが複数動作していた。実認証fileは読まず、metadataだけ確認した。通常ユーザーの既存Codex auth storeは変更していない。

## Codex CLI 0.163.0の認証契約

固定revision `rust-v0.163.0`の[auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)ではrefresh同期は個々の`AuthManager`内に限られる。[file storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)は選択中の`CODEX_HOME/auth.json`をtruncate/write/flushするが、process横断lockやatomic replacementを行わない。したがって、runner内`flock`は協調runnerだけを直列化し、同じUIDで起動する非協調processはOS上の起動権限で制御する必要がある。

`auto`はkeyring load/save error時にfileへfallbackし、`ephemeral`はprocess終了後に状態を保持しない。`keyring`もCodex processをまたぐrefresh lockを提供しないため、明示`file`の専用storeを候補実装にした。固定版の[login command](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/login.rs)はChatGPT login前に既存authをclear/revokeする。追加した本人向けlogin入口は空の新規storeだけを許可し、既存authや不確定markerがある場合はCodexを起動しない。固定版は`codex login --device-auth`を提供するが、今回は実行していない。

Codex source checkoutおよび`rustc`/`cargo`はこのWSL環境に見つからなかったため、固定source test harnessでのloopback refresh実験は未実行である。実モデル通信を伴う`codex exec`も実行していない。fake childによるstore更新はrunnerのpath/bind contractだけを検査し、Codex CLI自身のrefresh成功の証明には使っていない。

## 実装

共通launcherを次のように変更した。

- 専用`qa-agent-eval` UID、primary groupのみ、nologin shell、HOME/`CODEX_HOME`、所有者・mode・TOML backendを照合する。auth JSON本文は読まず、ChatGPT login status以外を許可しない。
- Codex attemptごとの一時`CODEX_HOME`はmode設定専用とし、認証fileを複製しない。専用永続`auth.json`をouter bubblewrapの`/codex-home/auth.json`へbindし、inner named permissions profileがshell readをdenyする。Agent/Judge/Repairは共通launcher経路を使う。
- 認証status、Agent、Judge、Repair、operator loginを同じnonblocking `flock`で直列化する。lock後およびCodex終了後に`/proc`を検査し、既に存在する非runner同一UID processや終了後に残る同UID processがあればfail-closedにする。
- Codex起動前にmode 0600の不確定状態markerを作成・fsyncする。通常終了、temporary home cleanup、専用auth storeと親directoryのfsync、残存同UID processなしが揃う場合だけmarkerを削除する。timeout、異常終了、cleanup/sync/process検査の失敗時はmarkerを残し、次のattemptを止める。
- authentication shell visibility、refresh persistence、process concurrencyの未解決フラグはtrueのまま。専用UIDやprocess-start管理境界がまだ配置されておらず、source harnessとfresh profile evidenceも未実施のためである。

`flock`とprocess scanは、scan後に同UIDでprocessを追加できる主体を制限しない。root/WSL administratorは認証storeとUID境界を越えられる信頼主体である。OSアカウント作成後も、専用UIDを任意processから使える主体を管理者とrunner/login入口に限定するOS側の運用境界が必要である。管理者が同時に別Codexを起動できる状態までOSユーザーだけで防いだとは扱わない。

## 回帰検証

Python 3.11.17、PyYAML 6.0.3、固定Codex CLI 0.163.0/bundled bubblewrap、Ruff 0.16.8、dprint 0.55.2を使用した。launcher integration、Deterministic repository suiteのhost再試験はCodex sandbox外の通常WSL2で実行した。表のほかのsuiteと品質checkはCodex sandbox内で実行した。すべて実認証、token、モデルAPIを使用していない。

| 検証 | 結果 |
| --- | --- |
| Launcher auth-focused unit tests | 38 tests、PASS、1 SKIP |
| Agent suite | 152 tests、PASS、2 SKIP |
| Agent repository contracts | 4 tests、PASS |
| Semantic suite | 27 tests、PASS |
| Semantic repository contracts | 13 tests、PASS |
| Semantic validator | 22 skills / 163 cases、PASS |
| Deterministic unit suite | 13 tests、PASS |
| Deterministic repository suite、通常WSL2 | 293 tests、PASS |
| Codex Harness、CLI 0.163.0をPATH指定 | 59 tests、PASS、8 SKIP（Windows専用） |
| Formal launcher integration、固定runtime、通常WSL2 | 1 test、PASS |
| `compileall -q scripts/skills/evals/agent` | PASS |
| `format_tracked.py format` | 2 Python files formatted、237 unchanged |
| `format_tracked.py check` | PASS、Ruff 0.16.8 / dprint 0.55.2、239 tracked files |
| `git diff --check` | PASS |

Codex development sandbox内のDeterministic repository suiteは、host localhost socket `EPERM`と権限制約による4 failure / 1 errorだった。同じ293 testsを通常WSL2で再実行し全件PASSした。formal launcher integrationもsandbox内ではAF_UNIX bind `EPERM`、通常WSL2の承認済み実行経路ではPASSした。検証条件やsandboxを緩和していない。

固定runtimeのformal launcher integrationは、Agent/Judge/Repairのouter/inner sandboxを用いてsynthetic auth markerを検査する単体統合試験であり、最終HEADに対するschema 2 evidenceそのものではない。最終clean HEADのevidenceについては上記`.agent-eval-runs/` pathを新規作成して確認する。16 required checks全件、3 mode verified、revision/profile/argv/runtime fingerprint、`model_api_used=false`を確認できなければ合格としない。

## 未達条件

- `qa-agent-eval` account、group、専用home/`CODEX_HOME`、root-owned runtime/source/venv、OS側process-start policyは未作成。作成には通常WSL2 terminalでのsudo passwordが必要。
- 実認証またはsource harnessによるrefresh/save/reload、異常終了時のCodex store回復は未検証。uncertain markerは自動解除しない。
- 非runner専用UID processの競合をOS権限で完全排除する条件は未配置。runner lock単体は非協調processを防がない。
- 合成shell markerはlauncher integrationで拒否されたが、変更後のclean HEADに対するfresh schema 2 evidenceはcommit後に生成する。実auth fileを用いた読取り試験はしていない。
- Judge fixture 11件は従来どおり承認済み0件、human review待ち9件、deterministic review待ち2件。人間承認の代行はしていない。
- 実Agent、Judge品質評価、QTS統合評価、Skill改善比較、実モデルAPIは未実施。認証条件と利用承認が満たされるまで停止する。
