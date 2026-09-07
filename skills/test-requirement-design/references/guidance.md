# テスト要求設計 詳細判断基準

## 目的

仕様分析とテスト分析から、**何を検証・保証する必要があるか**をTest Requirementとして定義します。

Test Requirementはこのワークフロー固有の中間成果物であり、Current Effective AuthorityとTest Conditionの間で検証責務を安定させ、AIが条件やケースへ早すぎる具体化をするのを防ぎます。

## 入力

必須:

- 対象範囲のCurrent Effective Authority
- テスト対象範囲

利用可能なら`test-analysis`のProduct Risk / テスト重点、案件コンテキスト、不明点・矛盾分析、テストレベル / 観測方法も使います。

## Current Effective Authority

Test Requirementが製品の期待挙動を含む場合、`spec-analysis`で解決済みのCurrent Effective Authority、または同等に有効性が確認された上流成果物へ追跡します。

本SkillはSPEC / DECISION / ASMの優先関係、version、情報源競合を再解決しません。Current Effective Authorityが未解決・陳腐化・競合状態なら`spec-analysis`へ戻します。

Product Risk、実装、既存テスト、一般的慣習、未承認`INFERENCE`だけで製品期待挙動を確定しません。

## 抽象度

Test Requirementは「何を検証するか」を表します。

含める:

- 検証対象の挙動 / ルール / 品質責務
- 期待される成立条件の意味
- Current Effective Authority
- Product Risk / 優先度
- テストレベル / 観測方法

含めない:

- 具体的入力値の列挙
- 境界値の具体展開
- 組合せ表
- 実行手順
- Test Caseの前提 / データ / Step

Test Requirementは上流記載の言い換えだけでは不十分です。「何を保証すればその上流責務が検証されたと言えるか」が独立して分かる検証責務へ変換します。

## 上流項目の閉鎖

フルワークフローでは、対象範囲内の上流項目を無言で消しません。

### Current Effective Authority

対象内の各Current Effective Authorityは、次のいずれかへ位置づけます。

- 1つ以上のTest Requirementへ接続
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

### Product Risk

対象内の各Product Riskも、次のいずれかへ位置づけます。

- 1つ以上のTest Requirementへ接続
- 別テストレベル
- 残存リスク
- 対象外
- Blocked

Product Riskが低いことだけを理由に、Current Effective AuthorityまたはProduct Riskを下流から消しません。

共通Dispositionの意味は`qa-workflow`、要求化固有の判断は本Skillを正本とします。

## 分割・統合の判断

1つにまとめてよいのは、守るべき製品挙動、Current Effective Authority、失敗時の意味、テストレベルが同じ検証責務として扱える場合です。

異なる業務ルール、権限責務、状態 / ライフサイクル責務、期待挙動の意味、または追跡責務を持つ場合は分割します。ケース数削減のために無関係な責務を統合しません。

## 優先度

関連Product Riskがある場合は、その最も高いRisk levelを既定優先度として引き継ぎます。案件固有の明示的重点がある場合はそれも考慮できます。

上流より優先度を下げる場合は、別テストレベル、重複責務等の理由を明示します。理由なく高い上流優先度を下げません。

## 手順

1. 対象範囲のCurrent Effective Authority、Product Risk、テストレベルを確認する
2. 「この上流責務が正しく実装されていると判断するために、何を保証する必要があるか」を検証責務として抽出する
3. 関連Product Riskを優先度・深度根拠として接続する
4. Test Requirementを作らないCurrent Effective Authority / Product Riskは共通Dispositionへ位置づける
5. 各Test Requirementが少なくとも1つのCurrent Effective Authorityへ戻れることを確認する
6. 対象内のCurrent Effective Authority / Product Riskに未処理項目がないことを確認する

## 出力

各Test Requirementに必要な情報:

- 安定ID（例: `TR-001`）
- 検証責務
- Current Effective Authority
- 関連Product Risk
- 優先度
- テストレベル / 観測方法

Test Requirementを作らない上流項目には、上流ID、種別、Disposition、理由が必要です。

## 停止条件

次の場合、影響要求をBlockedとします。

- 何を保証すべきかをCurrent Effective Authorityから決められない
- 期待挙動を未承認推論で埋めないと要求を書けない
- Current Effective Authorityが未解決
- 対象範囲そのものが特定できない

Product Riskが未評価でも上流責務自体が明確ならTest Requirement作成は可能です。その場合は優先度根拠の制約を明示します。

## 品質ゲート

- 各Test RequirementがCurrent Effective Authorityへ追跡できる
- 対象内の各Current Effective AuthorityがTest Requirementまたは明示Dispositionへ閉じている
- 対象内の各Product RiskがTest Requirementまたは明示Dispositionへ閉じている
- 上流記載の単なる言い換えではなく検証責務になっている
- Product Riskを期待挙動のAuthorityにしていない
- 未承認`INFERENCE`を完成済み要求の根拠にしていない
- 「何を検証するか」に留まり、具体条件 / 手順を先回りしていない
- 要求同士の重複・過剰統合がない
- Product Riskが低いという理由だけで上流項目を消していない
- 優先度にProduct Riskまたは明示的案件重点の理由があり、上流より下げる場合は理由がある

## 次の担当Skill

- 不明点・期待挙動不明 → `question-analysis`
- Test Condition / Coverage Item設計 → `test-condition-design`

## 出力前自己検証

最終出力前に、実際に利用した入力が本SkillのInput Contractを満たし、入力・Authority・判断状態に停止条件へ該当する未解決状態がないか確認します。あわせて、生成した成果物へ本SkillのOutput Contractと既存の品質ゲートを再適用します。品質基準は本ガイダンスの既存定義を正本とし、Self-Validation専用のrubricやチェックリストを別定義しません。

1. 実際に利用した入力がInput Contractを満たし、停止条件へ該当する未解決状態がないか確認する
2. 生成した成果物がOutput Contractと既存の品質ゲートを満たしているか確認する
3. 明白かつ局所的で、新しいDomain判断を必要としない契約違反だけを最大1回修正する
4. 修正後は修正箇所を含めて最終確認する。解消に新しいAuthority、上流判断、他SkillのDomain Logicが必要な場合は自力で補完せず、既存の停止条件・Blocked・routingに従う
5. 最終確認後も本Skill自身の契約違反が残り、既存の停止条件・Blocked・routingに該当しない場合は、2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わない。現在残っている契約上の制約だけを明示する

未解決AuthorityやProduct RiskをSelf-Validationの名目で再解釈せず、要求の抽象度や責務境界を超えてTest Condition設計へ進みません。既存の`Blocked`定義を未解消ローカル違反へ広げません。Self-Validationの実行経緯、修正回数、修正前状態、PASS / FAIL等の評価ログは通常成果物へ出力せず、現在有効な状態と未解消の契約上の制約だけを返します。
