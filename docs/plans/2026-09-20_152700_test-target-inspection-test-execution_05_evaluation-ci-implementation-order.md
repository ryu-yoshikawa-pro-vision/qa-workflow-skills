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

最低限、次を検査します。

- 正規セクション / テーブルが存在する
- 対象キーが一意
- 要素キーが一意
- 要素の対象キーが存在する
- 状態キーが一意
- 状態の対象キーが存在する
- 確認元が空でない
- 画面 / 要素 / 状態 / 操作・遷移 / データ・権限依存等の各記録が確認元と確認日時 / revisionへ追跡できる
- `今回確認`と`既存資料から継承・未再確認`を区別し、部分更新で未再確認行の鮮度を上げない
- 確認日時 / revisionが値または明示的未確認状態を持つ
- version / buildが値または明示的未確認状態を持つ
- 既存成果物更新時は今回の更新区分を持つ
- 未確認事項に対象・内容・理由がある
- fixtureで要求された対象 / 要素 / 状態を欠落させない
- fixtureに存在しない対象キーを創作しない
- secret / cookie / token値を平文成果物へ要求しない契約になっている
- TC判定や後続利用に不要な個人データ・機密情報をfixture上の必須出力にしない
- 削除確認fixtureでは、存在しないことを確認できた対象だけが現在一覧から除外され、単に未確認の対象を削除しない

意味判断が必要な次はdeterministic validatorへ入れません。

- locatorの最適性
- UI抽象化の粒度
- 画面分割の妥当性
- POMとしての設計品質

### 3.3 意味評価

`rubric.json`のcritical候補:

1. 実対象・repo・ユーザー提供情報を区別し、確認できない値を推測補完しない
2. 現在観測した実装を仕様Authorityへ昇格しない
3. テスト設計・AI直接操作・E2E inspectionから利用可能な粒度で整理する
4. 更新時に既存の有効情報を不必要に消さず、変更範囲だけを更新する
5. 古い確認日時 / version / revisionの資料を現在値として扱わず、version / build変更時は関連範囲だけ再確認する
6. 存在しないUI要素、locator、Page Object、routeを創作しない
7. live target確認要求をrepo確認だけで満たした扱いにしない
8. 永続更新では候補成果物を検証してから保存し、保存できない場合に更新済みと表現しない

semantic evalは最低2 case作成します。

- 新規作成
- 既存資料の部分更新

## 4. `test-execution` の評価

### 4.1 発火境界

positiveには最低限、次を含めます。

- 詳細TCを実画面でAIが操作してPASS / FAILを確認する
- 自動化対象外も含む指定TCを実行する
- 検証済み自動実行結果をTC期待結果と照合する
- 未実行 / 判定不能理由を含めTC実行結果を整理する

negativeには最低限、次を含めます。

- Playwrightをrunnerとして起動しraw resultだけ取得 → `e2e-test-execution`
- Playwright FAIL原因分析 → `e2e-test-result-analysis`
- Playwright runの人間向け報告 → `e2e-test-reporting`
- TC設計 → `test-case-design`
- テスト対象資料作成 → `test-target-inspection`

### 4.2 決定論的validator

最低限、次を検査します。

- 正規セクション / テーブルが存在する
- 元テストケース成果物参照とTC revision / content identityが存在する
- fixture指定の今回実行対象TC ID集合と結果表のTC ID集合が一致する
- fixtureに存在しないTC IDを創作しない
- 同じTC IDを不正重複させない
- 実行方式がTC単位で`AI直接操作`または`自動実行`
- 状態が`PASS / FAIL / 未実行 / 判定不能`
- PASS / FAILには期待結果・実測結果・判定根拠が存在する
- 未実行 / 判定不能には理由が存在する
- 実行済みTCには実測結果・判定根拠が存在し、実在しない証跡参照を要求しない
- 集計値がTC結果表の状態別件数と一致する
- retry / attempt数をTC件数へ混ぜない
- AI直接操作fixtureでは対象origin、アカウント / role、副作用の許可範囲・最大回数、cleanup対象 / 方法が実行前条件として確認される
- cleanup必須fixtureではcleanup状態が存在し、cleanup失敗で確定済みTC結果を書き換えない
- runner異常fixtureで対象TCを製品FAILとして誤分類しない
- 観測不能fixtureでPASSにせず、実行開始済みなら`判定不能`にする
- 自動実行fixtureではTC → E2E実装 → logical primary → resolved primary TestCase → 実行結果の対応が追跡できる
- run全体PASS、`outcome=expected`、最終retry PASSだけをTC PASS根拠にしない

### 4.3 意味評価

critical候補:

1. TC手順と期待結果に忠実に実行・比較する
2. 実測していない結果を推測してPASS / FAILにしない
3. 期待結果を書き換えて実測へ合わせない
4. runner / 認証 / setup / cleanup等の実行失敗と製品FAILを区別する
5. 副作用・権限・cleanupの安全条件を満たさない場合に実行を開始しない
6. 自動実行経路では既存E2E Skillのraw factを再解釈・創作しない
7. TCごとに開始状態を再確認し、前TCの残存状態を暗黙前提にしない
8. cleanup状態とTCの製品期待結果判定を別軸で扱う
9. 指定なしの実行方式を既存実装と安全条件からTC単位で決め、自動実行後にPASS取得目的でAI直接操作へ自動fallbackしない

semantic evalは最低2 case作成します。

- AI直接操作でPASS / FAIL / 判定不能が混在し、TC間の開始状態とcleanupを分離する複数TC
- 自動実行結果利用で未実行またはrunner異常を含み、raw statusだけではTC PASSにしないTC

## 5. `qa-workflow` 評価

routing caseへ最低限、次を追加します。

1. テスト対象資料作成だけ → `test-target-inspection`
2. 既存テスト対象資料更新だけ → `test-target-inspection`
3. 詳細TCのAI直接操作 → `test-execution`
4. Playwright raw実行のみ → `e2e-test-execution`
5. Playwright実行後にTC判定 → `e2e-test-execution` → `test-execution`。raw factだけでは判定できない場合だけ`e2e-test-result-analysis`
6. テスト対象資料が古くE2E inspection前に更新が必要 → `test-target-inspection` → `e2e-test-inspection`
7. `test-execution`で期待結果不足 → `test-case-design`または`question-analysis`へ修正routing
8. `test-execution`で対象構造未確認 → 必要時だけ`test-target-inspection`
9. `question-analysis`で一般的な実対象事実が解消 → `test-target-inspection`、汎用TC実行の再開 → `test-execution`
10. TC実行途中で局所ブロックがあっても他TCを安全に継続できるcase

`qa-workflow`自身が2 Skillの内部処理を再定義しないこともsemantic evalで確認します。

## 6. 既存E2E Skill回帰

新規Skill追加により次の境界が崩れていないことを確認します。

### `e2e-test-inspection`

- E2E実装可否・安全条件・Playwright固有事実の確認責務を維持する
- テスト対象資料が存在してもE2E固有preflightを省略しない
- 古いテスト対象資料をcurrentとみなさない

### `e2e-test-execution`

- Playwright runner固有のstatus / attempt / process / artifact / ownership / cleanup契約を維持する
- TCの意味上のPASS / FAILを新たに所有しない
- raw result契約を`test-execution`向けに簡略化しない

### `e2e-test-result-analysis`

- runner異常・環境・実装・対象製品等の原因分析責務を維持する
- TC期待結果を書き換える責務を持たせない

### `e2e-test-reporting`

- Playwright run報告の責務を維持する
- 汎用TC結果報告へ拡張しない

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

### Step 4: `test-execution`

- `SKILL.md`
- `references/guidance.md`
- `assets/output-template.md`
- trigger eval
- deterministic output eval / validator
- semantic eval
- `e2e-test-execution` / `e2e-test-result-analysis`境界

### Step 5: 既存Skillとの接続

- `test-case-design`へテスト対象資料の任意補助入力境界を追加
- `question-analysis`へ`test-target-inspection` / `test-execution`の再開routingを追加
- `e2e-test-inspection`へテスト対象資料の任意再利用境界を追加
- `e2e-test-execution` / `e2e-test-result-analysis`との自動実行境界を必要最小限で同期
- `coverage-analysis`へ新用途は追加しない

### Step 6: `qa-workflow`

- 16 Skill化
- routing
- workflow state template
- 案件コンテキストの既存`既存QA成果物`欄を使ったテスト対象資料参照
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
- `test-execution`へPlaywright runner内部契約を複製する
- `e2e-test-execution`を削除または汎用化する
- runner異常を製品FAILとして扱う
- 実測していない期待結果をPASSへ変換する
- 自動化対象外TCを実行対象外とみなす
- `test-target-inspection`成果物がないだけで実行可能なTCを止める
- 将来のAPI / mobile / DB等のためだけにrunner adapter frameworkを作る
- 今回使わない共通artifact registryや外部knowledge baseを追加する
- 新規2 Skillを現在要件だけを理由にPR #11のruntime / Machine Entity対象へ追加する
- `test-execution`結果の完全性確認だけのために`coverage-analysis`へ新しい比較対象を追加する

## 11. 完了条件

以下をすべて満たしたら実装完了とします。

- 正規Skillが16件になっている
- `test-target-inspection`が独立Skillとして作成・部分更新・未確認保持を扱える
- `test-target-inspection`成果物を`e2e-test-inspection`等が任意入力として再利用できる
- テスト対象資料が仕様Authorityとして扱われない
- `test-execution`がAI直接操作と検証済み自動実行結果利用の両方を扱える
- PASS / FAIL / 未実行 / 判定不能のTC結果契約が成立し、workflow上の`ブロック中`と分離される
- 今回要求されたTC集合と結果集合の完全性を`test-execution`自身が検査できる
- TC結果とcleanup状態が別軸で保持される
- 自動実行でTC → E2E実装 → logical primary → resolved primary TestCase → 実行結果を追跡できる
- runner異常と製品FAILが分離される
- `e2e-test-execution`のPlaywright固有契約が維持される
- `qa-workflow`が必要時だけ2 Skillへroutingできる
- trigger query合計が基準契約どおり（本Plan基準では320）
- semantic case合計が基準契約どおり（本Plan基準では32）
- deterministic output evalのrepository最低case数が基準契約どおり（本Plan基準では32）
- 既存14 Skillの回帰がPASSする
- `skills-ref validate`が全SkillでPASSする
- README、EVALS、ASSERTIONS、CIの記述と実装が一致する
- 実Agent発火評価を実施できない場合、repo内dataset PASSだけを発火PASSと表現していない
- AI直接操作の実対象smokeを実施できない場合、その経路を未検証として明示している
