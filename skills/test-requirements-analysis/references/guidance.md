# QA要求分析の判断基準

## 正本の境界

QA要求は「このQA活動で何を確かめ、どの品質目標を満たす必要があるか」を表します。製品がどう振る舞うべきか、特定の製品責務を何で検証するか、Product Riskをどう採点するかは別ownerの正本です。

| 情報                                    | 正本                                  |
| --------------------------------------- | ------------------------------------- |
| 製品の有効な仕様・Authority             | `spec-analysis`                       |
| 不明点・仕様競合・回答                  | `question-analysis` / `spec-analysis` |
| Product Risk・テスト深度                | `test-analysis`                       |
| 個別の製品検証責務（TR）                | `test-requirement-design`             |
| 全体のlevel/type/method/environment設計 | `test-architecture-design`            |
| 計画、source inventory、進捗、是正      | `test-management`                     |
| workflow routing/state                  | `qa-workflow`                         |

QA目標の文章を製品仕様へ転記したり、TR形式のIDをQA要求IDとして使ったりしません。QA要求のIDはartifact-localで、artifact ref・revision・scopeと組み合わせます。global counterは作りません。

## 要求の確定

1. 要求元の原文を必要最小限で参照し、要求元・source ref・revision・対象scopeを記録します。
2. QA活動の目的、品質特性、対象／対象外、対象build・期間、成功条件、成果物、優先度、制約を分けます。成功条件はQA活動の出口であり、製品の期待挙動を独自に作る欄ではありません。
3. 要求元の明示、Agentの提案、未回答、承認済みの状態を分けます。対象外やリスク受容に承認が必要なら、scope・artifact ref・revision・権限主体・承認証拠・失効条件を一致させます。
4. 仕様・Project Context・既存要求のrevisionが取れない場合は`unknown`とし、currentとみなしません。取得できた資料だけで確定できる独立した要求は残します。
5. すべての要求を有効な要求、理由付き対象外、未解決／担当・再開条件のいずれかへ閉じます。情報不足を「要求なし」や対象外に変換しません。

`QA目的・成功条件`テーブルでは、QA目的・品質目標・対象／対象外・活動の成功条件・根拠をそれぞれ記録します。source未取得時に値を補わず、草案／blockedのまま既存の`未取得`、`unknown`、`未確定`等と不足理由を明示します。未解決QA要求は同じIDの未決事項に結び、要求scopeを含む影響scope、担当、既存状態、再開条件を記録します。承認主体や担当、再開条件を推測しません。

## 変更と継続

- source ref・revision・内容範囲の変更を比較し、影響根拠がある要求だけを`要再確認`にします。
- QA要求の改版がarchitecture／計画の入力を変えるときだけ、該当refと旧／新revisionを引き渡します。
- 新規QA要求が不要な管理・報告要求では、既存current要求を読取再利用します。
- 保存providerが未選定、条件付き更新が未接続、readbackできない場合は永続化をblockedにします。出力を保存済みと偽らず、読み取りと草案作成を続けます。

## 品質ゲート

- QA目標、製品要求、Product Risk、TRが別の責務として示されている。
- 各確定要求に要求元とsource revisionがある。
- 対象／対象外、成功条件、制約、未決事項が欠落していない。
- `QA目的・成功条件`テーブルの5項目が空欄でなく、承認済みでは未取得・unknown・未確定の値を残していない。
- 草案／blockedで未確定値を残す場合は、`根拠`に不足理由を記録し、空欄や状態placeholderだけにしない。
- 未解決QA要求ごとにscope・担当・許可された状態・再開条件を持つ未決事項が一意に対応する。
- 未決事項が整っていても、承認対象scope内に状態`未解決`のQA要求が残るartifactは承認済みにしない。
- 承認済み表示は対象scope・ref・revisionと承認証拠に結び付いている。
- 取得不能／旧revisionをcurrentと扱わず、未取得を空集合と混同していない。
- 下流architecture／計画へowner ref・revision・scopeを渡し、第二の正本を作っていない。
