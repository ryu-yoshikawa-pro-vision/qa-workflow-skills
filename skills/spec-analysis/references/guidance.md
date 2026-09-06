# 仕様分析 通常ガイダンス

## 目的

権威ある情報源とCanonical Registry上の有効Authorityを、後続QA設計で利用できる追跡可能な仕様モデルへ整理します。Test Requirement・Test Condition・Test Caseへ先回りしません。

## 入力

必須: 対象機能・挙動について、権威ある情報源またはCanonical Registry上の有効Authorityを1つ以上利用できること。

利用可能なら案件コンテキスト、情報源優先順位、対象範囲、正式用語、Canonical Decision / Assumption Registry、変更差分、Issue / チケット、実装情報、既存QA成果物も使います。

既存QA成果物と実装は補助証拠であり、自動的に仕様Authorityへ昇格させません。

## IDと情報分類

- `SPEC-xxx`: 権威ある情報源に明記された仕様
- `DEC-xxx`: 正式に確定した決定
- `INF-xxx`: 根拠はあるが未確定の推論
- `UNK-xxx`: 根拠不足で確定できない事項

`DEC-xxx`はCanonical Decision Registryの既存IDを参照し、同じ決定を別IDで再採番しません。

### `SPEC`

案件で権威ある情報源に明記され、対象Version / Scopeに適用される現行挙動です。

### `DECISION`

正式に確定した挙動です。Decisionの補足 / 上書き / 置換や他Authorityとの競合判断が必要な場合は`authority-resolution.md`を読みます。

### `INFERENCE`

証拠に基づく合理的解釈ですが、明記・確定されていない内容です。`SPEC`として扱いません。

### `UNKNOWN`

利用可能な根拠だけでは結論を出せない内容です。一般的慣習や類似製品挙動で埋めません。

## 情報源の基本判断

- 案件固有の優先順位が定義されている場合はそれを使う
- 全案件共通の固定情報源順位を作らない
- 実装が正本でない場合、仕様と異なる実装へ仕様を合わせない
- 既存Test Caseの期待結果を、それが既存ケースに書かれているという理由だけで`SPEC`にしない
- 重大な情報源競合や版差がある場合は`authority-resolution.md`でCurrent Effective Authorityを解決する

## 手順

1. 対象機能、変更、画面、ユーザー / ロール、業務フロー、明示対象外を整理する
2. 実際に使用した情報源 / Canonical Registryを追跡可能な粒度で記録する
3. 対象範囲に関係する独立したルール・挙動を抽出する
4. `SPEC` / `DECISION` / `INFERENCE` / `UNKNOWN`を分類する
5. 必要な範囲でCurrent Effective Authorityを解決する。複数Authority等の詳細判断が必要なら`authority-resolution.md`を読む
6. 権威ある情報源の正式用語を維持する
7. 必要に応じて権限、表示、上限、条件分岐、優先順位等の業務ルールを構造化する
8. 意味のある状態がある場合だけ状態 / 遷移を整理する
9. 順序に意味がある場合だけ業務フローを整理する
10. 明示された境界、形式、件数、サイズ、日時、権限、性能、整合性等の制約を抽出する
11. `INFERENCE` / `UNKNOWN` / 矛盾を根拠と影響範囲付きで保持する
12. 内部整合性を確認する

文章1文ごとに機械分割せず、意味が異なるルールを件数削減目的で統合しません。未定義の境界を創作しません。

## 出力

必要に応じて次を表現します。

- 分析範囲 / 制約
- 使用した情報源 / Canonical Registry
- 分類と一致する安定IDを持つ分析項目
- Current Effective Authorityの正規化ビュー
- 業務ルール
- 状態 / 遷移
- 処理 / 業務フロー
- 明示的制約 / 境界
- 重大な矛盾 / 不明点
- 後続Skillへの補足

対象範囲内の現在有効な期待挙動は、情報源またはCanonical Registryへ追跡できなければなりません。

## 停止条件

次の場合、影響範囲をBlockedとします。

- Authority候補となる権威ある情報源またはCanonical Registry上の有効Authorityがない
- 対象範囲を意味のある程度に特定できない
- 必要資料 / Registryへアクセスできず信頼できる分析が成立しない
- Current Effective Authorityを解決できない重大競合がある

軽微な欠落、非Blockerの`UNKNOWN`、明示した推論、一部範囲だけの矛盾では全体停止しません。

## 品質ゲート

- IDが分類と一致している
- `DEC-xxx`を重複採番していない
- `SPEC`が権威ある根拠に支えられている
- `INFERENCE`を事実扱いしていない
- `UNKNOWN`を一般論で埋めていない
- 実装差分に合わせて仕様を書き換えていない
- 既存テストを仕様Authorityにしていない
- Current Effective Authorityが必要な範囲は解決済み
- 対象範囲内の現在有効な期待挙動が根拠へ追跡できる
- 関係のない周辺機能を追加していない
- 下流QA設計へ先回りしていない

## 次の担当Skill

- 不明点・矛盾の分類が必要 → `question-analysis`
- テスト重点・Product Risk分析が必要 → `test-analysis`

実際のroutingは`qa-workflow`へ委ねます。

## 出力前自己検証

最終出力前に、実際に利用した入力が本SkillのInput Contractを満たし、入力・Authority・判断状態に停止条件へ該当する未解決状態がないか確認します。あわせて、生成した成果物へ本SkillのOutput Contractと既存の品質ゲートを再適用します。品質基準は本ガイダンスの既存定義を正本とし、Self-Validation専用のrubricやチェックリストを別定義しません。

1. 実際に利用した入力がInput Contractを満たし、停止条件へ該当する未解決状態がないか確認する
2. 生成した成果物がOutput Contractと既存の品質ゲートを満たしているか確認する
3. 明白かつ局所的で、新しいDomain判断を必要としない契約違反だけを最大1回修正する
4. 修正後は修正箇所を含めて最終確認する。解消に新しいAuthority、上流判断、他SkillのDomain Logicが必要な場合は自力で補完せず、既存の停止条件・Blocked・routingに従う
5. 最終確認後も本Skill自身の契約違反が残り、既存の停止条件・Blocked・routingに該当しない場合は、2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わない。現在残っている契約上の制約だけを明示する

Authority不足、競合、未確定情報をSelf-Validationの名目で`SPEC` / `DECISION`へ昇格させません。既存の`Blocked`定義を未解消ローカル違反へ広げません。Self-Validationの実行経緯、修正回数、修正前状態、PASS / FAIL等の評価ログは通常成果物へ出力せず、現在有効な状態と未解消の契約上の制約だけを返します。
