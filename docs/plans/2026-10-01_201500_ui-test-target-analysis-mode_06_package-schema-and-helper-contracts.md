# UIテスト対象分析モード: package schema / helper contracts / legacy migration

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

関連Plan:
- 2026-10-01_201500_ui-test-target-analysis-mode_02_spec-analysis-package.md
- 2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md
- 2026-10-01_201500_ui-test-target-analysis-mode_09_runtime-entity-and-test-requirement-contracts.md

この文書は、UIテスト対象分析packageの機械可読schema、Skill-local helperのI/O、Machine Entity bridge、legacy package移行、filesystem safetyの正本です。UI操作のUS / UC / Behavior / AC semantic contractは `2026-10-01_201500_ui-test-target-analysis-mode_08_behavior-decomposition-and-acceptance-traceability.md` を正本とします。

LLMが仕様意味を判断し、helperはその判断結果の形式・参照・派生値だけを扱います。

## 1. package schema version

成果物revisionの `vNN` とpackage構造versionを分離します。

- package schema version: `ui-target-v1`
- package version: `v00`, `v01`, ...

READMEとMANIFESTの両方へ `ui-target-v1` を記録し、helperが一致を検証します。

schema versionがないpackageはlegacy / unversioned packageとして扱い、current schemaとして直接validateしません。

## 2. README schema

READMEには自由記述の概要に加え、次の2表をexact heading / exact headerで持ちます。

### Package metadata

| 項目 | 値 |
| --- | --- |
| Package Schema Version | ui-target-v1 |
| Package Version | v00 |
| Previous Package Version | - |
| Current UNKNOWN Count | 0 |

`Previous Package Version` は初回なら `-`、継続更新なら直前revisionを記録します。legacy移行時はlegacy側の明示versionを記録できます。

### Current payload files

| 順序 | ファイル | 種別 |
| ---: | --- | --- |
| 1 | 00_scope_and_context.md | core |

この表はMANIFESTのpayload file listと完全一致させます。

`MANIFEST.md` はcontrol fileのため、このpayload一覧へ含めません。

## 3. package file classification

### required core payload files

- README.md
- 00_scope_and_context.md
- 01_ui_structure_and_navigation.md
- 02_behavior_and_business_rules.md
- 06_spec_inconsistencies_and_pending.md
- 07_current_unknowns.md
- 09_authority_and_traceability.md
- CHANGELOG.md

### 条件付き必須payload files

`00_scope_and_context.md` のfile applicability判定に従います。

- 03_fields_and_validation.md
- 04_flows_and_data.md
- 05_notifications_and_external_interactions.md
- 08_repository_implementation_status.md

statusがrequiredならfileが必須、not-applicableならfileを作成しません。blockedならpackageを完成扱いしません。

### extension payload files

- 10_<domain-slug>.md以降

extension fileは00に責務・分割理由が宣言された場合だけ許可します。

### control file

- MANIFEST.md

MANIFEST自身はpayload / hash対象に含めません。

## 4. canonical file order

helperが使用するpayload順を固定します。

1. README.md
2. 00_scope_and_context.md
3. 01_ui_structure_and_navigation.md
4. 02_behavior_and_business_rules.md
5. 03_fields_and_validation.md（存在時）
6. 04_flows_and_data.md（存在時）
7. 05_notifications_and_external_interactions.md（存在時）
8. 06_spec_inconsistencies_and_pending.md
9. 07_current_unknowns.md
10. 08_repository_implementation_status.md（存在時）
11. 09_authority_and_traceability.md
12. 10_<domain-slug>.md以降を番号昇順
13. CHANGELOG.md

MANIFEST.mdはcontrol fileとして最後に別扱いします。

domain fileは `10_<lowercase-kebab-case>.md` 以降の連番とします。同じ番号・同じslugの重複を拒否します。

## 5. structured table schemas

自由記述sectionはLLMが対象に合わせて追加できます。ただしhelperが参照整合を検証するstructured tableは以下のexact heading / exact headerを使います。

### 5.1 00_scope_and_context.md

#### 分析対象機能scope一覧

| Scope ID | 対象機能 / 領域 | UI操作判定 | Behavior Decomposition | 関連UNKNOWN ID | 根拠 / 関連仕様項目ID |
| --- | --- | --- | --- | --- | --- |

標準ID: `SCOPE-xxx`

許可値:
- UI操作判定: あり / なし / 未確定
- Behavior Decomposition: required / not-applicable / blocked

固定対応:
- あり → required
- なし → not-applicable
- 未確定 → blocked + 関連UNKNOWN ID必須

#### 条件付き必須file applicability

| ファイル | 状態 | 根拠 / 関連仕様項目ID | 関連UNKNOWN ID |
| --- | --- | --- | --- |
| 03_fields_and_validation.md | required / not-applicable / blocked |  |  |
| 04_flows_and_data.md | required / not-applicable / blocked |  |  |
| 05_notifications_and_external_interactions.md | required / not-applicable / blocked |  |  |
| 08_repository_implementation_status.md | required / not-applicable / blocked |  |  |

triggerの意味判断はLLMが行います。helperは4rowの存在、許可値、blocked時のUNKNOWN、required / not-applicableと実file / MANIFESTの一致を検証します。

#### 案件固有構造ID

| Prefix | 意味 |
| --- | --- |
| CSV | CSV export |

mode標準prefix以外を使う場合だけ記載します。

- Prefixは大文字英数字、先頭英字、2〜16文字
- 標準prefixとの重複禁止
- helperはこの表に宣言されたprefixだけを案件固有prefixとして許可
- prefixを追加する意味判断はLLM

### 5.2 01_ui_structure_and_navigation.md

#### UI構造一覧

| 構造ID | 種別 | 名称 | Path / 識別子 | 親構造ID | 関連仕様項目ID | 関連構造ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |

許可する標準種別 / prefix:

- PAGE → PAGE-xxx
- STATE → STATE-xxx
- VIEW → VIEW-xxx
- STEP → STEP-xxx
- MODAL → MODAL-xxx
- BROWSER-DIALOG → BDLG-xxx
- PANEL / POPOVER / GLOBAL UI → PANEL-xxx
- EXTERNAL → EXT-xxx
- SHARED PAGE → SHARED-xxx

`Path / 識別子` はroute不明時 `PATH-TBD` を許可します。

### 5.3 02_behavior_and_business_rules.md

scope単位のsemantic contractは `_08` を正本とします。structured tableは次へ固定します。

#### UI操作一覧

| 操作ID | Scope ID | Actor / Role | 対象構造ID | 操作 | 関連仕様項目ID | 対応UC ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### User Story一覧

| US ID | Scope ID | Actor / Role | Goal | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- |

#### Use Case一覧

| UC ID | 関連US ID | Use Case | Trigger | Preconditions | Success Postcondition | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### Behavior一覧

| Behavior ID | UC ID | 結果分類 | 振る舞い | Postcondition / Result | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### Use Case振る舞い完全性

| UC ID | 結果分類 | 判定 | 関連Behavior ID | 関連UNKNOWN ID | 理由 / 根拠 |
| --- | --- | --- | --- | --- | --- |

#### Acceptance Criteria一覧

| AC ID | Behavior ID | Acceptance Criteria | 関連仕様項目ID | 関連構造ID |
| --- | --- | --- | --- | --- |

not-applicable / blocked scopeはUS / UC / Behavior / ACを確定済みrowとして持ちません。US / UC / Behaviorのblocked rowは `_08` のUNKNOWN contractへ従い、ACにはblocked rowを作りません。

#### ビジネスルール一覧

| ルールID | ルール名 | ルール詳細 | 適用条件 | 関連仕様項目ID | 関連構造ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- |

標準ID: `RULE-xxx`

### 5.4 03_fields_and_validation.md

#### 項目・バリデーション一覧

| 項目ID | 対象構造ID | ラベル / 名称 | 要素タイプ | 入力 / 表示仕様 | 制約 / バリデーション | 関連仕様項目ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |

標準ID: `FIELD-xxx`

### 5.5 04_flows_and_data.md

#### 処理フロー一覧

| フローID | 処理名 | トリガー / 操作 | 手順 / 状態遷移 | 結果 | 関連仕様項目ID | 関連構造ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |

標準ID: `FLOW-xxx`

手順が複数ある場合は同一cell内で `<br>` 区切りにし、同一FLOW IDを複数rowへ重複させません。

### 5.6 05_notifications_and_external_interactions.md

#### 通知・外部連携一覧

| 連携ID | 種別 | 名称 | 発火条件 | 宛先 / 遷移先 | 内容 / 挙動 | 関連仕様項目ID | 関連構造ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

標準ID:

- 通知 / メール → NOTIFY-xxx
- 外部連携 / 外部遷移イベント → INTERACT-xxx

外部画面そのものは01の `EXT-xxx` がownerであり、05では `関連構造ID` から参照します。

### 5.7 06_spec_inconsistencies_and_pending.md

#### 仕様矛盾・保留一覧

| ISSUE ID | 種別 | 内容 | 根拠 | 影響範囲 | 関連仕様項目ID | 関連構造ID | 状態 / 扱い |
| --- | --- | --- | --- | --- | --- | --- | --- |

標準ID: `ISSUE-xxx`

`種別` は矛盾 / 保留 / 実装差分起因確認 / その他。意味分類はLLMが行います。

### 5.8 07_current_unknowns.md

#### Current UNKNOWN一覧

| UNKNOWN ID | 確認事項 | 根拠 | 影響範囲 | 関連構造ID | 次の扱い |
| --- | --- | --- | --- | --- | --- |

`UNKNOWN ID` は09の `分類=UNKNOWN` かつ `現在有効か=Yes` のUNKだけを許可します。

### 5.9 08_repository_implementation_status.md

#### Repository実装状況

| 実装確認ID | 対象 | 観測事実 | 関連仕様項目ID | 判定 | 証拠 / 参照 | 備考 |
| --- | --- | --- | --- | --- | --- | --- |

標準ID: `IMPL-xxx`

`判定` は一致 / 差分 / 未実装 / 実装のみ / 判断不能。

この判定は仕様とrepository事実を比較したLLMの意味判断であり、helperは許可値と参照存在だけを検証します。

### 5.10 09_authority_and_traceability.md

既存 `skills/spec-analysis/assets/output-template.md` の意味契約を維持し、次をexact heading / exact headerで持ちます。

#### 情報源 / 正本参照一覧

| 参照ID | 情報源 / 正本一覧 | 権威 / 優先順位 | 鮮度 / バージョン | 対象範囲 | 参照 / 備考 |
| --- | --- | --- | --- | --- | --- |

#### 分析項目

| 項目ID | カテゴリ | 内容 | 分類 | 情報源 / 正本参照 | 現在有効か | 補足 / 上書き / 置換関係 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |

UI target modeでは `現在有効か` を `Yes / No` に固定します。

#### 現在有効な仕様根拠

| 仕様根拠ID | 種別 | 現在有効な内容 | 適用範囲 | 情報源 / 正本一覧 | 関係 | 関連仕様根拠ID |
| --- | --- | --- | --- | --- | --- | --- |

#### 後続Skillへの補足

| 項目 | 関連項目ID | 後続Skillへの関連 / 備考 |
| --- | --- | --- |

#### Machine Entity（機械証拠）

人間向けheadingとしてこのsectionを持ち、その配下の機械ブロックは既存runtime contractに合わせて次のexact形式を使用します。

`### Machine Entities: spec-analysis`

```json
{"schema_version":"entity-state-v1","skill":"spec-analysis","entities":[]}
```

`entities` は§9のdeterministic bridge結果をそのまま使用します。LLMがMachine Entity wrapper / fingerprintを計算・再構築しません。`expected_entity_identities` や `implementation_fingerprint` はhelper responseには保持しますが、artifactの `Machine Entities` block schemaへ混入させません。

### 5.11 10+ domain files

案件固有domain fileは自由な説明sectionを持てます。

structured tableを置く場合:

- primary ID列名を `項目ID` に固定する
- `関連仕様項目ID` を持つ
- UI構造へ関連する場合 `関連構造ID` を持つ
- primary ID prefixは00の `案件固有構造ID` で宣言する

helperは宣言されたheader名のexact ID参照だけを検証し、proseからIDを推測抽出しません。

## 6. ID rules

標準prefix:

- SCOPE
- PAGE
- STATE
- VIEW
- STEP
- MODAL
- BDLG
- PANEL
- EXT
- SHARED
- FIELD
- RULE
- FLOW
- NOTIFY
- INTERACT
- ISSUE
- IMPL
- UIOP
- US
- UC
- BH
- AC

形式は `PREFIX-001` ～ `PREFIX-999`。

`next-id` はLLMがnewと判断した後にのみ使用し、current + previousで既知の同prefix最大値+1を返します。

999を使用済みなら自動的に4桁へ拡張せず `id_space_exhausted` でblockedを返します。prefix拡張はschema変更として別途扱います。

SPEC / DEC / INF / UNK / SRC / ASMは既存spec-analysisのID契約を使用します。

## 7. helper CLI common contract

### 7.1 基本

`ui_target_package.py` と `unknown_links.py` は次を共通原則とします。

- Python 3.11標準ライブラリのみ
- 業務入力はstdinの1 JSON objectだけ
- stdoutは1 JSON object + LFだけ
- CLI positional argument / input file argument / environment variableを業務入力に使わない
- handled invalid input / limit exceededはexit 0でstructured blocked resultを返す
- unexpected internal errorだけexit 1
- handled errorでstderrへ業務データを出さない
- unknown top-level fieldを拒否
- aggregate stdin / stdout上限は既存runtime契約に合わせ16 MiB
- JSON duplicate keyを拒否

### 7.2 common response

成功:

```json
{
  "valid": true,
  "status": "ok",
  "operation": "validate",
  "payload": {},
  "issues": []
}
```

handled failure:

```json
{
  "valid": false,
  "status": "blocked",
  "operation": "validate",
  "payload": {},
  "issues": [
    {
      "issue_type": "invalid_input",
      "blocking": true,
      "message": "..."
    }
  ]
}
```

issue_typeは少なくとも:

- invalid_input
- limit_exceeded
- package_schema_mismatch
- path_outside_package
- symlink_not_allowed
- file_unreadable
- reference_not_found
- duplicate_id
- id_space_exhausted
- manifest_mismatch

## 8. ui_target_package.py operations

### inspect

stdin:

```json
{"operation":"inspect","package_root":"<path>"}
```

payload:

- package_schema_version
- package_version
- previous_package_version
- payload_files[]
- file_applicability[]
- domain_files[]
- canonical_item_ids[]
- current_unknown_ids[]
- resolved_unknown_ids[]
- current_unknown_count
- structural_ids[]
- exact_reference_index[]
- unresolved_structural_issues[]

`resolved_unknown_ids` は09で `分類=UNKNOWN` かつ `現在有効か=No` のUNK。

### validate

stdin:

```json
{"operation":"validate","package_root":"<path>"}
```

§2〜§6およびfilesystem safetyを検証します。

### next-version

stdin:

```json
{"operation":"next-version","previous_version":"v14"}
```

payload: `{"next_version":"v15"}`

default vNN policy以外では使用しません。

### next-id

stdin:

```json
{
  "operation":"next-id",
  "prefix":"PAGE",
  "known_ids":["PAGE-001","PAGE-002"]
}
```

payload: `{"next_id":"PAGE-003"}`

semantic identityは判断しません。

### build-manifest

stdin:

```json
{"operation":"build-manifest","package_root":"<path>"}
```

payloadへcanonical MANIFEST Markdownとpayload file metadataを返します。

LLM / AgentがSHA-256を手計算しません。

### impact

stdin:

```json
{
  "operation":"impact",
  "package_root":"<path>",
  "changed_ids":["SPEC-021","RULE-003"]
}
```

payloadへexact reference indexから `affected_files[] / affected_rows[]` を返します。

意味上の修正要否は判断しません。

### build-machine-evidence

stdin:

```json
{"operation":"build-machine-evidence","package_root":"<path>"}
```

§9に従い09からnormalized Authority inputを生成して既存 `authority_entities.py` のbuilderを呼び、02のcurrent ACと親US / UC / Behavior chainからAcceptance Criterion Machine Entityを生成して統合します。

payload:

- normalized_authorities[]
- normalized_acceptance_criteria[]
- normalized_skill_input
- acceptance_criterion_entities[]
- machine_entities[]
- expected_entity_identities[]
- implementation_fingerprint
- machine_entities_block（`schema_version` / `skill` / `entities` だけを持つartifact保存用object）

AgentがMachine Entity wrapper / content fingerprintを手組みしません。

### project-eval

semantic:

```json
{
  "operation":"project-eval",
  "package_root":"<path>",
  "projection":"semantic"
}
```

対象:

- README
- 00 / 01 / 02 / 06 / 07 / 09
- 03 / 04 / 05 / 08のうちfile applicability=requiredのcurrent file
- 10+ current extension files

除外:

- CHANGELOG
- MANIFEST

過去仕様を含むCHANGELOGをsemantic Judgeへ混ぜません。

deterministic:

```json
{
  "operation":"project-eval",
  "package_root":"<path>",
  "projection":"deterministic"
}
```

対象:

- 全payload file
- MANIFESTを最後にcontrol fileとして追加

各file前へ `<!-- FILE: <relative-path> -->` を付け、内容を変更せず連結します。

## 9. deterministic Authority / Acceptance Criterion Machine Entity bridge

LLMが09へCurrent Effective Authorityを確定し、02へcurrent US / UC / Behavior / ACを確定した後、`build-machine-evidence` がAuthority + current ACを固定変換します。

### 9.1 Authority

Authority部分は既存 `authority_entities.py` のnormalized input / builder契約をそのまま再利用します。

規則:
- 情報源 / 正本一覧と関連仕様根拠IDの複数IDは `<br>` 区切り
- 空参照は空array
- 種別は既存SPEC / DECISION / 承認済みASM
- INF / UNKNOWNはCurrent Effective Authority inputへ含めない
- LLMがJSON wrapper、fingerprint、expected identityを再生成しない

### 9.2 Acceptance Criterion

current ACだけを `spec-analysis / acceptance_criterion / AC-xxx` Entityへ変換します。blocked ACはEntity化しません。

AC Entity contentは `_08` のcurrent chainから次を固定projectionします。

- ac_id / acceptance_criteria
- behavior_id / result classification / behavior / postcondition
- uc_id / use case / trigger / preconditions / success postcondition
- user_stories[] の us_id / actor_role / goal
- scope_id
- authority_refs[]
- structure_refs[]

AC Entity dependencyは参照current Authority Entityへ固定します。

US / UC / BehaviorをMachine Entity typeへ追加しません。親chainをAC contentへ含めるため、親意味変更でAC content fingerprintが変わります。

### 9.3 normalized_skill_input

`build-machine-evidence` はqa-workflow / coverage-analysisへ渡すcanonical spec-analysis normalized inputも返します。

```json
{
  "authorities": [{"authority_id":"SPEC-001"}],
  "acceptance_criteria": [{"ac_id":"AC-001"}]
}
```

Agent / LLMがMarkdownからnormalized inputやexpected Entity一覧を再構築しません。

shared runtime contractの `acceptance_criterion` type / expected Entity / requirement-structure-v2連携は `_09_runtime-entity-and-test-requirement-contracts.md` を正本とします。

## 10. unknown_links.py contract

stdin:

```json
{
  "artifact_markdown": "<question-analysis output>",
  "current_unknown_ids": ["UNK-001"],
  "resolved_unknown_ids": ["UNK-002"]
}
```

helper自身が `不明点 / 質問一覧` の `ID` / `関連UNKNOWN ID` 列をparseします。

payload:

- question_links[]
- unknown_refs[]
- issues[]

検証:

- Q-xxx形式
- UNK-xxx形式
- `<br>` 区切り
- current UNKNOWNへの存在参照
- 同一Q内duplicate
- resolved-only UNKNOWNのcurrent question参照

QとUNKの意味的対応はLLM判断です。

spec-analysis modeからquestion-analysisへ進む場合、`ui_target_package.py inspect` が返す `current_unknown_ids[] / resolved_unknown_ids[]` をそのままunknown_links入力へ渡します。Agentが09からID集合を手作業で再構築しません。

## 11. filesystem safety

`ui_target_package.py` が読むpathに次を適用します。

- `package_root` は存在するdirectory
- absolute / relativeどちらの入力でもresolve後のrootを固定
- payload / MANIFESTからのabsolute path禁止
- `..` によるroot外参照禁止
- symlink file / symlink directory拒否
- regular fileだけを読む
- UTF-8 strict decode
- current package全read bytes合計16 MiB以下
- duplicate normalized relative path拒否
- case-sensitive canonical filenameを要求
- filesystem read失敗を意味上のUNKNOWNへ変換せずblocked

network accessは行いません。

## 12. MANIFEST schema

exact heading:

### Package manifest

| 順序 | ファイル | SHA-256 |
| ---: | --- | --- |

MANIFEST先頭に次を持ちます。

- Package Schema Version: ui-target-v1
- Package Version: vNN

tableにはpayload filesだけをcanonical順で列挙します。

- MANIFEST自身は含めない
- SHA-256はraw file bytes
- READMEのCurrent payload filesとfile集合 / 順序一致
- CHANGELOGもpayload / hash対象
- semantic projectionではCHANGELOGを除外するがMANIFEST上はcurrent package payloadとして保持

## 13. CHANGELOG contract

最新versionを先頭に置き、exact heading:

`## vNN`

各version entryは最低限:

- 変更概要
- 変更 / 解消したstable ID
- 新しいUNKNOWN / 解消したUNKNOWN
- 影響file

説明内容はLLMが作成します。

helperは最新headingがPackage Versionと一致することだけを検証します。

## 14. legacy / unversioned package migration

今回のmode導入前に作成済みの仕様理解packageを更新対象として受け取れるようにします。

### 14.1 migrationの基本

schema versionがないpackageを自動変換する汎用migration engineは作りません。legacy file構成は案件ごとに意味が異なるため、semantic mappingはLLMが行います。

LLMは:

1. legacy packageのcurrent内容とstable IDを読む
2. 新schemaの00〜09 / domain fileへ意味をmapする
3. semantic identityが同じ既存SPEC / DEC / INF / UNK / PAGE等は可能な範囲でID維持
4. 新しいentityだけnewと判断し、next-idを使う
5. legacyで未確定だった内容を推測で確定しない
6. current packageに不要な履歴はCHANGELOG / migration noteへ残し、current viewへ混ぜない

helperは変換後packageだけをvalidateします。

### 14.2 version

legacy packageに明示 `vNN` がある場合、default policyではnext-version結果を新package versionとします。

例:

- legacy v14
- migration後 current package v15
- Package Schema Version = ui-target-v1
- Previous Package Version = v14

legacy versionが確定できない場合は推測せず、new schema側を `v00` から開始し `Previous Package Version = legacy-unversioned` とします。仕様意味ではなく成果物管理metadataなので、version不明だけを理由に分析全体をblockしません。

### 14.3 legacy progress file

legacy packageに独立progress fileがある場合:

- 仕様理解のcurrent summary / current UNKNOWN件数 / 次工程可否 → READMEへsemantic migration
- workflow execution state / resume state → qa-workflowを正本とする
- 過去progress履歴 → CHANGELOG / legacy migration note
- product仕様として意味がある情報だけ該当domain fileへ残す

新modeではworkflow progress専用fileをcanonical packageとして追加しません。

## 15. deterministic output evaluation

mode固有の新しい決定論契約を通常spec-analysis 2caseへ混ぜず、`SPEC-OUT-003` を追加します。

- deterministic output case total: 44 → 46
- spec-analysis: 2 → 3
- test-requirement-design: 2 → 3
- question-analysis: 2のまま

SPEC-OUT-003はcurrent `ui-target-v1` package fixtureを持ち、UI操作scopeのbehavior decomposition contractを含めます。

TR-OUT-003はcurrent ACを入力に持ち、AC→TR / disposition closure、unknown AC、linked + disposed重複を検証します。

評価経路:

1. fixture packageを `ui_target_package.py project-eval projection=deterministic` で1 Markdownへ投影
2. 既存deterministic runnerへ渡す
3. spec-analysis validatorが通常3 canonical tableに加え、mode structured table / stable ref / current UNKNOWN / schema versionを独立検証する

deterministic validatorはproduction helperをimportしてexpectedを生成しません。

production helperのfilesystem / hash / projection / next-id / build-machine-evidence自体はrepository unit testで独立に評価します。

## 16. CI / portability

最低限追加:

- `skills/spec-analysis/scripts/ui_target_package.py` compile
- `skills/question-analysis/scripts/unknown_links.py` compile
- spec-analysis package単体コピー + `runtime_contract.py` / `authority_entities.py` / `ui_target_package.py` 実行
- question-analysis package単体コピー + `unknown_links.py` 実行
- valid minimal JSON fixture
- unknown top-level field
- malformed JSON / duplicate key
- 16 MiB境界 / 1 byte超過
- path traversal / absolute payload path / symlink
- missing required file
- invalid schema version
- duplicate / unknown stable ref
- scope applicability / conditional-required file mismatch
- required UI operation decompositionのmissing table / parent / closure
- UCごとの正常 / 準正常 / 例外3分類と定義あり / なし / 未定義整合
- MANIFEST hash mismatch
- semantic / deterministic projection差分
- build-machine-evidence内のAuthority部分と既存authority_entities.py結果一致
- current AC Entity contentへ親US / UC / Behavior chainが固定projectionされること
- 親US / UC / Behavior変更でAC fingerprintが変わること
- spec-analysis normalized_skill_input / expected identityがhelper結果から再現できること
- artifact `Machine Entities: spec-analysis` blockがruntime_contract.pyの `extract_machine_blocks(..., "Machine Entities")` で読めること
- legacy migration後fixtureのvalidate PASS

新しいGitHub Actions workflowは作りません。PR #14後の既存CIは `skills/*/scripts` を動的compileするため、helper compile目的のworkflow path追加は不要です。repository unit / runtime integration / portability testを既存test discoveryへ追加します。

## 17. 完了条件

- current packageを `ui-target-v1` として機械識別できる
- helperのoperation / input / output / failure contractが一意
- structured tableのheader / ID / ref列が一意
- scopeごとのUI操作適用判定と条件付き必須fileの存在を機械検証できる
- UI操作scopeでUIOP / US / UC / Behavior / AC hierarchyと3分類完全性を機械検証できる
- 09 → Authority Entity、02 → current AC EntityをLLM手組みなしで生成できる
- spec-analysis → question-analysisへUNKNOWN集合を手作業なしで渡せる
- semantic projectionへ過去CHANGELOGを混ぜない
- deterministic projectionでmulti-file contractを評価できる
- legacy vNN packageを意味を失わずcurrent schemaへ移行できる
- filesystem root外を読まない
- workflow progressと仕様package progressの正本が混ざらない
