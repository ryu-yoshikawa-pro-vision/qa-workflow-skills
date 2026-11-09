---
name: qa-knowledge
description: 探索のFinding / Observationを含むQA candidateを、既存正本へ戻すか、project-localで継続利用するknowledgeとして有効化・再検証・更新・置換・検索する。specification、Risk、TC、current UIの正本化には使用しない。既存knowledgeを他の分析・設計の入力として読むだけの場合は使用しない。
---

# QA Knowledge

QA活動のcandidateが既存QA正本へ属するか、継続利用するknowledgeとして保存できるか、既存entryを更新・再検証・置換するか、currentなentryを検索します。既存knowledgeを他の分析の入力として使うだけなら、本Skillをgatewayにしません。

## 実行契約

1. `references/guidance.md`を読み、owner routing、triage、entry lifecycle、currentness、保存条件に従います。
2. source refs / revisions、scope、environment / version applicability、currentness dependency、completeなfixed-root listingを確認します。不足時はcandidateを元Activity / Finding / Follow-upに残し、entry化しません。
3. 仕様候補は`spec-analysis`、Product Risk / test focusは`test-analysis`、current UI factは`test-target-inspection`、formal design artifactは該当design Skillへ戻します。第二の正本を作りません。
4. knowledge root配下は1 entry = 1 artifactです。stable `entry_ref`はsemantic identityから決定論的に作り、central manifest、global counter、relation indexを追加しません。
5. `有効`entryはcurrentness dependencyが確認済みのときだけcurrent判断へ返します。root / repository HEAD変更だけで全entryをstaleにしません。
6. 同一identityのcreateはcanonical targetへのatomic create-if-absent、same-entry updateはentry自身のexpected revisionを渡すnative atomic conditional writeを必須にします。CASが使えない場合は`blocked`とし、別ref作成、semantic auto-merge、LLM fallbackをしません。
7. 同一identityの再検証・更新は同じentry refを新revisionにします。replacementはsemantic identity変更等に限り、old/newを安全にatomic反映できなければblockします。
8. secret実値、未検証Finding / Observationを保存しません。
9. `identity.kind` / `identity.scope_refs`は直下の`kind` / `scope_refs`と一致が必要で、不一致entryはcreate / read / update / lookupのすべてで拒否します。lookupは適用範囲が確実に異なるentryの依存不明では停止せず、適用範囲を判断できないentryとroot列挙不完全だけを`incomplete`にします。`read_entry()`の`entry_revision`はentry本体と別に引き継ぎます。create / updateは保存後のreadbackで確認したrevisionだけを返し、updateは保存先nativeのconditional write（provider）がなければblockします。他ownerへの引継ぎは`improvement_reference()`のstate（current / stale / blocked）・validation・resume・承認欄つきの参照だけです。

## 正規対象

- `triage`
- `create / update`
- `revalidation`
- `lookup / history`

## リソース

- lifecycle / routing / storage境界: `references/guidance.md`
- entry schema: `references/data-contract.md`
- 正規出力形: `assets/output-template.md`
- entry schema template: `assets/entry-template.md` (JSON block is the machine-readable body)
- production helper: `scripts/knowledge_runtime.py`
- deterministic validator: `evals/deterministic/validator.py`
