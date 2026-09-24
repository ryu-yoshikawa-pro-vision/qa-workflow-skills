# テスト対象資料管理・テスト実行Skill追加Plan

## 1. 評価方針

新規2 Skill追加後も現行の評価層を維持します。

1. Agent Skills仕様検証
2. 発火評価データセット検証
3. 決定論的出力評価
4. 意味評価
5. `qa-workflow` routing / 状態評価
6. 既存14 Skillの回帰

repo内評価だけで実Agent上の動作をPASS扱いしません。browser操作、画像判断、Playwright MCP、独立一時Playwrightコード、永続更新競合等は実Agent / 実対象を利用できる場合のsmokeで確認します。

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
- 必要な画面 / 領域 / 状態のPlaywright ARIA snapshotを機械可読な観測証跡として安全に保存し、前回証跡との差分を変更候補の確認に利用する

negativeには最低限、次を含めます。

- POM / Page Objectコード実装 → `e2e-test-implementation`
- Playwright E2E実装可否のinspection → `e2e-test-inspection`
- 詳細TC作成 → `test-case-design`
- TCを実行して結果報告 → `test-execution`
- 仕様Authority整理 → `spec-analysis`
- ARIA snapshotを期待値assertionとしてrepoへ実装 / 更新 → `e2e-test-inspection` / `e2e-test-implementation`

### 3.2 決定論的validator

保存済みMarkdownから機械判定できる契約だけを検査します。

- 正規セクション / 必須テーブルが存在する
- 対象キー / 要素キー / 状態キーが一意で参照整合している。ただし`今回の更新`の`削除確認`行にある削除対象キーはcurrentな本体テーブルの実在キー参照チェック対象外とする
- 新規成果物では文書ローカルの正規キー形式を使用する
- 今回対象範囲の確認状態が`確認済み / 未確認 / 確認不能`の正規値へ閉じている
- 既存成果物更新時だけ`今回の更新`が存在し、更新区分が`変更なし / 更新 / 追加 / 削除確認`の正規値である
- 今回確認した行だけ確認日時 / version / build / 確認条件等が今回値へ更新される
- `操作・ふるまい`、視覚情報、データ・権限依存を含む鮮度管理対象が確認条件 / version / build / 確認日時へ追跡できる
- 未確認行の鮮度を成果物全体の更新日時だけで上げない
- 実対象で確認していない範囲をrepo情報だけでcurrentと表現しない
- UI要素 / 状態 / 操作・ふるまいがcurrentな実在キーへ追跡できる。`削除確認`行だけは削除後のcurrent本体テーブルに対象キーが存在しなくても正当とする
- 視覚情報表は必要時だけ存在でき、存在する場合は対象キーまたは要素 / 状態キーへ追跡できる
- 構造証跡表は任意であり、存在する場合は対象キーを必須とし、状態固有snapshotだけ状態キーを要求する。今回 / 前回の証跡参照がmutableなpathなら対応するrevision / SHA / content identityを要求し、過去内容を再取得できないlatest pathだけの履歴参照を許容しない。証跡参照・差分概要・証跡保存制約を本体の確認状態や更新区分と混同しない。raw `.aria.yml`の内容自体をdeterministic validatorの必須入力にはしない
- 既存テスト実装対応表は任意であり、存在する場合だけ参照整合を検査する
- `削除確認`行に確認条件 / version / build / 確認日時が存在し、比較条件へ追跡できる。version / buildは旧値との一致を要求せず、取得できない場合は`取得不能`を許容する。評価fixtureで更新前成果物を与える場合は、削除対象キーが更新前成果物に存在したことも確認する
- 永続保存を要求した場合は`保存結果`が存在し、更新元revision、更新方式、保存状態、保存後revision、競合・制約の記録が矛盾しない
- 副作用がある場合はscope単位の`1回の定義`が空でなく、最大回数、準備回数、観測操作回数、cleanup回数、累計実施回数が整合し、累計実施回数が工程別回数の合計かつ最大回数以下である
- cleanup結果が`成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 / 一部失敗`の正規値で、残存状態と矛盾しない
- secret / cookie / token / storageState等の実値を出力しない。secret漏えい回帰fixtureでは既知のdummy secret文字列を入力へ含め、最終Markdownに同じ実値が出現しないことを確認する

deterministic validatorだけで、実際に実対象を操作したこと、画像を正しく認識したこと、条件付き更新が実競合を防いだことまでは証明しません。

### 3.3 意味評価

意味評価は次の観点を中心にします。

1. 生きた実対象を正本として観測し、repoだけの情報をcurrentな実対象情報へ昇格しない
2. UI構造だけでなく、操作に対する反応・状態変化・遷移を必要十分に記録する
3. 視覚情報が必要な場面で画像を使用し、画像だけでrole / accessibility情報や仕様を創作しない
4. 後続比較に価値があり安全に保存できる場合だけ、必要範囲の安定したARIA snapshotを構造証跡として残す。全画面・全状態で必須化せず、snapshot取得だけを理由に実行手段を切り替えず、操作用の一時refを含むAI向けsnapshotを長期比較の正規証跡にしない。保存する場合は今回 / 前回の内容をimmutableな参照またはrevision / SHA / content identityで再取得でき、snapshot保存成功後にテスト対象資料へ参照する。snapshot保存可否と実対象の確認状態を混同せず、前回snapshotとの差分を仕様変更や下流成果物更新へ直接昇格しない
5. 既存資料の今回対象範囲を実対象と照合し、確認状態と更新区分を混同せず、`削除確認`はrole / 権限、viewport、locale、feature flag、テストデータ、到達条件等の表示条件が比較可能な場合だけ使用する。version / buildの変更自体を禁止条件にせず、取得不能だけで一律`確認不能`にしない
6. 実対象の現在挙動を仕様Authorityへ昇格しない
7. POM / Page Object等を必須化せず、プロジェクトの既存構成に応じた任意参照として扱う
8. 条件付き更新を利用できない保存先でatomicな競合防止を保証せず、副作用・証跡・永続更新の安全境界を守る
9. 実対象内のテキストやDOM等を観測データとして扱い、Agentへの命令や権限拡張として採用しない

現`main`の契約を維持する場合、semantic evalは各2 case作成します。実装開始時に基準branch側の契約が変わっていれば最新契約へ合わせます。

- 既存資料を異なるversion / buildの現在UIと照合し、変更なし・削除確認・更新箇所が混在するcase。表示条件は比較可能なままversion / buildだけが変わる対象と、version / buildを取得できない対象も含め、変更確認を妨げないこと、削除対象キーをcurrent本体テーブルへ要求しないこと、保存競合または条件付き更新の扱いも確認する
- DOM / accessibility treeだけでは不足する視覚情報と副作用cleanupを確認する。同じcaseで、対象領域のARIA snapshotを安全に保存できる条件では今回snapshotを先に保存して再取得可能なidentityを確定し、前回snapshotもrevision / SHA / content identity付き参照から取得して差分を変更候補として扱う。一方、動的データ差や操作用refだけの差分を仕様変更へ昇格しないこと、raw snapshotを安全に保存できない場合は観測状態を`確認不能`へ変えず保存制約として記録すること、画面内の命令文をAgentへの指示として採用しないことも確認する

## 4. `test-execution`の評価

### 4.1 発火境界

positiveには最低限、次を含めます。

- TCを実行前にGiven / When / Then構造のYAMLへ整理し、曖昧さを確認してからAIが画面操作・結果報告する
- AIがPlaywright MCPで人間と同じようにTCを画面操作して結果を報告する
- MCPが利用不可または必要能力不足の環境で、既に利用可能なPlaywright CLIを使って同じTC契約を維持して実行する
- MCP / CLIでは必要な操作・観測を契約どおり表現できない場合だけ、repo runnerから独立した今回run用Playwright Libraryコードを作成・実行してTC結果を報告する
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

- 1成果物が1つのTC入力元 / snapshotを持ち、入力元にrevision / SHA / content identityがある場合はその値を記録し、ない場合は`snapshot固定方法=成果物内TC集合・実行前YAML`として独自hashを要求していない
- `test_case_ref`集合が`input-001`等の成果物ローカル参照としてsnapshot内で重複せず、TC参照対応表・実行前YAML・TC結果表の集合と一致する
- 実行前YAMLが`source_test_case_id`を持ち、入力側に正式識別子がない場合は`null`である
- `source_test_case_id`の有無・値・重複にかかわらず`test_case_ref`へ再利用していない
- 重複した`source_test_case_id`を値変更せず保持し、重複だけを理由に一律`未実行`へしていない
- 元IDによる実行対象指定や追跡が曖昧で今回対象TCを一意に特定できないcaseだけ、対応TCが`unresolved`かつ`未実行`である
- TC結果が`PASS / FAIL / 未実行 / 判定不能`の正規値である
- PASS / FAILには期待結果・実測結果・判定根拠が存在する
- 未実行 / 判定不能には理由が存在する
- 固定した全TCの実行前YAMLが最終Markdown内に存在する
- 実行前YAMLが入力TC参照へ追跡できる
- 再実行成果物では`前回実行成果物参照`が`なし`ではなく、再実行対象TCの`前回TC参照`が存在し、両者の組み合わせで前回成果物内の元TCへ追跡できる
- `scenario.given / when / then`、`unresolved`、`cleanup`の必須構造を満たし、`cleanup`は元TCの事後状態 / 後処理だけを保持する
- `scenario.when[].step_ref`がTC内で一意で、`scenario.then[].after_step_ref`が存在する`step_ref`へ参照整合し、多段TCの中間期待結果を対応する操作へ追跡できる
- `unresolved`が空でないTCを操作済み / PASS / FAILとして扱っていない
- `実行開始`が`未開始 / 開始済み`の正規値で、`未実行`は`未開始`、`PASS / FAIL / 判定不能`は`開始済み`として出力上整合する
- run固定条件とTC実行条件が分離され、TCが明示的に要求するrole / viewport / locale / feature flag / テストデータの差異だけを理由に別成果物扱いしていない
- 使用した実行手段が記録される
- 手順・観測結果が判定根拠へ追跡できる
- 画像を使用した場合は視覚確認行がTC / 観測点へ追跡できる
- 画像を使用していないTCへ画像参照を必須化しない
- TC外の追加観測をTC結果と混同しない
- 副作用scope単位の`1回の定義`が空でなく、最大回数、準備回数、TC操作回数、TC事後処理回数、実行時cleanup回数、累計実施回数が正本表で整合し、累計実施回数が工程別回数の合計かつ最大回数以下で、TCごとに上限をリセットしていない
- cleanup結果が`成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 / 一部失敗`の正規値である
- TC事後状態 / 後処理と実行時cleanupを混同しない
- 集計がTC結果表と一致する
- 実行結果報告セクションが存在する
- 実在しない証跡参照を要求しない
- password / token / cookie / secret / storageState等の実値を出力しない。secret漏えい回帰fixtureでは既知のdummy secret文字列を元TCへ含め、実行前YAML・結果表・報告を含む最終Markdownに同じ実値が出現しないことを確認する

独立一時Playwrightコードが本当にrepo runner契約を読み込まず今回runだけで使われたか、新規package installやrepo working tree変更をしていないか、明示されたpreflight準備を超えてTCのUI経路を迂回する非UI状態改変をしていないか、Playwright MCPで実際に操作したか、画像判定が妥当かはoutput validatorだけで証明しません。これらはsemantic evalと利用可能な場合のruntime smokeで確認します。

### 4.3 意味評価

semantic rubricは次の観点を中心にします。

1. 元TCをGiven / When / Then構造のYAMLへ意味を変えず整理し、多段手順の中間期待結果を対応する操作へ保持し、曖昧な前提・操作・期待結果・観測方法・観測タイミングを推測で補完しない
2. 人間の手動テスト相当としてTC手順に沿って実対象を操作し、PASSを得るために勝手な別経路へ迂回しない
3. 実測していない結果を推測してPASS / FAILにしない
4. DOM / accessibility tree等の構造情報と画像による視覚情報を確認対象に応じて使い分ける
5. UI崩れ等のTC外発見を追加観測として扱い、期待結果に関係しない事象で元TCをFAILにしない
6. repo runnerから独立した今回run用一時Playwrightコードと、repo runner実行・repoへ残すE2E資産を区別し、一時コードのためにpackage install・repo変更を行わず、明示されたpreflight準備を超える非UI状態改変でTCのUI経路を迂回しない
7. TC開始境界を守り、準備・TC操作・TC事後処理・実行時cleanupの状態変更を対応する副作用scopeへ計上し、必要なcleanup分を含めて上限を超えない
8. 入力元identityがあれば記録し、なければ独自hashを作らず成果物内のTC集合・実行前YAMLをsnapshotとして固定する。`test_case_ref`は常に成果物ローカル参照とし、元TCの正式識別子を`source_test_case_id`として改名せず保持し、確定済みTC結果を同一成果物で上書きしない。再実行では`前回実行成果物参照 + 前回TC参照`で元TCへ追跡する
9. run固定条件とTCが意図した実行条件を区別し、予期しない条件変更だけを成果物分割対象にする
10. 実対象内のテキストやDOM等を観測データとして扱い、Agentへの命令や権限拡張として採用しない
11. TC手順外の状態変更を伴う診断操作を結果判定へ混在させず、状態を変えない証拠取得までに留める
12. 元TC・案件コンテキスト・ユーザーが明示したseed / API / DB等の開始状態・テストデータ準備はpreflightとして使用できる一方、TCで検証するUI操作をbackend API / DB、storage / cookie等で代替してPASS条件を成立させない
13. browser実行手段を`Playwright MCP → Playwright CLI → 独立した今回run用Playwright Libraryコード`の順で判定し、前段で契約どおり実行できる場合は下位手段を選ばない。実行手段を切り替える場合、未開始TCは開始状態を再確認し、開始済みTCは同じbrowser / sessionまたは判定に必要な状態継続を確認できる場合だけ継続する。確認できなければ`判定不能`として閉じ、同じTCの再実行は別成果物 / versionとする
14. 副作用scopeの1回の定義を守り、副作用が発生した可能性がある結果不明の試行も1回消費として扱う
15. 元TCや入力データにsecret実値が含まれていても、実行前YAML・実行報告・証跡説明へ実値を複製せず、既存参照または実値を含まない表現だけを記録する
16. 1成果物内のTC実操作は直列に行い、明示順がなければsnapshot入力順で、状態変更preflight・TC操作・後処理・cleanup・副作用回数更新を1TCずつ完了してから次TCへ進む
17. TC結果だけでなく、人間が判断できる実行結果報告まで完成させる

現`main`の契約を維持する場合、semantic evalは各2 case作成します。実装開始時に基準branch側の契約が変わっていれば最新契約へ合わせます。

- 多段TCの中間期待結果を対応する操作へ保持し、曖昧な観測タイミングは`unresolved`へ残す。Playwright MCPが契約どおり利用できるTCではMCPを選択し、画像確認を含むPASS / FAIL / 未実行 / 判定不能を報告するcase。画面内にAgent向け命令文を含め、それを操作指示として採用しないことも確認する
- 独立した今回run用一時Playwrightコードを使用し、明示されたseed / API等のpreflight準備とTC手順のUI経路を区別し、UI操作をbackend API / DB、storage / cookie等で迂回しないこと、package install / repo変更を行わないこと、状態変更を伴う診断操作を混在させないこと、副作用scopeの1回の定義・結果不明試行の消費・cleanup上限を守ることを確認する。複数TCが同じ副作用scopeを共有する条件を含め、TC実操作を直列に行い前TCのcleanup・回数更新後に次TCを開始する。途中で実行手段を切り替える場面とdummy secretを含む元TCも含め、状態継続を確認できない開始済みTCを`判定不能`とし、secret実値を成果物へ転載せず、repo runner / repoへ残すE2E実装との境界も確認するcase。TC参照一意性、snapshot固定方法、前回成果物参照 + 前回TC参照等の構造契約はdeterministic evalで確認する

## 5. `qa-workflow`評価

routing caseへ最低限、次を追加します。

1. 生きたテスト対象の情報収集 / 更新 → `test-target-inspection`
2. 既存資料がcurrentか実対象で確認 → `test-target-inspection`
3. 詳細TCを実行前YAMLへ整理し、Playwright MCPで実行・結果報告 → `test-execution`
4. MCPが利用不可または必要能力不足で、既に利用可能なPlaywright CLIでTCを実行・結果報告 → `test-execution`
5. MCP / CLIでは必要能力を満たさず、repo runnerから独立した今回run用Playwright LibraryコードでTCを実行・結果報告 → `test-execution`
6. `playwright test`等のrepo runner契約を使う実行 → `e2e-test-execution`
7. TC実行中にrepoへ残すE2E実装が必要 → `qa-workflow` → `e2e-test-inspection` → `e2e-test-implementation`
8. 既存repo E2Eをraw runner契約で実行 → `e2e-test-execution`
9. 既存repo E2E異常 → `e2e-test-result-analysis`
10. 既存repo E2EのPlaywright固有詳細報告 → `e2e-test-reporting`
11. TC入力snapshotまたはrun固定条件 / 予期しないTC実行条件の変更 → 旧`test-execution`を理由付きで閉じ、新しい成果物 / versionを開始
12. 元TCが明示するrole / viewport / locale / feature flag / テストデータ等の切替 → 同じ`test-execution`成果物を継続
13. 確定済みTCの再実行 → 前回成果物参照を持つ新しい`test-execution`成果物 / versionを開始し、再実行対象TCごとに前回TC参照も保持
14. 未開始TCで実行手段を切り替え、run固定条件と開始状態を再確認できる → 同じ`test-execution`成果物を継続
15. 開始済みTCで実行手段を切り替え、同じbrowser / sessionまたは判定に必要な状態継続を確認できない → 当該TCを`判定不能`として閉じ、同じTCの再実行は前回成果物参照を持つ新しい`test-execution`成果物 / versionとし、前回TC参照も保持
16. 明示されたseed / API / DB等で開始状態・テストデータをpreflight準備 → `test-execution`で許可。ただしTCで検証するUI操作の代替には使わない

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
- 実行前YAMLの構造検証用にeval環境だけへ`PyYAML==6.0.3`を明示installする
- `test-execution` validatorはMarkdown内のfenced YAMLを抽出し、`yaml.safe_load`でparseして構造・参照整合を検証する
- YAML解析のための正規表現parserや独自YAML parserを追加しない
- PyYAMLはdeterministic eval専用依存とし、Skill runtimeや一時Playwrightコードの依存へ広げない

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
- `Playwright MCP → Playwright CLI → 独立一時Playwright Libraryコード`の実行手段選択
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
- `assets/output-template.md`
- trigger / deterministic / semantic eval
- 実対象currentness確認
- UI構造・ふるまい収集
- DOM / accessibility treeと画像の使い分け
- 必要範囲のPlaywright ARIA snapshotを既存の対象キーへ紐付く任意の構造証跡として保存し、状態固有snapshotだけ状態キーも使用する契約。全画面必須化、snapshot専用registry、実行手段切替、新規installは行わない
- ARIA snapshotはimmutableな参照、またはrevision / SHA / content identity付き参照で過去内容を再取得できるようにし、snapshot保存成功とidentity確認後にテスト対象資料へ参照を記録する契約。新しいtransaction managerは追加しない
- snapshot保存可否を実対象の確認状態と分離し、ARIA snapshot差分を仕様Authorityや下流成果物更新へ直接昇格せず、実対象で意味上の変更を確認して本体成果物へ反映してから既存の変更伝播を使う契約
- 視覚情報テーブル
- 部分更新・変更なし管理
- 条件付き更新 / 再読込比較
- 保存結果 / 競合状態 / `削除確認`条件の記録。version / build差を一律比較不能扱いせず、`削除確認`対象キーをcurrent実在キー検証から除外
- inspection側の副作用scope、1回の定義、準備 / 観測 / cleanup回数、cleanup結果、残存状態の記録
- browser操作能力がない場合の`確認不能` / `ブロック中`
- POM等は任意参照
- 証跡保護

### Step 4: `test-execution`

- `SKILL.md`
- `references/guidance.md`
- `assets/execution-plan-template.yaml`
- `assets/output-template.md`
- trigger / deterministic / semantic eval
- `Playwright MCP → Playwright CLI → 独立した今回run用Playwright Libraryコード → 未実行 / ブロック中`の決定順序
- Playwright CLIやLibrary等を本Skillのために新規installせず、前段の手段で契約どおり実行できる場合は下位手段を選ばない
- repo runnerから独立し、package install・repo変更を行わず、明示されたpreflight準備を超える非UI状態改変でTCのUI経路を迂回しない今回run用一時Playwrightコード
- 人間の手動テスト相当の操作手順
- 多段手順の操作と中間期待結果の対応
- 常に成果物ローカルな`test_case_ref`と元IDの`source_test_case_id`分離、入力元identityまたは成果物内snapshot固定、`前回実行成果物参照 + 前回TC参照`による再実行追跡
- run固定条件とTC実行条件の分離
- DOM / accessibility treeと画像の使い分け
- TC外追加観測と、状態変更を伴う診断操作の禁止
- PASS / FAIL / 未実行 / 判定不能
- secret実値をYAML・報告・証跡説明へ転載せず、既存参照または実値を含まない表現を使用
- 1成果物内のTC実操作を直列化し、明示順なしではsnapshot入力順で次TCへ進む
- 準備・TC操作・TC後処理・実行時cleanupを含むscope単位の副作用上限、1回の定義、結果不明試行の消費
- browser操作能力がない場合の`未実行` / `ブロック中`
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
- 案件コンテキストの認証方法・テストデータ準備方法を新Skillのpreflightから再利用
- `副作用の許可範囲と根拠`を`副作用の許可範囲 / 1回の定義 / 最大回数 / 根拠`を保持できる形へ更新
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
- 安全にARIA snapshotを永続化できる検証環境が利用可能なら、必要範囲のsnapshot取得 → snapshot保存 → revision / SHA / content identity確認 → テスト対象資料への参照記録 → 前回証跡との差分確認 → 意味上の変更有無判定までを最低1 case通す。長期比較に適さない操作用ref付きsnapshotしか取得できない、または安全に保存できない場合は実行手段を切り替えず、Planどおりraw永続証跡を省略して保存制約を記録できることを確認する。利用できない場合は未検証として記録する
- Playwright MCPが利用可能なら第1経路で人間相当の非破壊TCを実行
- MCPを利用できずPlaywright CLIが既に利用可能な検証環境がある場合は、第2経路を最低1 case確認
- 画像確認可能なら現在のPlaywright実行手段から視覚観測を最低1 case確認
- MCP / CLIでは必要能力を満たさず、独立一時コード経路を安全に試せる場合は第3経路を最低1 case確認
- 利用できないruntime経路は未検証として記録する

## 10. 実装時に避けること

- `test-target-inspection`をrepo情報だけでcurrent扱いにする
- `test-target-inspection`で製品全体のfull scanを毎回必須にする
- POM / Page Object生成を`test-target-inspection`の目的にする
- 実対象の現在挙動を仕様Authorityへ昇格する
- 画像だけでrole / accessibility情報 / 仕様を推測する
- すべての観測へ不要なscreenshotを要求する
- 全画面・全状態のARIA snapshot保存を必須にする
- ARIA snapshot取得だけを理由に実行手段を切り替える、またはPlaywright Library / browser等を新規installする
- 操作用の一時refを含むAI向けsnapshotを長期比較の正規証跡として扱う
- ARIA snapshot差分だけで仕様変更を断定し、仕様、TC、E2E実装等を直接自動更新する
- `test-target-inspection`のcurrentness確認のために`toMatchAriaSnapshot()`や`--update-snapshots`を期待値正本として使用する
- 実行前YAMLを元TCの正本や仕様Authorityとして扱う
- YAML化の過程で曖昧な期待結果・前提・操作・中間観測タイミングをAIが独自補完する
- 手順と中間期待結果の対応を失ったまま`when[]` / `then[]`へ分離する
- YAML検証のために正規表現parserや独自YAML parserを実装する
- Gherkin / Cucumber全構文を今回要件のためだけに実装する
- `test-execution`を既存E2E結果の集約・判定だけのSkillにする
- 明示されたpreflight準備ではないbackend API / DB等を使ってTCで検証するUI操作を置き換え、PASS条件を成立させる
- TCのPASSを得るために手順外の別経路へ勝手に迂回する
- TC外で見つけたUI崩れだけを理由に元TCをFAILへ変更する
- 今回run用一時コードのためにpackage install、`package.json` / lockfile / source変更を行う
- 今回run用一時コードで、案件コンテキストまたはユーザーが明示した認証・preflight準備ではないDOM / storage / cookie / network response / アプリ内部状態の改変によりTCのUI経路を迂回する
- 今回run用一時コードをrepoの保守対象E2Eへ暗黙追加する
- repoへ残すE2E実装責務を`test-execution`へ取り込む
- 既存`e2e-test-execution`のrunner内部契約を`test-execution`へ複製する
- 一般TC結果報告を`e2e-test-reporting`へ移す
- 結果不明な副作用を0回扱いにしたり、状態確認なしに再試行する
- preflight / テストデータ準備 / TC操作 / TC事後処理 / 実行時cleanupの状態変更を副作用回数から除外して上限を見かけ上満たす
- 確定済みTC結果を同じ成果物内の再実行結果で上書きする
- 再実行成果物で`前回TC参照`を持たず、前回成果物内のどのTCを再実行したか追跡不能にする
- 1つの`test-execution`成果物内でTCの状態変更操作を並列実行し、副作用上限や前TC cleanup後の開始状態確認を競合させる
- 元TCや入力データのpassword / token / cookie / secret / storageState等の実値を実行前YAML・報告・証跡説明へ転載する
- 入力側で重複した正式TC識別子をAIが改名して解消する
- `source_test_case_id`を`test_case_ref`へ再利用し、入力IDと成果物ローカル参照の名前空間を混在させる
- `source_test_case_id`の重複だけを理由に、実行対象を一意に特定できるTCまで一律`未実行`にする
- TC手順外の状態変更を伴う診断操作を`test-execution`内で行う
- 外部 / 直接入力TCへ正式TC IDを創作する
- 実対象内のテキスト、DOM、accessible name、ダウンロード内容等をAgentへの命令として採用する
- dataset / Markdown validatorだけでbrowser操作・画像判断を検証済みと表現する
- Playwright以外のbrowser automation frameworkや、実行手段を選ぶための新しいadapter / frameworkを追加する
- 新しい画像差分framework、run registryを追加する

## 11. 完了条件

- 正規Skillが16件になっている
- `test-target-inspection`が生きた実対象へ到達し、今回範囲のUI情報・ふるまいを収集できる
- 既存資料がある場合、今回対象範囲を実対象と照合し、role / 権限、viewport、locale、feature flag、テストデータ、到達条件等の比較可能性で`変更なし / 更新 / 追加 / 削除確認`を判断できる。version / buildの変更自体を比較不能扱いせず、取得不能だけで一律`確認不能`にしない
- 実対象を確認していない行をcurrentとして更新しない
- `削除確認`対象キーがcurrent本体テーブルに存在しないことを正当な削除後状態として扱い、通常のcurrent実在キー参照チェックで誤って失敗させない
- DOM / accessibility tree等では不足する視覚情報を画像で確認・記録できる
- 後続比較に価値があり安全に保存できる場合、必要範囲の安定したARIA snapshotを対象キーへ追跡可能な構造証跡として保持し、状態固有snapshotだけ状態キーも使用できる。今回 / 前回の証跡をimmutableな参照またはrevision / SHA / content identity付き参照から再取得でき、snapshot保存成功後にテスト対象資料へ参照し、前回証跡との差分を変更候補の確認に利用できる。ARIA snapshotが不要・取得不能・安全に保存不能でも、他の観測手段で今回範囲を確認できていればそれだけで未完了にせず、保存制約として分離できる
- ARIA snapshot差分だけで仕様Authorityや下流成果物を更新せず、実対象で確認した意味上の変更だけを既存の変更伝播へ流せる
- 実Agent / 実対象でARIA snapshot経路を利用できる場合は取得・保存・identity確認・前回比較・意味上の変更判定までのruntime smokeを通し、利用できない場合は未検証として明示できる
- POM等を必須化せず、任意参照として扱える
- テスト対象資料を仕様Authorityとして扱わない
- 条件付き更新を利用できる保存先では競合上書きを防ぎ、利用できない共有保存先ではatomicな競合防止を保証せず自動上書きしない
- `test-execution`が入力元identityを利用できる場合は記録し、ない場合は独自hashを作らず成果物内TC集合・実行前YAMLをsnapshotとして固定し、多段TCの操作と中間期待結果の対応を失わず、元TCの意味を変えず曖昧さを顕在化できる
- 実行または合否判定に影響する`unresolved`が残るTCを推測で実行せず`未実行`として報告できる
- `test-execution`がAI自身による実対象操作を基本とする
- `Playwright MCP → Playwright CLI → 独立した今回run用Playwright Libraryコード → 未実行 / ブロック中`の順で実行手段を決定し、前段で契約どおり実施できる場合は下位手段へ切り替えない
- Playwright CLIやLibrary等を本Skillのために新規installせず、MCP / CLIでは必要な操作・観測を契約どおり表現できない場合だけ独立一時コードを使用し、package install・repo変更やUI経路の迂回を行わない
- 独立一時コードとrepo runner実行・repoへ残すE2E資産を区別できる
- DOM / accessibility tree等と画像を確認対象に応じて使い分けられる
- `test_case_ref`が常に`input-001`等の成果物ローカル参照としてsnapshot内で一意で、入力側の正式識別子を`source_test_case_id`として値を変えず保持できる。元ID重複だけでは一律`未実行`にせず、元IDによる対象指定・追跡が曖昧で一意に特定できない場合だけ`unresolved / 未実行`として閉じられる
- TC結果が`PASS / FAIL / 未実行 / 判定不能`へ漏れなく閉じ、`実行開始`と整合する
- 確定済みTCの再実行を別成果物 / versionとして扱い、`前回実行成果物参照 + 前回TC参照`で前回成果物内の元TCへ追跡できる
- run固定条件とTC実行条件を区別し、元TCが要求する条件切替を誤って成果物分割しない
- TC外追加観測を元TC結果と混同せず、状態変更を伴う診断操作を行わない
- 準備・観測 / TC操作・TC事後処理・cleanupの状態変更を副作用scopeへ漏れなく計上し、scopeごとの1回の定義を共有し、結果不明試行も消費として数え、必要なcleanup分を含めて最大回数を超えず、cleanup結果と残存状態を既存値域で閉じられる
- `test-execution`のTC実操作を直列に行い、明示順がなければsnapshot入力順で前TCのcleanup・副作用回数更新後に次TCを開始できる
- 元TCに含まれるsecret実値を実行前YAML・実行報告・証跡説明へ転載せず、dummy secret回帰で漏えいを検出できる
- `test-execution`自身が人間向けのTC実行結果報告まで完成させる
- 既存E2E Skillの責務を維持する
- trigger / semantic / deterministic基準が実装時の正規契約と一致する
- 新規2 Skillと隣接Skillの双方向発火境界を検証できる
- 既存14 Skill回帰、`skills-ref validate`、repository eval、workflow routing testsがPASSする
- README、EVALS、ASSERTIONS、CIが実装と一致する
- `PyYAML==6.0.3`をeval専用依存として使用し、実行前YAMLを`yaml.safe_load`で構造検証できる
- 利用できないruntime経路を未検証として明示し、repo内評価だけで実動作までPASS扱いしない

