# QAワークフロー オーケストレーション詳細

## 目的

複数QA Skillを成果物ベースでルーティングし、開始点、再利用、ブロック中 / 再開、変更伝播、修正先、ワークフロー全体状態を管理します。

工程固有の判断規則は担当Skillを正本とし、本ガイダンスへ複製しません。

## 入力

必須:

- ユーザー要求
- 要求する最終成果物
- 識別可能な対象範囲

利用可能なら情報源、既存QA成果物、案件コンテキスト、進行モード、既知のブロック中 / 残存リスク / `要再検証`状態、正本一覧も使います。

情報源や既存QA成果物がまだないこと自体は`qa-workflow`の起動を妨げません。担当Skillへルーティング後、そのSkillの必須入力を満たさない範囲をブロック中として扱います。

## ランタイム前提

全体ワークフローでは次の14 Skillが同一のAgentクライアント上で利用可能であることを前提とします。

- `qa-workflow`
- `spec-analysis`
- `question-analysis`
- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`
- `adversarial-review`
- `e2e-test-inspection`
- `e2e-test-implementation`
- `e2e-test-execution`
- `e2e-test-result-analysis`
- `e2e-test-reporting`

Agent Skills Specificationは共通Skill-to-Skill呼び出しAPIを規定しません。本ワークフローは、Agentクライアントが必要なSkillを追加で読み込み / 利用できる実装で動作することを前提とします。

必要Skillを利用できない場合は、そのSkillの責務を別Skillへ肩代わりさせず、必要範囲をブロック中として扱います。

## 工程固有ロジックの正本

| 工程固有ロジック | 担当Skill |
| --- | --- |
| 現在有効な仕様根拠の解決 | `spec-analysis` |
| 不明点分類 / 回答正規化 | `question-analysis` |
| プロダクトリスク / リスクマトリクス / 設計深度 | `test-analysis` |
| テスト要求粒度 / 上流閉鎖 | `test-requirement-design` |
| カバレッジ基準 / カバレッジ項目 / テスト技法 | `test-condition-design` |
| 詳細テストケース / 期待結果の根拠の具体化 | `test-case-design` |
| カバレッジ / 閉鎖性 / ギャップ | `coverage-analysis` |
| 独立レビュー / 重大度 | `adversarial-review` |
| E2E対象、repo / 実対象の事実、実装可能性、安全条件 | `e2e-test-inspection` |
| Playwright E2Eコード変更、静的 / 軽量検証 | `e2e-test-implementation` |
| 実行安全確認、準備、Playwright実行、構造化結果、cleanup | `e2e-test-execution` |
| 実行事実からの原因分析、追加証拠要求、修正routing | `e2e-test-result-analysis` |
| 検証済み結果の人間向け報告 | `e2e-test-reporting` |
| ルーティング / ブロック中 / 再開 / 変更伝播 / 完了 | `qa-workflow` |

### 現在有効な仕様根拠への依存

製品期待挙動の現在有効な仕様根拠が必要な場合は、`spec-analysis`の有効成果物を使用します。

既存`spec-analysis`成果物が対象範囲の現在有効な仕様根拠を十分に解決していない、古い、または競合を残している場合は`spec-analysis`へ戻します。

`qa-workflow`自身は、SPEC / DECISION / ASMの優先関係、バージョン選択、情報源優先順位、仕様根拠の競合解消を行いません。

### その他の工程固有ロジックへの依存

- プロダクトリスクの採点が必要 → `test-analysis`
- テスト要求の粒度判断が必要 → `test-requirement-design`
- BVA / Pairwise / 状態遷移等の具体カバレッジ判断が必要 → `test-condition-design`
- テストケースの期待結果の根拠 / 具体性判断が必要 → `test-case-design`
- カバレッジ判定が必要 → `coverage-analysis`
- 重大度付き独立レビューが必要 → `adversarial-review`

## 成果物チェーン

```text
現在有効な仕様根拠
  ↓
テスト要求
  ↓
テスト条件
  ↓
カバレッジ項目
  ↓
テストケース
  ↓
カバレッジ分析
```

プロダクトリスクは深度・優先度の横断入力です。反証レビューは各成果物層に適用できます。

## E2E要求時の分岐

全14 Skillを固定順に実行しません。要求成果物と有効な成果物から必要な依存だけを選びます。

- 詳細TCからE2E実装: `e2e-test-inspection` → `e2e-test-implementation` → `adversarial-review`（対象: `E2E実装`） → `coverage-analysis`（対象: `TC → E2E実装`）
- TCなしの明示E2E対象 / 既存E2E更新: 確認済みinspection情報がなければ `e2e-test-inspection` → `e2e-test-implementation`。E2E対象選定が要求されない限り`test-analysis`を必須にせず、TC生成のためだけに`test-case-design`へ戻さない
- 既存E2Eの実行だけ: `e2e-test-execution`から開始できる。実行安全条件を確認できない場合だけinspectionへ戻す
- 設計からE2E実行: 既存の設計経路 → `e2e-test-inspection` → `e2e-test-implementation` → E2E実装のreview / coverage → `e2e-test-execution`
- 実行異常、未実行、run-level error、cleanup失敗 / 未確認、明示分析要求がある場合: `e2e-test-result-analysis`。正常runかつ分析要求なしなら省略できる
- 追加実行が必要な場合: result-analysisはPlaywrightを直接起動せず、仮説・取得証拠・範囲を示して`e2e-test-execution`へ戻す
- 確定済み結果の報告だけ: `e2e-test-reporting`から開始できる。reportingは原因再判定や仕様再解釈をしない

`e2e-test-inspection`、`e2e-test-implementation`、`e2e-test-execution`等のPlaywright固有契約は各Skillを正本とし、本Skillへ複製しません。

## 状態と完了

状態表の一意性はSkill名ではなく`(Skill, 対象 / 実行範囲)`で判定します。複数用途Skillの正規対象は次です。

| Skill | 正規対象 / 実行範囲 |
| --- | --- |
| `test-analysis` | `テスト分析` / `E2E対象選定` |
| `coverage-analysis` | `テスト設計` / `TC → E2E実装` / `E2E実装 → 実行結果` |
| `adversarial-review` | `テスト設計成果物` / `E2E実装` |

単一用途Skillの対象欄は空欄にできます。開始Skill、最終Skill、`question-analysis`回答後の再開Skillが複数用途Skillなら対象 / 実行範囲も必須です。

ワークフロー完了は全E2E結果がPASSであることを意味しません。要求された実行・分析・報告が完了し、必要なcleanup確認、未処理ブロッカー、`要再検証`、未実施の必須実行が残っていないことを判定します。FAILでも、必要な分析・報告と安全なcleanupが完了し、追加修正が要求されていなければ完了できます。

全体ワークフローでは、対象範囲内の上流項目を無言で消しません。各担当Skillが定義する下流成果物または妥当な扱いへ閉じていることを、ワークフロー全体状態として確認します。

## 共通の扱い

### `対象外`

ユーザー、案件コンテキスト、または現在有効な対象範囲から外れる根拠がある場合に使用します。低プロダクトリスクだけを理由に使用しません。

### `別テストレベル`

現在レベルでは適切に検証できず、より適切なテストレベルを説明できる場合に使用します。

### `残存リスク`

対象範囲内だが意図的に未カバーとする場合に使用します。理由、関連プロダクトリスク、未カバー内容を明示します。

### `ブロック中`

必要な仕様根拠、重大な矛盾、必須入力不足等により、妥当な設計判断を確定できない範囲に使用します。

工程固有の扱い（例: `成立不能`、`重複`）の詳細条件は担当Skillを正本とします。

## 開始点

要求成果物を作るために必要な、最も早い担当Skillから開始します。

例:

- 仕様整理だけ → `spec-analysis`
- 有効な仕様分析がありテスト重点を決める → `test-analysis`
- 有効なテスト条件 / カバレッジ項目がありケースだけ作る → `test-case-design`
- 成果物チェーンの抜け・閉鎖性を見る → `coverage-analysis`
- 成果物を重大度付きで独立レビューする → `adversarial-review`

常に`spec-analysis`から開始しません。

## 既存成果物の再利用

既存成果物は次を軽量確認して再利用します。

1. 現在の対象範囲に適合する
2. 関連上流成果物に対して陳腐化していない
3. 担当Skillの意味上の出力契約を満たす
4. 後続判断に必要な追跡情報がある
5. `要再検証` / ブロック中のまま利用可能扱いされていない

工程固有の妥当性が疑わしい場合は、詳細規則を`qa-workflow`で再評価せず担当Skillへ戻します。

## 既定フロー

```text
spec-analysis
  ↓
question-analysis
  ↓
test-analysis
  ↓
test-requirement-design
  ↓
test-condition-design
  ↓
test-case-design
  ↓
coverage-analysis
  ↓
adversarial-review
```

これは依存関係を理解するための既定経路です。要求成果物と有効な既存成果物に応じて途中から開始・終了できます。

## 進行モード

### `continuous`

既定モード。現在Skillの成果物が次工程へ利用可能で、局所ブロッカーがなければ要求成果物まで継続します。非ブロッカーは可視化したまま進めます。

### `gated`

ユーザーまたは案件コンテキストが指定した場合に使用します。現在Skillの成果物を提示した時点で停止し、次Skillを自動実行しません。

優先順位:

1. ユーザーの明示指示
2. 案件コンテキスト
3. `continuous`

## 不明点・矛盾のルーティング

どの工程でも、下流成果物の妥当性を阻害する未解決事項を発見した場合は`question-analysis`へ送れます。

分類自体は`question-analysis`を正本とし、`qa-workflow`は返されたブロック中範囲、継続可否、再開先をワークフロー状態へ反映します。

一部範囲だけがブロック中なら、妥当性を維持できる他範囲は継続します。

## 修正ルーティング

カバレッジ分析 / 反証レビュー等で欠陥を見つけた場合は、最も早い責任Skillへ戻します。

- 仕様モデル / 現在有効な仕様根拠 → `spec-analysis`
- 不明点 / 仮定 / 期待結果の根拠不明 → `question-analysis`
- プロダクトリスク / テスト重点 → `test-analysis`
- テスト要求 → `test-requirement-design`
- テスト条件 / カバレッジ基準 / カバレッジ項目 → `test-condition-design`
- テストケース → `test-case-design`
- カバレッジ判定自体 → `coverage-analysis`
- E2E対象選定の価値判断 → `test-analysis`（対象: `E2E対象選定`）
- E2E対象・repo / 実対象事実 → `e2e-test-inspection`
- Playwright E2E実装 → `e2e-test-implementation`
- E2E実装レビュー → `adversarial-review`（対象: `E2E実装`）
- TC → E2E実装追跡 → `coverage-analysis`（対象: `TC → E2E実装`）
- 実行条件、実行不足、状態準備、cleanup → `e2e-test-execution`
- E2E実行結果の原因分析 / 証拠不足 → `e2e-test-result-analysis`
- 確定済み結果の報告 → `e2e-test-reporting`

レビューSkill自身や`qa-workflow`が担当層を直接再設計しません。

## 上流変更の伝播

上流成果物の意味が変わった場合は、影響する下流成果物を`要再検証`として扱います。

1. 変更した最も早い成果物を特定する
2. 直接・間接に依存する下流の影響範囲を特定する
3. 影響範囲だけを担当Skillへ戻す
4. 担当Skillで再検証・必要修正する
5. カバレッジ確認が要求される場合は`coverage-analysis`を再実行する
6. 独立レビューが要求される場合は意味が変わった範囲を`adversarial-review`で再確認する

無関係な下流成果物まで全再生成しません。

## ワークフロー全体状態

- `完了`: 対象スコープ内にブロック中と`要再検証`が残らず、要求成果物の完了条件を満たす
- `部分完了（ブロック中あり）`: ブロック中以外は完了しているが、対象スコープ内に局所ブロック中が残る
- `ブロック中`: ブロック中により要求成果物について意味のある完了範囲を確定できない

## 全体ワークフロー完了条件

対象範囲について次を満たしたとき`完了`です。

- `spec-analysis`で必要な現在有効な仕様根拠が解決済み
- 対象内の上流仕様根拠 / プロダクトリスク / テスト要求 / テスト条件 / カバレッジ項目が、担当Skillの契約に従って下流成果物または扱いへ閉じている
- 各担当Skillの最低品質条件を満たす
- 必要な追跡性がある
- 出力テストケースが`test-case-design`の詳細テストケース完了条件を満たす
- 必要なカバレッジ分析 / 反証レビューが完了している
- `要再検証`が残っていない
- 対象スコープ内にブロック中が残っていない
- `adversarial-review`で利用停止が必要な未処置指摘が残っていない
- E2E要求時は、必要なE2E工程の実行・分析・報告・cleanup確認が要求範囲に対して閉じている
- logical primary / resolved primary TestCase / retry attemptが混同されていない

重大度の詳細条件や残存リスク受容条件は`adversarial-review`を正本とします。

## 品質ゲート

- オーケストレーション以外の工程固有ロジックを再定義していない
- 要求成果物に対して適切な開始Skillを選んでいる
- 有効な既存成果物を不要に再生成していない
- 必要Skillの欠如を別Skillで肩代わりしていない
- ブロック中を必要以上に全体へ広げていない
- 修正を最も早い責任Skillへ戻している
- 上流修正後の影響下流だけを`要再検証`している
- 完了判定が成果物の存在だけでなく状態・閉鎖性・各担当Skillの契約を見ている
- E2E固有の判断を`qa-workflow`へ複製していない

## 出力前自己検証

最終出力前に、実際に利用した入力が本Skillの入力契約を満たし、入力・仕様根拠・判断状態に停止条件へ該当する未解決状態がないか確認します。あわせて、生成したオーケストレーション成果物へ本Skillの出力契約と既存の品質ゲートを再適用します。品質基準は本ガイダンスの既存定義を正本とし、自己検証専用のルーブリックやチェックリストを別定義しません。

確認対象は開始Skill、既存成果物の再利用、ブロック中 / 再開、変更伝播、修正ルーティング、ワークフロー完了判定など、本Skillが所有するオーケストレーション契約に限ります。他Skillの工程固有ロジックを再評価・再設計しません。

1. 実際に利用した入力が入力契約を満たし、停止条件へ該当する未解決状態がないか確認する
2. 生成したオーケストレーション成果物が出力契約と既存の品質ゲートを満たしているか確認する
3. 明白かつ局所的で、新しい工程固有の判断を必要としないオーケストレーション契約違反だけを最大1回修正する
4. 修正後は修正箇所を含めて最終確認する。解消に新しい仕様根拠、上流判断、他Skillの工程固有ロジックが必要な場合は自力で補完せず、既存の停止条件・ブロック中・ルーティングに従う
5. 最終確認後も本Skill自身のオーケストレーション契約違反が残り、既存の停止条件・ブロック中・ルーティングに該当しない場合は、2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わない。現在残っている契約上の制約だけを明示する

既存の`ブロック中`定義を自己検証の未解消ローカル違反へ広げません。自己検証の実行経緯、修正回数、修正前状態、PASS / FAIL等の評価ログは通常成果物へ出力せず、現在有効な状態と未解消の契約上の制約だけを返します。
