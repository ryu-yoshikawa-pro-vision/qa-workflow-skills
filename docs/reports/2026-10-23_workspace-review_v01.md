# qa-workflow-skills ワークスペース反復調査・レビュー v01

- 調査日: 2026-10-23 JST
- 対象: C:\Users\sella\Documents\qa-workflow-skills
- branch / HEAD: feat/agent-eval-runner / 03703f5ec0a281e7c4b86d4af1f0bb51f568e1af
- 起点: [初回レポート v00](2026-10-23_workspace-review_v00.md)。同ファイルは変更しない。
- 許可範囲: 読取り調査、安全なローカル検証、本ファイルの新規作成だけ。実装・Skill・test・fixture・Plan・依存・branch・index・PR・Issueは変更しない。
- 方法: repositoryのcode-review Skill、CODE_REVIEW.md、AGENTS.md、README.md、EVALS.md、対象Skill / Planを照合。subagent・外部review serviceは使っていない。

## 1. 総合評価

**分析・設計・成果物状態管理の基盤は継続利用できる。実Agent評価・Judge検証・自動改善を受入済みとして扱う段階ではない。全体を作り直す必要はなく、信頼境界と評価モジュール間の契約を先に限定修正する。**

最終確定は **11件: P0 0件 / P1 6件 / P2 5件**。初回の6件を無条件に採用せず、5件を維持、1件を撤回した。維持したうちF04はP1からP2へ変更、F06は根拠の範囲を縮小した。新規はN01–N06の6件である。

最優先はN02（Agent出力内symlinkをホスト書込みが追従する経路）。Linuxでの侵害実行を今回再現したわけではないが、両runnerの書込み順序と既存の検査位置から具体的な経路を特定した。次にN05（実normalizer出力でJudge検証がKeyError停止）を直し、N01・F01で「承認済み・検証済み」の根拠を閉じる。F02・F03の原因帰属・独立回帰が揃うまでは、Skill修正候補を検証済み改善へ昇格させない。

| 領域                         | 現在の判断                                                                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 22 Skillの責務・通常QAフロー | 仕様理解、質問、分析、TR / TCN / CI / TC、coverage、review、実行、E2E、継続QA、UI / WCAGへの分担は成立。必要工程を選ぶ設計を維持する |
| 決定論的runtime・成果物契約  | 今回runtime 371件（2 SKIP）、repository deterministic 290件が成功。構造・ID・鮮度・状態契約の検証に利用可能                          |
| semantic評価基盤             | dataset 22 Skill / 163 caseと共有normalizerの契約検証は成功。実Agent出力の全量品質を保証しない                                       |
| 実Agent / QTS runner         | 実装あり。PR #17が報告するlive受入は未達。新たにホスト書込み境界と未検証結果の保存契約に問題を確認                                   |
| Judge fixture / 改善         | 実装あり。ただしN05で実出力の接続が停止し、その先にも承認・集約・修正許可・独立回帰の不足がある                                      |
| 今後の開発                   | 通常QA基盤の開発は進められる。Agent評価・自動改善の受入は、指摘修正と限定した実環境検証を依存順に行う                                |
| 完成度の限界                 | コードの存在、fake test成功、実AgentのSkill使用、品質改善、製品自体の正しさを区別する。既存Codespaces問題は再調査していない          |

## 2. 現在状態・証拠の区別

### 2.1 Git・GitHub・環境

開始時のworking treeは、未追跡のv00だけ。tracked / staged差分はなかった。HEADは初回と同じであり、指摘が修正された前提にはしていない。

GitHub connectorを今回再取得し、[PR #17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)の実headも03703f5、open・未mergeと確認した。open Issue検索は0件、open PR検索は#17・[#10](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/10)。#10は別branchの同期batch Planであり、現在checkoutの実装済み機能へ数えない。default branchの独立した最新refは今回取得していない。

現行HEADに紐付く次の5 workflowはsuccess。取得APIが返すPR-triggered runのfirst pageの範囲であり、全eventの履歴を網羅する主張ではない。

- [Validate Agent Skills: 39809513941](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/39809513941)
- [Validate Deterministic Output Evals: 39809513879](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/39809513879)
- [Validate Semantic Output Evals: 39809513862](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/39809513862)
- [Code Quality: 39809513911](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/39809513911)
- [Codex Harness: 39809513853](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/39809513853)

[PR #14](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/14)、[#16](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/16)、[#18](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/18)は今回もAPIでmergedを確認。各headは763f01d、0202b12、81e5f5e。PR本文に残る当時のopen / 同期未了という記載を現在metadataより優先しない。

既存Pythonは3.11系の.venvを使用。通常のPowerShellから解決したCodexはVS Code拡張配置の **0.160.0**、tests/codexがshutil.which / Windows command prefixで実際に検査したCLIは **0.162.0-alpha.17.2**。この違いを一つのversionへ丸めない。Agent Dockerfile / profileの受入対象0.163.0を今回起動したわけでもない。version固定・install・更新はしていない。

### 2.2 ワークスペース構造と正本

主要directoryはskills、scripts、tests、docs、.agents、.codex、.github。既存の.venv、.agent-eval-runs、.artifacts、output等は依存・実験・保存証拠であり、canonical Skillや現行受入結果と混同しない。キャッシュや全保存成果物の一括内容監査はしていない。

全22 Skillの入口・責務を列挙し、主要なproduction helper、呼出し先、validator、対応test、CIを以下の範囲で追跡した。全source行の逐語監査という意味ではない。

| Skill / 基盤                                                       | 入口から終了までの主経路・今回の確認                                                                                                                                                                                 |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| spec-analysis / question-analysis                                  | Authority・質問ID → UI packageのread / inspect / materialize → Scope readiness → Q&A反映。package lock、receipt replay、staging / backup復旧、退役・同一ID復元を対応testと照合                                       |
| test-analysis                                                      | risk / technique / impact / environment generator → Machine Entity。意味判断を入力として受け、機械出力とRisk自体の妥当性を分離する契約を確認                                                                         |
| test-requirement-design / test-condition-design / test-case-design | TR → TCN / model / target → materialize CI → TC。stable ID、upstream dependency、current / inactive履歴、cutover順序、partial resumeをruntime suiteと照合                                                            |
| coverage-analysis / adversarial-review                             | traceability node / edge / closure・freshness → coverage / review → owner routing。構造の完全性と意味的網羅性を混同しない                                                                                            |
| qa-workflow                                                        | migration preflight → downstream state → 必須runtime / Entity集合 → freshness / closure → can_complete。保存baselineのhash binding、CAS capability不足時のblock、履歴再取得を逆方向にも確認                          |
| test-target-inspection / test-execution                            | current資料 → 固定TC snapshot → Given / When / Then → 実操作・観測・cleanup。未開始 / 判定不能 / PASS / FAILと副作用回数の契約を確認                                                                                 |
| 5つのe2e-test-*                                                    | inspection → implementation → execution → result-analysis / reporting。runner開始前必須情報、raw TestCase / attempt、retries、webServer ownership、artifact freshness、cleanupをvalidator / testと照合               |
| regression-testing / exploratory-testing / qa-knowledge            | baseline / selection / Activity、Charter / attempt / Session、canonical entry / currentness / lookup / CAS。N03・N04を追加。全required route開始条件・Knowledgeの更新停止条件は維持                                  |
| usability-evaluation / usability-inspection                        | 保存証拠の意味判断とcurrent browser ownerを分離。catalog、fixed probes、HMAC document identity、typed partial evidence、additional observation / Findingの区別を確認                                                 |
| wcag-conformance-evaluation                                        | versioned criterion / procedure → sampling / complete process → observation handoff → sample results → owner close-report → SQLite CAS / readback → formal report。pending-persistenceを完了と取り違えない経路を確認 |
| deterministic / semantic / Agent基盤                               | manifest → generation → output → grader / normalizer → attempt保存 → comparison / fixture検証 → analysis / repair / reevaluation。特にモジュールをまたぐ戻り値を実関数で検証                                         |
| tests / CI / safety / formatting                                   | 5 workflow、Windows / Linuxの適用範囲、Hook / execpolicy、formatter、固定依存、Skill-local配布を照合。通常CIに外部LLM受入を含めたとは解釈しない                                                                      |

主なPlanは、Agent runnerのMain Planと_02（QTS）・_03（分析改善）・_04（Judge）、UI対象分析modeのMain / 分割Plan、formatter / harness契約。改善Planの原因帰属、判定根拠種別、独立回帰、停止条件を独自に緩めていない。

### 2.3 保存済み証拠と今回の実行

PR #16の41項目smoke・8 case / 36 criterion PASS、PR #14の代表browser受入、PR #17のCodespaces診断・QTS / 共通runner smokeは**過去の記録**である。v00が確認したlocal manifest / hashは出典として参照したが、今回その全raw artifact hash連鎖を再検証・実Agent再実行していない。

PR #17の最新本文は、QTS 2 attemptでcanonical artifact indexなし・Judge未実行、共通4 smokeもSkill使用未検証、Judge fixture 11件のapproved 0、Skill改善未達と報告する。これを環境問題の新規発見として数えない。現在のhead / CIに関する本文の不一致だけはF06として別扱いする。

## 3. 調査履歴と終了判定の記録

周回は同じファイルの再読数ではなく、調査方法を変えたレビュー単位で数える。第1周は初回指摘の再検証、第2周以降は全主要領域を対象にした異なる観点のレビューである。

| 周回 | 範囲・主な観点・新たな事実                                                                                                                                                                                                                 | 新規確定 | 初回指摘の撤回 / 統合                             | 残る未確認・次の周回                                                                         |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 1    | 現在状態、6件のコード・Plan・caller / callee・test再照合。F01–F03のgateを合成データで再現。F04の入口制限確認。44 fake testを再実行し6 errorsを分類。F06のmetadataを再取得                                                                  | 0        | F05撤回1、初回IDの統合0。F04をP2へ変更            | liveは未確認。次に6段階の目的・経路・状態・評価・安全・保守を横断する                        |
| 2    | 目的と責務 → 正常 / 部分失敗 / 再実行 → ID / freshness / 保存 → Judge / 改善 → trust boundary → CI / 保守の順で確認。N01承認binding、N02ホスト書込み、N03結果不明retry、N04不完全scanを特定                                                | 4        | 0 / 0                                             | N02のLinux動作は未実行。新規指摘の共通原因、最終結果からの逆追跡へ進む                       |
| 3    | 原因から近隣経路を探索し、完了判定から逆追跡。QTSと共通runnerのsymlink症状をN02へ、古いfixture manifestをN01へ整理。実normalizer→fixture判定、未検証Judge→共通runner保存を接続しN05・N06を再現                                             | 2        | 0 / 0（既存IDの統合なし。同根症状は指摘内で統合） | 未確認は§7。新規発見があったため連続ゼロ回数をリセット。次に仕様→実装→testを全体確認する     |
| 4    | 全22 Skill入口、主経路の要求 / ID / Scope / workflow完了、E2E開始・raw結果、Regression全route、Knowledge CAS、UI / WCAG owner closure、評価の独立性、CI責務を仕様起点で照合。runtime 9コピー同一を再確認。実normalizer依存の他callerも検索 | 0        | 0 / 0                                             | 外部環境依存だけが残る。次にtest起点の見逃しと異常入力・保存境界・保守簡素化を確認する       |
| 5    | 成功testが検出できない境界を再評価し、negative契約、source / output / reference分離、archive / path、command / env、claims / cleanup、immutable history、通常CIとlive受入を全体横断。固定依存・既存helper再利用・formatter適用も確認       | 0        | 0 / 0                                             | 新規の根拠付き指摘なし。未確認を明示したうえで終了。以下はレポート整合性・変更範囲の最終確認 |

第4・第5周は、主経路の仕様保証と異常系・テストの保証限界という異なる観点の全体レビューで、連続して新規確定0件。単に「一度見つからなかった」ための終了ではない。問題が存在しないことの証明とは主張しない。

### 3.1 指摘化しなかった候補・統合

- **撤回D01:** repair diffがevals内の未変更fileを拒否する懸念。create_skill_workspaceが通常package領域だけを抽出し、evalsを含めないため、その前提の経路は成立しない。
- **撤回D02:** WCAG close-reportのunresolved判定が逆という懸念。childはpending-persistenceを返し、ownerが実行結果の保存・CAS / readbackを経てcompleteへ進める設計。caller / calleeとtestで整合する。
- **撤回D03:** Regressionが一部required routeだけでTCをexecutedにする懸念。project_activityは全routeのactual startを確認し、result finalizationも別に扱っている。
- **現状維持D04:** native CASのない保存先をblockすること、Skill-local runtime 9コピー、有限fixed browser probes。配布・権限・決定論的処理という既存要件がある。共通DB・汎用frameworkへ置換する根拠はない。
- **未指摘D05:** 複数workflowのsemantic検証重複。コストや障害の具体的証拠がなく、独立workflowで失敗も検出できるため、単なる重複を欠陥としない。
- **統合M01 → N02:** 共通runnerのoutput.md / stderr書込みとQTSのfinal-message書込みは、untrusted outputをホストが追従する同根の問題。別件へ水増ししない。
- **統合M02 → N01:** 承認の内容binding不足と、変異後も古いartifact manifestをfixture fingerprintへ使う問題は、承認対象の実体を固定できない症状としてまとめる。
- **環境差D06:** skills-refの初回実行はWindows既定cp932で22件decode error。PYTHONUTF8=1で同じ既存toolの個別validateが22/22成功。repositoryのSkill不良や新規依存不足とは扱わない。

## 4. 初回P1・P2の再検証

以下の判定では、実在、発生条件、caller / callee、既存防御、test検出力、具体的影響、修正の必要性、最小変更、重複、優先度を確認した。詳細な根拠・改善範囲・検証は§5へ集約する。

| 初回ID | 最終状態 / 優先度       | 再検証結果・変更理由                                                                                                                                                                                    |
| ------ | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F01    | 確定、P1維持            | verified caseの和集合を取るため、関連正常例のmismatch / 未検証を無視する。実関数→failure選択で再現。Judge側のcase単位判定では解決しない。N01とは「承認対象binding」と「関連fixture集約」の段階が異なる  |
| F02    | 確定、P1維持            | analysis schemaと実gateは未解消alternative_causesを除外しない。原成果物内容もworkspaceにない。completion側のSkill使用確認では修正開始を防げない。prompt改訂だけでなく開始gateの最小補強が必要           |
| F03    | 確定、P1維持            | 同一QTSで1→3・使用観測ありなら、独立case / 通常契約test結果なしでimprovement_demonstratedになる。既存compareは条件比較であり独立回帰の代替ではない                                                      |
| F04    | 確定、**P2へ変更**      | fixed QTS・Judge結果必須のためdeterministic-only入口がない。ただし危険な誤昇格ではなく、未受入の改善機能がPlan所定の独立案件を処理できない不足。誤許可するF01–F03より後に置く                           |
| F05    | **撤回**、件数から除外  | 6 errorsは再現したが、Agent runnerのREADMEはLinux Dockerを前提とする。Windows全suite成功の明示契約はなく、Windows CIもCodex開発harness用。Linux要件を満たさない実行の失敗だけで製品欠陥とする根拠は不足 |
| F06    | 確定、P2維持、scope縮小 | PR #17本文のremote head / ahead / CIなしはAPIと矛盾し、不要なpush / credential対応へ誘導する。UI Planの古い日付の記録や「未完了の場合」という条件文自体は誤りとしない                                   |

F05の6 errorsは、Linux hostチェック3件、shebang fake dockerをWindowsが実行できないWinError 193が1件、mock済みsubprocessより前のos.getuid / getgid不足2件。Linux上の現在CIはsuccessである。Windowsでもprotocol testを走らせたい場合はOS境界mockや明示skipが小さい選択肢だが、今回は必須改善に数えず、productionのLinuxチェックも弱めない。初回F05の「blanket skipせず修正」という必須提案は撤回する。

F01–F03はN05のため現在の通常Judge検証経路で到達できない場合がある。それでもN05修正後に現れる誤許可を残してよいことにはならない。現時点で実Skillが誤修正された事実は確認していない。

## 5. 確定した改善点

P0は0件。優先度はP1＝信頼境界・誤許可または主要評価機能の重大な停止、P2＝限定的な不整合・不足・運用誤誘導として評価した。全項目の状態は「確定」。静的な処理経路確認と合成データによる動的診断、実環境受入は以下で区別する。見積りは調査時の粗い修正・局所検証工数であり、外部環境構築・fixture人間承認待ちを含まない。

| ID  | 優先度 | 問題                                                          | 根拠の種類                                                           |
| --- | ------ | ------------------------------------------------------------- | -------------------------------------------------------------------- |
| N02 | P1     | Agentが作るsymlinkをホストの結果書込みが追従する              | caller順序・write API・既存検査位置の静的確認。Linux侵害実行は未実施 |
| N05 | P1     | Judge fixture判定がnormalizerにないevaluableを参照して停止    | 実_run_judge_case / 実normalizer / 実_expected_matchesで3条件再現    |
| N01 | P1     | fixture承認とfingerprintが実際の成果物内容に固定されない      | 実approval parser、実fixture変異の局所再現                           |
| F01 | P1     | criterion検証済み判定が関連fixtureの失敗・不足を無視する      | 実verification map → failure selectorで再現                          |
| F02 | P1     | 未解消の代替原因・原成果物不在でも修正開始gateを通る          | 実schema検証とAST抽出した実gateを評価                                |
| F03 | P1     | 独立回帰・通常契約testなしで改善実証へ昇格する                | 実assessmentを境界mock付きで評価                                     |
| N06 | P2     | 未検証Judge結果を共通runnerがKeyErrorにし、理由を保存できない | 実_render_gradeとcallerの必須keyアクセスを再現                       |
| N03 | P2     | 探索の結果不明attempt後に状態未確認の再試行を許す             | 実record_attempt → authorize_operationで再現                         |
| N04 | P2     | 存在しないRegression履歴rootを完全scanとして返す              | 実scan_activity_filesで再現                                          |
| F04 | P2     | deterministic-onlyの独立改善経路が未接続                      | CLI / 選択 / 保存結果の静的追跡                                      |
| F06 | P2     | PR #17の現在状態の案内が実metadata・CIと矛盾する              | 今回のGitHub API取得と本文比較                                       |

### N02 — P1: Agent出力内symlinkをホストの書込みが追従する

**位置・経路:** [run.py](../../scripts/skills/evals/agent/run.py) 608行・665行、[qa_training_store.py](../../scripts/skills/evals/agent/qa_training_store.py) 966行・1118行。verify_agent_docker_commandでAgentにattempt outputだけのwrite bindを許した後、ホストがその中のagent.stderr.log / output.md / final-message.mdへPath.write_textする。開始前のprepare_run_output_rootやlauncherのランダムな.codex-final-*検査は、Agentが後から作る別名fileの検査にはならない。

**条件・具体的影響:** LinuxのAgentがwrite可能なoutput内に、ホスト上ではoutput外へ解決される相対または絶対symlinkを作って終了すると、ホストのwrite_textがリンク先をtruncate / 上書きする。container内ではその外部pathへのwriteが拒否されても、終了後のホスト権限で別経路が成立する。影響はホストprocessが書けるfile。QTSのworkspace integrity確認と安全なoutput copyはこの書込みの後なので、事後の拒否では外部fileの変更を防げない。Main Plan 413–414・554・915行のoutput-only / symlink拒否契約に反する。

**既存対策・検証限界:** QTSの_copy_safe_agent_outputやartifact index検査はsymlinkを拒否するが、対象と時点が異なる。testはartifact参照の欠落・不正pathや保存copyを扱い、ホストが先に書くfileをAgentがsymlinkへ置換するnegative caseがない。今回の一時sentinelでのsymlink作成probeはWindows権限エラー1314で実行不能。権限変更や迂回はしていない。確定根拠はコード上の攻撃経路であり、Linuxでのexploit完遂を検証済みとはしない。

**推奨・最小範囲:** 両runnerでAgent由来directoryへのホスト結果書込みを安全化する。既存atomic_write_text等の再利用を検討し、Agent終了・cleanup確認後もfile / 親pathを安全に扱い、linkを追従しない。Evaluator-owned結果とuntrusted出力の分離も選択肢だが、汎用sandbox新設は不要。

**比較・リスク・検証:** 現状維持は実装費ゼロだがoutput-only境界を満たせない。局所修正は概ね0.5–1.5人日。正常fileや既存output保存契約を壊すリスクがあるため、Linuxの使い捨て一時sentinelでoutput.md・stderr・QTS final-message各経路、dangling / 相対link、正常file、timeout後を確認する。実sourceや秘密fileを攻撃対象にしない。

### N05 — P1: 実normalizer出力をJudge fixture判定へ渡すと必ずKeyErrorになる

**位置・経路:** [judge_validation.py](../../scripts/skills/evals/agent/judge_validation.py) 301–311・381–387・577–578行、[semantic/result.py](../../scripts/skills/evals/semantic/result.py) 120–131行。normalize_judge_responseのcriterion出力はid / title / critical / rating / status / reason / evidenceであり、raw入力のevaluableは残さない。_expected_matchesは出力にitem["evaluable"]があると仮定している。

**再現・影響:** subprocess境界だけをmockし、実_run_judge_caseに妥当なJSONを渡した。rating 3、rating 1、evaluable=false / rating=nullのすべてで実normalizerは成功し、その後の実_expected_matchesがKeyError: 'evaluable'。run_validationではこの場所の例外をcase結果へ変換せず、CLIがexit 2となり、独立Judge検証を完了できない。

**既存testの見逃し:** test_judge_validation.py 247–256行のfake_judgeはnormalizedへevaluableを手で入れるため、実normalizerとの接続不整合を隠す。共有semantic testが成功してもこのcallerの仮定は検証しない。QTSのrun_independent_judgesはrating is not Noneからraw shapeへ戻しており、同じ例外経路ではない。

**推奨・比較・検証:** normalizerを全体変更するより、このconsumerがnormalizedのrating / status契約を使う修正が小さい。jitter / proposalのevaluable参照も同じ契約へ揃える。0.25–0.5人日程度。現状維持では正常応答を受けても検証不能。実normalizerを省略しないnormal / violation / not_evaluable / invalid responseの接続testと、fixture単位のエラー保存を確認する。

### N01 — P1: fixture承認が対象成果物の内容に結び付かない

**位置・経路:** [judge_validation.py](../../scripts/skills/evals/agent/judge_validation.py) 76–128・499–554・621–675行。_approval_mapはdataset_revisionとcase ID、reviewer、日時、reference pathの引用だけを受ける。実fixtureはその都度選ばれたbaseline_outputをcopy・変異して作るが、その成果物hash・fixture fingerprint・target / reference fingerprintを承認入力と照合しない。

**再現・影響:** 同parserはartifact / reference hashを持たない合成承認を受理した。実_prepare_fixtureでmajor-violation-006を作るとartifact-04.mdの内容hashは変わったが、コピーされたartifact-manifest.jsonは元と同じまま。そのmanifest hashとdefinitionだけでfixture_fingerprintを作るため、実際にJudgeへ渡す内容の固定にも使えない。別baselineの不良成果物へ「正常例」の古い承認を流用し、Judgeが期待ratingを返しただけでverifiedへ進む条件がある。

**仕様・既存test:** Judge Plan _04の11・18・22・37行は、対象成果物・期待値・仕様path / fingerprint・確認履歴を特定revisionへ固定する。現在の承認待ち維持やreference path制限は必要な防御だが、内容bindingを代替しない。既存testはapproved / unapprovedだけで、承認後のbaseline / fixture内容変更を検査していない。

**推奨・比較・検証:** 変異後の実artifact・prompt根拠に結び付くfingerprintを再計算し、承認にfixture / 規範 / 期待値の固定bindingを持たせ照合する。新DBや自動承認は不要。現状維持では人間が未確認の内容まで承認済みになる。1–2人日程度、既存承認fileの再確認が必要になる。別baseline、内容だけ変更、古いmanifest、期待値 / 規範変更、同一内容再実行をnegative / replay testで確認する。

### F01 — P1: criterionのverified判定が関連fixtureを集約していない

**位置・経路:** [improve.py](../../scripts/skills/evals/agent/improve.py) 74–88・151–180・524行。_judge_verification_mapはstatus=verifiedのcaseだけからcriterionを和集合で集め、_stable_failuresはそのmembershipを修正許可へ使う。

**再現・影響:** normal-artifactsがlabel_or_judge_mismatch、major-violation-006だけverifiedという入力でQTS-SEM-006はverifiedとなり、2 attemptのrating 1が修正対象へ選ばれた。必要fixtureの未処理・不足でも同様。case単位のjitter確認や全体statusがreview_pendingでも防げない。現在catalogにはQTS-SEM-008の専用違反例もなく、正常例だけで十分とする設計にはできない。

**仕様・最小修正:** Judge Plan _04 37–40行は正常例の誤検出、重大違反の見逃し、揺れ、不足をcriterion別に確認する。catalog / 必要な事例種別からcriterion別の充足条件を作り、関連caseの全状態と不足を確認する。未検証criterionだけを止める。N01の正しい承認bindingが前提であり、別の修正箇所である。

**比較・検証:** 現状維持では不適切なJudgeからSkill変更を許可する。0.5–1.5人日程度。全体一律blockにして独立criterionを止める回帰に注意し、正常mismatch・違反mismatch・pending・missing・jitter・独立criterion継続を実map→selectorで確認する。既存testはverified mapを直接与えるため関連fixture集約を検出しない。

### F02 — P1: 原成果物と代替原因を確認せず修正開始を許す

**位置・経路:** [improve.py](../../scripts/skills/evals/agent/improve.py) 202–242・612–651・748–760行。analysis workspaceはSkillだけを配置し、prompt_evidenceのartifactsはpath / hashの組。原成果物本文と必要な公開仕様の本文を提供しない。_validate_analysisはalternative_causesの型だけを確認し、実gateはclassification・許可Skill・repair_paths・path/hash文字列を確認する。

**再現・影響:** 「AgentがSkillを読んだ / 従ったか未解消」というalternative_causesを持つJSONがschemaを通り、ASTから抽出した実mechanically_allowed式もtrueとなった。原artifactや該当Skill記述を突き合わせず、Agent / input / evaluator起因をSkillへ帰属する変更を始められる。最終_assess_improvementの使用観測gateは修正開始より後である。

**既存対策・推奨:** 2 attempt再現、runtime / artifact検査、単一Skill allowlistは維持する。安全化した原成果物と必要最小限の公開仕様をread-onlyに供給し、問題のsource箇所と実証拠の対応を確認する。未解消代替原因・使用未確認なら開始せずreview_pending。固定Reference・expected・独立回帰の内容を分析Agentへ渡す修正にはしない。

**比較・検証:** 現状維持は誤原因への自動変更を許す。1–3人日程度、証拠の安全化・情報分離を壊すリスクがある。原成果物を読めない、hashだけの根拠、未解消代替原因、Skill未使用、正しい単一Skill原因の各ケースで開始可否を確認する。既存testはschema→実開始gateの組合せを覆っていない。

### F03 — P1: 独立回帰なしでimprovement_demonstratedへ昇格する

**位置・経路:** [improve.py](../../scripts/skills/evals/agent/improve.py) 351–430・1049–1105・1130–1133行。同じQTSのrepeat 2と既存compare_runsを使い、target rating改善・同caseのcritical悪化なし・Skill使用観測だけで成功を判定する。未使用の別Eval Inputや、変更Skillの通常deterministic / semantic / runtime / portability test結果を受け取らない。

**再現・影響:** load / attempt境界をmockし、実_assess_improvementへbaseline 1→candidate 3を2組、使用observed、比較条件一致として渡すとimprovement_demonstrated=true。独立caseや通常契約testの結果は一つも入力していない。固定QTSへの過適合や別case・配布契約の回帰を検出せず検証済み修正と扱える。

**仕様・推奨:** 改善Plan _03 131–136・159–161行どおり、候補生成前に既存別case / fingerprintを固定し、その入力・期待値・事例別結果を修正Agentへ返さず評価する。関連既存testも接続し、「局所前進」と「独立回帰済み候補」を別状態にする。新規大型benchmarkは不要。

**比較・検証:** 現状維持では汎用Skillの改善を実証できない。2–4人日程度と別case実Agent評価費用。test不足・独立case不足はreview_pendingへ残すため、成功率が下がるのは正しい挙動である。同QTSだけ改善、通常test失敗、別caseの既存fail / 新規回帰、情報漏えい、条件違い、全条件成立を検査する。

### N06 — P2: 未検証Judge結果の返却shapeと保存側が整合しない

**位置・経路:** [run.py](../../scripts/skills/evals/agent/run.py) 270–291・682–707行。Codex Judgeのsidecar欠落・不正、tool event等でevidence_unverifiedとなると、_render_gradeはstatus=needs_review / reasonとjudge_runsを返し、grade keyを持たない。一方callerは直後にgrade["grade"]を必須として保存し、その後でjudge_runsをattemptへ設定する。

**再現・影響:** 実_render_gradeを外部実行・capture境界だけmockして呼ぶと、needs_review / judge_evidence_unverifiedとJudge記録1件を返す。実callerと同じkeyアクセスはKeyError: 'grade'。例外handlerがattemptをexecution errorへ変え、保存すべきJudge記録・原因がattemptに結び付かない。合否を誤PASSにはしないが、証拠不足とrunner故障を混同して調査を困難にする。

**推奨・比較・検証:** 非採点結果にも共通の返却shapeを定義するかgradeをoptionalとして保存し、judge_runsとreasonを採点有無に関係なく安全に保存する。N05のevaluableとは別のcaller契約であり、同時に正常化schemaを拡張する必要はない。0.25–0.5人日程度。現状維持では未検証理由がKeyErrorへ潰れる。実callerまで通すsidecar欠落 / 不正 / tool検出 / 正常Judge testで、needs_reviewと安全な記録が保持されることを確認する。

### N03 — P2: 結果不明操作の再試行を状態未確認のまま許可する

**位置・経路:** [exploratory_runtime.py](../../skills/exploratory-testing/scripts/exploratory_runtime.py) 123–160・293–317行、[対応test](../../tests/skills/evals/deterministic/test_qa_artifact_graph_skills.py) 1437–1483行。record_attemptはoutcome=unknownのときretry_without_state_check=trueを返す。authorize_operationはuncertain_previous_attemptを回数へ足すだけで、状態確認前の副作用retryを止めない。

**再現・影響:** 許可操作invalidate_session、最大3回でunknownの1回目を記録するとtrue。prior=1・uncertain=trueでauthorize_operationを呼ぶとallowed / attempt number 3となる。Skill本文16行とguidanceの「結果不明後はsource stateを確認してから再操作」に反する。helper自身は実対象を操作しないが、その許可結果を利用するAgentが同じ副作用を繰り返す条件がある。

**既存test・推奨:** 上限1のtestは回数超過を検出する一方、unknown時のtrueをassertして誤った契約を固定している。上限計算は維持し、未確認の副作用attemptがある場合は状態再確認が必要というblock / explicit decisionを返す。曖昧な返却fieldの意味も揃える。自動retry frameworkは不要。

**比較・検証:** 現状維持では書面の停止条件と許可helperが逆になる。0.25–0.5人日程度。read-onlyな状態確認まで止めないようにし、最大回数に余裕あり / なし、unknown、確認後再開、非副作用操作、回数二重消費防止をtestする。

### N04 — P2: 存在しないRegression履歴rootを完全列挙と返す

**位置・経路:** [regression_runtime.py](../../skills/regression-testing/scripts/regression_runtime.py) 830行以降のscan_activity_files。Path(root).rglobを使い、root自体の存在・directory性を確認しない。例外にならない空iteratorではcomplete=listing_complete（既定true）となる。

**再現・影響:** 存在しないdocs/reports/__review_nonexistent_activity_root__を実関数へ渡すとactivity_refs=[] / complete=true / unresolved=[]。root typo・未mount等で履歴が取得できない状況を「完全に検索したが0件」と誤報告する。guidanceのStorage and historyはscan error / truncationをcomplete=falseとする。qa-workflowのiterdir、Knowledgeのscandirによるroot失敗処理では同じ再現にならない。

**既存test・最小修正:** 既存testは正常JSON列挙とlisting_complete=falseだけ。まずrootのdirectory性を確認し、実際の列挙失敗をincompleteへ返す既存の方針へ合わせる。OSにより走査中の例外が抑制される可能性も確認し、完全性を主張できる列挙方法を使う。新index / DBは不要。

**比較・検証:** 現状維持は誤った「履歴なし」による再開判断を残す。0.25–0.5人日程度。既存の正常な空directoryはcomplete=trueを維持し、不存在・file指定・アクセス失敗・途中失敗・明示truncationをfalseと区別する。権限変更で失敗を迂回せず、再現不能な権限caseはmockと実OS検査を分ける。

### F04 — P2: deterministic-only改善案件を継続する入口がない

**位置・経路:** [improve.py](../../scripts/skills/evals/agent/improve.py) 91–180・500–524・1146行。fixed QTS target、normalized Judge criteria、Judge validation resultを必須とし、_CRITERION_SKILLSのQTS semantic critical failureだけを選ぶ。共通deterministic runnerのgrade.jsonを原因根拠にするadapterはない。

**仕様・影響:** 改善Plan _03 117・142・155・212行は、固定grader / expected / 機械的根拠だけで独立成立する案件をJudge未検証で止めない。現在は実行可能な機械根拠があっても、この経路を使えない。全runtime failureを修正対象へ解放するという意味ではない。

**推奨・比較・検証:** existing graderを再利用し、判定根拠種別ごとの入力adapter / gateを接続する。Evaluator / env / 証拠破損は引き続きblockする。2–4人日程度。現状維持はこの機能を未実装と明示して手動分析する選択肢だが、Plan受入完了は主張できない。Judge承認なしの正当なdeterministic案件、混合根拠の片方未検証、grader / envエラー、独立案件継続を確認する。誤許可のP1修正を先行する。

### F06 — P2: PR #17の現在状態がhead・CIと矛盾する

**位置・根拠:** [PR #17本文](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)の「状態」「GitHub / 検証」「残対応」はremote 691a34a / local 03703f5 ahead 1、現行headは未pushでCIなしと案内する。今回APIはhead 03703f5と同SHAの5 successを返した。

**影響・推奨:** 再開者が不要なcredential / push作業や、既存CIの再調査へ進む。現在状態の冒頭に確認日、実head、CI、live未受入を短く分けて記載し、当時の失敗記録は履歴として残すのが最小。全Planを現在状態へ書換える必要はない。本レビューでは外部更新しない。

**比較・検証:** 現状維持の費用はゼロだが再開判断の誤誘導が残る。更新は0.25人日未満。履歴を消す、mergedをlive受入済みとするリスクを避け、metadata / CIリンクと本文の現在要約を照合する。初回が挙げたUI Main Plan末尾は条件付き未完了規則も含むため、それ自体を現在の誤断定とはしない。

## 6. 今回実行した検証と意味

各validationは個別command・exit codeで判定した。unittestは既存.venvのpython.exe -Bを使用。既存testが一時fixtureや一時Git repository / bare remoteを作ることはあるが、対象repositoryのbranch / indexは変更しない。55件のtestが表示したbranch切替メッセージは一時fixtureのものである。

| 今回実行した入口                                                                | 結果                                                                                                                                         |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| unittest discover -s tests/skills/runtime -p 'test_*.py' -q                     | 371件、OK、2 SKIP、138.118秒                                                                                                                 |
| unittest discover -s tests/skills/evals/deterministic -p 'test_*.py' -q         | 290件、OK、77.929秒                                                                                                                          |
| unittest discover -s scripts/skills/evals/deterministic/tests -p 'test_*.py' -q | 13件、OK                                                                                                                                     |
| scripts/skills/evals/semantic/validate.py                                       | 22 Skill / 163 case、exit 0                                                                                                                  |
| unittest discover -s scripts/skills/evals/semantic/tests -p 'test_*.py' -q      | 27件、OK、2 SKIP                                                                                                                             |
| unittest discover -s tests/skills/evals/semantic -p 'test_*.py' -q              | 13件、OK、1 SKIP                                                                                                                             |
| unittest discover -s tests/skills/evals/trigger -p 'test_*.py' -q               | 1件、OK。native trigger評価ではない                                                                                                          |
| unittest discover -s scripts/skills/evals/agent/tests -p 'test_*.py' -q         | 44件、exit 1、6 errors。Linux前提外の内訳は§4                                                                                                |
| unittest discover -s tests/skills/evals/agent -p 'test_*.py' -q                 | 4件、OK                                                                                                                                      |
| unittest discover -s tests/codex -p 'test_*.py' -q                              | 55件、OK、169.639秒。実検査CLI 0.162.0-alpha.17.2                                                                                            |
| unittest discover -s tests -p 'test_format_tracked.py' -q                       | 10件、OK                                                                                                                                     |
| unittest discover -s tests -p 'test_ci_patch_whitespace.py' -q                  | 3件、OK。一時fixtureのLF / CRLF警告あり                                                                                                      |
| scripts/format_tracked.py check                                                 | exit 0。Ruff check / 235 Python file format / dprint check成功。既存native dprintのdirectoryと.venv/ScriptsをcommandのPATHへ指定             |
| skills-ref validate（各22 Skill）                                               | 初回cp932で22件失敗。PYTHONUTF8=1を設定した別の再実行で各return code 0、22/22成功。installなし                                               |
| node --check .codex/hooks/pre_tool_use_policy.mjs                               | exit 0                                                                                                                                       |
| runtime_contract.py内容hash                                                     | 9コピー、unique hash 1                                                                                                                       |
| 合成データ診断                                                                  | F01 selector、F02実gate、F03実assessment、N01承認 / fixture変異、N03二つの実helper、N04実scan、N05実normalizer接続、N06実grade返却を個別確認 |

実関数診断は外部Agent / Judgeを呼んでいない。N05では妥当なJudge JSONを合成し、実normalizerを通した。F02は実gate式をASTから抽出して評価し、F03はI/O境界をmockした。これらをlive修正成功や統計的改善実証として報告しない。

検査位置検索をまとめた1 commandに引用符不整合があり、PreToolUseがshell parse時に拒否した。拒否されたcommandは実行されていない。判定に必要な独立test・status確認はそれぞれ安全な別commandで実行し、拒否を解除・無効化していない。これをfresh runtimeの安全性受入の証拠へ拡張しない。

## 7. 未確認事項

未確認は **7項目**。確定指摘の実環境での検証不足もここへ関連付けるが、同じ問題を新しい欠陥として重複計上しない。

| ID  | 未確認対象・理由                                                                              | 必要な証拠・今後の必要性                                                                                                                                    |
| --- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| U01 | 現行HEADの共通runner / QTS実Agent受入。今回の禁止範囲でありPR #17の過去結果も未達             | 許可されたLinux環境で実Skill読取・実行、canonical成果物、runtime replay、2 attemptの保存。live受入時に必要                                                  |
| U02 | 承認済みJudge fixtureでの独立検証と、実Skill欠陥からの改善実証。approved 0、N01 / N05等が前提 | 人間等の独立承認binding、正常 / 違反・独立split、同条件baseline / candidate、未使用caseと関連test。改善受入時に必要                                         |
| U03 | N02のLinux実行negative testと、実Agent shellに対する認証・egress境界の総合受入                | 一時sentinelでのpost-run link拒否、credential read-denial、env / network等の実効証拠。Windows symlink probeは1314。既存Codespaces隔離調査は繰り返していない |
| U04 | fresh embedded / non-shared runtimeでDirect / nested Code ModeのPreToolUse・execpolicy受入    | codex --no-daemon --strict-configのfresh sessionで対象modeごとのrequired capability。55 contract成功と現在toolのHook拒否だけでは代替しない                  |
| U05 | 全Skillのnative trigger精度、163 semantic caseの現行実Agent品質・安定性                       | 現行source / input / runtimeを固定した対象別評価。488 queryの構造・163 caseの検証成功はその代わりにならない。必要な利用範囲から段階実施                     |
| U06 | 過去41 smoke・36 criteriaの全raw artifact連鎖と、現行sourceへ証拠を再利用できる範囲           | 保存manifestだけでなく元成果物 / fingerprint / sourceとの照合。今回再実行とはしない。過去証拠を正式受入へ再利用する場合に必要                               |
| U07 | UI / WCAGの現行live browser・AT・手動手順・外部保存providerの実案件受入                       | 対象・環境・権限・evidenceを固定したowner観測、cleanup、CAS / readback。単体testだけで製品適合・多host保存を保証しない。実案件の範囲で必要                  |

重要範囲のコード・仕様・testを未確認のまま放置したものと、外部環境がないため実行受入を主張できないものを区別した。後者を理由に今回の調査を無期限に続けない。

## 8. 改善の優先順位と依存関係

1. **N02:** live Agentを再開する前に、両runnerのホスト書込み境界を閉じる。コード修正とLinux negative testを行い、既存隔離を弱めない。
2. **N05・N06:** real normalizer / 非採点結果とcallerの接続を直す。外部LLMなしの接続testで確認でき、後続の承認・Judge評価を調査可能にする。
3. **N01 → F01:** 承認対象の実体を固定してから、必要fixtureのcriterion別集約を正す。0 approvedを便宜的に承認へ変えず、独立criterionだけ継続可能にする。
4. **F02 → F03:** 原成果物に基づく原因確認と修正開始gateを閉じ、未使用case・通常test・配布契約を含む完了gateへ接続する。独立回帰用入力は候補生成前に固定する。
5. **N03・N04:** 独立した小さい修正として並行可能な順序で扱える。探索の状態確認とRegression履歴の完全性を先に保証する。ここで並行可能とは今後の実装順序の提案であり、今回Agentを委譲したという意味ではない。
6. **F04:** 共通の安全gateを整えた後、既存graderによるdeterministic-only adapterを接続する。Judge未検証を理由に独立機械案件まで止めない。
7. **F06:** PR再開時の短い現在状態要約を更新する。修正着手前に行えば誤ったcredential / push調査を減らせるため、P2でも実務上は早期に行ってよい。
8. **U01–U07の必要範囲:** 修正後に承認済みfixture・隔離済み環境を使う限定live受入へ進む。高コスト全量評価や別環境の構築は、このレポートから暗黙に許可された作業ではない。

現状維持が妥当な領域は、Skillごとの責務分離、9コピーの配布契約、機械処理と意味判断の分離、native capability不足時のblock、既存SQLiteの単一host限定、E2E raw factの保持、有限browser probeと秘密URLの非保存、既存helper / 標準機能優先である。全体rewrite、GraphDB、新規scheduler、汎用抽象化、依存の追加を推奨しない。

## 9. 最終レビュー結果

- 実施5周。初回P1 / P2を全件再検証し、6段階の全体確認、原因 / 逆方向 / 仕様 / test / 簡素化の観点で関連経路を確認した。
- 確定11件（P0 0 / P1 6 / P2 5）、未確認7項目。初回から追加6件、撤回1件、初回IDの統合0件。F04はP2へ変更、F06は根拠範囲を縮小。同根症状M01・M02はN02・N01へ内部統合した。
- 第3周の新規発見後に終了判定をリセットし、第4・第5周の異なる全体レビューで新規根拠付き指摘0件が連続した。指定終了条件を満たしたと判断する。
- 「完全に問題がない」「すべて実環境で受入済み」とは主張しない。静的確認・合成診断・単体 / 統合test・保存証拠・live未確認の境界を維持する。
- 次に対応すべき最優先はN02。評価基盤の再開はN05・N06、N01・F01、F02・F03の依存順を守る。
- v00のSHA-256は43628ef8c6d88d6bf561b3df447cd89b63afb2fb89eaeb22fb1726af5c58781d。内容を維持する。
- 最終確認ではbranch / HEADは開始時と同じ、tracked差分・staged差分・git diff --checkはいずれも個別にexit 0。statusは開始時から存在するv00と新規v01の未追跡2件だけ。v00のhashも一致した。今回作成したのはv01だけである。
- 本ファイルを対象としたdprint checkもexit 0。UTF-8、9節、確定11件の件数、相対リンク先、末尾空白・conflict markerなしを別途確認した。
