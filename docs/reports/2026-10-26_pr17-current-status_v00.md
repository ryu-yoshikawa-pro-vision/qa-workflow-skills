# PR #17 現在状態・検証報告

## 判定と対象

- Repository: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- PR: [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)、base `main`、branch `feat/agent-eval-runner`、open
- この報告の検証対象HEAD: `a960f8728bb2e2c14e282d639170ffed6af11e9a`
- 作業branch: `work/pr17-auth-wsl-20261025`
- 固定QTS target: `qa-training-store@84ce165493649550832731a60cf436f8ae29c56b`

PR本文の旧累積記述を確認しました。既存の調査・設計根拠はv03〜v06等の履歴報告とPlanに保存されています。旧本文中のHEAD・CI・未達条件は現況ではなく、`509855d`のevidenceもより新しい`a960f87` evidenceに置き換わっています。最新状態を本文へ置き換える前に追加で保存する必要がある未記録の有効な判断は見つかりませんでした。

Agent、Judge、Repairの二重bubblewrap、schema 2 profile/evidence検証、deterministic / semantic runner、QTS sanitized target・artifact manifest、二系統Judge、改善候補の許可path・再評価・独立回帰の実装は存在します。現在、実運用を止めているのはrefresh永続化と非協調processとの競合です。未承認fixture・安全条件・実モデル利用承認を迂回してrunしていません。

## Codex CLI認証契約と選択肢

固定版`rust-v0.163.0`の公式実装では、refresh同期は個々の`AuthManager`内にあり、refresh成功後は選択中storage backendへ保存しreloadします。file backendは`CODEX_HOME/auth.json`を書き換えますが、process横断lock・atomic replacementを提供しません。`keyring`にもAuthManagerをまたぐrefresh lockはなく、`auto`はkeyring load/save error時にfileへfallbackし、`ephemeral`はprocessを越えて保存されません。公式source: [auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)、[auth storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)。

現行attempt-local copy/delete方式はrefresh更新を次attemptへ保持しません。この損失はfake childを使ったlauncher file-operation testで再現しましたが、過去の`refresh_token_reused`の直接原因とは確定していません。runner専用永続`CODEX_HOME`は保存先の寿命だけを延ばし、外部Codex processとの競合を防ぎません。runner内のfile lockはそのlockに参加しないCodex processを保護できません。Keyringへの切替もprocess横断排他を作らず、WSL2外側mount内でのkeyring backend可用性も確認されていません。専用OS identityは通常ユーザーのstoreとは分離できますが、そのidentityで動く複数のCodex process間では競合が残るため、runner専用identityを他用途で起動しない運用制約とidentity管理が別途必要です。brokerはsecretをshellから隔離しつつrefreshを一箇所へ集約できますが、認証protocol・daemonの新設と管理運用が必要で、既存Plan範囲外です。いずれもこの依頼では導入していません。

fixed CLIの[named permission profile implementation](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/config/permissions.rs)と[Linux bubblewrap deny handling](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs)に基づき、synthetic auth markerをinner shellから拒否し、親Codex processのreadを保つことはformal probeで確認済みです。これは実認証file・Codex親processの実モデル通信を使った検証ではありません。launcherは`authentication_refresh_persistence_unresolved=true`または`authentication_process_concurrency_unresolved=true`の間、Agent/Judge/Repairを認証照会・copy・起動前にfail-closedにします。`authentication_shell_visible_risk=false`はsynthetic markerで検査した経路に限定されます。

## Fresh合成隔離evidence

HEAD `a960f8728bb2e2c14e282d639170ffed6af11e9a`のclean treeで、WSL2 Ubuntu、Python 3.11.17、PyYAML 6.0.3、Codex CLI 0.163.0とpackage同梱bwrapを使い、README記載のschema 2 profile、`agent-command.json=["codex"]`、`verification.evidence_path="isolation.json"`でformal probeを実行しました。実認証、login status、`codex exec`、model APIは使っていません。

- Evidence: `.agent-eval-runs/pr17-isolation-a960-20261026T132518Z/isolation.json`（Git管理外）
- Status: `verified`、evaluator revisionは対象HEADと一致、16/16 required checks true
- Agent / Judge / Repair: 各mode `verified`、各26 subchecksすべてtrue
- `model_api_used=false`
- Profile fingerprint: `sha256:10d3a666dd26c19123cf8ed2cfff1ea4914f14f9f3f5aa15a6316e73c38175d4`
- Agent / Judge argv fingerprint: `sha256:e25eaf648dc7039953915d93cac78cc23b21b780b60f562ff1aaa53086f25364`
- Codex package: `@openai/codex@0.163.0-linux-x64`、SHA-512 `bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3`
- Codex binary SHA-256: `399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215`
- bundled bwrap SHA-256: `77360cb751ccedc5971391444ac86a8a33c15b04d6b4a6fe45f5d25496e62c4c`

16 required checks: `host_home_read_denied`, `symlink_escape_denied`, `timeout_cleanup`, `authentication_shell_read_denied`, `nested_namespaces`, `source_write_denied`, `other_attempt_home_read_denied`, `mounts_reviewed`, `agent_judge_separated`, `fresh_procfs`, `inner_shell_network_blocked`, `inherited_fd_denied`, `windows_filesystem_read_denied`, `extra_tools_disabled`, `output_write_allowed`、`evaluator_read_denied`。全項目trueでした。これらの結果は当該HEADだけに結び付きます。文書更新後のcommitには使い回さず、commit後に同じ正式probeを新規output rootで実施します。

## 通常WSL2での検証

Codex開発sandboxではDeterministic repository suiteが293件中4 failure / 1 errorとなり、AF_UNIX bindは`EPERM`でした。通常WSL2 hostで同じDeterministic suiteを再実行すると全293件PASSし、固定runtimeのformal launcher integrationも1件PASSしました。sandboxの失敗は通常WSL2で再現せず、実装不具合とは分類していません。Hook、execpolicy、sandbox条件は変更していません。

| 検証                               | 結果                                        |
| ---------------------------------- | ------------------------------------------- |
| Agent implementation suite         | 140 PASS、2 SKIP                            |
| Agent repository contract          | 4 PASS                                      |
| Semantic implementation suite      | 27 PASS                                     |
| Semantic repository suite          | 13 PASS                                     |
| Semantic validator                 | 22 Skills、163 cases PASS                   |
| Deterministic implementation suite | 13 PASS                                     |
| Deterministic repository suite     | 293 PASS（通常WSL2 host）                   |
| Codex Harness                      | 59 PASS、8 SKIP                             |
| WSL2 formal launcher integration   | 1 PASS（通常WSL2 host、fixed runtime）      |
| Agent `compileall`                 | PASS                                        |
| Tracked formatter / lint           | PASS、239 files、Ruff 0.16.8・dprint 0.55.2 |
| `git diff --check`                 | PASS                                        |

上記はWSL2上のローカル実行結果です。formatterはrepositoryの追跡対象239 filesを検査しました。固定Codex source内loopback mock refresh/persist/reload harnessは未実行です。

## HEAD `a960f8728bb2e2c14e282d639170ffed6af11e9a` のGitHub Actions

GitHub APIから取得した対象HEADのPR workflow runsはすべてSUCCESSでした。

| Workflow                            | Run ID        | 結果    |
| ----------------------------------- | ------------- | ------- |
| Validate Agent Skills               | `40323403471` | SUCCESS |
| Validate Deterministic Output Evals | `40323403436` | SUCCESS |
| Validate Semantic Output Evals      | `40323403453` | SUCCESS |
| Code Quality                        | `40323403665` | SUCCESS |
| Codex Harness                       | `40323403800` | SUCCESS |

これらは`a960f87`の結果で、今回の後続文書commitには未適用です。push後に新HEADのrunを個別に確認します。

## Judge fixtureの判定と人間レビュー資料

対象fixture catalogはrevision `qts-judge-fixtures-v2`、QTS targetは`84ce165493649550832731a60cf436f8ae29c56b`です。11件中`pending_deterministic_review`は2件（001/002）、`pending_human_review`は9件、`approved`は0件です。approval state、rubric、Referenceは変更していません。fixtureを使ったLLM Judge検証も行っていません。

既存deterministic validatorを既存fixture mutation builderへ適用した合成確認では、001は`test-case-design`を`skipped`にした結果、`noncompleted_routing`と`required_artifact_not_registered`を返しました。002は`qa-workflow=incomplete`かつ最終メッセージで完了を主張し、`noncompleted_routing`を返しました。両方ともfixture statusは`needs_review`になりました。このsynthetic placeholder baselineは実Agent artifactやapproval bindingではなく、rating `1`のJudge正解を直接確定する根拠ではないため、2件ともpendingを維持します。

以下は9件の人間レビュー用資料です。記載した推奨はAIが作成した候補で、承認ではありません。normative referencesはいずれもQTS固定revisionに結び付いています。

### `normal-workflow` — QTS-SEM-001 / QTS-SEM-002、tune、rating 3以上

- 入力変更: なし。通常のworkflow出力を使うpositive fixture。
- 規範根拠: [仕様の読み方とoracle優先順位](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/README.md)、[Checkout BR/AC](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/checkout-and-payment.md)。
- 期待の根拠: 要求されたworkflow routingと完了判断が根拠付きで妥当なら、該当criterionでrating 3以上が必要。
- 判断の分かれ目: 正常例の最終回答だけでなく、artifact indexと実成果物がrubricのcoverageを満たすか。現在は実baseline artifactがなく確認不能。
- 推奨: 期待範囲は妥当そうだが、fixture入力・baseline artifact・criterion別根拠の確認までpending。
- 確認者への質問: このpositive例は001/002それぞれのrubric要件を独立に満たす証拠を提供していますか。

### `normal-artifacts` — QTS-SEM-003..010、tune、rating 3以上

- 入力変更: なし。正常なQA成果物セットのpositive fixture。
- 規範根拠: [Checkout BR/AC](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/checkout-and-payment.md)、各criterionの参照先feature spec。
- 期待の根拠: 成果物が仕様・traceability・scope・coverageに合致していれば各criterionでrating 3以上。
- 判断の分かれ目: 8 criterionをまとめたfixtureが各々の判定を独立して支え、別criterionの欠陥を隠さないか。実baseline artifactがない。
- 推奨: 期待範囲は妥当そうだが、実artifactとrubricを照合するまでpending。
- 確認者への質問: 各criterionへの根拠割当とrating下限は、対象成果物に照らして適切ですか。

### `major-violation-003` — QTS-SEM-003、tune、rating 1

- 入力変更: 未確定のcross-platform pixel parityをWeb Checkoutの必須oracleへ昇格。
- 規範根拠: [未確定仕様](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/unresolved-specifications.md)はPlatform固有Navigation/Typographyの完全pixel parityを未決定とし、[spec oracle hierarchy](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/README.md)ではUnresolved項目を不具合判定の正本にしない。
- 期待の根拠: 未決定事項を確定済み期待動作へ変換するのは根拠のない仕様追加。
- 判断の分かれ目: QTS-SEM-003がWebの受入oracleを対象とし、単なるvisual regressionの指摘と確定仕様への昇格を区別するか。
- 推奨: 変更が記載どおりであることを確認できれば重大違反としてrating 1が妥当。
- 確認者への質問: この変更は未確定pixel parityを採点対象へ不当に昇格していますか。

### `major-violation-004` — QTS-SEM-004、independent、rating 1

- 入力変更: 期限切れCheckout sessionを期限後も有効・再開可能とする。
- 規範根拠: [BR-CHECKOUT-001 / AC-CHECKOUT-001](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/checkout-and-payment.md)はSessionが24時間でexpiredになること、期限切れを確認することを定める。[State and scenarios](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/state-and-scenarios.md)は`expired`を終端状態とする。
- 期待の根拠: expired sessionを有効なまま再開できるという期待は固定仕様に反する。
- 判断の分かれ目: fixtureの「session」がCheckout Sessionであり、別のlogin/session概念を混同していないか。
- 推奨: 対象概念が一致すれば重大違反rating 1が妥当。
- 確認者への質問: 24時間境界後のCheckout Sessionを再開可能にする記述が正確に違反を表していますか。

### `major-violation-005` — QTS-SEM-005、tune、rating 1

- 入力変更: Cart versionまたは価格の不一致にもかかわらずOrderを確定。
- 規範根拠: [BR-CHECKOUT-002 / AC-CHECKOUT-002](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/checkout-and-payment.md)は不一致ならOrder/Paymentを作らずCartへ戻す。[BR-CART-003](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/cart.md)は価格変更の承認前にCheckoutへ進めない。
- 期待の根拠: stale version/priceを確定してしまうのは明示された重要な境界条件への違反。
- 判断の分かれ目: fixtureが不一致を発生させる境界を対象とし、承認済み価格更新の通常ケースを違反扱いしていないか。
- 推奨: mutationどおりならrating 1が妥当。
- 確認者への質問: 期待rating 1はcriterion 005のcritical違反に対応し、過剰に広い条件を課していませんか。

### `major-violation-006` — QTS-SEM-006、independent、rating 1

- 入力変更: Mock Paymentの明確な失敗後に在庫を減算。
- 規範根拠: [BR-CHECKOUT-003](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/checkout-and-payment.md)は明確な失敗を`payment_failed`とし在庫を変更しない。購入時の減算履歴は[BR-ADMININV-002](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/admin-inventory.md)に定義される。
- 期待の根拠: 明示失敗時の在庫変更はPaymentとInventoryの整合性違反。
- 判断の分かれ目: 明確なPayment failureとprocessing、成功後のinventory不足を混同していないか。
- 推奨: mutationどおりならrating 1が妥当。
- 確認者への質問: fixtureはexplicit failureだけを対象にし、他の結果状態を誤って一般化していませんか。

### `major-violation-007` — QTS-SEM-007、independent、rating 1

- 入力変更: Payment processing中のretryまたはcancelを許可。
- 規範根拠: [BR-CHECKOUT-003](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/checkout-and-payment.md)と[Error and Boundary States](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/state-and-scenarios.md)はprocessing中のretry/cancelを禁止する。
- 期待の根拠: 二重確定や状態不整合につながる禁止境界の違反。
- 判断の分かれ目: processing中という限定を保ち、`payment_failed`後の状態遷移と混同していないか。
- 推奨: 記載どおりならrating 1が妥当。
- 確認者への質問: 期待rating 1はprocessing中の禁止事項に限定され、失敗後の許容遷移を誤って禁止していませんか。

### `major-violation-009` — QTS-SEM-009、independent、rating 1

- 入力変更: `AC-CHECKOUT-001`を在庫減算へ誤対応させ、下流testもcheckoutではなくrole authentication testへ接続。
- 規範根拠: [spec oracle hierarchy](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/README.md)と[AC-CHECKOUT-001..003](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/checkout-and-payment.md)はSession再開、stale Cart、Payment一度確定を区別する。
- 期待の根拠: Authorityから異なる要件へ意味を変えて接続するためtraceabilityが誤っている。
- 判断の分かれ目: Criterion 009が参照関係の存在ではなく意味の保持も評価するか。
- 推奨: 要件意味の置換が確認できればrating 1が妥当。
- 確認者への質問: このmutationは単なる誤リンクを越え、QTS-SEM-009の重大な意味不一致を直接示していますか。

### `major-violation-010` — QTS-SEM-010、tune、rating 1

- 入力変更: 外部Stripe API連携を確定済みbehaviorとして追加。
- 規範根拠: [Product Scope](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/product-scope.md)はLocal Mock Paymentを対象とし外部Payment APIを除外する。[spec oracle hierarchy](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/README.md)と[未確定仕様](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/unresolved-specifications.md)は未決定事項を期待動作にできないとする。
- 期待の根拠: 固定scope外の外部連携を確認済み挙動として追加している。
- 判断の分かれ目: fixtureが提案・将来案と現行仕様を明確に区別し、単なる外部サービス名への言及を違反扱いしていないか。
- 推奨: 確定済みbehaviorとして扱っているならrating 1が妥当。
- 確認者への質問: 期待rating 1はunsupported confirmed behaviorだけを対象にしていますか。

## 未実施と残る受入条件

- 固定Codex source harnessでのsynthetic loopback refresh/persist/reload、更新後の次attempt利用、異常終了・部分保存を含む実保存契約は未検証です。
- runner外の非協調Codex processや同一OS identityのprocessを含む競合制御は未成立です。現方式のまま安全にfail-closeします。
- Judge fixture approved件数は0。人間レビューを受ける前にAIがapprovalへ変更しません。
- TC-OUT-001、他の実Agent4ケース・batch、QTS実Agent、Judge、Skill修正・再評価・独立回帰は未実施です。
- 実認証、login、実token、モデルAPIは未使用です。利用者の明示承認を得ても、技術上のrefresh永続化・競合条件が解決するまでは開始しません。
- 文書変更を含む最終commit後にfresh isolation evidenceを再取得し、通常push後の5 workflowをその最新HEADで確認します。
