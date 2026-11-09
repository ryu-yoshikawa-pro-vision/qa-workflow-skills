# テストアーキテクチャの判断基準

## 責務境界

architectureは複数レベル／方式をまたぐ担保構造を所有し、個別test caseや正式coverageを生成しません。

| 判断                                                          | owner                      |
| ------------------------------------------------------------- | -------------------------- |
| Product Risk・テスト深度                                      | `test-analysis`            |
| item／quality attributeごとのlevel・type・method・environment | `test-architecture-design` |
| E2Eを自動化する価値                                           | `e2e-test-selection`       |
| Playwright固有の実装可否                                      | `e2e-test-inspection`      |
| 正式TR／TCN／CI／TC                                           | 既存の設計Skill            |
| suite順・非Regression実行準備・予定source一覧                 | `test-management`          |
| Regression membership／Run                                    | `regression-testing`       |
| workflow route／実行state                                     | `qa-workflow`              |

Architectureで参照する既存Risk・仕様・testwareはowner ref／revisionを使い、内容を複製して第二の正本にしません。

## レベル割当と競合

各要求・target・品質特性について適用される情報を確認します。

1. 現在の案件／利用者による明示的なレベル指定を優先します。
2. 明示指定がなければ、scope／revisionが一致した承認済みarchitecture割当を使います。
3. どちらもない範囲に限り、既存`test-analysis`の既定システムテストを使います。

明示指定と承認済み割当が競合する場合、当該範囲だけ判断元へ戻し、どちらかを無断で上書きしません。複数のレベル／タイプが必要なら個別の分担行として保持します。同じtargetの異なるlevelは重複ではありません。

## 割当の設計

対象ごとに、根拠付きで次を定義します。

- level、type、method／technique responsibility、対象と検証分担
- environment、data、接続・権限、runner／tool、手動／自動の方式
- 観測方法、測定可能な非機能特性と閾値のsource
- owner、依存ref・revision、制約、未実装・別level・対象外・blockedの理由

閾値、環境、データ、権限、runnerが入力にない場合は未確定とします。UIがないAPI／batch／component対象や非機能品質特性を落としません。E2Eを選定したことからPlaywrightで実装可能とは推論しません。

## 変更影響

1. source revision・scope・承認状態を再取得します。
2. 変更したlevel／method／environment／dataの依存を特定します。
3. 影響するProduct Risk・正式設計・testware準備だけを要再確認として参照します。
4. 影響根拠がないcurrent成果物は維持します。影響が不明なら「影響なし」とせず該当scopeを保留します。
5. 変更後の依存revisionと下流owner／resume先を記録します。

割当とRisk評価の相互依存は、入力revisionが変わった範囲だけ再確認し、同じ条件の循環再評価をしません。

## 品質ゲート

- 各割当にtarget・requirement・根拠・owner・revision・scopeがある。
- 明示指定＞承認architecture＞既定system testの優先を守り、衝突を隠さない。
- 複数レベル・複数方式・非UI対象を個別行として保持する。
- 不足する環境／data／測定可能性を確定済みとしない。
- E2E価値、Product Risk、正式TCN／CI／TCの責務を奪わない。
- 改版時の再確認範囲と、currentのまま保持した無関係範囲を示す。
