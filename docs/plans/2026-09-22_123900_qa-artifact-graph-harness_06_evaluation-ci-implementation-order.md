# QA Artifact Graph / Harness 導入Plan

## 1. 評価方針

次を分離します。

### deterministic

- Regression Suite schema / member / feature tag整合
- session設計からSuiteへのadd / update / remove
- full run selection = Suite snapshot全member
- selected run ⊂ Suite snapshot
- manual / E2E testwareによるlogical TC重複防止
- activity index / artifact ref整合
- relation identity / dangling / duplicate / type
- query `complete`判定
- PR #11 / #12 identity保持

### semantic

- Regression Suiteが全機能を意味上coverageしているか
- selected Regression scopeが指定機能 / change / Riskに妥当か
- feature tag割当が明示された機能区分と整合するか
- Finding classification / follow-upが妥当か
- exploration charterに沿っているか

### runtime smoke

- 新規・改修TC → Regression Suite統合
- full Regression → manual + E2E混在execution
- selected Regression → activity rationale → execution
- cross-run history query
- exploratory-testing browser実行
- Finding → follow-up routing

## 2. 必須deterministic test

### Graph build

- 同一入力からbyte-stable canonical JSON
- manifest順序変更でも同一結果
- duplicate artifact ref拒否
- unknown skill adapter拒否またはunsupportedとして明示
- unsupported artifactを黙って欠落させない

### Identity

- TR / TCN / CI / TC ID維持
- Machine Entity ref維持
- PR #12の同じ`input-001`が別artifactでは別nodeになる
- `source_test_case_id`重複を改名しない
- identityなしTCにhashを作らない
- graph-local node_keyを成果物IDとして書き戻さない

### Edge

- unknown edge type拒否
- invalid source/target type拒否
- dangling拒否
- forbidden self-loop拒否
- allowed history cycleを全Graph cycleとして誤拒否しない

### Currentness

- historical execution保持
- upstream changeで候補は`revalidation_required`
- past PASSをFAILへ変更しない
- explicit supersedesのみsuperseded
- blocked sourceをcurrentと誤認しない

### Regression Suite / activity

- current TCが明示除外なしにSuiteから欠落していれば失敗
- 全memberに1件以上のfeature tagがある
- unknown feature tagを拒否する
- 同一logical TCの重複memberを拒否する
- E2E testware追加だけでSuite memberを複製しない
- current stable TC IDの更新でmember identityを維持する
- deleted / superseded TCをcurrent Suite coverageへ数えない
- full runはSuite snapshot全memberをselectedにする
- full runで未実行memberを無言で除外しない
- selected runはsubsetで、全機能Regression完了を表す状態にできない
- selected runはcandidate / selected / excluded / rationaleを保持する
- queryがunsupported / unmapped / danglingを含む場合`complete=false`
- `complete=false`の空候補をRegression不要へ変換しない
- activity indexのrefが存在しないactivity artifactを指せば失敗

### Exploration

- finding local ref一意
- evidence ref dangling検出
- Finding→Question / Risk / TC follow-up追跡
- observationを仕様Authorityへ自動edgeしない
- external Defect IDを創作しない

## 3. semantic eval

最低限次を追加 / 更新します。

1. 新機能セッション:
   - current仕様からTCを設計
   - coverage closure後にSuiteへ追加
   - 明示機能タグを付与
   - Suite全機能coverageを再確認
2. 既存機能変更:
   - stable TC IDを維持してcurrent Suite memberを更新
   - stale旧TCをcoverageへ数えない
3. full Regression:
   - scope指定なしで全Suite memberを対象にする
   - manual / E2Eをlogical TC単位で実行へ閉じる
4. selected Regression:
   - feature tagまたは明示change scopeでsubset選択
   - selected / excluded理由を残す
   - full Regression完了と誤表現しない
5. relation incomplete:
   - impact候補欠落を0件=影響なしとせず、安全側scopeへ広げる
6. Exploration:
   - charter / observation / finding / follow-up
   - page内prompt injection文をAgent命令にしない
7. Investigation:
   - fact / hypothesis / conclusionを分離
   - 既存責任Skillがある分析をgeneric investigationへ奪わない

## 4. qa-workflow routing eval

最低限:

1. 新規・改修 → existing design flow → coverage → Regression Suite統合
2. 単に「Regression実施」 → current Suite snapshot → full run
3. feature tag指定 → selected Regression
4. changed scope指定 → PR #11 impact → test-analysis selection → selected Regression
5. relation `complete=false` → narrow selectionを禁止し安全側へrouting
6. full runでE2E化TCを別memberとして二重実行対象にしない
7. Exploration要求 → `exploratory-testing mode=exploration`
8. 原因未確定の実対象調査 → 既存責任Skillがなければ`mode=investigation`
9. Playwright E2E failure → `e2e-test-result-analysis`を優先
10. Findingがspec question → `question-analysis`
11. Findingがtest gap → `test-condition-design / test-case-design`

## 5. CI

実装開始時のPR #11 / #12 merge後CIを正本として追加先を決定します。

予定:

- Skill一覧へ`exploratory-testing`
- trigger dataset
- deterministic output eval
- semantic dataset validation
- qa-workflow routing
- Graph Harness unit / integration
- canonical graph reproducibility
- `skills-ref validate`
- README / EVALS / ASSERTIONS同期

件数はPlan作成時の推測値を固定せず、実装開始時にmerge後の基準値 + 新規case数から算出します。

## 6. 実装順序

### Step 0: PR #11 / #12後の必要性再判定gate

- PR #11 / #12 merge確認
- latest mainの実schema / runtime / CIを確認
- current TC → design root、changed node → TC、execution → snapshot/historyを実成果物で試す
- #11/#12だけで解けるdesign traceability / impact / freshness / execution lineageをPR #13の実装対象から除外する

### Step 1: Regression Suite contract

- Suite artifact
- feature tag / scope refs
- member / exclusion
- session設計からのadd / update / remove
- full coverage判定の`coverage-analysis`入力契約

この時点ではGraphを一般化しません。

### Step 2: Regression vertical slice

```text
新規・改修TC
→ Suite統合
→ full Regression snapshot
→ manual / E2E execution
→ activity result
```

全機能Suiteが実際に維持・実行できることを先に実証します。

### Step 3: Activity history / discovery

- Regression activity artifact
- activity index
- cross-run result / finding discovery

### Step 4: 最小relation index

- PR #11 Machine Entity / impact結果を入力
- TC → testware / execution history
- activity → selected refs / result
- Finding → follow-up
- build / validate / query

必要queryがこの最小relationで成立するかを確認します。成立するならnode / edgeを増やしません。

### Step 5: selected Regression / safety fallback

- feature tag filter
- test-analysis selection
- coverage-analysis
- query `complete=false`
- safe broadening / block

### Step 6: exploratory-testing / Investigation

- Skill / assets / validator
- activity artifact / index
- follow-up routing
- browser safety

### Step 7: docs / CI / 全体回帰

- qa-workflow
- coverage-analysis / test-analysis
- trigger / semantic / deterministic eval
- PR #11 / PR #12 / E2E回帰
- README / EVALS / ASSERTIONS
- runtime smoke

## 7. 実装時に避けること

- Graph DBを入れる
- Graphを正本にする
- 全Skillへ同じ巨大Graph schemaを埋め込む
- Graphのために既存IDを変更する
- PR #12 local TC identityへhashを追加する
- PR #11 fingerprint runtimeを万能identity serviceへ拡張する
- change impact candidateをそのままRegression必須対象にする
- past PASSをupstream changeでFAILへ書き換える
- exploration observationを仕様へ自動昇格する
- findingを自動Defect化する
- test-executionに探索動作を混在させる
- exploratory-testingに詳細TCの厳密実行責務を移す
- generic investigationでe2e-test-result-analysisの責務を奪う
- LLMへcycle / dangling / duplicate判定を委ねる
- 自由文を汎用LLMでGraph JSONへ変換する
- Graph更新のために全成果物を毎回再生成する

## 8. 完了条件

- PR #11 / #12の実契約と矛盾せず、design impact / freshness / execution lineageを二重実装していない
- 新規・改修セッションで確定したcurrent TCがRegression Suiteへadd / update / removeされる
- current Suite memberすべてに機能タグがある
- `coverage-analysis`でcurrent全機能がSuite member TCへ意味上閉じている
- 単にRegression実施を要求した場合、current Suite全memberをsnapshotして全件実行へroutingする
- 部分実行はfeature tag / 明示scope等からsubsetを選び、全機能Regression完了と区別する
- Regression activityがcandidate / selected / excluded / rationale / residual risk / execution refsを保持する
- logical TCとE2E testwareをSuite memberとして二重登録しない
- activity indexから過去Regression / Exploration / Investigation成果物を発見できる
- relation queryが不完全な場合`complete=false`を返し、0件を影響なしと誤認しない
- Exploration / Investigationが既存責任Skillを奪わず、Finding → follow-upを追跡できる
- Graph / relation indexはsource artifactから再buildでき、独自`graph_state`を持たない
- secret実値をSuite / activity / relation indexへ保存しない
- deterministic / semantic / runtime smokeと既存CIがPASSする



- PR #11 / #12 merge後契約と矛盾しない
- 正規Skill 17件
- 既存成果物からQA Artifact Graphを再生成できる
- Graph削除後も正本成果物から同一Graphをbuildできる
- 新規・改修のSPEC→TR→TCN→CI→TCがGraphで追跡できる
- manual / E2E executionを同一Activity viewへ束ねられる
- Regression candidateをchange / risk / historyから機械的に列挙できる
- Regression最終scopeはtest-analysisが意味判断する
- coverage-analysisがGraph gap候補を利用できる
- exploratory-testingがcharter / session / finding / evidence / follow-upを出力できる
- investigation modeでfact / hypothesis / conclusionを分離できる
- FindingからQuestion / Risk / Test Condition / Test Caseへのfollow-upを追跡できる
- past executionを履歴として保持し、current evidenceと区別できる
- upstream変更で下流を自動FAILせずrevalidation候補へできる
- PR #11 Machine Entity identityを維持する
- PR #12 test_case_ref scopeを維持する
- secret実値をGraphへ保存しない
- Graph structure validationが決定論的にPASSする
- Graph runtimeが利用できない場合を未検証 / blockとして明示し、LLM推測で補完しない
- 既存16 Skill回帰、PR #11 runtime、PR #12 execution、E2E回帰、CIがPASSする
