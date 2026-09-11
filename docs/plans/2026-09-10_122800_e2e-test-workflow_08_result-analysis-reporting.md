## `e2e-test-result-analysis`

### 責務

検証済みの実行結果、識別可能なE2E対象 / E2E実装参照、利用可能な証跡を最低入力として、異常結果の原因を判定可能な範囲で分析します。詳細TCと現在有効な仕様根拠は、存在し、かつ判定に必要な場合に利用します。

Playwrightが返した事実とAIによる原因判断を分離します。

正常結果だけで分析要求もない場合は、本Skillを必須にしません。TCなしの既存E2E結果を分析するためだけに詳細TCやTC IDを新規作成せず、`test-case-design`も機械的に要求しません。利用可能な証拠でE2E実装、実行条件、データ、環境等を分析し、権威ある期待挙動を確定できない場合は「プロダクトの実際の挙動が現在有効な仕様根拠と不一致」という原因だけを判定不能として残します。E2Eコード上のassertion自体を製品仕様の正本にはしません。

### 分析対象と起動条件

各attemptの`status`は常に実行事実として保持しますが、自動的に原因分析へ進むかは最終`outcome`、`expectedStatus`、run全体結果、cleanup状態、ユーザー要求を基準に判断します。

少なくとも次を分析対象にできます。

- 最終`outcome = unexpected`
- 最終`outcome = flaky`
- 期待していないskip
- 要求対象の未実行
- run全体の`failed` / `timedout` / `interrupted`
- testに紐づかないrun-level / global error
- cleanup失敗 / 一部失敗 / cleanup未確認 / 安全上未処理の残存副作用
- 明示的なユーザー分析要求

各attemptの`failed`、`timedOut`、`interrupted`等は重要な分析材料ですが、それ単独では自動起動条件にしません。`expectedStatus = failed`で実際も失敗し、最終`outcome = expected`となるexpected failure等を異常扱いしません。

ユーザーが明示的に「実行結果だけ」「分析しない」と要求した場合は、異常があっても原因分析を自動追加しません。実行事実と未処理の安全上の問題をそのまま提示します。

「必要なら分析」「実行から結果確認まで」等、分析を含み得る要求、または一連の`qa-workflow`が要求されている場合は、上記の異常があれば本Skillへ進みます。正常結果かつ分析要求なしの場合は本Skillを省略します。

### 原因

判明した原因は複数あって構いません。

- プロダクトの実際の挙動が現在有効な仕様根拠と不一致
- E2E実装の問題
- 詳細TCの問題
- テスト条件・カバレッジの問題
- E2E対象選定 / 自動化価値の問題
- テストデータ・開始状態の問題
- 指定されたテスト対象環境の問題
- ローカルPlaywright実行環境の問題
- 現在有効な仕様根拠の不足・矛盾

`証拠不足による判定不能`は原因として無理に確定せず、判定状態として保持します。

### テスト対象versionが不明な場合

仕様と観測結果が異なっても、指定環境が古いbuildである可能性等を排除できず原因判定へ影響する場合は、即座に「現在対象とするプロダクトの仕様不一致」と確定しません。

version / deployment差異を含む環境側の未確定事項または証拠不足として保持し、必要なら追加確認へ回します。

### 再現性

原因とは別軸で次を記録できます。

- 再現
- 再現せず
- 断続的
- 未確認

1回の`FAIL → retry PASS`だけで原因を確定しません。

### 追加実行

本SkillはPlaywrightを直接再実行しません。追加実行が必要な場合は、取得したい証拠、検証したい仮説、必要な実行範囲を出力し、`qa-workflow`を介して`e2e-test-execution`へルーティングします。`e2e-test-execution`が通常の安全確認、現在のcleanup状態、副作用、実行条件を確認したうえで必要範囲を実行し、新しい検証済み実行結果を取得します。その結果について再分析が必要なら本Skillへ戻します。

PASSになるまで繰り返す目的の追加実行は禁止します。

### 修正ルーティング

- 仕様根拠 → `spec-analysis`
- 製品仕様・期待結果の不明点 → `question-analysis`
- テスト方針・テストレベル・E2E対象選定 / 自動化価値 → `test-analysis`
- テスト要求 → `test-requirement-design`
- テスト条件・カバレッジ項目 → `test-condition-design`
- 詳細TC → `test-case-design`
- 追跡関係 / `coverage-analysis`自身の判定 → `coverage-analysis`
- inspection事実 → `e2e-test-inspection`
- Playwright実装 → `e2e-test-implementation`
- 実行条件・状態準備・実行不足・cleanup状態の再確認 → `e2e-test-execution`

プロダクトの仕様不一致をE2Eテストコード変更でPASSへ変えません。

### 出力

- 対象TC（存在する場合） / E2E実装参照 / 実行結果参照
- 実行事実の要約
- 判定状態
- 判明した原因
- 再現性
- 根拠
- 不足証拠
- 追加実行要否、取得したい証拠、検証する仮説、必要な実行範囲。実行自体は`e2e-test-execution`へ委譲
- 修正先Skill
- `要再検証`範囲
- 検出事項として報告可能な内容

## `e2e-test-reporting`

### 責務

検証済みの実行結果を、人間が判断できるテスト結果報告へ変換します。`e2e-test-result-analysis`を実施した場合は、検証済みの分析結果も入力として利用します。

原因の再判定、仕様の再解釈、結果の都合のよい単純化は行いません。分析済み結果だけから開始する場合も、URL、project、実行日時、E2E実装参照等の必要な実行事実へ辿れることを前提とします。

### 主な出力

- 対象機能 / 対象範囲
- テスト環境URL / origin
- テスト対象version。確認不能ならその旨
- E2Eコードbranch / commit / working tree状態
- 実行日時
- Playwright project
- Playwright run全体status / process exit code / run-level / global error
- 論理的な要求primary対象数
- resolved primary TestCase数
- 実際に開始したresolved primary TestCase数
- expected / unexpected / flaky / skipped等、必要なPlaywright結果集計
- 未実行logical primary数と理由
- 未実行resolved primary TestCase数と理由
- TC（存在する場合） / E2E実装参照
- 期待結果。確認可能な場合のみ
- 実際の結果
- 分析結果。`e2e-test-result-analysis`を実施した場合のみ
- 再現性。分析で確認した場合のみ
- 追加実行結果
- cleanup状態。成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態を区別
- 残存副作用
- ブロック中
- 残存リスク
- 未解決事項
- 安全に共有できる証跡参照

人間向けに論理的なE2E対象単位へ再集計する場合も、`論理対象単位`等の集計単位を明示します。resolved primary TestCase数とretry attempt数を混同せず、retryは別のattempt情報として扱います。

secret、cookie、token、不要な個人データ等を証跡から転載しません。
