# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. 追加するSkill

`usability-inspection` は、生きた実対象に対してuser goal / task scenarioを与え、AIエージェント自身がUIを操作しながら、task達成可否、interaction、feedback、error recovery、visual integrity、accessibility上の操作性、system responsivenessを観測・計測するSkillです。

`usability-evaluation` とは責務を分けます。

| Skill | 主責務 | 実対象の能動操作 | 主な根拠 |
| --- | --- | --- | --- |
| `usability-evaluation` | UI pattern / principle / standard / Design System知識からUI / UXを評価 | 所有しない | reference knowledge + evidence |
| `usability-inspection` | user goal / task scenarioに沿って実対象を操作し、task遂行中の事実と計測値を取得 | 所有する | task scenario + live observation / measurement |
| `test-target-inspection` | currentなテスト対象情報を収集・管理 | 必要範囲で行う | current target state |
| `test-execution` | 定義済み詳細TCを実行し期待結果と比較 | 行う | TC expected result |

`test-target-inspection` / `test-execution` は本Skillの代替ではありません。

## 2. 目的

次をAIエージェントが実対象で確認できるようにします。

- user goalへ到達できるか
- taskを進めるための操作をUI上から見つけられるか
- controlを実際に操作できるか
- 操作後に状態変化やfeedbackを確認できるか
- errorや失敗状態から回復できるか
- 主要なtask flowで行き止まりや不要な往復が発生しないか
- viewport / state変化で表示が崩れないか
- overlap、clipping、overflow、見切れ等でtaskが阻害されないか
- keyboard等、scopeで指定したinput methodでtaskを進められるか
- user actionに対してUIが応答するまでのsystem側待ち時間を計測できるか
- loading中なのか停止しているのか判別できるfeedbackがあるか

目的は詳細TCのPASS / FAIL判定ではなく、**user goalを起点に実対象を使ったときに生じる観測可能なusability上の問題を検出すること**です。

## 3. human usability testingとの境界

一般的なusability testingは、代表的な参加者に現実的なtaskを実施してもらい、研究者が行動・発話等を観測するUX research methodです。

本Skillは代表ユーザーを置き換えません。

canonical Skill名を `usability-inspection` とし、human participantを用いる正式なusability testingと区別します。「ユーザビリティテストして」等の依頼はtrigger aliasとして受けられますが、成果物ではAIによるinspectionであることを明示します。

本Skillが行うのはAIエージェントによるtask-basedな実対象検査です。

したがって、次を本Skill単独では事実として確定しません。

- 人間にとって使いやすいこと
- satisfaction
- 実ユーザーの認知負荷
- 実ユーザーの学習容易性
- 実ユーザーのtask completion rate
- 実ユーザーの平均task time
- 実ユーザーが迷った、困った、満足したという行動・感情
- 実ユーザー集団でのperformance percentile

実ユーザー調査、analytics、RUM等の証拠が入力に含まれる場合は、その証拠として参照できます。

本Skillの「問題なし」は、**今回のtask scenario、実行条件、観測範囲、evidenceの範囲で問題を確認しなかった**という意味です。製品のusability全体を保証しません。

### 初版のlive実行対象

初版の能動操作対象は、既存Playwright / browser経路で到達できるWeb UIに限定します。

- desktop Web
- responsive Web
- mobile Web viewport

を対象にできます。

native iOS / Android app、desktop native app等の能動操作は、対応runtimeがrepositoryへ実際に導入されるまで対象外です。

`usability-evaluation` 自体はplatform非依存のreference-based評価を維持するため、native向けHIGや設計資料の評価まで制限しません。

## 4. user goal / task scenario

本Skillは詳細手順ではなく、user goalとtask scenarioを実行単位にします。

最低限:

- user / role
- prior knowledge / experience assumptions
- prior knowledge / experience assumption source / evidence refs
- user goal
- user goalの根拠
- task scenario
- start state
- success condition
- target / entry point
- platform
- viewport / device
- input method
- locale
- role / permission
- 許可された副作用scope
- 利用可能なtest data / account
- timing thresholdがある場合はそのAuthority ref

### user goalの根拠

user goal / task scenarioの出所を区別します。

- ユーザーが今回明示
- project requirement / specification
- user research
- analytics / support data
- product documentation
- 過去の検証済みproject knowledge
- UIからの推定
- 不明

成果物では少なくとも `confirmed / inferred / unknown` を区別し、`inferred` は仮定として表示します。

user / roleだけで事前知識を推測しません。今回のinspectionで前提とする製品利用経験、業務知識、一般的なUI経験等を `prior knowledge / experience assumptions` として明示し、その根拠も残します。根拠がない場合は `unknown` とし、「初見」「熟練」等を勝手に確定しません。

UIや一般知識から推定したgoalは、実ユーザーのgoalとして確定しません。

推定しかない場合は「このgoalを仮定したtask-based inspection」として扱い、representative user taskとは表現しません。

### task選定

ユーザーが実行するtaskを明示した場合は、そのtaskを正本にします。

「このサービスの使い勝手を確認」「主要フローを見て」のようにscopeが広くtaskが明示されない場合は、次の既存情報からtask候補を作ります。

- project requirement / specification
- user research
- analytics / support data
- Product Risk / test scope
- 検証済みproject knowledge
- 既存の業務フロー / user journey
- current target artifactのentry point / role / known state
- 既存TCが示す機能・業務フローの存在

`test-target-inspection` や `test-execution` の成果物はtask候補や実行条件を理解するread-only contextとして利用できます。ただし、TCのstep sequenceやlocatorをusability-inspectionの正解経路として使いません。

候補から選定する場合は、最低限次を記録します。

- requested scope
- task candidate
- candidateの根拠
- selected / not-selected / deferred
- 選定理由
- coverage limitation

優先対象は、根拠がある範囲で主要、頻出、業務上重要、または高Riskなtaskです。独自scoreは作りません。

根拠あるtask母集団を作れない場合は、UIから推定したtaskを `inferred` として限定的に実行できますが、「製品全体」「代表task」「主要taskを網羅した」とは表現しません。

1つのActivityは1つの固定task scenarioを扱います。広い依頼で複数taskを選定した場合はtaskごとに別Activityとして実行し、task選定summaryはcoordination情報として保持します。task selection専用の新しいglobal Machine Entityは追加しません。

### task scenarioと詳細手順の境界

task scenarioは、何を達成するかを与えます。

例:

~~~text
user:
一般購入者

prior knowledge / experience assumptions:
このECサイトは初回利用、一般的なECサイトの利用経験あり

goal:
条件に合う商品を見つける

task scenario:
5,000円以下の防水スニーカーを探し、候補商品の詳細を確認する

start state:
トップページ

success condition:
条件を満たす商品の詳細画面へ到達し、その商品が条件を満たすことをUI上で確認できる
~~~

「検索欄をクリック → キーワード入力 → Filterを開く → 価格を入力」のような正解手順を最初から与えません。

詳細操作順と期待結果が正本として既に存在し、それを忠実に実行する依頼は `test-execution` の責務です。

## 5. 実行時のuser視点

task達成のための次の操作は、宣言したinteraction modeでユーザーが利用できる情報から選びます。

### visual / pointer中心

操作判断に利用してよいもの:

- rendered UI
- visible text
- visible control
- visible feedback
- screenshot
- userへ提示される状態

### keyboard中心

加えて次を利用できます。

- focus可能なcontrol
- focus order
- focus indicator
- keyboard interactionの結果

### assistive technology / accessibility scope

scopeに応じて次を利用できます。

- accessibility tree
- role
- accessible name / description
- state / property
- keyboard interaction

### task遂行判断に使わないもの

通常ユーザーから見えない実装情報を使って「正しい操作」を先回りしません。

- test id
- hidden DOM
- source code
- Page Object locator
- internal route knowledge
- backend API
- DB
- localStorage / sessionStorage
- hidden application state
- network responseの内部値

Playwrightで実際の操作を実装するときにrole / name等のlocatorを使うこと自体は禁止しません。ただし、どのcontrolを選ぶかという意味判断は宣言したuser-facing情報から行います。

taskで検証するUI経路をAPI / DB / storage操作で迂回しません。

## 6. 実行手順

### Step 1: preflight

確認します。

- targetへ安全に到達できる
- user / role / permission
- prior knowledge / experience assumptionsとその根拠
- start state
- task scenario / success condition
- side effect scope
- cleanup
- viewport / locale / input method
- timingを計測する場合の対象区間
- 各timing measurementのstart event / end predicate / measurement method / threshold Authorityの有無
- browser / computer操作能力

開始条件を満たせない場合は実操作へ進みません。

### Step 2: task snapshotを固定

今回runで使用するuser / role、prior knowledge / experience assumptions、user goal、task scenario、success condition、contextを固定します。

実行開始後にgoal、success condition、対象scopeを都合よく変更しません。

意味上変更する必要が出た場合は現在runを理由付きで閉じ、別runとして扱います。

### Step 3: start stateを確認

UI上でstart stateを確認します。

未確認の内部状態を推測しません。

### Step 4: taskを実行

Agentはtask goalだけを基準に、user-facing情報から次の操作を選択します。

詳細TCの固定手順を再現するのではありません。

各meaningful actionについて、

- action
- actionを選んだ根拠となるuser-facing cue
- before state
- observed response
- after state
- evidence
- system timing measurement

を必要範囲で保持します。

### Step 5: meaningful checkpointで観測

最低限、該当するものを確認します。

- 次のactionを見つけられるか
- controlが操作可能か
- system status / feedback
- loading
- success / error
- recovery
- navigation / back
- focus / keyboard
- visual breakage
- responsive state
- important content / primary actionのvisibility
- task continuation可能性

### Step 6: task outcomeを確定

task outcomeは次です。

- `達成`: success conditionをUI上の証拠で確認できた
- `未達成`: 許可されたinteraction modeでtaskを実行し、UI / system側の阻害を直接観測してsuccess conditionへ到達できないことを確認した
- `判定不能`: 実行を開始したが、Agent / tool capability、element localization、browser異常、環境・証拠不足、外部要因、またはUI問題との切り分け不能により達成可否を確定できない
- `未実行`: taskのuser-facing操作を開始していない

`未達成` を使うには、Agentが失敗したという事実だけでなく、product側の阻害を示すuser-facing evidenceが必要です。

例えば「Agentがbuttonを見つけられなかった」だけではdiscoverability問題としません。screenshot / rendered UI / accessibility evidence等から必要なcueが存在しない、操作不能、dead end等を確認できない場合は `判定不能` とします。

outcome basisも固定します。

- `達成` → `success-observed`
- `未達成` → `product-blocker-observed`
- `判定不能` → `agent-tool-limitation / environment-external / unresolved`
- `未実行` → `not-started`

これはTCのPASS / FAILではありません。

### Step 7: primary task outcomeを固定

Step 6で確定したtask outcome、outcome basis、primary action traceをprimary runの結果として固定します。

以降のwalkthrough、UI / UX評価、追加観測によってprimary runのtask outcomeやaction traceを書き換えません。

primary runをやり直す必要がある場合は、同じActivityを上書きせず別Activityとして再実行します。

### Step 8: post-task diagnosis

primary task outcome固定後に、必要な場合だけdiagnostic evaluationを行います。

#### Cognitive Walkthrough

currentなuser flow、specification、検証済みTC等から意図されたtask flowを確認できる場合は、read-onlyの参照情報としてCognitive Walkthroughを実施できます。

Cognitive Walkthroughでは、既知のflowをstep-by-stepでたどり、各stepについて少なくとも次を確認します。

- 今回固定したuser / prior knowledgeの前提で、次に達成すべきsub-goalを持てるか
- 必要なactionやcontrolへ気付けるか
- そのactionがsub-goalへつながると理解できるか
- actionを実行できるか
- action後のsystem response / feedbackから進捗を理解できるか

TCのstep sequenceを利用する場合も、primary run開始前には正解経路として渡しません。primary outcome固定後に、意図されたuser flowを表すと確認できる場合だけwalkthroughのread-only参照として利用します。

意図されたflowを信頼できるsourceから確認できない場合は、正しいstep sequenceを創作せずCognitive Walkthroughを省略します。

walkthroughで得た診断結果はprimary action traceへ混ぜず、post-task diagnostic evidenceとして保持します。

#### UI / UX評価

primary runおよび必要なpost-task diagnostic evidenceを `usability-evaluation` へ渡します。

`usability-evaluation` は、

- UI pattern
- purpose / rationale
- applicable standard
- project Authority
- platform / Design System guidance
- heuristic

に照らして評価します。

browser / sessionのownerは `usability-inspection` のままです。

追加観測が必要なら `usability-evaluation` は要求内容を返せますが、追加観測は必ずpost-task diagnosisとして扱います。`usability-inspection` がscope / safetyを確認して実行し、その結果によってprimary task outcomeを変更しません。

追加観測で新しいproduct-side problemを確認した場合は、別Observation / evaluation / Findingとして記録します。primary run自体を再評価する必要がある場合は新しいActivityで再実行します。

同じbrowser / sessionを両Skillが並行操作しません。

### Step 9: cleanup

副作用がある場合は、PR #12 merge後のbrowser / side-effect / cleanup契約を再利用します。

cleanup結果と残存状態を記録します。

## 7. 評価する観点

### task completion

- success conditionへ到達できるか
- dead endがないか
- required actionを実行できるか
- task flowを継続できるか

### Agent run上の操作負荷

人間のefficiencyとしてではなく、今回のAgent runで観測した事実として必要範囲で保持します。

- meaningful action数
- retry
- backtrack
- dead end
- error
- recovery
- system wait

定義:

- retry: 同じ意図のactionを、前回の操作で必要なobservable responseを得られず再実行した
- backtrack: 進行中の経路を取りやめ、user-facingなnavigation / state操作で前の状態へ戻って別経路を試した
- dead end: 許可されたinteraction modeでsuccess conditionへ進むuser-facing actionを確認できなかった
- recovery: error /失敗状態からtaskを継続可能な状態へ戻した
- errorはuser-facingなerror stateを数え、Agent / tool / browser自身のerrorを含めない

これらを単一scoreへまとめず、任意の回数thresholdも作りません。比較する場合は同じtask / contextの別run、またはprojectで明示された基準がある場合に限定します。

### interaction / feedback

- action可能性をuser-facing情報から判断できるか
- 操作後に反応を確認できるか
- loading / processing状態が分かるか
- state changeが認識できるか
- errorから回復できるか
- destructive actionに必要な保護があるか

### visual integrity

- overlap
- clipping
- overflow
- important actionの見切れ
- modal / popupの表示破綻
- unexpected horizontal scroll
- text expansion / zoomでの破綻
- feedback / errorの視認阻害
- visual instabilityにより操作対象が意図せず移動する状態

### input method / accessibility

scopeで指定した場合、

- keyboard-onlyでtaskを継続できるか
- focusが見えるか
- focus orderがtaskを阻害しないか
- accessible role / name / stateで必要controlを識別できるか
- assistive technology向けsemanticsと実際のtask progressionが矛盾しないか

WCAG conformance全体を単一taskから宣言しません。

product / app全体のaccessibility conformance評価を要求された場合はW3C WCAG-EM 2.0のscope / product exploration / representative sample / evaluation / reporting契約を参照します。通常の単一task usability-inspectionへWCAG-EM全手順を無条件適用しません。

### system responsiveness

測定対象はAgentの思考時間ではなく、system / browser側の待ち時間です。

例:

- actionから最初のvisible feedbackまで
- actionから次のtaskを継続可能になるまで
- navigation開始から主要内容が利用可能になるまで
- loading開始から完了状態まで

測定値には、

- start event
- end event
- elapsed time
- measurement method
- viewport / device
- network等、取得できる実行条件
- evidence ref

を残します。

各measurementのstart event、end predicate、measurement method、threshold Authorityの有無は対象action開始前に固定します。測定結果を見た後で都合のよいend conditionへ変更しません。

start / endは可能な限りbrowser / page側のmonotonicな時刻またはPerformance API等、同一計測系で取得します。

Agentが「次に何をするか」を考えるmodel turn、tool call待ち、チャット往復時間をsystem elapsed timeへ含めません。

browser側で区間を直接計測できず、Agent turnを跨ぐwall-clockしか得られない場合はsystem responsivenessの測定値として確定せず、`measurement-unavailable` または制約付き観測として扱います。

## 8. performance判定

### project thresholdがある場合

現在有効なperformance budget、SLO、仕様等をAuthorityとして比較できます。

### 標準metricを使う場合

metricの定義と測定方法を満たす場合だけ、そのmetric名で評価します。

WebのINP等を扱う場合、単一actionの独自elapsed timeをINPと呼びません。

field dataのpercentile等を要求するmetricについて、1回のAgent runだけからfield performanceやCore Web Vitals達成を断定しません。

### thresholdがない場合

任意の秒数を仕様FAIL thresholdとして創作しません。

次を分離して報告します。

- 実測値
- feedbackの有無
- taskが待機によって阻害された事実
- reference上の一般的なresponsiveness guidance
- threshold未定義であること

## 9. visual / performanceの反復

複数viewportや複数回測定を行う場合は、今回scopeで対象を固定します。

projectのsupport matrixがある場合はそれを使います。

support matrixが不明なのに「desktop / tablet / mobileすべて」を勝手に製品要件へしません。

性能測定も統計的代表性を装うために任意回数を繰り返しません。

## 10. Finding

PR #13 merge後のFinding契約を再利用します。

次はFinding候補になり得ます。

- product側の阻害をuser-facing evidenceで確認したtask未達成でfollow-upが必要
- user-facing操作から必要controlへ到達できない
- taskを阻害するvisual breakage
- error recovery不能
- required input methodでtask継続不能
- project threshold違反
- system delay + feedback不足等、後続QA活動で扱う必要がある観測

task outcomeだけからDefectを確定しません。

Agent / tool limitation、environment issue、またはproduct側阻害との切り分け不能で `判定不能` になった場合、それだけをproduct Findingへ昇格しません。

UI pattern / standardに基づく意味判断は `usability-evaluation` の評価結果を根拠にします。

## 11. 担当しないこと

- representative userを用いたUX research
- user interview
- satisfaction調査
- human task completion rateの測定
- human task timeの測定
- eye tracking
- session replay analytics
- RUM基盤の新設
- load / stress / soak test
- backend performance profiling
- detailed TCのPASS / FAIL
- current target inventoryの正本管理
- exploratory Session lifecycle
- pixel-perfect visual regression framework
- 新しいbrowser automation framework
- native mobile / desktop app向けlive automation runtime
- project requirementにないperformance thresholdの創作
- test idやhidden DOMを使ったuser task経路の先回り

## 12. 完了条件

1つのusability-inspection Activityは、最低限次を満たせば完了できます。

- task snapshotが固定されている
- goal / taskの出所が記録されている
- start stateが確認済み、または未実行理由がある
- task outcomeが `達成 / 未達成 / 判定不能 / 未実行` のいずれか
- `未達成` はproduct側阻害のuser-facing evidenceを持ち、Agent / tool limitationや切り分け不能は `判定不能` としている
- broad scopeではtask選定根拠、selected / not-selected / deferred、coverage limitationが残る
- 開始したtaskのmeaningful action / observationがevidenceへ追跡できる
- timingを報告する場合はaction前に固定したstart event / end predicate / measurement methodとsystem側実測値がある
- user-facing以外の内部情報でtask pathを先回りしていない
- side effect / cleanup契約が閉じている
- primary task outcome / action traceがpost-task diagnosis開始前に固定されている
- Cognitive Walkthroughを実施した場合はintended flowのsource refsとpost-task diagnostic evidenceへ追跡できる
- `usability-evaluation` を実行したscopeでは評価結果へ追跡でき、追加観測がprimary task outcomeを書き換えていない
- 必要なFindingがroutingされている
- human usability / satisfactionを捏造していない

問題が0件でも完了できます。
