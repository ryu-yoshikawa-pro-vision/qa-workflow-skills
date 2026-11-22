---
name: question-analysis
description: 仕様・QA成果物の曖昧さ、矛盾、欠落、未解決事項を分析し、ブロッカー・要確認・仮定可能・提案・任意に分類するSkill。下流成果物を止めるべきか、局所的に継続できるか、承認済み仮定として扱えるかを判断するときに使用する。
---

# 不明点・矛盾分析

## 実行契約

1. 実行前に`references/guidance.md`を読み、分類基準、情報源優先順位、停止・継続判断、回答の正規化、品質ゲートに従います。
2. 回答がなくても妥当な成果物を作れるかを、影響する下流成果物ごとに判断します。
3. 情報源優先順位や既存決定で解消済みの事項を再質問しません。
4. `仮定可能`は仕様ではありません。最終的な期待結果の根拠へ使う場合は、権限を持つユーザーまたはステークホルダーが明示的に承認した`ASM-xxx`として分離します。
5. ブロッカーは可能な限り影響範囲だけに限定します。
6. 既定出力形式が必要な場合は`assets/output-template.md`を使用します。UI target package由来のUNKNOWN IDと質問IDの割当・参照検証には`question_ids.py`を使用します。
7. 他Skillを参照するときは正規Skill名を使用します。
8. 回答後の再開先は既存設計Skillだけに限定しません。意味が変わる最も早い担当Skillが責任工程ならそこへ戻し、複数用途Skillでは再開対象 / 実行範囲も出力します。生きた対象情報の確認・更新なら`test-target-inspection`、詳細TCの今回run条件や未解決実行事項なら`test-execution`、repo Playwright E2Eの事実・実装・実行結果なら対応する既存E2E Skillへ戻します。
9. 最終出力前に、実際に利用した入力が本Skillの入力契約を満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成した成果物へ本Skill自身の出力契約・品質ゲートを適用して自己検証します。明白かつ局所的で新しい領域固有の判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。未解決事項や仮定の分類・承認状態を自己検証の名目で変更せず、仕様根拠不足や上流判断不足があれば既存の停止条件・ブロック中・ルーティングに従います。最終確認後も本Skill自身の契約違反が残り、既存の停止条件・ブロック中・ルーティングに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。自己検証の経緯や修正回数は出力しません。

## 決定論的runtimeとの関係

本Skillは独自のruntime dispatchを持ちません。上流Machine Entityの内容、依存fingerprint、`current` / `stale` / `legacy` / `deleted`状態を根拠として不明点を分類し、runtime結果がないことや`unknown`を推測で解消しません。下流へ渡す承認済み仮定とブロッカーは安定IDで追跡します。

## 回答フォームとの接続

複数の確認事項をHTMLで回答してもらう必要がある場合だけ、既存の質問一覧を`agent-answer-form`へ渡します。`Q-xxx`は再採番せず、質問の分類・ブロック中範囲・承認状態を変更しません。フォームから返却された回答はIDで照合した後、上記の回答正規化と再開先判断を本Skillで行います。保留や推奨案を正式回答・承認として扱いません。通常のMarkdown質問一覧も引き続き利用できます。

## インターフェース

- **入力**: 分類対象となる不明点・矛盾・欠落・未解決事項と、その判断に利用できる仕様分析、現在有効な仕様根拠、権威ある情報源、正本一覧等の根拠。
- **処理**: 各論点を`ブロッカー` / `要確認` / `仮定可能` / `提案・任意`へ分類し、停止・継続範囲と回答後の正規化先・再開先を決めます。
- **出力**: 不明点・矛盾の分類、根拠、影響範囲、回答なしの場合の扱い、ブロック中範囲、回答後の正規化先、再開先Skill / 対象を明示します。

## 保存（任意）

- 分析結果を保存する場合は、`assets/output-template.md` の見出しと表をそのまま使い、対象範囲（領域など）ごとに `question-analysis/<scope-id>.md` として保存します。保存先branchは案件・kindごとに分けます（例: `qa-artifacts/<project>/question-analysis`）。
- 保存前に `scripts/question_document.py validate` で形式を検証し、通過した文書だけを project-context の `artifact_host.py save-document --kind question-analysis` で保存します。検証に失敗した文書は保存されず、確認記録も登録されません。
- `--user-confirmed-ref` は、利用者がその文書を確認した後にだけ渡します。AIが確認前に値を作ってはなりません。確認記録は自己申告であり、認証ではありません。
- 更新する場合は、保存直前に `read` で現在のrevisionを取り直し、`--expected-revision git:<sha>` に渡します。古い値は `revision_conflict` で止まり、データは失われません。
- 保存の理由コード、証跡記法、既知の制約は `references/persistence-contract.md` に従います。検証は形式だけを見るため、意味の正しさ（分類の妥当性、質問の必要性、UNKNOWNの存在）は本Skillの自己検証と `question_ids.py` の既存検証で扱います。

```
python3 scripts/question_document.py validate --document-file <file> --scope-id <scope-id> --source-revision <rev>
python3 ../project-context/scripts/artifact_host.py save-document --kind question-analysis --repo <store-repo> --branch qa-artifacts/<project>/question-analysis --project-ref <project> --artifact-ref question-analysis/<scope-id>.md --document-file <file> [--expected-revision git:<sha>] --source-ref <ref> --source-revision <rev> --change-reason <reason> --user-confirmed-ref <confirmation>
```

- 保存契約（保存・検証・理由コード）: `references/persistence-contract.md`

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
- Q ID / UNKNOWN参照 helper: `scripts/question_ids.py`
- 保存の検証 helper: `scripts/question_document.py`
- 保存契約: `references/persistence-contract.md`
