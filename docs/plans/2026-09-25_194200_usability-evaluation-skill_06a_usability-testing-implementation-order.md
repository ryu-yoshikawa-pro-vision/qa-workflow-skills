# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. 実装開始条件

`usability-inspection` の実装は、次を確認してから開始します。

- PR #11 / #12 / #13がmainへmerge済み
- `usability-evaluation` の少なくともDialog縦断検証が成立済み
- 最新mainのbrowser safety / side-effect / cleanup契約
- 最新mainのqa-workflow / Activity / Finding契約
- Playwright利用経路
- repository標準のtrigger / deterministic / semantic eval構成

依存PRやusability-evaluation実装がPlanから変わった場合はcurrent implementationを正本にします。

## 2. Step 0: baseline再確認

最新mainとcurrent branchを同期した状態で、

- Skill一覧
- browser ownership
- side-effect contract
- Activity / artifact identity
- Finding
- qa-workflow routing
- evaluation runner

を確認します。

同じ責務が既に実装されている場合は重複実装しません。

## 3. Step 1: methodology reference

`_05a_usability-inspection-package-and-evaluation.md` のmethodology sourceを確認します。

最低限:

- ISO 9241-11の公開定義
- NN/g Usability Testing 101
- NN/g Task Scenarios for Usability Testing
- NN/g Task Analysis
- NN/g Cognitive Walkthroughs
- NN/g Summary of Usability Inspection Methods
- NIST Cognitive Walkthrough / usability inspection guidance
- W3C WCAG-EM 2.0
- web.dev User-centric Performance Metrics
- web.dev Interaction to Next Paint

current URL / publication state /利用条件を確認します。

長文本文をrepositoryへ複製しません。

## 4. Step 2: package skeleton / output contract

先に次を実装します。

- `skills/usability-inspection/SKILL.md`
- method references
- `assets/output-template.md`
- deterministic validator最小schema
- trigger fixture
- output fixture

まだ実browser操作を追加しません。

task selection summary、task snapshot、task outcome、outcome basis、action trace、Agent run上の操作負荷、timing measurement、Observation、evaluation ref、Finding refの構造を先に固定します。

## 5. Step 3: task execution contract

実browser接続前にfixtureで次を成立させます。

- goal / task source
- start state
- success condition
- user-facing cue
- meaningful action
- task outcome
- timing start / end
- no arbitrary threshold
- no TC PASS / FAIL
- no human satisfaction claim
- broad scope task selection / coverage limitation
- Agent / tool limitationとproduct-side blockerの分離
- live execution scopeがWeb UIに限定されること
- timing definitionをaction開始前に固定

詳細TCを入力したcaseがtest-executionへroutingされることも確認します。

## 6. Step 4: browser実行経路

PR #12 merge後のbrowser実行基盤を再利用します。

初版のlive実行対象は既存Playwright経路で到達可能なWeb UIに限定します。responsive mobile Web viewportは対象にできますが、native iOS / Android / desktop appの能動操作runtimeは追加しません。

新しいbrowser frameworkを作りません。

利用手段の選択規則が共有可能なら既存規則を利用し、Skill固有に別のrunner hierarchyを増やしません。

`usability-inspection` がbrowser / session ownerになります。

意味上の次actionを選ぶときはuser-facing information contractを適用します。

## 7. Step 5: 安全な縦断検証

最初に1つの低リスクtaskを端から端まで通します。

例:

~~~text
goal:
公開情報から目的のコンテンツを探す

side effect:
なし

start:
landing page

success:
指定条件を満たすdetail viewへ到達
~~~

確認:

- task snapshot
- visible / accessible cueからのaction選択
- browser操作
- screenshot / accessibility evidence
- task outcome
- action timing
- visual observation
- cleanup
- output validator

この段階では複数taskの大量実行へ広げません。

## 8. Step 6: usability-evaluation統合

Step 5で取得したimmutable evidenceを `usability-evaluation` へ渡します。

確認:

- inspectionがbrowser ownerを維持
- evaluationがread-only
- pattern / standard判断をinspection側へ複製しない
- evaluationから追加観測requestを返せる
- requestはinspection側でscope / safety判定してから実行
- finding traceability

同一sessionへの並行操作を行いません。

## 9. Step 7: visual / operability / responsiveness

### visual

代表caseで、

- clipping
- overflow
- primary action見切れ
- overlay / modal
- focus indicator
- unexpected layout shift

### operability

代表taskでmeaningful action、retry、backtrack、dead end、error / recoveryをAgent run上の観測事実として記録します。

回数をhuman efficiencyへ読み替えず、独自scoreや任意thresholdを作りません。

を確認します。

### responsiveness

代表actionで、action開始前にstart event / end predicate / measurement method / threshold Authorityの有無を固定したうえで、

- action start
- first visible feedback
- task-ready state

のsystem elapsed timeを取得します。

測定結果を見た後でend predicateを差し替えないcaseも検証します。

Agentの生成・推論時間を混ぜないことを確認します。

project thresholdがないcaseと、Authorityにthresholdがあるcaseの両方を検証します。

単一runをINP field resultへ誤変換しないcaseも含めます。

## 10. Step 8: input method

最低限keyboard-only caseを実行します。

- pointerでshortcutしない
- focus progression
- focus visibility
- keyboard activation
- task continuation

を確認します。

screen reader等の実行能力がrepository / hostで利用可能でない場合は、利用可能と偽らず、accessibility tree / keyboard evidenceまでを確認範囲として記録します。

## 11. Step 9: workflow integration

`_04a_usability-inspection-workflow-integration.md` に従い、

- direct trigger
- qa-workflow
- usability-evaluation
- test-target-inspection境界
- test-execution境界
- exploratory-testing境界
- regression-testing
- qa-knowledge

を接続します。

test-target-inspection / test-executionのownerロジックへusability-inspection固有処理を埋め込みません。

## 12. Step 10: repository eval

### trigger

repository標準件数に合わせます。

### deterministic

最低限:

- output schema
- task selection summary / coverage limitation
- task outcome / outcome basis
- action / observation / measurement ref
- Agent run上の操作負荷
- timing value / threshold整合
- goal provenance
- cleanup
- evaluation / Finding ref

### semantic

`_05a_usability-inspection-package-and-evaluation.md` §7のcaseを最低限含めます。

### real Agent

利用可能な環境で、実Agentがtask scenarioからuser-facing情報だけを使って操作することを確認します。

あわせて、Agentがcontrolを見落としただけのcaseをproduct defectへ昇格しないこと、UI側の阻害を直接観測したcaseだけ `未達成` を許可することを確認します。

## 13. Step 11: repository integration

最新mainを基準に、

- Skill一覧
- README
- EVALS
- ASSERTIONS
- qa-workflow
- validation workflow
- dataset counts

を同期します。

数値をPlan記載値で固定しません。

## 14. 完了条件

次をすべて満たしたら `usability-inspection` 実装完了とします。

- Agent Skills仕様を満たす
- task scenario / success condition契約がある
- user goalの出所または推定状態を保持する
- broad scopeではtask候補、selected / not-selected / deferred、coverage limitationを保持する
- task母集団の根拠がない場合に製品全体 / 代表taskを評価したと主張しない
- live execution対象をPlaywrightで到達可能なWeb UIへ限定する
- detailed TCを正本にしない
- user-facing informationからtask pathを選ぶ
- hidden implementation情報でdiscoverability問題を回避しない
- task outcomeをTC PASS / FAILと分離する
- `未達成` はproduct-side blocker evidenceがある場合だけ使用し、Agent / tool limitationまたは切り分け不能は `判定不能` とする
- meaningful action / retry / backtrack / dead end / error / recoveryをhuman efficiencyへ読み替えない
- visual observationをscreenshot等へ追跡できる
- timing measurementでAgent思考時間を除外する
- measurement definitionをaction前に固定し、結果を見た後でend predicateを変更しない
- arbitrary performance thresholdを作らない
- single-run elapsed timeをINP field resultへ昇格しない
- keyboard-only representative caseを確認する
- browser ownerがusability-inspectionである
- usability-evaluationとのread-only連携が成立する
- same session concurrent manipulationを要求しない
- side-effect / cleanup契約を満たす
- FindingがPR #13契約へ接続する
- representative-user usability studyを実施したと偽らない
- test-target-inspection / test-execution / exploratory-testingと責務重複しない
- trigger / deterministic / semantic eval PASS
- repository validation PASS
- README / EVALS / Skill一覧整合
- git diff --check PASS

## 15. Plan全体の完了

本PRの後続実装は、

1. `usability-evaluation` が `_06_evaluation-ci-implementation-order.md` の完了条件を満たす
2. `usability-inspection` が本ファイル§14の完了条件を満たす
3. 両Skillのqa-workflow routingと相互連携が成立する

まで完了扱いにしません。

## 16. 対象外

- human participant recruitment / study management
- survey platform
- eye tracking
- session replay基盤
- RUM collection service
- load / stress / soak testing
- backend profiler
- performance observability platform
- screenshot pixel-diff engine
- 新browser framework
- global Usability Test Case ID体系
- native mobile / desktop app live automation runtime
- automatic user persona generation
