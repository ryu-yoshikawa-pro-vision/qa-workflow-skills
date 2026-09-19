# テスト分析・テスト技法の決定論的自動化Plan

## 1. 目的

現在の`qa-workflow-skills`は、テスト分析・テスト要求・テスト条件・詳細テストケース・カバレッジ分析をSkill instructionとLLM判断で実行し、開発・回帰時に決定論的validatorで出力契約を評価しています。

本変更では、テスト分析・テスト設計のうち、入力が構造化された後は機械的に処理できる部分をSkill実行時のscriptへ移します。加えて、調査で必要と判断したテスト分析・設計技法を既存の`test-analysis` / `test-condition-design`へ正式追加し、技法選択、Coverage / 終了条件、成果物形式、validator、semantic eval、発火評価まで既存Skill契約へ組み込みます。

LLMには、仕様の意味理解、要素抽出、仕様根拠の対応付け、リスク判断、技法採用判断、成立条件の意味解釈、具体的な期待結果等の意味判断を残します。値・組合せ・遷移・経路・Coverage・追跡・優先度継承・重複検出・変更伝播等の機械処理はscriptへ移します。

決定論性の保証対象は自然言語入力そのものではありません。**同じcanonicalなruntime入力、同じruntime / generator contract version、同じruntime / generator implementation fingerprint、同じ静的参照データversionから同じgenerator結果を再現でき、statefulなID materializeではさらに同じtarget annotation / Disposition / merge指定とprevious target / CI / expected result root / ID stateから同じID対応を再現できる状態**を作ります。

正規化済みモデルが元のAuthority / Risk / TR等を意味的に漏れなく表しているかは、既存の上流閉鎖、semantic eval、レビューで確認します。

## 2. 現状

基準commit `3510e6ffce87ba8c025ebde22f9947dbb6074f9c`では14 Skillが存在します。

本Planでテスト分析・設計のgenerator・構造検査を追加する主対象は次の5 Skillです。`qa-workflow`にもruntime状態の集約、stale判定、完了判定を機械処理するruntimeを追加するため、Skill実行時にPython scriptを持つ対象は6 Skillです。

- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`

加えて、成果物の再利用、上流変更の伝播、局所ブロック、完了判定を新契約へ合わせるため、`qa-workflow`も統合対象とします。runtime由来の未解決事項をmodel単位で質問・再開できるようにするため、`question-analysis`の質問一覧・ブロック中範囲へ`Runtime Skill / Runtime Unit Key / Model Key / Target Key / Generation Fingerprint`列を追加し、deterministic validatorも更新します。技法固有ロジックは`test-analysis` / `test-condition-design`を正本とし、`question-analysis`や`qa-workflow`へ複製しません。

現状はLLMが成果物を作り、評価側でPairwise、BVA、状態遷移、Authority / Risk → TR、TCN / CI → TC、追跡グラフ等の一部を後から機械検査しています。本変更では、評価側で既に機械判定できる領域を中心に、実行時も「LLMが意味を正規化する → Skill runtime scriptが生成・計算・構造検査する → LLMが意味を統合する → 独立validator / semantic evalが検証する」構造へ変更します。

## 3. 自動化対象の全体一覧

### 3.1 一覧化の基準

対象は、現在の`qa-workflow-skills`の責務と、ISTQB CTFL / CTAL-TA / CTAL-TTAでテスト分析・テスト設計として扱われる技法のうち、**意味判断後に機械的に処理できる部分**です。

既存技法のCoverage modeや入力形式として自然に表現できるものは既存名を再利用します。独立した問題構造・選択理由・Coverage契約を持つ技法は、正規技法名・成果物契約・deterministic / semantic evalを同時に追加します。

| 対象 | scriptへ移す処理 | LLMへ残す処理 | 本Planでの扱い |
| --- | --- | --- | --- |
| プロダクトリスク | 確定済みschemeと入力値からlevel計算、並び替え、範囲検証 | リスク発見、採点根拠、scheme採用判断 | 実装 |
| 変更影響 / 回帰対象抽出 | 明示済み変更nodeとdependency / traceability edgeから影響候補を抽出 | edge自体の意味、構造外の間接影響判断 | 実装 |
| テスト技法選択 | 正規化済みproblem signalから技法候補を算出 | problem signal抽出、最終採用 | 実装 |
| 同値分割 / Each Choice | partition構造検査、代表値候補、Coverage計算 | partitionの意味的定義 | 実装 |
| 境界値分析 | 2-value / 3-value、包含 / 排他、step / 最小単位に基づく候補生成 | 境界の意味、採用深度 | 実装 |
| Domain Testing | Reliable Domain Coverageとしてrelation別のON / OFF / IN / OUT等を生成・計算 | domain式、対象border、precisionの意味 | 実装 |
| Decision Table | rule space、成立不能、未定義、重複、矛盾、Coverage | condition / action / constraint抽出 | 実装 |
| Decision Table最適化 | action-equivalentなruleのdon't-care統合候補 | 統合で業務意味・Authorityを失わないか | 実装 |
| 全組合せ / Base Choice / Pairwise / N-wise / mixed-strength | 成立可能tuple、Coverage row、constraint処理 | factor / value / constraint、strength選択 | 実装 |
| Classification Tree | classification / classから組合せmodelへの機械変換 | classification / classの意味的分解 | 実装 |
| 状態遷移 / n-switch / Round-trip | 状態・遷移Coverage、sequence、到達可能性、setup prefix | state / event / guard / resetの意味 | 実装 |
| Use Case / シナリオ | path / node / edge / simple loop / fork-join Coverage | main / alternative分類、業務上の意味 | 実装 |
| CRUD Testing | CRUD completenessのoperation Coverageと、正規化済みlifecycle / negative sequenceのconsistency Coverage | function / entity / operation / lifecycleの業務意味 | 実装 |
| Cause-Effect Graph | 構造化済みcause / effectからDecision Table入力へ展開 | cause / effect / 論理関係抽出 | 実装 |
| Syntax-Based Testing | 明示grammar / BNF相当modelからvalid syntax、production Coverage、明示mutation候補 | grammar作成、mutation結果のinvalid意味判断 | 実装 |
| JSON Schema / OpenAPI / HTML constraint | 対応subsetのmachine-readable schema / DOM属性を正規化しCoverage候補生成 | そのschema / DOMが製品Authorityとして有効か | 実装 |
| UI pattern | catalogから一般的な確認候補を生成 | 製品固有expected result、pattern採用判断 | 実装 |
| テストデータ要求 | role / state / partition / boundary / entity等から要求を統合し矛盾検出 | 実データ選定、準備方法、利用可否 | `test-condition-design`で実装 |
| テスト環境要求 | browser / role / feature flag / integration等を統合し矛盾検出 | 環境選定、利用可否、運用判断 | `test-analysis`で実装 |
| Random Testing | 指定domain / distribution / seed / algorithmから再現可能入力列を生成 | operational profile、distribution、oracle、停止条件 | 実装 |
| Metamorphic Testing | 明示済みrelationからfollow-up inputと期待関係を生成 | relation発見・妥当性 | 実装 |
| テスト要求の構造処理 | Authority / Risk → TR閉鎖、未知参照、Disposition重複、優先度 | TR本文、分割 / 統合、検証責務 | 実装 |
| テストケースの構造処理 | TCN / CI → TC閉鎖、未知参照、優先度、Authority対応 | 前提、手順、具体データ、期待結果 | 実装 |
| 要求追跡 | Authority / Risk → TR → TCN → CI → TCのmissing / orphan / unknown | 意味上のedge作成 | 実装 |
| 構造的重複 / 統合 | 同一key / assignment / rule / transition等の重複、明示済みmerge groupのunion | 意味上の同一性判断 | 実装 |
| テスト優先順位 | 採用済み計算式または既存継承規則による計算・sort | scoreモデル設計、リスク採点 | 実装 |

### 3.2 正規技法名との関係

次は既存技法の内部Coverage modeまたは入力形式として扱います。

- Each Choice → `同値分割`
- Base Choice / Pairwise / N-wise / mixed-strength / Classification Tree由来の組合せ → `Pairwise / 組合せ`
- transition-pair / n-switch / Round-trip → `状態遷移`
- Cause-Effect Graph → Decision Tableへの機械変換

Domain Testing、CRUD Testing、Random Testing、Metamorphic Testing、Syntax-Based Testingのように独立したproblem model / selection reason / Coverageまたは終了条件の契約を持つものは、既存技法へ無理に押し込めず正規技法名を追加します。

追加する正規技法名は次で固定します。

- `Domain Testing`
- `CRUD Testing`
- `Random Testing`
- `Metamorphic Testing`
- `Syntax-Based Testing`

`test-analysis`の許可技法、`references/guidance.md`、`assets/output-template.md`、deterministic / semantic evalをこの表記へ揃えます。`test-condition-design`では`SKILL.md`、`references/coverage-techniques.md`、出力template、validator、semantic evalへ同じ表記と適用条件を反映します。

### 3.3 Coverageの意味

generatorが返す100%等のCoverageは、**明示された正規化済みモデル内のCoverage**です。対象仕様全体の100%とは扱いません。

- Authority / Risk → TR → TCNの上流閉鎖は別途確認する
- 選択した技法はmodel、対象外、未解決、または明示的なruntime非対応へ必ず閉じる
- 正規化済みモデルが上流の意味を十分に表しているかはsemantic evalで確認する
- 全runtime unitで`result_status=ready / freshness_status=current`を必須とし、さらに`runtime_required=true`のunitでは`deterministic_generated=true`を必須とする
- Dispositionによる成果物上の閉鎖と技法Coverage達成を混同しない

## 4. 本Planの実装範囲

本Planは部分実装を完了条件にしません。上記3.1で「実装」とした処理を、対応Skillのruntime、成果物契約、validator、semantic eval、workflow統合まで含めて実装します。加えて、runtimeの上流fingerprintをMarkdown再解釈に依存させないため、`spec-analysis` / `test-analysis` / `test-requirement-design` / `test-condition-design` / `test-case-design`へcanonical machine Entityを保存します。

主な責務は次のとおりです。

1. `spec-analysis`
   - 現在有効なAuthorityをcanonical machine JSONとして成果物へ保存する
   - runtimeは追加せず、既存の仕様解決責務を維持する

2. `test-analysis`
   - risk scheme計算
   - technique candidate
   - change impact
   - テスト環境要求

3. `test-requirement-design`
   - Authority / Risk → TRの構造処理

4. `test-condition-design`
   - 各テスト技法generator
   - schema / HTML / UI候補
   - テストデータ要求
   - Coverage Itemの機械証拠

5. `test-case-design`
   - TCN / CI → TCの構造処理
   - 具体的なテストデータ・手順・expected resultはLLMの意味判断に残す

6. `coverage-analysis`
   - テスト設計範囲のtraceabilityと構造ギャップ

7. `qa-workflow`
   - contract / model version、上流変更、runtime unit間依存、stale派生成果物、局所ブロック、`要再検証`、legacy成果物再利用、完了判定
   - fingerprint比較、runtime状態集約、機械的なstale / 完了判定をLLMに手計算させずruntime scriptで実行する

8. `question-analysis`
   - runtimeの構造化issueに含まれる`skill / runtime_unit_key / model_key / target_key / generation_fingerprint`を質問・ブロック・回答後の再開まで保持する
   - 技法固有の判定は行わず、既存の不明点分類と回答正規化だけを担当する

9. 評価契約
   - 新規技法に伴う`test-analysis` / `test-condition-design`の発火評価を更新する
   - trigger evalは`test-analysis` / `test-condition-design`をtrain 24件（12 / 12）・validation 20件（10 / 10）、その他12 Skillをtrain 12件（6 / 6）・validation 8件（4 / 4）とし、repository全体328件へ固定する
   - `adversarial-review`には技法ロジックを複製せず、新規技法の代表的な誤用を検出するsemantic fixtureだけを追加する

## 5. 本Planの対象外

次は機械化可能でも、テスト分析・テスト設計成果物の生成・構造検査を越えて、コード解析やテスト実行そのものを主責務とするため本Planの対象外です。

- Property-Based Testing runtime / shrinking engine
- fuzzing engine
- Differential Testing runner
- symbolic / concolic execution
- statement / branch / condition / MC/DC instrumentation
- mutation testing実行
- visual regression runner
- accessibility checker実行
- E2Eテストコード自動生成

対象外項目について将来用adapterやplugin構造は作りません。

## 6. 自動化しない判断

次はLLMまたは人間の意味判断として残します。

- 自然言語から仕様・condition・partition・state・risk・metamorphic relation等を発見すること
- どのAuthorityが現在有効かを決めること
- 期待結果やoracleを新規に決めること
- リスクの影響度・発生可能性を採点すること
- 技法を最終採用すること
- 意味上の重複・統合可否を判断すること
- 実データ、環境、運用上の利用可否を決めること
- Error GuessingやExploratory Testingで新しい故障仮説を発見すること

scriptが正規化済みモデル内で100% Coverageを返しても、LLMの正規化に意味上の漏れがないことまでは保証しません。

## 7. 実装時に維持する責務境界

本Planの実装では、次を全Skillで共通の前提とします。

- LLMは自然言語から意味を正規化し、Authority対応、risk判断、技法採用、意味上の同一性、expected result等を決める。scriptへ渡した後の列挙、計算、fingerprint、ID採番、Coverage集計、構造検査、stale判定をLLMが再計算しない
- Skillがruntime対象を扱う場合は、Skill instructionに定義したdispatch表からscriptを選び、保存済み`Machine Runtime Input / Result`を決定論的に抽出・strict decodeして再投入する。MarkdownをLLMが読み直してJSONを再生成しない
- runtime間で機械変換した結果は、上流の`skill + runtime_unit_key + generation_fingerprint`を保持して下流へ渡す。上流runtime結果が変わった場合は依存する下流runtime unitだけをstaleへ戻す
- generator targetは、Coverage Item、明示的なmerge、または既存Skill契約上のDispositionへ閉じる。Dispositionによる成果物上の閉鎖と技法Coverage達成は別に判定する
- 本Planで追加する全scriptは、deterministicなdispatch / integration testで実際の呼出経路を検証する。実Agentでは代表経路でPython実行、stdout envelope parse、machine結果採用まで確認する

本Planは1 PR内で全対象を完了させる前提です。実装途中の契約確認は後続実装の手戻りを減らすための検証点であり、そこで対象を打ち切ったり別PRへ先送りしたりしません。
