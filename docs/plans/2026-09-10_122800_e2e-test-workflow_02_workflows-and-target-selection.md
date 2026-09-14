## 推奨ワークフロー

全14 Skillを固定順に毎回実行しません。要求成果物と有効な既存成果物に応じ、必要な依存関係だけを実行します。

### テスト設計のみ

```text
必要な開始Skill
  ↓
spec-analysis
  ↓
question-analysis        ※必要な場合だけ
  ↓
test-analysis
  ↓
test-requirement-design
  ↓
test-condition-design
  ↓
test-case-design
  ↓
coverage-analysis        対象: テスト設計
  ↓
adversarial-review       対象: テスト設計成果物
  ↓
完了
```

有効な既存成果物があれば従来どおり途中から開始します。

### 詳細テストケースからE2E実装

ユーザーが詳細テストケースを明示した場合、そのテストケースをE2E対象として採用し、E2E価値の再判断を必須にしません。

```text
e2e-test-inspection
  ↓
e2e-test-implementation
  ↓
adversarial-review       対象: E2E実装
  ↓
coverage-analysis        対象: TC → E2E実装
  ↓
完了
```

生のユーザー依頼が「このTCをPlaywrightで実装して」で、inspection相当の確認済み情報がまだない場合は、`qa-workflow`が`e2e-test-inspection`から開始する経路を選びます。

TCがない状態で「ログインフローをPlaywrightで実装して」のように明示E2E対象の実装を要求された場合や、「この既存Playwright testを更新して」のように更新対象の既存E2E実装参照だけが指定された場合も、inspection相当の確認済み情報がなければ同じく`qa-workflow → e2e-test-inspection → e2e-test-implementation`で進めます。E2E対象の選定自体を要求されていなければ`test-analysis`を必須にせず、TCを作る目的だけで`test-case-design`を挟みません。

`e2e-test-implementation`を直接開始できるのは、有効なinspection成果物または同等の確認済み情報が既にある場合です。必要な事実が不足している場合は存在しないlocator等を推測せず、コード変更を開始せずにinspection相当の確認が必要な状態として扱います。

### 既存E2Eの実行のみ

有効な既存Playwrightテストがあり、ユーザーが実行だけを要求する場合は設計・inspection・implementationを機械的に挟みません。

```text
e2e-test-execution
  ↓
要求が実行だけなら完了
```

ただし`e2e-test-execution`自身が、今回の実行に必要な最小限の安全確認を行います。既存E2Eが指定環境で安全に実行できるか判断できない場合だけ、`e2e-test-inspection`へ戻します。

### 設計からE2E実装・実行・報告まで

```text
既存のテスト分析・設計経路
  ↓
coverage-analysis        対象: テスト設計
  ↓
adversarial-review       対象: テスト設計成果物
  ↓
E2E対象確定
  ↓
e2e-test-inspection
  ↓
e2e-test-implementation
  ↓
adversarial-review       対象: E2E実装
  ↓
coverage-analysis        対象: TC → E2E実装
  ↓
e2e-test-execution
  ↓
異常または分析要求あり?
  ├─ なし → 報告要求があれば e2e-test-reporting
  └─ あり → e2e-test-result-analysis
              ↓
            必要な修正・再検証・再実行
              ↓
            報告要求があれば e2e-test-reporting
  ↓
qa-workflowによる完了判定
```

通常実行では`e2e-test-execution`自身が「要求された実行対象 → 実行結果または未実行理由」の完全性を保証します。`E2E実装 → 実行結果`を確認するためだけに`coverage-analysis`を毎回必須実行しません。

ユーザーが全体追跡監査を要求した場合や、実行結果との対応に疑義がある場合は`coverage-analysis`を部分実行できます。

異常がなく、分析要求もない場合は`e2e-test-result-analysis`を必須にしません。

### FAIL後の原因分析・修正・再実行

```text
e2e-test-result-analysis
  ↓
原因・判定状態を確認
  ├─ E2E実装問題       → e2e-test-implementation
  ├─ 詳細TC問題        → test-case-design
  ├─ 条件問題           → test-condition-design
  ├─ テスト方針問題     → test-analysis
  ├─ 仕様根拠問題       → spec-analysis / question-analysis
  ├─ inspection事実不足 → e2e-test-inspection
  ├─ 実行条件問題       → e2e-test-execution
  ├─ プロダクト仕様不一致 → 検出事項として保持。E2EをPASSさせる変更をしない
  └─ 証拠不足           → 判定不能または追加証跡取得
  ↓
影響する成果物だけ`要再検証`
  ↓
必要なレビュー / 追跡確認
  ↓
必要なE2Eだけ再実行
  ↓
必要なら再分析
```

追加実行はPASSにするためではなく、原因判断に必要な証拠を得る目的で行います。

## E2E対象の決定

### `test-analysis`の扱い

`test-analysis`の主責務であるプロダクトリスク、テスト重点、テストレベル、深度、観測方法を維持します。

E2E自動化まで要求されている場合に限り、次のような高位の候補範囲・目的・判断基準を補助情報として出力できるようにします。

- UIを通したシステムレベル検証として価値がある範囲
- 主要業務経路
- 繰り返し確認する価値がある範囲
- 他テストレベルだけでは十分に保証しにくい範囲

これはPlaywright固有の実装可否や実装コストを判断する責務ではありません。また、自動化維持コストをプロダクトリスク評価値へ混ぜません。`対象 / 実行範囲 = E2E対象選定`では、少なくとも自動化目的、候補範囲、技術非依存の判断基準 / 根拠を成果物として残し、これらが欠落したまま既存の通常テスト分析項目だけで完了扱いにならないよう決定論的評価で検出します。通常の`テスト分析`ではこの追加成果物を必須にしません。

### 具体TCの決定

具体的なE2E対象TCは次の順で決定します。

1. ユーザーがTCを明示している場合は、その指定を採用する
2. 既存成果物でE2E対象が確定している場合は再利用する
3. 未指定の場合は、`test-analysis`の候補範囲・判断基準と詳細TCの追跡関係を`e2e-test-inspection`で照合し、具体TCを確定する

`e2e-test-inspection`は単に候補範囲に属するTCを機械的に全件採用しません。既存E2E重複、不可逆操作、安定したデータ準備可否、外部依存等の新しい事実を確認します。

新しい事実により「そもそも自動化する価値」を再判断する必要が生じた場合は、該当範囲だけ`test-analysis`へ戻します。

新しい`e2e-test-selection` Skillは追加しません。
