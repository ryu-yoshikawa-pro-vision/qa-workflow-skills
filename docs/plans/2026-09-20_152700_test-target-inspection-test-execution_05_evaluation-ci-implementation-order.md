# テスト対象資料管理・テスト実行Skill追加Plan

## 1. 評価方針

新規2 Skill追加後も現行の評価層を維持します。

1. Agent Skills仕様検証
2. 発火評価データセット検証
3. 決定論的出力評価
4. 意味評価
5. `qa-workflow` routing / 状態評価
6. 既存14 Skillの回帰

repo内評価だけで実Agent上の動作をPASS扱いしません。browser操作、画像判断、Playwright MCP / CLI利用、永続更新競合等は実Agent / 実対象を利用できる場合のsmokeで確認します。

## 2. Skill数と固定値

本Plan基準では14 Skillから16 Skillへ増えます。

現行の次契約が維持されている場合:

- trigger train: 12 query / Skill
- trigger validation: 8 query / Skill
- semantic: 2 case / Skill
- deterministic output eval: 各Skill 2 case以上

repository合計は次です。

- trigger query: 280 → 320
- semantic case: 28 → 32
- deterministic output eval最低case数: 28 → 32

実装開始時に最新`main`と先行PRを確認し、その時点の正規契約を優先します。

## 3. `test-target-inspection`の評価

### 3.1 発火境界

positiveには最低限、次を含めます。

- 現在の実画面を確認してUI情報とふるまいを資料化する
- 既存のテスト対象資料が今も正しいか実対象で確認して更新する
- 生きたテスト対象の画面・状態・遷移・操作反応を管理する
- DOMだけでは分からないレイアウトやUI崩れを画像でも確認して記録する

negativeには最低限、次を含めます。

- POM / Page Objectコード実装 → `e2e-test-implementation`
- Playwright E2E実装可否のinspection → `e2e-test-inspection`
- 詳細TC作成 → `test-case-design`
- TCを実行して結果報告 → `test-execution`
- 仕様Authority整理 → `spec-analysis`

### 3.2 決定論的validator

保存済みMarkdownから機械判定できる契約だけを検査します。

- 正規セクション / 必須テーブルが存在する
- 対象キー / 要素キー / 状態キーが一意で参照整合している
- 新規成果物では文書ローカルの正規キー形式を使用する
- 今回対象範囲が`変更なし / 更新 / 追加 / 削除確認 / 未確認 / 確認不能`の適切な状態へ閉じている
- 既存成果物更新時だけ`今回の更新`が存在する
- 今回確認した行だけ確認日時 / version / build等が今回値へ更新される
- 未確認行の鮮度を成果物全体の更新日時だけで上げない
- 実対象で確認していない範囲をrepo情報だけでcurrentと表現しない
- UI要素 / 状態 / 操作・ふるまいが実在キーへ追跡できる
- 視覚情報表は必要時だけ存在でき、存在する場合は対象キーまたは要素 / 状態キーへ追跡できる
- 既存テスト実装対応表は任意であり、存在する場合だけ参照整合を検査する
- 保存結果・競合状態の記録が矛盾しない
- secret / cookie / token等の値を必須出力にしない

deterministic validatorだけで、実際に実対象を操作したこと、画像を正しく認識したこと、条件付き更新が実競合を防いだことまでは証明しません。

### 3.3 意味評価

意味評価は次の観点を中心にします。

1. 生きた実対象を正本として観測し、repoだけの情報をcurrentな実対象情報へ昇格しない
2. UI構造だけでなく、操作に対する反応・状態変化・遷移を必要十分に記録する
3. 視覚情報が必要な場面で画像を使用し、画像だけでrole / accessibility情報や仕様を創作しない
4. 既存資料の今回対象範囲を実対象と照合し、変更なしを含め鮮度を正しく管理する
5. 実対象の現在挙動を仕様Authorityへ昇格しない
6. POM / Page Object等を必須化せず、プロジェクトの既存構成に応じた任意参照として扱う
7. 副作用・証跡・永続更新の安全境界を守る

semantic evalは最低2 case作成します。

- 既存資料を現在UIと照合し、変更なしと更新箇所が混在するcase
- DOM / accessibility treeだけでは不足し、画像で視覚情報を確認するcase

## 4. `test-execution`の評価

### 4.1 発火境界

positiveには最低限、次を含めます。

- TCを実行前にGiven / When / Then構造のYAMLへ整理し、曖昧さを確認してからAIが画面操作・結果報告する
- AIがPlaywright MCP等で人間と同じようにTCを画面操作して結果を報告する
- AIがブラウザを操作して指定TCを手動テスト相当で実施する
- Playwright CLIを使ってTCを実行し、期待結果と実測結果を報告する
- 今回runだけのPlaywrightコードを作成・実行してTC結果を報告する
- screenshotを見てUI崩れを含む期待結果を確認する

negativeには最低限、次を含めます。

- repoへ残すPlaywright E2Eを実装 / 更新 → `e2e-test-inspection` / `e2e-test-implementation`
- 既存repo E2Eをraw runner契約で実行するだけ → `e2e-test-execution`
- 既存Playwright runの原因分析 → `e2e-test-result-analysis`
- Playwright runner固有の詳細報告だけ → `e2e-test-reporting`
- 詳細TC設計 → `test-case-design`
- 生きたテスト対象資料の収集 / 管理 → `test-target-inspection`

### 4.2 決定論的validator

保存済み出力から機械判定できる契約だけを検査します。

- 1成果物が1つのTC入力元 / snapshotを持つ
- 今回TC識別子集合とTC結果表の集合が一致する
- 正式TC IDを創作しない
- TC結果が`PASS / FAIL / 未実行 / 判定不能`の正規値である
- PASS / FAILには期待結果・実測結果・判定根拠が存在する
- 未実行 / 判定不能には理由が存在する
- 固定した全TCに実行前YAMLまたはその成果物参照が存在する
- 実行前YAMLが入力TC識別子へ追跡できる
- `scenario.given / when / then`、`unresolved`、`cleanup`の必須構造を満たす
- `unresolved`が空でないTCを操作済み / PASS / FAILとして扱っていない
- 使用した実行手段が記録される
- 手順・観測結果が判定根拠へ追跡できる
- 画像を使用した場合は視覚確認行がTC / 観測点へ追跡できる
- 画像を使用していないTCへ画像参照を必須化しない
- TC外の追加観測をTC結果と混同しない
- 副作用scope、最大回数、累計実施回数が出力上整合する
- TC後処理と実行時cleanupを混同しない
- 集計がTC結果表と一致する
- 実行結果報告セクションが存在する
- 実在しない証跡参照を要求しない
- 機密情報を必須出力にしない

一時Playwrightコードが本当に今回runだけで使われたか、Playwright MCPで実際に操作したか、画像判定が妥当かはoutput validatorだけで証明しません。

### 4.3 意味評価

semantic rubricは次の観点を中心にします。

1. 元TCをGiven / When / Then構造のYAMLへ意味を変えず整理し、曖昧な前提・操作・期待結果・観測方法を推測で補完しない
2. 人間の手動テスト相当としてTC手順に沿って実対象を操作し、PASSを得るために勝手な別経路へ迂回しない
3. 実測していない結果を推測してPASS / FAILにしない
4. DOM / accessibility tree等の構造情報と画像による視覚情報を確認対象に応じて使い分ける
5. UI崩れ等のTC外発見を追加観測として扱い、期待結果に関係しない事象で元TCをFAILにしない
6. 今回run用の一時Playwrightコードと、repoへ残すE2E資産を区別する
7. 副作用、開始状態、事後状態、cleanup、証跡の安全境界を守る
8. TC結果だけでなく、人間が判断できる実行結果報告まで完成させる

semantic evalは最低2 case作成します。

- 元TCの曖昧さを実行前YAMLの`unresolved`へ残して該当TCを`未実行`にし、明確なTCだけPlaywright MCP等で操作して画像確認を含むPASS / FAIL / 判定不能を報告するcase
- Playwright CLI / 今回run用の一時コードを使用し、実行前YAML・画像確認・repoへ残すE2E実装との境界をまとめて確認するcase

## 5. `qa-workflow`評価

routing caseへ最低限、次を追加します。

1. 生きたテスト対象の情報収集 / 更新 → `test-target-inspection`
2. 既存資料がcurrentか実対象で確認 → `test-target-inspection`
3. 詳細TCを実行前YAMLへ整理し、曖昧さを確認してからAIがPlaywright MCP等で実行・結果報告 → `test-execution`
4. AIがPlaywright CLI / 今回run用コードでTCを実行して結果報告 → `test-execution`
5. TC実行中にrepoへ残すE2E実装が必要 → `qa-workflow` → `e2e-test-inspection` → `e2e-test-implementation`
6. 既存repo E2Eをraw runner契約で実行 → `e2e-test-execution`
7. 既存repo E2E異常 → `e2e-test-result-analysis`
8. 既存repo E2EのPlaywright固有詳細報告 → `e2e-test-reporting`
9. 既存repo E2Eの結果をTC結果として報告する要求 → 必要なE2E経路後に`test-execution`
10. TC開始後の対象変更 → 旧`test-execution`を理由付きで閉じ、新しい成果物 / versionを開始

`qa-workflow`自身は各Skillの観測・実行ロジックを再定義しません。

## 6. 既存Skill回帰

### `e2e-test-inspection`

- repo E2E実装前のPlaywright固有inspection責務を維持する
- currentな`test-target-inspection`成果物を任意入力として再利用できる
- テスト対象資料があってもPlaywright固有確認を省略しない

### `e2e-test-implementation`

- repoへ残すPlaywright E2Eの実装 / 更新責務を維持する
- 今回runだけの一時コード生成を必須責務へ広げない

### `e2e-test-execution`

- 既存 / 実装済みrepo E2Eのrunner固有契約を維持する
- `test-execution`の人間相当UI操作を取り込まない
- raw result契約を一般TC報告向けに簡略化しない

### `e2e-test-result-analysis`

- 既存repo E2Eの異常原因分析責務を維持する
- `test-execution`で見つかったTC FAILを自動的に原因分析対象へ変えない

### `e2e-test-reporting`

- Playwright runner固有報告を維持する
- 一般TC結果報告を取り込まない

### `test-case-design` / `question-analysis`

- `test-case-design`はcurrentなテスト対象資料をUI名称・到達方法・具体手順・観測可能性の補助入力として利用できる
- テスト対象資料を期待結果の仕様根拠にしない
- `question-analysis`は解消内容に応じて`test-target-inspection` / `test-execution`へ再開できる

## 7. CI変更

### `.github/workflows/validate-skills.yml`

- expected Skill一覧へ2 Skill追加
- Skill countを16へ更新
- trigger query repository合計を320へ更新
- README / EVALSで新Skill名が説明されていることを確認

### `.github/workflows/deterministic-output-evals.yml`

- skills一覧へ2 Skill追加
- repository最低case数を32へ更新

### semantic dataset test

- 正規Skill一覧へ2 Skill追加
- repository合計を基準契約に合わせて更新
- 新規2 Skillではcritical criterion IDが最低1件のsemantic caseから参照されることを確認
- 既存Skillへ同じ制約を一括適用しない

### 共通validator

`scripts/skills/evals/deterministic/common.py`:

- `CANONICAL_SKILLS`へ2 Skill追加
- `MULTI_USE_SKILL_TARGETS`は今回変更しない
- 新規共通ID体系は追加しない

## 8. README / EVALS / ASSERTIONS

### README

実装後の実契約に合わせて以下を説明します。

- 16 Skill構成
- `test-target-inspection`: 生きた実対象のUI情報・ふるまい収集 / 管理
- `test-execution`: AIによる手動テスト相当のTC実行・結果報告
- Given / When / Then構造の実行前YAML生成と`unresolved`判定
- Playwright MCP等の対話操作、CLI / 一時コード利用
- 画像判断
- repoへ残すE2Eと今回run用一時コードの境界
- 既存E2E Skillとの責務境界

### EVALS

- 対象Skill一覧
- trigger / semantic合計
- 新規2 Skillの発火境界
- 隣接Skillとの双方向境界
- repo内評価と実Agent評価の区別

### ASSERTIONS

新規2 Skillのdeterministic assertion IDとworkflow routing assertionを同期します。

## 9. 実装順序

### Step 1: 基準再確認

- 最新`main`との差分確認
- Draft PR #11等の先行変更確認
- Skill数 / trigger / semantic / deterministic基準再計算
- 既存評価PASS確認

### Step 2: 共通Skill登録

- `CANONICAL_SKILLS`へ2 Skill追加
- CI / repository Skill一覧更新

### Step 3: `test-target-inspection`

- `SKILL.md`
- `references/guidance.md`
- `assets/execution-plan-template.yaml`
- `assets/output-template.md`
- trigger / deterministic / semantic eval
- 実対象currentness確認
- UI構造・ふるまい収集
- DOM / accessibility treeと画像の使い分け
- 視覚情報テーブル
- 部分更新・変更なし管理
- 条件付き更新 / 再読込比較
- POM等は任意参照
- 証跡保護

### Step 4: `test-execution`

- `SKILL.md`
- `references/guidance.md`
- `assets/output-template.md`
- trigger / deterministic / semantic eval
- Playwright MCP等の対話操作
- Playwright CLI / 今回run用一時コード
- 人間の手動テスト相当の操作手順
- DOM / accessibility treeと画像の使い分け
- TC外追加観測
- PASS / FAIL / 未実行 / 判定不能
- 副作用 / 後処理 / cleanup
- TC結果報告
- repoへ残すE2E資産との境界

### Step 5: 既存Skillとの接続

- `test-case-design`へcurrentなテスト対象資料の任意補助入力境界
- `question-analysis`の再開routing
- `e2e-test-inspection`へcurrentなテスト対象資料の任意再利用
- `e2e-test-implementation`のrepo永続E2E責務維持
- `e2e-test-execution` / `e2e-test-result-analysis` / `e2e-test-reporting`の既存責務維持

### Step 6: `qa-workflow`

- 16 Skill化
- routing
- workflow state
- テスト対象資料成果物参照の案件コンテキスト反映
- ブロック / 再開 / 変更伝播
- routing fixture / deterministic / semantic eval

### Step 7: 文書・CI同期

- README
- EVALS
- ASSERTIONS
- GitHub Actions
- repository eval tests

### Step 8: 全体検証

- `skills-ref validate`
- trigger dataset構造
- deterministic output eval
- semantic dataset構造
- repository tests
- workflow routing tests
- 既存14 Skill回帰
- 実Agentが利用可能なら`test-target-inspection`で実対象currentness確認を実施
- Playwright MCP等が利用可能なら`test-execution`で人間相当の非破壊TCを実行
- 画像確認可能なら視覚観測を最低1 case確認
- CLI / 一時コード経路を安全に試せる場合は最低1 case確認
- 利用できないruntime経路は未検証として記録する

## 10. 実装時に避けること

- `test-target-inspection`をrepo情報だけでcurrent扱いにする
- `test-target-inspection`で製品全体のfull scanを毎回必須にする
- POM / Page Object生成を`test-target-inspection`の目的にする
- 実対象の現在挙動を仕様Authorityへ昇格する
- 画像だけでrole / accessibility情報 / 仕様を推測する
- すべての観測へ不要なscreenshotを要求する
- 実行前YAMLを元TCの正本や仕様Authorityとして扱う
- YAML化の過程で曖昧な期待結果・前提・操作をAIが独自補完する
- Gherkin / Cucumber全構文を今回要件のためだけに実装する
- `test-execution`を既存E2E結果の集約・判定だけのSkillにする
- `test-execution`で人間のUI経路を避けるためにbackend API / DBを直接操作する
- TCのPASSを得るために手順外の別経路へ勝手に迂回する
- TC外で見つけたUI崩れだけを理由に元TCをFAILへ変更する
- 今回run用一時コードをrepoの保守対象E2Eへ暗黙追加する
- repoへ残すE2E実装責務を`test-execution`へ取り込む
- 既存`e2e-test-execution`のrunner内部契約を`test-execution`へ複製する
- 一般TC結果報告を`e2e-test-reporting`へ移す
- 結果不明な副作用を状態確認なしに再試行する
- 外部TCへ正式TC IDを創作する
- dataset / Markdown validatorだけでbrowser操作・画像判断を検証済みと表現する
- 新しい画像差分framework、browser automation framework、run registryを追加する

## 11. 完了条件

- 正規Skillが16件になっている
- `test-target-inspection`が生きた実対象へ到達し、今回範囲のUI情報・ふるまいを収集できる
- 既存資料がある場合、今回対象範囲を実対象と照合し、変更なしを含めcurrentnessを更新できる
- 実対象を確認していない行をcurrentとして更新しない
- DOM / accessibility tree等では不足する視覚情報を画像で確認・記録できる
- POM等を必須化せず、任意参照として扱える
- テスト対象資料を仕様Authorityとして扱わない
- 永続更新の競合上書きを避け、安全に保存できる
- `test-execution`が固定TC集合を実行前にGiven / When / Then構造のYAMLへ整理し、元TCの意味を変えず曖昧さを顕在化できる
- 実行または合否判定に影響する`unresolved`が残るTCを推測で実行せず`未実行`として報告できる
- `test-execution`がAI自身による実対象操作を基本とする
- Playwright MCP等の対話操作でTCを手順どおり実行できる
- 必要時にPlaywright CLI / 今回run用の一時コードを使用できる
- 今回run用一時コードとrepoへ残すE2E資産を区別できる
- DOM / accessibility tree等と画像を確認対象に応じて使い分けられる
- TC結果が`PASS / FAIL / 未実行 / 判定不能`へ漏れなく閉じる
- TC外追加観測を元TC結果と混同しない
- 副作用、後処理、cleanup、証跡の安全境界を守る
- `test-execution`自身が人間向けのTC実行結果報告まで完成させる
- 既存E2E Skillの責務を維持する
- trigger / semantic / deterministic基準が実装時の正規契約と一致する
- 新規2 Skillと隣接Skillの双方向発火境界を検証できる
- 既存14 Skill回帰、`skills-ref validate`、repository eval、workflow routing testsがPASSする
- README、EVALS、ASSERTIONS、CIが実装と一致する
- 利用できないruntime経路を未検証として明示し、repo内評価だけで実動作までPASS扱いしない

