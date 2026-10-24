# 実Agent評価ランナー

このランナーは、指定した`qa-workflow-skills` Git revisionのSkill packageを一時領域へ展開し、実Agentで生成した結果を固定Evaluatorの既存grader / Judgeで評価します。評価結果と機械判定をattempt単位で保存します。既存Skillの通常実行経路やSkill packageの配置規則は変更しません。

Codex Agent / Judge / RepairはWSL2 Ubuntuの二重bubblewrap方式で起動します。実行profile、実効command、run結果は秘密情報を含めず、run単位の`.agent-eval-runs/`へ置きます。このdirectoryはGit管理対象外です。通常CIは外部LLMを呼ばず、fake Agent / Judgeの契約テストだけを実行します。QTSのCodexを使わないdeterministic verifierは既存の固定Docker image契約を維持します。

## CLI一覧

| Module                                       | 用途                                                                                  |
| -------------------------------------------- | ------------------------------------------------------------------------------------- |
| scripts.skills.evals.agent.run               | deterministic / semantic case、Skill単位、明示されたall batch                         |
| scripts.skills.evals.agent.isolation_probe   | WSL2、outer/inner bubblewrap、固定binary、mount、namespace、FD、network、evidence検証 |
| scripts.skills.evals.agent.qa_training_store | 固定qa-training-store revisionのCheckout / Payment workflow評価                       |
| scripts.skills.evals.agent.judge_validation  | 正常例・固定違反例でのJudge独立検証とレビュー用候補比較                               |
| scripts.skills.evals.agent.compare           | 条件が一致するrun間のattempt / criterion比較                                          |
| scripts.skills.evals.agent.improve           | 保存済みrunの分析、許可path限定修正、同条件での再評価                                 |

## 実行前提

- 評価ランナー本体はWSL2 Ubuntu内のclean Linux checkoutから起動します。Windows Python、Windows開発checkout、/mnt/c上のtarget checkoutは正式実行に使用しません。
- Python 3.11と既存deterministic validator用PyYAML 6.0.3、Codex CLI Linux x64 0.163.0、そのpackageに同梱されたbwrap、最小runtimeとCA bundleを使います。追加system packageや管理者権限は避けます。
- Codex packageは公開npm tarball https://registry.npmjs.org/@openai/codex/-/codex-0.163.0-linux-x64.tgz を使い、package name/version `@openai/codex@0.163.0-linux-x64`とSHA-512を照合します。既知tarball SHA-512は `bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3` です。launcherは実行時のCLI version、CLI binary SHA-256、同梱bwrap SHA-256も照合します。system bwrapへ暗黙に切り替えません。
- Agent、Judge、Repairは、tmpfs rootに必要最小限のruntime、sanitized workspace、attempt output、一時CODEX_HOMEだけをmountするouter bubblewrap内でCodexを起動し、Codex自身のLinux sandboxを内側で有効にします。host root、host home、Evaluator checkout、元target、Windows filesystem、Docker socket、他attemptのpathはAgent/Judgeから見えません。
- Agent/Judge/Repairごとに独立したprocess、outer namespace、workspace、cwd、一時CODEX_HOMEを作ります。JudgeへAgent workspaceをmountしません。Judge入力はstdinのみ、shell/MCP/追加Skill roots/web searchは無効にし、JSONLのtool eventがあればjudge_unverifiedにします。raw JSONLは保存しません。
- outer networkはCodex親processのモデルAPI通信に必要なため維持します。inner Codex sandboxのshellはTCP/DNS/AF_UNIX/WSL interop/localhostを使えないよう設定し、正式launcherからnegative testします。TEST-NET等の単一接続失敗を全面egress遮断の根拠にしません。
- Codex shellは合成認証markerとAPI keyを読めた過去実測があります。一時CODEX_HOME方式では実認証も可視になる可能性があるため残留リスクとして扱います。実認証やモデルAPI送信は、隔離合成検証後に別途承認が確認できるまで行いません。
- Codex CLI固有設定は固定profileから検証し、MCP、外部指示、global config、追加Skill、web検索を無効にします。秘密値・生認証情報・秘密hashをargv、environment、profile、provenance、raw JSONLへ保存しません。
- Codex source / 固定targetの既存ファイル・directoryはouter mountで個別にread-only bindします。Codex workspace-writeがsandbox準備で必要とするattempt-local workspace root、`.git`、`.codex`だけは一時領域として分離し、許可outputとRepair対象Skill以外の既存sourceは変更できません。実行前後manifestを比較し、単にworkspace全体をwrite可能にする方式は不適合です。
- 通常CIは外部LLM、実認証、live Codex execを呼びません。fake Agent/Judge contract testsを実行します。実Codex sandbox smokeはWSL2のformal launcher経由で無認証のsynthetic inputだけに実行します。

実効profileはJSON schema version 2です。Agent / Judge model、timeout、reasoning、sandbox、approval、network、tools、MCP、Skill rootsに加え、runtimeにはWSL2実行mode、Codex package source/version/SHA-512、Codex binaryとbwrapのSHA-256、outer/inner argv・mount・network fingerprint、probe version、evidence fingerprint、依存versionを記録します。secret自体は記録しません。旧Docker profileは読み取り用に保持しますが、新方式と直接比較できません。

Profile verificationは同じEvaluator revision、profile、Agent/Judge/Repair mode、binary digest、実効argv・mount/network、probe versionに結び付くisolation.jsonを要求します。evidence欠落、旧Docker evidence、別mode evidence、fingerprint不一致、必須negative test未確認の場合はisolation_unverifiedとして起動を拒否します。

launcherは既存executor.run_commandを使い、shell=False、固定argv、close_fds=True、未許可pass_fdsなし、stdin/stdout/stderr契約、timeout、POSIX process group cleanup、safe diagnosticsと一時領域cleanupを維持します。失敗時はfail-closedです。

## 共通case実行

WSL2 clean checkoutからprofileを指定し、固定Skill revisionを実行します。Codex用launcherや外側bubblewrap argvを利用者が自由入力する必要はありません。profileに指定された固定実行modeだけが利用できます。

```bash
python -m scripts.skills.evals.agent.isolation_probe \
  --profile .agent-eval-runs/config/profile.json \
  --output-root .agent-eval-runs/isolation

python -m scripts.skills.evals.agent.run \
  --suite deterministic \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --skill-revision <40文字のSkill Git SHA> \
  --execution-profile .agent-eval-runs/config/profile.json \
  --output-root .agent-eval-runs/TC-OUT-001 \
  --agent-name codex \
  --agent-model <model名>
```

起動前にprofileとfresh isolation evidenceを照合します。合成security testが成立しない限りCodex exec、実Agent/Judge評価へ進めません。正式方式の認証可視性は残留リスクであり、今回の方式移行承認だけを実認証承認として扱いません。

受入smoke対象はTC-OUT-001、TCN-OUT-001、TC-SEM-001、WF-SEM-003です。ケースを個別実行します。Semantic caseはJudgeを別process・別outer bubblewrapで起動し、既存semantic result normalizerで判定します。--skill allは明示時だけ使います。

## 固定qa-training-store統合評価

この評価はWSL2内のclean target checkoutで`qa-training-store@84ce165493649550832731a60cf436f8ae29c56b`のsource treeを読み取り、Checkout / Payment Web範囲の固定scenarioを最低2 attemptで実行します。target repoへcheckout、commitその他のGit mutationを行いません。Codex Agent/JudgeだけをWSL2二重bubblewrapで起動します。Codexを起動しないproduction verifier capture/replayは固定Docker verifier imageと既存`--network none`契約を維持します。

```bash
python -m scripts.skills.evals.agent.qa_training_store \
  --target-root /home/<user>/src/qa-training-store \
  --skill-revision <40文字のqa-workflow-skills Git SHA> \
  --execution-profile .agent-eval-runs/config/profile.json \
  --verifier-image <固定verifier image digest> \
  --output-root .agent-eval-runs/qts-baseline \
  --repeat 2
```

Runnerはtarget用sanitized workspace、synthetic baseline、Skill / source manifest、artifact contract、runtime verifier replay、workflow runtime replay、Judge evidence、workspace integrityを保存します。Artifact Judgeはcanonical artifactsと不足placeholderのみを受け取り、routing / final stdout / machine summaryは受け取りません。Workflow Judgeはrouting / final stdoutと固定machine summaryを受け取ります。二つの判定は別process・別outer bubblewrap namespace・別cwd・別一時`CODEX_HOME`で実行します。`--verifier-image`は既存verifier contractの固定digestを指定し、Codex imageへ置き換えません。

## Judge検証とSkill改善

`judge_validation`は固定scenarioの正常・限定違反fixtureを別々にJudgeへ渡します。AI生成fixtureは承認済み扱いにせず、`--approval-file`でdataset revision、reviewer、timezone付き日時、該当fixtureの固定規範根拠を指定しない限りfixtureはreview pendingです。承認行には、実際のfixtureを確認した後にそのrunの`result.json`に出力された`cases[].approval_binding`全体を`binding`として記録してください。このbindingはfixture定義、baselineとfixture成果物の内容、Judge入力、criterionと期待判定、規範revisionと参照内容を固定します。どれかが変わると既存承認は一致せず、fixtureはreview pendingになります。`binding`を持たない旧形式の承認行は読み込めますが、`legacy_unbound`として保留されます。再承認には新しいrunの成果物を人が確認し、そのrunのbindingを承認行へ記録してください。未承認fixtureを自動承認する移行は行いません。tuning proposalはtune splitの観測だけを受け取り、independent splitの期待値・判定を受け取りません。Candidate Judgeも固定fixtureで独立評価されますが自動採用しません。

`qts-judge-fixtures-v2`の`major-violation-003`は、未確定のWeb/Native間pixel parityを確定済みCheckout oracleへ昇格し、Navigation / Typographyの完全一致をWeb Checkoutの失敗条件にする`QTS-SEM-003`違反fixtureです。共有する意味・情報順と完全な視覚的一致は区別します。このfixtureは引き続き`pending_human_review`で、v1のbindingは再利用しません。`QTS-SEM-008`には新fixtureを推測で追加せず、正式なAgent成果物が得られるまでは`judge_unverified`を維持します。

```bash
python -m scripts.skills.evals.agent.judge_validation \
  --baseline-result .agent-eval-runs/qts-baseline/result.json \
  --target-root /home/<user>/src/qa-training-store \
  --execution-profile .agent-eval-runs/config/profile.json \
  --output-root .agent-eval-runs/judge-validation \
  --approval-file .agent-eval-runs/config/human-approvals.json \
  --max-cases 11 --max-seconds 1800 --repeat 2
```

`improve`は、2回以上再現し、既存runtime / artifact検証が通り、承認済みJudge fixtureに対応する固定critical failureだけを分析対象にします。分析Agentの自己申告だけで修正可とはしません。候補sourceは一つのSkill内の`SKILL.md` / `references/**` / `scripts/**` / `assets/**`に限定し、候補patch・package fingerprint・比較結果をrunへ保存します。RunnerはGit branch / commit / push / PRを作成せず、候補を自動採用しません。実Skill使用観測が得られない場合、品質差があってもSkill改善実証とは判定しません。

```bash
python -m scripts.skills.evals.agent.improve \
  --baseline-result .agent-eval-runs/qts-baseline/result.json \
  --judge-validation-result .agent-eval-runs/judge-validation/result.json \
  --target-root /home/<user>/src/qa-training-store \
  --execution-profile .agent-eval-runs/config/profile.json \
  --output-root .agent-eval-runs/improve-run \
  --verifier-image <固定verifier image digest> \
  --max-cases 10 --max-repairs 5 --max-seconds 3600 --analyze-only
```

`--analyze-only`も分析Agentの実行を伴いますが、Skillファイルは変更しません。修正が許可された通常runでは、各候補を同一target / scenario / profileで2回以上再評価します。外部Judgeの承認、実行環境、比較条件が不足している場合はreview pending / unverifiedとして残し、PASSへ読み替えません。

## CI・ローカルテスト

通常CIは外部LLM、Codex、Docker runtimeを起動しません。Fake Agent / Judgeのunit・integration testとrepository contract testを実行します。

```bash
python -m compileall -q scripts/skills/evals/agent tests/skills/evals/agent
python -m unittest discover -s scripts/skills/evals/agent/tests -p 'test_*.py' -v
python -m unittest discover -s tests/skills/evals/agent -p 'test_*.py' -v
```

すべての実run結果は`.agent-eval-runs/`に保存し、Gitへ追加しません。
