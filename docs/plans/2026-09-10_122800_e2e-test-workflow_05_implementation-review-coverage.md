## `e2e-test-implementation`

### 責務

確認済みのE2E対象と事実を、対象repo / workspaceの既存構造に従ったPlaywright E2Eへ変換または更新し、実装成果物が技術的に成立していることを検証します。詳細TCが存在する場合はそのTCも入力として利用します。

### 入力

必須:

- 有効な`e2e-test-inspection`成果物または同等の確認済み情報
- 次のいずれか
  - 詳細TC
  - ユーザーが明示したE2E対象
  - 更新対象となる既存E2E実装参照

TCなしの経路では、ユーザーが明示したE2E対象、現在有効な仕様根拠、その他の確認済み情報から、実装に必要な期待挙動・観測条件を確認します。必要なassertionの期待挙動を確定できない場合は推測で補わず、その範囲だけをブロックします。TCなし経路のためだけに`test-case-design`へ戻したり、TC / TC IDを生成したりしません。

### 実装前確認

コード変更前に最低限次を確認します。

- 現在branch
- HEAD commit
- working tree変更有無
- 今回変更予定ファイルと既存未commit変更の競合有無
- inspection時点から関連repo構造が変わっていないか

clean working treeを一律必須にしません。今回変更するファイルと競合しない既存変更がある場合は、それだけを理由に停止しません。

### 実装原則

- 既存spec、fixture、helper、Page Object、設定を優先して再利用する
- 存在しない抽象化を推測で利用しない
- Page Object等の特定アーキテクチャをSkill側で必須化しない
- locatorは対象repoの既存方針を優先する
- 既存方針がない場合だけPlaywright公式推奨を基準にする
- 固定時間待機を既定手段にしない
- 各テストを他テストの実行順・結果へ依存させない
- 共有サーバー側データも含めて独立性を考慮する
- 詳細TCが存在する場合は元TCの期待結果を実装都合で変更しない。TCなしの場合は、明示E2E対象と確認済みの期待挙動を実装都合で変更しない
- secretや認証情報をコードへ埋め込まない
- inspectionで確認したURL、外部遷移、副作用制約を超えない
- 新しい共通抽象化は現在の具体的な必要性を説明できる場合だけ追加する

### 実装後の静的・軽量検証

implementationの完了条件として、対象repoで適用可能な既存検証を実施します。

優先順位:

1. 対象repoの既存verify / test validation手順
2. 対象repoのlint
3. typecheck
4. Playwright test discovery
5. その他、実対象へ副作用を与えない軽量検証

既存の`verify`、`test`、test validation、lint等は名前だけで非破壊と判断しません。package script、task定義、wrapper script等から今回起動されるcommand / script chainを必要な範囲で確認し、実対象へのE2E実行、外部I/O、状態変更、破壊的なファイル操作等を含まないことを確認できたものだけimplementationの静的・軽量検証として実行します。実E2Eや外部状態変更を含む場合はimplementationでは実行せず、ユーザー要求に必要なら`e2e-test-execution`の安全契約に従って扱います。安全性を確認できない検証は推測して実行せず、未実施理由を残します。

`playwright test --list`等の公式機能は利用候補ですが、repo固有の設定読み込み自体に副作用がある場合もあるため一律強制しません。

指定テスト環境への本実行は`e2e-test-execution`の責務です。implementation完了のために本番相当の副作用を伴うE2E実行を勝手に行いません。

検証が利用不能または失敗した場合は、結果を隠さずブロック / 未完了として扱います。

### 追跡参照

対象repoに既存テストID、annotation、tag、命名規則等がある場合はそれを優先します。

既存規則がない場合でもSkill成果物上でE2E対象とE2E実装を一意に辿れる参照を保持します。詳細TCが存在する場合はTCとの対応も保持します。コードへ独自annotationを強制しません。

基本となる実装参照は次を優先します。

```text
repo-relative test file
+ Playwright test title / title path
```

project、repeat、retry等は実行単位の情報であり、静的なE2E実装参照そのものとは分けます。

### 出力

- 実装 / 更新 / 再利用したPlaywrightテスト
- 元TC IDとの対応。TCが存在する場合のみ
- 元の明示E2E対象 / 既存E2E実装参照。該当する場合のみ
- E2E実装参照
- 変更したfixture / helper / Page Object / config等
- 実装前のbranch / HEAD / working tree確認結果
- 実施した静的・軽量検証
- 各検証結果
- inspectionからの差分・再inspection要否
- ブロック / `要再検証`

## `adversarial-review`の拡張

Playwright E2Eテスト成果物を独立レビュー対象へ追加します。

Playwright固有の詳細ルールは`SKILL.md`へ大量に追加せず、E2E実装レビュー用referenceを追加して必要時だけ読みます。

レビュー対象:

- 詳細TCが存在する場合は元TCと同じ検証目的・期待結果を維持しているか
- TCなしの場合は、ユーザーが明示したE2E対象、確認済みの期待挙動、現在有効な仕様根拠と意味が一致しているか。E2Eコード上のassertion自体を仕様根拠として扱わない
- 仕様根拠のないassertionを追加していないか
- assertionを弱くしていないか
- 存在しないlocator、fixture、helper、Page Object等を仮定していないか
- 既存実装を無視した重複実装がないか
- 不安定な固定待機や不要に脆弱なlocatorがないか
- テスト間依存がないか
- テストデータ・開始状態・cleanupが設計と整合するか
- secretや機密情報をコード・ログへ埋め込んでいないか
- 未許可の副作用や別環境操作につながらないか

lint、typecheck、test discovery等の実行責務は`e2e-test-implementation`に置きます。`adversarial-review`はその結果を根拠として参照できますが、一般的なlint runnerにはしません。

一般的なReact / API / DB等のプロダクトコードPRレビューは従来どおり本Skillの発火対象にしません。

決定論的評価では、QA成果物レビューの既存ID検証とE2E testwareレビューの実装参照検証を分けます。E2E testwareでは、対象repoに既存の安定したtest identifierがあればそれを優先し、なければrepo-relative path + title path等のE2E実装参照をfixtureと照合して対象の存在・一致を確認します。`ALL_ID_RE`へpathを追加したり、架空の`E2E-001`等を必須化したりしません。

## `coverage-analysis`の拡張

既存の設計追跡に加えて、E2E自動化が要求された範囲について次を意味上の追跡対象へ追加します。

```text
詳細TC
  ↓
E2E実装 / 既存E2E / E2E対象外 / ブロック
```

各TCについて、次のいずれかへ閉じていることを確認します。

- 新規E2E実装
- 既存E2E再利用
- 既存E2E拡張
- 上流判断で妥当なE2E対象外
- ブロック中

通常のE2E実行では、`e2e-test-execution`自身が「実行対象 → 実行結果または未実行理由」を保証します。そのため`E2E実装 → 実行結果`のcoverage-analysisを主経路の必須工程にしません。

ユーザーが完全な追跡監査を要求した場合や対応関係に疑義がある場合は、`E2E実装 → 実行結果`も部分分析できます。

分析・報告そのものまでcoverage graphへ追加しません。分析・報告はTC、E2E実装参照、実行結果参照を保持することで追跡可能にします。

既存のAuthority / QA IDからTCまでの追跡グラフは維持します。`TC ↔ E2E実装参照`は既存IDグラフへ新しいE2E IDを追加して表現せず、TC IDとrepo-relative test path + title path等のE2E実装参照との対応関係として別途検証します。`ALL_ID_RE`や共通追跡グラフをE2E実装参照のためだけに一般化しません。

`coverage-analysis`の対象が`TC → E2E実装`の場合は、最低限次の対応表を持ちます。TCなしの既存E2Eや明示E2E対象から開始する経路へ、この表やTC IDを機械的に要求しません。

```text
TC ID | 扱い | E2E実装参照 | 根拠 / 備考
```

`扱い`は既存の判断語彙を再利用します。

- 新規E2E実装
- 既存E2E再利用
- 既存E2E拡張
- E2E対象外
- ブロック中

新規実装・既存再利用・既存拡張では、対象repoに既存の追跡方式がなければrepo-relative test path + title path等でE2E実装を一意に辿れるようにします。E2E対象外・ブロック中では存在しない実装参照を要求しません。決定論的評価はこの対応表を既存QA IDグラフとは別契約として検証します。`E2E実装 → 実行結果`だけを部分分析する場合は、TCが存在しなくてもE2E実装参照から実行結果へ辿れればよく、架空のTC / TC IDを生成しません。

`coverage-analysis`の対象が`E2E実装 → 実行結果`の場合は、既存のカバレッジマトリクス等で最低限、各E2E実装参照からresolved primary TestCaseまたは実行結果参照へ辿れ、その結果または未実行理由を確認できるようにします。専用の新しいE2E coverage表や追跡グラフは追加しません。fixtureから期待するE2E実装参照を一意に決められるケースでは、対象参照が欠落したまま完了扱いにならないよう、この最低追跡契約を既存QA IDグラフとは別に決定論的に検証します。

`coverage-analysis`がギャップを検出した場合の修正先表現は、既存`SKILL.md` / guidanceに残る「最も近い担当Skill」ではなく、`qa-workflow`の共通契約である「意味が変わる最も早い責任Skill」へ統一します。
