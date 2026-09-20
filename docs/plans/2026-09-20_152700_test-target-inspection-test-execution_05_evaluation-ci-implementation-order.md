# テスト対象資料管理・テスト実行Skill追加Plan

## 1. 評価方針

新規2 Skillを追加した後も、現行リポジトリの評価層を維持します。

1. Agent Skills仕様検証
2. 発火評価データセット検証
3. 決定論的出力評価
4. 意味評価
5. `qa-workflow` routing / 状態評価
6. 既存14 Skillの回帰

新規Skillについて、repo内評価だけで実Agent上の発火をPASS扱いしません。現行`EVALS.md`と同様、repo内ではデータセット構造と出力契約を検証し、実Agent上の発火評価は別に扱います。

新規Skillの`evals/deterministic/validator.py`は出力評価インフラとして使用し、Skill実行時のruntime validatorにはしません。runtimeの最終出力確認は各`SKILL.md` / guidanceに既存Skillと同じ自己検証契約として定義します。

## 2. Skill数と固定値

基準branchでは正規Skillは14です。本変更で次を追加します。

- `test-target-inspection`
- `test-execution`

実装後は16 Skillです。

現行の各Skill発火データセット契約を維持する場合:

- train: 12件 / Skill（positive 6 / negative 6）
- validation: 8件 / Skill（positive 4 / negative 4）
- 16 Skill合計: 320 query

現行のsemantic eval最小契約である2 cases / Skillを維持する場合:

- 16 Skill × 2 = 32 cases

現行のdeterministic output evalも各Skill2 cases以上を維持し、repository合計の最低値を28から32へ更新します。

実装開始時に基準branch側でこれらの契約値が変更済みなら、その時点の正本から再計算し、本Planの14 / 280 / 28を機械的に上書きしません。特にPR #11が先にmergeされてSkill別trigger / semantic exact countやMachine Entity契約が変わっている場合は、その実装済み契約を正本とします。TCの`content_fingerprint`等は利用可能なら再利用しますが、本変更だけを理由に新規2 SkillをPR #11のruntime / Machine Entity対象へ追加しません。

## 3. `test-target-inspection` の評価

### 3.1 発火境界

positiveには最低限、次の意図をtrain / validation双方へ含めます。

- 実対象を調べてテスト設計・実行用の参照資料を作成する
- 既存のテスト対象資料を現在のUIに合わせて更新する
- POM相当のUI構造・操作・状態情報を整理する
- 自動化対象外も含む対象資料を作成・更新する

negativeには最低限、次を含めます。

- Playwright Page Objectコード実装 → `e2e-test-implementation`
- E2E実装可否のinspection → `e2e-test-inspection`
- 詳細TC作成 → `test-case-design`
- TC実行 → `test-execution`
- 仕様Authority整理 → `spec-analysis`

### 3.2 決定論的validator

保存済みMarkdownから機械判定できる出力契約だけを検査します。最低限、次を対象にします。

- 正規セクション / 必須テーブルが存在する
- 対象キー / 要素キー / 状態キーが一意で、新規成果物では文書ローカルの正規形式を使用する
- 要素・状態・操作・遷移・データ / 権限依存・未確認事項が参照するキーが現在成果物に存在するか、許可された明示状態である
- 既存成果物更新時だけ`今回の更新`が存在し、`追加 / 更新 / 変更なし`は現在成果物、`削除確認`は更新前成果物の実在キーへ追跡できる
- 同じ更新処理中に削除したキーを即再利用しない。過去versionの削除済みキー履歴を要求しない
- 各事実が確認元、確認version / build、確認日時 / revision、必要な確認条件へ追跡できる
- repo由来事実を利用した場合はbranch / commit / working treeを区別し、未commit変更に依存した事実をHEADだけでcurrentとみなさない
- `今回確認 / 既存資料から継承・未再確認 / 未確認 / 確認不能`を区別し、部分更新で未再確認行の鮮度を今回値へ上げない
- fixtureで要求された対象は確認済み事実または理由・後続影響付き未確認事項のいずれかへ閉じ、存在しない事実・キーを創作しない
- 任意の既存テスト実装対応表は、出力された場合だけ参照整合を検査し、表自体を必須にしない
- 削除確認fixtureでは、削除根拠と更新前キー参照が出力上整合し、単に見つからない対象を削除扱いしていない
- inspection副作用fixtureでは、許可scope、最大回数、実施回数、実施結果、cleanup結果、残存状態が出力され、記録上の実施回数が上限を超えない
- 永続保存fixtureでは保存結果、更新元revision / content identityまたは条件付き更新に利用した元状態、競合時の扱いが出力上矛盾せず、`未保存 / 保存後不整合`を保存済みと表現しない
- secret / cookie / token等の値や不要な個人データを必須出力として要求しない

deterministic output evalは保存済みMarkdownだけを評価するため、実際に条件付き更新が競合を防いだこと、browser操作を所定回数だけ実施したこと、証跡を共有・commitしなかったことまでは証明しません。これらのruntime挙動は実Agent / 実対象を利用できる場合のsmokeで確認し、利用できない場合は未検証として残します。

locatorの最適性、UI抽象化の粒度、画面分割、POM設計品質等の意味判断はdeterministic validatorへ入れません。

### 3.3 意味評価

`rubric.json`はdeterministic validatorと重複させず、意味判断が必要な次の観点を中心にします。

1. 実対象・repo・ユーザー提供情報を区別し、確認できない事実を創作しない
2. 現在観測した実装を仕様Authorityへ昇格しない
3. live target確認要求をrepo確認だけで満たした扱いにせず、後続が再利用できる必要十分な粒度で整理する
4. 部分更新で既存の有効情報・行ごとの鮮度を不必要に失わず、変更範囲だけを更新する
5. 削除・永続更新で不確かな事実を確定扱いせず、競合や保存失敗を隠さない
6. 副作用・cleanup・証跡の安全境界を守り、機密情報を不要に残さない
7. 対象製品コード、Page Object、fixture、helper、既存テストコードを変更しない

semantic evalは最低2 case作成します。

- 新規作成
- 既存資料の部分更新

現行契約がsemantic 2 case / Skillのexact countを要求する場合もcase数を増やしません。各critical criterion IDが最低1件のcaseから参照されることだけdataset testで確認し、機械検証できる項目をsemantic criterionへ重複追加しません。

## 4. `test-execution` の評価

### 4.1 発火境界

positiveには、leaf Skill単体で完結する次の意図を最低限含めます。

- 詳細TCを実画面でAIが直接操作してPASS / FAILを確認する
- 検証済みの既存E2E実行成果物をTC期待結果と照合する
- 未実行 / 判定不能理由を含むTC実行結果を整理する

negativeには最低限、次を含めます。

- Playwrightをrunnerとして起動しraw resultだけ取得 → `e2e-test-execution`
- 自動実行を含むTC一式を、方式判断・runner実行・必要な分析・TC判定まで通して実施 → `qa-workflow`
- Playwright FAIL原因分析 → `e2e-test-result-analysis`
- Playwright runの人間向け報告 → `e2e-test-reporting`
- TC設計 → `test-case-design`
- テスト対象資料作成 → `test-target-inspection`
- API / DB専用runnerでのTC実行や新しい実行基盤の追加 → 本変更の`test-execution`対象外

新規2 Skill側のnegativeだけで境界検証を完了扱いにしません。全Skill同時利用の正規発火評価で双方向の誤発火を検出できるよう、隣接Skillの既存query件数を維持しながら必要なnegative queryを置換・再配分します。

### 4.2 決定論的validator

保存済み出力から機械判定できる契約だけを検査します。

- 正規セクション / 必須テーブルが存在する
- 1成果物が1つのテストケース入力元 / snapshotを持ち、入力元種別と`TC revision / content identity`または明示的未提供状態を記録する
- 各入力TCが既存TC ID、外部システムの一意識別子等、入力側で既に存在する一意なTC識別子を持ち、正式TC IDを創作しない
- 固定した今回TC識別子集合とTC結果表の集合が一致し、要求外・欠落・不正重複がない
- 実行方式がTC単位で`AI直接操作 / 自動実行`、状態が`PASS / FAIL / 未実行 / 判定不能`の正規値である
- PASS / FAILには期待結果・実測結果・判定根拠、未実行 / 判定不能には理由が存在する
- 集計値がTC結果表と一致し、retry / attemptをTC件数へ混ぜない
- AI直接操作の実行前条件と副作用実績が存在し、同じ許可scopeを複数TCが共有するfixtureでは累計実施回数がscope全体の上限を超えない
- TC事後状態 / 後処理、実行時cleanup、Playwright runner管理cleanupを混同せず、cleanup失敗で確定済みTC結果を書き換えない
- runner異常を製品FAILへ変換せず、実行開始済みで必要観測がない場合はPASSにしない
- 自動実行では`今回TC識別子 → 既存TC ID（存在時のみ） → E2E実装参照 → E2E実行成果物参照 → logical primary → resolved primary TestCase → 実行結果`を、既存E2E成果物から得た参照として追跡できる
- `test-execution`自身にlogical primary解決・重複排除・preflight・run partitionの出力契約を要求しない
- 自動実行対応が`TC判定 / 診断のみ`を区別し、診断runだけを正式TC PASS根拠にしない
- 新しいrunner実行前にE2Eの期待結果検証十分性が未解決なfixtureは`未実行`、既存runを後から判定へ利用して十分性を確認できないfixtureは`判定不能`となる
- 実行開始後のTC追加・除外または方式変更では元成果物の固定集合を書き換えず、旧成果物の未開始 / 未完了TCを理由付きで閉じ、新しい成果物 / versionへ分ける
- 外部 / 直接入力TCを内部QA IDへ変換せず、内部workflowへの取込が明示されていないfixtureで`coverage-analysis`等の内部成果物を必須化しない
- 実在しない証跡参照を生成せず、機密情報を必須出力にしない

Skill間routing、実際のPlaywright run起動、browser操作回数、証跡共有の有無はoutput validatorだけで証明せず、`qa-workflow` routing testまたは利用可能な実Agent smokeで検証します。

### 4.3 意味評価

semantic rubricは次の7観点を中心にし、deterministic / routing評価と重複させません。

1. TC手順・期待結果・実測を忠実に比較し、未観測結果を推測してPASS / FAILにしない
2. runner / 認証 / setup / cleanup等の実行失敗と製品FAILを区別する
3. 副作用、開始状態、後処理、cleanup、証跡の安全境界を守る
4. 外部 / 直接入力TCを内部QA成果物へ自動変換せず、期待結果・E2E対応不足を適切にブロックする
5. 自動実行では既存E2E Skillのraw factと責務境界を守り、Playwright固有判断やSkill間routingを`test-execution`へ取り込まない
6. currentなE2Eが必要な期待結果を検証しているかを新規run前に確認し、既存run再評価時の`未実行 / 判定不能`境界と診断runの扱いを守る
7. 固定TC集合・1入力元 / snapshot・旧成果物の終了・過去結果再利用を一貫して扱う

semantic evalは最低2 case作成します。

- AI直接操作でPASS / FAIL / 判定不能が混在し、開始状態、副作用scope、TC後処理、安全cleanupを分離する複数TC
- 検証済み自動実行結果の利用でrunner異常または未実行、外部 / 内部TC境界、期待結果検証の十分性、診断runを含むTC

現行契約がsemantic 2 case / Skillのexact countを要求する場合もcase数を増やしません。各critical criterion IDが最低1件のcaseから参照されることだけ確認します。

## 5. `qa-workflow` 評価

routing caseへ最低限、次を追加します。

1. テスト対象資料作成 / 更新だけ → `test-target-inspection`
2. 詳細TCのAI直接操作だけ → `test-execution`
3. 検証済み既存E2E成果物のTC判定だけ → `test-execution`
4. AI直接操作 / 自動実行が混在し新しいPlaywright runが必要 → `test-execution`でTC集合・方式・E2E実装参照を確定 → `qa-workflow` → `e2e-test-execution` → 必要時`e2e-test-result-analysis` → `qa-workflow` → 同じ`test-execution`へ再開
5. Playwright raw実行のみ → `e2e-test-execution`
6. Playwright正常run後にTC判定 → `e2e-test-execution` → `test-execution`
7. Playwright異常 / 未実行 / run-level error / cleanup失敗・未確認後にTC判定 → `e2e-test-execution` → `e2e-test-result-analysis` → `test-execution`
8. 新規自動実行要求で期待結果検証の十分性が未解決 → runnerを起動せず必要なreview / ブロックへrouting
9. 内部QA成果物TCの`TC → E2E実装`欠落 → `coverage-analysis`。外部 / 直接入力TCの対応欠落 → 内部成果物へ自動取込せずブロック
10. テスト対象資料が古くE2E inspection前に更新が必要 → `test-target-inspection` → `e2e-test-inspection`
11. 開始後のTC追加・除外 / 方式変更 → 旧`test-execution`を理由付きで閉じ、新しい成果物 / versionを開始
12. TC実行途中で局所ブロックがあっても他TCを安全に継続できる

`qa-workflow`自身が各Skillの工程固有ロジックを再定義せず、Skill間routing・再開・完了だけを所有することもsemantic evalで確認します。

## 6. 既存Skill回帰

新規Skill追加により、直接境界が変わる既存Skillの責務・routing・発火境界が崩れていないことを確認します。

### `e2e-test-inspection`

- E2E実装可否・安全条件・Playwright固有事実の確認責務を維持する
- テスト対象資料が存在してもE2E固有preflightを省略しない
- 古いテスト対象資料をcurrentとみなさない

### `e2e-test-execution`

- Playwright runner固有のstatus / attempt / process / artifact / ownership / cleanup契約を維持する
- TCの意味上のPASS / FAILを新たに所有しない
- raw result契約を`test-execution`向けに簡略化しない
- 異常、未実行、run-level error、cleanup失敗 / 未確認を`e2e-test-result-analysis`へ渡す現行routingを維持する

### `e2e-test-result-analysis`

- runner異常・環境・実装・対象製品等の原因分析責務を維持する
- TC期待結果を書き換える責務を持たせない
- 分析後にTC判定が要求されている場合だけ`test-execution`へ接続し、Playwright raw fact自体をTC結果へ置き換えない

### `e2e-test-reporting`

- Playwright run報告の責務を維持する
- 汎用TC結果報告へ拡張しない

### `coverage-analysis` / `adversarial-review`

- `coverage-analysis`の既存`TC → E2E実装`追跡責務は内部QA成果物TCの対応欠落・陳腐化時だけ再利用し、`TC → テスト実行結果`という新用途は追加しない
- 外部 / 直接入力TCのために内部`TC ID`や`TC → E2E実装`成果物を自動生成しない
- `adversarial-review`（対象: `E2E実装`）は既存の期待結果 / assertionレビュー責務を維持し、TC実行を所有しない
- `test-execution`専用のrevision / working tree追跡schemaは追加せず、`qa-workflow`の`要再検証`と現在対象の再reviewで鮮度を担保する

### `test-case-design` / `question-analysis`

- `test-case-design`は`SKILL.md`の補助入力契約にもテスト対象資料を明示し、UI名称・到達方法・具体手順・観測可能性へ利用できるが、期待結果の仕様根拠にしない
- `question-analysis`は一般的な実対象事実の解消後に`test-target-inspection`、汎用TC実行条件の解消後に`test-execution`へ再開できる
- 両Skillの既存deterministic / semantic / routing評価へ、この境界を検出できる回帰caseを追加または既存caseへ統合する

## 7. CI変更

最低限、次を更新します。

### `.github/workflows/validate-skills.yml`

- expected Skill一覧へ2 Skill追加
- Skill countを16へ更新
- trigger query repository合計を320へ更新
- README / EVALSで新Skill名が説明されていることを確認

固定値を増やすだけではなく、実装時に既存workflowが現在のSkill数を自動導出できないか確認します。現行の明示一覧は正規Skill集合の意図しない増減を検出する役割もあるため、単純な動的列挙へ置き換えません。

### `.github/workflows/deterministic-output-evals.yml`

- skills一覧へ2 Skill追加
- repository最低case数を32へ更新

### semantic dataset test

- `tests/skills/evals/semantic/test_repository_structure.py`の正規Skill一覧へ2 Skillを追加する
- 現行契約が維持されている場合は`tests/skills/evals/semantic/test_semantic_datasets.py`のrepository合計28を32へ更新する
- PR #11等でSkill別expected count mapへ移行済みなら、その時点の正規一覧・Skill別exact count・repository合計へ2 Skill分を追加し、旧32固定値へ戻さない
- 新規2 Skillでは`rubric.json`のcritical criterion IDが最低1件のsemantic caseから参照されることをdataset testで確認する。既存Skillへ同じ制約を一括適用して無関係な回帰を起こさない

### 共通validator

`scripts/skills/evals/deterministic/common.py`:

- `CANONICAL_SKILLS`へ2 Skill追加
- `MULTI_USE_SKILL_TARGETS`は今回変更しない
- 新規共通ID体系は追加しない

## 8. README / EVALS / ASSERTIONS

実装後、実際の契約に合わせて更新します。

### README

- 16 Skill構成
- `test-target-inspection`は固定workflow工程ではなく必要時利用
- `test-execution`はTC実行・期待結果比較
- E2E Skillとの責務境界
- テスト対象資料の永続保存先は案件側
- 発火評価320 query

### EVALS

- 対象Skill一覧16件
- trigger合計320
- semantic合計32
- 新Skillの発火境界
- 隣接する既存Skillとの双方向発火境界。既存Skillは件数を増やさずqueryを置換・再配分する
- repo内評価と実Agent発火評価の区別

### ASSERTIONS

現行の`scripts/skills/evals/deterministic/ASSERTIONS.md`へ、新規2 Skillのvalidator assertion IDとworkflow routing assertionを同期します。存在確認を条件にせず、現在の正本へ実装と同時に反映します。

## 9. 実装順序

### Step 1: 基準再確認

- 最新`main`との差分確認
- Draft PR #11等、先行merge済み変更の取り込み
- 正規Skill数 / query合計 / semantic case合計 / deterministic最低case数を再計算
- 既存評価がPASSする基準を確認

### Step 2: 共通Skill登録

- `CANONICAL_SKILLS`へ2 Skill追加
- CI / repository Skill一覧更新
- 空Skillを先に通すのではなく、次StepでPackageを完成させてから構造CIを通す

### Step 3: `test-target-inspection`

- `SKILL.md`
- `references/guidance.md`
- `assets/output-template.md`
- trigger eval
- deterministic output eval / validator
- semantic eval
- `e2e-test-inspection`再利用契約
- 文書ローカルキーの新規採番 / 安定維持、確認条件、repo working tree、更新元revision / content identity、保存直前の競合確認、最終出力自己検証

### Step 4: `test-execution`

- `SKILL.md`
- `references/guidance.md`
- `assets/output-template.md`
- trigger eval
- deterministic output eval / validator
- semantic eval
- テストケース入力元、入力側の既存一意TC識別子、今回TC識別子と既存E2E `TC ID`の分離、実行開始後に不変なTC識別子集合、TC revision未提供、外部 / 直接入力TCの期待結果境界、既存結果再利用、AI直接操作preflight、副作用実施回数、TC後処理 / cleanup、結果不明な副作用操作の再試行禁止
- 自動実行の今回TC識別子 → 既存TC ID（存在時のみ） → E2E実装 / revision / working tree → logical primary → E2E実行成果物 → resolved primary → 結果追跡、対象環境整合、期待結果検証とreview鮮度の十分性確認
- 同一logical primaryの委譲集合一意化、preflight条件ごとの複数E2E run分割、診断runと正式TC実行の分離
- AI直接操作 / 自動実行混在時のsubset委譲・同一`test-execution`再開・重複実行防止、最終出力自己検証
- `e2e-test-execution` / `e2e-test-result-analysis`の既存異常routingを維持

### Step 5: 既存Skillとの接続

- `test-case-design/SKILL.md`とguidanceへテスト対象資料の任意補助入力境界を追加
- `question-analysis`へ`test-target-inspection` / `test-execution`の再開routingを追加
- `e2e-test-inspection`へテスト対象資料の任意再利用境界を追加
- `e2e-test-execution` / `e2e-test-result-analysis`の既存routingを変更せず、`test-execution`への接続だけを必要最小限で追加
- `coverage-analysis`（対象: `TC → E2E実装`）を対応欠落・陳腐化時の既存修正先として再利用し、新用途は追加しない
- `adversarial-review`（対象: `E2E実装`）の既存期待結果 / assertionレビューを自動実行PASS判定の確認元として再利用し、対象E2E実装revision / working treeを追跡できる最小契約を同期する
- E2Eコード変更は実装・更新がユーザー要求 / workflow範囲に含まれる場合だけ`e2e-test-implementation`へroutingする
- `test-case-design` / `question-analysis`自身の回帰評価を更新
- 隣接Skillのtrigger negativeを件数維持のまま置換・再配分し、既存の固有境界が別caseで残ることを確認
- `coverage-analysis`へ新用途は追加しない

### Step 6: `qa-workflow`

- 16 Skill化
- routing
- workflow state template
- `test-target-inspection`が返した保存済み成果物参照・範囲・鮮度を、`qa-workflow`が案件コンテキストの既存`既存QA成果物`欄へ反映
- 途中開始 / 再利用 / ブロック / 再開
- routing fixture / deterministic validator / semantic eval

### Step 7: 文書・CI同期

- README
- EVALS
- ASSERTIONS
- GitHub Actions固定値
- semantic repository structure / dataset testsを含むrepository eval tests

### Step 8: 全体検証

- `skills-ref validate` 全Skill
- trigger dataset構造検証
- deterministic output eval
- semantic dataset構造検証
- repository deterministic tests
- workflow routing tests
- 既存14 Skill回帰
- 実Agentを利用できる環境では、新規2 Skillのpositive / negative発火smokeに加え、安全な実対象で`test-target-inspection`の観測と`test-execution`の非破壊TC実行を最低1経路ずつ確認する
- 実Agentまたはbrowser / computer操作能力を利用できない場合は、その経路を未検証として記録し、repo内dataset PASSだけでAI直接操作まで検証済みと表現しない

## 10. 実装時に避けること

- `test-target-inspection`を通常workflowへ無条件挿入する
- 案件固有テスト対象資料を`qa-workflow-skills`へ永続保存する
- POMコード生成を`test-target-inspection`の必須責務にする
- 実対象の現在挙動を仕様Authorityへ昇格する
- `test-target-inspection`で対象製品コード、Page Object、fixture、helper、既存テストコードを変更する
- 実対象で確認したUI / 状態 / 遷移を、repoで見つからないだけで削除する
- `test-execution`へPlaywright runner内部契約を複製する
- `e2e-test-execution`を削除または汎用化する
- runner異常を製品FAILとして扱う
- 既存E2E異常routingを`test-execution`追加のためだけに迂回する
- 実測していない期待結果をPASSへ変換する
- E2E対応が存在するだけで方式未指定TCを自動実行へ決める
- 固定TC集合と無関係なprimary testを「ついでに」実行する
- AI直接操作で結果不明の副作用操作を状態確認なしに再試行する
- 外部TCやユーザー直接入力に正式TC IDを勝手に採番する
- 混在実行で同じTC識別子をAI直接操作と自動実行の両方へ暗黙に割り当てる
- 永続保存・更新が要求成果物なのに未保存 / 保存後不整合の候補返却だけで完了扱いする
- `test-target-inspection`自身が案件コンテキストを更新する
- run PASSだけを根拠に、E2E実装がTCの必要な期待結果を検証しているか未確認のTCをPASSにする
- 自動化対象外TCを実行対象外とみなす
- `test-target-inspection`成果物がないだけで実行可能なTCを止める
- 将来のAPI / mobile / DB等のためだけにrunner adapter frameworkを作る
- 今回使わない共通artifact registryや外部knowledge baseを追加する
- 新規2 Skillを現在要件だけを理由にPR #11のruntime / Machine Entity対象へ追加する
- `test-execution`結果の完全性確認だけのために`coverage-analysis`へ新しい比較対象を追加する
- 操作・遷移や期待結果のためだけに新しい共通ID体系を追加する
- test execution履歴管理のためだけに新しいrun registry / DBを追加する
- `evals/deterministic/validator.py`をSkill runtimeのvalidatorとして呼び出す
- 任意形式の既存テスト対象資料を更新するためだけに汎用document parser / mergerを追加する
- 複数TCが同じlogical primaryへ対応するとき、TC数だけ同じlogical primaryをrunnerへ重複指定する
- preflight条件が両立しない自動実行TCを1回の`e2e-test-execution`へ無理にまとめる
- 診断runだけを正式TC結果のPASS根拠へ昇格する
- 実行だけの要求からE2Eコード変更を暗黙許可する

## 11. 完了条件

以下をすべて満たしたら実装完了とします。

- 正規Skillが16件になっている
- `test-target-inspection`が独立Skillとして作成・部分更新でき、`未確認`を今回確認対象だが未確認、`確認不能`を今回確認対象だが確認できない状態として区別し、要求範囲外を`未確認`へ混ぜず、必要な`未確認 / 確認不能`をrepo情報だけで完了扱いしない
- テスト対象資料の操作・遷移、データ・権限依存、更新履歴が既存の`対象キー / 要素キー / 状態キー`へ追跡できる
- 新規テスト対象資料で`target-001` / `element-001` / `state-001`の文書ローカルキーを安定して採番し、既存資料の別キー規則は不要に置換せず、削除確認済みキーを再利用しない
- 各観測事実が該当時のrole / 権限、viewport、locale、feature flag、テストデータ等の確認条件へ追跡でき、repo事実はworking tree状態も含めて鮮度判定できる
- inspection副作用を実施した場合は許可範囲・最大回数・実施回数・cleanup結果・残存状態が記録され、実施回数が最大回数を超えない
- 実対象UI / 状態 / 遷移とrepo事実で削除判定の根拠を分け、単に見つからない情報を削除しない
- `test-target-inspection`成果物を`e2e-test-inspection`等が任意入力として再利用でき、各継承行の確認version / build・revisionを保持したうえで、該当事実へ影響するrole / viewport / locale / feature flag / データ条件等の差異を確認する
- 永続保存・更新が要求成果物の場合は保存成功まで完了にせず、`qa-workflow`利用時の案件コンテキスト`既存QA成果物`更新を`qa-workflow`が担当する
- 既存資料の永続更新では候補作成時の更新元revision / content identityを保存直前に再確認し、途中変更を古い候補で上書きしない
- テスト対象資料が仕様Authorityとして扱われない
- `test-execution`が`qa-workflow`成果物、外部成果物、ユーザー直接入力のTCを受け、入力側の既存一意TC識別子を使い、外部 / 直接入力の期待結果を今回実行契約として扱いながら仕様Authorityへ昇格せず、AI直接操作と検証済み自動実行結果利用の両方を扱える
- PASS / FAIL / 未実行 / 判定不能のTC結果契約が成立し、workflow上の`ブロック中`と分離される
- 実行開始前に今回要求された具体的TC識別子集合が固定され、識別不能TCへ正式TC IDを創作せず、開始後のTC追加・除外または方式変更で同じ成果物の集合を書き換えず、その集合と結果集合の完全性を`SKILL.md` / guidanceの最終出力自己検証で確認できる
- TC revision / content identityが未提供でも今回実行は可能で、未提供状態を明示し、過去結果のcurrent再利用では鮮度を確認する
- AI直接操作の実行前条件がTC単位で記録され、再試行を含む副作用実施回数が最大回数以下であることを記録・検証し、結果不明な副作用操作を盲目的再試行せず、TC事後状態 / 後処理、実行時cleanup、Playwright runner管理cleanupが区別される
- TC結果と後処理 / cleanup状態が別軸で保持される
- 自動実行で固定TC識別子集合の自動実行subset → 既存TC ID（存在時のみ） → E2E実装 / revision / working tree → 今回logical primary → E2E実行成果物 → resolved primary TestCase → 実行結果を追跡でき、同一runへ渡すlogical primary集合を一意化して要求外primaryを暗黙追加しない
- AI直接操作 / 自動実行の混在時に、自動実行subsetだけをE2E Skillへ委譲して同じ`test-execution`へ再開し、同一TCを重複実行せず全結果を統合できる
- 自動実行subsetのpreflight条件が両立しない場合は複数の`e2e-test-execution`へ分割し、各成果物参照を同じ`test-execution`へ統合できる
- `e2e-test-result-analysis`からの診断runを正式TC実行と区別し、診断runだけをPASS根拠にしない
- currentな`TC → E2E実装`対応が欠落・陳腐化した場合は`coverage-analysis`へ戻り、実行だけの要求からE2Eコード変更へ暗黙routingしない
- 自動実行結果が今回要求したURL / origin、project、role / 認証、開始状態 / データ、version / build等のうちTC判定へ影響する条件へ適用可能であることを確認できる
- 自動実行でTCをPASSにする際、E2E実装が必要な期待結果を検証し、根拠に使うE2E実装reviewから対象E2E実装revision / working treeへ追跡してcurrentであることを確認でき、確認不能なら`判定不能`になる
- 今回の新規実行要求を過去結果だけで完了扱いせず、currentな自動runがない場合は`e2e-test-execution`へroutingする
- runner異常と製品FAILが分離され、既存`e2e-test-result-analysis` routingが維持される
- `e2e-test-execution`のPlaywright固有契約が維持される
- `qa-workflow`が必要時だけ2 Skillへroutingできる
- trigger query合計が基準契約どおり（本Plan基準では320）
- semantic case合計が基準契約どおり（本Plan基準では32）
- 新規2 Skillのsemantic evalで、各critical criterion IDが最低1件のcaseから参照される
- deterministic output evalのrepository最低case数が基準契約どおり（本Plan基準では32）
- 既存14 Skillの回帰がPASSする
- `e2e-test-inspection`、`e2e-test-execution`、`test-case-design`等の隣接Skillと新規2 Skillの双方向発火境界が、既存query件数を維持したデータセットと実Agent評価可能時のsmokeで確認される
- `skills-ref validate`が全SkillでPASSする
- README、EVALS、ASSERTIONS、CIの記述と実装が一致する
- 実Agent発火評価を実施できない場合、repo内dataset PASSだけを発火PASSと表現していない
- AI直接操作の実対象smokeを実施できない場合、その経路を未検証として明示している
