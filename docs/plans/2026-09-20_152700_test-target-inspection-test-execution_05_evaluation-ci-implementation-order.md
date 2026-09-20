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

実装開始時に基準branch側でこれらの契約値が変更済みなら、その時点の正本から再計算し、本Planの14 / 280 / 28を機械的に上書きしません。

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
- 確認日時 / revisionが値または明示的未確認状態を持つ
- version / buildが値または明示的未確認状態を持つ
- 既存成果物更新時は今回の更新区分を持つ
- 未確認事項に対象・内容・理由がある
- fixtureで要求された対象 / 要素 / 状態を欠落させない
- fixtureに存在しない対象キーを創作しない
- secret / cookie / token値を平文成果物へ要求しない契約になっている

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
5. 古い確認日時 / version / revisionの資料を現在値として扱わない
6. 存在しないUI要素、locator、Page Object、routeを創作しない

semantic evalは最低2 case作成します。

- 新規作成
- 既存資料の部分更新

## 4. `test-execution` の評価

### 4.1 発火境界

positiveには最低限、次を含めます。

- 詳細TCを実画面でAIが操作してPASS / FAILを確認する
- 自動化対象外も含む指定TCを実行する
- 検証済み自動実行結果をTC期待結果と照合する
- 未実行 / ブロック理由を含めTC実行結果を整理する

negativeには最低限、次を含めます。

- Playwrightをrunnerとして起動しraw resultだけ取得 → `e2e-test-execution`
- Playwright FAIL原因分析 → `e2e-test-result-analysis`
- Playwright runの人間向け報告 → `e2e-test-reporting`
- TC設計 → `test-case-design`
- テスト対象資料作成 → `test-target-inspection`

### 4.2 決定論的validator

最低限、次を検査します。

- 正規セクション / テーブルが存在する
- fixture指定の全TC IDが結果表に存在する
- fixtureに存在しないTC IDを創作しない
- 同じTC IDを不正重複させない
- 実行方式が`AI直接操作`または`自動実行`
- 状態が`PASS / FAIL / 未実行 / ブロック中`
- PASS / FAILには期待結果・実測結果・判定根拠が存在する
- 未実行 / ブロック中には理由が存在する
- 実行済みTCには実行結果参照または証跡参照が存在する
- 集計値がTC結果表の状態別件数と一致する
- retry / attempt数をTC件数へ混ぜない
- cleanup必須fixtureではcleanup状態が存在する
- runner異常fixtureで対象TCを製品FAILとして誤分類しない
- 観測不能fixtureでPASSにしない

### 4.3 意味評価

critical候補:

1. TC手順と期待結果に忠実に実行・比較する
2. 実測していない結果を推測してPASS / FAILにしない
3. 期待結果を書き換えて実測へ合わせない
4. runner / 認証 / setup / cleanup等の実行失敗と製品FAILを区別する
5. 副作用・権限・cleanupの安全条件を満たさない場合に実行を継続しない
6. 自動実行経路では既存E2E Skillのraw factを再解釈・創作しない

semantic evalは最低2 case作成します。

- AI直接操作でPASS / FAILが混在する複数TC
- 自動実行結果利用で未実行またはrunner異常を含むTC

## 5. `qa-workflow` 評価

routing caseへ最低限、次を追加します。

1. テスト対象資料作成だけ → `test-target-inspection`
2. 既存テスト対象資料更新だけ → `test-target-inspection`
3. 詳細TCのAI直接操作 → `test-execution`
4. Playwright raw実行のみ → `e2e-test-execution`
5. Playwright実行後にTC判定 → `e2e-test-execution` → 必要なら`e2e-test-result-analysis` → `test-execution`
6. テスト対象資料が古くE2E inspection前に更新が必要 → `test-target-inspection` → `e2e-test-inspection`
7. TC結果の追跡性確認 → `coverage-analysis`、対象`TC → テスト実行結果`
8. `test-execution`で期待結果不足 → `test-case-design`または`question-analysis`へ修正routing
9. `test-execution`で対象構造未確認 → 必要時だけ`test-target-inspection`
10. TC実行途中で局所ブロックがあっても他TCを安全に継続できるcase

`qa-workflow`自身が2 Skillの内部処理を再定義しないこともsemantic evalで確認します。

## 6. `coverage-analysis` 評価

新規対象`TC → テスト実行結果`について最低限、次を確認します。

- 詳細TC集合を母集団として取得する
- 各TCがPASS / FAIL / 未実行 / ブロック中のいずれかへ対応する
- 未実行 / ブロック中をcoverage済みとして閉じない
- retry attemptを別TCとして数えない
- E2E自動化対象外TCも実行対象なら追跡対象になる
- `TC → E2E実装`と混同しない
- テスト実行結果側だけに存在する未知TC IDを検出する

既存3用途の回帰fixtureは維持します。

## 7. 既存E2E Skill回帰

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

## 8. CI変更

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

現行の`tests/skills/evals/semantic/test_semantic_datasets.py`でrepository合計28を固定している箇所を32へ更新します。

### 共通validator

`scripts/skills/evals/deterministic/common.py`:

- `CANONICAL_SKILLS`へ2 Skill追加
- `MULTI_USE_SKILL_TARGETS`は今回変更しない
- 新規共通ID体系は追加しない

## 9. README / EVALS / ASSERTIONS

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

存在する場合は、新規validator assertion ID、`coverage-analysis`追加対象、workflow routing assertionを同期します。実装開始時に現行構成を確認して対象ファイルを確定します。

## 10. 実装順序

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

### Step 5: `coverage-analysis`

- `TC → テスト実行結果`対象追加
- template / guidance / validator / fixture / semantic eval更新
- 既存3用途回帰

### Step 6: `qa-workflow`

- 16 Skill化
- routing
- workflow state template
- 途中開始 / 再利用 / ブロック / 再開
- routing fixture / deterministic validator / semantic eval

### Step 7: 文書・CI同期

- README
- EVALS
- ASSERTIONS
- GitHub Actions固定値
- repository eval tests

### Step 8: 全体検証

- `skills-ref validate` 全Skill
- trigger dataset構造検証
- deterministic output eval
- semantic dataset構造検証
- repository deterministic tests
- workflow routing tests
- 既存14 Skill回帰
- 可能なら実Agent上で新規2 Skillのpositive / negative発火smoke

## 11. 実装時に避けること

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

## 12. 完了条件

以下をすべて満たしたら実装完了とします。

- 正規Skillが16件になっている
- `test-target-inspection`が独立Skillとして作成・部分更新・未確認保持を扱える
- `test-target-inspection`成果物を`e2e-test-inspection`等が任意入力として再利用できる
- テスト対象資料が仕様Authorityとして扱われない
- `test-execution`がAI直接操作と検証済み自動実行結果利用の両方を扱える
- PASS / FAIL / 未実行 / ブロック中の契約が成立する
- runner異常と製品FAILが分離される
- `e2e-test-execution`のPlaywright固有契約が維持される
- `coverage-analysis`が`TC → テスト実行結果`を検査できる
- `qa-workflow`が必要時だけ2 Skillへroutingできる
- trigger query合計が基準契約どおり（本Plan基準では320）
- semantic case合計が基準契約どおり（本Plan基準では32）
- deterministic output evalのrepository最低case数が基準契約どおり（本Plan基準では32）
- 既存14 Skillの回帰がPASSする
- `skills-ref validate`が全SkillでPASSする
- README、EVALS、ASSERTIONS、CIの記述と実装が一致する
- 実Agent発火評価を実施できない場合、repo内dataset PASSだけを発火PASSと表現していない
