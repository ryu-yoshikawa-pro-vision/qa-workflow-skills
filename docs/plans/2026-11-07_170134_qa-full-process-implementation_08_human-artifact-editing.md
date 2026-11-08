# 人間によるQA成果物の編集・正式取り込み・構成管理

## 対象と責務

この文書は[開発連動QA PlanのQ06](./2026-11-07_122247_development-qa-traceability.md#成果物の配置人間編集方針の初期合意q06)の実装・受入契約である。人間がMarkdown等の**編集可能なQA成果物を直接編集・レビュー**し、AIエージェントがその差分を安全に正式成果物へ反映する。人間の編集内容が機械検証に通っただけで仕様Authority・承認・正式テスト設計へ昇格することはない。

新しい配置管理Skill、全成果物共通の編集台帳、汎用schema、別のcanonical writerは作らない。案件の配置・編集方針は新設予定の`project-context`、受付・停止・再開・変更影響のroutingは既存`qa-workflow`、差分の意味確認・正式保存は**対象成果物のowner**が担当する。既存`ui-target-v1`の正本更新は`ui_target_package.py`の`materialize`経路に集約する。

| 対象                                   | 編集・判断の担当                                         | 正本への反映                                                                     |
| -------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 案件の成果物配置・編集方針             | `project-context`が調査・提案し、利用者が合意            | Project Contextの既存Section 12・14、または既存外部正本へのref／revision         |
| 期待仕様・Authority・AC・UNKNOWN       | `spec-analysis`、必要時`question-analysis`・正本の承認者 | 現行UI packageの該当箇所は`ui_target_package.py materialize`へ意味更新を渡す     |
| UI構造・操作・表示状態                 | 新設予定の`ui-target-analysis`                           | 同じUI package writerを利用。旧`spec-analysis`からの移行前は現行ownerを維持      |
| その他のQA成果物                       | TR／TCN／CI／TC等の各既存owner                           | 各ownerの既存正本更新・履歴・validator。UI packageの編集方式を無条件に流用しない |
| 人間が編集する作業用branch／作業用copy | 人間の編集者・レビュー担当                               | **未確定の変更案**。正式成果物の第二の正本として参照・再利用しない               |

## 既存UI packageの制約

現行`skills/spec-analysis/scripts/ui_target_package.py`は`ui-target-v1`の`00〜09`、`README.md`、`CHANGELOG.md`、`MANIFEST.md`と条件付きfileを一体として扱う。以下は実装時に変更せず守る契約である。

- `_read_package()`は`MANIFEST.md`、必須file、canonical UTF-8/LF、ファイル集合・順序、payloadのSHA-256、schema・version、参照等を検証する。標準Markdownを直接書き換えてManifestを更新しない場合は`manifest_mismatch`となる。
- `_execute_operation()`の`inspect`、`validate`、`build-machine-evidence`、`materialize(update)`は有効なpackageを前提とする。Manifest不一致の編集途中ファイルを`current`として検証・更新できたと扱わない。
- 正式更新は`inspect`の`update_snapshot`（`package_version`、payload SHA-256一覧、`manifest_sha256`）を`previous_snapshot`に渡す。`_validate_snapshot()`が差異を拒否し、`materialize`が新revision、CHANGELOG、README、MANIFEST、Machine Entityを生成・検証・確定する。
- 既存のpackage-local process lockとdirectory commit・recoveryは**このwriter経由の競合**を扱う。別のプロセスによる手動のin-place更新、外部Git branch／リモート保存先、複数workspace間の競合まで自動で排他すると見なさない。
- canonical root直下への任意の機能別directory追加、Manifestの手修正、固定標準fileの改名・分割、標準headingの追加・削除は既存`ui-target-v1`の更新として認めない。人間向けの機能別索引はID・revisionから導出する読取専用情報である。

## 人間が編集する場所と基準revision

1. **事前確認**：`project-context`の配置合意に基づき、対象案件・正本owner・編集権限・編集可能file／範囲・機能IDと参照先を示す。対象packageを`inspect`して有効なcurrentの`update_snapshot`を取得し、元の保存先ref／branch／commit、package version、scope／関連ID、編集対象pathを記録する。
2. **作業用の分離**：人間は承認済みの作業用branch／独立copyで実際のMarkdown等を直接編集する。未確定差分でcanonical rootを上書きしない。Gitの作業branchと正本を提供する保存先のversion／CASは別の検査対象として保持する。編集案のファイル名やフォルダ配置は既存schemaに従う。
3. **編集の入口**：機能別索引から、編集する正本fileと行・stable IDに辿れる。共有する条件・仕様は参照先のowner fileでのみ編集する。生成一覧は読取専用と明示し、`MANIFEST.md`、READMEの派生metadata、CHANGELOGの機械生成履歴、Machine Entities block等は編集入口としない。
4. **変更案の保持**：作業用branch／copyの元revision、実際の編集差分、レビュー記録と編集者を追跡する。差分には未承認の仕様変更や秘密情報が含まれ得るため、許可された保存先・共有範囲を守る。ファイルパスそのものを安定IDとして使わない。

現行canonical rootを人間が誤って**直接書き換えた**場合は、`inspect`／`materialize`が不正なcurrentを採用できないことを維持する。編集前後のbytesと元revisionの証拠を損なわないよう保全し、未検証の手作業でManifestを再計算して整合したことにしない。元の有効revisionを独立した履歴から取得できる場合だけ、編集差分を作業用変更案へ分離し、復旧・再反映の対象を確定する。元revisionを検証できない、または復旧・上書きの権限がない場合はそのpackageの更新を`blocked`とし、復旧・採用の判断元へ戻す。自動復元や破棄で人間の編集案を失わない。

## 編集差分の検証と意味更新

正本への書込み前に、対象ownerが次の順番で確認する。

1. **基準の整合**：正式に保存された元packageの有効性、編集案の基準version／hash、現在の正本version／hash、対象scopeとowner、作業branch／copyの由来を照合する。編集案を正本の`inspect`へ直接渡して正常なManifestであるかのように扱わない。
2. **変更範囲の抽出**：元の有効ファイルとのdiffから変更された標準file・section・table row・stable ID・column／proseを抽出する。変更されていない行、生成箇所、条件付きfileのTrigger、参照元・先、追加・削除された行を区別し、差分取得が不完全なら採用しない。対象の元ファイルが不明な変更は推測で新IDへ付け替えない。
3. **検証可能な構造**：既存の`ui-target-v1`のtable heading／列、canonical encoding、サイズ上限、正規ファイル集合、stable ID・参照規則とscopeを守る。編集により生成metadata、Manifest、Machine Entityが変わっていても、それらの編集を成果物更新として受け付けない。手入力された新規IDを正規の採番済みIDとみなさない。
4. **意味上の採用**：ownerが各変更のsource／Authority、期待挙動・実装観測の区別、参照先と影響範囲、意味上の同一性、承認の要否を確認する。既存IDは妥当な場合のみ`reuse`、追加は`@draft:<draft_key>`を利用してhelperに採番させ、廃止は根拠を持つ明示`retire_ids[]`へ渡す。手動削除を自動的な廃止とみなさない。仕様変更の承認やUNKNOWNの解決は各正本ownerに戻す。
5. **衝突の判定**：元revision以降に別のAgent／人間の更新があれば、変更されたID・field・proseと依存参照を比較し、競合箇所または意味上の関連が未確認なら該当scopeの採用を止める。同じ入力revisionと同じ意味が確認できる無変更・独立編集は現在の正本を保持して再評価する。単にGitの行単位mergeが成功しただけで意味上の衝突解決・承認済みとはしない。
6. **既存更新契約への変換**：採用する意味変更を`ui_target_package.py materialize`の既存`table_changes[]`、`keyed_table_updates[]`、`prose_updates[]`、`extension_file_updates[]`、`retire_ids[]`等の適切な入力へ写像する。変更前の正式packageを正本として扱い、編集案のpackage一式や改変Manifestをcopyして置換しない。`_validate_previous_model_transition()`と既存semantic／Machine Entity検証を通過させる。変換できない編集は承認済みとして黙って破棄せず、変更案と停止理由を保持する。

**成果物の識別**：差分の受付・結果は既存の保存可能な編集／レビュー参照に、元versionとsnapshot、対象scope・ID、変更したfield／prose、source／承認ref、採否・未確認理由、正本更新後のversion／receipt・readbackを対応付ける。新しい共通台帳・独立した編集manifestを正本として増やさない。生のsecret、PII、cookie、tokenを新しい証拠へ複製しない。

## 正式保存・変更影響・再開

1. **再読込と競合防止**：書込み直前にcanonical packageの有効なcurrentを再読込する。元snapshotから変更があれば該当diffを再照合し、元versionのまま無条件上書きしない。`materialize(update)`では検証済みの最新`previous_snapshot`を使用し、条件付き更新・排他が必要な外部保存先にはそのproviderが保証するnative CAS／ref更新を要求する。package-local lockを外部providerのCASの代わりにしない。
2. **一貫した確定**：既存writerが一括生成した`README.md`、`CHANGELOG.md`、`MANIFEST.md`、Machine Entityと各payloadを一つの正本revisionとして確定する。生成された`allocated_ids`・`retired_ids`・`changed_files`・package version／receiptを照合する。変更がないなら新versionを作らない。
3. **独立検証**：確定後に`inspect`／`validate`でManifestの一致、安定ID、参照、scope readiness、変更行・無変更行、機能別索引への到達、元snapshotからの差分と履歴を検証する。必要なら`build-machine-evidence`で下流Entityを再生成し、変更されたsource／Authority／UIの依存だけを`qa-workflow`へ渡す。下流を無関係に全再生成しない。
4. **結果不明と再開**：書込み・応答・readbackが失敗したら、元snapshot、更新要求のfingerprint／receiptと実際の保存先状態を照合する。確定済みの更新を別IDで再適用せず、未確定なら正本更新と下流の引継ぎを`blocked`とする。再開時も同じ元snapshot・編集差分・判断根拠を用い、古い基準から黙って再生成しない。
5. **直接編集とレビューの区別**：人間の編集とレビュー承認は別の行為として記録する。変更可能な正本fileでも、保存先の認可や仕様／テスト成果物の承認規則を省略しない。編集差分の内容に未承認の新仕様・削除・権限変更がある場合は、当該owner・承認者の判断を待つ。

## 実装対象と受入テスト

**実装対象**：`project-context`の初回配置・編集合意と既存Section 12／14、`qa-workflow`の必要時routing・現在性・再開、`ui-target-analysis`／移行前の`spec-analysis`の編集差分受付・意味更新、既存`ui_target_package.py`の検証・`materialize`・履歴・失敗処理とその呼び出し元。既存helperの契約を再利用し、正しい編集差分取得・変換に必要なSkill-local helper／テストだけ追加する。UI以外の成果物には各ownerの現行保存契約を適用し、中央編集エンジンを新設しない。

以下を`tests/skills/runtime/test_ui_target_package.py`、関連owner・workflowの決定論的テストと`EVALS.md`に従う実Agent評価へ追加し、該当結果を独立して記録する。

1. **通常編集**：有効`vNN`からworktree／copyで一つの既存行・proseを編集し、元IDと無変更行を保持して`materialize`経由で次revisionへ反映する。編集案の古いManifestは正式成果物として読み取られず、確定後のManifestと`validate`は成功する。
2. **新規行・廃止**：人間の新規行に手動採番IDを採用せず`@draft:<draft_key>`から割り当てる。行の削除だけではretireしない。承認された明示廃止と履歴・参照・影響範囲を検証する。
3. **変更禁止領域**：人間が`MANIFEST.md`、generated README metadata、CHANGELOG、Machine Entities、標準heading／file名を直接書き換えた場合、改変値を正本へ採用しない。不正なTrigger・参照や正本の形式不一致は対象の更新を拒否する。
4. **無承認の意味変更**：実装観測だけで期待仕様を上書きする編集、Authority・承認根拠が欠けるAC変更、UNKNOWNの無根拠解決を拒否し、元の有効な正本を保持する。
5. **同時編集**：同じ元snapshotから同一ID・fieldを人間とAgentが更新した場合に競合を拒否し、無関係な行の変更は依存確認後に局所反映する。Gitのmerge成功だけで承認済みとしない。
6. **currentの直接改変**：canonical rootを直接編集してManifestが不一致になった場合、元versionを勝手に上書き・自動復旧・編集破棄せず、変更案と有効な元revisionを分離できたときだけ正式反映する。元revisionの検証不能はblockedにする。
7. **失敗・再開**：保存途中の障害、二重受付、commit済み応答消失、readback不一致、権限不足、保存先native CASなし、別セッション再開を検証し、誤成功・ID二重割当・編集差分喪失を防止する。
8. **人間の確認経路**：機能IDから正本file・行・関連ID・差分へ辿れ、共通成果物は一つの正本で編集できる。変更後に下流の関連scopeだけ要再検証になり、既存UI package・通常`spec-analysis`・TR／TCN／CI／TCの直接利用・migration／legacyの互換性が維持される。

**完了条件**：上記の各受入に、編集案の入力・元revision・実際の保存／拒否結果・変更された正本revision・検証証拠が揃うこと。実Agentが人間の編集を読んだだけ、形式validatorだけがPASS、または編集案が正本と無関係な場所に存在するだけでは完了としない。未検証の外部保存先・権限・同期方式を成功済みと扱わない。
