## README更新

READMEは詳細ロジックの正本にせず、次を更新します。

- リポジトリの目的を、要求された場合のE2E実装・ローカル実行・分析・報告まで含む表現へ変更
- Skill構成を14 Skillへ更新
- 汎用QA SkillとPlaywright固有E2E Skillの責務境界を簡潔に説明
- 全体フロー図を条件分岐型へ更新
- 「全14 Skillを常に通すわけではない」ことを明記
- E2E実装前の実対象調査を明記
- implementation自身が静的・軽量検証を行うことを明記
- executionが安全確認、状態準備、実行、結果収集、cleanupを担当することを明記
- 正常runではresult-analysisが不要な場合があることを明記
- ワークフロー完了と全テストPASSを分離
- CIでの対象プロダクトE2Eは今回対象外であることを明記
- 特定ブラウザ操作方式を固定しないことを明記
- ナレッジ蓄積・Skill判断基準更新は別責務であることを簡潔に記載

READMEへ各Skillの細かなPlaywright判断ロジックを複製しません。

## 実装順序

### 1. 共通契約・状態・用語を先に修正する

対象:

- `README.md`
- `EVALS.md`
- `skills/qa-workflow/SKILL.md`
- `skills/qa-workflow/references/guidance.md`
- `skills/qa-workflow/assets/workflow-state-template.md`
- `skills/qa-workflow/assets/project-context-template.md`
- `skills/qa-workflow/evals/deterministic/validator.py`
- `skills/question-analysis/SKILL.md`
- `skills/question-analysis/references/guidance.md`
- `skills/question-analysis/assets/output-template.md`
- 必要な`skills/question-analysis/evals/`
- 関連fixture / 回帰テスト / assertion docs
- `skills/coverage-analysis/references/guidance.md`

実施内容:

- 14 Skill構成と責務境界を確定
- 条件分岐型の代表経路へ更新
- `Skill + 対象 / 実行範囲`状態へ変更し、`test-analysis` / `coverage-analysis` / `adversarial-review`の正規対象値を共通契約どおりに固定
- `WF-D006` / `WF-D007`は対象識別が必要なfixtureだけtarget-aware、`WF-D008`はSkill利用有無の既存意味を維持、`WF-D012` / `WF-D014`は`(Skill, 対象)`単位で検証
- `expected_start_target` / `expected_final_target` / `expected_scoped_skill_states`等、対象別期待値を表現できるfixture契約を追加し、必要な場合は実出力の`開始対象 / 実行範囲` / `最終対象 / 実行範囲`と比較して、対象を失って誤PASSする回帰を検出
- 複数用途Skillの`対象 / 実行範囲`は実際の状態行で常に定義済み正規値を必須とし、空欄や非正規値を決定論的に検出。単一用途Skillでは空欄を許容
- 指定URL、ブロック、再開、完了条件を定義
- `question-analysis`回答後の再開先を既存設計Skillだけに固定せず、最も早い責任工程がE2E SkillならそのE2E Skillへ戻せるようoutput template / guidance / 評価を更新。再開Skillが複数用途Skillなら`再開対象 / 実行範囲`も常に正規値で必須とし、fixtureで一意に期待できる再開Skill / 対象との一致と、質問一覧 / ブロック中範囲の再開先整合を決定論的に検証
- E2E用語衝突を解消

### 2. `test-analysis`を必要時だけ最小拡張する

対象:

- `skills/test-analysis/SKILL.md`
- 必要な`references/` / `assets/` / `evals/`

実施内容:

- ユーザーがE2E対象の選定自体を要求し、再利用可能な選定結果がない場合だけ、高位の自動化目的・候補範囲・技術非依存の判断基準を出力できるようにする
- Playwright固有の実装可否、locator、fixture、実装コスト等の技術判断は持たせない
- 自動化維持コストをプロダクトリスク評価へ混ぜない
- ユーザーがTCを直接指定している場合や、有効なE2E対象決定成果物がある場合は`test-analysis`再実行を要求しない
- inspectionで得た新事実により自動化価値そのものを再判断する必要が生じた場合だけ、該当範囲を`test-analysis`へ戻す
- `対象 / 実行範囲 = E2E対象選定`では、自動化目的・候補範囲・技術非依存の判断基準 / 根拠を必須成果物とし、決定論的評価で欠落を検出できるようにする。通常の`テスト分析`ではこの追加成果物を必須にしない

E2E対象選定の価値判断を`e2e-test-inspection`だけへ寄せず、上記条件では`test-analysis`を明示的に利用します。

### 3. `e2e-test-inspection`を追加する

対象:

- `skills/e2e-test-inspection/**`

実施内容:

- E2E対象決定ルール。詳細TC、ユーザーが明示したE2E対象、更新対象となる既存E2E実装参照のいずれもinspection入力として扱い、TCなし経路のためだけにTC / TC IDを生成しない
- inspection相当情報がないTCなしの明示E2E実装依頼または既存E2E更新依頼は、`qa-workflow → e2e-test-inspection → e2e-test-implementation`で開始し、E2E対象選定自体を要求されていなければ`test-analysis`、TC作成だけを目的とする`test-case-design`を必須にしない
- repo / Playwright構成確認
- 必要時の実UI確認
- 既存E2E確認
- 認証、データ、状態準備方法
- URL / origin / 外部依存
- 副作用と許可
- 証跡・認証状態保護
- inspectionの確認元・revision・鮮度
- 実装可能性 / ブロック
- Playwright未導入時の最小導入可否判定

### 4. `e2e-test-implementation`を追加する

対象:

- `skills/e2e-test-implementation/**`

実施内容:

- branch / HEAD / working tree競合確認
- inspection成果物または同等確認情報の利用
- 詳細TC、ユーザーが明示したE2E対象、更新対象の既存E2E実装参照のいずれからも開始でき、TCなし経路では確認済み期待挙動を利用してTCを創作しない
- 既存実装優先のPlaywright実装
- E2E対象 ↔ E2E実装参照。TCが存在する場合はTC ↔ E2E実装参照も保持
- lint / typecheck / test discovery等の静的・軽量検証を完了条件化し、既存verify / test validation等は実行内容を確認して実E2E・外部I/O・状態変更等を含まないものだけimplementationで実行
- inspection差分があれば必要範囲だけ再inspection
- Playwright未導入でも明示要求 + 最小構成で済む場合は局所導入可能にする

### 5. E2E実装レビューとTC追跡を既存Skillへ追加する

対象:

- `skills/adversarial-review/**`
- `skills/coverage-analysis/**`

実施内容:

- E2Eテスト成果物用review referenceを追加し、TCありでは元TC、TCなしでは明示E2E対象・確認済み期待挙動・現在有効な仕様根拠との意味一致を確認
- E2E testwareレビューでは、QA IDの既存検証とは別に対象repoの安定したtest identifierまたはrepo-relative path + title path等のE2E実装参照をfixtureと照合できる決定論的契約を追加し、対象の存在・一致を検証する
- `adversarial-review`からlint / typecheck / discoveryの主責務を外す
- 一般プロダクトコードレビューとの発火境界を維持
- `coverage-analysis`へTC → E2E実装 / 扱いの意味追跡を追加
- E2E対象時は`TC ID | 扱い | E2E実装参照 | 根拠 / 備考`の対応表を持ち、既存QA IDグラフとは別契約で決定論的に検証
- E2E実装 → 実行結果は通常経路の必須分析にしない。部分分析する場合は、各E2E実装参照からresolved primary TestCaseまたは実行結果参照と結果 / 未実行理由へ辿れることを最低契約として決定論的に検証
- `coverage-analysis`の`SKILL.md` / guidanceにある「最も近い担当Skill」を、共通契約の「意味が変わる最も早い責任Skill」へ統一

### 6. `e2e-test-execution`を追加する

対象:

- `skills/e2e-test-execution/**`

実施内容:

- execution直接開始の契約
- 今回利用する実際の実行入口とpackage script / task / wrapper / pre-post処理のうち、安全性・実行意味へ影響するcommand chain確認
- 指定URL / origin / project確認
- project dependencies / teardown
- `globalSetup` / `globalTeardown`と`globalSetup`が返すteardown callback
- fixture / hookの副作用確認。automatic fixture、worker-scoped automatic fixtureを含む
- 実行対象test本体から到達するhelper / Page Object / API等のうち副作用・環境越境へ関係する経路確認
- `webServer`の起動・終了と、今回起動したprocess / 既存reuse processの所有関係
- custom reporterの外部I/O・状態変更と、test / reporter output先の削除・上書き影響
- snapshot / source更新と実行前後のworking tree差分確認
- config / project / file / describe / test / CLIの上書きを含む対象testの実効設定と、retries / repeatEach / workers / parallel設定
- 実行集合・途中停止へ影響する設定やfilter / focus
- shared account / server-side data
- 高リスク副作用回数を確定できない場合の局所ブロック
- 通常runではretries / repeatEachを原則変更せず、変更実行は診断目的として区別
- runner管理のdependency / setup / fixture / hookと、run外でexecutionが行う準備を分離し、二重setupを禁止
- Playwright外で必要な場合だけ、確認済み方法による認証・データ・開始状態準備を実行
- 既存機械可読reporterまたは標準JSON等による構造化結果取得。今回runで生成・更新されたartifactだけを結果として利用
- reporter / Playwright API / process観測が直接提供する値だけをraw factとして扱い、提供されないrun status / repeatEachIndex等を推測補完しない。複数情報源から導出した値はraw factと区別し、必要値を取得できなければ確認不能 / 構造化結果不完全として扱う
- run全体status / process exit code / run-level errorを別々に保持し、取得不能なraw値を他項目から代用しない
- primary / dependency / teardown testを区別し、論理的な要求primary対象とproject / repeatEach等を解決したresolved primary TestCaseを分離して、生の`TestResult.status` / `outcome` / attemptsを保持
- 各logical primaryが1件以上のresolved primary TestCaseへ解決されるか、解決できなければ理由を保持し、logical primaryが存在するのにresolved 0件・理由なしを完全実行扱いしない
- runner管理teardownとrun外cleanupを分離し、二重cleanupを禁止したうえでcleanup成功 / 失敗 / 未確認等を記録
- 証跡・secret保護
- Playwright機能・設定の対応状況や挙動が不確かな場合だけ、その時点で対象repoと公式仕様を確認。毎回のversion確認は行わない

### 7. `e2e-test-result-analysis`を追加する

対象:

- `skills/e2e-test-result-analysis/**`

実施内容:

- Playwright事実と原因推論の分離
- 検証済み実行結果・E2E実装参照・証跡を最低入力とし、TC / 仕様根拠は存在し判定に必要な場合だけ利用する。TCなし経路のためにTCを創作しない
- raw attempt statusではなく最終outcome / expectedStatus / run全体結果 / cleanup / ユーザー要求を基準にした起動契約
- cleanup未確認も分析対象に含め、cleanup状態の再確認が必要なら`e2e-test-execution`へ戻す
- 「実行結果だけ」と明示された依頼では原因分析を自動追加しない契約
- 原因を複数持てる設計
- 判定不能を原因と混同しない
- テスト対象version不明時の扱い
- 再現性を別軸で保持
- 追加証拠取得が必要な場合は、目的・仮説・必要範囲までを本Skillで決め、実際の再実行は`qa-workflow`を介して`e2e-test-execution`へ委譲
- 最も早い責任Skillへのrouting
- プロダクトFAILをE2Eコード修正で消さない契約

### 8. `e2e-test-reporting`を追加する

対象:

- `skills/e2e-test-reporting/**`

実施内容:

- 検証済み実行結果を必須入力とし、分析を実施した場合だけ検証済み分析結果を利用
- 実行事実・分析結果・ブロック・残存リスクを報告
- run全体status / process exit code / run-level / global errorと、cleanupの成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態、残存副作用を失わず報告
- 論理的な要求primary対象数、resolved primary TestCase数、実際に開始したresolved primary TestCase数を区別して報告し、未実行もlogical primary単位とresolved primary TestCase単位を分ける。人間向けに再集計する場合は集計単位を明示し、retry attempt数をresolved件数へ混ぜない
- TC IDは存在する場合だけ出力し、TCなし経路のために生成しない
- 異常のない実行からも必要なら報告可能
- 分析済み結果だけから直接開始する場合は必要な実行事実へ追跡可能であることを確認
- flaky / timeout / interrupted等を単純PASS / FAILへ潰さない
- 証跡内容を無条件転載しない
- 新しい原因判断・仕様解釈を禁止

### 9. 評価基盤を14 Skillへ更新する

対象:

- `.github/workflows/validate-skills.yml`
- `.github/workflows/deterministic-output-evals.yml`
- 必要な`.github/workflows/*-evals.yml`
- `EVALS.md`
- `scripts/skills/evals/**`
- `tests/skills/evals/**`
- 各Skill `evals/**`

実施内容:

- 9 Skill / 180 query前提を14 Skill / 280 queryへ更新
- semantic 2ケース / Skill契約を維持するなら28件へ更新
- deterministic最低ケース数の固定値を既存契約に合わせて更新
- `CANONICAL_SKILLS`更新
- `Skill + 対象`状態のvalidator / fixture / regression更新
- E2E Skillの出力契約validator追加
- 発火境界を既存queryの置換・再配分で反映
- repo内CIではtrigger datasetの件数・比率・構造等を検証し、実際のSkill発火 / trigger_rateは実Agent評価として区別。実Agent評価を利用できない場合は未実施とし、dataset検証だけで発火PASSとしない
- 共通runtimeで変更不要な箇所は触らない

### 10. `qa-workflow`ルーティングを評価する

実Agent統合harnessは作りません。

`qa-workflow`の決定論的 / 意味評価で、途中開始、省略、直接execution、異常のない実行のanalysis省略、異常時analysis、局所ブロック、修正routing、再実行、報告までを確認します。
