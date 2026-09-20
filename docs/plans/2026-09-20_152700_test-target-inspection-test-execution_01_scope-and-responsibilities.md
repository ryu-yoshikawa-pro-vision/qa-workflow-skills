# テスト対象資料管理・テスト実行Skill追加Plan

## 1. 現状

`main@3510e6ffce87ba8c025ebde22f9947dbb6074f9c`では、次の14 Skillがあります。

```text
qa-workflow
spec-analysis
question-analysis
test-analysis
test-requirement-design
test-condition-design
test-case-design
coverage-analysis
adversarial-review
e2e-test-inspection
e2e-test-implementation
e2e-test-execution
e2e-test-result-analysis
e2e-test-reporting
```

通常のテスト分析・設計は`spec-analysis`から`adversarial-review`までで完了できます。Playwright E2Eが要求された場合は`e2e-test-inspection`以降のE2E Skillへ分岐します。

現在の`e2e-test-inspection`は、E2E実装前にrepo / workspaceと必要時の実対象を確認し、画面、経路、実在locator、非同期状態、Page Object、fixture、認証・データ等を調査します。ただし入力契約が詳細TC、明示E2E対象、既存E2E実装参照のいずれかであり、成果物の目的もPlaywright実装可否の確定です。

現在の`e2e-test-execution`はPlaywright runnerの安全な実行とraw fact収集を担当し、原因分析や一般的なTC実行判定は担当しません。

そのため次の2責務が不足しています。

- 自動化対象に依存せず、実対象を調査してテスト設計・実装・実行時に再利用する資料を作成・更新する責務
- テストケースを実行方式に依存せず実施し、期待結果と実測結果を比較してTC単位の結果を確定する責務

## 2. 追加するSkill

### `test-target-inspection`

実際のテスト対象を観測し、後続作業で参照するテスト対象資料を作成・更新します。

主責務:

- 対象画面 / 領域 / 経路の確認
- UI要素と操作可能性の確認
- role / accessible name / test id等の識別情報の確認
- 表示状態、loading / empty / error、modal等の状態確認
- 画面遷移、非同期状態、データ / 権限依存の確認
- 既存Page Object / fixture / helperとの対応確認
- 既存のテスト対象資料との差分確認と必要範囲の更新
- 確認元、確認日時、version / build、repo revision、未確認範囲の保持

担当しないこと:

- 現在有効な仕様根拠の決定
- 実装挙動から期待結果を確定すること
- テスト要求 / 条件 / ケースの設計
- 自動化対象選定
- Playwrightコード実装
- テスト実行結果のPASS / FAIL判定

### `test-execution`

詳細テストケースを実行し、期待結果と実測結果を比較してTC単位の結果を確定します。

主責務:

- 実行対象TCと実行範囲の確定
- 前提条件、テストデータ、環境、安全条件の確認
- `AI直接操作`による手順実施と観測
- `自動実行`で取得済みの検証済みrunner事実の利用
- 期待結果と実測結果の対応付け
- `PASS / FAIL / 未実行 / ブロック中`判定
- 証跡参照、未実行理由、cleanup / 残存状態の記録

担当しないこと:

- テストケースの期待結果を作り直すこと
- Playwright runner固有設定 / retry / reporter / raw result解釈の再実装
- 原因未確認のFAILを製品不具合と断定すること
- E2Eコードの修正
- テスト結果に合わせた仕様の再解釈

## 3. 責務境界

| 項目 | 担当Skill | 備考 |
| --- | --- | --- |
| 現在有効な仕様根拠 | `spec-analysis` | 実対象観測で上書きしない |
| 詳細テストケース / 期待結果 | `test-case-design` | 実行時の期待結果の正本 |
| テスト対象資料 | `test-target-inspection` | 必要時に作成・更新する補助成果物 |
| Playwright E2E実装前事実 | `e2e-test-inspection` | テスト対象資料を再利用可能 |
| Playwrightコード | `e2e-test-implementation` | 既存責務維持 |
| Playwright runner事実 | `e2e-test-execution` | 既存責務維持 |
| TC実行と期待結果比較 | `test-execution` | AI直接操作 / 自動実行に共通 |
| Playwright異常原因分析 | `e2e-test-result-analysis` | 既存責務維持 |
| Playwright固有結果報告 | `e2e-test-reporting` | 既存責務維持 |
| TCから実行結果への閉鎖性 | `coverage-analysis` | 新規比較対象を追加 |
| ルーティング / 完了 | `qa-workflow` | 2 Skillを正規Skillへ追加 |

## 4. `test-target-inspection` を既定フローへ固定しない理由

対象UIの構造情報がなくても、仕様と既存成果物だけで有効なテスト分析・設計を実施できる案件があります。常に実対象調査を要求すると、不要なbrowserアクセス、認証、環境準備、資料更新を増やします。

そのため`qa-workflow`では次の場合だけ利用します。

- ユーザーがテスト対象資料の作成・更新を要求した
- 後続Skillが実対象の構造情報を必要としている
- 既存資料の鮮度が不足し、実対象確認が必要
- UI変更等により既存資料の該当範囲が陳腐化した

既存資料が現在の対象範囲に対して十分であれば再利用し、更新のためだけに全対象を再調査しません。

## 5. 案件固有成果物の管理方針

`skills/test-target-inspection/assets/`はテンプレートを保持する場所であり、案件固有の生成物の保存先にはしません。

永続的な更新を要求された場合は次を入力として扱います。

- 保存先リポジトリ / workspace
- repo-relative pathまたはユーザーが指定した文書参照
- 更新対象の既存成果物（存在時）

保存先が指定されない、またはAgentに書込能力がない場合は、完成した資料を成果物として返すことはできますが、「管理済み」「更新済み」とは扱いません。保存先を推測して対象repoへ新規文書を作成しません。

既存文書を更新する場合は、既存の対象キーと未変更情報を可能な限り維持します。既定テンプレート外の人間記載セクションを無関係に削除しません。既存構造が曖昧で安全に差分更新できない場合は上書きせず、更新不能範囲を明示します。

## 6. テスト対象資料と仕様根拠の分離

テスト対象資料に記録する内容は、原則として次のいずれかです。

- 実対象で観測した事実
- repoで確認した実装事実
- ユーザー提供情報
- 未確認 / 確認不能状態

実対象で現在表示されている文言・状態・遷移を、それだけを根拠に`SPEC` / `DECISION`へ昇格させません。

期待結果との不一致を発見した場合は、テスト対象資料を仕様へ合わせて改変するのではなく、観測事実を保持したまま必要な場合は`question-analysis`やテスト実行結果へ渡します。

## 7. 安全境界

両Skillで共通して、以下を暗黙許可しません。

- productionや対象外originへの切替
- 削除、決済、メール / 通知送信、権限変更、共有データ更新等の高リスク副作用
- secret、cookie、token、storageState等の成果物への転載
- 指定外アカウントへのログイン
- cleanup方法未確認の破壊的操作

`test-target-inspection`は原則として観測・低リスク操作を優先し、副作用を発生させる必要がある範囲は許可を確認します。

`test-execution`はTCが要求る操作でも、環境・副作用・cleanup条件を確認できなければ該当TCだけを`ブロック中`または`未実行`とし、他の安全なTCまで一律停止しません。

## 8. 対象外

今回追加しません。

- 新しいbrowser automation framework
- Playwright以外のrunner adapter framework
- テスト管理SaaSへの自動登録
- 不具合管理システムへの自動起票
- 画像差分専用Skill
- API / DB専用の新規実行Skill
- テスト対象資料の独自DB / registry
- 自動的な案件横断knowledge base
- E2E既存5 Skillの統廃合
- 人間が手動実施した外部結果の取込専用workflow

現在の要求を満たすために必要になった場合だけ、既存Skillの入力として扱える範囲を実装します。
