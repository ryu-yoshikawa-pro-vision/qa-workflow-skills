# PR #17 残課題の実装・検証結果

## 概要

PR #17 (`feat/agent-eval-runner`) で調査済みだったF02、F03、N03、N04、F04を実装し、既存のN01、N02、N05、N06、F01を現行コードで再確認した。F06としてPR本文冒頭に最新状態をまとめ、従来のDocker/Codespaces記録は履歴として残した。

コード検証対象のHEADは `595a34b75228529951b3a0366a7fbc208bc148e9`。このSHAで5つのGitHub Actions workflowがすべて成功した。作業ブランチは `feat/agent-eval-runner`、PRのbaseは `main`。

コード上の修正とCI検証は完了した。一方、Windows環境制約とDocker内Codexの隔離障害により、正式な実Agent受入は未達である。Judge fixtureの独立承認と、自動Skill改善の実証も完了していない。これらを成功扱いにしたり、セキュリティ条件を緩めたりしていない。

## 指摘ごとの結果

### N01 — Judge承認と評価対象binding

Judge fixtureと評価対象の承認状態・fingerprint bindingが不十分だと、未承認または別内容のfixtureを有効扱いする余地があった。今回の再実装は行わず、`judge_validation.py`、`qa_training_store.py`と関連README・テストを確認した。承認bindingと評価対象fingerprintの照合を維持している。Judge validation / training-store関連テストを含むCIが成功し、未承認fixtureの状態は変更していない。

### N02 — Agent出力symlink

Agent出力をsymlink経由でホスト側の書込み先へ向けられる危険があった。今回の再実装は行わず、`run.py`の隔離処理と関連テストを確認した。Agent SkillsとCodex Harnessを含むCIが成功した。

### N05 — Judge normalizer契約

Judge normalizerとfixture判定の契約が一致せず、正規化結果とfixture条件の解釈がずれる問題があった。今回の再実装は行わず、`judge_validation.py`と`qa_training_store.py`の契約・回帰テストを確認した。関連テストを含むCIが成功した。

### N06 — 未検証Judge結果の保存

未検証のJudge結果を保存時にverified相当として扱う危険があった。今回の再実装は行わず、Judge結果の保存契約と検証状態を確認した。関連テストを含むCIが成功し、未検証結果を承認済みに変更していない。

### F01 — criterion単位の検証状態

複数criterionのJudge検証状態を全体で誤集約する可能性があった。今回の再実装は行わず、criterion単位の検証状態と集約処理を確認した。Judge validation関連テストとCIが成功した。fixtureの人手承認は別途未完了である。

### F02 — Skill修正の原因確認gate

**問題・原因:** 分析JSONのschema適合だけで修正Agentへ進める余地があり、原成果物・Skill実使用・原因帰属・代替原因の排除が修正許可に結び付いていなかった。

**変更:** `improve.py`、`prompt_builder.py`、`tests/test_improve.py`を変更した。独立attemptでの再現、runtime/Judge証拠、Skill実使用、原成果物本文と根拠、Skill仕様との対応、代替原因の解消、単一Skillの許可pathを修正開始前に照合する。分析workspaceには必要な安全化済み証拠だけを渡し、evaluator-only正解・独立期待値・秘密情報を除外する。判断不能は理由付きでreview pendingとし、production経路の結合テストで修正Agentが起動しないことを確認する。

**検証:** `test_run` + `test_improve`は42件中38件成功、4件skip。CIの5 workflowも成功した。

### F03 — 独立回帰による改善判定

**問題・原因:** 対象QTSケースだけで評価が改善すると、独立回帰や通常契約テストを経ずに改善実証へ進む危険があった。

**変更:** `improve.py`、`run.py`、`tests/test_improve.py`、`tests/test_run.py`を変更した。候補生成前に独立case/input/evaluator/Skill/grader/profile/command条件を固定し、期待結果を修正Agentへ渡さない。対象改善、独立回帰なし、関連契約テスト成功、Skill実使用、条件一致、証拠完全性を改善成立条件にする。未実行・未検証の独立評価はpendingに残す。

**検証:** Agent runner/improvement対象テスト42件は38件成功、4件skip。実Agentによる独立評価の受入は後述の理由で未達である。

### N03 — 結果不明の副作用操作

**問題・原因:** 副作用操作の結果が不明でも、試行回数が残っているだけで再試行を認め得た。

**変更:** `skills/exploratory-testing/scripts/exploratory_runtime.py`と`tests/skills/evals/deterministic/test_qa_artifact_graph_skills.py`を変更した。成功・失敗・不明を区別し、不明な副作用操作は状態確認で未適用を確認するまで再試行不可にする。読み取り専用状態確認は継続可能。

**検証:** N03/N04の対象runtimeテスト4件が成功。Agent Skill/CI検証も成功した。

### N04 — Regression履歴の完全性

**問題・原因:** 存在しない、アクセス不能、途中失敗、打切りの履歴rootを完全検索済みと誤認する余地があった。

**変更:** `skills/regression-testing/scripts/regression_runtime.py`と同上の契約テストを変更した。実在する空directoryと未存在rootを区別し、file指定・アクセス/途中エラー・明示的打切りなど、完全に見えていない場合はcomplete扱いしない。

**検証:** N03/N04の対象runtimeテスト4件が成功。deterministic repository契約を含むGitHub CIも成功した。

### F04 — deterministic-only改善経路

**問題・原因:** deterministic graderで直接確認できる失敗まで、Judge未検証を理由に改善入口で一律停止していた。

**変更:** `improve.py`、`run.py`、`tests/test_improve.py`、`tests/test_run.py`を変更した。既存の固定graderで再計算できるdeterministic-only経路を追加し、grader成功、固定revision、原成果物・実使用・原因帰属、同一profile/command、反復結果・trace hash、独立回帰を要求する。semantic/mixed evidenceはverified Judgeが必要で、未検証の意味評価はpendingとする。Agent commandの秘密情報も保存前と再利用時に拒否する。

**検証:** 対象テスト42件は38件成功、4件skip。CIの5 workflowが成功した。deterministic-onlyの実Agent改善を完了したものではない。

### F06 — PR本文の現在状態

**問題・原因:** PR本文の現在状態が実際のbranch HEAD、CI、未達条件から遅れていた。

**対応:** PR本文冒頭に最終report commitのHEAD、修正・検証状況、CI、実Agent/Judge/自動改善の状態、次の対応をまとめ、旧Docker/Codespaces記録は明示的な履歴節の下に保持した。base branchは変更していない。

**検証:** 本文更新後にPRがopen、base `main`、headがreport commit SHAであることを再確認する。

### 変更範囲

- F02: `scripts/skills/evals/agent/improve.py`、`prompt_builder.py`、`tests/test_improve.py`
- F03: `improve.py`、`run.py`、`tests/test_improve.py`、`tests/test_run.py`
- N03/N04: `skills/exploratory-testing/scripts/exploratory_runtime.py`、`skills/regression-testing/scripts/regression_runtime.py`、`tests/skills/evals/deterministic/test_qa_artifact_graph_skills.py`
- F04: `improve.py`、`run.py`、`tests/test_improve.py`、`tests/test_run.py`

N01/N02/N05/N06/F01は既存実装の再確認のみで、今回の残課題修正として重複実装していない。

## テスト・CI

### ローカル検証

- Agent runner + improvement対象 (`test_run`, `test_improve`): 42件、PASS 38、SKIP 4。
- Agent suite全体: 90件、PASS 77、SKIP 7、ERROR 6。
- Agent repository contract: 4件、PASS 4。
- Deterministic harness: 13件、PASS 13。
- Deterministic repository suite: 206件、PASS 181、ERROR 24、FAIL 1。
- Semantic harness: 27件、PASS 25、SKIP 2。
- Semantic repository suite: 13件、PASS 12、SKIP 1。
- N03/N04 runtime focused tests: 4件、PASS 4。
- `compileall` (Agent evaluation package): PASS。
- `git diff --check`: PASS。

Agent suiteの6 ERRORは、WindowsでLinux専用Docker launcherを実行できないこと、Docker image probe executableの起動エラー（WinError 193）、およびWindowsのPython `os.getuid` / `os.getgid`欠如によるもの。deterministic repository suiteの24 ERRORと1 FAILは、ローカルPython環境に`yaml` (PyYAML)がなくvalidatorのimportとそこから呼ぶCLIが失敗したため。PyYAMLを追加導入して環境を変更してはいない。

N03/N04のfocused testは、テスト対象外のvalidator importがPyYAML不足で止まらないよう一時的な`yaml` module stubをテスト起動時に注入して実行した。YAML処理自体の検証には使っていない。

`python scripts/format_tracked.py check`はローカルにRuff executableがなく起動できなかった。GitHub Code Quality workflowではRuffとdprintによるチェックが通っている。

### GitHub Actions

検証HEAD: `595a34b75228529951b3a0366a7fbc208bc148e9`

- Validate Agent Skills (run 1388): SUCCESS。
- Validate Deterministic Output Evals (run 1387): SUCCESS。
- Validate Semantic Output Evals (run 1352): SUCCESS。
- Code Quality (run 82): SUCCESS。
- Codex Harness (run 82): SUCCESS。

過去SHAの結果をこのHEADの結果として流用していない。

## 残課題

### 実Agent受入とDocker隔離

正式な実Agent受入は未達。既存Docker環境ではCodexのbubblewrapがnamespace作成後のprocfs mountで失敗し、Agent shell実行まで到達できない。Dockerのseccomp設定だけを変えた診断でもprocfsのmasked/overmount制約が残った。必要なshell隔離、認証アクセス制御、egress制御が成立した証拠はない。

`danger-full-access`、approval/sandbox bypass、privileged、capability追加、seccomp緩和、host filesystem/Docker socket mountは使用していない。新しいPlan適合環境と、credentialをAgent shellから分離しegressを制御した構成で、negative isolation testを通してから実Agent評価を再開する必要がある。

### Judge fixture承認

fixtureは11件あり、approved 0、human review待ち9、deterministic review待ち2。Codexによる人間承認の代行や合成承認はしていない。独立根拠でのdeterministic reviewも未完了のまま維持する。

### 自動Skill改善

改善経路は実装・契約テスト済みだが、実AgentがSkillを使用した正式なQTS成果物がなく、自動Skill改善の実証は未達。Judge fixtureの独立承認、隔離済み実Agent評価、固定条件での独立回帰証拠が揃った後に実証可能となる。

### ローカル依存・OS制約

ローカルWindows環境ではAgent suiteのLinux専用テストと、PyYAML/Ruff未導入により全体テストを完走できない。GitHub Linux CIは5 workflowすべて成功している。Windowsでの完全なAgent/Docker受入を成功扱いしてはいない。

## 最終判定

- 実装完了 — 完了。F02/F03/N03/N04/F04のコード変更と回帰テストをpush。N01/N02/N05/N06/F01も現行コードで再確認。
- 単体・契約テスト — 部分完了。対象テストとGitHub CIは成功。Windows固有の6 Agent test errorsおよびPyYAML不足によるdeterministic suiteの失敗は残る。
- 結合検証 — 実装経路のテスト完了。F02/F03/F04をproduction関数経由で検査するテストが成功。実Agent環境での結合受入は未実施。
- 実Agent受入 — 未完了。bubblewrapのprocfs制約と隔離・認証・egress検証不足。
- Judge受入 — 未完了。fixture 11件すべて未承認。
- 自動改善実証 — 未完了。実Agentの有効なSkill使用・独立回帰証拠がまだない。

## 関連コミット

- F02: `e246303192e1e599975f6844e4bb7ef32fb0fc65`
- F02 formatter: `df220174aaed7b06dbed2a27e02bbf0b82911b42`
- F03: `57793f373c478b18945721ab3b4ba562d8689287`
- N03/N04: `74f936632450893d3ad69d4feeab3fa46d190ec7`
- N03/N04 formatter: `fac8966a40008f6bdf97163010ee753731cc69b2`
- F04: `f11e7aec9696078077e38353fd10713ae80ef92b`
- F04 formatter followups: `0651d7c4da71e25538e4311663cc752aa94b9d99`、`aab9cf7e6479db6f969f0934e0301b593f00f84d`、`0229ec8d8cd841b4a6ac8d1e96a97a90f7226111`、`595a34b75228529951b3a0366a7fbc208bc148e9`

このレポートは実Agent/Judgeの未達条件を明示するものであり、それらを完了済みとするものではない。
