# テスト対象資料管理・テスト実行Skill追加Plan

## 1. 現状

`main@3510e6ffce87ba8c025ebde22f9947dbb6074f9c`では14 Skillがあります。既存の`e2e-test-inspection`はPlaywright E2E実装前の調査、`e2e-test-execution`は既存 / 実装済みPlaywright E2Eの安全なrunner実行とraw fact収集を担当します。

今回不足しているのは次の2責務です。

- **生きたテスト対象の現在情報を継続的に収集・確認・管理する責務**
- **人間の手動テスト相当の操作をAIが実施し、TC結果を報告する責務**

この2責務を`test-target-inspection`と`test-execution`として追加します。

## 2. 追加するSkill

### `test-target-inspection`

目的は、生きた実対象から現在のUI情報とふるまいを収集し、後続のテスト設計・実装・実行で再利用できる資料として管理することです。

主責務:

- 対象画面 / 領域 / 到達経路の確認
- UI要素、操作可能性、role / accessible name / test id等の確認
- 表示状態、loading / empty / error / modal等の状態確認
- 操作に対する反応、画面遷移、非同期状態、データ / 権限依存の確認
- DOM / accessibility tree等では確認できない視覚状態の画像確認
- レイアウト崩れ、重なり、欠け、表示位置、画像、canvas等の視覚情報の記録
- 既存資料がある場合、今回対象範囲を実対象と照合してcurrentか確認する
- 変更がある箇所だけ更新し、変更がない箇所も今回確認済みとして鮮度を更新する
- 確認元、確認日時、version / build、確認条件、未確認 / 確認不能範囲の保持
- POM / Page Object / fixture / helper等は、対象プロジェクトで利用されており後続作業に有用な場合だけ任意参照として記録する

担当しないこと:

- 実対象の現在挙動を仕様Authorityへ昇格すること
- テスト要求 / 条件 / ケースの設計
- 自動化対象選定
- POM / Page Object / fixture / helperの作成・更新
- Playwright E2Eコードの永続実装
- TCのPASS / FAIL判定

`test-target-inspection`は実対象への到達を基本とします。repo / workspaceだけを確認した結果は補助情報として利用できますが、実対象を確認していない範囲をcurrentなテスト対象情報として扱いません。

### `test-execution`

目的は、人間が手動テストで行うのと同様にAIが実対象を操作し、詳細TCを実施して、その結果をユーザーへ報告することです。

主責務:

- 入力側の既存一意識別子から今回実行するTC集合を固定する
- 実操作前に各TCをGherkinのGiven / When / Then構造を持つYAMLへ整理し、開始状態・操作・期待結果・観測方法の曖昧さを明示する
- 実行または合否判定に影響する未解決事項が残るTCは開始せず、解消条件を報告する
- 前提条件、テストデータ、role / アカウント、環境、安全条件を確認する
- Playwright MCP等の対話的なbrowser操作でTC手順を実施する
- 必要に応じてPlaywright CLIまたはPlaywrightコードを使って現在TCを実行する
- 今回の実行だけに必要な一時的Playwrightコードを最小限生成・実行する
- DOM / accessibility tree等による構造・意味情報の観測
- screenshot等の画像による視覚情報の観測
- 期待結果と実測結果を比較し、`PASS / FAIL / 未実行 / 判定不能`を確定する
- TCごとの手順・観測、判定根拠、証跡、後処理 / cleanup、残存状態を整理する
- **テスト実行結果を人間が判断できる形で報告する**

担当しないこと:

- 実行前YAMLを正本TCの代替にすること
- YAML化の過程で元TCにない前提・操作・期待結果を補完すること
- TCの期待結果を実測へ合わせて変更すること
- 実対象の現在挙動を仕様Authorityへ昇格すること
- 原因未確認のFAILを製品不具合と断定すること
- 将来も維持するrepo内Playwright E2Eコードを、実行だけの要求から暗黙に追加・更新すること
- 既存Playwright runnerのretry / reporter / process ownership等の契約を再設計すること

## 3. Playwrightコードとの境界

`test-execution`で許可するPlaywrightコード生成は、**今回のテスト実行を成立させるための一時的なコード**です。

例えば次を含みます。

- 対話操作だけでは安定して実施できない複数手順を、今回TC用の一時スクリプトとして実行する
- 同じ観測を複数データで繰り返すため、今回runだけで使用する最小コードを生成する
- screenshotや必要な観測値を取得するための一時コードを実行する

一方、次は既存E2E Skillの責務を維持します。

| 目的 | 担当 |
| --- | --- |
| 将来も維持するPlaywright E2Eをrepoへ実装 / 更新 | `e2e-test-inspection` → `e2e-test-implementation` |
| 既存 / 実装済みrepo E2Eを正式なrunner契約で実行 | `e2e-test-execution` |
| 既存E2E実行異常の原因分析 | `e2e-test-result-analysis` |
| Playwright runner固有のrun / attempt等の詳細報告 | `e2e-test-reporting` |
| 人間の手動テスト相当のAI操作とTC結果報告 | `test-execution` |

これにより、`test-execution`で一時コードを使えるようにしつつ、既存のE2E資産管理責務を重複させません。

## 4. 画像判断

両Skillで、必要な場合は画像を正式な観測元として使用します。

画像を使用する代表例:

- UI要素の重なり
- 文字やコンテンツの欠け / はみ出し
- レスポンシブ崩れ
- modal / popupの視覚的な表示状態
- 画像・アイコン・canvasの描画
- DOM / accessibility treeでは判断できない位置・サイズ・視覚状態
- TC期待結果が視覚的表示を要求している場合

構造情報と画像は役割を分けます。

- role、accessible name、DOM状態等はDOM / accessibility tree等を優先
- 見た目・配置・描画は画像を使用
- 必要なら両方を併用する
- 画像だけから仕様、role、accessible name等を推測しない

UI崩れ等をTC外で発見した場合は追加観測として報告できますが、元TCの期待結果に含まれない事象を理由なくTC FAILへ変換しません。

## 5. `test-target-inspection`の鮮度管理

既存資料がある場合でも、そのままcurrentとはみなしません。Skill実行時に今回対象範囲の実対象を確認し、既存情報と照合します。

今回対象範囲の各情報は最低限、次のいずれかへ閉じます。

- `今回確認・変更なし`
- `今回確認・更新`
- `今回確認・削除確認`
- `未確認`
- `確認不能`

要求範囲外の情報を無理に再確認しません。製品全体のfull scanを毎回要求するのではなく、**今回利用・更新する範囲についてcurrentか確認する**ことを必須にします。

既存情報を今回確認していない場合は、古い確認日時 / version / buildを保持し、currentとして更新しません。

## 6. 案件固有成果物の管理

`skills/test-target-inspection/assets/`はテンプレートだけを保持します。案件固有のテスト対象資料はユーザーまたは案件が指定した保存先で管理します。

永続更新では以下を守ります。

- 保存先が提供するSHA / revision / ETag等の条件付き更新を優先
- 利用できない場合は保存直前に再読込・比較
- 途中変更を古い候補で上書きしない
- 保存後に確認できる場合は保存内容を再読込して確認
- 新しいlock / artifact registry / 独自DBは追加しない

POM等の実装資産はテスト対象資料の保存対象とは別です。`test-target-inspection`からPOM等を書き換えません。

## 7. TC入力と結果

`test-execution`は`qa-workflow`成果物、外部成果物、ユーザー直接入力の詳細TCを受け付けます。

- 1つの成果物では1つのTC入力元 / snapshotを扱う
- 既存TC IDまたは外部システムの一意識別子を使用する
- 正式TC IDを新規創作しない
- 外部TCを内部QA成果物へ自動変換しない
- 実行開始後にTC集合を書き換えない
- TC追加 / 除外 / 実行手段変更があれば旧成果物を理由付きで閉じ、新しい成果物 / versionを開始する

TC結果は以下です。

- `PASS`: 必要な期待結果をすべて観測し、一致した
- `FAIL`: 有効な期待結果との不一致を実測した
- `未実行`: TC自体を開始していない
- `判定不能`: 開始したが必要な観測を完了できず判定できない

`ブロック中`はTC結果ではなくworkflow状態です。

## 8. 安全境界

両Skillで次を暗黙許可しません。

- productionや対象外originへの切替
- 削除、決済、メール / 通知送信、権限変更、共有データ更新等の高リスク副作用
- 指定外アカウントへのログイン
- cleanup方法未確認の破壊的操作
- secret、cookie、token、storageState等の記録・転載

副作用の最大回数は許可された操作scope全体で累計し、TCごとにリセットしません。

trace / screenshot / page snapshot / video / network等は必要最小限だけ取得し、機密情報を含む可能性がある証跡を自動共有・commit・転載しません。

## 9. 対象外

今回追加しません。

- 新しいbrowser automation framework
- Playwright以外のrunner adapter framework
- POM生成専用Skill
- 画像差分専用Skill
- API / DB専用の新規実行Skill
- テスト対象資料の独自DB / registry
- 自動的な案件横断knowledge base
- E2E既存5 Skillの統廃合

