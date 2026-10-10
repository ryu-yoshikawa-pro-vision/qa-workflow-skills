# 実Agent評価ランナー実装Plan

このPlanは、既存のAgent Skills評価データセットを使って実Agentから成果物を生成・採点し、結果の自動分析、根拠が十分なSkill修正、同条件での再評価、レビュー待ちへの振分けまで一括して実行できる開発用の評価・改善基盤を追加する実装計画です。固定テスト対象 `qa-training-store` での統合評価も含みます。改善工程の詳細は[自動分析・修正・再評価Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)を正本とします。

Skill本体の実行基盤は変更しません。Codex、Claude Code等のAgent runtimeは各クライアントへ任せ、今回追加する評価・改善基盤はリポジトリ開発時の評価と、その結果に基づく隔離されたSkill修正・再評価だけを担当します。固定テスト対象での評価もSkill本体へ対象repo固有処理を入れず、評価側から実行します。

## 対象ブランチ

`feat/agent-eval-runner`

## 基準

- 対象リポジトリ: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- 基準branch: `main`
- 基準commit: `dec3f7c764db2869dc24eb3d6f154712a6677068`
- 正規Skill数: 19
- trigger dataset: 428 query
- deterministic output dataset: 38 case
- semantic dataset: 72 case
- `qa-workflow` routing fixture: 61件

現在の評価契約では、決定論的出力評価と意味評価はいずれも保存済みの評価対象出力を評価し、Agent実行と評価対象出力の生成は責務外です。

PR #11の検証では`codex exec`で評価対象成果物を生成し、既存の`semantic/run.py`へ渡して外部Judgeで評価した実績があります。ただし、評価対象成果物の生成は一時batch scriptで行っており、現在のリポジトリには共通の実Agent実行ランナーがありません。

## 目的

### 最終目的

このPlanの最終目的は、`qa-workflow-skills`の実Agent評価結果を**自動分析し、根拠が十分で安全に限定できるSkill起因の問題をAgentが修正・再評価して、改善が確認された候補を保存すること**です。原因不明・根拠不足・高リスク・改善未確認の案件はレビュー待ちに分けます。変更前後は同じEvaluatorと実行条件で比較し、検証済み候補でも採用は人間が決めます。

今回作るものはSkillを実行する新しいAgent runtimeではありません。Codex、Claude Code等が持つAgent runtimeをそのまま使い、`qa-workflow-skills`側にはQA Skillの評価に必要な最小の実行・記録経路だけを追加します。

また、現在すでに存在するdeterministic / semantic / trigger / routing / runtime評価を置き換えません。実Agent生成・評価・保存に加え、結果の分析と限定した修正・再評価を既存評価へ接続します。native triggerの実Agent評価は引き続き対象外です。

完成後は、少なくとも次の改善ループを同じ仕組みで繰り返せる状態にします。

```text
現在のSkill
  ↓
固定した評価条件で実Agent実行
  ↓
既存評価 + 固定テスト対象評価
  ↓
結果と失敗根拠を保存
  ↓
分析Agentが問題原因を分析
  ↓
機械的に自動修正可否を判定
  ├─ 根拠不足・不明・高リスク → レビュー待ちとして保存
  └─ 条件成立 → 修正Agentが隔離環境でSkillを修正
                        ↓
                 同じ評価条件で再実行・比較
                        ├─ 改善確認 → 検証済み修正候補を保存
                        └─ 未改善・回帰 → レビュー待ちとして保存
```

自動分析と、機械的な条件で許可された限定的なSkill修正・再評価は今回の実装範囲です。LLMの自称確信度では自動修正を許可しません。自動A/Bランキング、Skillの無制限な書換え、自動採用・push・PR作成・mergeは行いません。比較条件と根拠を保存し、**実際の品質問題に対する自動修正・改善実証**を受入検証します。実証できなければ分析・評価基盤の成立と改善実証の未達を分けて報告します。対象は明示的なSkill利用による既存Eval Inputの出力品質と、固定repo上の分析・設計workflow品質です。リポジトリ内の全Skillの実環境動作、ブラウザE2E、native Skill trigger精度まで測定できたとは扱いません。

### フェーズ1で実現すること

既存Eval Inputを使い、次の一連の処理を1つの共通経路から再現可能に実行できるようにします。

```text
既存Eval Input
  ↓
実Agentを独立プロセスで実行
  ↓
評価対象成果物を保存
  ↓
既存deterministic / semantic evalを実行
  ↓
ケース別結果と実行全体の結果を保存
```

Skillを変更した後に同じ評価ケースを実Agentで再実行し、既存評価基準で結果を確認できるようにします。

### フェーズ2で実現すること

固定revisionの`qa-training-store`を実際のテスト対象として、`qa-workflow-skills`の複数Skillを使う分析・設計workflowを実Agentで動かします。

単一SkillのEval Inputだけでは確認できない、次を評価できる状態にします。

- 実repoから正しい仕様根拠を選べるか
- `qa-workflow`が必要な工程だけを適切にroutingできるか
- 複数Skillの成果物chainが追跡可能な状態で閉じるか
- stable ID / runtime evidence / currentness等の既存契約を維持できるか
- 規範仕様にない期待動作を追加しないか
- 同じtarget revisionと評価要求でSkill修正前後を再評価できるか

### このPlanのレビューで維持する前提

今後別セッションでPlanをレビュー・修正する場合も、次はこのPlanの目的上の前提として維持します。

- Agent loop、context管理、sandbox、subagent等はCodex / Claude Code等のruntimeへ任せ、独自Agent runtimeを作らない
- 既存deterministic / semantic graderを再実装しない
- Skill本体から評価ランナーへ依存させない
- Codex固有実装をSkill契約へ入れず、Agent commandは外部から注入する
- 評価対象AgentへReference / expected / rubric / grader等の評価正解情報を公開しない
- `qa-training-store`固有処理をSkill本体へ入れない
- 現在必要な1つの固定targetを評価するためだけに、汎用plugin framework、DB、MCP、LangGraph等を追加しない
- 十分な再現性・根拠・変更範囲・検証条件を満たしたSkill問題だけ、隔離したAgentが修正して同条件で再評価する。原因不明・証拠不足・高リスク案件はレビュー待ちに保存し、自動採用・push・PR作成・mergeは行わない
- `description`による実Agent上のnative Skill発火評価は、クライアント固有の観測が必要なため今回の出力品質・workflow評価とは分離する。既存trigger datasetは維持し、今回のPlanだけでlive trigger最適化まで達成したとは扱わない

### フェーズ3: 評価結果の自動分析・限定修正・再評価

フェーズ1・2の実Agent評価結果を分析Agentが読み、修正可否条件を機械的に検査します。条件を満たすSkill単独の問題は修正Agentが隔離環境で最小修正し、関連テストと固定Evaluatorによる再評価で確認します。条件不足・高リスク・改善未確認の案件はレビュー待ちとして根拠付きで保存します。詳細は[自動分析・修正・再評価Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)を正本とします。フェーズ1の共通ランナー実装を待たず、分析・振分けのfake Agentテストを並行して開発できます。

## フェーズ構成

### フェーズ1: 既存Eval Inputで実Agent生成を自動化する

本Plan本文の共通ランナーを実装し、既存deterministic / semantic caseを実Agentで生成して現在のgraderへ接続します。

ここでは新しい評価基準を作らず、既存の評価データセットとgraderを再利用します。

PR #14で追加された3 Skillのsemantic caseも、固定Evaluator revisionに評価caseが存在する場合は同じ実Agent生成・Judge評価経路で扱います。PR #14から移管された83 caseの全量実Agent反復評価はPR #17の評価範囲に含めます。ただし実際のcase集合と件数は実行時の固定Evaluatorのmanifestから取得し、83件という過去の観測値をランナーの固定条件にはしません。PR #14のマージを共通ランナー実装の前提にはしません。

### フェーズ2: qa-training-storeを固定テスト対象として評価する

フェーズ1完了後、`ryu-yoshikawa-pro-vision/qa-training-store`を固定revisionで使い、実repoを入力にした分析・設計workflowを評価します。

詳細は [`qa-training-store固定対象の実Agent統合評価Plan`](./2026-10-03_132700_agent-eval-runner_02_qa-training-store-integration-eval.md) を正本とします。

初回対象は次で固定します。

- target repo: `ryu-yoshikawa-pro-vision/qa-training-store`
- target revision: `84ce165493649550832731a60cf436f8ae29c56b`
- Platform: Web
- Feature: Checkout / Payment

フェーズ2は新しい汎用benchmark frameworkを作るものではありません。まず1つの固定repo・固定revision・固定Featureで実行し、追加の抽象化が必要かは実測後に判断します。

## 現在確認できている不足

### 1. 評価対象成果物の生成が共通化されていない

`scripts/skills/evals/deterministic/run.py`と`scripts/skills/evals/semantic/run.py`は保存済み出力を受け取ります。

一方、実AgentへEval Inputを渡し、出力を所定の場所へ保存する共通処理はありません。

### 2. 実Agent実行と既存評価を一括で回せない

現在は次を個別に行う必要があります。

1. Agentへ評価ケースを渡す
2. 最終出力を保存する
3. deterministicまたはsemantic evalを起動する
4. 結果を収集する

同じSkillを繰り返し改善する場合、この手作業が評価の再現性と実行量の妨げになります。

### 3. 評価結果から原因を分析して修正・再評価する共通処理がない

現Planの既存評価は合否・理由を出力しますが、Skill起因かどうかの切り分け、修正可否判定、隔離した候補の修正と再評価、レビュー待ちの整理は自動化されていません。評価結果の収集だけで改善が自動的に進むとは扱いません。

### 4. 評価対象Agentから評価用正解情報を隔離する共通処理がない

`skills/<skill>/evals/`には次が存在します。

- deterministicの`expected.json`
- semanticの`reference.md`
- semanticの`rubric.json`
- validator

リポジトリrootをそのままAgentの作業ディレクトリにすると、Agentがこれらを検索・参照できてしまいます。

評価対象Agentへ渡す情報と、評価側だけが使う情報を物理的に分離する必要があります。

## 設計方針

### 1. Skill本体からランナーへ依存させない

依存方向は次に固定します。

```text
実Agent評価ランナー
  ↓
Skill Package
  ↓
Skill-local scripts
```

次は禁止します。

```text
SKILL.md
  ↓
実Agent評価ランナー
```

`SKILL.md`、`references/`、`scripts/`、`assets/`の通常実行契約へ、今回の評価ランナー固有のcommand、path、状態を追加しません。

### 2. Agentクライアント固有処理を実装しない

ランナーは特定AgentのSDKやCLIをimportしません。

実Agentとは次の外部command契約だけで接続します。Agent subprocessの`cwd`はフェーズ1ではSkill-only workspace、フェーズ2ではsanitized targetに固定します。ただし`cwd`自体に情報の読み取り制限はありません。隔離は後述の実行条件で保証します。

```text
stdin:  Agentへ渡す評価用prompt UTF-8
stdout: Agentの最終成果物のみ UTF-8
stderr: Agentの進行・診断ログを許可
exit 0: Agent実行成功
non-zero: Agent実行失敗
```

commandはargvとして受け取り、`shell=True`を使いません。

Codex、Claude Code等の起動方法はランナーの実装へ固定しません。

OpenAI公式のCodex eval例でも、`codex exec`は自動実行向けに最終結果をstdout、進行をstderrへ出す用途として案内されています。この性質を利用できますが、Codex固有flagはランナーへ埋め込みません。

参考:
- https://developers.openai.com/blog/eval-skills

### 3. 出力品質評価とSkill発火評価を分離する

今回のランナーは、対象Skillを明示して出力品質を評価します。

生成promptでは対象Skill名と一時実行ディレクトリ内の`skills/<skill>/SKILL.md`を明示し、そのSkillを使用するよう指示します。

これは`description`による自動発火を評価するものではありません。

既存のtrigger datasetと、実Agent上でのnative Skill発火評価は別契約として維持します。クライアント別のnative trigger検出adapterは追加せず、利用可能なtraceに記録されたSkillファイルの読み取り事実だけを補助的に保存します。

### 4. 評価用正解情報をAgentから隔離する

各Agent実行前に一時実行ディレクトリを作成します。

一時実行ディレクトリへは、指定した`--skill-revision`のGit treeのtracked `skills/<skill>/SKILL.md`から検出したSkill集合から、通常実行に必要なファイルだけをコピーします。

コピー対象:

```text
skills/<skill>/SKILL.md
skills/<skill>/references/**
skills/<skill>/scripts/**
skills/<skill>/assets/**
```

コピーしないもの:

```text
skills/<skill>/evals/**
scripts/skills/evals/**
docs/**
.git/**
```

検出したSkill集合すべての通常Skill Packageを配置し、`qa-workflow`等が他Skill名を前提にする場合も通常構成を維持します。配置元はworking treeではなく、明示した`--skill-revision`のGit treeのtracked contentだけとします。Skill名・件数を固定せず、検出したSkill名を昇順に並べ、各Skill packageのpath・SHA-256とともにmanifestへ保存します。候補revisionに存在しないSkillを補完したり、Evaluator側のSkill packageを追加したりしません。

Eval Inputはファイルとして一時実行ディレクトリへコピーせず、生成promptへ埋め込みます。

Agent-visible workspaceには`reference.md`、`expected.json`、rubric、validatorを配置しません。**このコピー条件だけでは元Evaluatorへのアクセス禁止を保証しない**ため、実行開始前に後述の隔離preflightを満たす必要があります。

### 5. 既存graderを再実装しない

新しいランナー内にdeterministic assertionやsemantic Judgeロジックを複製しません。

- deterministic: 既存`scripts/skills/evals/deterministic/run.py`を使用
- semantic: 既存`scripts/skills/evals/semantic/run.py`を使用

ランナーは、評価対象成果物の生成、保存、既存graderの呼び出し、結果収集だけを担当します。

### 6. 通常CIでは外部LLMを呼ばない

現在の方針を維持し、pull request / pushで自動実行される通常GitHub ActionsからCodex等を呼びません。

CIではfake Agent commandを使って、ランナー自体の契約・一時実行ディレクトリ・grader接続だけを検証します。

実Codex等を使う評価は、開発者が明示的に起動するローカル評価とします。

### 7. 評価対象Skillと採点基準のrevisionを分離する

ランナーと既存graderは**固定Evaluator revision**のcleanなcheckoutから実行する。評価対象のSkill packageだけは別の`--skill-revision <40文字Git SHA>`で選択する。

1. Evaluator側の`HEAD`、working tree・indexがcleanであることをlive runのpreflightで検証し、Evaluator SHAを保存する。dirty状態では実行しない。
2. `--skill-revision`で指したGit commitのtracked contentを`git archive`等で取得し、検出したSkillの`SKILL.md` / `references/**` / `scripts/**` / `assets/**`だけを配置する。未コミット変更、候補側`evals/**`、Evaluatorのworking treeのSkillを混ぜない。
3. 配置した各Skill fileの相対path / size / SHA-256からmanifestとSkill package fingerprintを生成し、指定Git treeとの一致を検証する。存在しないcommitや不一致はAgent実行前のerrorにする。
4. deterministic / semantic grader、Reference、rubric、Judge prompt / response正規化は固定Evaluator側を使用する。ただし、runtime実装の鮮度判定は候補revision由来の信頼済みsourceを参照する。固定版production verifierを候補成果物へそのまま適用して実装fingerprint差をFAILへ変換しない。
5. Evaluator SHA、graderの内容fingerprint、dataset / rubric / Referenceのfingerprintをprovenanceへ保存する。候補Skill側のeval実装を採点側へimportしない。

評価可能なcaseは固定Evaluatorのdataset / manifestにあるcaseと、候補revisionに存在するSkillの対応で確定します。`--skill <name>`の明示指定で候補Skillが存在しなければpreflight errorとします。`--skill all`では両方に存在するcaseだけを実行し、Evaluator側にcaseがあっても候補Skillが存在しないもの、候補SkillがあってもEvaluator側にcaseがないものを、それぞれ理由付きで結果の評価対象範囲へ記録します。どちらもPASS / FAILとして捏造せず、未実行を全件PASSとみなしません。Skill名やcase数をコードへ固定しません。

Skill-local verifierはSkill本体にも含まれる。runtimeの再実行と共通の品質判定を次のように分ける。

- **候補実装の鮮度・正当性**：EvaluatorがAgentの作業ツリーから独立して展開した、指定Skill revisionの信頼済みsourceを使い、そのrevisionのproduction verifier / generatorで実際のrequestを再実行する。保存結果との対応、実装fingerprint、generation、`valid`、`current_structure_state`を確認する。候補側のverifierが無効な結果を完成扱いした場合は品質の問題とする。
- **固定基準の採点**：deterministic / semanticのgrader、expected / rubric / Reference、判定ルールは固定Evaluator revisionを使う。フェーズ2の共通機械判定も固定Evaluatorに置き、候補verifierの`valid`や候補generatorの`can_complete`をそれ単体で合否の根拠にしない。既存`deterministic/runtime_validator.py`の`_source_paths()`は現在Evaluator側`REPO_ROOT`へ固定されているため、`deterministic/run.py`へ任意の`--runtime-source-root`を追加し、`grade()` → `validate_runtime_evidence()` → `_assert_runtime_pair()` → `_source_paths()`へそのpathを明示的に渡す。指定時はEvaluatorが作成した**候補Git tree由来の信頼済みsource root**に一致することをrunner側で検証する。引数省略時は従来のEvaluator側`REPO_ROOT`を使用し、既存CLI・テストの動作を維持する。`run.py`からruntime assertionへ明示的に伝播し、**graderのコードとassertionの意味は固定したまま、実装由来のfingerprint / generator version / static-dataの照合先だけを候補の信頼済みsourceへ切り替える**。従来のgrader CLIは引数省略で従来動作を維持し、一般Skill validatorのimport先・eval datasetは変更しない。Agentが編集できるworkspaceをsource rootに指定しない。
- **契約非互換**：両revisionで共通に判定できるcriteriaを評価し、schema / 機械契約が実際に互換でない部分だけを`evaluator_incompatible`として扱う。単なるimplementation fingerprint相違は非互換理由にならない。`evaluator_incompatible`を品質FAILへ読み替えず、共通部分のsemantic評価まで破棄しない。出力契約が変わり固定graderで評価できない場合は、両revisionを処理できる共通Evaluatorへ更新後、**旧版・新版の両方をそのEvaluatorで新規に実行・再採点**する。過去の別Evaluator評価を混ぜない。互換adapterの汎用基盤は今回作らない。

候補verifier / generatorの独立再実行は、Agentに見えるworkspaceとは別の指定Git treeを使い、**Evaluator本体のprocess内ではimportも実行もしない**。候補のtracked contentも実行可能コードであり、Git SHAによる出自確認は安全性の証明ではない。既存のDocker方式を使用し、次の固定経路にする。

1. Evaluatorは候補revisionの**各Skillの`scripts/**`と`assets/**`を元の`skills/<skill>/`相対配置のまま**Git objectから別ディレクトリへ展開する。generatorが参照する同revisionの静的データを含め、相対path・size・SHA-256 manifestを両方検証する。Agent-visible workspaceからの取得や候補側`evals/**`の混入は認めない。必要なsource・静的データが欠落した場合は再実行環境の準備エラーでありSkill品質FAILではない。
2. `codex_docker_launcher.py`と同じDocker実行基盤・固定imageで、**Python-only検証用の別コンテナ**を`--read-only --cap-drop=ALL --security-opt=no-new-privileges --network none`で起動する。候補sourceと同revisionの`assets/**`は`readonly` bind mountし、requestはEvaluatorが検証した固定byte列をstdinから渡す。書込み可能なのは`/tmp`のtmpfsのみとする。Evaluator checkout、grader、rubric、Reference、認証情報、Docker socket、元target、Agent用`CODEX_HOME`をmountしない。
3. 候補`runtime_contract.py` / generator / `workflow_runtime.py`を元Skillの相対pathが解決できるcwdと固定argvで直接起動し、stdoutのJSON、終了コード・制限時間、stderr診断をEvaluator側で安全化して回収する。`test-condition-design/scripts/ui_pattern_candidates.py`が`../assets/ui-pattern-catalog.json`を読み込めることを隔離再実行の回帰テストで確認する。任意のPython module import、自由なshell command、ネットワーク通信を許可しない。stdin / stdoutのsource SHA・request SHA・result SHAをprovenanceへ紐付ける。
4. Docker mount・network・UID・認証情報非公開・source write-denialを実行前に確認し、候補sourceからEvaluator-only sentinelを読み取れないnegative testを用意する。timeout時はコンテナを終了・削除し、そのattemptをrunner / environment errorとする。候補sourceが独自に`valid=false`を返す場合はエラーとして隠さず、その判定を保持する。

この候補再実行は**鮮度と結果再現の検証**であり、固定品質判定の代わりではない。候補が`valid=true`を返しても、固定Evaluatorの共通機械判定・意味Judgeの基準を満たさなければPASSにしない。候補sourceを隔離実行できない環境ではrunner / environment errorとして残し、Skill品質FAILへ変換しない。

### フェーズ2で固定する共通機械判定

フェーズ2はcase固有`expected.json`がないため、既存の`deterministic/run.py`を架空eval IDで起動しない。代わりに**固定Evaluator内の**`scripts/skills/evals/agent/common_runtime_checks.py`が、回収した成果物本文・artifact manifest・保存request / result・workflow runtime resultを、候補verifierの`valid`とは独立して検査する。

- JSON fenceの厳格解析、Runtime Input / Resultの一致、Machine Entity構造と重複、input / model / generation / upstream依存fingerprintの再計算、entity / runtime間dependencyの整合は、固定Evaluatorの`deterministic/runtime_validator.py`にある純粋なparser・assertionを再利用または必要な部分を共通関数へ切り出す。`expected.json`に依存した固定caseのexact期待Entity集合検査は流用しない。
- stable ID一意性、Authority / TR / TCN / CI / TC間の参照、孤立・逆向き・重複edge、coverage / closureは、固定Evaluator側の`skills/coverage-analysis/scripts/traceability.py`のgraph検査・規範を、候補sourceをimportせず再利用する。保存normalized inputと回収した同一attemptのMachine Entity / graph根拠を照合する。固定targetの`BR-CHECKOUT-001..003` / `AC-CHECKOUT-001..003`をEvaluator scenarioから固定し、Agentの入力省略で検証対象が狭まらないようにする。正当にblockedな箇所は未完了として保存し、存在しないtest caseは捏造しない。
- expected runtime unit / entity集合の導出は固定scenario scope・既存Skill契約・保存済み正規入力・実際のroutingを突き合わせて行う。routing自己申告だけで母集団を縮小せず、routing不足も判定に残す。必要な入力がなく判定不能なら`evidence_unverified`または`evaluator_incompatible`として検証済みPASSにしない。
- **候補verifierは生成・鮮度の照合にのみ使う。** 候補`valid=true`だが固定検査FAILなら、具体的な共通assertionを機械品質の非passとする。候補`valid=false`で固定検査PASSでも候補側の契約失敗を隠して全体PASSにはせず、双方の結果を保存する。schemaの意味が異なり共通判定不能な部分は`evaluator_incompatible`とし、必要なら両revision対応の固定Evaluatorで両方を新規実行する。

新しいproduction verifier、全Skill専用parser、独自graph engineは作らない。`common_runtime_checks.py`は共通不変条件の呼出しと結果集計のみを持ち、候補sourceの検証ロジックへ委譲しない。受入テストでは正常baseline、runtime fingerprintのみ変更した候補、`valid=true`を常に返すよう弱体化した候補、重複stable ID・未解決参照・欠けた必須edgeを持つ不正成果物を確認する。弱体化候補が`valid=true`でも固定機械判定FAILになることを要求する。
main / candidate比較は、**同じEvaluator checkoutを起動したまま**`--skill-revision`だけを変更して2 runを生成する。checkout全体を入れ替えてgraderが変わる方式を採らない。

### 8. Agent / Judgeの実効実行条件を固定する

Live CLIへ`--execution-profile <path/to/execution-profile.json>`を必須追加する。これはEvaluator側にのみ置く**秘密を含まないJSON**で、比較に影響する実効設定とその確認状態を保持する。fake Agentテストでは固定fixtureを使う。

最低限、次を記録する。

- `schema_version`、Agent名・model・CLI version、推論設定、実行オプション、sandbox / approval / networkの方針
- Agentが利用できるSkill・tool・MCPの集合、user/globalの設定・指示の扱い、読み取り可能なmount・ファイル範囲、隔離方式
- 候補Agentと独立Judgeそれぞれの非秘密の起動設定fingerprint、Judge model / version / 推論・tool・指示条件
- 実効設定の照合方法、根拠への相対path、検証状態（`verified`または`unverified`）。提供側のmodel更新等を確認できなければ不確実性として記載する。許可済みのモデルAPI通信で残る外部アクセス可能性は実行条件・制約として保存し、それ自体を必須隔離の検証失敗とはしない。

`--agent-name` / `--agent-model`とprofileの宣言を照合し、実際のlauncher / CLIで観測できる設定と矛盾した場合は停止する。汎用subprocessだけでuser/global config等を完全に解析できると仮定しない。profileの自己申告だけで`verified`にせず、確認根拠がなければ結果は保存しても`not_comparable`とする。比較対象runではprofileの非秘密fingerprintと実効設定検証結果を一致させる。

環境変数、secret実値、認証用argv、設定ファイルの秘密は保存もhash化もしない。Judgeの`command_argv`にも秘密を埋め込まず、起動前に秘密が含まれないことを検査する。生argvに秘密を含めず、Agent別SDKや新たなAgent config parserは作らない。Judgeは生成とは別process / 別prompt / 別sessionで起動する。生成Agentの起動argvはJudgeへ流用しない。Judgeの独立argv・cwd・model・実効設定を記録する。

### execution-profile.jsonの最小契約

`--execution-profile`はEvaluatorが事前に確定したUTF-8 JSON objectを読み取り、少なくとも以下のキーと型を検証する。ランナーは任意Agentのconfigを自動発見する新しいadapterを持たない。

```json
{
  "schema_version": 1,
  "agent": {
    "name": "codex",
    "model": "<実際に固定したmodel ID>",
    "timeout_seconds": 3600,
    "cli_version": "<CLIで確認したversion>",
    "reasoning_effort": "<固定した推論設定>",
    "launch_options": ["<認証情報を含まない実行オプション>"],
    "sandbox_policy": "<固定した実効sandbox>",
    "approval_policy": "<固定した承認設定>",
    "network_policy": "<固定した外部アクセス条件>",
    "tools": ["<利用可能なtool名>"],
    "mcp_servers": [],
    "skill_roots": ["<Evaluatorが配置したSkill root>"],
    "external_instructions": "<noneまたは非秘密の固定指示のfingerprint>",
    "global_config": "<disabledまたは非秘密の固定設定fingerprint>"
  },
  "judge": {
    "model": "<実効Judge model ID>",
    "command_argv": ["<Judge専用launcher>", "<秘密を含まない固定argv>"],
    "cwd": "evaluator-judge-workspace",
    "timeout_seconds": 600,
    "cli_version": "<Judge実行commandのversion>",
    "reasoning_effort": "<固定した推論設定>",
    "launch_options": ["<非秘密の起動オプション>"],
    "sandbox_policy": "<Judge実行時のsandbox>",
    "approval_policy": "<Judge実行時の承認設定>",
    "network_policy": "<Judge実行時の外部アクセス条件>",
    "skill_roots": [],
    "global_config": "<disabledまたは非秘密の固定設定fingerprint>",
    "tools": [],
    "mcp_servers": [],
    "external_instructions": "<noneまたは固定指示のfingerprint>"
  },
  "isolation": {
    "method": "<OSまたは既存実行環境の境界>",
    "agent_read_roots": ["<候補Agentから読めるroot>"],
    "evaluator_read_blocked": true
  },
  "verification": {
    "status": "verified",
    "method": "<実効設定・アクセス境界の検証方法>",
    "evidence_path": "<Evaluator側非秘密証拠の相対path>"
  }
}
```

上記`agent.timeout_seconds: 3600`はJSON例であり既定値ではない。live実行では`agent.timeout_seconds`を必須の正の整数として明示し、フェーズ1・2の共通`executor.py`がAgent起動開始から適用する。timeout値はprovenanceと比較条件に含め、Runnerが勝手に別の値へ置換しない。timeout時は子孫processと実行中Dockerコンテナを終了・回収してAgent execution error（exit code 2）とし、Skill品質FAILにはしない。後続caseを実行できるbatchでは続行する。

`<...>`は説明用の占位記号であり、live実行時には実値に置き換える。不明な実効項目は架空の固定値で埋めず、`null`とし`verification.status=unverified`を記録する。`verification.status=verified`を必須とする直接比較では、nullの実効必須項目は許可しない。`verification.status=verified`は自己申告では成立しない。Evaluatorは証拠fileの存在、読み取り拒否probeの結果、非秘密のCLI設定情報との照合を行い、**必須のローカル隔離・起動条件**に不明・不一致があれば`unverified` / `not_comparable`とする。許可済みのモデルAPI通信が残ることのみで`unverified`にはしない。`evaluator_read_blocked=true`も強制境界の代わりにならない。

相対pathはEvaluator-owned出力rootを基準に正規化する。profileをSHA-256へ含めるときは、認証やOS絶対pathを除いた上記の正規比較項目だけを固定順序で正規化する。profileが異なるが実効条件は同じと推測して自動同一視しない。実Codex Judgeは生成側とは別コンテナ・別`CODEX_HOME`・別launcher設定に固定し、Judge固有の実効profileを検証する。

### 9. 正解情報の読み取り隔離を確認する

EvaluatorとAgentの間に、ディレクトリ分割だけでなく**OS等による実効読み取り禁止境界**を設ける。Agent subprocessの`cwd`だけでは成立しない。

- Agentが利用できるファイル・mount・tool / MCPにはEvaluator原本のexpected、Reference、rubric、grader、結果、元target checkoutを公開しない。Linuxの隔離コンテナを今回の実Codex smokeの標準構成とし、独自sandboxは実装しない。外部ネットワーク経由で公開評価資料を取得できる可能性は、ファイル隔離だけでは排除できないため、次節のネットワーク・tool条件を別途確認する。
- user/global指示・設定・Skill・MCPを固定された評価条件以外から混入させない。認証情報は必要最小限の別経路で渡し、provenanceに書かない。
- preflightではEvaluator-only領域の**非秘密sentinel**を、Agentと同一権限・mount・tool構成から読めないことを確認する。fake Agentはrunnerの失敗時動作を検査し、実Codex smokeでは実際の読み取り拒否と余分な設定の混入防止を確認する。
- Evaluator原本のOS境界、許可mount、意図しないSkill / MCP / web検索の無効化など**必須条件**を確認できないrunは`isolation_unverified`として保持しても、比較可能な品質評価にはしない。許可したモデルAPI通信の残留アクセス可能性は別途記録し、それだけで比較不可としない。stderr等は秘密混入を想定し、出力上限・安全化を行い、安全なログとして保存できない生内容は保存しない。

### 実Codex smokeで使用する固定実行構成

今回、**Linux Docker Engine上の使い捨て非特権コンテナ**を実Codex smokeの基準環境とする。Windowsから実施するときはDocker Desktop / WSL2等でLinuxコンテナを起動できることを前提条件とする。Dockerを使用できない環境ではfake Agentによるrunner testまでは実行できるが、実Codex評価の完了とはしない。ほかのAgentにも同等の外部argv契約を使うが、隔離と実効条件を確認できたとみなすのはこのCodex実行構成だけとする。

1. ホストで固定Evaluator checkoutを開き、Evaluator-owned領域で候補Skill tracked contentと（フェーズ2では）sanitized targetを準備する。bind mountは、使い捨てAgent-visible workspace（**読み取り専用**）、その配下の`.qa-eval-output/`へ重ねるattempt専用**書込み可能**出力root、一時`CODEX_HOME`の3箇所に限定する。Evaluator checkout・採点資料・元target checkout・Docker socket・ホストhomeはmountしない。`--privileged`、host PID、host filesystem mountを使わない。
2. Codex CLIとPythonが入った固定バージョンのLinux imageを使用し、image digest、Codex CLI version、Python versionをrunへ記録する。`docker run --rm -i --read-only --cap-drop=ALL --security-opt=no-new-privileges`を基本に、`--workdir /workspace`、`--tmpfs /tmp`等の一時書込み領域、`--mount type=bind,src=<Agent-visible workspace>,dst=/workspace,readonly`、`--mount type=bind,src=<attempt専用出力root>,dst=/workspace/.qa-eval-output`、`--mount type=bind,src=<使い捨てCODEX_HOME>,dst=/codex-home`、`-e CODEX_HOME=/codex-home`を指定する。workspaceの`.qa-eval-output/`を事前に作成し、その位置だけ書込み可能mountで覆う。必要なUID/GIDと書込み権限は出力root、最小`CODEX_HOME`、`/tmp`に限定する。source・Skill・評価用設定への書込みはmountで拒否し、post-run差分検査は補助として残す。実行中コンテナへEvaluator資料を`docker cp`しない。
3. 認証は既存Codexのログイン情報を使い捨て`CODEX_HOME`へ**起動前に必要最小限で複製**する。ホストの本来の`~/.codex`はmountしない。秘密内容・そのhash・container内の生環境変数は永続保存しない。認証情報がAgent側プロセスから参照可能である制約を認識し、信頼できない入力へ広く公開しない。API keyを使う場合も同様に限定し、明示的な承認なく認証方式を変更しない。
4. コンテナ内の`config.toml`は評価専用の最小値に固定する。`model`、`model_reasoning_effort`、`sandbox_mode`、`approval_policy`を明示し、既定のMCP server / plugins / 追加Skill / user-global指示・memory / web検索などの評価外入力は使用可能な範囲で無効化する。実効CLI引数と非秘密設定のhashを照合し、未確認の項目は`unverified`にする。候補revisionから検出したSkill集合はworkspace側にだけ配置する。Codex CLIが当該設定を無視・拒否したら比較可能として起動しない。
5. Agentのweb検索・外部資料取得tool / MCPと余分なSkillを無効化し、実効設定と許可toolを照合する。**モデルAPI通信は許可**し、コンテナのネットワーク方式、web機能、既存egress制御の有無を非秘密profileへ記録する。利用可能なproxy / firewallで宛先制限を行う場合はその設定を固定するが、専用egress環境は必須としない。モデルAPI通信を通じて残る外部アクセス可能性は評価の制約として報告し、それだけで`isolation_unverified` / `not_comparable`にはしない。意図しないweb検索・外部資料取得が観測されたrun、必要なtool / MCP設定を確認できないrunは比較不可とする。
6. ホストEvaluator-onlyの非秘密sentinelをAgentにmountしない。**Agentと同じコンテナ権限のOSコマンド**で該当host-only pathの読み取り不能を確認し、同時にDocker container inspect相当でmount集合・権限・image digestを確認する。LLMによる「見えない」という返答は証拠にならない。意図的にsentinelを追加mountしたnegative fixtureではpreflight失敗を確認する。
7. 評価用の最小launcher（`scripts/skills/evals/agent/tools/codex_docker_launcher.py`）はDocker CLIへ`subprocess`のargvで接続し、stdin promptをそのまま`codex exec ... -`へ渡す。`--json`のJSONL stdoutを収集し、`--output-last-message`で得た最終応答だけを共通executorへstdoutとして返す。containerで作成した`.qa-eval-output/`内の一時message fileを回収し、元JSONLからコマンド実行などの**非秘密の事実だけ**を安全化してprovenanceへ保存する。launcherはsmoke用だけであり、共通`executor.py`やSkill PackageにCodex固有SDKを追加しない。JSONL全量を無条件に永続化しない。
8. JudgeはAgentコンテナ**外のEvaluator側**で、生成とは独立したprocess / sessionを使って起動する。Evaluator資料はJudgeにのみ与える。Judge実行環境の固定model・CLI・設定・Reference hashを別に記録し、生成コンテナの一時認証・workspaceを無条件に共有しない。

コンテナ起動時の概形は次とし、`<...>`は起動前に固定・検証した値へ置き換える。実装する`codex_docker_launcher.py`がDockerへこれと等価なargvを渡し、利用者に毎回shell手順を組み立てさせない。

```text
docker run --rm -i --read-only --cap-drop=ALL --security-opt=no-new-privileges
  --workdir /workspace --tmpfs /tmp
  --mount type=bind,src=<sanitized-workspace>,dst=/workspace,readonly
  --mount type=bind,src=<attempt-output-root>,dst=/workspace/.qa-eval-output
  --mount type=bind,src=<temporary-codex-home>,dst=/codex-home
  -e CODEX_HOME=/codex-home
  <pinned-image-digest>
  codex exec --json --model <model-id> --sandbox workspace-write
    --ask-for-approval never --config model_reasoning_effort=<fixed-effort>
    --output-last-message /workspace/.qa-eval-output/final-message.md -
```

上記はargvの構成例であり、shellに貼り付ける逐語的な完成コマンドではない。実際のDocker / Codex CLI引数は`docker run --help`と`codex exec --help`で検証する。フェーズ1の非Git workspaceでは、CodexがGit rootを要求する場合にのみ、そのCLIで確認した`--skip-git-repo-check`相当の正規optionをlauncher側から追加する。ホストでEvaluatorを動かすJudgeはこのコンテナへmountしない。

`docker version`、イメージ起動、コンテナ内`codex --version` / 認証可否、Python実行、Codex応答、JSONL出力・Skill読取観測、read-denial、source書込み拒否、必要なモデルAPI通信を**実Agent smokeで確認**してから`verified`へ進める。環境未構築・必須のローカル隔離条件未確認なら比較可能なlive評価を完了したとは報告しない。外部egress制御を行えない場合は残留リスクとして記録する。image digest・model ID・実効設定は実行時に取得して固定し、未確認の値をPlanへ作り込まない。


### 10. Skillの実使用を確認できた範囲で記録する

明示的Skill使用を要求する今回の評価では、次の**二つの事実を別々に記録**する。

- **評価条件へのSkill投入**：指定Git SHAのtracked contentを配置し、file manifest・SHA-256を照合したこと、生成promptが対象Skill名・pathを指定したことをEvaluatorが独立確認する。これは成果物品質比較の必須条件であって、実使用を証明しない。
- **Agent内部での実使用観測**：`codex exec --json`の`command_execution`等で`SKILL.md`を読む操作を確認できたときだけ`observed`、確認できなければ`unverified`とし、取得元の非秘密log・pathを記録する。native Skill injectionではOSコマンド読取ログに出ないことがある。`command_execution`の欠落をSkill未使用の証明にしない。

**両attemptでのSkill読取`observed`は成果物品質比較の必須条件としない**。両方で投入したSkill SHAと比較条件を検証できれば成果物品質を比較できる。ただし**Skill改修そのものの改善・悪化・変化なしを判断するには別の証拠が必要**。フェーズ1では変更対象Skill、フェーズ2では変更されたSkillのうちrouting対象のSkillについて、比較する両revisionでファイルの読取・適用を裏付ける実行証拠を要求する。未観測なら成果物差は報告できるがSkill改修効果は`判断不能`とする。複数Skill同時変更の個別寄与や観測済みSkillと結果の因果関係は断定しない。native `description` trigger精度を今回評価したともしない。Native Skill専用の観測基盤・汎用Agent adapterは追加しない。
## 追加する評価実行コード

評価結果の分析・限定修正の入口は`scripts/skills/evals/agent/improve.py`に分離し、既存`executor.py`と固定Evaluatorの`run.py`を再利用します。分析Agent・修正Agentを採点基準の保管領域から隔離し、許可条件・変更範囲・1回の修正上限・レビュー待ち保存は[改善Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)に従います。


### 配置

```text
scripts/skills/evals/agent/
├── __init__.py
├── executor.py
├── run.py
├── prompt_builder.py
├── workspace.py
├── qa_training_store.py
├── target_workspace.py
├── scenarios/
│   └── qa-training-store-checkout-payment-web-v1/
│       ├── scenario.json
│       ├── task.md
│       └── rubric.json
├── README.md
└── tests/
```

`executor.py`だけをフェーズ1 / フェーズ2の共通Agent subprocess境界にします。任意target向けのplugin interfaceは作りません。

### `executor.py`

- 外部Agent commandへUTF-8 promptをstdinで渡し、Agent-visible workspaceを`cwd`に固定する
- stdout / stderr / exit codeを返す
- `shell=True`を使わない
- Agentにはprofileの`agent.timeout_seconds`（必須の正の整数）、Judgeには`judge.timeout_seconds`を独立に適用し、timeout / process failureをexecution errorへ正規化する
- timeout時はPOSIX process group / Windows process treeの子孫とDocker launcherが起動したcontainerを終了・回収し、後続batchへ進む
- Agent SDKやCodex固有flagを持たない

### `run.py`

既存Eval Inputを扱うフェーズ1の入口です。

- CLI引数解析
- deterministic / semantic評価ケースの選択
- 固定Evaluator SHAのpreflight、`--skill-revision`のGit treeからSkill-only workspace作成、execution profile / 隔離preflight
- `executor.py`でAgent command実行
- 評価対象成果物保存
- 既存grader起動
- ケース別結果保存
- 全体結果集計
- exit code決定

### `prompt_builder.py`

フェーズ1でAgentへ渡す生成promptだけを構築します。

promptに含めるもの:

- 対象Skill名
- 一時実行ディレクトリ内のSkill path
- 「対象Skillを使用する」という明示指示
- Eval Input全文
- 最終成果物だけを回答する指示

promptに含めないもの:

- `expected.json`
- `reference.md`
- rubric
- validatorの判定内容
- 期待rating / pass条件

### `workspace.py`

フェーズ1用のSkill-only workspaceを作ります。

- `tempfile`で一時実行ディレクトリを作る
- 候補Skill commitのtracked contentから検出したSkill集合の通常実行ファイルだけをコピーし、内容manifestを照合する
- `evals/`を除外する
- Agent実行終了後に一時ディレクトリを削除する

### `qa_training_store.py`

フェーズ2の`qa-training-store`固定対象評価だけを担当します。

- tracked scenario `qa-training-store-checkout-payment-web-v1`を読み込む
- `--target-root`のrevision / clean state、Evaluator / Skill revisionとprofile / 隔離条件をpreflightする
- `target_workspace.py`でsanitized targetを作る
- `executor.py`で実Agentを実行する
- `.qa-eval-output/`の全fileを回収し、Agent作成`artifact-index.json`の`routing[]`（Skill / scope / status / reason / artifact_ids）と`artifacts[]`（Skill / kind / scope / artifact_id / path）を固定scenarioの要求結果・既存Skill契約・実fileと照合する。自己申告だけで必須成果物集合を縮小せず、分類不能・routing記録不足と実際の未生成を区別する
- artifact manifestに分類・Skill / path / hash・Judgeへの投入対象と固定順序を記録する。JudgeのQA成果物部分は`qa_artifact`のみとし、`routing[]`・最終stdoutのrouting / 完了宣言・固定機械判定要約は`QTS-SEM-001/002`に限って別証拠として渡す。verifierの生JSONは渡さない
- captureで得た候補側production verifier証拠を候補の信頼済みtracked sourceで独立再実行し、固定Evaluatorの機械・意味評価と分離して成果物対応・completionを判定する
- 既存semantic評価のprompt構築 / result正規化処理を再利用して独立Judgeを実行する。フェーズ2は`QTS-SEM-001/002`と`QTS-SEM-003..010`を**異なるCandidate Outputの2回のJudge呼び出し**へ分離し、後者へ`routing[]`・最終stdout・機械判定要約を渡さない。各応答を該当criterion集合で検証し、全10件を結合して既存`normalize_judge_response()`で最終判定する
- provenanceと評価結果を保存する

### `target_workspace.py`

フェーズ2の固定target preparationだけを担当します。`verifier_capture.py`をsanitized targetの`.qa-eval-tools/`へ配置し、生成する評価用`AGENTS.md`へその利用方法と`artifact-index.json`の**`routing[]` / `artifacts[]`登録形式**を記載します。QA成果物の期待本文やrubric・模範回答は記載しません。

- 指定された`qa-training-store` source revisionのtracked contentだけからsanitized targetを作る
- target固有`.agents/**` / `.codex/**`、過去Plan / report、instructor情報、target側Skill evalを除外する
- 評価用`AGENTS.md`と、元repoの運用指示を含まない評価用`docs/PROJECT_CONTEXT.md`を生成する
- 候補revisionから検出したSkill集合だけをAgent-visibleに配置する
- `.qa-eval-output/`と必要な評価用Project Context rootを準備する
- 実行前にsource・配置Skill・評価用設定を読み取り専用にし、`.qa-eval-output/`だけを書き込み可能にする。終了後はtracked / untracked / ignoredを含む許可外の差分・symlink / path境界を検証する
- 回収後にsanitized targetを削除する

### tracked scenario

`scenarios/qa-training-store-checkout-payment-web-v1/`は、フェーズ2初回評価を同条件で再実行するためのEvaluator側fixtureです。

- `scenario.json`: target repo / revision、Platform、Feature、除外対象、参照する規範仕様path等
- `task.md`: Agentへ渡す固定評価要求
- `rubric.json`: workflow / 仕様根拠 / 分析設計 / traceability / 根拠のない追加を評価するcriteria

これらはEvaluator側にのみ存在します。`rubric.json`は評価対象Agentへ渡しません。`task.md`には期待するQA成果物の正解を含めません。

独自sandboxは実装せず、実Codex smokeのファイルアクセス隔離は先述したLinux Docker構成に統一します。Codex自身のsandbox設定はその内側で固定し、ホストとの読み取り禁止境界の代わりとしません。

## CLI契約

### 単一deterministic case

```bash
python scripts/skills/evals/agent/run.py \
  --suite deterministic \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --output-root .agent-eval-runs/run-001 \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

### 単一semantic case

```bash
python scripts/skills/evals/agent/run.py \
  --suite semantic \
  --skill test-case-design \
  --eval-id TC-SEM-001 \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --output-root .agent-eval-runs/run-001 \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

`--agent-command`はCLIの最後に置き、後続値をそのままargvとして扱います。live実行では`--skill-revision`に存在するfull commit SHA、`--execution-profile`にEvaluator-onlyの非秘密設定JSONを指定します。`--agent-name` / `--agent-model`はprofileと実効設定照合結果に一致する必要があります。既存semantic CLIの`--judge-command`と同じ方式にします。

### Skill単位batch

```bash
python scripts/skills/evals/agent/run.py \
  --suite semantic \
  --skill test-case-design \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --output-root .agent-eval-runs/run-001 \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

`--eval-id`省略時は、指定Skillの対象suiteに定義された全caseを実行します。

### 全Skill batch

```bash
python scripts/skills/evals/agent/run.py \
  --suite deterministic \
  --skill all \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --output-root .agent-eval-runs/run-001 \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

`--skill all`は明示指定時だけ許可します。既定で全caseを外部LLMへ送信しません。対象caseは固定Evaluatorのmanifestと候補revisionのSkill集合の対応から取得し、未評価Skill / caseは理由付きで結果に残します。

### 複数回実行

`--repeat N`を任意指定できるようにし、既定は1とします。

同一caseを複数回実行した場合も独自の平均点は作りません。attemptごとの既存eval結果と、pass / needs_review / fail / execution errorの件数だけを集計します。

### 実Agent metadata

実Agentを起動するcommandでは、`--agent-command`より前に少なくとも次を明示します。

```text
--agent-name <agent name>
--agent-model <model identifier>
```

`--agent-version`は任意です。安全に取得できる場合だけ指定または記録します。

### qa-training-store固定scenario

フェーズ2は同じ`executor.py`を使いますが、既存Eval datasetとは別入口にします。`--repeat N`（既定1）を受け付け、各attemptで独立したsanitized target / Agent session / verifier / Judgeを使用します。

```bash
python scripts/skills/evals/agent/qa_training_store.py \
  --scenario qa-training-store-checkout-payment-web-v1 \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --repeat 2 \
  --target-root ../qa-training-store-eval-target \
  --output-root .agent-eval-runs/qa-training-store-baseline \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

`--target-root`は指定revisionをcheckoutしたcleanなGit working treeを要求します。Evaluator checkoutもcleanで、skill packageは別の`--skill-revision`のtracked contentから配置します。Evaluatorはそのworking treeを直接変更せず、指定revisionのtracked contentからsanitized targetを作ります。

この入口は`qa-training-store`の初回scenario専用です。任意repoを動的に登録するplugin機構は作りません。

## semantic評価時のAgent command

v1では生成AgentをCLI末尾の`--agent-command <argv...>`で起動し、Judgeは`--execution-profile`の`judge.command_argv`に定義した**独立したargv**で起動する。`judge.command_argv`は1個以上の非秘密文字列からなる配列で、`shell=True`は使わない。semantic runで欠落・空配列なら事前検証で停止する。deterministic runではJudgeを起動しない。

JudgeのcwdはEvaluatorが作成する`evaluator-judge-workspace`に固定する。固定Evaluator版`build_judge_prompt()`で構築したEval Input / Reference / rubric / Candidate OutputをUTF-8 stdinで渡し、stdoutには既存`semantic/result.py`が解釈できるJudge JSONだけを返す。`judge.timeout_seconds`は正の整数で、初回Codex Judgeの既定は600秒とする。終了コード非0・timeout・JSON不正はJudge execution errorにし、生成Skillの品質FAILへ変換しない。

**新ランナーの両フェーズは、既存`semantic/run.py`をsubprocessとして起動しない。** 固定Evaluatorの`build_judge_prompt()`と`normalize_judge_response()`を直接再利用し、共通`executor.py`がJudge subprocessのstdin・stdout・timeoutと終了を管理する。フェーズ1は従来どおり各semantic caseを1回採点する。フェーズ2では同じ固定Judge profile / `judge.command_argv`を使いつつ、`QTS-SEM-001/002`と`QTS-SEM-003..010`を**独立した2回のJudge呼び出し**とし、後者のCandidate Outputには検証済み`qa_artifact`本文と必須成果物欠落表示だけを渡す。`routing[]`・`final-message.md`・固定機械判定要約は`001/002`側だけに渡し、rubricも各呼び出しの対象criterionだけを含める。Linux / POSIXでは`start_new_session=True`でprocess groupを作り、timeout時にgroup全体へTERM・必要ならKILLする。Windowsでは子孫を含むprocess treeを`taskkill /T /F`等のOS機能で終了する。Docker Judgeの場合はlauncherが実行中コンテナを`docker rm -f`で終了・削除する。終了確認、出力サイズ制限、安全化を行い、エラーattemptを保存して次caseを継続する（共通環境自体が実行不能なら停止）。既存の単独用`semantic/run.py`は変更せず、Judgeコマンドのstdin / JSON stdout / result正規化契約を共有する。

実Codex smokeのJudgeは**生成Agentとは別の使い捨てDockerコンテナ**に固定する。生成側とは別の一時`CODEX_HOME`に、秘密を含まない固定`config.toml`と必要最小限の認証だけを配置する。固定image digest、Codex CLI version、model ID、推論設定、tool / MCP、sandbox / approval、web検索の無効化をpreflightで照合する。Judgeコンテナにはsanitized target・Agent側workspace・Agent側`CODEX_HOME`・Evaluator checkout・Docker socketをmountせず、stdinで受け取るJudge promptだけを評価入力とする。Judge側に必要な`/tmp`等の一時領域を用意し、モデルAPI以外のtoolは評価に使用しない。Judge専用launcherは`codex exec --json`の進行ログを分離し、最終Judge JSONだけを共通executorのstdoutへ返す。生成launcherと同一のargvやcontainerを流用しない。

Judgeの非秘密command fingerprint、image / CLI / model / 推論設定、実効tool / MCP・指示の確認根拠、stdout変換、timeout / cleanup結果をprovenanceへ記録する。Judgeの追加Skill・外部指示・MCP等を確実に排除したと確認できないrunは`unverified`として直接比較しない。非公開のprovider-side model更新は確認済み設定と区別して制約として記録する。別モデルを使うときは`judge.command_argv`を含むprofileを明示的に変更し、条件の異なるrunは直接比較しない。

フェーズ2は各Judge応答のJSONを対象criterion ID集合で別々に`normalize_judge_response()`へ通し、余分・不足・重複したcriterionを拒否する。両応答の生`criteria[]`を固定順に結合したJSONを**全10criterionの`normalize_judge_response()`へ1回渡して**唯一の最終verdictを導出する。部分結果のverdictを別の総合点や独自集計式で混ぜない。どちらかのJudgeに非0終了・timeout・JSON不正・criterion集合不一致があれば全体の意味評価は検証済みPASSとせずJudge execution errorに分類し、得られた途中結果は診断用に限って保存する。両方のprompt / response、投入した成果物manifest、各入力区分・SHA-256、判定をattemptへ記録する。Judge timeoutは呼び出しごとに適用し、独立session / processを使う。

既存`semantic/run.py --judge-command`のstdin・stdoutと`result.py`の正規化を再利用し、独自の採点frameworkは追加しない。保存済み成果物だけの再採点には既存`semantic/run.py`を引き続き使用できる。
生成とJudgeの実行は次の独立した経路に固定する。

```text
生成: CLI --agent-command → Docker内Agent → output.md / QA成果物
採点: フェーズ1は既存semantic caseを1回Judge評価。フェーズ2はworkflow(001/002)・QA成果物(003..010)の各Judge prompt生成 → 各々profile.judge.command_argv（独立process / session） → criterion集合を個別検証 → 10件を結合 → 既存result.pyで全体判定
```

## 結果保存

既存の評価run成果物は変更しません。改善工程は同じ`--output-root`配下の`improvement/`に`analysis.json`・`analysis.md`、検証済み候補と`review-pending/`、修正・再評価結果を別保存します。分析Agentによる原判定の上書きは禁止します。

`--output-root`配下へ、少なくとも次を保存します。

```text
<output-root>/
├── result.json
└── <suite>/
    └── <skill>/
        └── <eval-id>/
            └── attempt-01/
                ├── output.md
                ├── agent.stderr.log（安全化できる場合のみ）
                ├── grade.json
                └── grader.stderr.log（安全化できる場合のみ）
```

`result.json`には、評価結果に加えて変更前後を同条件で比較できる非秘密のprovenanceを保持します。

最低限、次を保存します。

- suite
- Skill
- eval IDまたはscenario ID
- attempt番号
- 評価対象`qa-workflow-skills` Skill commit SHA、候補revisionから検出したSkill名集合、配置したSkill package fingerprint、固定Evaluatorの評価case集合との対応（対象・対象外とその理由）
- 評価基準であるEvaluator commit SHAと固定grader / 固定共通機械判定 / Judge prompt・dataset / rubric / Referenceのfingerprint。フェーズ2のJudgeは2系統それぞれのprompt / response・criterion集合・入力hashも別々に記録する
- 候補Skill revision由来のproduction verifier / generator・assetsのfingerprint（候補ごとの鮮度 / 再現性の照合用。固定graderのfingerprintとは別項目）
- 評価データセットまたはscenario定義のfingerprint
- 評価入力のfingerprint
- target repoを使う場合はrepository名とsource revision
- Agent名
- Agent model
- Agent / Judgeの非秘密実効設定profile fingerprintと検証結果、隔離preflight結果、Tool / MCP / user-global指示の扱い
- Skill投入の検証済みrevision・file hashと、内部実使用の観測（`observed` / `unverified`）・根拠pathを別々に保存する
- Agent versionを安全に取得できる場合はそのversion
- semantic評価ではJudge専用command・cwd・実効profile・その確認結果
- Agent commandのexit code
- Judge commandのexit code・timeout / process tree cleanup状況（semantic時）
- graderのexit code
- deterministic statusまたはsemantic verdict
- 各保存fileの相対path
- 実行日時

`--agent-name`と`--agent-model`は実Agent runでcallerが明示し、profileと照合した結果へ保存します。Agent / Judgeの実効構成、隔離の検証根拠、未確認要素も同時に保存します。`--agent-version`はcaller指定または安全に取得できる場合だけ保存します。Agent command全文からmodelやversionを推測しません。

評価データセットのfingerprintは、選択caseの**固定Evaluator revision**にある入力・期待値 / Reference・rubric等、評価判定に影響する内容からEvaluator側で算出します。採点に使うvalidator / prompt builder / result normalizer等のソースはEvaluator SHAと別に内容fingerprintも持ちます。fingerprintだけをrun結果へ保存し、Reference / expected本文をAgent-visible workspaceへコピーしません。

環境変数、認証情報、token、Agent command全体は保存しません。stdout / stderr等の保存対象はサイズ・内容を検査し、秘密を含む可能性のある生ログを無条件に永続化しません。必要な診断が安全に残せない場合はログ欠落理由を記録します。

### 比較可能性の条件

Skill修正前後を比較するときは、少なくとも次が一致するrunを同条件として扱います。

- target repo / target revision、または同じEval case
- 評価入力fingerprint
- 評価データセット / scenario fingerprint
- Agent名 / modelと検証済み実効実行profile（推論設定、CLI version、tools / MCP / 指示、sandbox等）
- 評価側Evaluator SHA・固定grader / 共通機械判定 / Judge prompt・rubric / Reference fingerprint（フェーズ2は2系統のJudge入力構築規則を含む）
- Judge実効条件とその検証結果
- 情報隔離の成立条件と検証結果
- 実行回数の扱い

比較対象として変えるのはSkill packageのrevisionとその内容fingerprintだけです。Skill数の増減自体は比較を一律に拒否する理由にせず、同じ固定Evaluatorと同じcaseが両revisionで評価できる範囲のみを比較します。一方のrevisionに存在しないSkill / caseや固定Evaluatorに評価caseがないSkillは未評価として明示し、その部分を改善・悪化・変化なしと判定しません。Skillの不存在はschema / 機械契約の`evaluator_incompatible`とは区別します。共通評価caseがない場合、当該比較は`not_comparable`です。**候補側production verifier / generator / assetsはSkill packageの一部なので、そのSHAの差は許容する**。候補ごとに同revision由来sourceで隔離再実行して鮮度・再現性を確認し、固定Evaluatorの採点規則と混同しない。候補のschema / 機械契約が固定Evaluatorと互換でない場合に限り該当部分を`evaluator_incompatible`とする。EvaluatorのSHAと採点基準は変えません。いずれかの設定が違う、未検証、またはSkill packageが同一なら、Skill変更による改善・悪化とは断定しません。provider側の隠れたmodel更新やSkill読み取りが観測不能な場合も限界を明記します。

今回、比較結果の自動rankingや独自総合scoreは作りません。保存済みrunを人間または別Agentが以下の規則で比較できれば目的を満たします。

`.agent-eval-runs/`は`.gitignore`へ追加し、実Agent出力・ログ・Judge結果を通常commit対象にしません。

### 保存済み結果の比較・改善判断

新しい独自スコアや統計検定は作りません。既存の比較条件・criterion別結果・証拠を機械的に照合し、改善の成否を検証します。分析Agentは原因仮説・修正案を作成しますが、自動修正に進むかどうかは[改善Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)の全条件で決めます。未確認・矛盾・再評価失敗はレビュー待ちに残します。

1. 同じEvaluator・target / Eval Input・Agent / Judge modelと実効profile・`agent.timeout_seconds` / `judge.timeout_seconds`・隔離・repeat条件を満たすrunのみ並べる。各criterionのrating・根拠、固定機械判定、execution error、evidence未確認、Skill使用観測を区別して表示する。
2. `--repeat 1`は配線確認・個別問題検出用に許可する。LLM品質の改善・悪化・変化なしの傾向を判断する際は、**両revisionを同じ条件でそれぞれ2attempt以上**実行し、すべての個別結果を確認する。比較前に回数を決め、attempt番号を同じ乱数条件の対として扱わない。2回で判断できる保証はなく、ばらつきが残れば判断不能とする。
3. **改善**：重要criterionまたは機械品質の向上が比較したattempt群で一貫し、他の重要観点に明確な悪化がない。**悪化**：重要観点の低下が一貫している。**変化なし**：確認した観点で実質的な差が検出されない（品質が同一である証明ではない）。**判断不能**：結果が相反する、改善と悪化が重要観点で混在する、証拠・比較条件が不足する、またはSkill改修の判断に必要な実使用が観測できない。
4. 成果物品質の差と**Skill改修効果**は別に結論を書く。Skill改修効果として上記三分類を採用するには、フェーズ1は変更対象Skill、フェーズ2はroutingされた変更対象Skillについて、双方のrunで読取・適用に関する実行証拠が必要。観測不能なら成果物比較は残すがSkill改修効果は判断不能。使用証拠があっても厳密な因果関係や統計的有意差を主張しない。
5. 判断には対象criterion、両revisionのattempt件数と結果・証拠・矛盾点を明示する。多数決やPASS数だけで自動的に改善・悪化へ分類しない。

### 判定結果と比較可否の分離

既存graderの`pass / needs_review / fail`、Agent / Judge / grader実行エラー、`evidence_unverified`、`isolation_unverified` / `not_comparable` / `evaluator_incompatible`を別々に保存する。必須QA成果物の実際の未生成、verifier未実行が信頼できるtool traceで確定した場合、`valid=false`を完成扱いした場合、固定機械判定の重大な失敗はSkill品質の非passとする。**request / result・trace欠落だけで未実行か判断できない場合**や、成果物が実在するが登録・分類不能な場合は`evidence_unverified`として理由を記録し、Skill品質failへ転記しない。

attemptの結果は**品質結果（semantic / deterministic / fixed machine）・証拠検証・比較可能性**を別軸で保持し、外部へ返す`attempt_status`を次の規則で導出する。

- `pass`：適用される全品質基準がpass、必須QA成果物の識別・production verifier / fixed machineの必要証拠・workflow最終判断が検証済みであり、採点と証拠検証が最後まで完了している場合のみ。フェーズ1のケースにフェーズ2固有の必須成果物を要求しない。
- `needs_review`：semantic等はpassでも、必須runtime証拠の`evidence_unverified`、QA成果物登録の分類不能、final response証拠欠落、`evaluator_incompatible`により必要な品質観点が未検証である場合。または通常の品質`needs_review`の場合。既に確定したsemanticのpassは保管するが、attempt全体を検証済みpassとしない。
- `fail`：確認済みの品質判定がfailの場合。ただし証拠取得の欠落・Evaluator内部I/O失敗だけからfailを作らない。
- `execution error`：Runner準備・Judge実行・capture処理・候補verifier隔離実行・Evaluator I/Oの失敗等で評価を正常に実施できない場合。既存CLIと同じexit code 2へ対応する。agentが正常に証拠を保存しなかった可能性と、Runner自身の記録処理失敗は診断理由で区別する。

直接比較の可否は`attempt_status`とは独立に、固定Evaluator / Skill投入 / target / Agent / Judge条件とOS隔離などの一致で判断する。特に内部Skill読取が`unverified`でも成果物の品質比較は可能だが、Skill修正が原因だとは確定しない。証拠未確認のattemptを「全観点の検証済み改善」とは報告しない。
Run同士の比較成立確認は**2つの保存済みrunの共通条件の照合**で行い、ファイル名や同じmodel名だけから同条件と判断しない。repeatの各attemptと対象Skill使用観測の状態も比較表示に残す。

## exit code

既存評価ランタイムと意味を揃えます。

```text
0: 選択した全attemptが検証済みpass（品質・必須証拠がすべて成立）
1: 評価処理は完了したがneeds_review / failが1件以上、または必須証拠未確認・部分的Evaluator非互換で検証済みpassにできない
2: dataset / workspace / Agent / Judge / grader / capture / 隔離再実行等の実行エラー
```

Agent commandがnon-zeroの場合、そのattemptではgraderを実行せずexecution errorとして記録します。

batchは途中1件が失敗しても残りcaseを実行し、最後に全体結果を返します。ただし一時実行ディレクトリの作成失敗等、後続caseも実行不能な初期化エラーでは即時終了します。

## 変更対象

### 新規

- `scripts/skills/evals/agent/__init__.py`
- `scripts/skills/evals/agent/executor.py`
- `scripts/skills/evals/agent/run.py`
- `scripts/skills/evals/agent/improve.py`（保存済み評価結果の分析、修正可否判定、隔離修正、再評価、レビュー待ち保存）
- `scripts/skills/evals/agent/prompt_builder.py`
- `scripts/skills/evals/agent/workspace.py`
- `scripts/skills/evals/agent/qa_training_store.py`
- `scripts/skills/evals/agent/target_workspace.py`
- `scripts/skills/evals/agent/scenarios/qa-training-store-checkout-payment-web-v1/scenario.json`
- `scripts/skills/evals/agent/scenarios/qa-training-store-checkout-payment-web-v1/task.md`
- `scripts/skills/evals/agent/scenarios/qa-training-store-checkout-payment-web-v1/rubric.json`
- `scripts/skills/evals/agent/tools/codex_docker_launcher.py`（手動の実Codex smoke専用。共通executorからは外部argvとして呼ぶ）
- `scripts/skills/evals/agent/verifier_capture.py`（フェーズ2に配置する評価専用stdin / stdout記録用。Skill本体を変更しない）
- `scripts/skills/evals/agent/common_runtime_checks.py`（フェーズ2の固定Evaluator共通機械契約。既存validatorの純粋な検査部品を再利用し、候補の`valid`から独立して判定）
- `scripts/skills/evals/agent/README.md`（実行profile、`artifact-index.json`の`routing[]` / `artifacts[]`、成果物品質比較とSkill改修効果の判断規則、未確認時の報告方法を記載）
- `scripts/skills/evals/agent/tests/`
- `tests/skills/evals/agent/`

### 更新

- `.gitignore`
  - `.agent-eval-runs/`を追加
- `EVALS.md`
  - 「Agent実行はgraderの責務外」という既存境界を維持したまま、別層の実Agent評価ランナーを追加したことを記載
  - CLI、情報隔離、実Agent評価とtrigger評価の境界を記載
- `README.md`
  - 現在の「Agent実行と評価対象出力の生成は評価ランタイムの責務外」という説明を、deterministic / semantic grader単体の責務として維持
  - 実Agent評価を行う場合の入口として新ランナーを案内
- `docs/PROJECT_CONTEXT.md`
  - 現在の評価・検証欄へ、実Agent評価ランナーの責務と通常CIでは外部LLMを呼ばない境界を追記
- `.github/workflows/deterministic-output-evals.yml`
  - 新ランナーのcompileとfake Agent unit / repository integration testだけを追加
  - 実Codex等は起動しない

`semantic-output-evals.yml`へ外部LLM実行は追加しません。

## テスト

自動分析・修正可否・安全な隔離変更・レビュー待ち・再評価のfake Agentテストと、実Agentによる1件の修正受入検証を追加します。詳細と正常・拒否・未改善ケースは[改善Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)を参照してください。通常CIで外部LLMは起動しません。

### 共通ランナーunit test

fake Agent subprocessを使って少なくとも次を検証します。

- 固定Evaluator SHAと候補Skill SHAを独立に指定でき、dirty Evaluatorを拒否し、候補Git treeから実ファイルを選択する
- execution profileの必須項目（`agent.timeout_seconds`と`judge.timeout_seconds`は正の整数）・実効設定との不一致・検証不能時の比較不可を確認する
- fake Agentの無応答・子孫process残存を制限時間で停止し、containerを回収してexecution errorへ分類する。batch後続処理を継続し、Agent timeout値の違うrunは同条件として比較しない
- Evaluator-only sentinelのread-denial preflightをfake Agentで検証し、`cwd`変更だけでは合格させない
- Eval Inputがstdin promptへ含まれる
- 対象Skill名とSkill pathがpromptへ含まれる
- Reference / expected / rubricがpromptへ含まれない
- Agent stdoutを`output.md`へUTF-8で保存する
- Agent stderrを安全化できる場合のみ診断ログとして保存し、拒否した場合は理由を記録する
- non-zero exitをexecution errorとして扱う
- `shell=True`を使用しない
- `--agent-command`後続argvを順序どおり渡す
- batchで1件失敗しても残りcaseを継続する
- `--repeat`でattemptを独立保存する
- 候補runtime実装のfingerprintと候補sourceを照合し、固定Evaluator側実装fingerprintへ誤照合しない。既存graderの通常CLIは従来の評価動作を維持する
- フェーズ1 semanticでは生成用Docker launcherをJudgeとして誤使用せず、profileに定義された独立Judge commandへUTF-8 Judge promptを渡す。Judge JSON不正・非0終了・timeoutを実行エラーとして区別する
- 入出力証拠の欠落をSkill品質failにせず`evidence_unverified`と分類する。実際の`valid=false`と区別する。semantic passでも必須runtime / artifact分類・workflow判断の証拠が欠ければattemptが`needs_review`・exit 1となり、Runner障害ならexit 2となる
- 正常・重要欠落・根拠のない動作を含む評価専用fixtureを使い、semantic Judgeの判定方向と根拠を確認する
- 異なるSkill revisionを同じ固定graderで採点し、比較条件が異なる結果は`not_comparable`にする。比較条件一致・成果物品質差・変更対象Skillの使用証拠の有無を別々に報告し、単発の結果・相反する複数attempt・未使用観測ではSkill改修効果を確定しない
- 秘密を含み得るargv・環境変数・生ログがprovenanceに残らない

### 一時実行ディレクトリtest

- 指定SHAのtracked fileだけがmanifestと一致し、dirty working treeのSkillが混入しない。Skill集合は候補Git tree内のtracked `skills/<skill>/SKILL.md`から導出され、固定件数や固定リストに依存しない
- 候補revisionから検出した全Skillの`SKILL.md`が存在し、配置manifestと一致する
- `references/` / `scripts/` / `assets/`が存在する場合はコピーされる
- 候補revisionにSkillが追加・削除された場合も、検出した集合だけが配置される。固定Evaluatorのcaseが候補に存在しないSkillを要求する場合は未評価と記録し、単独`--skill`指定ならpreflight errorとする
- 候補Skillに対応するEvaluator caseがない場合は未評価と記録し、評価実行済みと扱わない
- どのSkillにも`evals/`が存在しない
- `scripts/skills/evals/`が存在しない
- `docs/`、`.git/`が存在しない
- 元repositoryのSkill fileを変更しない
- 終了後に一時実行ディレクトリを削除する

### grader接続integration test

repositoryの既存caseを使い、fake Agentで次を自動検証します。

1. deterministic caseを生成し、既存`deterministic/run.py`が実行される
2. semantic caseを生成し、既存`semantic/prompt_builder.py`と`semantic/result.py`の処理が固定Evaluatorから呼ばれ、Judgeは独立argv・cwd・実効設定で起動する。既存`semantic/run.py` CLIは起動せず、そのCLIのstdin / stdout / 判定契約を再利用する
3. `grade.json`へ既存graderの結果が保存される。semanticは生成側と異なるJudge argv・cwdで起動し、Reference / rubricを含むJudge promptを生成Agentに送らない。Judgeのinvalid JSON / non-zero / timeoutを生成Skill品質failに変換しない
4. batch結果が`result.json`へ集計される
5. dataset / input fingerprintとAgent metadataが`result.json`へ保存される

テスト用fake Agentは評価対象ケースの正解ロジックを実装しません。ランナーの配線確認に必要な最小固定応答だけを使用します。

### qa-training-store scenario integration test

外部LLMは起動せず、fake Agentと一時Git repositoryを使って次を検証します。

- source revisionのtracked contentだけからsanitized targetを作る
- 元`docs/PROJECT_CONTEXT.md`を除外し、stable keyを維持する最小Project Contextを生成して既存parser / root解決に通す
- フェーズ2の各`--repeat`で新規target / Agent session / Judgeを作り、前attemptの成果物を再利用しない
- 元`.agents/**` / `.codex/**`、元`AGENTS.md` / `QA_AGENT.md`、過去Plan / report、instructor情報、target側Skill evalをAgent-visible targetへ残さない
- 評価用`AGENTS.md`へ製品仕様や正解QA成果物を混ぜない
- 候補revisionから検出したSkill集合だけをAgent-visibleにする。user/global追加Skill・指示・MCPが有効なrunは比較可能として扱わない
- 親workspaceとSkill packageを実行中読み取り専用mountにし、`.qa-eval-output/**`だけを書込み可能mountにする。sourceを変更して元へ戻す操作も権限で拒否する
- fake Agentの`artifact-index.json`に`routing[]`・`artifacts[]`を保存し、Evaluatorが固定scenarioの要求結果・既存Skill条件・実fileと照合する。必須工程のrouting行なし、根拠のない`skipped`、妥当な`blocked` / `incomplete`、optionalな`question-analysis`、生成済みファイルの未登録、重複・誤scope・cross-attemptをそれぞれ検証し、単なる登録欠落を未生成と扱わない
- symlink / path traversal / output root外参照をrejectする
- output root外にsource変更があるrunを有効評価へ昇格しない。Gitのignored / untrackedを含む全相対pathの許可外新規fileを検出し、`.gitignore`の隠蔽で見逃さない
- target revision / scenario fingerprint / Skill・Evaluator revision / Judge Reference fingerprint / Agent・Judge profileをprovenanceへ保存する
- artifact / verifier request / result / rerun resultの一意対応、欠落・参照差し替えを検出する
- artifact分類により`.runtime-evidence/**`・workflow stateを正規QA成果物から除外し、正規QA成果物の順序とhashを固定する。`QTS-SEM-001/002`用Judgeだけに`routing[]`・`final-message.md`・固定機械判定要約を渡し、`QTS-SEM-003..010`用Judge promptには**これらの専用情報を一切含めない**。後者の正規QA成果物にPayment失敗条件を欠落させ、最終回答に正解を書いたfixtureでも`QTS-SEM-006`が救済されないことを検証する。2応答のcriterion ID重複・欠落・入れ替えを検出し、既存`normalize_judge_response()`で最終判定する。片方だけJudge timeout / 不正JSONになった場合も全体PASSにしない。最終stdoutのみ完了宣言があるfixtureも判定する
- フェーズ2の`QTS-SEM-001..010`をrubricにID / critical / Reference対応ごとに固定し、正常・Payment整合違反・仕様外動作のfixtureの判定を確認する
- `valid=false`同士の再実行一致をPASSにしない。`workflow_runtime.py`の実行成功とcompletionを区別する。候補verifierだけを弱体化して`valid=true`を返すrevisionでも、固定Evaluatorが不正なID・参照・graph・closureをFAILにする
- 元repoの`docs/PROJECT_CONTEXT.md`等をAgent-visible環境から読み取れないことを実環境の隔離検証で確認し、Agent-visibleなProduct Spec / Skill packageへのwrite-denialを検証する
- cleanup後にsanitized targetが残らない

### 品質差を検出できることの受入検証

固定Evaluator・rubric・Referenceを使い、(1)規範仕様に根拠を持つ正常なQA成果物、(2)Checkout / Paymentの重要なBR / AC・境界条件を意図的に欠落させた成果物、(3)根拠のない動作を追加した成果物を**Evaluator-only fixture**として採点する。期待方向は正常例がpass、重要欠落・捏造例が該当critical criterionで低評価または`needs_review` / `fail`となり、その根拠が規範Referenceに追跡できることとする。既存semantic prompt builder / normalizerは利用するが、Judgeの文章が存在するだけで成功にしない。結果が期待方向と異なればrubric / criteriaを修正し、同じ固定条件でfixtureとbaseline / candidate両方を再実行する。恣意的な「総合点」は導入しない。

deterministicではruntime実装だけを変更した候補（payload / schema / 結果意味は同一）を用い、旧Evaluator graderの固定assertionで**候補sourceと整合するfingerprint**を受け入れつつ、改ざんされたfingerprintと不正なpayloadは検出することを確認する。互換性のないfixtureでは該当機械criteriaだけ`evaluator_incompatible`となり、意味品質の判定を失わないことも検証する。同一Skill / model / inputの`--repeat`で結果の揺れを個別attemptに残し、差を無条件に改善と呼ばないことを検証する。


### 追加の比較・隔離検証

fake Agentで、指定候補SHAの内容と配置manifestの一致、Evaluatorと候補の分離、Judge / grader固定、profile不一致時の拒否、必要な隔離証拠がないrunの比較不可、異なる2つの保存runの比較条件判定を検証する。**候補production verifierだけ内容SHAが異なりschema・結果意味が互換な2 revisionは比較可能**とし、共通graderやrubricが異なれば比較不可、schemaが非互換なら該当criteriaのみ`evaluator_incompatible`となることを確認する。候補generatorの隔離再実行では`scripts/**` / `assets/**`を同revisionから検証して配置し、`ui_pattern_candidates.py`の正常実行・静的データ欠落時の環境エラー分類を確認する。変更されたSkill packageと同一packageの別Git SHAを区別し、後者を改善検出実績に数えない。

live Codexでは、実効設定の確認とEvaluator-onlyの非秘密sentinel読み取り拒否を含めて検証する。2つの異なるSkill package revisionを同じEvaluator / dataset / profileで実行して比較可能なprovenanceを保存する。実Agentが意図するSkillを読み取ったか観測できない場合はその制約を報告し、成功扱いしない。

## このブランチで行う実Agent検証

実装後、同じ`feat/agent-eval-runner` branch上で実Codexを使ったsmokeを実施します。

実行前にローカル`codex exec --help`で非対話・stdin・sandboxの現在利用可能なflagを確認します。ランナー実装へそのflagを埋め込まず、`--agent-command`へ渡します。

最低限、次の4 caseを実行します。

### 1. `TC-OUT-001`

- suite: deterministic
- Skill: `test-case-design`
- 目的: 単純な正規出力生成 → deterministic grader接続を確認

### 2. `TCN-OUT-001`

- suite: deterministic
- Skill: `test-condition-design`
- 目的: Pairwise制約を含むケースで、Skill指示・Skill-local決定論処理を利用できる状態から生成し、既存validatorで評価できることを確認

### 3. `TC-SEM-001`

- suite: semantic
- Skill: `test-case-design`
- 目的: 実Agent生成 → 独立Judge invocation → semantic verdict保存まで確認

### 4. `WF-SEM-003`

- suite: semantic
- Skill: `qa-workflow`
- 目的: 単一成果物だけでなくworkflow routing責務を持つSkillでも共通ランナーが機能することを確認

実Agent smokeの結果は`.agent-eval-runs/`へ保存し、commitしません。

実Agentのsemantic結果が`needs_review` / `fail`になった場合、ランナーが正常に生成・評価・保存できていればランナー実装失敗とは扱いません。ただし結果を無視せず、Skill / Eval Input / Reference / Judgeのどこに原因があるかを別途確認できる状態で報告します。

## フェーズ2: qa-training-store固定対象の統合評価

フェーズ1の実Codex smokeが完了した後、同branch上で `qa-training-store` の固定revisionを対象に実Agent統合評価を実施します。

詳細な対象準備、Checkout / Paymentの評価範囲、既存 `.agents/skills/` との分離、source変更検出、workflow / traceability / semantic評価条件は [`2026-10-03_132700_agent-eval-runner_02_qa-training-store-integration-eval.md`](./2026-10-03_132700_agent-eval-runner_02_qa-training-store-integration-eval.md) に従います。

フェーズ1のランナーは、このフェーズを見越して「入力準備」「Agent execution」「成果物保存」「評価」を分離します。ただし任意repo向けplugin frameworkは作りません。

## 実際のSkill改善と再評価の受入検証

共通ランナーとフェーズ2の固定scenarioが動作した後、**実Agentが生成したQA成果物の品質を改善できるか**を1件以上実証する。既存の2 revisionの比較や、意図的に不正を混入したEvaluator-only fixtureの判別だけでは、この受入検証を満たしたことにしない。今回は、この受入検証を自動分析・許可判定・隔離修正・再評価の機能検証としても使用する。採用・push・mergeは自動化しない。

1. **実際の問題を選ぶ**：フェーズ2の固定Checkout / Payment scenarioの実Agent baselineから、固定grader / Referenceと原成果物で裏付けられた**修正可能なSkill起因の品質問題**を分析Agentが選ぶ。対象criterion・違反根拠・該当Skill・実行条件を保存し、機械的な許可条件で自動修正可能か判定する。判定不能な場合はレビュー待ちにする。Agentの単発のばらつき、Judgeの誤判定、証拠欠落、Evaluator / 実行環境の障害だけをSkill欠陥と見なさない。**わざと壊したSkill・人工的に劣化させたbaseline・Evaluator-only fixtureを改善実証の対象にしない**。
2. **baselineを確定する**：修正前Skill revisionを40文字Git SHAと内容fingerprintで特定し、同じ固定Evaluator / datasetまたはscenario / target / Agent・Judge実効profile / 隔離条件で**2attempt以上**評価する。改善対象に選んだ失敗が再現せず、品質問題と認められない場合は改善実証に使わない。実行結果・原成果物・Judge evidenceと機械判定・Skill使用証拠を保存する。
3. **Skillだけを修正する**：機械的な自動修正条件が全て成立する場合は隔離した修正Agentが、成立しない場合はレビュー待ちとし、人間の判断後に、判明した原因に対して**該当Skillの`SKILL.md` / `references/**` / `scripts/**` / `assets/**`の必要な箇所だけ**を修正する。変更内容と根拠、既存Skillの契約 / portability / 関連テストへの影響を確認する。実行用の固定Evaluator checkout、rubric、Reference、grader、target revision、scenario、Agent / Judge設定を改善効果が出るように変更しない。評価対象の候補は**PR #17の実装branchとは別のローカルworktree / branchでcommitして、独立した候補Git SHAを作る**。改善候補をこのPRへ自動取り込み・push・採用しない。
4. **同条件で再評価する**：変更後の候補revisionについて同じ固定条件で**2attempt以上**の実Agent評価を実施する。変更前後は候補Skill revision以外の比較条件を一致させ、両revisionのSkill使用観測・個別criterion ratingと根拠・固定機械判定・runtime証拠・実行エラーを比較する。候補sourceの実装fingerprint差だけでFAILにせず、互換性が失われたcriterionを品質改善に数えない。Evaluator基準の不具合が見つかり改訂を要するときは、**修正後の単一Evaluatorでbaseline / candidate双方を最初から再実行**する。
5. **改善成立を確認する**：対象とした重要criterionまたは固定機械品質について、複数attemptの評価・原成果物・規範根拠から**一貫した実質的な向上**が確認でき、他の重要criterionや既存契約に明確な回帰がなく、修正対象Skillの実使用証拠が両revisionにある場合のみ「Skill改善を実証」と報告する。PASS件数だけ、Judgeによる印象評価、総合点、1回の偶然のPASSでは実証しない。修正後の通常Skillテストと必要な回帰テストも実施する。使用証拠・評価結果が不十分または矛盾する場合は、成果物品質の比較とSkill改修効果を分けて「判断不能」と記録する。
6. **未達を隠さない**：初回に改善が認められなければ原因を確認し、既存の受入検証範囲で有効な問題・修正候補があるなら再検証する。実際に改善を確認できない、または修正可能な実問題が見つからない場合は**「ランナー・比較機能は検証済み／実Skill改善の実証は未達」**として、対象run、試した変更、根拠、障害と残課題を明記する。架空の失敗や基準緩和で達成扱いにしない。

各baseline / candidateのGit SHA、Skill差分、選定した失敗と修正根拠、2attempt以上の結果、比較条件・実使用観測、改善・回帰の判断および未達理由を**既存の`.agent-eval-runs/`のrun結果を参照する検証記録**として残す。秘密情報を含み得る生ログは既存の保存規則に従い通常commitしない。専用の自動改善ループ・ランキング・新しいDBは作らない。

## 既存検証

実装後は少なくとも次を実行します。

```bash
python -m compileall -q scripts/skills/evals/agent
python -m unittest discover -s scripts/skills/evals/agent/tests -v
python -m unittest discover -s tests/skills/evals/agent -v

python -m unittest discover -s scripts/skills/evals/deterministic/tests -v
python -m unittest discover -s tests/skills/evals/deterministic -v
python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v

python scripts/skills/evals/semantic/validate.py
python -m unittest discover -s scripts/skills/evals/semantic/tests -v
python -m unittest discover -s tests/skills/evals/semantic -v
python -m unittest discover -s tests/skills/evals/trigger -v

git diff --check
```

既存Skill仕様適合検証も実行します。

## 実装順序

共通ランナーとフェーズ2の評価を成立させた後、保存済みrunを使った`improve.py`の分析・振分け、修正Agentの隔離実行、関連テスト・同条件再評価を追加します。分析・修正を行うときもEvaluatorとtargetの固定境界を変更しません。

1. branch開始時点が基準`main`から意図しない差分を持たないことを確認する
2. 固定Evaluator checkoutのclean状態・grader / Judge条件を確定し、候補Skill revisionのtracked contentから一時実行ディレクトリを作る
3. workspaceと実効OS境界のread-denial、余分なuser / global設定・Skill / MCPを排除するpreflightを定義し、fake Agentで失敗時の分類を固定する
4. `prompt_builder.py`で生成prompt契約を実装し、Reference / expected / rubricを渡さないtestを追加する
5. `run.py`へ単一caseのAgent subprocess実行と成果物保存を実装する
6. deterministic単一caseを既存graderへ接続する
7. semantic単一caseを固定Evaluator側graderへ接続し、生成用`--agent-command`とprofileの`judge.command_argv`を**別process・別cwd・別Docker環境**で起動する。共通`executor.py`がtimeout時に子孫process / containerを停止し、Judge errorを別軸で保存する。両stageの実効設定を記録する
8. Skill単位batch、`--skill all`、`--repeat`、結果集計、exit codeと、Evaluator固定・Skill SHA・実効設定profile・隔離preflightによる比較可否判定を追加する
9. fake Agentを使った共通unit / repository integration testを完成させる
10. `.gitignore`、`EVALS.md`、`README.md`、`PROJECT_CONTEXT.md`を現在実装へ同期する
11. GitHub Actionsへ外部LLMを使わないcompile / testだけを追加する
12. 既存評価・runtime・trigger検証を全件実行する
13. 同branch上で実Codex smoke 4 caseを実行する
14. 実Codex結果とrunnerの保存物を確認し、runner起因の未達が0件であることを確認する
15. フェーズ2補助Planに従い、`qa-training-store`固定revisionから元Project Contextを除いた使い捨て評価対象を準備し、評価用`AGENTS.md`とProject Contextを生成する
16. 対象repo固有のAgent Skill集合を評価条件から除外し、候補revisionから検出したSkill集合だけをAgent-visibleにする
17. Checkout / PaymentのWeb範囲で実Agent分析・設計workflowをattemptごとに実行し、source無変更、runtime証拠と成果物の対応、traceability、workflow状態、固定Referenceでの意味品質を評価する
18. フェーズ1 / フェーズ2の結果を分離して保存し、runner起因の失敗とSkill品質上の非passを区別して報告する

## 対象外

今回追加しません。

- 新しいAgent Skill
- Skillの無制限な自動修正・原因不明案件の自動修正
- Skill変更候補の自動採用・push・PR作成・merge
- 自動branch作成 / commit / PR作成
- Skillなし / Skillありの自動A/B比較
- mainとbranchの自動ランキング
- 独自総合スコア
- 外部LLMを使う通常CI job
- scheduled Agent eval
- MCP server
- SQLite / PostgreSQL
- 独自Agent runtime
- LangGraph等のworkflow framework
- Codex / Claude Code専用SDK依存
- Codex固有flagのハードコード
- native Skill trigger観測のクライアント別adapter
- 新しいサンプルアプリ
- `qa-training-store`以外を含む複数target repo向けplugin framework
- フェーズ2初回でのNative / 実ブラウザE2E評価

Skillなし / Skillあり比較やmain / candidate比較は、今回保存するcase単位結果を使って2回のrunを比較すれば手動で実施できます。比較作業が継続的なボトルネックになった場合に、比較専用処理を追加します。

native trigger評価は、Skill activationを観測する方法がAgentクライアントごとに異なるため今回の共通ランナーへ含めません。既存trigger datasetとvalidationを維持し、実クライアントでの発火自動測定は別の課題として扱います。

## ポータビリティ条件

次をすべて満たすことを必須とします。

- 通常のSkill実行に`agent`評価ランナーが不要
- `SKILL.md`へCodex / Claude Code等の評価用commandを追加しない
- Skill-local scriptから評価ランナーをimportしない
- Agent固有SDKを共通評価ランナーへ追加しない
- Agent commandは外部argvとして注入する
- 評価対象成果物は既存Markdown契約のまま
- deterministic / semantic graderの正規契約を変更しない
- 1 Skillだけを移植する既存ポータビリティtestを壊さない

## 完了条件

次をすべて満たしたら、この実装を完了とします。

- 固定Evaluatorのclean checkoutから異なるSkill revisionを選択でき、候補Git treeの配置内容とmanifestが一致する
- 候補Skillのevalを採点へ混入させず、grader・Judge / Referenceを固定Evaluatorに統一し、候補のproduction verifierは候補の信頼済みsourceで再実行できる
- 生成Agent / Judgeが独立argv・cwd・非秘密実効profileを使い、必須のローカル隔離条件を確認できないrunを比較可能としない
- 実Agent評価ランナーが追加されている
- 単一deterministic caseを「実Agent生成 → 既存grader」まで1 commandで実行できる
- 単一semantic caseを「実Agent生成 → 独立Judge → 既存semantic判定」まで1 commandで実行できる
- Skill単位batchを実行できる
- `--skill all`を明示した場合だけ固定Evaluatorと候補Skill集合に共通する全case batchを実行でき、対象外のSkill / caseは理由付きで記録する
- `--repeat`で同一caseを複数回独立実行できる
- AgentへReference / expected / rubric / validatorを公開しない一時実行ディレクトリと、読み取り禁止が実証された隔離境界を使用する。Product Code / Test / Spec / Skillを実行中読み取り専用にし、出力root以外への書込みを拒否する
- 一時実行ディレクトリに候補revisionから検出したSkill集合の通常実行ファイルが存在し、Skill集合の増減を固定件数のassertionなしで検証できる
- 実Agent commandを特定プロバイダーへ固定していない
- `shell=True`を使用していない
- Agent出力、grader結果、全体結果を保存でき、stderrは安全化できる場合のみ保存し、除外した場合は理由を記録できる
- 認証情報や環境変数を結果fileへ保存していない
- `.agent-eval-runs/`がgit管理対象外になっている
- fake Agentを使うrunner unit / integration testがpassする
- 既存deterministic / runtime / semantic / trigger testがpassする
- 通常GitHub Actionsで外部LLMを呼ばない
- Linux Docker上の実Codex smokeで、image / CLI / 認証・必要なモデルAPI通信・Evaluator-only領域の読み取り拒否とsource / Skillの書込み拒否・Judge独立実行・非秘密実行profileを検証している。公開資料へのegress制御の有無は残留リスクとして記録し、それだけを理由に比較不能としない
- `TC-OUT-001`、`TCN-OUT-001`、`TC-SEM-001`、`WF-SEM-003`を実Codexで同branch上から実行し、生成・保存・grader起動・結果集計まで完了する
- 実Codex smokeでrunner起因の未処理エラーが0件
- 実Codexの非pass結果がある場合、その結果を隠さず保存・報告できる
- 各live runにSkill revision、評価入力 / scenario fingerprint、Agent名 / model等の比較に必要なprovenanceが保存される
- 2つの実runでEvaluator・入力・Judge・`agent.timeout_seconds`を含む実効Agent profile・隔離・repeatを照合する。成果物品質の比較とSkill改修の効果判断は別々に記録し、改修効果は変更対象Skillの使用証拠と複数attemptの一貫した根拠がある場合だけ判断する。未観測・矛盾する場合は判断不能とし、厳密な因果証明は主張しない
- **自動分析・機械的な修正可否判定・レビュー待ち保存が成立し、条件に合致する実際のSkill欠陥をbaseline評価から1件以上特定して、隔離した修正Agentが候補revisionを作り、同条件で再評価する受入検証**を実施している。比較する各revisionを2attempt以上評価し、重要品質の改善・回帰・使用証拠を原成果物と固定Referenceから確認できる。改善が確認できない場合は未達として記録し、実改善の証拠なしにPlan全体の改善実証を完了扱いしない
- 同一Evaluatorで正常・重要欠落・捏造のQA成果物を判別できた根拠とrepeatの揺れを保存する
- 互換なruntime implementation更新がfingerprint相違だけを理由に非passとならず、真の契約非互換を個別criteriaへ区分できる
- `qa-training-store`固定revision `84ce165493649550832731a60cf436f8ae29c56b` を対象にフェーズ2初回評価と独立したrepeat試行を実行している
- Checkout / PaymentのWeb範囲で実Agentによる分析・設計workflowが完了し、成果物・workflow・traceability・意味評価結果が保存されている
- `qa-training-store`のProduct Code、既存Test、規範仕様に許可外変更がない
- 対象repo既存Skillではなく候補revisionから検出したSkill集合だけをAgent-visibleにし、元`PROJECT_CONTEXT.md`を最小評価用内容へ置換した条件を記録している
- フェーズ2のrunner / environment error、Skill品質のneeds_review / fail、実行証拠の`evidence_unverified`、`valid=false`、比較不可・部分的Evaluator非互換を区別している
- フェーズ2のJudgeは固定rubricを`QTS-SEM-001/002`と`QTS-SEM-003..010`へ分割して別々に実行し、後者へ`routing[]`・最終stdout・固定機械判定要約を渡さない。各応答のcriterion集合を検証後、統合して既存result正規化で全10件を判定し、部分失敗を全体PASSにしない
- 候補production verifier / generatorのSHAだけが変わりschema・機械契約が互換なら、同じ固定Evaluatorでrunの直接比較を妨げない
- `--analyze-only`で分析・レビュー待ちのみを生成でき、根拠不足・高リスク・非互換・Judge揺れ・実行エラーを自動修正せずレビュー待ちに分けられる。修正許可をLLMの自己申告だけで判断しない
- 修正Agentは隔離したSkill packageの許可pathだけを変更し、固定Evaluator・target・元branchを不変に保ち、修正試行は1回で停止する。改善が確認された差分・候補revision・検証結果を保存するが自動採用しない
- ランナー導入のためにSkill本体の通常実行経路とポータビリティを変更していない。別revisionでの**受入用Skill改善**は既存契約・ポータビリティを維持し、関連テストで確認している
- `git diff --check`がpassする
