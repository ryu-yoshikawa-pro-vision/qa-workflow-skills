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

`Previous Package Version` は初回なら `-`、継続更新なら `next-version` が返した `previous_version` を記録します。default policyでは `Package Version` と1 revision差であることをhelperが検証します。legacy移行時はlegacy側の明示versionまたは `legacy-unversioned` を記録できます。

上表は完成packageのschema例です。asset templateの `Current UNKNOWN Count` cellは空で置き、初回materialize時にhelperが実際のcurrent UNKNOWN集合から `0` 以上の整数を生成します。完成packageでは空値を許可しません。

### Current payload files

| 順序 | ファイル | 種別 |
| ---: | --- | --- |

templateではbodyを空にし、完成packageでは `render-readme-controls` が全payload rowを生成します。この表はREADME.md自身を含むMANIFESTのpayload file listと完全一致させます。

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

| Scope ID | 対象機能 / 領域 | UI操作判定 | Behavior Decomposition | 関連UNKNOWN ID | 関連仕様項目ID | 根拠 / 備考 |
| --- | --- | --- | --- | --- | --- | --- |

標準ID: `SCOPE-xxx`

許可値:
- UI操作判定: あり / なし / 未確定
- Behavior Decomposition: required / not-applicable / blocked

固定対応:
- あり → required
- なし → not-applicable
- 未確定 → blocked + 関連UNKNOWN ID必須

#### 条件付き必須file applicability

| ファイル | 状態 | 関連仕様項目ID | 根拠 / 備考 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- |
| 03_fields_and_validation.md | required / not-applicable / blocked |  |  |  |
| 04_flows_and_data.md | required / not-applicable / blocked |  |  |  |
| 05_notifications_and_external_interactions.md | required / not-applicable / blocked |  |  |  |
| 08_repository_implementation_status.md | required / not-applicable / blocked |  |  |  |

triggerの意味判断はLLMが行います。helperは4rowの存在、許可値、blocked時のUNKNOWN、required / not-applicableと実file / MANIFESTの一致を検証します。

上記2 tableの `関連仕様項目ID` はstable ID参照専用列です。値は空または `<br>` 区切りのexact stable IDだけを許可し、説明文を混在させません。`根拠 / 備考` は自由記述で、helperはそこに現れるID文字列をstable referenceとして扱いません。

`08_repository_implementation_status.md` のapplicabilityは「そのversionでrepositoryを再確認したか」ではなく、current packageがrepository / product implementation evidenceを現在保持・利用しているかで判定します。前versionの08をcurrent packageが継続利用する場合は `required` のまま保持し、08内の基準branch / commit / revisionを変更しません。current分析からrepository evidenceを明示的に外した場合だけ `not-applicable` とし、08を除去します。

#### 案件固有構造ID

| Prefix | 意味 |
| --- | --- |
| CSV | CSV export |

mode標準prefix以外を使う場合だけ記載します。

- Prefixは大文字英数字、先頭英字、2〜16文字
- 標準prefix / DEC / ASM / Qとの重複禁止
- helperはこの表に宣言されたprefixだけを案件固有prefixとして許可
- prefixを追加する意味と名称はLLMが判断する
- 一度stable ID採番に使ったPrefix rowはidentity historyとして削除・意味変更しない。不要になっても宣言を残し、配下IDのlifecycleをCHANGELOGで追跡する
- 宣言済み案件固有prefixはstandard structural prefixと同じく `inspect / next-id / materialize / impact / CHANGELOG / validate` の追跡・採番対象へ自動追加する

#### 案件固有extension file一覧

| ファイル | Slug | 責務 | 分割理由 |
| --- | --- | --- | --- |

extension fileを使う場合だけrowを持ち、templateはheader-onlyにします。

- `ファイル` は `10_<slug>.md` 以降のcanonical relative path
- `Slug` はlowercase kebab-case
- `責務` と `分割理由` はLLMが意味判断して記述する
- 同じファイル / Slugのduplicateを拒否する
- final packageでは宣言rowと実file集合が完全一致する
- 通常のcreate / updateではAgentがファイル番号やこのtableを手入力せず、`materialize.extension_file_updates[]` からhelperが連番・path・宣言rowをまとめて生成する

### 5.2 01_ui_structure_and_navigation.md

#### UI構造一覧

| 構造ID | 種別 | 名称 | 状態軸 | Path / 識別子 | 親構造ID | 関連仕様項目ID | 関連構造ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`種別` は次のexact enumだけを許可します。

- PAGE → PAGE-xxx
- STATE → STATE-xxx
- VIEW → VIEW-xxx
- STEP → STEP-xxx
- MODAL → MODAL-xxx
- BROWSER-DIALOG → BDLG-xxx
- PANEL → PANEL-xxx
- POPOVER → PANEL-xxx
- GLOBAL UI → PANEL-xxx
- EXTERNAL → EXT-xxx
- SHARED PAGE → SHARED-xxx

`状態軸` はSTATE rowだけ必須で、契約 / データ / 制限等のsource上の意味に沿った軸名をLLMが記録します。STATE以外では空を要求します。helperは軸名の意味を固定せず、空 / 非空条件とparent / reference整合だけを検証します。

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

| UC ID | 結果分類 | 判定 | 関連Behavior ID | 関連仕様項目ID | 関連UNKNOWN ID | 理由 / 根拠 |
| --- | --- | --- | --- | --- | --- | --- |

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

| 項目ID | カテゴリ | 内容 | 分類 | 情報源 / 正本参照 | 現在有効か | 解消先ID | 補足 / 上書き / 置換関係 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

UI target modeでは `現在有効か` を `Yes / No` に固定します。

UNKNOWNのlineageは次に固定します。

- `分類=UNKNOWN` かつ `現在有効か=Yes` → `解消先ID` は空
- `分類=UNKNOWN` かつ `現在有効か=No` → `解消先ID` は1件以上必須
- `解消先ID` はcurrentなSPEC / DECISION / 承認済みASMのstable IDだけを許可する
- 解消済みUNKNOWNでresolver Authorityだけが変わり、同じ論点が引き続き解消済みなら、同じUNK IDを維持して `解消先ID` を新しいcurrent Authorityへ更新する
- 解消根拠がなくなり、LLMが同じ論点と判断した場合は、同じUNK IDを `現在有効か=Yes`、`解消先ID=空` へ戻してreopenする
- LLMが別論点と判断した場合は、旧UNKを `現在有効か=No` のresolved historyとして維持し、new UNKを採番する
- UNKNOWN以外のrowでは `解消先ID` は空
- 同一論点 / 別論点、どのAuthorityがUNKNOWNを解消したかはLLMが判断し、helperはID・状態・currentness・種別・CHANGELOG eventの構造整合だけを検証する

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
{"schema_version":"entity-state-v2","skill":"spec-analysis","entities":[]}
```

`entities` は§9のdeterministic bridge結果をそのまま使用します。LLMがMachine Entity wrapper / fingerprintを計算・再構築しません。`expected_entity_identities` はhelper responseに保持しますが、artifactの `Machine Entities` block schemaへ混入させません。`authority_entities.py` が内部返却する `implementation_fingerprint` は本modeのconsumer契約では使用せず、`build-machine-evidence` の統合responseへ公開しません。

### 5.11 10+ domain files

案件固有domain fileは自由な説明sectionを持てます。

structured tableを置く場合:

- primary ID列名を `項目ID` に固定する
- `関連仕様項目ID` を持つ
- UI構造へ関連する場合 `関連構造ID` を持つ
- primary ID prefixは00の `案件固有構造ID` で宣言する

helperは宣言されたheader名のexact ID参照だけを検証し、proseからIDを推測抽出しません。

### 5.12 asset initialization contract

`skills/spec-analysis/assets/ui-test-target-analysis/` のtemplateは、実データと誤認できる例示IDを置きません。

- variable structured tableはheader / separatorだけを持ち、`PAGE-001` / `SPEC-001` / `AC-001` 等の例示rowを置かない
- `条件付き必須file applicability` の4rowのようにschema上固定のrowだけ事前配置する
- READMEのPackage Schema Versionは `ui-target-v1`、初回Package Versionは `v00`、Previous Package Versionは `-` を固定初期値とする
- READMEのCurrent UNKNOWN Count / Current payload filesはhelper生成結果を貼り付けるcontrol sectionとし、例示値を置かない
- CHANGELOG初回entryは `## v00` と3つの固定subheading、空の `Stable ID changes` tableを持つ
- Machine Entities blockはschema上の空blockをtemplateに置けるが、完成packageでは `build-machine-evidence` 再生成結果へ置換しvalidate一致を必須とする

extension fileの必要性とslugはLLMが判断します。連番は `next-domain-file` が決定します。

## 6. ID rules

packageがstable reference / CHANGELOG / impactで追跡できるprefixと、`ui_target_package.py next-id / materialize` が採番できるprefixを分離します。標準prefixに加え、00の `案件固有構造ID` で宣言された案件固有prefixも同じ履歴契約へ参加します。

### 6.1 packageで追跡できるstable ID

canonical spec-analysis / Authority:

- SRC
- SPEC
- INF
- UNK
- DEC
- ASM

UI target structural:

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

案件固有prefixを含む形式は `PREFIX-001` ～ `PREFIX-999`。

`DEC / ASM` もpackage内で参照される外部ownerのstable IDなので、exact reference validation、CHANGELOG `Stable ID changes`、`impact` の追跡対象に含めます。v01以降にpackageへ初めて取り込むDEC / ASMは `added`、既に追跡中の同一IDの内容・状態変更は `changed` とします。current structured modelからidentity自体を外す場合でも、`retired` はLLMがexplicit `retire_ids[]` でsemanticに除去を確定したときだけ生成し、row消失から自動推測しません。`resolved` は `UNK-xxx` 専用であり、DEC / ASMへ使用しません。

### 6.2 ui_target_package.py next-idの採番対象

`next-id / materialize` が番号決定できるprefixは、次の標準prefixと、00で宣言済みの案件固有prefixです。

canonical spec-analysis item:

- SRC
- SPEC
- INF
- UNK

UI target structural:

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

`next-id` はLLMがnewと判断した後にのみ使用します。Agentから既知ID一覧を受け取らず、helperが `package_root` のcurrent structured row、CHANGELOGに記録されたexact stable ID token、previous snapshotを走査し、同prefixの既知最大番号+1を返します。案件固有prefixも同じ処理を使い、LLMが `CSV-001` 等の番号を手計算しません。

削除済み・置換済みentityのIDもCHANGELOGのexact `Stable ID changes` tableへ記録済みである限り再利用しません。stable IDを削除・置換するversionでは、そのIDを同tableへ必ず記録します。

999を使用済みなら自動的に4桁へ拡張せず `id_space_exhausted` でblockedを返します。prefix拡張はschema変更として別途扱います。

`SRC / SPEC / INF / UNK` は既存spec-analysisの分類・形式契約を維持しつつ、UI target mode内でnewと判断した後の番号決定だけ `next-id` を使用します。

`DEC / ASM` は追跡対象ですが本helperの採番対象ではありません。canonical Authority IDは既存spec-analysis契約どおり常に `DEC-xxx / ASM-xxx` とします。Project Context以外のownerを利用する場合も、そのownerがcanonical DEC / ASM IDを発行・保持することを前提とします。Jira issue key、ADR番号、外部DB key等のowner固有識別子を `authority_id` へ直接入れず、source / evidence側の参照metadataとして保持します。canonical DEC / ASM IDを正本ownerから確定できない場合はcurrent Authorityへ昇格させずblockedとします。

### 6.3 structured Markdown parse contract

production helperは任意Markdownを解釈する汎用parserにしません。§2〜§5で定義したcanonical heading / tableだけを対象に、次の固定規則でparseします。

- canonical structured tableのheadingはexact文字列で1回だけ存在する
- 同じcanonical heading配下に対象tableが複数ある場合は `package_schema_mismatch`
- tableはheader / separator / rowの列数一致を要求する
- cell前後の空白はtrimする
- literal `|` をcellに含める場合は `\|` とする
- 複数stable ID参照は `<br>` だけを区切りとして使い、各要素をtrimし、空要素を拒否する
- prose中に現れたID文字列はstable referenceとして扱わない
- production helperとdeterministic eval validatorは実装を共有しないが、同じparse fixture corpusで上記契約を検証する

## 7. helper CLI common contract

### 7.1 基本

`ui_target_package.py`、`unknown_links.py`、`question_ids.py`、`project_context_ids.py` は次を共通原則とします。

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

handled `issue_type` は次のexact enumに固定します。

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
- stale_snapshot
- state_transition_required

unknown operation / unknown top-level field / JSON・table schema不正は `invalid_input`、packageのcanonical heading / file set / version schema不一致は `package_schema_mismatch`、参照先不存在は `reference_not_found`、ID重複は `duplicate_id`、MANIFESTのfile set / order / SHA差分は `manifest_mismatch` へ固定します。single-writer前提に反してsnapshot取得後にpackage bytesが変わっていた場合は `stale_snapshot`、previous tracked IDが明示 `retire_ids[]` なしでcurrent modelから消えた場合は `state_transition_required` へ固定します。新しいhandled failure種別が実装中に必要になった場合は、実装だけで増やさずこのPlan contractを更新します。

### 7.3 update concurrency contract

同じpackage revisionの更新はsingle writerとします。複数Agent / processが同じrevisionを並行編集することはPR #16の対象外です。generic CAS / lock serviceは追加しません。

通常更新は必ず `inspect → update_snapshot保持 → materialize` の順で行います。`materialize` は書込み前にsnapshotのPackage Versionと `payload_file_sha256[]` をcurrent packageへ照合し、1 byteでも変化していれば `stale_snapshot` で書込みせずblockedにします。これにより、single writer前提を破る外部変更をsilent overwriteしません。

## 8. ui_target_package.py operations

### inspect

stdin:

```json
{"operation":"inspect","package_root":"<path>"}
```

payload:

```json
{
  "package_schema_version":"ui-target-v1",
  "package_version":"v15",
  "previous_package_version":"v14",
  "payload_files":[
    {"order":1,"path":"README.md","kind":"core"}
  ],
  "file_applicability":[
    {"path":"03_fields_and_validation.md","status":"required","authority_refs":["SPEC-001"],"unknown_refs":[]}
  ],
  "domain_files":[
    {"order":10,"path":"10_csv-export.md","slug":"csv-export"}
  ],
  "canonical_item_ids":["SRC-001","SPEC-001","UNK-001"],
  "current_unknown_ids":["UNK-001"],
  "resolved_unknown_ids":["UNK-002"],
  "current_unknown_count":1,
  "structural_ids":["PAGE-001","SCOPE-001"],
  "exact_reference_index":[
    {"target_id":"SPEC-001","file":"02_behavior_and_business_rules.md","section":"Acceptance Criteria一覧","row_index":1,"column":"関連仕様項目ID"}
  ],
  "update_snapshot":{
    "package_version":"v15",
    "tracked_items":[
      {"stable_id":"SPEC-001","tracking_file":"09_authority_and_traceability.md","tracking_section":"分析項目","row_fingerprint":"<sha256>","unknown_active":null,"resolution_refs":[]}
    ],
    "exact_reference_index":[],
    "payload_file_sha256":[
      {"path":"README.md","sha256":"<lowercase-64-hex>"}
    ]
  },
  "unresolved_structural_issues":[]
}
```

規則:

- `payload_files[]` はcanonical file order
- `file_applicability[]` は03 / 04 / 05 / 08の順
- ID配列はlexicographic昇順
- `domain_files[]` はorder昇順
- `exact_reference_index[]` は `target_id / file / section / row_index / column` の順で安定sort
- `row_index` は対象structured tableのdata rowを1始まりで数える
- `unresolved_structural_issues[]` は `issue_type / file / section / row_index / column / message` を持ち、存在しない位置はnull
- `update_snapshot` は更新開始前の状態を後続operationへそのまま渡すmachine inputであり、Agent / LLMが編集・再構築しない
- `tracked_items[]` は§6.1のtracked stable IDをpackage内canonical tracking row単位で1行に正規化し、`stable_id` 昇順。field名は `tracking_file / tracking_section` とし、Authorityの実際の正本ownerを意味しない。DEC / ASMの実ownerがProject Contextや外部正本でも、ここでは09のpackage projection rowをtracking位置として記録する。自由記述ではなくcanonical structured tracking rowの正規化結果から `row_fingerprint` を計算する
- UNKNOWN rowは `unknown_active=true / false` とcanonical `resolution_refs[]` を保持し、それ以外は `unknown_active=null / resolution_refs=[]`
- snapshotの `exact_reference_index[]` と `payload_file_sha256[]` はsnapshot時点の値を保持し、retired IDの過去参照先や更新前file集合もimpact算出へ利用できるようにする

`resolved_unknown_ids` は09で `分類=UNKNOWN` かつ `現在有効か=No` のUNK。

### validate

stdin:

```json
{"operation":"validate","package_root":"<path>","previous_snapshot":null}
```

fresh v00 / standalone検証では `previous_snapshot=null` を許可します。通常更新runでは内容編集前の `inspect.payload.update_snapshot` をそのまま渡します。

§2〜§6およびfilesystem safetyを検証します。default version policyでは `v00 / Previous=-` またはcurrent / previousの1 revision差とpackage内version一致を検証します。加えて、resolved UNKNOWNの `解消先ID`、`Machine Entities: spec-analysis` blockのexactly-one存在、build-machine-evidence再生成結果との完全一致を検証します。

通常更新で `previous_snapshot` が与えられた場合、latest `Stable ID changes` と `影響file` が同snapshotから `impact` を再実行した結果とexact一致することも検証します。standalone検証では過去snapshotがないため、CHANGELOGのschema / lifecycle履歴整合だけを検証し、latest差分の再計算は行いません。

current packageだけから過去の同version内容とのbyte同一性は証明しません。canonical更新経路では `materialize` がprevious snapshotとの差分を確認し、差分がある完成package保存ではdefault policyのversionを必ず+1します。focused `next-version` operationは同じ導出規則を単独確認するために残します。

### next-version

current `ui-target-v1` packageをdefault policyで更新する場合:

```json
{"operation":"next-version","package_root":"<path>"}
```

helperがREADMEからcurrent Package Versionを取得します。

payload:

```json
{
  "previous_version":"v14",
  "next_version":"v15",
  "readme_version_rows_markdown":"| Package Version | v15 |\n| Previous Package Version | v14 |"
}
```

Agent / LLMがcurrent packageのversion文字列を抽出して `previous_version` として渡す経路は作りません。

legacy package migrationで、LLMのsemantic mappingによりlegacy側の明示versionが確定済みの場合だけ次のexact inputを許可します。

```json
{"operation":"next-version","source":"legacy-migration","previous_version":"v14"}
```

このlegacy inputも同じ3 fieldを返し、`readme_version_rows_markdown` までhelperが生成します。案件固有version policyではnext-versionを使用しません。

### next-id

stdin:

```json
{
  "operation":"next-id",
  "package_root":"<path>",
  "prefix":"PAGE",
  "previous_snapshot":null
}
```

helperはcurrent structured row、CHANGELOG各versionのexact `Stable ID changes` table、`previous_snapshot.tracked_items[]` のunionから既知ID集合を内部導出します。fresh v00では `previous_snapshot=null`、通常更新では内容編集前のinspect snapshotを必須とします。CHANGELOG本文のproseに現れたID文字列は採番履歴として扱いません。

payload:

```json
{
  "next_id":"PAGE-003",
  "stable_id_change":{"stable_id":"PAGE-003","change":"added"}
}
```

semantic identityは判断しません。Agent / LLMが `known_ids[]` を組み立てる経路は作りません。

同一prefixで複数IDを割り当てる場合は、返却された `next_id` を対象structured rowへ反映してから、同じ `previous_snapshot` を渡して次の `next-id` を呼びます。`stable_id_change` は即時CHANGELOG書込み用ではなく、採番結果確認用です。latest `Stable ID changes` tableは後段の `impact` がprevious/current差分からsection全体を生成します。

### render-readme-controls

stdin:

```json
{"operation":"render-readme-controls","package_root":"<path>"}
```

payload:

```json
{
  "package_metadata_markdown":"### Package metadata\n\n| 項目 | 値 |\n| --- | --- |\n| Package Schema Version | ui-target-v1 |\n| Package Version | v15 |\n| Previous Package Version | v14 |\n| Current UNKNOWN Count | 1 |",
  "current_payload_files_markdown":"### Current payload files\n\n| 順序 | ファイル | 種別 |\n| ---: | --- | --- |\n| 1 | README.md | core |\n| 2 | 00_scope_and_context.md | core |"
}
```

helperはREADMEのcurrent Package Version / Previous Package Version、09のcurrent UNKNOWN集合、current file setを読み、2 section全体をcanonical Markdownとして返します。READMEのfile listはhashを持たないため、MANIFEST生成より前にこのoperationで確定します。Agent / LLMがmetadata table、UNKNOWN件数、payload file順、種別を再構築しません。

### next-domain-file

stdin:

```json
{
  "operation":"next-domain-file",
  "package_root":"<path>",
  "slug":"csv-export"
}
```

payload:

```json
{"order":10,"slug":"csv-export","path":"10_csv-export.md"}
```

slugはlowercase kebab-caseを要求します。helperはsemanticなslug選択を行わず、existing 10+ fileの最大番号+1だけを決定します。

focused `next-domain-file` を単独で連続利用する場合だけ、返却pathを実fileへmaterializeしてから次を呼びます。canonical package create / updateで複数extensionを追加する場合は本operationを逐次利用せず、`materialize.extension_file_updates[]` がrequest順にbatch採番します。

### materialize

通常のpackage作成 / 更新で使うcanonical write pathです。汎用Markdown engineではなく、§2〜§5で定義した `ui-target-v1` の既知file / heading / table registryだけを扱います。通常更新ではAgentが `next-id → Markdown row手書き → section貼付け` を行わず、本operationがsemantic入力からID割当・escape・sort・table serialization・section置換・標準file同期・control再生成まで実行します。

stdin:

```json
{
  "operation":"materialize",
  "package_root":"<path>",
  "artifact_mode":"update",
  "previous_snapshot":{"package_version":"v14","tracked_items":[],"exact_reference_index":[],"payload_file_sha256":[]},
  "change_mode":"normal",
  "version_policy":"default",
  "target_version":null,
  "legacy_source_version":null,
  "migration_retained_ids":[],
  "legacy_lifecycle_events":[],
  "change_summary":"<current versionの変更概要本文>",
  "retire_ids":["PAGE-009"],
  "table_changes":[
    {
      "file":"02_behavior_and_business_rules.md",
      "section":"User Story一覧",
      "rows":[
        {
          "draft_key":"us-login",
          "identity_action":"new",
          "reuse_id":null,
          "primary_prefix":"US",
          "cells":{
            "Scope ID":"SCOPE-001",
            "Actor / Role":"管理者",
            "Goal":"...",
            "関連仕様項目ID":["SPEC-001"],
            "関連構造ID":["PAGE-001"],
            "状態":"current",
            "関連UNKNOWN ID":[]
          }
        }
      ]
    }
  ],
  "keyed_table_updates":[
    {
      "file":"00_scope_and_context.md",
      "section":"条件付き必須file applicability",
      "rows":[
        {"ファイル":"03_fields_and_validation.md","状態":"required","関連仕様項目ID":["SPEC-001"],"根拠 / 備考":"入力項目あり","関連UNKNOWN ID":[]},
        {"ファイル":"04_flows_and_data.md","状態":"not-applicable","関連仕様項目ID":[],"根拠 / 備考":"対象flowなし","関連UNKNOWN ID":[]},
        {"ファイル":"05_notifications_and_external_interactions.md","状態":"not-applicable","関連仕様項目ID":[],"根拠 / 備考":"外部interactionなし","関連UNKNOWN ID":[]},
        {"ファイル":"08_repository_implementation_status.md","状態":"not-applicable","関連仕様項目ID":[],"根拠 / 備考":"repository evidence未使用","関連UNKNOWN ID":[]}
      ]
    }
  ],
  "prose_updates":[
    {"file":"06_spec_inconsistencies_and_pending.md","section":"<exact heading>","body_markdown":"..."}
  ],
  "extension_file_updates":[
    {"draft_key":"domain-csv","identity_action":"new","path":null,"slug":"csv-export","responsibility":"CSV export仕様","split_reason":"標準fileと独立したAuthority / flow / rule集合を持つ","body_markdown":"..."}
  ]
}
```

`artifact_mode` は `create / update` の2値です。normal createではasset初期状態のtarget root + `previous_snapshot=null` を要求し、default policyならPackage Version=v00 / Previous=-で作成します。normal updateでは完成済みcurrent package + non-null previous snapshotを必須とし、snapshot無し更新をfail-closedにします。legacy-migrationは `artifact_mode=create` だけを許可します。

`change_mode` は `normal / legacy-migration` の2値です。

normalでは `version_policy` を `default / project` の2値から選びます。既存完成package更新のdefaultではhelperがprevious snapshotのversionから次versionを導出し、README / CHANGELOG / MANIFESTへ同時反映します。projectの場合だけ、案件で明示されたpolicyに基づく `target_version` を必須とし、helperはpackage内一致を検証します。完成済みpackageへ1 byteでも永続変更を加えて再び完成状態として保存する場合、default policyではsemantic / presentationを問わず必ずversionを+1します。in-memory生成結果がprevious packageと完全同一ならno-opとして書込み・version upを行いません。

legacy-migrationでは `previous_snapshot=null` を要求し、`legacy_source_version` は明示 `vNN` または `legacy-unversioned` を必須とします。明示vNNならtargetを次のvNN、`legacy-unversioned` ならtargetをv00 / Previous=`legacy-unversioned`へ固定します。`version_policy=project` はlegacy-migrationでも案件に明示policyがある場合だけ許可します。`migration_retained_ids[]` と `legacy_lifecycle_events[]` は§14のsemantic mapping結果だけを受け、helperが番号予約・lifecycle生成へ使います。

table input contract:

`table_changes[]` はstable IDのowner tableだけを対象にします。

- owner table: 分析対象機能scope一覧、UI構造一覧、UI操作一覧、User Story一覧、Use Case一覧、Behavior一覧、Acceptance Criteria一覧、ビジネスルール一覧、項目・バリデーション一覧、処理フロー一覧、通知・外部連携一覧、仕様矛盾・保留一覧、Repository実装状況、情報源 / 正本参照一覧、分析項目、10+ domain fileの案件固有stable row
- `file / section` は§2〜§5のregistryに存在するexact pairだけを許可する。extension fileのstructured table更新は、既存extensionなら宣言済みpath、新規extensionなら同requestの `extension_file_updates[].draft_key` で対象を特定する
- `cells` はprimary ID列を除いたexact header名だけを許可する。stable reference列はJSON string array、通常cellはstringで受ける
- 新規rowは `identity_action=new / reuse_id=null / draft_key=<request内unique>`
- 既存row更新は `identity_action=reuse / reuse_id=<stable ID>`。normalではprevious snapshot / current packageに存在するIDだけをreuseでき、legacy-migrationでは `migration_retained_ids[]` に含まれるIDだけをreuseできる
- request内の新規row参照はstable IDの代わりに `@draft:<draft_key>` をreference配列へ指定できる。helperが採番後に解決する
- standard tableの `primary_prefix` はregistryと完全一致を要求する。10+ domain fileでは00の案件固有prefix宣言と一致する値だけを許可する

`keyed_table_updates[]` はstable IDを採番しないview / fixed-key tableの**完成row集合**を対象にし、section単位で全rowを置換します。部分patchは許可しません。exact registryは次です。

| file / section | key | 固定規則 |
| --- | --- | --- |
| `00_scope_and_context.md / 条件付き必須file applicability` | `ファイル` | 03 / 04 / 05 / 08の4row exactly。canonical順固定 |
| `00_scope_and_context.md / 案件固有構造ID` | `Prefix` | semantic declaration。使用済みPrefixの削除 / 意味変更は禁止 |
| `02_behavior_and_business_rules.md / Use Case振る舞い完全性` | `UC ID + 結果分類` | current UCごとに3分類 exactly |
| `07_current_unknowns.md / Current UNKNOWN一覧` | `UNKNOWN ID` | 09のcurrent UNKNOWN ID集合とexact一致 |
| `09_authority_and_traceability.md / 現在有効な仕様根拠` | `仕様根拠ID` | LLMが確定したCurrent Effective Authorityだけ。09分析項目のcurrent SPEC / DECISION / approved ASMへ存在参照 |
| `09_authority_and_traceability.md / 後続Skillへの補足` | `項目` | 項目duplicate禁止。stable refsだけhelper検証 |

`keyed_table_updates[]` のrowはexact header名をJSON keyとして持ち、stable reference列だけstring arrayを受けます。stable IDをkey / referenceとして持つcellでは、同requestのnew owner rowを `@draft:<draft_key>` で参照できます。helperはstable owner ID割当後にkey / reference内の `@draft` を解決し、未解決draftをrejectします。helperがcanonical key order / Markdown escape / `<br>` serialization / row sortを行います。view tableからrowが消えてもowner stable IDのretireとは扱いません。owner lifecycleは `table_changes[] / retire_ids[]` だけで管理します。

normal updateで `keyed_table_updates[]` にsectionが無い場合、そのsectionはcurrent packageの完成row集合を保持します。normal create / legacy-migrationでは `条件付き必須file applicability` を必須とし、その他view tableは必要な最終集合を明示します。owner stable row変更により保持したviewが不整合になればfinal validateでblockedし、helperが意味を推測して自動修正しません。
extension input contract:

- `extension_file_updates[]` のnew rowは `draft_key` unique、`identity_action=new / path=null`、lowercase kebab-case slug、非空responsibility / split_reasonを要求する。reuseは `identity_action=reuse / path=<existing canonical path>` とし、slugを変更しない
- new extension pathはexisting extension最大番号+1から、request配列順に連続採番する。同じrequest内で複数追加しても空fileによる番号予約を要求しない
- helperは最終pathを00の `案件固有extension file一覧` へcanonical orderで生成し、Agent / LLMがtable rowを組み立てない
stable owner allocation / lifecycle contract:

- new IDはcanonical file order → section order → request row orderで割り当てる。同一JSON inputから同じID割当になる。legacy-migrationでは `migration_retained_ids[]` と `legacy_lifecycle_events[].stable_id` を採番前の使用済み集合へ必ず含め、current rowに存在しないretired / resolved legacy IDを再利用しない
- unchanged rowはcurrent packageから保持する。requestにない既存rowを削除しない
- `retire_ids[]` はLLMが「このsemantic identityをcurrent package modelから意図的に除去する」と判断したIDだけを渡す。row消失だけからhelperがretireを推測しない
- previous snapshotに存在するIDがmaterialize後modelから消えるのに `retire_ids[]` にない場合は `state_transition_required` で書込み前にblocked
- `retire_ids[]` のIDがcurrent rowへ残る、previous snapshotに存在しない、current exact referenceから参照されたままの場合はblocked
- UNKNOWN解消はretireではなくrow保持 + resolved、DEC / ASMの撤回 / 置換もlineageを保持する間はrow保持 + changedを使う。canonical itemをretireするのは、そのidentityをpackage trackingから意図的に除去し、必要なlineage / exact referenceが残らないとLLMが判断した場合だけ
- structural itemは対象UI構造等が意味上current modelから削除された場合にexplicit retireできる

file / control materialization order:

1. artifact_mode / change_mode / previous_snapshotの組合せを検証する。normal updateではprevious snapshotとcurrent bytesを照合し、staleなら書込みしない。normal create / legacy-migrationでは新しいcurrent-schema target rootがasset初期状態であることを検証する
2. change_mode / version policyを解決し、target version / Previous Package Versionをin-memory metadataへ設定する
3. legacy-migrationでは `migration_retained_ids[] / legacy_lifecycle_events[]` の形式・duplicate・lifecycleを先に検証して使用済みID集合へ予約する
4. `keyed_table_updates[]` のうちfile applicability / 案件固有prefix宣言を先にparseし、意味値を変更せず構造検証する
5. applicabilityに従い条件付き標準fileのtemplateをin-memoryへ追加 / removal予定化し、`extension_file_updates[]` のnew pathをrequest順でbatch allocationして新規extension templateを準備する
6. stable owner `table_changes[]` をin-memory modelへ適用し、reuse / new IDを割り当て、owner row内の `@draft` referenceを解決する。新規条件付きfile / extension fileのowner rowもこの段階で適用する
7. remaining `keyed_table_updates[]` のkey / reference内 `@draft` を解決して完成row集合を確定する
8. normal updateの `retire_ids[]` を検証してin-memory owner modelから除去する。removal予定fileにtracked owner rowが残る場合は対応retire intent不足としてblockedする。legacy-migrationの過去lifecycle eventは `legacy_lifecycle_events[]` だけから扱い、current row削除操作へ流用しない
9. extension最終集合から00の `案件固有extension file一覧` をcanonical生成する
10. stable owner / keyed / generated tableをexact Markdownへescape / canonical sortしてserializeし、known sectionだけ置換する。prose updateはexact heading配下のbodyだけを置換し、意味を書き換えない
11. normalではprevious snapshot + explicit retire intent、legacy-migrationではmigration retained / lifecycle mapping + current owner modelからimpactを生成し、CHANGELOGのtarget version entryを作成して `変更概要 / Stable ID changes / 影響file` を更新する
12. `build-machine-evidence` 相当処理で09のMachine Entities sectionをcanonical生成・置換する
13. README controlsをcanonical生成・置換する
14. MANIFESTを最後に再生成する
15. normal updateでin-memory結果がprevious packageと完全同一ならno-opを返す。差分がある場合、またはlegacy-migrationではfinal validateを実行し、成功した場合だけpackage filesへ書き出す

payload:

```json
{
  "changed":true,
  "allocated_ids":[{"draft_key":"us-login","stable_id":"US-003"}],
  "allocated_extension_files":[{"draft_key":"domain-csv","path":"10_csv-export.md"}],
  "retired_ids":["PAGE-009"],
  "changed_files":["README.md","02_behavior_and_business_rules.md","CHANGELOG.md","MANIFEST.md"],
  "previous_package_version":"v14",
  "package_version":"v15"
}
```

`changed=false` のno-opでは `allocated_ids=[] / allocated_extension_files=[] / retired_ids=[] / changed_files=[]` とし、`previous_package_version / package_version` はcurrent package値を返します。create / legacy-migrationは成功時 `changed=true` です。

通常のUI target package更新は `materialize` を正本のwrite pathとします。`next-id / impact / render-readme-controls / build-machine-evidence / build-manifest` は同じ内部contractを個別検証・focused useするoperationとして残しますが、Agentがそれらの返却Markdownを手作業で貼り合わせて完成packageを作る経路をcanonical手順にしません。

### build-manifest

stdin:

```json
{"operation":"build-manifest","package_root":"<path>"}
```

payload:

```json
{
  "manifest_markdown":"- Package Schema Version: ui-target-v1\n- Package Version: v15\n\n### Package manifest\n...",
  "files":[
    {"order":1,"path":"README.md","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}
  ]
}
```

`files[]` はcanonical payload order、`sha256` はraw file bytesのlowercase 64 hexです。README controls反映後のbytesをhashし、LLM / AgentがSHA-256を手計算しません。

### impact

通常のcurrent version更新では、内容編集前の `inspect.payload.update_snapshot` と更新中current packageを比較します。

stdin:

```json
{
  "operation":"impact",
  "package_root":"<path>",
  "previous_snapshot":{"package_version":"v14","tracked_items":[],"exact_reference_index":[],"payload_file_sha256":[]},
  "change_mode":"normal",
  "retire_ids":["PAGE-009"]
}
```

helperはstable ID owner rowのprevious/current差分からlifecycleを決定します。

- previousに存在せずcurrentに存在 → `added`
- same IDがprevious/currentに存在しowner row fingerprintが不変 → eventなし
- same IDが存在しowner row fingerprintが変化 → 原則 `changed`
- UNKが `unknown_active=true → false` → `resolved`
- resolved UNKのresolver変更、`false → true` のsame-ID reopen → `changed`
- reopen後の `true → false` → 再び `resolved`
- previousに存在しcurrent structured modelから消え、かつ `retire_ids[]` に明示された → `retired`
- previousに存在しcurrent structured modelから消えたが `retire_ids[]` にない → `state_transition_required` でblockedし、自動retireしない
- `retire_ids[]` にあるIDがcurrent modelへ残る / previousに存在しない / exact referenceが残る → blocked
- previous CHANGELOGですでに `retired` のIDはcurrentへ再導入不可

LLM / Agentが `added / changed / resolved` のevent rowを手入力しません。`retired` の意味判断だけはLLMが行い `retire_ids[]` として明示し、helperが存在・参照・lifecycleを検証してCHANGELOG rowへ変換します。semantic identityのreuse / new、same-UNK reopenかnew UNKかもLLMが先に判断し、helperはその結果として成立したstructured stateと明示retire intentからlifecycleを決定します。

payload:

```json
{
  "changed_ids":["SPEC-001"],
  "stable_id_changes_markdown":"### Stable ID changes\n\n| Stable ID | Change |\n| --- | --- |\n| SPEC-001 | changed |",
  "affected_files":["02_behavior_and_business_rules.md","09_authority_and_traceability.md"],
  "affected_files_markdown":"### 影響file\n\n- 02_behavior_and_business_rules.md\n- 09_authority_and_traceability.md",
  "affected_rows":[
    {"changed_id":"SPEC-001","file":"02_behavior_and_business_rules.md","section":"Acceptance Criteria一覧","row_index":1,"column":"関連仕様項目ID"}
  ]
}
```

`affected_files[]` は「実際に本文変更が必要だったfile」ではなく、changed stable IDのprevious/current package tracking fileとprevious/current exact reference先のunionです。再確認対象を漏らさないための決定論的な影響候補としてcanonical file orderで返し、CHANGELOGの `影響file` もこの定義へ固定します。意味上そのfileを修正すべきかはLLMが判断します。

`stable_id_changes_markdown` と `affected_files_markdown` はsection全体を置換するcanonical Markdownです。Agent / LLMがchanged ID集合・Change値・影響file一覧を再構築しません。

legacy migrationではsemantic identity mappingだけはLLM判断です。変換後current packageに対し次のmodeを使います。

```json
{
  "operation":"impact",
  "package_root":"<path>",
  "previous_snapshot":null,
  "change_mode":"legacy-migration",
  "migration_retained_ids":["SPEC-001","DEC-001"],
  "legacy_lifecycle_events":[
    {"stable_id":"UNK-009","change":"resolved"}
  ]
}
```

- `migration_retained_ids[]` はLLMがlegacy/currentのsemantic identity一致を判断した結果だけを渡し、helperが `migrated` に変換する
- current tracked IDのうちretainedでないnew IDは `added`
- `legacy_lifecycle_events[]` はlegacy資料から明示確認できる `resolved / retired` だけを許可し、helperが形式・duplicate・prefix/lifecycle整合を検証する
- legacy proseからIDやlifecycle eventを自動推測しない

意味上の修正要否、semantic identity、legacy mappingは判断しません。

### build-machine-evidence

stdin:

```json
{"operation":"build-machine-evidence","package_root":"<path>"}
```

§9に従い09からnormalized Authority inputを生成して既存 `authority_entities.py` のbuilderを呼び、02のcurrent ACと親US / UC / Behavior chainからAcceptance Criterion Machine Entityを生成して統合します。

payload:

```json
{
  "normalized_authorities":[],
  "normalized_skill_input":{"authorities":[],"acceptance_criteria":[]},
  "acceptance_criterion_entities":[],
  "machine_entities":[],
  "expected_entity_identities":[],
  "machine_entities_markdown":"### Machine Entities: spec-analysis\n\n\`\`\`json\n{...}\n\`\`\`\n"
}
```

各Machine Entity / identity rowのschemaはshared runtime contractを正本とします。配列はentity identityの `skill / entity_type / entity_ref` 順でcanonical sortします。統合responseに独自の `implementation_fingerprint` fieldは持ちません。

`machine_entities_markdown` は既存shared `runtime_contract.py::render_machine_entities("spec-analysis", machine_entities)` の戻り値をそのまま使用します。Agentは09の `### Machine Entities: spec-analysis` section全体をこの文字列で置換し、heading / JSON fence / wrapper / content fingerprintを手組みしません。

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

- CHANGELOG全体
- MANIFEST

過去仕様を含むCHANGELOG全体はsemantic Judgeへ混ぜません。ただしcurrent Package Versionの `### 変更概要` bodyだけは今回のsemantic update説明として抽出し、synthetic control frame `CHANGELOG.current_change_summary` としてprojection末尾へ追加します。`Stable ID changes / 影響file` はdeterministic controlなのでsemantic projectionへ入れません。

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

payloadは両projectionで次のexact shapeです。

```json
{
  "projection":"semantic",
  "files":["README.md","00_scope_and_context.md"],
  "controls":["CHANGELOG.current_change_summary"],
  "markdown":"<!-- FILE: README.md -->\n...\n<!-- CONTROL: CHANGELOG.current_change_summary -->\n..."
}
```

`files[]` は実際に連結したrelative pathをcanonical順で持ちます。`controls[]` はsynthetic control frame名を順序付きで持ち、semantic projectionでは `CHANGELOG.current_change_summary`、deterministic projectionでは空arrayです。各file frameは `<!-- FILE: <relative-path> -->` + LF + UTF-8 decodeしたfile textです。semantic change summary frameは `<!-- CONTROL: CHANGELOG.current_change_summary -->` + LF + current versionの `### 変更概要` bodyだけを使用します。file textがLFで終わらない場合だけ、次のmarkerを独立行にするtransport separatorとしてLFを1文字追加します。このseparatorはsource file内容には含めず、その他の正規化・trim・改行変換を行いません。

raw SHA-256はprojectionから再計算しません。production `validate` / repository unit testがraw bytesでMANIFEST hashを検証し、projected deterministic evalはMANIFEST schema、file集合・順序、SHA-256文字列形式、stable ref等を検証します。

## 9. deterministic Authority / Acceptance Criterion Machine Entity bridge

LLMが09へCurrent Effective Authorityを確定し、02へcurrent US / UC / Behavior / ACを確定した後、`build-machine-evidence` がAuthority + current ACを固定変換します。

### 9.1 Authority

Authority部分は既存 `authority_entities.py` のnormalized input / builder契約をそのまま再利用します。09の「現在有効な仕様根拠」tableから `normalized_authorities[]` への変換はhelper内で次に固定します。

| 09 column | normalized Authority field |
| --- | --- |
| 仕様根拠ID | `authority_id` |
| 種別 | `authority_type` |
| 現在有効な内容 | `active_content={"text":"<cell>"}` |
| 適用範囲 | `scope` |
| 情報源 / 正本一覧 | `source_refs[]` |
| 関係 | `relations[]` |
| 関連仕様根拠ID | `related_authority_refs[]` |

規則:
- `現在有効な内容` はtrim後の非空文字列を `active_content.text` へ入れ、helperが意味的な再要約・再構成をしない
- `適用範囲` はtrim後の非空文字列をそのまま `scope` へ入れる。UI target modeでは `null` / objectへ変換しない
- `情報源 / 正本一覧` は1件以上の `SRC-xxx` stable ID参照を要求し、複数IDは `<br>` 区切り
- `関係` は `独立 / 補足 / 上書き / 置換 / 未定義部分の補完` の単一値だけを許可し、`relations=[<trim済み値>]` へ固定する。`<br>` による複数関係は許可しない
- `関連仕様根拠ID` の複数IDは `<br>` 区切り。空欄は `related_authority_refs=[]`
- `source_refs[]` / `related_authority_refs[]` はtrim・duplicate拒否後に昇順canonical化する
- 種別は既存SPEC / DECISION / 承認済みASM
- INF / UNKNOWNはCurrent Effective Authority inputへ含めない
- LLMがnormalized Authority JSON、Machine Entity wrapper、fingerprint、expected identityを再生成しない

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

AC / Behavior / UC / US chainの `関連仕様項目ID` にはSPEC / DEC / INF / UNK等が現れ得ますが、AC Entityの `authority_refs[]` / `upstream_entity_dependencies[]` へ投影するのは09のCurrent Effective Authorityに存在するcurrent SPEC / DECISION / approved ASMだけです。INF / UNK、inactive Authority、存在しないIDをMachine Entity dependencyへ入れません。

current ACは、chain全体のstable refsを解決した結果としてcurrent Authorityを1件以上持つことを要求します。current Authorityが0件なら `build-machine-evidence / validate` は `state_transition_required` でblockedし、AC Entityを生成しません。helper自身はUNKNOWNやblocked Behaviorを生成しません。LLMが不足の意味を判断して既存UNKをreuseするかnew UNKを作り、親Behaviorをblockedへ戻してから再materializeします。helperはAuthority集合のfilter / existence / currentnessだけを判定し、どのAuthorityが意味上ACを支えるかはLLMがstructured rowへ記録します。

US / UC / BehaviorをMachine Entity typeへ追加しません。親chainをAC contentへ含めるため、親意味変更でAC content fingerprintが変わります。

### 9.3 normalized_skill_input

`build-machine-evidence` はqa-workflow / coverage-analysisへ渡すcanonical spec-analysis normalized inputも返します。

```json
{
  "authorities": [{"authority_id":"SPEC-001"}],
  "acceptance_criteria": [
    {"ac_id":"AC-001","authority_refs":["SPEC-001","DEC-002"]}
  ]
}
```

`authority_refs[]` はAC / Behavior / UC / US chain全体のstable refsを09のCurrent Effective Authority集合へ解決した結果のunionであり、current SPEC / DECISION / approved ASMだけを残して重複除去・昇順canonical化します。INF / UNKは含めません。current ACでは1件以上必須です。

Agent / LLMがMarkdownからnormalized inputやexpected Entity一覧を再構築しません。

shared runtime contractの `acceptance_criterion` type / expected Entity / requirement-structure-v2連携は `_09_runtime-entity-and-test-requirement-contracts.md` を正本とします。

## 10. question-analysis / Project Context helper contract

### 10.1 unknown_links.py

stdin:

```json
{
  "operation":"validate-links",
  "artifact_markdown":"<question-analysis output>",
  "current_unknown_ids":["UNK-001"],
  "resolved_unknown_ids":["UNK-002"]
}
```

helper自身が `不明点 / 質問一覧` の `ID` / `関連UNKNOWN ID` 列をparseします。

payload:

```json
{
  "question_links":[
    {"question_id":"Q-001","unknown_ids":["UNK-001"]}
  ],
  "unknown_refs":["UNK-001"]
}
```

規則:

- `question_links[]` はquestion_id昇順
- 各 `unknown_ids[]` とtop-level `unknown_refs[]` は昇順・重複なし
- Q-xxx形式
- UNK-xxx形式
- `<br>` 区切り
- current UNKNOWNへの存在参照
- 同一Q内duplicate
- resolved-only UNKNOWNのcurrent question参照

issueは§7.2のtop-level `issues[]` だけに返し、payload内へ重複保持しません。

QとUNKの意味的対応はLLM判断です。

spec-analysis modeからquestion-analysisへ進む場合、`ui_target_package.py inspect` が返す `current_unknown_ids[] / resolved_unknown_ids[]` をそのままunknown_links入力へ渡します。Agentが09からID集合を手作業で再構築しません。

### 10.2 question_ids.py

`skills/question-analysis/assets/output-template.md` へ次のexact tableを追加します。

```markdown
## 質問ID履歴

| ID |
| --- |
```

`不明点 / 質問一覧` はcurrent未解決質問だけを持ち、`質問ID履歴` はその成果物系列で一度でも使用したQ IDをcurrent / resolvedを問わず保持します。両tableともplaceholder `Q-001` を置きません。
`不明点 / 質問一覧` のexact headerは次へ固定します。

```markdown
| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 関連UNKNOWN ID | Runtime Skill | Runtime Unit Key | Model Key | Target Key | Generation Fingerprint | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill | 再開対象 / 実行範囲 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

#### next-id

stdin:

```json
{
  "operation":"next-id",
  "artifact_mode":"create",
  "previous_artifact_markdown":null,
  "artifact_markdown":"<candidate current question-analysis output>"
}
```

payload:

```json
{"next_id":"Q-003"}
```

`artifact_mode` は `create / update` の2値です。createではprevious=nullを要求し、updateではprevious artifactを必須とします。既存成果物更新でprevious=nullを渡した場合はfail-closedでblockedします。

helperの使用済み集合は `build-history` と同じ正本へ固定します。

- previous artifactのcurrent `不明点 / 質問一覧` ID
- previous artifactの `質問ID履歴` ID
- current artifactのcurrent `不明点 / 質問一覧` ID

candidate current artifactに残っている `質問ID履歴` はnext-idの入力集合へ含めません。古い / 誤ったcandidate historyによる番号skipや `id_space_exhausted` を起こさないためです。

- Q-xxx形式・各table内duplicateを検証する
- 使用済み集合の既知最大番号+1を返す
- 使用済みQが0件ならQ-001
- Q-999使用済みなら `id_space_exhausted`
- Qの意味的reuse / new、質問文、分類は判断しない
- Agent / LLMへprevious履歴の事前転記を要求しない

同一runで複数new Qを採番する場合は、返却IDをcandidateのcurrent質問tableへ反映してから、同じprevious artifactと更新済みcandidateを次の `next-id` へ渡します。

#### build-history

stdin:

```json
{
  "operation":"build-history",
  "artifact_mode":"create",
  "previous_artifact_markdown":null,
  "current_artifact_markdown":"<candidate current question-analysis output>"
}
```

payload:

```json
{
  "used_question_ids":["Q-001","Q-002"],
  "question_id_history_markdown":"## 質問ID履歴\n\n| ID |\n| --- |\n| Q-001 |\n| Q-002 |"
}
```

`artifact_mode` のcreate / updateとprevious必須規則はnext-idと同じです。

helperは次のunionを昇順canonical化します。

- previous artifactのcurrent `不明点 / 質問一覧` ID
- previous artifactの `質問ID履歴` ID
- current artifactのcurrent `不明点 / 質問一覧` ID

current artifactに手書きされた既存 `質問ID履歴` は正本入力にせず、helper返却の `question_id_history_markdown` でsection全体を置換します。previous artifactがない初回はcurrent質問IDだけから履歴を生成します。

これにより、回答済みQがcurrent質問一覧から消えても使用済みIDを保持します。`Q-001` 解消後に新規質問が発生した場合、Q-001を再利用せずQ-002を返します。

#### materialize

question-analysisのcurrent Q table / 質問ID履歴を決定論生成します。candidate artifactのその他sectionはそのまま保持します。

stdin:

```json
{
  "operation":"materialize",
  "artifact_mode":"update",
  "previous_artifact_markdown":"<previous question-analysis output>",
  "artifact_markdown":"<candidate artifact with narrative sections>",
  "questions":[
    {
      "draft_key":"q-login-role",
      "identity_action":"new",
      "reuse_id":null,
      "cells":{
        "問題 / 質問":"...",
        "根拠":"...",
        "分類":"要確認",
        "影響範囲 / 成果物":"...",
        "関連UNKNOWN ID":["UNK-001"],
        "Runtime Skill":"",
        "Runtime Unit Key":"",
        "Model Key":"",
        "Target Key":"",
        "Generation Fingerprint":"",
        "回答なしの場合の扱い":"",
        "回答後の正規化先":"SPEC",
        "再開Skill":"spec-analysis",
        "再開対象 / 実行範囲":""
      }
    }
  ]
}
```

- create / updateとprevious必須規則はnext-idと同じ
- reuse rowは `identity_action=reuse / reuse_id=Q-xxx`、new rowは `identity_action=new / draft_key=<unique>`
- helperがprevious current Q + previous history + request内reuse/new割当済みQのunionからnew Qを採番する
- Q tableをID昇順、reference cellをcanonical `<br>` 形式でserializeする
- 同じrunで生成した全Q IDを含む `質問ID履歴` を生成する
- candidate artifact内の既存Q table / 質問ID履歴は正本にせず、2 section全体をhelper生成結果で置換する
- 分類や質問文、UNKNOWNとの意味対応、回答後正規化先の意味は判断しない

payload:

```json
{
  "allocated_ids":[{"draft_key":"q-login-role","question_id":"Q-003"}],
  "artifact_markdown":"<full artifact with current Q / 質問ID履歴 materialized>",
  "used_question_ids":["Q-001","Q-002","Q-003"]
}
```
### 10.3 project_context_ids.py

Project ContextのSection 12 / 13が案件の決定事項 / 仮定の正本ownerである場合に使うdefault allocatorです。Project Context ownerではstable ID rowをidentity履歴として保持し、撤回 / 置換済みでもID row自体を削除しません。内容・状態は更新できますが、previous Project Contextに存在したDEC / ASM IDをcandidateから消しません。

#### next-id

stdin:

```json
{
  "operation":"next-id",
  "previous_artifact_markdown":"<previous Project Context or null>",
  "artifact_markdown":"<candidate Project Context>",
  "kind":"decision"
}
```

`kind` は `decision / assumption` の2値です。

payload:

```json
{"kind":"decision","next_id":"DEC-003"}
```

固定対応:

- `decision` → `## 12. 確定事項（決定事項の正本一覧）` の `ID` 列、prefix `DEC`
- `assumption` → `## 13. 仮定（仮定の正本一覧）` の `ID` 列、prefix `ASM`

helperはprevious + candidate両方の対象tableから使用済みID unionを取り、既知最大番号+1を返します。candidateからprevious IDが誤って消えていても、その番号を再利用しません。existing rowが0件ならDEC-001 / ASM-001、999使用済みなら `id_space_exhausted` です。

#### validate-history

stdin:

```json
{
  "operation":"validate-history",
  "previous_artifact_markdown":"<previous Project Context or null>",
  "artifact_markdown":"<candidate Project Context>"
}
```

payload:

```json
{
  "missing_previous_ids":[],
  "decision_ids":["DEC-001"],
  "assumption_ids":["ASM-001"]
}
```

previousが存在する場合、previous Section 12 / 13に存在した全DEC / ASM IDがcandidateにも存在することを要求します。削除されたIDが1件でもあればblockedです。row順は意味を持たず、ID集合で比較します。状態変更・置換先・本文の意味妥当性は検証しません。

#### materialize

Project ContextがDEC / ASMの正本ownerである場合、Section 12 / 13のID割当とcanonical table serializationをhelperへ寄せます。その他sectionはcandidate artifactの内容を保持します。

stdin:

```json
{
  "operation":"materialize",
  "artifact_mode":"update",
  "previous_artifact_markdown":"<previous Project Context>",
  "artifact_markdown":"<candidate Project Context narrative>",
  "decisions":[{"draft_key":"dec-auth","identity_action":"new","reuse_id":null,"cells":{"確定内容":"...","状態":"有効","決定根拠":"...","影響範囲":"...","関係":"独立","関連仕様根拠ID":[],"置換先ID":[],"備考":""}}],
  "assumptions":[]
}
```

- create / updateを区別し、updateではprevious artifact必須
- new IDはprevious + candidateの全状態rowを使用済み集合として採番する
- previousに存在したDEC / ASM IDはcandidate結果から削除できない
- helperがSection 12 / 13をID昇順・canonical escapeでserializeし、2 tableをsection全体として置換する
- 撤回 / 置換済みrowもidentity historyとして保持する
- 状態変更、置換関係、決定内容、ASM承認可否の意味はLLM / stakeholderが判断する

payload:

```json
{"allocated_ids":[{"draft_key":"dec-auth","stable_id":"DEC-003"}],"artifact_markdown":"<full Project Context with Section 12 / 13 materialized>"}
```

LLM / stakeholder側がsemantic identityのreuse / new、DECISION / ASM区分、決定内容、関係、影響範囲、状態遷移の意味、ASM承認可否を判断します。helperはProject ContextのSection 12 / 13だけを書き換え、その他sectionの意味を変更しません。

案件でProject Contextとは別の決定事項 / 仮定の正本一覧が明示されている場合は、そのownerを維持します。

- Project Contextへ同じDECISION / ASMを複製しない
- `project_context_ids.py` で別ownerのIDを採番しない
- ownerが提供するdeterministicなID割当て / ID履歴機構があり、canonical `DEC-xxx / ASM-xxx` を発行する場合はそれを使用する
- Jira key / ADR番号等のowner固有IDだけしかない場合、それをcanonical Authority IDへ流用しない。owner側でDEC / ASM IDを確定できるまでcurrent Authority登録をblockedとし、外部IDはsource / evidence metadataとして保持する
- ownerが新規canonical IDをまだ確定できない場合、LLMが番号を手計算・推測しない
- PR #16から任意の外部ownerへProject Contextのappend-only規則を強制しない
- 任意schemaを読むgeneric allocatorはPR #16では作らない

`skills/qa-workflow/assets/project-context-template.md` を正本ownerとして使う場合、Section 12 / 13はheader-onlyとし、placeholder `DEC-001` / `ASM-001` を配置しません。

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
- SHA-256はraw file bytesのlowercase 64 hex
- READMEのCurrent payload filesとfile集合 / 順序一致
- CHANGELOGもpayload / hash対象
- semantic projectionではCHANGELOGを除外するがMANIFEST上はcurrent package payloadとして保持

## 13. CHANGELOG contract

最新versionを先頭に置き、version headingはexact `## vNN` とします。

各version entryは次の順序で持ちます。

`### 変更概要`

- 変更理由・意味はLLMが記述する
- helperは本文からstable IDを抽出しない

`### Stable ID changes`

| Stable ID | Change |
| --- | --- |

通常更新ではこのtable全体を `impact.stable_id_changes_markdown` で生成します。Agent / LLMはrowを手入力しません。legacy migrationでは `impact(change_mode=legacy-migration)` がLLMのsemantic mapping結果を受けてtableを生成します。

`Change` は次の5値だけを許可します。

- `added`
- `changed`
- `resolved`
- `retired`
- `migrated`

規則:

- fresh packageの `v00` はbaselineであり、templateどおり `Stable ID changes` tableを空で開始できる。v00時点でcurrent structured rowに存在するIDはbaseline identityとして扱う
- v01以降にpackageへ初登場するtracked stable IDは `added`。通常更新では `impact` がprevious snapshot/current state差分から判定する。UI target mode所有IDの `next-id.stable_id_change` は採番確認用であり、CHANGELOG rowの正本にはしない。外部ownerのDEC / ASMもowner確定IDがpackageへ初登場した差分から `added` とする
- legacy packageからsemantic identityを維持してcurrent schemaへ持ち込んだtracked stable IDは、SRC / SPEC / INF / UNK / DEC / ASM / structural IDを問わずmigration versionで `migrated` とする
- 同一identityを維持したまま内容・状態・関係が変わり、current structured modelへ残る場合は `changed`
- `resolved` はUNKNOWN lineage専用。対象は `UNK-xxx` だけで、そのversionでUNKNOWNが `現在有効か=Yes` から `No` へ閉じたことを表す。DEC / ASMその他のprefixへ `resolved` を使用しない
- resolved UNKNOWNでresolver Authorityだけを変更して `現在有効か=No` を維持する場合、または同じUNKを `現在有効か=Yes / 解消先ID=空` へreopenする場合は `changed` を使う
- reopen後に同じUNKを再度閉じる場合は再び `resolved` を使用できる
- current structured modelからstable ID自体を外す場合でも、`retired` はLLMがそのidentityをpackage trackingから意図的に除去すると判断し `retire_ids[]` へ明示した場合だけ生成する。DEC / ASMが撤回・置換等でcurrent Authorityから外れても09の分析項目へ履歴rowを残す場合は `changed` とする
- 1 version内で同じStable IDを重複させない
- 1つのStable IDに `added` または `migrated` を記録できるのは履歴全体で最初の1回だけ
- `retired` だけをterminal eventとし、その後に `added / migrated / changed / resolved / retired` を再記録しない
- `retired` は明示 `retire_ids[]` によるsemantic decisionがある場合だけ生成し、row消失から自動推測しない
- `next-id / materialize` はcurrent structured row、全versionのこのtable、通常更新で渡されたprevious snapshotのStable ID unionを使用済みIDとして扱う
- 00で一度採番に使った案件固有prefix宣言を削除・別意味へ再定義しない

`### 影響file`

`impact.affected_files_markdown` をそのまま使用します。changed stable IDのprevious/current owner fileとprevious/current exact reference先のunionであり、「実際に本文変更したfile」ではなく今回のsemantic変更に対する再確認候補fileです。`next-id` の入力には使用しません。

helperは次を検証します。

- 最新version headingがPackage Versionと一致
- 各version entryに上記3 headingがexactly one存在
- `Stable ID changes` tableのheader / Change enum / Stable ID形式 / version内duplicate
- 履歴全体で `added / migrated` が同じStable IDへ複数回現れない
- `resolved` はUNK prefixだけに現れ、そのversionでUNKNOWNをresolved状態へ閉じるeventとして扱う
- current UNKNOWN rowが `現在有効か=No` の場合はcurrentな `解消先ID`、`Yes` の場合は空 `解消先ID` を要求する
- resolved後の `changed` によるresolver変更 / reopenと、reopen後の再 `resolved` を許可する
- `retired` 後に同じStable IDのeventが存在しない
- v01以降に初登場するDEC / ASMを `added` として追跡でき、既追跡DEC / ASMの状態変更を `changed`、明示 `retire_ids[]` によるcurrent structured modelからの除去だけを `retired` として受理する
- current structured rowとStable ID履歴のID形式が§6.1の標準prefixまたは00宣言済み案件固有prefix契約に一致する
- `next-id / materialize` input prefixは§6.2の採番対象だけを許可し、DEC / ASM / Qを拒否する
- previous tracked ID消失に明示retire intentがない場合はcompleted packageとして受理しない

helperは「そのIDが実際にnext-id operationから返されたか」という実行履歴を推測・検証しません。検証対象はcurrent packageとCHANGELOGに保存された成果物状態です。

`変更概要` だけをLLMが記述します。`Stable ID changes` と `影響file` はhelper生成です。

## 14. legacy / unversioned package migration

今回のmode導入前に作成済みの仕様理解packageを更新対象として受け取れるようにします。

### 14.1 migrationの基本

schema versionがないpackageを自動変換する汎用migration engineは作りません。legacy file構成は案件ごとに意味が異なるため、semantic mappingはLLMが行います。

LLMは:

1. legacy packageのcurrent内容とstable IDを読む
2. 新schemaの00〜09 / domain fileへ意味をmapする
3. semantic identityが同じ既存SRC / SPEC / INF / UNK / DEC / ASM / structural IDは、実際の正本ownerを維持したままID維持する
4. retained current tracked ID集合と、legacy履歴から明示確認できるretired / resolved IDだけをsemantic mapping結果として確定する
5. new entity / extension / file applicability / narrativeをsemantic inputとして確定する。new ID番号、Markdown row、CHANGELOG eventはまだ手組みしない
6. assetから作った空のcurrent-schema target rootへ `materialize(change_mode=legacy-migration)` を1回実行し、`legacy_source_version / migration_retained_ids[] / legacy_lifecycle_events[] / table_changes[] / prose_updates[]` を渡す
7. helperがretained / terminal IDを採番前に予約し、reuse / new ID割当、Markdown serialization、`migrated / added / resolved / retired`、影響file、Machine Entity、README、MANIFESTまで生成する
8. legacyで未確定だった内容を推測で確定しない
9. current packageに不要な履歴説明はCHANGELOGの変更概要 / migration noteへ残し、current viewへ混ぜない

LLMがCHANGELOG row、stable ID番号、Markdown tableを手入力しません。legacy固有のsemantic mappingだけをLLMに残し、別registry / counter / generic migration engineは追加しません。

DEC / ASMは実際の正本ownerの既存IDを参照し、migrationを理由にUI target packageで再採番しません。Project Context以外の明示正本をProject Contextへ複製しません。

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

production helperのfilesystem / raw hash / projection / README control rendering / next-id / next-domain-file / build-machine-evidence自体はrepository unit testで独立に評価します。

## 16. CI / portability

次を追加:

- `skills/spec-analysis/scripts/ui_target_package.py` compile
- `skills/question-analysis/scripts/unknown_links.py` compile
- `skills/question-analysis/scripts/question_ids.py` compile
- `skills/qa-workflow/scripts/project_context_ids.py` compile
- spec-analysis package単体コピー + `runtime_contract.py` / `authority_entities.py` / `ui_target_package.py` 実行
- question-analysis package単体コピー + `unknown_links.py` / `question_ids.py` 実行
- qa-workflow package単体コピー + `project_context_ids.py` 実行
- valid minimal JSON fixture
- unknown top-level field
- malformed JSON / duplicate key
- 16 MiB境界 / 1 byte超過
- path traversal / absolute payload path / symlink
- missing required file
- invalid schema version
- current package next-versionの `package_root` 読み取り / legacy migration専用explicit previous_version / exact `readme_version_rows_markdown`
- render-readme-controlsのPackage metadata / Current payload files exact MarkdownとREADME.md自身を含むcanonical file順
- build-manifestがREADME controls反映後のraw bytesをlowercase 64 hex SHA-256でhashすること
- next-domain-fileのlowercase kebab-case / max+1 / canonical path / id_space_exhausted
- CHANGELOG `Stable ID changes` exact heading / header / Change enum / duplicate
- inspectのupdate_snapshotがtracked owner row fingerprint / previous exact refs / payload file hashをcanonical生成すること
- next-id / materializeが標準prefix + 00宣言済み案件固有prefixについてcurrent structured row + historical stable ID + previous snapshotから使用済みIDを導出し、更新途中でowner rowから消えたIDも再利用しないこと
- impactがprevious snapshotとcurrent owner row差分からadded / changed / resolvedを導出し、retiredだけは明示retire_idsから生成すること。row消失だけならstate_transition_requiredでblockedすること
- materializeがdraft_key / identity_action / @draft referenceを解決し、canonical table serialization、条件付き標準file同期、CHANGELOG controls、Machine Entities section、README controls、MANIFESTを1 write pathで生成すること
- duplicate canonical heading / table、row列数不一致、escaped pipe / `<br>` reference parse
- duplicate / unknown stable ref
- current UNKNOWNの `現在有効か / 解消先ID` 組合せ、resolved UNKNOWNのresolver変更、same-UNK reopen / re-resolve、`解消先ID` missing / invalid / non-current Authority
- scope applicability / conditional-required file mismatch
- required UI operation decompositionのmissing table / parent / closure
- UCごとの正常 / 準正常 / 例外3分類と定義あり / なし / 未定義整合
- MANIFEST hash mismatch
- semantic / deterministic projection差分、exact `projection / files[] / controls[] / markdown` response、current change summary control frame、transport separator
- projected deterministic evalではraw SHAを再計算せずMANIFEST SHA文字列形式 / file集合 / 順序を評価すること
- 09 table → normalized Authority固定projectionと既存authority_entities.py結果一致
- Authority projectionでscopeがtrim済み非空string、relationsが単一許可値の1要素arrayになること
- current AC Entity contentへ親US / UC / Behavior chainが固定projectionされること
- 親US / UC / Behavior変更でAC fingerprintが変わること
- spec-analysis normalized_skill_input / expected identityがhelper結果から再現できること
- artifact `Machine Entities: spec-analysis` blockがexactly one存在し、runtime_contract.pyの `extract_machine_blocks(..., "Machine Entities")` で読め、helper再生成結果と完全一致すること
- unknown_links.pyのexact `operation=validate-links` / payload / top-level issues contract
- question_ids.pyのheader-only current質問table + `質問ID履歴`、create/update fail-closed、previous current Q + previous history + current current Qだけを共通正本にするnext-id / build-history exact contract、duplicate / Q-999
- `Q-001` 解消でcurrent質問0件になった後の新規質問がQ-002となり、過去Q IDを再利用しないこと
- project_context_ids.pyのSection 12 / 13 exact table、previous + candidate unionでのDEC / ASM採番、validate-historyによるprevious ID削除拒否、canonical DEC / ASM namespace、kind / duplicate / 999 exhaustion
- Project Contextがownerでない案件ではproject_context_ids.pyを使わず、外部ownerのIDを維持し、owner未採番時にLLM hand-numberingへfallbackしないこと
- CHANGELOG / impactがDEC / ASMを追跡可能stable IDとして受理しつつ、ui_target_package.py next-idではDEC / ASMを拒否すること
- fresh v00の空change table、v01以降のDEC / ASM初登場=added、既追跡内容・状態変更=changed、current structured model除去=retiredを区別すること
- resolvedをUNK以外へ使用するとrejectし、resolved後のchangedによるresolver変更 / reopenと再resolvedを許可し、retired後の後続eventだけをrejectすること
- legacy migrationでDEC / ASMを含むretained tracked IDをmigratedとしてseedすること
- question-analysis output templateのcurrent Q table / `質問ID履歴` とProject Context template Section 12 / 13がheader-onlyでplaceholder IDを持たないこと
- legacy migration後fixtureのvalidate PASS

新しいGitHub Actions workflowは作りません。PR #14後の既存CIは `skills/*/scripts` を動的compileするため、helper compile目的のworkflow path追加は不要です。repository unit / runtime integration / portability testを既存test discoveryへ追加します。

## 17. 完了条件

- current packageを `ui-target-v1` として機械識別できる
- helperのoperation / input / output / failure contractが一意
- current packageの `Machine Entities: spec-analysis` blockがexactly one存在し、helper再生成結果と一致する
- UNKNOWNがopen / resolved / resolver変更 / same-ID reopen / re-resolveの各状態で `現在有効か / 解消先ID` 契約を満たし、resolved時はcurrent Authorityへ機械検証可能に閉じる
- current packageの次versionをAgentが転記せずhelperが `package_root` から導出できる
- README metadata / UNKNOWN件数 / payload file tableをAgentが再構築せずcanonical Markdownとして生成できる
- extension fileの必要性 / slug / 案件固有prefixの意味だけLLMが判断し、file連番 / stable ID番号 / 履歴はhelperが決定できる。一度使用した案件固有prefixを再定義しない
- Machine Entity sectionのheading / JSON fence / wrapperをAgentが組まず、build-machine-evidenceがshared render_machine_entities()由来のcanonical Markdown sectionを返す
- new ID採番時にAgentが既知ID集合を手組みせず、CHANGELOG stable ID履歴を含めて過去IDを再利用しない
- new Q / DEC / ASMのsemantic identityはLLM / stakeholder側に残す。Qはcurrent + 使用済み履歴からquestion-analysis helperが番号を決定して過去IDを再利用せず、Project ContextがDEC / ASM ownerの場合はqa-workflow helper、別ownerの場合はそのownerのdeterministic allocatorで番号を決定し、未採番時にLLM hand-numberingへfallbackしない
- semantic row / proseが決まった後のstable ID割当、Markdown escape、row serialization、known section置換、条件付き標準file作成 / 除去、control section更新をmaterializeが決定論実行し、Agentが完成Markdownを手組みしない
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
