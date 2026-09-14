## 検証

実装時はリポジトリ既存の検証手順を正本とし、少なくとも次を確認します。

- 全`skills/*/SKILL.md`が現在pinしているAgent Skills仕様検証を通る
- `Validate Agent Skills`相当の構造検証が14 Skillで通る
- trigger train / validation件数とpositive / negative比率が契約どおり
- deterministic output evalが全Skillで通る
- semantic dataset / rubric構造検証が通る
- 既存9 Skillの回帰が維持される
- trigger datasetの件数・positive / negative比率・14 Skill / 280 query・構造がrepo内CIで通る。実Agentクライアントで発火評価を実施できる場合は新規5 Skillの発火境界 / trigger_rateも確認し、利用できない場合は未実施と記録してdataset検証だけで発火PASSとしない
- `qa-workflow`の開始、省略、再利用、ブロック、再開、修正routingがE2E後段でも成立する
- 同一Skillの複数対象状態がvalidatorで正しく扱われ、複数用途Skillの実際の状態行では`対象 / 実行範囲`空欄を拒否し、単一用途Skillでは空欄を許容できる
- implementationの既存verify / test validation等を名称だけで安全と判断せず、実行内容を確認してexecutionの安全契約を迂回しない
- implementationの静的・軽量検証失敗を成功扱いしない
- execution直接開始時も実際のpackage script / task / wrapper / pre-post処理を必要な範囲で確認し、安全確認を避けるために実行入口を勝手に置換しない
- executionでautomatic fixture / worker-scoped automatic fixtureの副作用と実行回数を必要な範囲で確認できる
- executionで論理的な要求primary対象とresolved primary TestCaseを区別し、各logical primaryが1件以上のresolved primary TestCaseへ解決されるか解決不能理由を持ち、各resolved primary TestCaseにも結果または未実行理由が存在する
- 異常のない実行で不要なresult-analysisを必須化しない
- 異常時にresult-analysisへroutingされる
- TCなしの明示E2E対象または更新対象の既存E2E実装参照を、inspection相当情報がない状態から`qa-workflow → inspection → implementation`へ渡せる。対象選定要求がなければ`test-analysis`、TC作成だけを目的とする`test-case-design`を必須にせず、TCを創作しない
- TCなしの明示E2E対象または既存E2E更新をinspectionからimplementation / E2E testware reviewへ渡す場合もTCを創作せず、既存E2E結果を含めresult-analysis / reportingまで追跡できる
- cleanup未確認がresult-analysis / reportingで欠落せず、安全な完了条件と整合する
- reportingで論理的な要求primary対象数とresolved primary TestCase数を区別し、未実行数 / 理由もlogical primary単位とresolved primary TestCase単位を分け、retry attemptをresolved件数へ混ぜない
- `question-analysis`回答後に正しい再開Skillへroutingでき、再開Skillが複数用途Skillなら`再開対象 / 実行範囲`が必須で正規値と一致し、質問一覧とブロック中範囲の再開先が食い違わない
- `test-analysis`のE2E対象選定成果物欠落、`adversarial-review`のE2E実装参照不一致、`coverage-analysis`のE2E実装 → 実行結果追跡欠落を決定論的評価で検出できる
- machine-readable resultの取得元が提供しないraw値を推測補完せず、確認不能 / 導出値として区別できる
- result-analysisが追加実行を必要と判断しても直接実行せず、executionへ戻して安全契約を適用できる
- README、EVALS、workflow、test内に古い9 Skill / 180件前提が残っていない
- `git diff --check`相当で不要な空白差分がない

## 実装時に避けること

- 外部記事の固有構成をそのままコピーしない
- 特定プロダクト向け判断基準を汎用QA Skillへ埋め込まない
- Playwright固有情報を既存汎用Skillへ大量に混ぜない
- 特定ブラウザ操作ツールを必須化しない
- Playwright設定やPage Object構造を一律強制しない
- E2E実行のためだけに対象プロダクトCI責務を追加しない
- 実装前調査を省略してlocator / helper / fixtureを推測しない
- 実装完了前のlint / typecheck / discoveryを`adversarial-review`へ丸投げしない
- executionの安全確認をinspection成果物の存在だけに依存しない
- project dependencies / setup / teardownやautomatic fixtureを無視して「指定testだけ実行」と判断しない
- repo既存の実行入口に含まれる前後処理を確認せず、Playwright CLI直呼びへ勝手に置き換えない
- FAILを自動でプロダクト不具合確定しない
- プロダクトFAILをテストコード変更でPASSへ変えない
- 1回のretry成功で初回FAILを消さない
- cleanup失敗または未確認を無視して再実行しない
- `e2e-test-result-analysis`からPlaywrightを直接再実行してexecutionの安全確認を迂回しない
- reporter / APIが提供しないPlaywright raw値を他情報から推測してraw fieldとして記録しない
- logical primaryが存在するのにresolved primary TestCaseが0件・理由なしの状態を完全実行扱いしない
- 複数用途Skillの状態行や`question-analysis`再開先で`対象 / 実行範囲`を空欄のまま出力し、後続処理へ用途の再解釈を委ねない
- reportingの「実行対象件数」「未実行件数」を単位不明のまま出力せず、logical primary / resolved primary TestCaseを区別する
- terminal表示だけを実行事実の唯一の正本にしない
- trace / storageState等を安全確認なしに共有・commitしない
- 実行結果から自動的にナレッジやSkill判断基準を書き換えない
- READMEへ工程固有の詳細ロジックを複製しない
- 新しいSkillを増やすことで既存Skillの責務を重複させない
- 将来用途だけを理由にadapter、runner、reporter、workflow frameworkを新設しない

## 参考にする一次資料

実装時は対象リポジトリの既存実装と現在pinしているAgent Skills仕様を優先し、外部情報は一次資料を正本として確認します。

- Agent Skills Specification / skill creation guidance
- ISTQB CTFL v4.0.1
- Playwright Best Practices
- Playwright Locators
- Playwright Isolation / Authentication
- Playwright Projects
- Playwright Global setup / teardown
- Playwright Parallelism
- Playwright Retries
- Playwright CLI / test discovery
- Playwright TestCase / TestResult
- Playwright Reporters
- Playwright Trace Viewer
- Playwright webServer / configuration

外部記事は補助的な事例としてのみ扱い、CI並列化等の今回対象外の内容をPlan根拠へ持ち込みません。

## 完了条件

本変更の実装完了条件は次です。

- 新規5 Skillが追加され、各責務が重複せず説明できる
- Playwright固有責務が新規E2E Skill側へ閉じている
- `qa-workflow`がコード実装・実行・分析ロジックを持たず、要求に応じて14 Skillをルーティングできる
- E2Eを要求しない既存利用経路を維持できる
- ユーザー指定TCからE2E実装へ進む場合に不要なE2E価値再判断を要求しない
- E2E対象未指定時は利用可能な既存テスト分析結果とTCを基に具体対象を確定できる。TCなしの明示E2E実装依頼または既存E2E更新依頼でinspection相当情報がない場合も、`qa-workflow → inspection → implementation`へ進み、対象選定要求がなければ`test-analysis`、TC作成だけを目的とする`test-case-design`を必須にせず、TCを創作しない
- 実装前にrepoと必要な実対象を確認し、inspectionの確認元・鮮度を判定できる
- implementationがbranch / working tree競合を確認できる
- implementationがlint / typecheck / test discovery等の適用可能な検証を完了条件として扱い、既存verify / test validation等を名称だけで安全と判断せず実行内容を確認する
- E2E実装が独立レビューを通せ、TCありではTC → E2E追跡確認、TCなしでは明示E2E対象 / 確認済み期待挙動との意味一致を確認できる。`adversarial-review`ではQA IDとは別にE2E実装参照を決定論的に照合できる
- 既存E2E実行だけならexecutionから直接開始できる
- executionが直接開始時でも、実際の実行入口とpackage script / task / wrapper / pre-post処理、project dependencies、setup / teardown、automatic fixture、URL、副作用、parallel / retry、test本体から到達する安全判断上必要な経路と、対象testへ最終的に適用される実効設定を確認できる
- runner管理のsetup / cleanupとrun外でexecutionが明示実行する処理を区別し、`webServer`や`globalSetup`が返すteardown callbackも含めて同じ処理を二重実行しない
- executionが必要なrun外準備だけ確認済み方法で実施し、runner管理分を含むcleanup結果を確認できる
- executionが構造化されたPlaywright結果を取得し、利用した情報源が直接提供するrun全体status / TestCase / TestResult等のraw factと、process exit code / 導出値を区別する。取得元が提供しないraw値を推測せず、必要値を取得できない場合は確認不能 / 構造化結果不完全として扱える
- 構造化resultが今回runで生成・更新されたことを確認し、古いartifactを今回結果として利用しない
- 要求されたprimary testとdependency / teardown testを区別し、各論理的な要求primary対象が1件以上のresolved primary TestCaseまたは解決不能 / 未実行理由へ閉じ、解決された各resolved primary TestCaseにも結果または未実行理由が存在する
- Playwright実行前後のworking tree差分を確認し、snapshot / source等への想定外のrepo内変更を隠さない
- custom reporter / output先を含む実行経路の外部I/O・削除・上書き影響を安全確認できる
- 高リスク副作用の最大実行回数を合理的に確定できない場合は推測せず該当範囲をブロックできる
- cleanup成功 / 失敗 / 未確認と残存副作用を保持でき、必要なcleanupが未確認のまま安全な完了や自動再実行へ進まない
- trace / storageState / report等の機密情報を安全に扱う契約がある
- 正常の判断はraw `failed`ではなく`outcome` / `expectedStatus` / run全体結果等で行える
- 異常のない実行かつ分析要求なしならresult-analysisを省略できる
- 「実行結果だけ」の依頼では原因分析を勝手に追加せず、それ以外の分析対象異常やcleanup未確認を`e2e-test-result-analysis`へ渡せる
- FAILとプロダクト不具合を区別できる
- 分析結果から最も早い責任工程へ戻し、`question-analysis`で不明点を解消した場合も正しい再開Skillへ戻せる。再開Skillが複数用途Skillなら`再開対象 / 実行範囲`を必須で保持する。追加実行はresult-analysis自身が行わず`e2e-test-execution`へ委譲し、必要範囲だけ再検証・再実行できる
- ワークフロー完了と全E2E PASSを区別できる
- `Skill + 対象 / 実行範囲`で同一Skillの複数利用を状態管理でき、複数用途Skillでは実際の状態行に正規対象値を常に必須とし、空欄・非正規値をvalidatorで拒否できる。単一用途Skillでは対象空欄を許容できる
- `WF-D006` / `WF-D007`は必要なfixtureだけtarget-awareとして実出力の開始 / 最終対象を比較し、`WF-D008`はSkill単位を維持、`WF-D012` / `WF-D014`は対象別に検証できる
- 既存QA IDグラフをE2E参照のためだけに拡張せず、TCありの`TC → E2E実装`範囲では`TC ID | 扱い | E2E実装参照 | 根拠 / 備考`の対応関係として決定論的に検証できる。`E2E実装 → 実行結果`を部分分析する場合もE2E実装参照からresolved primary TestCase / 実行結果と結果 / 未実行理由へ辿れる
- TCありでは`TC → E2E実装 → 実行結果 → 分析 → 報告`、TCなしでは`E2E実装参照 → 実行結果 → 分析 → 報告`を最低限の参照で辿れ、TCなし経路のためにTC / TC IDを生成しない
- reportingで論理的な要求primary対象数、resolved primary TestCase数、実際に開始したresolved primary TestCase数を区別し、未実行もlogical primary / resolved primary TestCaseの単位を明示して報告できる。retry attempt数をresolved件数へ混ぜない
- ナレッジ蓄積とSkill判断基準更新が本ワークフローの必須工程へ混入していない
- 実Agent統合harnessを新設せず、既存評価層の範囲で14 Skill化を検証できる
- 14 Skillの評価構造とリポジトリ検証が整合し、repo内trigger dataset検証と実Agent上の実発火評価を区別できる
- READMEとEVALSの説明が実装と一致する
