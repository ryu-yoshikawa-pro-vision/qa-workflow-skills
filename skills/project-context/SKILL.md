---
name: project-context
description: QA案件のProject Contextを初回発見・新規初期化・必要項目検証・差分更新・既存配置方針再利用する場合に使用する。既存16節とDEC/ASMを維持し、安全な保存条件を判定する。
---

# Project Contextの管理

## 実行契約

1. 対象案件を特定し、利用者が明示した文書または許可された候補rootだけを調べます。対象外repoや全filesystemを無断で探索しません。
2. 既存文書、確認済み不存在、候補重複、未指定、アクセス不能を区別します。候補が複数あれば自動統合しません。
3. 有効な既存文書がある場合は必要なfieldだけ検証して再利用します。初回の不存在が確認された場合のみ、既存qa-workflowの16節templateで作成候補を作ります。未知の案件値や承認を補いません。
4. Section 12/13のDEC/ASM正本は既存project_context_ids.pyを利用し、独立したID正本を新設しません。Section 16のstable key解析とcurrentnessは既存artifact_graph.pyを使用します。 正本ownerがこの文書の案件だけ、prepare-idsで既存ID helperによる採番・履歴を使用します。
5. 初回配置と人間編集方針は、既存正本と編集可能範囲を調べたうえで利用者に合意を求めます。合意済み方針のscope・revision・失効条件を確認し、条件が変わらなければ再承認を繰返しません。Section 14の正本参照を第二の正本にしません。
6. 決定論的な発見・候補作成・field更新の判定はscripts/project_context.pyを使用します。このhelperのdraftやreuse_candidateは保存成功・認証済み承認ではありません。
7. 書込みは案件の許可されたproviderによるnative create-if-absent／CAS、履歴取得、独立readback、実認証済み承認の条件が揃ってから実行します。不足時はその操作をblockし、読取専用分析を止めません。

## リソース

- 既存template: ../qa-workflow/assets/project-context-template.md
- 既存parse・必須項目検証: ../qa-workflow/scripts/artifact_graph.py
- 既存DEC/ASM履歴: ../qa-workflow/scripts/project_context_ids.py
- owner処理手順: references/guidance.md
- 入出力・保存条件: references/data-contract.md
- 結果の確認形式: assets/output-template.md
- helper: scripts/project_context.py
