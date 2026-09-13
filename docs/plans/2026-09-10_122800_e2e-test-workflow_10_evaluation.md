## 評価の変更

### 用語整理

`EVALS.md`の「ワークフローE2E評価」はブラウザE2Eとの混同を避ける名称へ変更します。

実Agentクライアント上で複数Skillを実際に連続実行する評価は引き続き未実装とします。名称変更だけを理由に新しいAgent統合harnessを作りません。

`coverage-analysis/references/guidance.md`のブラウザE2Eと紛らわしい「E2E追跡」も意味が明確な表現へ変更します。

### 新規5 Skillの評価構造

新しい5 Skillも既存Skillと同じ基本構造を持たせます。

```text
skills/<skill-name>/
├── SKILL.md
├── references/
├── assets/
└── evals/
    ├── trigger/
    ├── output/
    ├── deterministic/
    └── semantic/
```

内容が短いSkillへ不要な空reference / assetを機械的に増やさず、既存リポジトリの構造契約に必要なものだけ作成します。

### 発火評価

現行契約を維持する場合は各Skillについて次を用意します。

- train: 12件（positive 6 / negative 6）
- validation: 8件（positive 4 / negative 4）

14 Skill合計で280クエリです。

リポジトリ内CIで検証する発火関連項目と、実Agentクライアントでのみ確認できる実発火を分けます。リポジトリ内CIではtrigger datasetの件数、positive / negative比率、14 Skill / 280 query、データ構造等を検証します。実際にどのSkillが選択されたか、`trigger_rate`、誤発火等は実Agentクライアントで評価します。実Agent評価を利用できない実装環境では、その結果をPASSとみなさず`未実施`として記録し、今回そのための新しい実Agent統合harnessは作りません。

既存Skillの発火評価は単純追加して総数を増やさず、必要な新境界を既存queryの置換・再配分で反映します。

重点境界:

- `test-case-design` ↔ `e2e-test-implementation`
- `test-analysis` ↔ `e2e-test-inspection`
- `e2e-test-inspection` ↔ `e2e-test-implementation`
- `e2e-test-implementation` ↔ `e2e-test-execution`
- `e2e-test-implementation` ↔ `adversarial-review`
- `e2e-test-execution` ↔ `e2e-test-result-analysis`
- `e2e-test-result-analysis` ↔ `e2e-test-reporting`
- `coverage-analysis` ↔ `e2e-test-result-analysis`
- `coverage-analysis` ↔ 単純な実行結果集計
- `adversarial-review` ↔ 一般的なプロダクトコードPRレビュー
- `qa-workflow` ↔ 各単独E2E Skill

代表的な発火期待:

```text
inspection相当の確認情報がない状態で「このTCをPlaywrightで実装して」
→ qa-workflow
→ inspection → implementationへルーティング
→ test-analysisを必須にしない

inspection相当の確認情報がない状態で「ログインフローをPlaywrightで実装して。TCはない」
→ qa-workflow
→ inspection → implementationへルーティング
→ E2E対象選定自体を要求していなければtest-analysisを必須にしない
→ TCを作る目的だけでtest-case-designを挟まない

inspection相当の確認情報がない状態で「この既存Playwright testを更新して」
→ qa-workflow
→ 既存E2E実装参照を入力としてinspection → implementationへルーティング
→ TCを生成しない

「このinspection結果に従ってTC-001をPlaywrightで実装して」
→ e2e-test-implementation
→ 有効なinspection成果物または同等の確認済み情報がある場合だけコード変更を開始

「このinspection済みの明示E2E対象を新規実装して。TCはない」
→ e2e-test-implementation
→ TCを生成せず、明示E2E対象と確認済み期待挙動を入力として実装

「既存PlaywrightをこのURLで実行して」
→ e2e-test-execution
→ inspectionは必要な場合だけ

「このE2Eが実行可能か安全性だけ調べて。実行はしないで」
→ e2e-test-inspection
→ e2e-test-executionへ誤発火させない

「この失敗結果を分析して」
→ e2e-test-result-analysis

「分析し、必要なら修正して再実行して」
→ qa-workflow

「分析済み結果から報告だけ作って」
→ e2e-test-reporting

「通常のアプリコードPRをレビューして」
→ adversarial-reviewのE2Eテスト成果物用途へ誤発火しない
```

### 決定論的評価・意味評価

- 5 Skillそれぞれの出力契約を決定論的評価へ追加
- 既存契約が最低2ケース / Skillなら、新規5 Skill分を追加して最低28ケースを満たす
- 意味評価を2ケース / Skillで維持する場合は14 Skill × 2 = 28ケースへ更新
- 既存Skillの意味評価は必要な責務変更部分だけ更新
- `test-analysis`の`E2E対象選定`では、少なくとも自動化目的・候補範囲・技術非依存の判断基準 / 根拠が存在することを、通常の`テスト分析`とは別の対象契約として決定論的に検証する。具体TCの技術的採否は要求しない
- `adversarial-review`のE2E testwareレビューでは、QA成果物の既存ID検証と分け、対象repo既存の安定したtest identifier、またはrepo-relative path + title path等のE2E実装参照をfixtureと照合できる決定論的契約を追加する。`ALL_ID_RE`へpathを追加したり架空のE2E IDを必須化したりしない
- `question-analysis`では、再開Skillの正規名検証に加え、fixtureから再開先を一意に決められるケースで期待再開Skillと必要時の期待`再開対象 / 実行範囲`を比較し、同じブロッカーの質問一覧 / ブロック中範囲で再開先が不一致なら検出する
- `coverage-analysis`の`E2E実装 → 実行結果`では、fixtureから期待するE2E実装参照が分かる場合に、resolved primary TestCaseまたは実行結果参照と結果 / 未実行理由へ追跡できない状態を検出する
- `e2e-test-execution`では、logical primaryが存在するのにresolved primary TestCaseが0件で理由もないケース、利用したresult形式が提供しないraw値を推測補完するケースを誤PASSさせない
- `e2e-test-result-analysis`では、追加実行の必要性を判断しても本Skill自身が実行せず、`e2e-test-execution`へルーティングする契約を評価する
- `e2e-test-reporting`では、logical primary件数とresolved primary TestCase件数、双方の未実行数 / 理由を区別し、retry attemptをresolved件数へ混ぜない契約を評価する
- `test-analysis`はPlaywright固有Skillへ変えないため、E2E固有語への過度な発火変更を避ける

### `qa-workflow`ルーティング評価

実Agent統合harnessではなく、既存の決定論的 / 意味評価で少なくとも次を確認します。

1. E2E不要の設計依頼では既存経路だけで完了できる
2. ユーザー指定TCからE2E実装へ進む場合、E2E価値再判断を必須にしない
3. E2E実装前に必要なinspectionを通せる
4. 有効なinspection結果があればimplementationから開始できる
5. 既存E2E実行だけならexecutionから開始できる
6. execution直接開始でも安全確認が行われる
7. implementation完了前に静的・軽量検証結果が必要
8. E2E実装レビュー指摘がimplementationへ戻る
9. TC → E2Eの追跡不足がcoverage-analysisへ戻る
10. 異常のない実行で分析要求がなければresult-analysisを省略できる
11. 異常時はresult-analysisへ進む
12. E2E実装問題はimplementationへ戻り、必要範囲だけ再実行する
13. 仕様不明はquestion-analysisへ戻り、回答後は意味が変わる最も早い責任SkillがE2E工程ならそのE2E Skillへ再開できる
14. TCなしの既存E2E結果をresult-analysisへ渡してもTCを創作せず、判定可能な原因だけ分析できる
15. automatic fixture / worker-scoped automatic fixtureの副作用をexecutionの安全確認で扱える
16. cleanup未確認をresult-analysis / reportingへ失わず伝播できる
17. resolved primary TestCaseの一部結果が欠落した場合に完全実行と誤判定しない
18. テスト環境URL不足はexecution範囲だけブロックできる
19. 未許可副作用は該当TCだけブロックできる
20. E2EをFAILのまま正しく分析・報告してもworkflow完了可能
21. TCなしの明示E2E対象をinspection後にimplementationへ渡してもTCを創作しない
22. inspection相当情報がないTCなしの明示E2E実装依頼を`qa-workflow → inspection → implementation`へルーティングし、対象選定要求がなければ`test-analysis`、TC作成だけを目的とする`test-case-design`を必須にしない
23. inspection相当情報がない既存E2E更新依頼を既存E2E実装参照からinspection → implementationへ渡し、TCを生成しない
24. question-analysisの再開先が複数用途Skillの場合、`再開対象 / 実行範囲`まで必須で一意に復元できる
25. logical primaryがresolved primary TestCaseへ0件しか解決されない場合、理由なしで完全実行扱いしない
26. result-analysisが追加実行を必要と判断した場合、実行自体はexecutionへルーティングする
27. 利用したresult形式が提供しないraw値を推測補完せず、確認不能 / 導出値として区別する
28. reportingではlogical primary件数とresolved primary TestCase件数を区別し、未実行数も同じ単位で分けて報告できる
29. reportingだけの途中開始が可能
