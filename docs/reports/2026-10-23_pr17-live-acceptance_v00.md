# PR #17 実Agent評価・Judge独立検証・自動Skill改善の受入結果

- 記録日: 2026-10-23（Asia/Tokyo）
- Repository: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- PR: #17、`feat/agent-eval-runner` → `main`
- 評価対象コードrevision: `5b4059ada6ae8d115f1a10048d98fccb19050a85`
- QTS固定対象revision: `84ce165493649550832731a60cf436f8ae29c56b`
- 詳細な今回の非秘密環境・契約検証記録: `.agent-eval-runs/live-acceptance-20261023-5b4059/`

## 判定概要

PR #17のコード修正と通常テスト・CIは確認できましたが、PR全体の正式受入は未完了です。現在のWSL2 Docker daemonは、過去にCodex bubblewrapのnamespace作成とprocfs mountで失敗した環境と同じLinux kernel・builtin seccomp条件です。前回失敗を繰り返さないため、Codex shell smokeは再実行していません。Agent shell、認証ファイルへのアクセス制御、shell egressを確認できないため、後続の実Agent評価、QTS評価、Judge評価、Skill改善にも進んでいません。

固定QTS checkoutのclean状態・revisionと仕様文書は確認しました。Judge fixture 11件の定義、規範箇所、変異方法、承認に必要なbindingを静的に整理しましたが、fixtureを生成する実Agent baseline成果物がなく、実際の変異後成果物とbindingもありません。11件すべての承認状態を維持し、承認済みには変更していません。

## Git、PR、Plan

作業開始時のbranch、HEAD、状態は次のとおりです。

- Branch: `feat/agent-eval-runner`
- Local HEAD: `5b4059ada6ae8d115f1a10048d98fccb19050a85`
- `git fetch origin`後のremote branch: 同じ `5b4059ada6ae8d115f1a10048d98fccb19050a85`
- GitHub PR #17: open、base `main`、headは同じSHA、未merge
- 作業開始時の未追跡ファイル: `docs/reports/2026-10-23_local-docker-evaluation_v00.md`、`docs/reports/2026-10-23_local-docker-evaluation_v01.md`

2件の未追跡Dockerレポートと既存の`.agent-eval-runs/`証拠は削除・上書きしていません。今回のソースコード変更はありません。確認した正本Planは、共通Agent評価、QTS統合評価、自動分析・改善、Judge評価・改善の4文書です。Planが要求するclean Evaluator checkout、実Agent shell、独立2 attempt、独立Judge、独立回帰の条件は省略していません。

## 実行環境の確認

- Windowsから確認したCodex CLI: `0.162.0-alpha.17.2`。これはCLI versionの記録であり、runtime受入の証明ではありません。
- Windows Python仮想環境: Python 3.11.9、PyYAML 6.0.3、Ruff 0.16.8。必要なPython依存は既に固定版で導入済みでした。
- dprint: CIとrepositoryで固定された0.55.2を一時prefixへ導入し、formatter checkで使用しました。既存のPython環境やrepository依存は変更していません。
- WSL: Ubuntu 24.04、WSL2、kernel `6.18.54.1-microsoft-standard-WSL2`。WSL内system Pythonは3.12.3、既存validation venvは3.11.17ですがpipがなく、YAML/Ruffの有無は確認できなかったため、今回のWindowsテストには使っていません。
- Docker Desktop CLI plugin: 4.96.2。Docker client/server: 29.9.2。daemonはLinux/amd64で、kernelは上記WSL2 kernelです。
- Dockerの実効security optionsとして確認できたものは `seccomp profile=builtin` と `cgroupns` です。AppArmor等の別の実効強制状態は今回確認していません。
- 現daemonに `codex-agent:0.163.0` imageはありませんでした。今回使える固定Agent/Judge/verifier image IDもありません。
- WSL側のmemory表示は合計約3.8 GiB、available約3.1 GiB、swap 1 GiB、Windows C:の空きは約13.5 GiBでした。Windows host memory queryはアクセス拒否で取得できませんでした。
- 認証ファイルの内容・hashは取得していません。Agent shellが起動しなかったため、shell内からの認証ファイルread-denialも確認していません。

既存の`2026-10-23_local-docker-evaluation_v01.md`には、同じDocker Desktop/WSL2系環境でCodex 0.163.0がモデル応答後、bwrap namespace作成で拒否され、shell commandが起動しなかった記録があります。Codespaces記録ではDocker標準seccomp下のnamespace syscall拒否に続き、限定的な診断profileでもprocfs mountが拒否されたことが記録されています。これらは異なる実行環境・revisionの過去証拠としてのみ参照し、今回の成功証拠へ流用していません。

現在のdaemonもWSL2 kernelとbuiltin seccompの組み合わせですが、Agent imageは存在しません。過去と同じ設定でbwrapやprocfs試験を反復しても新しい原因情報を得られないため、shell起動smokeを停止しました。既存のisolation probeが確認したmount境界（Evaluator sentinelの読取拒否、source write拒否、output write許可）はDocker mount範囲の証拠です。Codex内部sandbox、実Agent認証アクセス、外部egressの証明ではありません。禁止されたprivileged、追加capability、unconfined security option、approval/sandbox bypass、host PID、Docker socket mountは使っていません。

## 共通Agent評価

今回の正式なAgent attempt数は0です。次の4件は実行していません。

- `TC-OUT-001`
- `TCN-OUT-001`
- `TC-SEM-001`
- `WF-SEM-003`

shell実行と必要な隔離が確認できなかったためです。Skill配置、Skill file read、helper実行、生成成果物、grader/Judge結果、run traceの整合性を今回の受入結果として主張できる証拠はありません。以前のCodex smokeやWindows fake-agent contract testを、今回の実Agent attemptとして数えていません。

## QTS固定対象

固定checkout `/home/sella/src/qa-training-store-pr17-fixed-84ce165-20261023` はcleanで、HEADとcommit objectは `84ce165493649550832731a60cf436f8ae29c56b` でした。Scenarioは `qa-training-store-checkout-payment-web-v1`、対象はCheckout / Payment Webです。規範文書の存在とSHA-256も確認し、値を`.agent-eval-runs/live-acceptance-20261023-5b4059/environment.json`へ記録しました。

新しいQTS baseline result、固定profileの検証証拠、現daemonにあるAgent/Judge/verifier imageがありません。さらにshell隔離が不成立です。したがって独立2 attemptは0件で、Agent session、sanitized artifact、`artifact-index.json`、必須QA成果物、runtime replay、target不変性、grader、Judgeの正式結果はありません。過去の失敗runは新しいbaselineとして使っていません。

## Judge fixtureの確認・承認準備

現在のfixture catalogue revisionは `qts-judge-fixtures-v1`、合計11件です。Human review待ち9件、deterministic review待ち2件、approved 0件です。期待ratingは通常fixtureが `rating_at_least_3`、違反fixtureが `rating_1` です。fixture JSON自体に`evaluable`値はありませんが、既存判定器は通常例でstatus `pass`、違反例でstatus `fail`を要求し、`not_evaluable`を期待判定と一致させません。したがって承認候補はevaluable=trueである必要があります。実成果物に根拠がなく評価不能なら、そのcaseを承認せずreview pendingに残す必要があります。

### Deterministic review待ちの2件

- `major-violation-001` — QTS-SEM-001。mutatorは`test-case-design` routingをskippedにし、対応するartifact-index項目とartifactを除きます。期待rating 1 / evaluable true。判定根拠の確認先はscenario rubricのWorkflow routing criterionです。
- `major-violation-002` — QTS-SEM-002。mutatorは`qa-workflow` routingをincompleteにし、final messageへ完了主張を入れます。期待rating 1 / evaluable true。判定根拠の確認先はscenario rubricのWorkflow completion decision criterionです。

既存の`_prepare_fixture()`はbaseline成果物をコピーしてこれらの変異を作り、`validate_artifact_index()`で構造を検証します。ここで行う構造検証はJudgeの意味的な期待ratingを独立に証明しません。該当するbaseline artifact-indexがないため、今回実際にfixtureを生成・検査して紐付けた証拠もありません。2件ともdeterministic review pendingを維持しました。

### Human review待ちの9件

以下はfixture定義と規範箇所に基づく静的な確認準備です。「対象artifact」はgeneratorがbaselineの`artifact-index.json`から選ぶkindであり、今回の実ファイルpathは生成されていません。

- `normal-workflow` — QTS-SEM-001/002、変異なし、Workflow/routingとfinal decisionの正常例。期待ratingは両criterionで3以上、evaluable true。実baselineのrouting・artifact・final messageが揃っていないため正常例として未確認。
- `normal-artifacts` — QTS-SEM-003〜010、変異なし、canonical QA artifactsの正常例。期待ratingは各criterionで3以上、evaluable true。実成果物のtraceabilityと内容は未確認。
- `major-violation-003` — QTS-SEM-003、test-requirementまたはspec-analysisへ「未解決仕様を確定oracleへ昇格」する内容を追加。期待rating 1、evaluable true。根拠: target `docs/spec/README.md:42-68`、`docs/spec/unresolved-specifications.md:1-11`。Product Decision前のUnresolvedは期待挙動の正本ではありません。ただし固定revisionのunresolved文書にある項目はWeb/Native間のvisual parityだけで、stale Cartに関する未解決記述はありません。変異文はCheckoutの未解決仕様が存在するように述べており、ケースの説明と参照仕様にずれがあります。Cart Version不一致時にOrder/Paymentを作らないというBR-CHECKOUT-002にも直接反するためrating 1候補ではありますが、このfixtureが測るべき論点を人が確認するまで未承認にします。
- `major-violation-004` — QTS-SEM-004、test-condition-and-ciまたはtest-caseへ「24時間超過後もCheckout Sessionが有効」と追加。期待rating 1、evaluable true。根拠: `docs/spec/features/checkout-and-payment.md:9-11`、`docs/spec/state-and-scenarios.md:11-17`。
- `major-violation-005` — QTS-SEM-005、test-condition-and-ciまたはtest-caseへ「stale Cart Versionまたは価格差異があってもOrderを確定」と追加。期待rating 1、evaluable true。根拠: `docs/spec/features/checkout-and-payment.md:13-15`、`docs/spec/features/cart.md:17-19`。
- `major-violation-006` — QTS-SEM-006、test-caseへ「明示的Payment failure時にも在庫を減算」と追加。期待rating 1、evaluable true。根拠: `docs/spec/features/checkout-and-payment.md:17-19`、`docs/spec/features/admin-inventory.md:13-15`。
- `major-violation-007` — QTS-SEM-007、test-caseまたはtest-condition-and-ciへ「Payment processing中にretry/cancel可能」と追加。期待rating 1、evaluable true。根拠: `docs/spec/features/checkout-and-payment.md:17-19, 154-161`、`docs/spec/state-and-scenarios.md:25-27`。
- `major-violation-009` — QTS-SEM-009、coverage-analysisへAC-CHECKOUT-001と異なる意味の要件・testのtraceabilityを追加。期待rating 1、evaluable true。根拠: target `docs/spec/features/checkout-and-payment.md:238-252`でAC-CHECKOUT-001はSession再開・置換、BR-CHECKOUT-001に対応します。mutationはこれをPayment失敗時の在庫減算と誤定義し、下流testもCheckoutを実行しない認証role testとします。scenario rubricのTraceability meaning and closure criterionにも対応します。実際のsource-to-test mappingは未生成。
- `major-violation-010` — QTS-SEM-010、test-requirementまたはtest-caseへStripe等の外部Payment APIとserver-side authorizationを確認済み動作として追加。期待rating 1、evaluable true。根拠: `docs/spec/product-scope.md:17-28`、`docs/spec/features/checkout-and-payment.md:5, 17-23`。外部Payment APIはscope外で、PaymentはLocal Mockです。

期待ratingが規範とmutation名に合うという静的照合だけでは、実fixture承認になりません。実baseline成果物がないため、actual artifact path、baselineと変異後の本文、Judge入力、`approval_binding`はすべて未生成です。人間が確認する成果物とbindingが得られるまで承認依頼を出さず、承認ファイルも作成していません。実行後に確認する承認bindingはREADMEの契約どおり、dataset revision、case ID、reviewer、timezone付きapproved_at、normative evidence、run出力のbinding全体を使用します。旧承認や合成承認は使いません。

## 実Judge評価と自動Skill改善

- Judge independent validation: 0 attempt。baseline result、verified isolation/profile、承認fixtureとrun固有bindingがそろっていません。正常例の誤検出、違反見逃し、not_evaluable回避、反復揺れ、criterion別状態は未評価です。
- 改善分析: 未実行。実Agent baseline、2 attempt再現、観測済みSkill使用、検証済みJudge根拠がありません。
- Skill candidate: なし。人工欠陥や合成Judge承認を作っていません。
- 独立回帰: 未実行。候補生成前のcase固定・条件固定を伴う独立attemptはありません。
- 今回のlive runで判明したコード欠陥: なし。実Agent経路に到達していないため、ランナー不具合を発見したとは結論しません。

## 単体・契約テスト、formatter、CI

指定された各validationを個別に実行しました。

- Agent eval suite: 90 tests、77 pass、7 skip、6 errors。全6件はWindowsでLinux専用Docker launcherを呼ぶテスト、image probeのWinError 193、またはWindows Pythonに`os.getuid/getgid`がないことによる環境非互換です。Agent suite全体をPASSとはしていません。
- Agent repository contract: 4/4 pass。
- Semantic harness: 27 tests、25 pass、2 skip。
- Deterministic repository suite: 293/293 pass。PyYAML 6.0.3入りのvenvで再実行しました。
- Semantic repository suite: 13 tests、12 pass、1 skip。
- `compileall` for agent eval package: pass。
- `scripts/format_tracked.py check`: Ruff 0.16.8 pass、dprint 0.55.2 pass。報告書追加前のtracked対象236 filesはすべてformattedでした。報告書stage後にもう一度checkします。
- `git diff --check`: pass。報告書をstageした後にcached diffにも再実行します。

評価対象コードSHA `5b4059ada6ae8d115f1a10048d98fccb19050a85`についてGitHub Actions 5件すべてSUCCESSを確認しました。Validate Agent Skills (1391)、Validate Deterministic Output Evals (1390)、Validate Semantic Output Evals (1355)、Code Quality (85)、Codex Harness (85)です。通常CIは外部LLMを使った実Agent評価の代わりではありません。今回の報告書commit後のCIはPRと最終回答で別途確認します。

## 完了条件ごとの最終判定

- コード実装: 既存変更は指定revisionにあり、現在のPR headで5 CIが成功。今回追加の実装修正なし。
- 単体・契約テスト: 部分達成。上記suiteは成功したものの、Windows Agent suiteの6 environment errorが残ります。
- 実Agent shell実行: 未達。Codex bubblewrap shell toolの成功記録なし。
- 隔離の実効性: 部分確認。過去のDocker mount境界確認のみ。Codex sandbox、credential denial、shell egressは未確認。
- 共通Agent評価: 未実施、4 caseとも0 attempt。
- QTS統合評価: 未実施、独立baseline attempt 0件。
- Judge独立検証: 未実施、fixture全11件が未承認。
- Skill改善実証: 未実施。自然発生したSkill欠陥と改善候補なし。
- 独立回帰: 未実施。
- PR #17正式受入: 未完了。

## 残課題と次の手順

まず、禁止された権限緩和なしでCodex bubblewrap namespaceとprocfsを通し、固定workspace外の読取・書込拒否、認証ファイルのread denial、shellからの外部通信制御をnegative testで示せるLinux環境が必要です。候補として専用Linux VM/hostを調べる場合も、Dockerの標準seccomp/procfs制約が残る可能性があるため、環境移行だけで解決したとは扱えません。別のhost-native方式は現行Planの信頼境界を変えるため、Plan変更案と安全性比較を先に提示し、承認を得る必要があります。

新規VM/hostの課金、管理者操作、仮想化設定変更、外部サービス契約は実行していません。これらに該当する環境を使う場合はユーザーの承認が必要です。安全なsmokeが成立した後に、共通4 case、QTS独立2 attempt、fixture生成とbinding確認、fixtureごとの人間/決定論的承認、承認範囲のJudge検証、条件成立時のみ改善分析と独立回帰の順で再開します。
