# PR #220 開発連動QA分析

- 対象: product PR #220「chore: Expo SDK推奨依存へ同期する」
- merge commit: `2a8bcf57ff091e84a8b3bf7b123568e967000d88`（base: `d866f90961d73f738473b2c700780abe169ff79e`）
- 作成日: 2026-11-13
- 製品コード: 変更なし（読み取りのみ）
- 状態: 作業版。機能台帳への正式保存は保存先未確定のため未実施（HOLD-01）

## 1. 結論

- 変更は`package.json`と`pnpm-lock.yaml`の2ファイルのみで、機能仕様・画面・業務ロジックの変更は含まれない。
- ただし、変更対象は全ルートが依存する`expo-router` / `expo`と、テスト制御のbuild metadata判定に使う`expo-constants`を含む。両ファイルを**影響ありに分類**した（DIF-001 / DIF-002）。
- 影響候補は、(a) ネイティブのテストモード隔離（AC-NATIVE-002）、(b) Web / Nativeのルーティング・起動、(c) build・prebuild・依存互換性、の3系統に集中する。
- 製品の挙動が変わったかどうかは、このPR単体では確認していない（ローカルbuild・CI結果は未取得）。

## 2. 変更差分の分類

| ID      | ファイル         | 分類   | 根拠                                                                                                                           |
| ------- | ---------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------ |
| DIF-001 | `package.json`   | impact | dependencies 6件のversion更新と`pnpm.overrides.expo-constants`の同期。追加・削除なし。SDK 57のpatch相当。                      |
| DIF-002 | `pnpm-lock.yaml` | impact | DIF-001の解決結果。79キー追加・71キー削除。transitiveの`zod@3.25.76`削除と`glob` / `minimatch` / `path-scurry`等の追加を含む。 |

### DIF-001 の内訳

| package                   | 旧      | 新      | 利用箇所（確認済み）                                                                    |
| ------------------------- | ------- | ------- | --------------------------------------------------------------------------------------- |
| `expo`                    | 57.0.31 | 57.0.32 | SDK本体。全画面                                                                         |
| `expo-router`             | 57.0.29 | 57.0.30 | `app/`配下のルート、`src/presentation/**`のshell・guard・Link・Redirect                 |
| `expo-constants`          | 57.0.22 | 57.0.23 | `native-test-control-bridge.tsx`が`extra.testMode` / `buildKind`を読む（AC-NATIVE-002） |
| `expo-build-properties`   | 57.0.22 | 57.0.23 | `app.config.ts`のAndroid SDK / iOS deployment target                                    |
| `expo-dev-client`         | 57.0.20 | 57.0.21 | `dependencies`（devDependenciesではない）                                               |
| `@expo/metro-runtime`     | 57.0.17 | 57.0.18 | Web / Metro runtime                                                                     |
| override `expo-constants` | 57.0.22 | 57.0.23 | direct dependencyと同期                                                                 |

### 分類の判断

- `no_impact`にしなかった理由: 全ルートと両プラットフォームのbuild経路に入るpackageが含まれ、未確認の挙動変化を影響なしと推測できないため。
- `out_of_scope`にしなかった理由: 製品の機能範囲外ではなく、基盤依存。
- 承認を要する`no_impact` / `out_of_scope`には該当しないため、この分類で承認refは不要。

## 3. 機能台帳への反映（作業版）

保存先: `qa-state/pr-220/feature-ledger-delta.json`

- 機能の安定IDは未付与。製品の初回機能台帳（baseline）が存在しないため、`docs/spec/features/*.md`を暫定グルーピングとして参照し、次の4件を`provisional_feature_refs`として扱った。
  - `PLATFORM-ROUTING`（expo-routerの画面遷移・ルート解決、Web / Native共通）
  - `PLATFORM-NATIVE-RUNTIME`（テストモード判定、AC-NATIVE-002）
  - `PLATFORM-BUILD-WEB`（Web build）
  - `PLATFORM-BUILD-NATIVE`（Android / iOS build・prebuild）
- 変更履歴: 初回の作業版エントリ`EVT-220-MERGE`のみ。過去DIFとの衝突はない。
- 分類率: 2 / 2（今回のmerge差分のみ）。候補台帳が無いため候補対応率は分母0（null）。
- Git path照合: 2 / 2 件を手作業で確認。`reconcile_git_coverage.py`は保存契約の入力（registry_request）が未作成のため未実行。
- 未知領域: 製品全体の発見は未完了（`all_product_features_discovered = null`）、upgraded packageの実行時挙動は未検証、CI結果は未取得。

## 4. 影響するテスト項目候補

既存のテスト資産を、影響系統ごとに対応づけた。ITEM ID・TC化・実行はまだ行っていない（test-item-analysis以降の判断）。

| 候補ID | 影響系統                                         | 候補内容                                                                                                                | 既存資産（確認済み）                                                                                                                                                               | 優先度 |
| ------ | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| IMP-01 | Native テストモード判定                          | `extra.testMode` / `buildKind` の解決（production時は無効化）を検証                                                     | `tests/contracts/app-config.test.ts`                                                                                                                                               | 高     |
| IMP-02 | Native テスト制御の隔離（AC-NATIVE-002）         | テスト制御bridgeがexpo-constantsの値で有効・無効を切り替えること。production build にテスト用marker・画面が残らないこと | `tests/component/native/native-test-control-bridge.test.tsx`、`native-automation-bridge.test.tsx`、`maestro/native-test-control.yaml`、`maestro/native-production-validation.yaml` | 高     |
| IMP-03 | Web ルーティング・起動                           | 主要ルートの描画、ルート遷移、404相当の挙動                                                                             | `e2e/web/smoke.spec.ts`、`e2e/web/phase1-required.spec.ts`                                                                                                                         | 高     |
| IMP-04 | 権限ガード・ロールごとの遷移（Web）              | 未ログイン・顧客・管理者ごとのredirect（expo-router Redirect）                                                          | `e2e/web/cross-role-lifecycle.spec.ts`、`tests/component/route-guard.test.tsx`                                                                                                     | 中     |
| IMP-05 | Native 画面遷移・起動                            | Native shellとルーティングの描画、主要導線（ストア、カート）                                                            | `tests/component/native/native-shell.test.tsx`、`native-runtime-provider.test.tsx`、`maestro/native-storefront.yaml`、`maestro/native-cart.yaml`                                   | 中     |
| IMP-06 | Native 再起動後の永続化（BR-NATIVE-002のSQLite） | アプリ再起動後のデータ保持。expo系の更新によるSQLite周辺の影響を確認                                                    | `maestro/native-restart-persistence.yaml`、`maestro/native-session-checkout-restart.yaml`                                                                                          | 中     |
| IMP-07 | build・依存互換性                                | `expo install --check`、Expo Doctor、Web / Native build、prebuild                                                       | `.github/workflows/native-ci.yml`、`native-ios-ci.yml`、Web CI verify                                                                                                              | 高     |
| IMP-08 | transitive変更（zod 3.x削除）                    | 製品コードが直接zod 3.xを使っていないことの確認（静的確認）                                                             | 静的検索（product src / tests）                                                                                                                                                    | 低〜中 |

### 優先度の理由

- 高: 実行時の基盤（テストモード判定・ルーティング・build）に直接入る。AC-NATIVE-002の隔離は誤ると本番に検証用機能が残るため、影響が大きい。
- 中: 基盤経由で間接的に影響する画面・永続化。
- 低〜中: transitive削除。直接依存がなければ影響は小さい。

### 既存CIとの関係

PR #220では`Web CI / verify`と`native-ci / verify`等が必須とされている（`docs/plans/2026-09-12_071621_issue-141-expo-dependency-maintenance.md`）。IMP-03、IMP-07は既存CIで既にカバーされている可能性が高いが、CI結果は未取得のため、カバー済みとは判定していない（HOLD-03）。

## 5. 保留（承認が必要な項目）

| ID      | 内容                                                                            | 担当                                    | 必要な判断                                          |
| ------- | ------------------------------------------------------------------------------- | --------------------------------------- | --------------------------------------------------- |
| HOLD-01 | 成果物の保存先・Project Context（`qa.workflow_state_root`、保存provider）の確定 | project-context                         | 保存先の承認                                        |
| HOLD-02 | 製品全体の初回機能台帳（baseline）の作成範囲                                    | feature-analysis                        | 実施するか、範囲をどうするか                        |
| HOLD-03 | PR #220のGitHub上のCI結果の取得                                                 | 実行担当                                | GitHub参照の許可                                    |
| HOLD-04 | ローカルのpnpm install・expo prebuild・production bundle検査                    | testware-execution / e2e-test-execution | 実行の許可（node_modules・android/ios生成物が発生） |
| HOLD-05 | 影響テスト項目候補のtest-item-analysis以降への進行                              | test-item-analysis                      | 次工程へ進めるか                                    |

## 6. 未検証・未知領域

- 製品全体の機能台帳は未作成。機能の発見は完了していない。
- upgraded packageの実行時挙動（Web / Native起動、prebuild、production bundle）は未検証。
- PR #220のCI結果は未取得。
- `docs/spec/features/*.md`の現在有効なAuthorityは`spec-analysis`で未解決。暫定グルーピングとしてのみ使用。
- `reconcile_git_coverage.py`と`feature_registry.py`の機械検証は未実行。

## 7. 参照

- 機械証拠: `qa-state/pr-220/evidence/pr220-evidence.json`（git inventory、package.json・lockfileの差分集計）
- 作業版台帳: `qa-state/pr-220/feature-ledger-delta.json`
- 工程状態: `qa-state/pr-220/workflow-state.json`
