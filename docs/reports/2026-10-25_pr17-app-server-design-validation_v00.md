# PR #17 Codex app-server設計検証報告

作成日: 2026-10-25

## 判定

**第1段階で停止。app-serverへの実行経路移行は実装していない。**

Codex app-serverのRPC仕様と認証実装を確認したが、Agent / Judge / Repairの独立した外側bubblewrap、認証refreshの競合防止、Agent shellからapp-server socketへ接続できないことを同時に実証できる構成は確認できなかった。依頼の停止条件に従い、既存launcherと評価処理を変更しない。

## 対象状態

- Repository: ryu-yoshikawa-pro-vision/qa-workflow-skills
- PR: #17（open、base main）
- Branch: feat/agent-eval-runner
- 確認したHEAD: 58074531f4b2854757dbf3353138998f1972ba33
- 同SHAの指定5 workflow: すべてSUCCESS
- 本報告では認証状態、auth file、tokenを読み取っていない。実モデル通信、Agent / Judge / Repair実行もしていない。

既存のWSL2移行PlanはAgent / Judge / Repairに別process、別outer bwrap、別workspace、別一時CODEX_HOMEを要求する。また、repositoryのAgent Working Agreementではruntime受入対象をcodex --no-daemon --strict-configのembedded / non-shared runtimeに限定し、managed/shared app-serverを検証済み扱いしない。この契約を満たすapp-server構成は未確認である。

## 固定CLIの仕様確認

Codex CLI rust-v0.163.0の公式ソースを確認した。

- app-server --listenはstdio、Unix socket、WebSocket transportを持つ。Unix socket transportのデータはWebSocket frameであり、JSONLをsocketへ直接送る方式ではない。
- client側はinitialize responseを待ってからinitialized通知を送る。request/responseのIDとnotification streamを別々に扱う。
- account/readはrefreshToken=trueでmanaged authの通常refreshを要求できる。responseはaccount種別等で、refresh tokenをclientへ渡すAPIではない。
- model/listは候補情報を返すが、アカウントの利用権限を保証しない。
- thread/startにはmodel、cwd、approval policy、Codex sandbox等を指定できる。これらはthreadのruntime設定であり、別々のhost mount namespaceや外側bwrapを生成する契約ではない。
- turn/start後はturn/completedのterminal status（completed / interrupted / failed等）を評価する必要がある。turn/interruptはthread IDとturn IDを要求する。
- Unix socket実装は、指定pathをrendezvous aliasとして扱い、実socketを別の保護directoryに置く場合がある。Unix socket modeは0600。これは他のOS userへの接続制限にはなるが、同じUIDで動くAgent shellからの接続拒否を証明しない。

参照したprimary sources:

- [Codex app-server documentation](https://developers.openai.com/codex/app-server)
- [v0.163.0 app-server CLI entry point](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/main.rs)
- [v0.163.0 app-server protocol: account](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/app-server-protocol/src/protocol/v2/account.rs)
- [v0.163.0 app-server protocol: model](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/app-server-protocol/src/protocol/v2/model.rs)
- [v0.163.0 app-server protocol: thread](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/app-server-protocol/src/protocol/v2/thread.rs)
- [v0.163.0 app-server protocol: turn](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/app-server-protocol/src/protocol/v2/turn.rs)
- [v0.163.0 remote app-server client](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/app-server-client/src/remote.rs)
- [v0.163.0 Unix socket transport](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/app-server-transport/src/transport/unix_socket.rs)
- [v0.163.0 auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)
- [v0.163.0 auth storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)

## 方式比較

### 案A: 手動起動した1つのapp-serverを共有

- **公式仕様上の可否:** 複数threadを扱うRPCはある。threadごとの設定を外側process隔離とみなす根拠はない。
- **認証refreshの責任主体:** 1つのapp-server内のAuthManager。調査したrefresh mutexは同一AuthManager内の処理を直列化する。
- **実行processとfilesystem:** server processは1つ。threadごとに独立したouter bwrapを作る仕様ではない。
- **Agent shellからの認証・socket可視性:** same-UIDのsocket接続とthread横断境界は未実証。認証shell可視性リスクも残る。
- **Judge / Repair:** thread独立だけではJudgeの独立process / outer bwrapを満たさない。thread sandboxだけでRepairの単一Skill書込範囲を保証できない。
- **実装範囲:** thread設定だけで既存契約へ接続する案。
- **残留リスク:** Evaluator-only資料、Judge workspace、認証情報、app-server socketへのアクセスをthread単位で拒否できる証拠がない。
- **判定:** **不採用。**

### 案B: 1回のユーザー操作から独立app-serverを起動

- **公式仕様上の可否:** app-server processを別々に起動すること自体は可能。認証・socket・隔離条件を合わせた構成は未検証。
- **認証refreshの責任主体:** 各app-server processが持つAuthManager。refresh mutexはAuthManager instance単位で、複数process間の排他を示す根拠はない。
- **実行processとfilesystem:** 各serverを独立bwrapへ置ける可能性はあるが、Codexが起動する内側shell、socket、mountの実効範囲を未検証。
- **Agent shellからの認証・socket可視性:** bwrap外のcredential mount、inner shellからのcredential/socket到達性、FD伝播を未実証。
- **Judge / Repair:** 独立server / bwrapと単一Skill mountで構成できる可能性はある。Judge shellからAgent領域、Repairから対象外Skill、各modeからserver socketへの到達拒否は未実証。
- **実装範囲:** supervisor、起動中processの識別、認証storeの所有者、socket管理、interrupt、終了、cleanupを整合させる必要がある。
- **残留リスク:** 共有auth storeでは外部のCodex processも含むrefresh競合を排除できる根拠がない。same-UIDのsocket接続も未検証。
- **判定:** **候補に留める。安全性未確認のため実装しない。**

### 案C: app-serverを認証管理に使い、既存codex execへ委譲

- **公式仕様上の可否:** 認証状態やrefresh結果を別codex execへ委譲するRPCは確認できない。
- **認証refreshの責任主体:** app-serverとcodex execが別々に認証処理を持つ。
- **実行processとfilesystem:** 既存launcherのbwrapは維持できるが、serverからexecへ認証状態を安全に渡す公式経路がない。
- **Agent shellからの認証・socket可視性:** token抽出、store copy、同期なしでは接続できると確認できない。これらは今回の許可範囲外。
- **Judge / Repair:** 既存の独立境界は維持可能だが、認証委譲が未解決。
- **実装範囲:** 独自のtoken transferやauth proxyなしで実現できる範囲は確認できない。
- **残留リスク:** app-server側とcodex exec側のrefresh競合、auth file複製・書戻しの必要性が残る。
- **判定:** **不採用。**

案Bを成立させるには、少なくとも、同一UIDの無関係なCodex processを含むrefresh競合の排除、更新後auth storeの公式な永続性、Agent shellからsocketとcredentialへの到達拒否、Agent / Judge / Repairごとの独立bwrapとmode別mountを実測する必要がある。manager内のmutexはprocess間lockの代用にならない。専用CODEX_HOMEへ公式loginする案も、現時点ではユーザーが使用中のlogin storeとの関係、運用、shell可視性を確認しておらず、既存loginのコピーやtoken同期で穴埋めしない。

案Cのaccount/readは認証情報を返さない。protocolにはexternal auth向けの内部/experimental token入力経路があるが、これはCodex CLIのstoreを別codex execへ渡すサポートされた認証委譲ではない。したがってtoken抽出やauth file複製を伴う設計へ進まない。

## 実測と未確認事項

- 固定CLI 0.163.0のapp-server --helpで--listenと--strict-configを確認済み。今回の検証中に実認証、account/read、model/list、thread/start、turn/startは呼び出していない。
- 過去の合成socket probeは、テストscriptが指定alias pathと保護された物理socket pathを同一視してrelative_to()で例外となり、RPC initialize前に終了した。これはapp-server通信の成功/失敗を示さない。
- 今回の残存一時socket確認はWSL起動時にWsl/Service/E_ACCESSDENIEDとなり、inventoryを取得できなかった。以前のprobeが作成した一時作業directoryは削除済みだが、物理socket残存の有無は未確認である。未知のsocketを探索・削除していない。
- WSL2上での新規synthetic integration、15件のrequired isolation checks、FD/socket/network negative tests、Agent/Judge/Repairのbwrap試験は今回実施していない。
- auth managerのrefresh semaphoreはinstance内にあり、auth storageはCODEX_HOMEのofficial file storageへ書く実装を確認した。これは複数process間のrefresh lockや、同時refresh時の無競合を証明しない。
- authentication_shell_visible_risk=trueを維持する。refresh tokenの状態、auth store内容/hash、Windows側認証は調査していない。

## 変更・検証状況

- 実行経路、profile/evidence schema、README、Plan、grader/rubricは変更していない。
- 実Agent、Judge、Repair、実モデル、QTS、Skill改善を起動していない。
- 新しいtestは追加していない。app-server統合、WSL2隔離、refresh競合にPASSを付けられる実測はない。
- このレポートの変更後に実行するgit diff --checkとCIは、移行実装の検証ではない。

## 次の進行条件

1. ユーザーが対象WSL2 UbuntuでChatGPT再ログインを完了し、固定Codex binaryのcodex login statusでChatGPT loginを確認する。実施時は認証fileを閲覧・複製・記録しない。OPENAI_API_KEYとCODEX_API_KEYはunsetのままにする。
2. WSL2の実アクセスが復旧した後、固定0.163.0のapp-serverを合成環境で起動する。まずtransport handshake、request ID routing、terminal turn status、interrupt、process/socket cleanupだけを無認証で検証し、認証やmodel APIは使わない。
3. 案Bを再検討するなら、同時に複数serverを起動した場合と他のCodex processが存在する場合のrefresh競合をfail-closedにできる根拠を確立する。Unix権限だけをsame-UID隔離として扱わない。
4. Agent / Judge / Repairごとにouter bwrapが独立し、Evaluator-only、Windows filesystem、他mode、他attempt、認証store、app-server socketへのアクセスを拒否することをWSL2 ext4上で正式launcherから実証する。
5. 上記を満たした後に限り、Plan・evidence契約・実行経路を変更する。再ログイン前と新方式の隔離確認前にTC-OUT-001を実行しない。

現時点でユーザーが再ログインを行う場合は、対象のWSL2 Ubuntu login environment内で、利用中の固定runtimeと通常の永続CODEX_HOMEを指定して公式CLIのcodex loginを実行し、その後同じ環境・同じbinaryのcodex login statusでChatGPT loginを確認する。ログインをこちらから実行・誘導していない。refresh_token_reusedが継続する場合は実行を止め、別認証方式へ切り替えない。

## 結論

app-serverには必要なthread / turn RPCとUnix socket transportがあるが、それらは既存の外側bubblewrap隔離や複数process間のauth refresh排他を保証しない。案Aと案Cは要件に適合せず、案Bもsocket・認証・同一UID・refresh競合の負の検証が未完了である。よって、現時点では安全なapp-server構成を確認できず、PR #17の実Agent評価へ進める状態とは判定しない。既存のWSL2 codex exec launcherを保持し、本報告だけを設計検証成果として扱う。
