## 共通契約

### ワークフロー状態は`Skill + 対象 / 実行範囲`で識別する

同じSkillを異なる対象へ複数回適用できるよう、ワークフロー状態表はSkill名だけを一意キーにしません。

最低限、状態表に`対象 / 実行範囲`を追加し、例えば次を独立して保持できるようにします。

```text
coverage-analysis  | テスト設計       | 完了
adversarial-review | テスト設計成果物 | 完了
adversarial-review | E2E実装          | 要再検証
coverage-analysis  | TC → E2E実装     | 完了
```

`対象 / 実行範囲`を無制限の自由記述キーにはしません。複数用途を持つSkillでは、少なくとも次の正規値を使用します。

```text
test-analysis
- テスト分析
- E2E対象選定

coverage-analysis
- テスト設計
- TC → E2E実装
- E2E実装 → 実行結果  ※横断追跡監査を要求された場合だけ

adversarial-review
- テスト設計成果物
- E2E実装
```

単一用途のSkillへ意味のない対象名を増やさず、`対象 / 実行範囲`は空欄を許容します。一方、上記の複数用途Skillは実際の状態行へ出力する時点で用途が確定しているため、`対象 / 実行範囲`を常に定義済みの正規値で必須とし、空欄や非正規値を許容しません。validatorでもこの許可範囲を検証し、表記ゆれや用途不明の行を別対象として扱わないようにします。

ワークフロー状態表の出力契約は最低限次とします。

```text
Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考
```

開始・終了Skillが複数用途Skillの場合は、状態表から推測せず、次の対象値も必須で出力します。単一用途Skillでは対象値を必須にせず、対象を区別しない既存経路との互換性を維持します。

```text
- 開始Skill:
- 開始対象 / 実行範囲:
- 最終Skill:
- 最終対象 / 実行範囲:
```

状態・validatorの最低契約は次とします。

- `WF-D006`: `expected_start_skill`は維持する。実際の`開始Skill`が複数用途Skillなら、fixtureに`expected_start_target`があるかにかかわらず`開始対象 / 実行範囲`を必須とし、定義済み正規値であることを検証する。fixtureに`expected_start_target`がある場合は、さらにその期待値と一致することを検証する
- `WF-D007`: `expected_final_skill`は維持する。実際の`最終Skill`が複数用途Skillなら、fixtureに`expected_final_target`があるかにかかわらず`最終対象 / 実行範囲`を必須とし、定義済み正規値であることを検証する。fixtureに`expected_final_target`がある場合は、さらにその期待値と一致することを検証する
- `WF-D008`: 「Skillを少なくとも一度利用したか」という既存の意味では`expected_skills`をSkill単位のまま維持する。特定対象の利用が必須な場合は後述の対象別期待状態等で検証する
- `WF-D012`: Skill名単独の重複禁止ではなく、同じ`(Skill, 対象 / 実行範囲)`の不正な重複を検出する
- `WF-D014`: Skill名だけの辞書ではなく、`(Skill, 対象 / 実行範囲)`ごとの状態を比較できるようにする

複数対象の状態を期待するfixtureでは、概念上次を表現できる`expected_scoped_skill_states`を持たせます。

```json
[
  {"skill": "adversarial-review", "target": "テスト設計成果物", "state": "完了"},
  {"skill": "adversarial-review", "target": "E2E実装", "state": "要再検証"}
]
```

既存のSkill単位fixtureを不要に破壊せず、対象を区別しないと誤PASSするケースだけ対象別期待値を追加します。`WF-D002`〜`WF-D005`、`WF-D010`、`WF-D011`等、全体状態またはSkill利用有無だけで契約を満たせるassertionまで対象-awareにしません。

retry attempt、Playwright run、各TestResultは`e2e-test-execution`成果物内で管理し、`qa-workflow`の状態行へ展開しません。

### ワークフロー完了とテスト結果を分離する

次を明示的な原則とします。

```text
ワークフロー完了 ≠ 全E2EテストPASS
```

ユーザーが「実行・分析・報告」を要求した場合、プロダクトの仕様不一致によりE2E結果がFAILでも、要求された実行・分析・報告が完了し、未処理のブロックや必要な`要再検証`がなければワークフロー自体は完了できます。

要求成果物に応じ、次が残る場合は未完了またはブロック中とします。

- 必要な実行が未実施
- 原因判定に必要な証拠不足が未処理で、その解消まで要求されている
- E2E実装不備が未修正で、修正まで要求されている
- 必須cleanup失敗またはcleanup状態の未確認が未処理
- 必須実行環境を利用できない
- 必要な再検証が未実施
- `要再検証`が残る
- 必須報告が未完成

判定不能を正確に分析・報告すること自体が要求を満たす場合は、判定不能という結果だけを理由にワークフロー全体を未完了にはしません。

### `question-analysis`へ送る不明点を限定する

製品仕様、期待結果、既存QA成果物の意味に関する不明点・矛盾は`question-analysis`へ送ります。

次のような運用上の不足は原則として該当E2E Skillのブロッカーとして扱います。

- テスト環境URL不足
- credential取得経路不足
- browser操作能力不足
- Playwright runtime不足
- 副作用許可不足
- cleanup方法不足

これらを製品仕様の質問として`question-analysis`へ機械的に送らないようにします。

`question-analysis`で不明点が解消した後は、従来どおり「意味が変わる最も早い責任Skill」へ戻します。E2E工程がその責任工程である場合は、新規E2E Skillも再開先になり得ます。例えばinspection中の仕様不明なら`e2e-test-inspection`、E2E実装判断へ影響する回答なら`e2e-test-implementation`、結果分析中の期待結果不明なら`e2e-test-result-analysis`へ戻します。不要な`test-case-design`等を機械的に挟みません。

再開先が上記の複数用途Skillの場合は、`再開Skill`だけでなく`再開対象 / 実行範囲`も常に必須で出力します。値はワークフロー状態で定義した正規値を再利用します。単一用途Skillでは`再開対象 / 実行範囲`を必須にせず、空欄を許容します。`question-analysis`の`assets/output-template.md`、guidance、決定論的評価もこの契約へ合わせます。

決定論的評価では、`再開Skill`が`CANONICAL_SKILLS`に含まれるかという正規名検証だけで完了しません。fixtureから再開先を一意に決められるケースでは、質問IDごとの期待`再開Skill`と、必要な場合は期待`再開対象 / 実行範囲`を実出力と比較します。同じブロッカーが「不明点 / 質問一覧」と「ブロック中範囲」の双方に出る場合は、両方の再開先が一致することも決定論的に確認します。具体的なfixture key名やassertion IDは既存形式へ合わせて実装時に決めます。
