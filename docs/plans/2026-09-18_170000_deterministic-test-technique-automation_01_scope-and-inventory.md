# テスト分析・テスト技法の決定論的自動化Plan

## 1. 目的

現在の`qa-workflow-skills`は、テスト分析・テスト要求・テスト条件・詳細テストケース・カバレッジ分析をSkill instructionとLLM判断で実行し、開発・回帰時に決定論的validatorで出力契約を評価しています。

本変更では、テスト分析・テスト設計のうち、入力が構造化された後は機械的に処理できる部分をSkill実行時のscriptへ移します。

狙いは「LLMを使わないこと」ではありません。LLMの責務を、仕様の意味理解、要素抽出、仕様根拠の対応付け、リスク判断、成立条件の解釈など、人間の意味判断が必要な箇所へ限定します。値・組合せ・遷移・カバレッジ等の計算をscriptへ移し、同じ入力から同じテスト設計結果を再現しやすくします。

## 2. 現状

基準commit `3510e6ffce87ba8c025ebde22f9947dbb6074f9c` では、14 Skillが存在します。

今回の主対象は次の3 Skillです。

- `test-analysis`: プロダクトリスク、テスト重点、テストレベル、テスト可能性、適用テスト技法
- `test-condition-design`: テスト条件、カバレッジ基準、カバレッジ項目、具体的なテスト技法
- `coverage-analysis`: 仕様根拠からテストケースまでの追跡、閉鎖性、ギャップ、孤立

`test-condition-design/references/coverage-techniques.md`は、同値分割、境界値分析、デシジョンテーブル、状態遷移、Pairwise / 組合せ、エラー推測、シナリオ / ユースケースを定義しています。

一方、`skills/test-condition-design/`には現在`scripts/`がありません。技法適用はLLMが行い、評価側では次の機械判定が既に実装されています。

- Pairwiseの因子 / 値、禁止制約、未知値、欠落因子、成立可能な全ペアの100%カバレッジ
- 状態遷移の必須遷移閉鎖
- BVA必須値の存在
- カバレッジ項目ID、参照、必須フィールド、仕様根拠の整合

`scripts/skills/evals/deterministic/common.py`には、`itertools.product`と`itertools.combinations`を使った成立可能Pairwise集合と実カバレッジ算出が既にあります。

`test-analysis`のvalidatorには、影響度1〜4と発生可能性1〜4からリスクレベルを算出する4×4マトリクスが既にあります。

`coverage-analysis`のvalidatorには、追跡グラフから未閉鎖ノード、孤立成果物、修正先の不整合を求める処理が既にあります。

現状は「LLMが生成し、評価scriptが後から一部を検証する」構造です。本変更では、評価側で既に機械判定できる領域を中心に「LLMが構造化し、実行時scriptが生成・計算し、評価scriptが独立に検証する」構造へ変更します。

## 3. 自動化対象の全体一覧

以下は、一般的なテスト分析・テスト設計のうち、構造化入力があれば決定論的処理または機械的生成へ移せるものを整理したものです。

| 対象 | 自動化できる処理 | 人間 / LLMに残す処理 | このbranchでの扱い |
| --- | --- | --- | --- |
| プロダクトリスク | 確定済み影響度・発生可能性からレベル算出、並び替え、範囲検証 | リスク発見、影響度・発生可能性の採点根拠 | 実装対象 |
| テスト技法選択 | 正規化済み問題構造から技法候補を規則で絞る | 自然言語から問題構造を読み取る、複数技法の必要性判断 | 実装対象。ただし最終判断はLLM |
| 同値分割 | 明示済みpartitionの重複・空白・境界整合、列挙可能なdomainから代表値候補生成、partition coverage計算 | 何を同値と扱えるかの意味判断 | 実装対象 |
| 境界値分析 | 2-value / 3-value BVA、包含 / 排他、stepに基づく直前・境界・直後値生成 | 境界の意味、型、最小単位、採用するBVA深度 | 実装対象 |
| デシジョンテーブル | 条件値の組合せ列挙、制約除外、成立不能判定、未定義rule検出、重複rule、同条件で異なる結果の矛盾検出、rule coverage算出 | 条件・結果・制約・期待結果根拠の抽出 | 実装対象 |
| デシジョンテーブル最適化 | 同一結果かつ安全にdon't care化できるruleの機械統合 | 統合しても業務上の意味を失わないかの確認 | 実装対象。最適化前tableを必ず保持 |
| 全組合せ | 有限domainのCartesian product生成、禁止組合せ除外 | 因子・値・制約抽出 | 実装対象 |
| Pairwise | 成立可能な2-wise組合せ生成、全ペアCoverage計算 | 因子・値・制約抽出、Pairwise採用判断 | 実装対象 |
| N-wise | t-wise組合せ生成、成立可能tupleのCoverage計算 | t値と対象因子の選択 | 実装対象。ただし入力規模上限を設ける |
| mixed-strength組合せ | 一部因子だけ高いinteraction strengthを適用 | 高強度対象の選択根拠 | 今回は一覧化・契約予約のみ。初回実装からは外す |
| Classification Tree | classification / classが明示された後の最小基準、全組合せ、Pairwise / N-wise展開 | classification / classの意味的分解 | 実装対象 |
| 状態カバレッジ | 状態集合と遷移から対象状態のCoverage算出 | 状態モデル抽出 | 実装対象 |
| 遷移カバレッジ | 有効遷移列挙、全遷移Coverage、欠落遷移検出 | 遷移の有効性と期待結果根拠 | 実装対象 |
| transition-pair / switch coverage | 連続遷移の組合せ列挙、n-switch Coverage | どの深度を要求するか | 実装対象 |
| 状態経路 | 開始状態からの到達可能性、到達不能状態、dead end、指定Coverageを満たす経路候補生成 | reset可能性、業務上意味のある経路選択 | 実装対象 |
| 無効遷移 | 明示された許可遷移の補集合から候補生成 | 未定義操作が本当に拒否される仕様か | 候補生成のみ実装。期待結果は自動確定しない |
| Use Case / シナリオ | 明示済みflow graphのmain / alternative path列挙、分岐Coverage | 業務上意味のあるシナリオ、優先度 | 一部実装対象 |
| Cause-Effect Graph | boolean条件 / effectが構造化済みならrule spaceへ展開しDecision Tableへ変換 | cause / effectと論理関係抽出 | 実装対象。Decision Table経路へ統合 |
| 制約充足 | 有限domain制約のSAT / UNSAT判定、成立可能assignment列挙 | 制約式への正規化 | 実装対象。まず有限domainの明示制約のみ |
| 矛盾検出 | 同一入力条件への複数期待結果、相互排他的rule、到達不能ruleの検出 | 仕様のどちらを正とするか | 実装対象 |
| Syntax / grammar-based testing | grammarが明示されている場合の有効構文生成、規則単位Coverage、単一規則破壊によるinvalid候補生成 | grammarの作成、invalid時の期待結果 | 実装対象。ただし汎用fuzzer化しない |
| JSON Schema等のschema-based testing | type、required、enum、minimum、maximum、length、format等から候補生成 | schemaが製品仕様として有効かの確認 | 実装対象。汎用schemaの最小subsetから開始 |
| HTML form constraint | `required`、`min`、`max`、`minlength`、`maxlength`、`pattern`等から候補生成 | DOM値と製品仕様の優先関係判断 | UI候補生成として実装 |
| UIコントロール別確認候補 | button、checkbox、radio、combobox、dialog等の種別から一般的な確認候補を参照 | その製品で期待される挙動の確定 | 実装対象 |
| keyboard / focus候補 | UI patternと外部標準からキー操作・focus候補を引く | 製品がそのpattern / 標準を採用しているかの判断 | 候補生成のみ実装 |
| test data matrix | 型、partition、boundary、enum、nullability、constraintから入力データ候補を組成 | 実データの業務意味 | 実装対象 |
| seed付きランダム生成 | 同一seedで再現可能なサンプル生成 | 何をランダム化するか | 補助機能として実装可能。主技法にはしない |
| Property-Based Testing | property / generator domainが定義済みなら大量入力生成、shrinkingは既存ライブラリで自動化可能 | property / invariant定義 | 自動化可能として記録するが、現在のQA成果物workflow外のため実装対象外 |
| Metamorphic Testing | metamorphic relationが定義済みなら派生入力・期待関係生成 | relation発見・妥当性 | 自動化可能として記録するが実装対象外 |
| Fuzzing | grammar / schema / corpusがあれば入力変異・生成 | oracle、重要領域、停止条件 | 自動化可能として記録するが実装対象外 |
| Differential Testing | 比較対象と同一入力を与え結果差分を抽出 | 参照実装が正しいという前提、差分解釈 | 自動化可能として記録するが実装対象外 |
| Model-Based Testing | 状態モデルからCoverageを満たす経路生成 | モデル作成・oracle | 状態遷移実装の延長として一部実装 |
| 要求追跡 | Authority → TR → TCN → CI → TCの閉鎖性、孤立、欠落、未知参照 | 意味上の対応edge作成 | 実装対象 |
| Coverage集計 | partition、boundary、rule、pairwise / n-wise、state、transition、traceability等の割合計算 | どのCoverageを完了条件にするか | 実装対象 |
| 構造的重複 | 同一ID、同一入力組合せ、同一遷移、同一rule等の重複検出 | 意味上の重複・統合可否 | 実装対象 |
| テスト優先順位 | 採用済み計算式がある場合のscore計算・sort | scoreモデル設計、リスク値採点 | 案件固有式がある場合だけ利用できる共通hookとして扱い、独自式は追加しない |
| statement / branch / condition / MC/DC | instrumentationまたはCFGがあればCoverage計算、solverを使えば入力探索も可能 | コード解析環境、対象レベル選択 | 自動化可能だが現在のSkill責務外 |
| symbolic / concolic execution | path constraint生成とsolverによる入力生成 | 実行環境・モデル化・oracle | 自動化可能だが現在のSkill責務外 |
| mutation testing | mutation生成、実行、mutation score | surviving mutantの意味判断 | 自動化可能だが現在のSkill責務外 |
| visual regression | screenshot差分・閾値判定 | 意図した見た目変更かの判断 | 自動化可能だがテスト技法生成ではなく実行領域のため対象外 |
| accessibility checker | DOM / accessibility treeの規則検査 | 製品要件・例外・UX妥当性 | 自動化可能だが実行検査はE2E / 専用tool側。設計側は候補生成のみ |
| Error Guessing | 過去不具合等から候補を検索することは可能 | 故障仮説の発見・優先度判断 | 決定論的generator対象外 |
| Exploratory Testing | charter templateや既知リスクの提示 | 探索・観察・次行動の判断 | 決定論的generator対象外 |
| Checklist-Based Testing | catalogから候補を引く | 対象への関連性・期待結果 | UI pattern等の候補検索に限定 |
| リスク発見 | 既知カテゴリとの照合 | 何が製品上の失敗になるか | LLM / 人間 |
| 期待結果の補完 | なし | 現在有効な仕様根拠から確定 | 自動化しない |

## 4. 今回の実装範囲

このbranchでは、現在のテスト分析・設計・カバレッジ責務へ自然に収まるものを実装対象とします。

実装対象は次です。

1. `test-analysis`
   - 確定済みリスク値からのリスクレベル算出
   - 正規化済み問題構造からの技法候補判定

2. `test-condition-design`
   - 同値分割の構造検査と代表値候補
   - BVA
   - Decision Table
   - 全組合せ / Pairwise / N-wise
   - Classification Tree展開
   - 状態 / 遷移 / transition-pair
   - 明示flowのpath列挙
   - Cause-Effect GraphからDecision Tableへの展開
   - 有限domain制約の成立可能性
   - schema / grammar由来のテストデータ候補
   - UIコントロール別の確認候補

3. `coverage-analysis`
   - 追跡グラフの閉鎖性
   - 孤立 / 欠落 / 未知参照
   - 技法別Coverage集計

## 5. 今回実装しないもの

次は自動化可能ですが、現在のリポジトリ責務を広げるためこのbranchでは実装しません。

- Property-Based Testingのruntime
- fuzzing engine
- Differential Testing runner
- symbolic / concolic execution
- statement / branch / MC/DC instrumentation
- mutation testing
- visual regression runner
- accessibility実行checker
- 対象プロダクトへテストコードを自動実装する汎用generator

必要になった場合は、既存E2E Skillまたは別Skill / 別Issueとして扱います。

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
