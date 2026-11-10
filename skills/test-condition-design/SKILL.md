---
name: test-condition-design
description: テスト要求を条件・観点へ展開し、同値分割、境界値・Domain、Decision Table、状態遷移、CRUD、組合せ・分類木、文法、schema/UI、Random、Metamorphic等のカバレッジ基準と項目を定義するSkill。候補母集団と扱いを管理し、テストケース設計前に必要なカバレッジを具体化するときに使用する。
---

# テスト観点・条件設計

## 実行契約

1. テスト要求を「どの条件・観点で検証するか」へ展開し、実行手順は`test-case-design`へ委ねます。
2. 複数候補を持つ場合は候補母集団を先に識別し、カバレッジ基準、カバレッジ項目、採用しない候補の扱いを明示します。test itemと共通condition候補があるformal_designでは全item×condition pairを明示評価します。採用時はitemごとに別TCNへ接続し、候補CIと共通condition IDを混同しません。
3. 期待挙動をプロダクトリスクやテスト仮説から創作しません。
4. カバレッジ設計の基本手順、閉鎖、扱い、停止条件、最低品質は`references/guidance.md`に従います。
5. runtime dispatch表にある技法を適用する場合は`references/coverage-techniques.md`を読み、対応する技法の規則を使います。複数技法を採る場合やadapterからchild modelへ渡す場合も、各ownerの契約を確認します。
6. 既定出力形式が必要な場合は`assets/output-template.md`を使用します。
7. 他Skillを参照するときは正規Skill名を使用します。
8. 最終出力前に、実際に利用した入力が本Skillの入力契約を満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成した成果物へ本Skill自身の出力契約・品質ゲートを適用して自己検証します。明白かつ局所的で新しい領域固有の判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。自己検証を理由にカバレッジ戦略を根本から再設計したり、未定義の期待結果や期待結果の根拠を追加したりしません。仕様根拠不足、上流判断不足、他Skillの領域固有ロジックが必要な問題は推測補完せず既存の停止条件・ブロック中・ルーティングに従います。最終確認後も本Skill自身の契約違反が残り、既存の停止条件・ブロック中・ルーティングに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。自己検証の経緯や修正回数は出力しません。

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

## item × 共通conditionの正式適用

`condition_structure`内のformal design validatorはTI／COND candidateの参照とrevision、全pairの明示判定、テストレベル優先順位、期待結果候補のAuthority・観測方法・副作用を検証します。test levelはpacket全体の単一値にせず、TRへ対応するitemごとに解決し、採用pair・TCN・対応TRの割当が一致することを確認します。current revisionのchange reasonとrevision 1から直前revisionまでの連続履歴を要求し、履歴の各candidate retirementと理由を保持してID再利用を拒否します。採用pairだけ既存のTCN draftへ投影し、item_ref・condition_ref・formal design revision・期待結果candidate refsをTCN Entityへ保持します。全pair判断、候補、source revision、履歴、retirement reasonは`payload.formal_design_record`へ保持します。採用しない候補は対象外、別テストレベル、重複、未確認、blockedを区別します。sourceがstale／unknownなら、そのsourceに依存するpairとduplicate経由で依存するpairだけをblockedにし、影響しないpairの判断と既存IDを維持します。stale pairのTCN／model draftが既存IDのreuseを指定している場合、update scope内でもそのIDのlifecycle履歴を削除せず保持しますが、freshness未確認のTCN／model Entityは現行成果物に出力しません。明示的なzero-scope terminalは既存の削除契約に従います。依存関係が不明ならpacketを安全に利用可能と推測しません。候補母集団が不完全、unconfirmed／blockedが残る、分母が0のときはcoverageをcomplete／100%へ昇格しません。

adopted pairのTCN draftが参照する追加Authorityは、pair単位のcanonical `tcn_authority_refs`としてformal design recordへ保存します。入力値がdraftとともにある場合は一致を検証し、入力にない場合は存在する検証済みdraftから取得します。coverage validatorも同じ参照集合をpair dependencyへ加え、source revision／currentnessに基づき同じpairだけをblockedにします。partial rerunでdraftがなく、packetにも参照集合がないpairは依存関係未検証としてunresolvedにします。旧recordは読めますが、`tcn_authority_refs`がないadopted pairをcurrentな完全成果物として扱いません。

formal_designのitem／condition source refsは固定fixtureで局所検証できます。実owner artifactのID・revision・currentness照合と保存readbackは、owner統合時のPR #22確認事項です。

## インターフェース

- **入力**: 何を検証するかが明確なテスト要求または同等の成果物。現在有効な仕様根拠、プロダクトリスク、状態モデル / 業務ルール等は利用可能な場合に補助入力とします。
- **処理**: テスト要求を検証条件へ展開し、問題構造に合う技法、カバレッジ基準、カバレッジ項目、採用しない候補の扱いを定義します。
- **出力**: テスト条件、適用技法、カバレッジ基準、必要なカバレッジ項目、関連テスト要求 / 仕様根拠 / プロダクトリスク、優先度、テスト要求とカバレッジ候補の扱いを作ります。

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
