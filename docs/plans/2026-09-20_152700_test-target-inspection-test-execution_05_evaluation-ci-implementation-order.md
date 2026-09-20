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
- 操作・遷移、データ・権限依存、既存テスト実装との対応、未確認事項が参照する`対象キー / 要素キー / 状態キー`は現在成果物に存在する、または`未使用`等の明示状態である。`今回の更新`の`追加 / 更新 / 変更なし`も現在成果物のキーを参照するが、`削除確認`だけは更新前成果物に存在したキーへの参照を許可する
- 確認元が空でない
- 画面 / 要素 / 状態 / 操作・遷移 / データ・権限依存等の各記録が確認元、確認version / build、確認日時 / revisionへ追跡できる
- `今回確認`と`既存資料から継承・未再確認`を区別し、部分更新で未再確認行の確認version / build・確認日時 / revisionを今回値へ上げない
- 確認version / buildと確認日時 / revisionが値または明示的未確認状態を持つ
- version / buildが値または明示的未確認状態を持つ
- 既存成果物更新時は今回の更新区分を持つ
- 未確認事項に対象・内容・理由がある
- fixtureで要求された対象 / 要素 / 状態は、確認できた場合は対応する事実テーブルへ、確認できなかった場合は`未確認事項`へ理由・後続影響付きで閉じ、無言で欠落させない。validator通過のために未確認事実を創作しない
- fixtureに存在しない対象キーを創作しない
- secret / cookie / token値を平文成果物へ要求しない契約になっている
- TC判定や後続利用に不要な個人データ・機密情報をfixture上の必須出力にしない
- 削除確認fixtureでは、実対象UI / 状態 / 遷移は同一対象条件の実対象で不存在を確認するか、repoだけで不存在を証明できる明確な根拠がある場合だけ除外し、Page Object / fixture / helper等のrepo事実は対象revisionで不存在を確認した場合だけ除外する。`削除確認`のキーは更新前成果物に存在することを確認し、単に見つからない対象や存在しなかったキーを削除扱いしない
- inspection副作用fixtureでは対象origin、許可範囲、最大回数、実施回数、実施結果、cleanup方法 / 結果、残存状態が記録され、実施回数が最大回数を超えない
- 永続保存fixtureでは保存結果が存在し、保存・更新自体が要求成果物なのに`未保存 / 保存後不整合`のまま完成扱いしない

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
5. 古い確認日時 / version / revisionの資料を現在値として扱わず、version / build変更時は関連範囲だけ再確認する。部分更新で未再確認行の確認version / buildを今回値へ上書きしない
6. 存在しないUI要素、locator、Page Object、routeを創作しない
7. live target確認要求をrepo確認だけで満たした扱いにしない
8. 永続更新では候補成果物を検証してから保存し、保存できない場合に更新済みと表現しない。永続保存・更新自体が要求成果物なら、保存先不明、書込不能、安全な差分更新不能、保存後不整合を残したまま完了扱いしない
9. `未確認`を今回確認対象だが未確認、`確認不能`を今回確認対象だが確認できない状態として区別し、要求範囲外を`未確認`へ混ぜない。必要な`未確認 / 確認不能`が残る場合にrepo情報だけで完了扱いしない
10. 通常の`test-target-inspection`では実対象事実を正本とし、repo / workspaceだけの確認を実対象確認済みへ昇格しない。ユーザーがrepo限定調査を明示した場合だけその限定成果物として扱う
11. inspectionで永続的副作用を伴う操作が必要な場合は対象origin、許可範囲、最大回数、cleanup方法を確認し、確認できなければ操作しない。再試行を含む実施回数を記録して最大回数を超えず、実施した副作用とcleanup結果を成果物へ残す
12. `test-target-inspection`が対象製品コード、Page Object、fixture、helper、既存テストコードを変更しない

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

新規2 Skill側のnegativeだけで境界検証を完了扱いにしません。全Skill同時利用の正規発火評価で双方向の誤発火を検出できるよう、`e2e-test-inspection`、`e2e-test-execution`、`test-case-design`等の隣接Skillについて、既存train / validation件数を維持したまま必要なnegative queryを置換・再配分します。置換は意味的に重複しているnegativeを優先し、既存の固有境界をrepository全体から消しません。削るqueryが担っていた境界はtrain / validationの別caseまたは同等caseで引き続き検証されていることを確認します。既存Skillのquery総数は増やしません。

### 4.2 決定論的validator

最低限、次を検査します。

- 正規セクション / テーブルが存在する
- テストケース入力元 / 成果物参照が存在し、`qa-workflow`成果物、外部成果物、ユーザー直接入力のいずれかを識別できる。永続参照がない場合は`ユーザー提供 / 永続参照なし`等の明示状態を許容する
- `TC revision / content identity`が既存値、または`未提供 / 未確認`等の明示状態を持つ
- 各入力TCが既存TC ID、外部システムの一意識別子等、入力側で既に存在する一意なTC識別子を持つ。識別子を持たないTCへ`test-execution`が正式TC IDを創作しない
- 範囲指定fixtureでは実行開始前に具体的TC識別子集合へ解決され、その集合と結果表のTC識別子集合が一致する
- fixture指定の今回実行対象TC識別子集合と結果表のTC識別子集合が一致する
- fixtureに存在しないTC識別子を創作しない
- 同じTC識別子を不正重複させない。混在実行でも同じTC識別子を複数方式で暗黙に重複実行しない
- 実行方式がTC単位で`AI直接操作`または`自動実行`
- 状態が`PASS / FAIL / 未実行 / 判定不能`
- PASS / FAILには期待結果・実測結果・判定根拠が存在する
- 未実行 / 判定不能には理由が存在する
- 実行済みTCには実測結果・判定根拠が存在し、実在しない証跡参照を要求しない
- 集計値がTC結果表の状態別件数と一致する
- retry / attempt数をTC件数へ混ぜない
- AI直接操作fixtureではTC単位の実行前条件表が存在し、対象origin、アカウント / role、開始状態 / テストデータ、副作用の許可範囲、最大回数、安全cleanup対象 / 方法が確認される。副作用を実施したfixtureでは再試行を含む実施回数が記録され、`実施回数 <= 最大回数`であり、結果不明の副作用操作を状態確認なしに盲目的再試行しない
- TCに事後状態 / 後処理があるfixtureでは、その実施結果が記録され、実行時cleanupと二重実行されない
- cleanup必須fixtureでは実行時cleanup状態が存在し、後処理 / cleanup失敗で確定済みTC結果を書き換えない
- runner異常fixtureで対象TCを製品FAILとして誤分類しない
- 観測不能fixtureでPASSにせず、実行開始済みなら`判定不能`にする
- 自動実行fixtureではTC識別子 → E2E実装 → logical primary → resolved primary TestCase → 実行結果の対応が追跡できる。既存`TC → E2E実装`対応を使う場合は既存TC IDと今回TC識別子が同一TCを指す
- 固定した今回TC識別子集合の自動実行subsetから今回必要なlogical primary集合を実行前に解決し、要求外primaryを暗黙追加しない。runner上必要なdependency / teardownは別扱いとする
- TC要求の対象条件と`e2e-test-execution`が記録したURL / origin、Playwright project、必要なrole / 認証条件、開始状態 / テストデータ、version / build等のうち判定へ影響する条件が整合する
- 自動実行対応表に独自の`対応状態`を追加せず、既存E2E実装参照・resolved primary・実行結果とTC結果を使用する
- run全体PASS、`outcome=expected`、最終retry PASSだけをTC PASS根拠にしない

### 4.3 意味評価

critical候補:

1. TC手順と期待結果に忠実に実行・比較する
2. 実測していない結果を推測してPASS / FAILにしない
3. 期待結果を書き換えて実測へ合わせない。外部成果物・ユーザー直接入力で既に明示された期待結果は今回実行の契約として利用できるが、`SPEC`や製品期待挙動の正本へ昇格しない
4. runner / 認証 / setup / cleanup等の実行失敗と製品FAILを区別する
5. 副作用・権限・cleanupの安全条件を満たさない場合に実行を開始しない
6. 自動実行経路では既存E2E Skillのraw factを再解釈・創作しない
7. TCごとに開始状態を再確認し、前TCの残存状態を暗黙前提にしない
8. TCの事後状態 / 後処理、AI直接操作の安全cleanup、Playwright runner管理cleanupを区別し、TCの製品期待結果判定と別軸で扱う
9. 方式未指定時はE2E対応が存在するだけで自動実行を選ばず、必要な期待結果を十分検証できcurrentなreview / 実装根拠があり、今回環境で安全に実行できる場合だけ自動実行を選ぶ。ユーザー指定の自動実行を勝手にAI直接操作へfallbackしない
10. 今回の新規実行要求を過去の`test-execution`成果物だけで代替しない
11. AI直接操作で副作用操作の結果が不明な場合は状態確認なしに盲目的再試行せず、重複副作用を回避できなければ`判定不能`または`ブロック中`として停止する
12. 自動実行でcurrentな今回runがなければ`e2e-test-execution`へ戻し、異常・未実行・run-level error・cleanup問題は既存契約どおり`e2e-test-result-analysis`を経由する
13. 自動実行でTCをPASSにする前に、currentなE2E実装がPASS判定に必要な期待結果を検証していると確認できる。`adversarial-review`を根拠にする場合はE2E実装変更後の`要再検証`が残っていない等reviewの鮮度も確認し、確認できなければ`判定不能`とする
14. 自動実行では固定TC識別子集合の自動実行subsetから必要logical primary集合を解決し、要求外primaryを暗黙実行しない。TC要求とrunの対象環境差も判定前に確認する
15. AI直接操作 / 自動実行が混在する場合は`test-execution`が固定TC識別子集合と方式を保持し、自動実行subsetだけをE2E Skillへ委譲して同じ`test-execution`へ再開し、同一TCを二重実行せず結果を統合する

semantic evalは最低2 case作成します。

- AI直接操作でPASS / FAIL / 判定不能が混在し、TC間の開始状態、TC後処理、安全cleanupを分離する複数TC
- 自動実行結果利用で未実行またはrunner異常を含み、既存`e2e-test-result-analysis` routingと期待結果検証の十分性を守り、raw statusだけではTC PASSにしないTC

## 5. `qa-workflow` 評価

routing caseへ最低限、次を追加します。

1. テスト対象資料作成だけ → `test-target-inspection`
2. 既存テスト対象資料更新だけ → `test-target-inspection`
3. 詳細TCのAI直接操作 → `test-execution`
4. AI直接操作 / 自動実行が混在 → `test-execution`でTC識別子集合・方式を固定 → 自動実行subsetだけ`e2e-test-execution` → 必要時`e2e-test-result-analysis` → 同じ`test-execution`へ再開して全結果を統合
5. Playwright raw実行のみ → `e2e-test-execution`
6. Playwright正常run後にTC判定 → `e2e-test-execution` → `test-execution`
7. Playwright異常 / 未実行 / run-level error / cleanup失敗・未確認後にTC判定 → `e2e-test-execution` → `e2e-test-result-analysis` → `test-execution`
8. 新規自動実行要求だがcurrentな今回runがない → `test-execution`で自動実行subsetを確定して`e2e-test-execution`へ委譲し、過去結果だけで`test-execution = 再利用`にしない
9. テスト対象資料が古くE2E inspection前に更新が必要 → `test-target-inspection` → `e2e-test-inspection`
10. `test-execution`で期待結果不足 → `test-case-design`または`question-analysis`へ修正routing
11. `test-execution`で対象構造未確認 → 必要時だけ`test-target-inspection`
12. `question-analysis`で一般的な実対象事実が解消 → `test-target-inspection`、汎用TC実行の再開 → `test-execution`
13. TC実行途中で局所ブロックがあっても他TCを安全に継続できるcase

`qa-workflow`自身が2 Skillの内部処理を再定義しないこともsemantic evalで確認します。

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

### Step 4: `test-execution`

- `SKILL.md`
- `references/guidance.md`
- `assets/output-template.md`
- trigger eval
- deterministic output eval / validator
- semantic eval
- テストケース入力元、入力側の既存一意TC識別子、実行対象TC識別子集合、TC revision未提供、外部 / 直接入力TCの期待結果境界、既存結果再利用、AI直接操作preflight、副作用実施回数、TC後処理 / cleanup、結果不明な副作用操作の再試行禁止
- 自動実行のTC識別子 → E2E実装 → logical primary固定 → resolved primary → 結果追跡、対象環境整合、期待結果検証とreview鮮度の十分性確認
- AI直接操作 / 自動実行混在時のsubset委譲・同一`test-execution`再開・重複実行防止
- `e2e-test-execution` / `e2e-test-result-analysis`の既存異常routingを維持

### Step 5: 既存Skillとの接続

- `test-case-design/SKILL.md`とguidanceへテスト対象資料の任意補助入力境界を追加
- `question-analysis`へ`test-target-inspection` / `test-execution`の再開routingを追加
- `e2e-test-inspection`へテスト対象資料の任意再利用境界を追加
- `e2e-test-execution` / `e2e-test-result-analysis`の既存routingを変更せず、`test-execution`への接続だけを必要最小限で追加
- `adversarial-review`（対象: `E2E実装`）の既存期待結果 / assertionレビューを自動実行PASS判定の確認元として再利用
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

## 11. 完了条件

以下をすべて満たしたら実装完了とします。

- 正規Skillが16件になっている
- `test-target-inspection`が独立Skillとして作成・部分更新でき、`未確認`を今回確認対象だが未確認、`確認不能`を今回確認対象だが確認できない状態として区別し、要求範囲外を`未確認`へ混ぜず、必要な`未確認 / 確認不能`をrepo情報だけで完了扱いしない
- テスト対象資料の操作・遷移、データ・権限依存、更新履歴が既存の`対象キー / 要素キー / 状態キー`へ追跡できる
- inspection副作用を実施した場合は許可範囲・最大回数・実施回数・cleanup結果・残存状態が記録され、実施回数が最大回数を超えない
- 実対象UI / 状態 / 遷移とrepo事実で削除判定の根拠を分け、単に見つからない情報を削除しない
- `test-target-inspection`成果物を`e2e-test-inspection`等が任意入力として再利用でき、各継承行の確認version / build・revisionを保持したうえで、該当事実へ影響するrole / viewport / locale / feature flag / データ条件等の差異を確認する
- 永続保存・更新が要求成果物の場合は保存成功まで完了にせず、`qa-workflow`利用時の案件コンテキスト`既存QA成果物`更新を`qa-workflow`が担当する
- テスト対象資料が仕様Authorityとして扱われない
- `test-execution`が`qa-workflow`成果物、外部成果物、ユーザー直接入力のTCを受け、入力側の既存一意TC識別子を使い、外部 / 直接入力の期待結果を今回実行契約として扱いながら仕様Authorityへ昇格せず、AI直接操作と検証済み自動実行結果利用の両方を扱える
- PASS / FAIL / 未実行 / 判定不能のTC結果契約が成立し、workflow上の`ブロック中`と分離される
- 実行開始前に今回要求された具体的TC識別子集合が固定され、識別不能TCへ正式TC IDを創作せず、その集合と結果集合の完全性を`test-execution`自身が検査できる
- TC revision / content identityが未提供でも今回実行は可能で、未提供状態を明示し、過去結果のcurrent再利用では鮮度を確認する
- AI直接操作の実行前条件がTC単位で記録され、再試行を含む副作用実施回数が最大回数以下であることを記録・検証し、結果不明な副作用操作を盲目的再試行せず、TC事後状態 / 後処理、実行時cleanup、Playwright runner管理cleanupが区別される
- TC結果と後処理 / cleanup状態が別軸で保持される
- 自動実行で固定TC識別子集合の自動実行subset → E2E実装 → 今回logical primary集合 → resolved primary TestCase → 実行結果を追跡でき、要求外primaryを暗黙追加しない
- AI直接操作 / 自動実行の混在時に、自動実行subsetだけをE2E Skillへ委譲して同じ`test-execution`へ再開し、同一TCを重複実行せず全結果を統合できる
- 自動実行結果が今回要求したURL / origin、project、role / 認証、開始状態 / データ、version / build等のうちTC判定へ影響する条件へ適用可能であることを確認できる
- 自動実行でTCをPASSにする際、E2E実装が必要な期待結果を検証し、根拠に使うE2E実装reviewもcurrentであることを確認でき、確認不能なら`判定不能`になる
- 今回の新規実行要求を過去結果だけで完了扱いせず、currentな自動runがない場合は`e2e-test-execution`へroutingする
- runner異常と製品FAILが分離され、既存`e2e-test-result-analysis` routingが維持される
- `e2e-test-execution`のPlaywright固有契約が維持される
- `qa-workflow`が必要時だけ2 Skillへroutingできる
- trigger query合計が基準契約どおり（本Plan基準では320）
- semantic case合計が基準契約どおり（本Plan基準では32）
- deterministic output evalのrepository最低case数が基準契約どおり（本Plan基準では32）
- 既存14 Skillの回帰がPASSする
- `e2e-test-inspection`、`e2e-test-execution`、`test-case-design`等の隣接Skillと新規2 Skillの双方向発火境界が、既存query件数を維持したデータセットと実Agent評価可能時のsmokeで確認される
- `skills-ref validate`が全SkillでPASSする
- README、EVALS、ASSERTIONS、CIの記述と実装が一致する
- 実Agent発火評価を実施できない場合、repo内dataset PASSだけを発火PASSと表現していない
- AI直接操作の実対象smokeを実施できない場合、その経路を未検証として明示している
