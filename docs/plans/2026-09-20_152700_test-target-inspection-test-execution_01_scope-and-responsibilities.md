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

詳細テストケースを実行し、期待結果と実測結果を比較してTC単位の結果を確定します。現スコープでは、利用可能なbrowser / computer操作能力で実対象UIを操作・観測できるTCと、既存Playwright E2Eで実行できるTCを扱います。API / DB等の専用実行基盤は本変更の対象にしません。

主責務:

- 実行要求を、入力側で既に存在する一意識別子を使って具体的なTC集合へ解決し、今回の実行母集団を開始前に確定。TCは`qa-workflow`成果物、外部成果物、ユーザー直接入力のいずれでもよい。既存TC IDや外部システムの一意識別子を再利用し、`test-execution`自身が正式TC IDを創作しない
- 前提条件、テストデータ、事後状態 / 後処理、環境、安全条件の確認
- `AI直接操作`による手順実施と観測
- `自動実行`で取得済みの検証済みrunner事実の利用
- 期待結果と実測結果の対応付け
- `PASS / FAIL / 未実行 / 判定不能`判定
- 証跡参照、未実行理由、TCに定義された事後状態 / 後処理、実行時cleanup / 残存状態の記録

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
| 詳細テストケース / 期待結果 | `test-case-design` | workflow内で設計・変更する責任Skill。外部成果物 / ユーザー直接入力の既存期待結果は今回実行の契約として利用可だが仕様Authorityへ昇格しない |
| テスト対象資料 | `test-target-inspection` | 必要時に作成・更新する補助成果物 |
| Playwright E2E実装前事実 | `e2e-test-inspection` | テスト対象資料を再利用可能 |
| Playwrightコード | `e2e-test-implementation` | 既存責務維持 |
| TC → E2E実装の追跡関係 | `coverage-analysis`（対象: `TC → E2E実装`） | 対応の欠落・陳腐化を`test-execution`で推測補完しない |
| E2E実装の期待結果 / assertionレビュー | `adversarial-review`（対象: `E2E実装`） | TC PASS根拠に使う場合は対象E2E実装revision / working treeとの対応を追跡する |
| Playwright runner事実 | `e2e-test-execution` | 既存責務維持 |
| TC実行と期待結果比較 | `test-execution` | AI直接操作 / 自動実行に共通 |
| Playwright異常原因分析 | `e2e-test-result-analysis` | 既存責務維持 |
| Playwright固有結果報告 | `e2e-test-reporting` | 既存責務維持 |
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

保存先が指定されない、またはAgentに書込能力がない場合は、完成した資料を成果物として返すことはできますが、「管理済み」「更新済み」とは扱いません。保存先を推測して対象repoへ新規文書を作成しません。ユーザー要求が資料案の作成だけならこの返却で完了できますが、永続的な作成・更新自体が要求成果物なら、保存先不明、書込不能、安全な差分更新不能、保存後不整合が残る範囲を完了扱いにしません。

`test-target-inspection`は保存したテスト対象資料の場所・範囲・鮮度 / バージョンを返します。`qa-workflow`を利用している場合だけ、`qa-workflow`が既存の`skills/qa-workflow/assets/project-context-template.md`にある`既存QA成果物`欄へその情報を反映します。`test-target-inspection`単体利用では案件コンテキストを変更しません。新しいregistry / DBは追加しません。

既存文書を更新する場合は、正規テンプレートまたは構造的に互換性を確認できる資料だけを自動差分更新の対象とし、既存の対象キーと未変更情報を可能な限り維持します。既定テンプレート外の人間記載セクションを無関係に削除しません。任意形式の文書を汎用的に解析・mergeする仕組みは追加しません。既存構造が曖昧で安全に差分更新できない場合は上書きせず、更新不能範囲を明示します。

永続更新では、更新候補を作成した元成果物のrevision / content identityを保持し、保存直前に対象成果物が同じ元状態のままか再確認します。変更済みなら古い候補で上書きせず、最新内容を再読込して候補を作り直します。新しいlockやartifact registryは追加しません。

成果物の単位は、既存成果物があればその単位を維持します。新規作成では今回要求された調査範囲を1成果物の範囲とし、明示要求なしに製品全体へ拡張したり画面単位へ細分化したりしません。

## 6. テスト対象資料と仕様根拠の分離

テスト対象資料に記録する内容は、原則として次のいずれかです。

- 実対象で観測した事実
- repoで確認した実装事実
- ユーザー提供情報
- 未確認 / 確認不能状態

実対象で現在表示されている文言・状態・遷移を、それだけを根拠に`SPEC` / `DECISION`へ昇格させません。

期待結果との不一致を発見した場合は、テスト対象資料を仕様へ合わせて改変するのではなく、観測事実を保持します。現在有効な仕様根拠が明確なら、その不一致だけを理由に`spec-analysis`へ戻さず、実装観測と仕様根拠の差として後続へ渡します。どの仕様が有効か不明、仕様根拠同士が競合、期待結果の意味を確定できない場合だけ`question-analysis` / `spec-analysis`へ戻します。

現在有効なテスト対象資料は、`test-case-design`でUI名称、到達方法、実施手順、観測可能性等の補助情報として利用できます。ただしテスト対象資料を期待結果の仕様根拠にはしません。

## 7. 安全境界

両Skillで共通して、以下を暗黙許可しません。

- productionや対象外originへの切替
- 削除、決済、メール / 通知送信、権限変更、共有データ更新等の高リスク副作用
- secret、cookie、token、storageState等の成果物への転載
- TC判定に不要な個人データ・機密情報の成果物や証跡への転載
- 指定外アカウントへのログイン
- cleanup方法未確認の破壊的操作

`test-target-inspection`は観測・非永続操作を既定とします。永続的な副作用を伴う操作が必要な場合は、対象origin、許可範囲、最大回数、cleanup方法を確認してから実施します。実施した場合は操作内容、許可範囲、最大回数、実施回数、cleanup結果、残存状態を成果物へ記録します。再試行も実施回数へ含め、実施回数が最大回数を超えないことを確認します。これらを確認できない場合は操作せず、その範囲を`未確認`または`確認不能`として残します。inspectionであることを理由に副作用確認を省略しません。

`test-execution`はTCが要求する操作でも、環境・副作用・cleanup条件を確認できなければ該当TCを開始せず`未実行`とし、必要な条件が解消するまで`test-execution`の該当範囲をworkflow上`ブロック中`として扱います。実行開始後に必要な観測を完了できずPASS / FAILを確定できない場合はTCを`判定不能`とします。他の安全なTCまで一律停止しません。

`test-target-inspection`で`未確認`は今回確認対象だがまだ確認していない情報、`確認不能`は今回確認する必要があるがアクセス・権限・環境等により確認できなかった情報として区別します。要求範囲外の情報を`未確認`へ混ぜず、既存情報を保持するだけなら`既存資料から継承・未再確認`として扱います。今回確認すべき範囲に必要な`未確認`または`確認不能`が残り、要求資料を完成できない場合は、repo由来情報だけで`完了`にせず該当範囲をworkflow上`ブロック中`として扱います。

`test-target-inspection`は対象製品コード、Page Object、fixture、helper、既存テストコードを変更しません。永続的な書込は、ユーザーまたは案件が指定したテスト対象資料の作成・更新に限定します。実装修正が必要と判明した場合は観測事実として残し、責任Skillへroutingします。

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
