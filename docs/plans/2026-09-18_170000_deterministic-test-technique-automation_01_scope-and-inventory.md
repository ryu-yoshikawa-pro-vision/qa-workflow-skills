# テスト分析・テスト技法の決定論的自動化Plan

## 1. 目的

現在の`qa-workflow-skills`は、テスト分析・テスト要求・テスト条件・詳細テストケース・カバレッジ分析をSkill instructionとLLM判断で実行し、開発・回帰時に決定論的validatorで出力契約を評価しています。

本変更では、テスト分析・テスト設計のうち、入力が構造化された後は機械的に処理できる部分をSkill実行時のscriptへ移します。

狙いは「LLMを使わないこと」ではありません。LLMの責務を、仕様の意味理解、要素抽出、仕様根拠の対応付け、リスク判断、成立条件の解釈など、人間の意味判断が必要な箇所へ限定します。値・組合せ・遷移・カバレッジ・追跡・優先度継承等の計算をscriptへ移し、**同じ正規化済みモデルから同じ機械処理結果を再現できる状態**を作ります。

自然言語資料から正規化済みモデルを作るLLM判断自体は決定論的とは扱いません。正規化モデルが元のAuthority / Risk / TR等を意味的に漏れなく表しているかは、既存の上流閉鎖、意味評価、レビューで確認します。

## 2. 現状

基準commit `3510e6ffce87ba8c025ebde22f9947dbb6074f9c` では、14 Skillが存在します。

今回の主対象は次の5 Skillです。

- `test-analysis`: 変更影響、プロダクトリスク、テスト重点、テストレベル、テスト可能性、適用テスト技法
- `test-requirement-design`: Authority / Riskからテスト要求への閉鎖、優先度、Disposition
- `test-condition-design`: テスト条件、カバレッジ基準、カバレッジ項目、具体的なテスト技法
- `test-case-design`: カバレッジ項目 / テスト条件から詳細テストケースへの閉鎖、優先度、Authority対応
- `coverage-analysis`: 仕様根拠からテストケースまでの追跡、閉鎖性、ギャップ、孤立

`test-condition-design/references/coverage-techniques.md`は、同値分割、境界値分析、デシジョンテーブル、状態遷移、Pairwise / 組合せ、エラー推測、シナリオ / ユースケースを定義しています。

一方、対象Skillには現在、テスト技法生成や構造閉鎖を実行時に担うscriptがありません。LLMが成果物を作り、評価側では既に次の機械判定が実装されています。

- Pairwiseの因子 / 値、禁止制約、未知値、欠落因子、成立可能な全ペアの100%カバレッジ
- 状態遷移の必須遷移閉鎖
- BVA必須値の存在
- Authority / Risk → TRの閉鎖、上流参照整合、優先度継承
- TCN / CI → TCの閉鎖、上流参照整合、優先度継承、複数期待結果とAuthorityの対応
- カバレッジ項目ID、参照、必須フィールド、仕様根拠の整合
- 追跡グラフの未閉鎖ノード、孤立成果物、修正先の不整合

`scripts/skills/evals/deterministic/common.py`には、`itertools.product`と`itertools.combinations`を使った成立可能Pairwise集合と実カバレッジ算出が既にあります。

`test-analysis`のvalidatorには、影響度1〜4と発生可能性1〜4からリスクレベルを算出する4×4マトリクスが既にあります。

現状は「LLMが生成し、評価scriptが後から一部を検証する」構造です。本変更では、評価側で既に機械判定できる領域を中心に「LLMが意味を正規化し、Skill runtime scriptが生成・計算・構造検査を行い、評価scriptが独立に検証する」構造へ変更します。

## 3. 自動化対象の全体一覧

以下は、一般的なテスト分析・テスト設計のうち、構造化入力があれば決定論的処理または機械的生成へ移せるものを整理したものです。

### 3.1 一覧化の基準

「自動化できるものをすべて列挙する」の範囲を無制限に広げず、次を基準集合として確認します。

- 現在の`qa-workflow-skills`が正本としているテスト分析・テスト設計の技法とCoverage契約
- ISTQB CTFL v4.0.1のテスト技法
- ISTQB CTAL-TA v4.0のデータベース、振る舞いベース、ルールベース、経験ベースのテスト技法とCoverage基準
- ISTQB CTAL-TTA v4.0のwhite-box Coverage技法

この基準集合に含まれることと、このbranchで実装することは分けて扱います。既存技法のCoverage modeや入力形式として自然に表現できるものは既存名を再利用します。一方、独立した入力モデル・選択理由・Coverage契約を持つ技法は、必要性と評価契約を確認した上で正規技法名として追加して構いません。外部資料にある名称を、契約確認なしに機械的追加はしません。

| 対象 | 自動化できる処理 | 人間 / LLMに残す処理 | このbranchでの扱い |
| --- | --- | --- | --- |
| プロダクトリスク | 確定済み影響度・発生可能性からレベル算出、並び替え、範囲検証 | リスク発見、影響度・発生可能性の採点根拠 | 実装対象 |
| 変更影響 / 回帰対象抽出 | 明示済み変更要素と依存・追跡edgeから、影響するAuthority / TR / TCN / CI / TC候補を抽出 | どの依存が意味上の影響を持つか、構造上つながらない間接影響を追加するか | 実装対象。構造的な候補抽出に限定 |
| テスト技法選択 | 正規化済み問題構造から技法候補を規則で絞る | 自然言語から問題構造を読み取る、複数技法の必要性判断 | 実装対象。ただし最終判断はLLM |
| 同値分割 | 明示済みpartition set内の重複・空白・境界整合、列挙可能なdomainから代表値候補生成、partition coverage計算 | 何を同値と扱えるか、どのpartition setへ属するかの意味判断 | 実装対象 |
| Each Choice Coverage | 複数partition setについて各partitionが少なくとも1回Coverageされているかを計算 | partition setの意味、複数set間の組合せ方 | `同値分割`の内部Coverage基準として実装対象 |
| 境界値分析 | 2-value / 3-value BVA、包含 / 排他、stepに基づく直前・境界・直後値生成 | 境界の意味、型、最小単位、採用するBVA深度 | 実装対象 |
| Domain Testing | 構造化済みの多変数domainと境界式からON / OFF / IN / OUT候補とCoverageを計算 | domain式、精度、どのborderを対象にするか | 自動化可能として一覧化。多変数border契約とsolver要否を決めるため後続候補 |
| デシジョンテーブル | 条件値の組合せ列挙、成立不能判定、未定義rule検出、重複rule、同一条件に対するaction vectorの矛盾検出、rule coverage算出 | 条件・action・制約・期待結果根拠の抽出 | 実装対象 |
| デシジョンテーブル最適化 | 完全rule setからdon't care化できるrule候補を求めることは可能 | 統合で業務上の意味・根拠を失わないかの確認 | 自動化可能として一覧化するが、初回実装では行わない |
| 全組合せ | 有限domainのCartesian product生成、禁止組合せ除外 | 因子・値・制約抽出 | 実装対象 |
| Base Choice Coverage | 各因子のbase valueが確定している場合のbase組合せと1因子ずつの置換組合せ生成 | base valueの選択根拠 | `Pairwise / 組合せ`の内部Coverage modeとして実装対象。初回は`forbidden_constraints`なしに限定 |
| Pairwise | 成立可能な2-wise tupleを求め、全Cartesian productを事前materializeせずCoverageする組合せを生成 | 因子・値・制約抽出、Pairwise採用判断 | 実装対象 |
| N-wise | 成立可能なt-wise tupleを求め、全Cartesian productを事前materializeせずCoverageする組合せを生成 | t値と対象因子の選択 | 実装対象。ただし入力規模上限を設ける |
| mixed-strength組合せ | 一部因子だけ高いinteraction strengthを適用 | 高強度対象の選択根拠 | 今回は一覧化・契約予約のみ。初回実装からは外す |
| Classification Tree | classification / classが明示された後の全組合せ、Base Choice、Pairwise / N-wiseへの正規化 | classification / classの意味的分解 | 実装対象。新しい正規技法名にはしない |
| 状態カバレッジ | 状態集合と遷移から対象状態のCoverage算出 | 状態モデル抽出 | 実装対象 |
| 遷移カバレッジ | 有効遷移列挙、全遷移Coverage、欠落遷移検出 | 遷移の有効性と期待結果根拠 | 実装対象 |
| transition-pair / switch coverage | 連続遷移の組合せ列挙、n-switch Coverage | どの深度を要求するか | `状態遷移`のCoverage modeとして実装対象 |
| Round-trip Coverage | state graph上のround trip候補列挙とCoverage計算 | どのloopが対象範囲か、guardを含む実行可能性 | `状態遷移`のCoverage modeとして実装対象 |
| 状態経路 | graph上の到達可能性、outgoing transitionのない状態、指定Coverageを満たす経路候補生成 | guardを含む実行可能性、terminalか欠陥候補か、reset可能性、業務上意味のある経路選択 | 実装対象。構造事実と意味判断を分離 |
| 無効遷移 | 根拠付きで明示された無効遷移候補の構造検査・Coverage確認 | どの遷移を無効として確認するか、期待結果 | 実装対象。ただし有効遷移の補集合から全無効遷移を機械生成しない |
| Use Case / シナリオ | 明示済みflow graphのbounded path列挙、node / edge Coverage | main / alternativeの分類、業務上意味のあるシナリオ、優先度 | 一部実装対象。main / alternativeはscriptが推測しない |
| CRUD Testing | 構造化済みCRUD matrixのoperation Coverage、欠落operation、entity lifecycleの組合せ候補 | function / entity / operationの意味、欠落が仕様欠陥か対象外か | 自動化可能として一覧化。独立model / Coverage契約の実装は後続候補 |
| Cause-Effect Graph | boolean causeとeffect式が構造化済みならrule spaceへ展開し、複数effectのaction vectorをDecision Tableへ変換 | cause / effectと論理関係抽出 | 実装対象。boolean subsetだけをDecision Table経路へ統合 |
| 制約充足 | 有限domain制約のSAT / UNSAT判定、成立可能assignment列挙 | 制約式への正規化 | 実装対象。まず有限domainの明示制約のみ |
| 矛盾検出 | 同一入力条件への複数期待結果、相互排他的rule、到達不能ruleの検出 | 仕様のどちらを正とするか | 実装対象 |
| Syntax / grammar-based testing | grammarが明示されている場合の有効構文生成や規則Coverageは自動化可能 | grammarの作成、terminal / nonterminal、depth、invalid判定 | 自動化可能として一覧化するが、初回実装からは外す |
| JSON Schema等のschema-based testing | 正規化済みfield constraintのtype、required、enum、minimum、maximum、length等からCoverage候補生成 | schema dialectの意味解釈、schemaが製品仕様として有効かの確認 | 実装対象。raw schema parserは作らない |
| HTML form constraint | constraint validation対象controlの`required`、`min`、`max`、`minlength`、`maxlength`、`step`からCoverage候補生成 | DOM値と製品仕様の優先関係、`disabled` / `readonly`等の適用可否判断 | UI候補生成として実装。`pattern`の具体値生成は初回対象外 |
| UIコントロール別確認候補 | button、checkbox、radio、combobox、dialog等の種別から一般的な確認候補を参照 | その製品で期待される挙動の確定 | 実装対象 |
| keyboard / focus候補 | UI patternと外部標準からキー操作・focus候補を引く | 製品がそのpattern / 標準を採用しているかの判断 | 候補生成のみ実装 |
| test data matrix | 型、partition、boundary、enum、nullability、constraint由来の候補を整理・統合 | 実データの業務意味 | 独立generatorは作らず、成果物統合規則として実装 |
| テストデータ要求 | 構造化済みrole / state / partition / boundary / entity等から必要データ条件を重複統合し、矛盾・不足を検出 | どの実データを使うか、準備方法、個人情報等の利用可否 | 自動化可能として一覧化。初回は専用generatorを追加しない |
| テスト環境要求 | 構造化済みbrowser / role / feature flag / integration等から必要環境条件を統合し、矛盾を検出 | 環境選定、利用可否、運用上の準備判断 | 自動化可能として一覧化。初回は専用generatorを追加しない |
| Random Testing | 指定済みdomain・確率分布・seedから再現可能な入力列を生成 | 確率分布、operational profile、oracle、停止条件 | 自動化可能として一覧化。分布・停止条件の意味判断比重が高いため後続候補 |
| Property-Based Testing | property / generator domainが定義済みなら大量入力生成、shrinkingは既存ライブラリで自動化可能 | property / invariant定義 | 自動化可能として記録するが、現在のQA成果物workflow外のため実装対象外 |
| Metamorphic Testing | metamorphic relationが定義済みなら派生入力・期待関係生成 | relation発見・妥当性 | 自動化可能として記録するが実装対象外 |
| Fuzzing | grammar / schema / corpusがあれば入力変異・生成 | oracle、重要領域、停止条件 | 自動化可能として記録するが実装対象外 |
| Differential Testing | 比較対象と同一入力を与え結果差分を抽出 | 参照実装が正しいという前提、差分解釈 | 自動化可能として記録するが実装対象外 |
| Model-Based Testing | 状態モデルからCoverageを満たす経路生成 | モデル作成・oracle | 状態遷移実装の延長として一部実装 |
| テスト要求の構造処理 | Authority / Risk → TRの閉鎖、未知参照、Disposition重複、関連リスクからの最低優先度算出 | TR本文、分割 / 統合、検証責務の意味 | 実装対象 |
| テストケースの構造処理 | TCN / CI → TCの閉鎖、未知参照、最高優先度継承、番号付き期待結果とAuthority対応の構造検査 | 前提、手順、具体データ、期待結果の意味 | 実装対象 |
| 要求追跡 | Authority / Risk → TR → TCN → CI → TCの閉鎖性、孤立、欠落、未知参照 | 意味上の対応edge作成 | 実装対象 |
| Coverage集計 | partition、boundary、rule、pairwise / n-wise、state、transition等の技法別Coverageを各技法scriptで計算し、traceabilityではmissing / orphan / unknown referenceを算出 | どのCoverageを完了条件にするか、意味上のCoverage充足 | 実装対象 |
| 構造的重複 | 同一ID、同一入力組合せ、同一遷移、同一rule等の重複検出 | 意味上の重複・統合可否 | 実装対象 |
| テスト優先順位 | 採用済み計算式または既存の上流優先度継承規則がある場合の計算・sort | scoreモデル設計、リスク値採点、優先度の意味判断 | 自動化可能として一覧化。独自score式は追加しない |
| statement / branch / condition / MC/DC / Multiple Condition | instrumentationまたはCFGがあればCoverage計算、solverを使えば入力探索も可能 | コード解析環境、対象レベル選択 | 自動化可能だが現在のSkill責務外 |
| symbolic / concolic execution | path constraint生成とsolverによる入力生成 | 実行環境・モデル化・oracle | 自動化可能だが現在のSkill責務外 |
| mutation testing | mutation生成、実行、mutation score | surviving mutantの意味判断 | 自動化可能だが現在のSkill責務外 |
| visual regression | screenshot差分・閾値判定 | 意図した見た目変更かの判断 | 自動化可能だがテスト技法生成ではなく実行領域のため対象外 |
| accessibility checker | DOM / accessibility treeの規則検査 | 製品要件・例外・UX妥当性 | 自動化可能だが実行検査はE2E / 専用tool側。設計側は候補生成のみ |
| Error Guessing | 過去不具合等から候補を検索することは可能 | 故障仮説の発見・優先度判断 | 決定論的generator対象外 |
| Exploratory Testing | charter templateや既知リスクの提示 | 探索・観察・次行動の判断 | 決定論的generator対象外 |
| Checklist-Based Testing | catalogから候補を引く | 対象への関連性・期待結果 | UI pattern等の候補検索に限定 |
| リスク発見 | 既知カテゴリとの照合 | 何が製品上の失敗になるか | LLM / 人間 |
| 期待結果の補完 | なし | 現在有効な仕様根拠から確定 | 自動化しない |

### 3.2 正規技法名との関係

既存技法のCoverage modeまたは入力形式として意味が保てる場合は、不要に正規技法名を増やしません。

- Base Choice / Pairwise / N-wise / Classification Tree由来の組合せは、`Pairwise / 組合せ`の内部Coverage modeまたは入力形式として扱う
- transition-pair / n-switch / Round-tripは、`状態遷移`の内部Coverage modeとして扱う
- Cause-Effect GraphはDecision Table入力への変換、schema / UI属性は既存技法の候補生成元として扱う

一方、CRUD Testing、Domain Testing、Metamorphic Testing等のように、独立した問題構造・適用理由・Coverage契約を持つ技法を今後実装する場合は、既存名へ無理に押し込めず、`test-analysis`の正規技法名・成果物契約・deterministic / semantic evalを同時に拡張します。

### 3.3 Coverageの意味

generatorが返す100%等のCoverageは、**明示された正規化済みモデル内のCoverage**です。これだけで対象仕様全体を100%カバーしたとは扱いません。

- Authority / Risk → TR → TCNの上流閉鎖は既存成果物と構造検査で確認する
- 正規化済みモデルがTCNの意味を漏れなく表しているかはsemantic evalで確認する
- `unresolved` / `unsupported` / `limit_exceeded`が残るmodelを100%完了扱いしない
- Dispositionによる成果物上の閉鎖と、技法Coverage達成を混同しない

## 4. 今回の実装範囲

このbranchでは、現在のテスト分析・設計・カバレッジ責務へ自然に収まり、構造化後の結果が一意に計算できるものを実装対象とします。

1. `test-analysis`
   - 確定済みリスク値からのリスクレベル算出
   - 正規化済み問題構造からの技法候補判定
   - 明示済み変更要素と追跡 / 依存edgeからの構造的な影響範囲・回帰候補抽出

2. `test-requirement-design`
   - Authority / Risk → TRの構造的な閉鎖
   - 未知上流ID、linked + disposed重複の検出
   - 関連プロダクトリスクからの最低優先度算出

3. `test-condition-design`
   - 同値分割の構造検査、代表値候補、Each Choice Coverage
   - BVA
   - Decision Table
   - 全組合せ / Base Choice / Pairwise / N-wise
   - Classification Treeから組合せ入力への正規化
   - 状態 / 遷移 / transition-pair / n-switch / Round-trip
   - 並行性を含まない明示flowのpath / node / edge / simple loop Coverage
   - Cause-Effect GraphからDecision Tableへの展開
   - 有限domain制約の成立可能性
   - 正規化済みschema / HTML constraint由来のテストデータ候補
   - UIコントロール別の確認候補

4. `test-case-design`
   - TCN / CI → TCの構造的な閉鎖
   - 未知上流ID、linked + disposed重複の検出
   - Coverage Itemからの最高優先度継承
   - 複数期待結果とAuthorityの番号対応に関する構造検査

5. `coverage-analysis`
   - `対象 / 実行範囲 = テスト設計`での追跡グラフの構造検査
   - 孤立 / 欠落 / 未知参照
   - 技法別Coverage値は`test-condition-design`成果物を利用し、本Skillで再計算しない

TR本文、テストケースの具体的前提・手順・テストデータ・期待結果、変更の意味的な影響判断はLLMに残します。

## 5. 今回実装しないもの

次は自動化可能ですが、独立した入力モデル・Coverage契約・実行環境等の追加設計が必要なため、このbranchでは実装しません。

- Domain Testingの多変数domain generator
- CRUD Testing
- Random Testing
- Metamorphic Testingのfollow-up test generator
- mixed-strength組合せ
- grammar-based testing runtime
- test data requirement専用generator
- test environment requirement専用generator
- Property-Based Testingのruntime
- fuzzing engine
- Differential Testing runner
- symbolic / concolic execution
- statement / branch / MC/DC instrumentation
- mutation testing
- visual regression runner
- accessibility実行checker
- 対象プロダクトへテストコードを自動実装する汎用generator

これらを今後追加する場合も、「意味判断をLLMに残し、構造化済み入力から一意に処理できる部分だけをscriptへ移す」という本Planの境界を維持します。

## 6. 自動化しない判断

以下は機械処理へ移しません。

- 自然言語仕様から業務上の意味を決める
- 「この値は同値」と判断する
- 製品リスクそのものを発見する
- 影響度・発生可能性を根拠なく採点する
- 未定義の製品挙動を一般慣習から確定する
- 一般的なUIパターンを製品仕様として上書きする
- エラー推測や探索的テストの仮説を固定ロジックで置き換える
- テストケースの期待結果を、仕様根拠なしにscriptが作る

この境界は既存Skillの「プロダクトリスク、エラー推測、実装情報等から未定義の期待結果を作らない」という契約を維持します。

また、scriptが正規化済みモデル内で100% Coverageを返しても、LLMの正規化に意味上の漏れがないことまでは保証しません。モデル完全性は既存のAuthority / Risk / TR閉鎖とsemantic evalで確認します。
