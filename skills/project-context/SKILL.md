---
name: project-context
description: QA案件のProject Contextを初回発見・新規初期化・必要項目検証・差分更新・既存配置方針の再利用で扱う。「Project Contextの有無確認・初期化・確認・更新、保存先や編集方針の承認確認」を求められたら、自分で調べる前に必ずこのSkillを読み込む。既存16節とDEC/ASMを維持し、安全な保存条件を判定する。
---

# Project Contextの管理

## 実行契約

1. 対象案件を特定し、利用者が明示した文書または許可された候補rootだけを調べます。対象外repoや全filesystemを無断で探索しません。
2. 既存文書、確認済み不存在、候補重複、未指定、アクセス不能を区別します。候補が複数あれば自動統合しません。
3. 有効な既存文書がある場合は必要なfieldだけ検証して再利用します。初回の不存在が確認された場合のみ、既存qa-workflowの16節templateで作成候補を作ります。未知の案件値や承認を補いません。
4. Section 12/13のDEC/ASM正本は既存project_context_ids.pyを利用し、独立したID正本を新設しません。Section 16のstable key解析とcurrentnessは既存artifact_graph.pyを使用します。 正本ownerがこの文書の案件だけ、prepare-idsで既存ID helperによる採番・履歴を使用します。
5. 初回配置と人間編集方針は、既存正本と編集可能範囲を調べたうえで利用者に合意を求めます。合意済み方針のscope・revision・失効条件を確認し、条件が変わらなければ再承認を繰返しません。Section 14の正本参照を第二の正本にしません。
6. 決定論的な発見・候補作成・field更新の判定はscripts/project_context.pyを使用します。このhelperのdraftやreuse_candidateは保存成功・認証済み承認ではありません。
7. 明示されたローカル保存providerではscripts/artifact_store.pyのLocalArtifactStoreとpersist_preparedを使用します。承認方式が`trusted-callback`の場合、認証済み権限・承認の照合は信頼済み呼出し元のauthorize callbackで行い、CLI入力だけで許可しません。書込みは案件の許可されたproviderによるnative create-if-absent／CAS、履歴取得、独立readback、実認証済み承認の条件が揃ってから実行します。不足時はその操作をblockし、読取専用分析を止めません。保存の承認方式（`approval_source`）は、`authorize`を渡していなければ既定の`user-confirmed`、渡していれば`trusted-callback`です。`user-confirmed`は、ユーザーの確認後にホストが登録した確認記録との完全一致で判定します（詳細はreferences/data-contract.md）。`user-confirmed`のユーザー確認は自己申告であり認証ではありません。`trusted-callback`は、信頼済みhostが承認サービスを注入する場合の追加検証（より強い承認）で、任意です。ホストはユーザーが当該成果物を明示的に確認した後にのみ `record_user_confirmation` を呼ぶ。AIが確認前に呼んではならない。ホスト経由（`scripts/artifact_host.py` の `save-prepared`）のuser-confirmed保存は、自己申告の確認記録であり認証ではありません。実認証済み承認の条件を満たすものではないため、ユーザーの確認が得られた候補に限って実行します。

## リソース

- 既存template: ../qa-workflow/assets/project-context-template.md
- 既存parse・必須項目検証: ../qa-workflow/scripts/artifact_graph.py
- 既存DEC/ASM履歴: ../qa-workflow/scripts/project_context_ids.py
- owner処理手順: references/guidance.md
- 入出力・保存条件: references/data-contract.md
- 結果の確認形式: assets/output-template.md
- helper: scripts/project_context.py

既存のGit管理Markdownを正本として更新する場合は`scripts/git_artifact_store.py`の`GitArtifactStore`を利用します。Git refを条件付き更新（commit SHAでCAS）し、元のMarkdown pathと旧revisionをGit履歴に保持します。ローカルSQLite正本への移行は行いません。両保存先とも承認方式に応じた判定を行い、読取にも権限確認を適用します（`user-confirmed`では、読取は登録済み案件scopeの判定になります）。`trusted-callback`では信頼済みhostからの認可callbackを必須とします。既定の`user-confirmed`では、確認記録の完全一致が判定になります。
