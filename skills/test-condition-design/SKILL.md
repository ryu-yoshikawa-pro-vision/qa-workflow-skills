---
name: test-condition-design
description: テスト要求を条件・観点へ展開し、同値分割、境界値・Domain、Decision Table、状態遷移、CRUD、組合せ・分類木、文法、schema/UI、Random、Metamorphic等のカバレッジ基準と項目を定義するSkill。候補母集団と扱いを管理し、テストケース設計前に必要なカバレッジを具体化するときに使用する。
---

# テスト観点・条件設計

## 実行契約

1. テスト要求を「どの条件・観点で検証するか」へ展開し、実行手順は`test-case-design`へ委ねます。
2. 複数候補を持つ場合は候補母集団を先に識別し、カバレッジ基準、カバレッジ項目、採用しない候補の扱いを明示します。
3. Pairwise等で使う因子は、入力で指定された独立した条件だけにします。制約は因子名や因子値として追加せず、出力templateの`制約・備考`列へ記録します。
4. 期待挙動をプロダクトリスクやテスト仮説から創作しません。
5. カバレッジ設計の基本手順、閉鎖、扱い、停止条件、最低品質は`references/guidance.md`に従います。
6. runtime dispatch表にある技法を適用する場合は`references/coverage-techniques.md`を読み、対応する技法の規則を使います。複数技法を採る場合やadapterからchild modelへ渡す場合も、各ownerの契約を確認します。
7. 既定出力形式が必要な場合は`assets/output-template.md`を使用し、契約されている節・表ヘッダーを空データの場合も保持します。該当行がない表はヘッダーと区切り行を残して空にし、「該当なし」という本文だけへ置き換えません。
8. 他Skillを参照するときは正規Skill名を使用します。
9. 入力に必須値・境界値・遷移・制約が指定されている場合、runtimeの正規化結果と各Coverage Itemにそれぞれ対応する値・根拠を保持します。runtime結果に現れない必須値を省略せず、対応するCoverage Itemを作れない場合は対象をブロック中にします。テスト要求を実際に展開した場合は「テスト条件へ展開しないテスト要求」に重複記載せず、未展開の要求だけを許可されたDisposition値で閉じます。
10. Pairwise等の組合せ技法では、各生成組合せを実行可能な完全な因子割当として記載します。runtime targetに対応する行は`execution.row`の全因子値を使い、必要な因子対だけを含む`factor_assignment`を組合せ全体として転記しません。
11. 入力に因子・値・有限制約、具体的な境界値、または有効遷移が明示され、それらからcoverage構造を作れる場合は、入力由来の条件・Coverage Item候補を記録します。current Authority不足だけを理由に入力済みの組合せ・値・遷移を削除しません。期待する製品挙動が入力から確定できない場合は、Coverage Itemの期待挙動欄に「入力で条件のみ確認。期待挙動はcurrent Authority未解決」と記し、関連candidateとMachine Runtime target dispositionを`ブロック中`で閉じます。入力で分からない期待結果は追加せず、製品behaviorの検証が完了したとも主張しません。
12. 上記の入力由来Coverage Itemを作成した要求を「テスト条件へ展開しないテスト要求」へ重複記載しません。coverage modelが実際に出した条件・遷移・値を保持し、Coverage Itemに対応づけ、未解決の期待挙動は同じ項目へ追跡します。
13. 最終出力前に、実際に利用した入力が本Skillの入力契約を満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成した成果物へ本Skill自身の出力契約・品質ゲートを適用して自己検証します。明白かつ局所的で新しい領域固有の判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。自己検証を理由にカバレッジ戦略を根本から再設計したり、未定義の期待結果や期待結果の根拠を追加したりしません。仕様根拠不足、上流判断不足、他Skillの領域固有ロジックが必要な問題は推測補完せず既存の停止条件・ブロック中・ルーティングに従います。最終確認後も本Skill自身の契約違反が残り、既存の停止条件・ブロック中・ルーティングに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。自己検証の経緯や修正回数は出力しません。

## 決定論的runtime dispatch

`condition_structure`を親runtimeとし、各技法を次のSkill-local runtime unitへdispatchします。

| model_type                  | runtime_unit_key                         | 備考                              |
| --------------------------- | ---------------------------------------- | --------------------------------- |
| 同値分割                    | `equivalence_partitions`                 | パーティションと代表値            |
| 境界値 / ドメイン           | `bva` / `domain_testing`                 | 型・精度を保った境界              |
| デシジョン / 因果           | `decision_table` / `cause_effect`        | 実行可能ルール                    |
| CRUD / 文法                 | `crud_matrix` / `grammar_cases`          | 操作・文法の条件                  |
| 組合せ / 分類木             | `combinatorial` / `classification_tree`  | 制約付き2-wiseと木構造            |
| 状態 / フロー               | `state_transition` / `flow_paths`        | 有効遷移・経路                    |
| ランダム / メタモルフィック | `random_testing` / `metamorphic`         | 再現可能seed・関係                |
| スキーマ / UI               | `schema_cases` / `ui_pattern_candidates` | supported subsetとunsupported     |
| テストデータ要求            | `test_data_requirements`                 | targetと要件の交差                |
| materialize                 | `materialize_coverage`                   | current model結果からTCN/CIへ統合 |

すべてのruntimeは共通envelope、stable target ID、Machine Entity、freshnessを使用します。adapter childは親modelのgeneration fingerprintとderived child inputに依存し、親と同じ内容を独立再生成しません。`materialize_coverage`はcurrentかつdeterministicなruntime結果だけを統合し、unsupported / stale / legacy / semantic CI不足をcompleteへ昇格しません。

`materialize_coverage.py`の`models[]`は、current model runtimeのMachine Runtime Result envelopeと実行時metadataをSkill-local `runtime_contract.py::current_model_result_row(envelope, metadata)`へ渡した戻り値だけを使います。raw envelope、`runtime_unit_row()`の戻り値、Agent / LLMが手組みしたmodel resultは渡しません。

### 最終runtime evidence gate

最終成果物の直前にSkill-local `scripts/runtime_contract.py`の`operation=verify_runtime_evidence`へ、実際に使用したcanonical normalized inputとcandidate成果物全文、固定booleanの`partial_rerun`を渡します。full buildでは`partial_rerun=false`かつ`previous_artifact_markdown=null`、partial rerunではscope外Entityの有無にかかわらず`partial_rerun=true`と同一成果物系列の直前artifact全文を渡します。Disposition-onlyのscope外Entityもpreviousから検証するためです。判定やprevious Entity配列を手組みしません。返却`valid=true`の場合だけ完成として返し、`valid=false`は既存の最大1回の局所修正・最終確認契約へ統合し、未解決なら完成扱いしません。

## インターフェース

- **入力**: 何を検証するかが明確なテスト要求または同等の成果物。現在有効な仕様根拠、プロダクトリスク、状態モデル / 業務ルール等は利用可能な場合に補助入力とします。
- **処理**: テスト要求を検証条件へ展開し、問題構造に合う技法、カバレッジ基準、カバレッジ項目、採用しない候補の扱いを定義します。
- **出力**: テスト条件、適用技法、カバレッジ基準、必要なカバレッジ項目、関連テスト要求 / 仕様根拠 / プロダクトリスク、優先度、テスト要求とカバレッジ候補の扱いを作ります。

runtime targetが`ブロック中`となりCoverage Itemへmaterializeされない場合は、CI IDやactive CI Entityを創作せず、output templateの技法別runtime target候補表に入力由来の構造、target key、扱い、理由を残します。候補の構造的な網羅確認と、active Coverage Item / 製品挙動の確定を区別します。

優先度のenum欄に記載できる値は`高` / `中` / `低`です。入力に優先度や導出根拠がない場合は欄を空にし、`未提示`などの説明は備考欄へ記載します。

## 基本停止条件

- テスト要求の意味が曖昧で条件へ展開できない
- 現在有効な仕様根拠を解決できない
- 未承認推論で期待挙動を補わないと条件を作れない
- カバレッジ基準を定義するために不可欠な仕様がない

低リスクの追加観点が不明、任意のエラー推測仮説が不足、全組合せが巨大という理由だけでは停止しません。

## リソース

- カバレッジ設計の基本契約: `references/guidance.md`
- 技法固有のカバレッジ規則: `references/coverage-techniques.md`
- 既定出力形式: `assets/output-template.md`

`ui_pattern_candidates`を適用する場合は、`assets/ui-pattern-catalog.json`を参照し、同runtimeのcurrent結果にある`payload.catalog_version`と`static_data_versions.ui_pattern_catalog`、canonical `pattern_key`、candidate keyを根拠として保持します。カタログ候補は製品Authorityや期待結果の代わりにしません。
