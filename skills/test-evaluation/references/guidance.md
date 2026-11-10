# Test Evaluation guidance

## 責務境界

| 事項                                       | 正本owner                                                                                 | 本Skill                                          |
| ------------------------------------------ | ----------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 元実績・正式テスト結果・承認               | 各source owner / 権限者                                                                   | 読取り・参照のみ。書き換えない                   |
| 計画・予算・資源・実行順序の改版           | `test-management`                                                                         | 改版依頼とその結果の参照                         |
| テスト方式・環境・品質特性の改版           | `test-architecture-design`                                                                | 改版依頼とその結果の参照                         |
| 正式TR / TCN / CI / TCの改版               | 元の設計owner（`test-requirement-design` / `test-condition-design` / `test-case-design`） | 改版依頼とその結果の参照                         |
| 継続QA知識                                 | `qa-knowledge`                                                                            | 再利用候補の引渡しだけ。登録は改善の実施ではない |
| Agent Skill自体の品質・Skill構成の効率比較 | `EVALS.md`                                                                                | 扱わない                                         |
| リリース承認・プロジェクト終了の決定       | 権限者                                                                                    | 代行しない                                       |

## 1. 評価の入力と固定

統合報告snapshot、計画と予実、欠陥・Risk・coverage、工数・期間・再作業、前回改善と引継ぎ状況を入力とする。各入力は`ref`・`revision`・`content_hash`で固定し、`verify-inputs`で再取得した現在値と比較する。旧版・欠落した入力があればstaleまたは未検証とし、評価を`provisional`にする。

## 2. 5軸と指標

案件QA活動の評価軸は、利用者が確定した次の5軸（Q08）とする。

| 軸                               | 指標の候補                                                                         | 注意                                                                     |
| -------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `traceability`（追跡性・網羅性） | 独立した母集団に対する機能・仕様・TR / TCN / CI / TCの対応、未分類・未確認数       | 分母・版・対象外理由を固定。発見済み候補の対応率と全機能発見を混同しない |
| `quality`（設計・実行品質）      | 独立レビューで見つかった誤り、期待結果の根拠欠落、実行の誤判定、再現可能な欠陥検出 | 欠陥件数の多寡だけで品質を決めない                                       |
| `efficiency`（効率）             | 同一範囲の人手・Agent時間、差戻し・再作業、変更後の再検証時間                      | 環境・対象・品質条件を揃えて比較。未測定なら明示                         |
| `process`（プロセス）            | 必要成果物の現在性、承認・変更履歴、blocked・再開、完了条件の再現性、保管・引継ぎ  | CI PASSだけで完了としない                                                |
| `reusability`（再利用・導入）    | 案件間で変更せず使えた範囲、導入作業、利用先の制約                                 | 実証していない範囲へ一般化しない                                         |

「効果」は品質・追跡性の軸、「保守・再利用」は再利用性、「引継ぎ」はプロセスと`handoff`、「改善」は改善lifecycleで扱う。独自の総合点を作らない。

各指標は`axis`、`definition_version`、`unit`、`numerator` / `denominator` / `value`、`direction`、測定元`source_refs[]`（ref・revision）、測定条件`conditions`（`scope_ref` / `environment_ref` / `population_ref`）を持つ。`evaluate-axes`は次のように分類する。

- `unmeasured`：値・測定元・分母がない。理由が必須で、0として扱わない。
- `not_comparable`：前回の指標と定義版・単位・測定条件が異なる。改善・悪化として扱わない。
- `improved` / `worsened` / `unchanged`：比較可能な前回値との差を`direction`で判定。
- `measured`：前回値のない初回測定。基準であり改善ではない。

主張（`claims[]`）は、その軸の比較可能な指標で支えられる場合だけ採用する。作業時間の短縮（効率）だけで品質・追跡性の改善を主張しない。軸内に悪化した指標があれば「改善」を採用しない。

## 3. 改善のlifecycle

`proposed` → `adopted` → `handed_off` → `implemented` → `measured_effective` / `measured_no_effect` / `measured_worsened` / `not_comparable` / `not_measurable`（`rejected`は引継ぎ前のみ）。`advance-improvement`が各eventを検証し、段階の飛ばしを拒否する。

1. `adopt`：信頼できる承認サービスで認証され、改善ref・提案revision・scopeに一致し、有効期間内の承認が必要。
2. `handoff`：`change_kind`に対応するownerへ引継ぐ（`plan`→`test-management`、`architecture`→`test-architecture-design`、`design`→元設計owner）。依頼refと更新前revisionを記録する。
3. `implement`：ownerが当該依頼・採用に紐づく新revisionを`applied`として記録した場合だけ。revisionが変わらない、依頼・採用・ownerが一致しない、適用済みでない場合は実施済みにしない。実変更がなければ未実施の理由を残す。
4. `measure`：新revisionを適用した後に始まった別の活動から、同じ測定条件の指標を取得する。同じ活動、旧revision、実施前の活動は使えない。測定結果は`measured_effective`（改善）、`measured_no_effect`、`measured_worsened`、`not_comparable`、`not_measurable`に分類する。
5. `knowledge_registered`：Knowledge候補の記録のみ。状態を進めない。

`summarize-improvements`の達成数は`measured_effective`だけ。未承認・承認済み未実施・実施済み未測定・比較不能・効果なし・悪化は達成数に含めず、未完了の改善は一覧にする。

## 4. 保管・引継ぎ

`handoff-status`は、各項目に受領者と、項目・revisionに束縛された認証済み確認（信頼できる承認サービス由来）がある場合だけ`closed`とする。確認がない項目は未完了として列挙する。

## 5. 計画改版の影響

改善で計画等が改版されたら、`propagate-change`で依存関係を辿り、影響するアーキテクチャ・Risk・実行準備だけを再確認対象にする。無関係なcurrent成果物は維持する。

## 6. 停止条件

- 入力や承認が不足する指標・改善だけを未測定・blockedにし、評価できる軸の作業を続ける。
- 元実績の改変、リリース承認・プロジェクト終了決定の代行、Skill構成の効率判定は行わない。
- secret・個人情報を転載しない。保存はcreate-if-absent / expected revision CAS / readbackが可能な場合だけで、能力がなければ保存をblockedにする。
