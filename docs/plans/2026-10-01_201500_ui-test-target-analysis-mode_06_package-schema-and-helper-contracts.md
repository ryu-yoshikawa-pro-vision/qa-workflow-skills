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
- package version: `^v[0-9]{2,}$`。初回`v00`、以後は数値部分を1増分し最低2桁でzero paddingする。`v09 → v10`、`v99 → v100`。上限は設けない

READMEとMANIFESTの両方へ `ui-target-v1` を記録し、helperが一致を検証します。

schema versionがないpackageはlegacy / unversioned packageとして扱い、current schemaとして直接validateしません。

### Machine Entity namespace

UI target package内のstable IDはpackage-localに採番されます。一方、shared Machine Entity identityは `skill / entity_type / entity_ref` であり、`package_ref` は持ちません。

そのため `ui-target-v1` では、1つのspec-analysis normalized input / current Entity collectionへ複数のcurrent UI target packageのMachine Entity blockを直接連結・mergeしません。複数packageの情報を同じworkflowで扱う必要がある場合は、spec-analysisがAuthority / scope / stable identityを意味統合して1つのcurrent canonical package / `normalized_skill_input` を成立させてから下流へ渡します。統合できない複数packageを同一Entity collectionへ流し込んでpackage-local `SPEC-xxx / AC-xxx` 等の衝突を解決する仕組みはPR #16では追加しません。

`ui-target-v1` のMachine Entity schemaへ `package_ref` を追加しません。

## 2. README schema

READMEには自由記述の概要に加え、次の2表をexact heading / exact headerで持ちます。

### Package metadata

| 項目 | 値 |
| --- | --- |
| Package Schema Version | ui-target-v1 |
| Package Version | v00 |
| Previous Package Version | - |
| Current UNKNOWN Count | 0 |
| Completion Status | complete |
| Ready Scope Count | 1 |
| Blocked Scope Count | 0 |

`Previous Package Version` は初回なら `-`、継続更新なら `materialize` 内部version builderがcurrent package / previous snapshotから導出した `previous_version` を記録します。default policyでは `Package Version` と1 revision差であることをhelperが検証します。legacy移行時はlegacy側の明示versionまたは `legacy-unversioned` を記録できます。

上表は完成packageのschema例です。asset templateでは `Current UNKNOWN Count / Completion Status / Ready Scope Count / Blocked Scope Count` を空で置き、初回materialize時にhelperがcurrent modelから生成します。`Current UNKNOWN Count` は情報量でありblocking判定には使いません。`Completion Status` とscope countsは§7.2のscope progress契約から生成し、完成packageでは空値を許可しません。

### Current payload files

| 順序 | ファイル | 種別 |
| ---: | --- | --- |

templateではbodyを空にし、完成packageでは `materialize` 内部README control builderが全payload rowを生成します。この表はREADME.md自身を含むMANIFESTのpayload file listと完全一致させます。

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

file applicabilityはfile × Scope ID単位です。1件以上のrequired scopeがあるfileは必須、全scopeがnot-applicableなら作成しません。blocked scopeは**構造的invalidではありません**。createではそのscopeのrowを生成せず、updateではそのscopeだけを参照する既存tracking rowを保持します。required scopeのrowは更新可能です。blocked scopeとrequired scopeを同時参照する既存rowは意味を安全に分離できないため変更を拒否して保持します。current UNKNOWNの存在だけで他scopeを停止しません。package全体の進行可否は§7.2の `ready_scope_ids[] / blocked_scope_ids[] / completion_status` を使います。

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

standard 00〜09 fileのheading集合は `skills/spec-analysis/assets/ui-test-target-analysis/` のassetに存在するheadingをcanonical registryとします。LLM / Agentはstandard fileへ新しいheadingを追加・rename・削除せず、既存heading配下の本文だけを生成・更新します。標準構造で表現できない独立domainだけを10+ extension fileへ分離します。

helperが参照整合を検証するstructured tableは以下のexact heading / exact headerを使います。

stable reference列のprefix契約は `_05 §5` を正本とします。全standard tableの `対象構造ID` はUI構造ID（`PAGE / STATE / VIEW / STEP / MODAL / BDLG / PANEL / EXT / SHARED`）だけを許可します。`関連構造ID` はUI構造IDまたはdomain item ID（`FIELD / RULE / FLOW / NOTIFY / INTERACT`）だけを許可し、helperはprefixで機械的に分類します。名称・Path・同一PAGE / Scope等から参照を補完しません。

### 5.1 00_scope_and_context.md

#### 分析対象機能scope一覧

| Scope ID | 対象機能 / 領域 | UI操作判定 | Behavior Decomposition | 関連UNKNOWN ID | 関連仕様項目ID | 根拠 / 備考 |
| --- | --- | --- | --- | --- | --- | --- |

標準ID: `SCOPE-xxx`

許可値:
- UI操作判定: あり / なし / 未確定
- Behavior Decomposition: required / not-applicable / blocked

LLMが意味判断するのは `UI操作判定` です。`Behavior Decomposition` は `あり → required / なし → not-applicable / 未確定 → blocked` の固定対応からhelperが生成し、LLM / Agent入力として独立に指定させません。

固定対応:
- あり → required
- なし → not-applicable
- 未確定 → blocked + 関連UNKNOWN ID必須

#### 条件付き必須file applicability

| ファイル | Scope ID | Trigger判定 | 状態 | 関連仕様項目ID | 根拠 / 備考 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- |
| 03_fields_and_validation.md | SCOPE-001 | あり / なし / 未確定 | required / not-applicable / blocked |  |  |  |
| 04_flows_and_data.md | SCOPE-001 | あり / なし / 未確定 | required / not-applicable / blocked |  |  |  |
| 05_notifications_and_external_interactions.md | SCOPE-001 | あり / なし / 未確定 | required / not-applicable / blocked |  |  |  |
| 08_repository_implementation_status.md | SCOPE-001 | あり / なし / 未確定 | required / not-applicable / blocked |  |  |  |

current Scope IDごとに4fileのrowをexactly 1件ずつ持ちます。LLMが意味判断するのは `Trigger判定` だけです。helperが `あり → required / なし → not-applicable / 未確定 → blocked` を導出し、`状態` をLLM / Agent入力として独立指定させません。`未確定` では関連UNKNOWN IDを1件以上必須にします。Current UNKNOWNが存在しても、このtableまたはscope / behavior rowでblockedへ明示されないscopeは停止しません。

file materializationは全scope rowを集約して決めます。

- requiredが1件以上 → fileを作成 / 保持する
- required=0かつblocked=0 → fileを作成しない / updateでは除去する
- required=0かつblocked>0 → createでは作成しない。updateではblocked scopeに属する既存rowがあれば保持する
- requiredとblockedが混在 → fileを保持し、required scopeだけ更新可能。blocked scopeの既存rowは保持する
- Trigger=`あり`はdomainの存在判定であり、内容不足を理由に `未確定` へ戻さない
- required scopeは、03=FIELD、04=FLOW、05=NOTIFY|INTERACT、08=IMPLについてcurrent / blocked canonical rowを1件以上持つのを原則とする
- identityまで分かるが内容が未確定ならblocked row + UNKNOWNを使う。identity自体を安全に発行できず0 rowになる場合だけ、07のcurrent UNKNOWNにそのScope IDを `Blocking Scope ID`、該当fileを `関連File` として持つことを要求する
- 08のrepository observationは `判定=判断不能` をcurrent observationとして保持できる。repository access自体が未確定でscopeを止める場合は07 UNKNOWN + 関連Fileで表す
- helperはこのclosureを検証するが、FIELD等の意味上の個数や内容を推測生成しない

逆方向整合もdeterministic validationで固定します。

- 03が`not-applicable`のScope IDをFIELD rowの`関連Scope ID`が参照してはならない
- 04が`not-applicable`のScope IDをFLOW rowの`関連Scope ID`が参照してはならない
- 05が`not-applicable`のScope IDをNOTIFY / INTERACT rowの`関連Scope ID`が参照してはならない
- 08が`not-applicable`のScope IDをIMPL rowの`関連Scope ID`が参照してはならない
- 1 rowが複数Scopeを参照し、その一部だけが該当domainで`not-applicable`でもrejectする。helperはScope参照の除去、row split、identity reuse / retireを推測せず、LLMのsemantic updateへ戻す

上記2 tableの `関連仕様項目ID` はstable ID参照専用列です。値は空または `<br>` 区切りのexact stable IDだけを許可し、説明文を混在させません。`根拠 / 備考` は自由記述で、helperはそこに現れるID文字列をstable referenceとして扱いません。

`08_repository_implementation_status.md` のapplicabilityは「そのversionでrepositoryを再確認したか」ではなく、current packageがrepository implementation evidenceを現在保持・利用しているかで判定します。前versionの08をcurrent packageが継続利用する場合は `required` のまま保持し、08内の基準branch / commit / revisionを変更しません。current分析からrepository evidenceを明示的に外した場合だけ `not-applicable` とし、08を除去します。

#### 案件固有extension file一覧

| ファイル | Slug | 責務 | 分割理由 | 関連Scope ID | 関連仕様項目ID | 関連構造ID | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- |

extension fileを使う場合だけrowを持ち、templateはheader-onlyにします。

- `ファイル` は `^(?:1[0-9]|[2-9][0-9]+)_[a-z0-9]+(?:-[a-z0-9]+)*\.md$` のroot-level canonical relative path。10, 11, 12...と10進数で連番し、leading zeroを許可しない
- `Slug` はlowercase kebab-case
- `責務` と `分割理由`、4種類の関連stable refはLLMが意味判断して記述する
- `関連Scope ID / 関連仕様項目ID / 関連構造ID / 関連UNKNOWN ID` は空またはexact stable IDの`<br>`区切り。helperが存在参照とduplicateを検証する
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

UI構造の `種別` 変更でcanonical prefixが変わる場合（例: PAGE → VIEW）は、同じstable IDのreuseを禁止します。LLMが再分類を確定した後、旧IDを `retire_ids[]` へ明示し、新しいprefixでnew IDを採番します。PANEL / POPOVER / GLOBAL UIのように同じPANEL prefixを共有する種別間は、semantic identityが同一とLLMが判断した場合だけ同じIDをreuseできます。

### 5.3 02_behavior_and_business_rules.md

scope単位のsemantic contractは `_08` を正本とします。structured tableは次へ固定します。

#### UI操作一覧

| 操作ID | Scope ID | Actor / Role | 対象構造ID | 操作 | 関連仕様項目ID | 対応UC ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`対象構造ID` は `_05` のUI構造ID exact prefix集合だけを許可します。UIOPはdomain item IDを直接保持せず、操作に意味上関係するFIELD / RULE / FLOW / NOTIFY / INTERACTは親US / UC / Behavior / ACの `関連構造ID` でLLMが明示します。

#### User Story一覧

| US ID | Scope ID | Actor / Role | Goal | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- |

#### Use Case一覧

| UC ID | 関連US ID | Use Case | Trigger | Preconditions | Success Postcondition | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### Behavior一覧

| Behavior ID | UC ID | 関連操作ID | 結果分類 | 振る舞い | Postcondition / Result | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### Use Case振る舞い完全性

| UC ID | 結果分類 | 判定 | 関連Behavior ID | 関連仕様項目ID | 関連UNKNOWN ID | 理由 / 根拠 |
| --- | --- | --- | --- | --- | --- | --- |

#### Acceptance Criteria一覧

| AC ID | Behavior ID | Acceptance Criteria | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- |

not-applicable、またはUI操作有無自体が未確定のscopeはUIOP / US / UC / Behavior / ACを確定済みrowとして持ちません。Behavior Decomposition=`not-applicable`のScope IDをこれらのrowがScopeまたはparent chain経由で参照する状態はdeterministic validationでrejectします。required scopeではUIOP / US / UC / Behavior / ACが `current / blocked` 相当のstate modelを持てます。USは自身のfield / UNKNOWNだけでstateを決め、UC / Behavior / ACは自身のblockerに加えてancestor blockedをeffective stateへ決定論伝播します。ancestor由来blockedだけを理由に子へUNKNOWNを複製しません。semantic identityが既知なら同じstable IDをblockedで保持し、ancestor / 自身のblocker解消後に同IDをcurrentへ戻します。semantic identity自体が未確定ならrowを発行せず、Blocking UNKNOWNの置き場所は `_08 §3.1` の階層別規則へ従います。特にUC identity不明は親US、Behavior identity不明はUse Case振る舞い完全性、AC identity不明は親Behaviorを正本とし、Scopeへ一律集約しません。本当に意味上廃止された項目だけをexplicit retireします。

Behaviorの`関連操作ID`はUIOP stable IDの`<br>`区切り参照です。どのUIOPがBehaviorに意味上関係するかはLLMが判断します。current Behaviorは1件以上のmapped UIOPを参照し、各UIOPの`対応UC ID`にそのBehaviorの`UC ID`が含まれ、UIOPのScopeとUC→USから導出したScopeが一致することをhelperが検証します。blocked Behaviorは確定済みの関連操作だけを保持でき、未確定なら空を許可します。blocked UIOPを参照する場合は同じScopeだけを許可し、current Behaviorからblocked UIOPを参照しません。

ancestor state propagationの意味契約は `_08 §3.1` を正本とします。current descendantは全ancestor currentを要求し、blocked descendantはcurrent / blocked ancestorを参照できます。ancestor由来blockedの子は既知semantic fieldとstable IDを保持し、自身に未確定fieldがない限り自身の`関連UNKNOWN ID`を増やしません。

#### ビジネスルール一覧

| ルールID | 関連Scope ID | ルール名 | ルール詳細 | 適用条件 | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

標準ID: `RULE-xxx`

### 5.4 03_fields_and_validation.md

#### 項目・バリデーション一覧

| 項目ID | 関連Scope ID | 対象構造ID | ラベル / 名称 | 要素タイプ | 入力 / 表示仕様 | 制約 / バリデーション | 関連仕様項目ID | 状態 | 関連UNKNOWN ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

標準ID: `FIELD-xxx`

### 5.5 04_flows_and_data.md

#### 処理フロー一覧

| フローID | 関連Scope ID | 処理名 | トリガー / 操作 | 手順 / 状態遷移 | 結果 | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

標準ID: `FLOW-xxx`

手順が複数ある場合は同一cell内で `<br>` 区切りにし、同一FLOW IDを複数rowへ重複させません。

### 5.6 05_notifications_and_external_interactions.md

#### 通知・外部連携一覧

| 連携ID | 関連Scope ID | 種別 | 名称 | 発火条件 | 宛先 / 遷移先 | 内容 / 挙動 | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

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

| UNKNOWN ID | 確認事項 | 根拠 | 影響範囲 | 関連Scope ID | Blocking Scope ID | 関連File | 関連構造ID | 次の扱い |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`UNKNOWN ID` は09の `分類=UNKNOWN` かつ `現在有効か=Yes` のUNKだけを許可します。

- `関連Scope ID` は意味上影響するcurrent Scope ID、`Blocking Scope ID` はそのうち後続工程を止めるscopeをLLMが明示する。`Blocking Scope ID` は `関連Scope ID` のsubsetでなければならない
- `関連File` は影響するcanonical relative path。standard 00〜09はstandard file registryに存在するpathなら、conditional applicabilityによりそのversionで未materializeでも参照を許可する。extensionはcurrent `案件固有extension file一覧` に宣言され、実fileも存在するpathだけを許可する。空を許可し、helperはこの識別子妥当性とduplicateを検証する
- `Blocking Scope ID` が空ならcurrent UNKNOWNでもworkflow blockerではない。UNKNOWN件数だけからscopeをblockedへしない
- semantic identity自体が未確定でstable rowを発行できない場合は、親scopeを `Blocking Scope ID`、該当domain fileを `関連File` に記録してmachine-readableなblockerとして残す
- question-analysisへ渡すUNKNOWNは、対象blocked scopeの `Blocking Scope ID` に一致する集合をhelperが返す

### 5.9 08_repository_implementation_status.md

#### Repository確認基準

| Repository | Branch / Ref | Commit / Revision | 確認時点 | 関連Scope ID | 備考 |
| --- | --- | --- | --- | --- | --- |

`Repository確認基準` は0..N rowを許可し、`Repository` keyはpackage内uniqueです。normal updateでこのsectionを省略した場合はexisting row集合をそのまま保持します。更新する場合は `keyed_table_updates[]` のfull-replacement契約に従い、再確認したRepository rowだけ値を変更し、未確認Repository rowはprevious modelの値をそのまま含めます。helperは値を推測せず、current branch / revisionへ自動追従しません。

#### Repository実装状況

| 実装確認ID | Repository | 関連Scope ID | 対象 | 観測事実 | 関連仕様項目ID | 判定 | 証拠 / 参照 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

標準ID: `IMPL-xxx`

`判定` は一致 / 差分 / 未実装 / 実装のみ / 判断不能。

- `Repository` は同fileの `Repository確認基準` に存在するexact keyを必須とする
- carry-forwardするIMPL rowは対応Repository baselineを変更しない。repository Aだけを再確認した場合はAのbaselineと必要なAのIMPL rowだけを意味更新し、B等の未確認baseline / IMPL rowはprevious modelの値を保持する
- repository由来の実装事実はAuthorityではない。ただし01のtarget-model structure等へ採用したimplementation-only factが変われば、target-model dependencyとしてAC/TR freshnessの再確認契機にはできる

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

案件固有domain fileは、標準fileの責務へ混在させるべきでない独立domainの**自由記述Markdown**として扱います。

- extension file内にui-target-v1独自のstructured tracking tableを定義しない
- extension file用のcustom stable ID prefixを追加しない
- FIELD / RULE / FLOW / NOTIFY / INTERACT等として構造化・追跡する必要がある情報は03〜05または09のstandard tableへ置く
- extension本文からstable IDを参照してよいが、prose中のIDをhelperがexact referenceとして抽出・検証しない
- extensionのsemantic内容、必要性、責務、分割理由はLLMが判断する
- helperはfile名 / slug / declaration / payload order / MANIFEST / create-update-retireだけを決定論管理する

これにより、案件ごとの動的table schema / column registry / custom ID allocatorを追加しません。

### 5.12 asset initialization contract

`skills/spec-analysis/assets/ui-test-target-analysis/` のtemplateは、実データと誤認できる例示IDを置きません。

- variable structured tableはheader / separatorだけを持ち、`PAGE-001` / `SPEC-001` / `AC-001` 等の例示rowを置かない
- `条件付き必須file applicability` はheader / separatorだけをassetへ置く。Scope IDは実データなので、materializeがcurrent Scope ID × 4fileのrowを生成する
- READMEのPackage Schema Versionは `ui-target-v1`、初回Package Versionは `v00`、Previous Package Versionは `-` を固定初期値とする
- READMEのCurrent UNKNOWN Count / Current payload filesはhelper生成結果を貼り付けるcontrol sectionとし、例示値を置かない
- CHANGELOG初回entryは `## v00` と3つの固定subheading、空の `Stable ID changes` tableを持つ
- Machine Entities blockはschema上の空blockをtemplateに置けるが、完成packageでは `build-machine-evidence` 再生成結果へ置換しvalidate一致を必須とする

extension fileの必要性・責務・分割理由・slug・本文はLLMが判断します。連番とfile/control同期は `materialize` 内部extension allocatorが決定します。

## 6. ID rules

packageがstable reference / CHANGELOG / lifecycle差分で追跡できるstandard prefixと、`ui_target_package.py materialize` 内部allocatorが採番できるprefixを分離します。`ui-target-v1` ではcustom stable ID prefixを追加しません。

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

`DEC / ASM` もpackage内で参照される外部ownerのstable IDなので、exact reference validation、CHANGELOG `Stable ID changes`、`impact` の追跡対象に含めます。v01以降にpackageへ初めて取り込むDEC / ASMは `added`、既に追跡中の同一IDの内容・状態・関係変更は `changed` とします。ただしpackageはDEC / ASMのidentity ownerではないため、**`retire_ids[]` でDEC / ASMをterminal retireしません**。current scopeから外れる場合は09の履歴rowを保持し、Current Effective Authorityから外すだけです。owner側で撤回・置換された場合もpackageではownerのcurrentnessをmirrorして`changed`として追跡します。`resolved` は `UNK-xxx` 専用です。

### 6.2 ui_target_package.py内部allocatorの採番対象

`materialize` 内部allocatorが番号決定できるprefixは、次のstandard prefixだけです。

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

内部allocatorはLLMがnewと判断したrowだけを対象にします。Agentから既知ID一覧を受け取りません。normal updateではhash-only `previous_snapshot` の一致確認後にcurrent packageを再parseして `previous_model` を構築し、そのstructured rowとCHANGELOGに記録されたexact stable ID tokenから使用済みIDを導出します。create / legacy-migrationではcurrent staging modelとmigration入力を使用します。同prefixの既知最大番号+1をbatch allocationします。

削除済み・置換済みentityのIDもCHANGELOGのexact `Stable ID changes` tableへ記録済みである限り再利用しません。stable IDを削除・置換するversionでは、そのIDを同tableへ必ず記録します。

`SRC / SPEC / INF / UNK` は既存spec-analysis契約どおりexact 3桁を維持し、999使用済みなら `id_space_exhausted` でfail-closedにします。PR #16で新設するUI target structural prefixは `PREFIX-\d{3,}` を許可し、999の次を1000として上限なく連番採番します。既存canonical ID体系全体の桁拡張は行いません。
`DEC / ASM` は追跡対象ですが本helperの採番対象ではありません。canonical Authority IDは既存spec-analysis契約どおり常に3桁の `DEC-xxx / ASM-xxx` とします。Project Context以外のownerを利用する場合も、そのownerがcanonical DEC / ASM IDを発行・保持することを前提とします。Jira issue key、ADR番号、外部DB key等のowner固有識別子を `authority_id` へ直接入れず、source / evidence側の参照metadataとして保持します。**canonical DEC / ASM ID lifecycleを提供できない外部ownerはPR #16の対応範囲外**であり、current Authorityへ昇格させません。generic mapping / registryは追加しません。

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

`ui_target_package.py`、`question_ids.py`、`project_context_ids.py` は次を共通原則とします。

- Python 3.11標準ライブラリのみ
- 業務入力はstdinの1 JSON objectだけ
- stdoutは1 JSON object + LFだけ
- CLI positional argument / input file argument / environment variableを業務入力に使わない
- handled invalid input / limit exceededはexit 0でstructured blocked resultを返す
- unexpected internal errorだけexit 1
- handled errorでstderrへ業務データを出さない
- unknown top-level fieldを拒否
- `ui_target_package.py / question_ids.py / project_context_ids.py` のaggregate stdin / stdout上限は本Planのhelper contractとして16 MiB。後続handoffでは§9.3の**ready-scope batch全体**に対する事前検査を行う。`artifact:analysis_entities:all` / `artifact:requirement_structure:all` は別途 `_09` のroot runtime契約でaggregate 16 MiBとし、その他の通常runtime generatorは2 MiBを維持する
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

`valid` はschema / reference / filesystem等の**構造的妥当性**を表し、workflow completionとは分離します。`ui_target_package.py inspect / validate / materialize` はcurrent Scope ID集合から `current_scope_ids[] / ready_scope_ids[] / blocked_scope_ids[]` を返します。`current_scope_ids[]` はcurrent SCOPE row全件のcanonical sortで、`ready_scope_ids[] ∪ blocked_scope_ids[]` とexact一致し、`scope_readiness[].scope_id` 集合ともexact一致させます。次の固定規則で `completion_status` を生成します。

- `blocked_scope_ids=[]` → `complete`
- ready / blockedが両方1件以上 → `partial`
- `ready_scope_ids=[]` かつblockedが1件以上 → `blocked`

workflow readinessではSCOPEを原子的な後続進行単位にします。`Behavior Decomposition=required` は意味モデル上の適用状態であり、workflow readinessのreadyを意味しません。

`Behavior Decomposition=required` のscopeは、readiness計算前に次の最低closureを決定論検証します。

- scope内にUIOP rowが1件以上存在する、またはUIOP semantic identity自体を確定できないcurrent UNKNOWNが07で当該scopeを `Blocking Scope ID`、`02_behavior_and_business_rules.md` を `関連File` に持つ
- current USは1件以上のcurrent / blocked UCへ接続する。Use Case identity未確定のBlocking UNKNOWNを自身に持つblocked USはUC 0件を許可する
- current UCは正常 / 準正常 / 例外3rowを持ち、少なくとも1分類が `定義あり` でcurrent Behaviorへ到達するか、1分類以上が `未定義 + 関連UNKNOWN ID` で当該scopeをblockedにする。3分類すべて `なし` かつBehavior=0件のcurrent UCをreadyにしない
- current Behaviorは1件以上のcurrent / blocked ACへ接続する。AC identity未確定のBlocking UNKNOWNを自身に持つblocked BehaviorはAC 0件を許可する。blocked ACが残るscopeはreadyにしない
- 上記row / blockerのどちらもない欠落はsemantic不足をhelperが推測補完せず `state_transition_required` でfail-closedする

blocked scopeは次のunionです。

- `Behavior Decomposition=blocked` のscope
- そのscopeに属するblocked UIOP / US / UC / Behavior / AC / RULE / FIELD / FLOW / NOTIFY / INTERACTが1件以上あるscope
- current UCの `Use Case振る舞い完全性` に `判定=未定義` が1件以上あるscope
- そのscopeのconditional file applicabilityに `blocked` があるscope
- 07のcurrent UNKNOWNで `Blocking Scope ID` に明示されたscope

current UNKNOWNの存在だけではblockedにしません。下位rowだけをblockedにするとは、Scopeの `Behavior Decomposition=required` をnot-applicable / blockedへ書き換えない意味です。 child identity自体が未確定な場合のUNKNOWN配置は `_08 §3.1` の階層別規則を正本とし、UC identity未確定をScopeだけへ置く、AC identity未確定をScopeだけへ置く、Behavior identity未確定をblocked Behavior rowへ捏造する状態を許可しません。workflow上はその下位blockerが解消するまで当該scopeを `blocked_scope_ids[]` に入れます。`scope_readiness[].blocking_unknown_ids[]` は、Scope自身・自身のUNKNOWNでblockedになった下位row・UC完全性=`未定義`・conditional applicabilityの `関連UNKNOWN ID`、07でそのscopeを `Blocking Scope ID` に持つcurrent UNKNOWNに加え、effective blockedを生じさせたancestor chainのUNKNOWN IDをunion / dedupe / canonical sortします。ancestor由来だけのblocked descendant自身へUNKNOWN IDを複製しません。blockerのroot causeへUNKNOWNが存在しない状態は許可しません。qa-workflowはpackage全体のbinary statusではなくこの結果で影響scopeだけ停止します。completion状態だけを理由に `valid=false` へしません。

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
- write_locked
- write_lock_unavailable
- write_commit_failed
- write_recovery_failed

unknown operation / unknown top-level field / JSON・table schema不正は `invalid_input`、packageのcanonical heading / file set / version schema不一致は `package_schema_mismatch`、参照先不存在は `reference_not_found`、ID重複は `duplicate_id`、MANIFESTのfile set / order / SHA / receipt差分は `manifest_mismatch` へ固定します。package-local lockが他processに保持されている場合は `write_locked`、実行platform / filesystemで必要なprocess-scoped lock primitiveを安全に使えない場合は `write_lock_unavailable` とし、writeを開始しません。callerが保持したsnapshotとcommit直前のcurrent package bytesが変わっていた場合は `stale_snapshot`、previous tracked IDが明示 `retire_ids[]` なしでcurrent modelから消えた場合は `state_transition_required`、staging検証後のpackage commitに失敗して旧packageを復旧できた場合は `write_commit_failed`、旧packageの復旧自体に失敗した場合は `write_recovery_failed` へ固定します。新しいhandled failure種別が実装中に必要になった場合は、実装だけで増やさずこのPlan contractを更新します。

### 7.3 update concurrency / idempotent replay contract

同じ `package_root` への `materialize` はsingle writerです。snapshot照合だけを相互排他として扱わず、PR #14のgeneric claim / shared-resource reservationもこのwrite pathへ流用しません。UI target packageはSkill自身が管理するlocal filesystem packageなので、`ui_target_package.py` がpackage専用の短時間process lockとMANIFEST receiptを所有します。

- lock pathは `package_root=/parent/<name>` に対して `/parent/.<name>.ui-target.lock` exactlyとする。package payload / MANIFEST対象には含めない
- POSIXではPython標準ライブラリの `fcntl.flock(LOCK_EX | LOCK_NB)`、Windowsでは `msvcrt.locking(..., LK_NBLCK, 1)` でlock fileの先頭byteをnon-blocking exclusive lockする。lock fileはregular fileとして固定pathへ置き、symlink / reparse point等の既存filesystem safety違反をrejectする
- lock ownershipはfile内容やPID metadataで判定しない。open handleのOS lockだけを正本とし、正常終了 / exception / process killでhandleが閉じれば解放される。lock file自体は残ってよく、stale lock file削除によるowner推測を行わない
- lock取得競合は `write_locked`、実行platformで必要なprocess-scoped lock primitiveを利用できない / lock APIが失敗する場合は `write_lock_unavailable` としてfail-closedする。本契約のsingle-writer保証は同一host上のlocal filesystemを対象とし、network / shared filesystemのinter-host排他はPR #16の対象外とする
- qa-workflow / standalone callerは `claim_mutable_operation()` / `reserve_shared_resource()` を重ねず、package writeの排他・commit・replay判定を `materialize` に一任する
- `materialize` は入力schema / text newlineを正規化した後、`operation / package_root` を除くmaterialize request全体をcanonical JSON化し、lowercase SHA-256の `request_fingerprint` を生成する。array orderが契約上意味を持つ `table_changes[].rows[] / extension_file_updates[]` 等は順序を保持し、stable reference array等のcanonical sort対象だけ既存規則で正規化してからhashする
- changed=trueでcommitするpackageのMANIFESTへ§12の `Last materialize receipt` を生成し、`request_fingerprint`、artifact/change mode、割当ID / extension path、retire結果、changed files、previous/current package versionを保存する。receiptはhelper-owned controlでありversion up要否の原因に数えない
- lock取得後、current packageがvalidでreceiptの `request_fingerprint` が今回requestと一致する場合は、artifact_mode=create / updateを問わずmutationを再適用せず `replayed=true` で保存済み割当結果を返す。これをsnapshot / create precondition判定より先に行う
- receiptが一致しないupdateだけ、callerの `previous_snapshot` とcurrent packageを照合する。不一致なら `stale_snapshot`。receiptが一致しないcreateはtargetが不存在または空directoryであることを要求し、既存valid packageを別create requestで上書きしない
- changed=falseのno-opはpackageへreceiptを書き込まない。同じrequestの再実行は通常のno-op判定をもう一度行っても副作用がない
- replay対象receiptがlast receiptではなくなっている場合、過去requestを推測して再適用しない。updateはsnapshot mismatch、createは既存targetとしてfail-closedし、current packageから新しいsemantic runを開始する

この契約により、`commit成功 → response返却前 / caller state更新前にprocess停止` しても、同一request replayではnew Stable ID、new extension、retireを二重適用しません。generic transaction manager / distributed lock / storage adapterは追加しません。

### 7.4 canonical bytes / package commit

helperが所有して書き出すcurrent `ui-target-v1` fileは次のbyte contractへ固定します。

- UTF-8 without BOM
- newlineはLFのみ
- file末尾はexactly 1 LF
- `body_markdown` / `change_summary` 等のcaller提供textはCRLF / CRだけをLFへ正規化し、それ以外を意味変更目的でtrim / rewriteしない
- MANIFESTのSHA-256はこの最終canonical bytesに対して計算する

structured Markdown table cellは次のcanonical encodeへ固定します。

- callerのscalar cellはCRLF / CRをLFへ正規化する
- scalar cellにliteral `<br>` は許可しない。複数行はraw LFで受け、helperが `<br>` へ変換する
- encode順はbackslashを`\\`へescape、`|`を`\|`へescape、最後にLFを`<br>`へ変換する。stable reference array cellは各IDを検証後、canonical sortして`<br>`でjoinする
- parserはcanonical outputだけを受理し、ambiguous escape、raw LFを含むtable row、未escape `|` をrejectする
- prose section本文はtable-cell規則の対象外で、§7.4のfile byte contractだけを適用する

`materialize` はtarget fileをcurrent packageへ順次直接書込みません。

1. current packageと同じparent / filesystem上のsibling staging directoryへ全target fileをcanonical bytesで生成する
2. staging側でREADME controls / Machine Entity / MANIFESTを含むfinal validateを完了する
3. commit直前にprevious snapshotをcurrent packageへ再照合する
4. current package rootをsibling backupへ移し、staging rootを`package_root`へ切り替える
5. staging→package_root切替に失敗した場合はbackupを元の`package_root`へ復旧する。復旧成功なら`write_commit_failed`、復旧失敗なら`write_recovery_failed`でblockedとし、staging / backupを診断・手動復旧用に保持する
6. package切替成功後だけbackupを削除し、`changed=true`の成功responseを返す

この方式は汎用transaction managerではなく、UI target packageのcanonical write pathだけに適用します。実装では標準ライブラリの同一filesystem rename / replaceを使い、採用した方式をrepository portability testで固定します。

process kill等でhelper-owned siblingが残った場合のpreflight recoveryもこのwrite path内で固定します。`package_root=/parent/<name>` に対してstagingは `/parent/.<name>.ui-target-staging`、backupは `/parent/.<name>.ui-target-backup` exactlyとし、任意名をscanしません。preflight recoveryは§7.3のprocess lock取得後だけ行います。

- current package rootがvalidなら、残存staging / backupは前回未cleanupのorphanとして削除する。その後receipt replay判定を行い、一致なら既適用結果を返す
- current rootが不存在でvalid backupが存在する場合はbackupをrootへrestoreし、stagingを削除する。restore後にreceipt replay判定 / update snapshot判定を通常どおり行い、caller workflow stateをrecovery根拠にしない
- createでroot / backupが存在せずstagingだけ残る場合は未commit stagingとして削除できる
- root不在 + backup不正、rootとbackupのどちらもinvalid、helper-owned siblingが矛盾状態など一意に復旧できない場合は `write_recovery_failed` でfail-closedし、自動promotion / 推測復旧をしない

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
  "completion_status":"partial",
  "current_scope_ids":["SCOPE-001","SCOPE-002"],
  "ready_scope_ids":["SCOPE-002"],
  "blocked_scope_ids":["SCOPE-001"],
  "scope_readiness":[
    {"scope_id":"SCOPE-001","status":"blocked","blocking_unknown_ids":["UNK-004"]},
    {"scope_id":"SCOPE-002","status":"ready","blocking_unknown_ids":[]}
  ],
  "payload_files":[
    {"order":1,"path":"README.md","kind":"core"}
  ],
  "file_applicability":[
    {"path":"03_fields_and_validation.md","scope_id":"SCOPE-001","trigger":"未確定","status":"blocked","authority_refs":[],"unknown_refs":["UNK-004"]}
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
    "payload_file_sha256":[
      {"path":"README.md","sha256":"<lowercase-64-hex>"}
    ],
    "manifest_sha256":"<lowercase-64-hex>"
  },
  "unresolved_structural_issues":[]
}
```

規則:

- `payload_files[]` はcanonical file order
- `file_applicability[]` は03 / 04 / 05 / 08の順。`trigger` は `あり / なし / 未確定`、`status` はhelper導出結果
- stable IDはprefixのlexicographic順 → numeric suffixの整数昇順でcanonical sortする。`SCOPE-999` は `SCOPE-1000` より前になる
- `domain_files[]` はorder昇順
- `exact_reference_index[]` は `target_id / file / section / row_index / column` の順で安定sort
- `row_index` は対象structured tableのdata rowを1始まりで数える
- `unresolved_structural_issues[]` は `issue_type / file / section / row_index / column / message` を持ち、存在しない位置はnull
- `update_snapshot` はCAS相当の更新前identityだけを持つ。Agent / LLMが編集・再構築しない
- snapshotから信頼するのは `package_version / payload_file_sha256[] / manifest_sha256` だけとし、`tracked_items[] / exact_reference_index[]` 等のderived情報をcallerに持ち回らせない
- materializeはsnapshot hash一致を確認した後、current packageを自身で再parseし、tracking row / current UNKNOWN / exact reference index / lifecycle比較元を再導出してin-memory previous modelとして使う
- `payload_file_sha256[]` のpath集合 + `MANIFEST.md` がsnapshot時点のcurrent package file setであり、materializeはstaging前とcommit直前に全件照合する

`resolved_unknown_ids` は09で `分類=UNKNOWN` かつ `現在有効か=No` のUNK。

### validate

stdin:

```json
{"operation":"validate","package_root":"<path>","previous_snapshot":null}
```

fresh v00 / standalone検証では `previous_snapshot=null` を許可します。通常更新runでは内容編集前の `inspect.payload.update_snapshot` をそのまま渡します。

§2〜§6およびfilesystem safetyを検証します。default version policyでは `^v[0-9]{2,}$`、`v00 / Previous=-` またはcurrent / previousの数値1 revision差とpackage内version一致を検証します。加えて、resolved UNKNOWNの `解消先ID`、`Machine Entities: spec-analysis` blockのexactly-one存在、build-machine-evidence再生成結果との完全一致を検証します。schema/referenceが正しければcompletion blocked packageも `valid=true` とし、payloadの `completion_status` で区別します。

`validate` へ `previous_snapshot` が与えられた場合は、current packageのPackage Version / payload file set・raw hash / MANIFEST raw hashがsnapshotと一致することだけを検証します。hash-only snapshotから過去tracking state / exact referenceを復元してlatest `Stable ID changes` / `影響file` を再計算しません。latest差分の正当性はcanonical write pathである `materialize` がsnapshot一致後に再parseした `previous_model` とprovisional current modelを比較して保証します。standalone `validate` はcurrent package自身のschema / lifecycle履歴整合を検証します。

current packageだけから過去の同version内容とのbyte同一性は証明しません。canonical更新経路では `materialize` がprevious snapshotとの差分を確認し、差分がある完成package保存ではdefault policyのversionを必ず+1します。version導出はmaterialize内部関数としてunit testし、production CLI operationは追加しません。

### materialize内部の決定論処理

次はproduction CLI operationとして公開せず、`materialize` / `validate` が使う内部関数として実装します。

- default vNN version導出
- standard prefixのstable ID batch allocation
- README metadata / Current payload files生成
- extension file番号batch allocation
- MANIFEST file order / SHA-256生成
- snapshot一致後に再parseした `previous_model` とprovisional current modelからのStable ID lifecycle / 影響file算出

これらはAgent / workflowが単独で呼ぶ用途を持たず、canonical package作成 / 更新の一部です。repository unit testは内部関数または `materialize / validate` の入出力を直接検証し、focused CLI wrapperを作りません。

### materialize

通常のpackage作成 / 更新で使うcanonical write pathです。汎用Markdown engineではなく、§2〜§5で定義した `ui-target-v1` の既知file / heading / table registryだけを扱います。通常更新ではAgentがstable ID番号や完成Markdown rowを手書きせず、本operationがsemantic入力からID割当・escape・sort・table serialization・section置換・標準file同期・control再生成まで実行します。

stdin:

```json
{
  "operation":"materialize",
  "package_root":"<path>",
  "artifact_mode":"update",
  "previous_snapshot":{"package_version":"v14","payload_file_sha256":[],"manifest_sha256":"<lowercase-64-hex>"},
  "change_mode":"normal",
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
          "cells":{
            "Scope ID":"SCOPE-001",
            "Actor / Role":"管理者",
            "Goal":"...",
            "関連仕様項目ID":["SPEC-001"],
            "関連構造ID":["PAGE-001"],
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
        {"ファイル":"03_fields_and_validation.md","Scope ID":"SCOPE-001","Trigger判定":"あり","関連仕様項目ID":["SPEC-001"],"根拠 / 備考":"入力項目あり","関連UNKNOWN ID":[]},
        {"ファイル":"04_flows_and_data.md","Scope ID":"SCOPE-001","Trigger判定":"なし","関連仕様項目ID":[],"根拠 / 備考":"対象flowなし","関連UNKNOWN ID":[]},
        {"ファイル":"05_notifications_and_external_interactions.md","Scope ID":"SCOPE-001","Trigger判定":"未確定","関連仕様項目ID":[],"根拠 / 備考":"外部interaction有無が未確定","関連UNKNOWN ID":["UNK-004"]},
        {"ファイル":"08_repository_implementation_status.md","Scope ID":"SCOPE-001","Trigger判定":"なし","関連仕様項目ID":[],"根拠 / 備考":"repository evidence未使用","関連UNKNOWN ID":[]}
      ]
    }
  ],
  "prose_updates":[
    {"file":"06_spec_inconsistencies_and_pending.md","section":"<exact heading>","body_markdown":"..."}
  ],
  "extension_file_updates":[
    {"draft_key":"domain-csv","identity_action":"new","path":null,"slug":"csv-export","responsibility":"CSV export仕様","split_reason":"標準fileと独立したAuthority / flow / rule集合を持つ","scope_refs":["SCOPE-001"],"authority_refs":["SPEC-001"],"structure_refs":["PAGE-001"],"unknown_refs":[],"body_markdown":"..."}
  ],
  "extension_file_retirements":["10_legacy-domain.md"]
}
```

`artifact_mode` は `create / update` の2値です。normal create / legacy-migrationでは `package_root` を**出力先**として扱います。§7.3のlock取得後、同一request receiptがあれば既適用結果を返し、receipt不一致時だけtarget不存在または空directoryを要求します。helperがSkill-local `skills/spec-analysis/assets/ui-test-target-analysis/` を読み、同じparent/filesystem上のsibling staging directoryへasset初期状態を内部展開してからsemantic inputをmaterializeします。Agent / callerへasset copyを要求しません。normal updateでは完成済みcurrent package + non-null previous snapshotを必須としますが、lock取得後のreceipt一致判定をsnapshot比較より先に行います。receipt不一致updateだけsnapshot無しをfail-closedにします。legacy-migrationは `artifact_mode=create` だけを許可します。

`change_mode` は `normal / legacy-migration` の2値です。

normal create / updateのversion policyは`ui-target-v1` defaultだけを使用します。通常更新ではhelperがprevious snapshotのversionからnext version候補を導出しますが、差分確定前にはREADME / CHANGELOG / MANIFESTへ反映しません。semantic / presentationを問わず、requested updateを反映した**user-managed / semantic payload**またはrequested `change_summary` がcurrent packageの対応内容から変わる場合にだけversionを+1します。Package Version / Previous Package Version、CHANGELOGのversion heading / `Stable ID changes` / `影響file`、README generated controls、MANIFESTのように他の変更からhelperが導出するcontrol差分は、変更有無の原因として数えません。provisional payload + requested `change_summary` がcurrentと同一ならno-opとして書込み・version upを行いません。`version_policy / target_version` inputは持ちません。案件固有version policyはPR #16の対象外です。

legacy-migrationでは `previous_snapshot=null` を要求し、`legacy_source_version` は明示 `vNN` または `legacy-unversioned` を必須とします。明示vNNならtargetを次のvNN、`legacy-unversioned` ならtargetをv00 / Previous=`legacy-unversioned`へ固定します。`migration_retained_ids[]` と `legacy_lifecycle_events[]` は§14のsemantic mapping結果だけを受け、helperが番号予約・lifecycle生成へ使います。

table input contract:

`table_changes[]` はstable IDのpackage tracking tableだけを対象にします。ここでいうtracking table / tracking rowはpackage内でstable ID lifecycleを保持する構造上の位置を意味し、DEC / ASM等の実際の正本ownerを意味しません。

- tracking table: 分析対象機能scope一覧、UI構造一覧、UI操作一覧、User Story一覧、Use Case一覧、Behavior一覧、Acceptance Criteria一覧、ビジネスルール一覧、項目・バリデーション一覧、処理フロー一覧、通知・外部連携一覧、仕様矛盾・保留一覧、Repository実装状況、情報源 / 正本参照一覧、分析項目
- `file / section` は§2〜§5のstandard registryに存在するexact pairだけを許可する。extension fileは `table_changes[]` の対象にしない
- `cells` はprimary ID列とhelper-owned derived列を除いたexact header名だけを許可する。UIOP / US / UC / Behavior / RULE / FIELD / FLOW / NOTIFY / INTERACTの `状態` はhelper-ownedでcaller inputを拒否する。stable reference列はJSON string array、通常cellはstringで受ける
- 新規rowは `identity_action=new / reuse_id=null / draft_key=<request内unique>`
- 既存row更新は `identity_action=reuse / reuse_id=<stable ID>`。normalではsnapshot一致後に再parseした `previous_model` に存在するIDだけをreuseでき、legacy-migrationでは `migration_retained_ids[]` に含まれるIDだけをreuseできる
- request内の新規row参照はstable IDの代わりに `@draft:<draft_key>` をreference配列へ指定できる。helperが採番後に解決する
- primary prefixは `file / section` のstandard registryからhelperが導出する。caller inputに `primary_prefix` を持たせない

`keyed_table_updates[]` はstable IDを採番しないview / fixed-key tableの**完成row集合**を対象にし、section単位で全rowを置換します。部分patchは許可しません。exact registryは次です。

| file / section | key | 固定規則 |
| --- | --- | --- |
| `00_scope_and_context.md / 条件付き必須file applicability` | `ファイル + Scope ID` | current Scope IDごとに03 / 04 / 05 / 08の4row exactly。callerは `Trigger判定 / 関連仕様項目ID / 根拠 / 備考 / 関連UNKNOWN ID` を渡し、helperが `状態` を生成する。file順→Scope ID昇順でcanonical sort |
| `02_behavior_and_business_rules.md / Use Case振る舞い完全性` | `UC ID + 結果分類` | current UCごとに3分類 exactly |
| `07_current_unknowns.md / Current UNKNOWN一覧` | `UNKNOWN ID` | 09のcurrent UNKNOWN ID集合とexact一致。`Blocking Scope ID` は `関連Scope ID` のsubset。`関連File` はstandard registry pathなら物理file未作成でも許可し、extensionはcurrent宣言 + current実fileを必須とする |
| `08_repository_implementation_status.md / Repository確認基準` | `Repository` | 0..N row、Repository key duplicate禁止。normal updateでsection省略ならexisting baseline集合を保持する。full replacementで一部Repositoryだけ再確認する場合、未確認rowはprevious値のまま含め、自動でbranch / revisionを更新しない |
| `09_authority_and_traceability.md / 現在有効な仕様根拠` | `仕様根拠ID` | LLMが確定したCurrent Effective Authorityだけ。09分析項目のcurrent SPEC / DECISION / approved ASMへ存在参照 |
| `09_authority_and_traceability.md / 後続Skillへの補足` | `項目` | 項目duplicate禁止。stable refsだけhelper検証 |

`keyed_table_updates[]` のrowは原則exact header名をJSON keyとして持ち、stable reference列だけstring arrayを受けます。例外として `条件付き必須file applicability` は `状態` をcaller入力に含めず、helperが `Trigger判定` から生成します。stable IDをkey / referenceとして持つcellでは、同requestのnew tracking rowを `@draft:<draft_key>` で参照できます。helperはstable tracking ID割当後にkey / reference内の `@draft` を解決し、未解決draftをrejectします。helperがcanonical key order / Markdown escape / `<br>` serialization / row sortを行います。view tableからrowが消えてもtracking stable IDのretireとは扱いません。tracking lifecycleは `table_changes[] / retire_ids[]` だけで管理します。

normal updateで `keyed_table_updates[]` にsectionが無い場合、そのsectionはcurrent packageの完成row集合を保持します。normal create / legacy-migrationでは `条件付き必須file applicability` を必須とし、その他view tableは必要な最終集合を明示します。tracking stable row変更により保持したviewが不整合になればfinal validateでblockedし、helperが意味を推測して自動修正しません。

normative traceability contract:

- UIOP / US / RULE / FIELD / FLOW / NOTIFY / INTERACTの `状態` は自身の必須fieldと `関連UNKNOWN ID` からhelperが導出する。UC / Behavior / ACはそれに加えて§5.3 / `_08 §3.1` のancestor state propagationを適用してeffective `blocked / current` を導出する。callerは `状態` を入力しない
- current Behaviorは`関連操作ID`を1件以上要求する。参照先はmapped UIOPで、UIOPの`対応UC ID`にBehaviorの`UC ID`を含み、UIOP.Scopeと親UCのScopeが一致しなければならない。blocked Behaviorでは確定済み参照だけを保持し、未確定なら空を許可する。helperは意味上の関連性を作らず、存在・state・UC / Scope整合・duplicateだけを検証する
- USは自身の必須field / `関連UNKNOWN ID`だけでstateを導出する。UCは参照USのいずれかがblockedならeffective blocked、Behaviorは親UCがblockedならeffective blocked、ACは親Behaviorがblockedならeffective blockedとする。ancestor由来blockedでは子のstable ID / 既知fieldを保持し、ancestor UNKNOWNを子の`関連UNKNOWN ID`へ複製しない
- descendant自身の必須field不足があるのに自身の`関連UNKNOWN ID`がなく、ancestor blockedだけではその不足を説明できない場合は`state_transition_required`でrejectする。ancestorがcurrentへ戻り、子自身の必須fieldが揃い`関連UNKNOWN ID`が空ならhelperが同じstable IDをcurrentへ戻す
- current / mapped UIOP / US / UC / Behavior / AC / RULE / FIELD / FLOW / NOTIFY / INTERACT rowは `関連仕様項目ID` を1件以上要求する。current ACはさらにcurrent SPEC / DECISION / approved ASMを1件以上要求する。blocked ACが自身の不足でblockedなら `関連UNKNOWN ID` を1件以上要求し、ancestor由来だけのeffective blockedなら自身の `関連UNKNOWN ID` は空を許可する
- current rowの `関連仕様項目ID` はcurrent SPEC / DECISION / approved ASM / INFだけを許可する
- identityは確定しているが内容不足の場合はTriggerや存在判定を書き換えず、blocked row + `関連UNKNOWN ID` 1件以上で表す。identity自体を確定できない場合はstable rowを作らず07のUNKNOWNからscope/file blockerへ閉じる
- RULE blocked rowは `関連Scope ID / ルール名 / 関連UNKNOWN ID`、FIELDは `関連Scope ID / ラベル / 名称 / 関連UNKNOWN ID`、FLOWは `関連Scope ID / 処理名 / 関連UNKNOWN ID`、NOTIFY / INTERACTは `関連Scope ID / 種別 / 名称 / 関連UNKNOWN ID` を最低限必須とする。その他の意味fieldは確定済み分だけ保持できる
- UNKNOWNを `関連仕様項目ID` へ入れてblocked根拠を代用しない
- current ACはさらに§9 / _08の契約どおりcurrent SPEC / DECISION / approved ASM Authorityを1件以上要求し、INFだけではcurrentにしない
- PAGE / STATE / VIEW等の純粋な構造row、ISSUE、IMPLは上記normative必須規則の対象外で、各table固有schemaに従う

prose input contract:

- `prose_updates[]` はcurrent canonical asset / packageにexactly one存在する既存headingの**本文だけ**を置換する。heading行自体は `body_markdown` に含めない
- 新規heading作成、heading rename / deleteは許可しない
- structured table、README generated controls、CHANGELOG generated controls、Machine Entities、MANIFEST等のhelper-owned sectionをtargetにできない
- 同じ `file / section` を1 requestで複数指定しない
- `body_markdown=""` はsection本文を空にするがheading自体は残す
- standard fileのproseだけを対象とする。extension file全体の自由記述は `extension_file_updates[].body_markdown` を使い、`prose_updates[]` でextension headingを部分編集しない
- helperはCRLF / CRをLFへ正規化し、最終file byte contractは§7.4に従う
extension input contract:

- `extension_file_updates[]` のnew rowは `draft_key` unique、`identity_action=new / path=null`、lowercase kebab-case slug、非空responsibility / split_reason / body_markdownと `scope_refs[] / authority_refs[] / structure_refs[] / unknown_refs[]` を要求する。reuseも4参照配列の完成値を渡す。4参照配列では同requestのnew tracking rowを `@draft:<draft_key>` で参照でき、§8のrequest-wide stable draft mapで実IDへ解決してから存在・duplicate・canonical sortを検証する。extension自身のdraft_keyはextension path返却用の別namespaceであり、stable `@draft` 参照先にはしない
- extension fileはstructured tracking table / custom stable IDを持たない。`table_changes[] / keyed_table_updates[] / prose_updates[]` でextension内部を部分編集しない
- `extension_file_retirements[]` はLLMが「そのextension domainをcurrent packageから除去する」と判断したexisting canonical extension pathだけを受ける。duplicate、存在しないpath、同requestでreuse対象のpathを拒否する
- retirement成功時は実fileと00の `案件固有extension file一覧` rowを同じstaging stateから除去する。extension prose中の意味参照はsemantic review対象であり、helperがproseからID / file参照を推測しない
- file order番号自体はstable IDではないため、将来のnew extension採番はその時点のcurrent extension最大番号+1を使用する
- new extension pathはexisting current extension最大番号+1から、request配列順に連続採番する。同じrequest内で複数追加しても空fileによる番号予約を要求しない
- helperは最終pathを00の `案件固有extension file一覧` へcanonical orderで生成し、Agent / LLMがtable rowを組み立てない
stable tracking allocation / lifecycle contract:

- new IDはcanonical file order → section order → request row orderで割り当てる。同一JSON inputから同じID割当になる。legacy-migrationでは `migration_retained_ids[]` と `legacy_lifecycle_events[].stable_id` を採番前の使用済み集合へ必ず含め、current rowに存在しないretired / resolved legacy IDを再利用しない
- unchanged rowはcurrent packageから保持する。requestにない既存rowを削除しない
- `retire_ids[]` はLLMが「この**package-owned** semantic identityをcurrent package modelから意図的に除去する」と判断したIDだけを渡す。DEC / ASMはownerがpackage外なので `retire_ids[]` を拒否する。row消失だけからhelperがretireを推測しない
- `previous_model` に存在するIDがprovisional current modelから消えるのに `retire_ids[]` にない場合は `state_transition_required` で書込み前にblocked
- `retire_ids[]` のIDがprovisional current rowへ残る、`previous_model` に存在しない、provisional current exact referenceから参照されたままの場合はblocked
- UNKNOWN解消はretireではなくrow保持 + resolved、DEC / ASMの撤回 / 置換もlineageを保持する間はrow保持 + changedを使う。ACを含むpackage-owned rowの `current ↔ blocked` は同じstable IDのchanged lifecycleでありretireではない。canonical itemをretireするのは、そのidentityをpackage trackingから意図的に除去し、必要なlineage / exact referenceが残らないとLLMが判断した場合だけ
- structural itemは対象UI構造等が意味上current modelから削除された場合にexplicit retireできる

file / control materialization order:

1. request schema、artifact_mode / change_mode / previous_snapshotの組合せ、path safetyを検証し、text newlineとcanonical sort対象fieldを正規化して `request_fingerprint` を計算する
2. §7.3のpackage-local process lockを取得し、helper-owned staging / backupのpreflight recoveryを行う。current valid packageのlast receiptが `request_fingerprint` と一致する場合は以降のmutationを行わず保存済み結果を `replayed=true` で返す
3. receipt不一致の場合、normal updateではhash-only previous snapshotとcurrent bytesを照合してcurrent packageを再parseし、immutableな `previous_model`（tracking state / UNKNOWN state / exact reference index / current file model）を構築する。normal create / legacy-migrationではtargetが不存在または空directoryであることを確認し、Skill-local assetをsibling staging directoryへ内部展開する。callerがasset初期状態を用意しない
4. version policyを検証し、normal updateではnext version候補だけを保持する。まだPackage Version / CHANGELOG / README / MANIFESTへ反映しない
5. legacy-migrationでは `migration_retained_ids[] / legacy_lifecycle_events[]` の形式・duplicate・lifecycleを検証して使用済みID集合へ予約する
6. 全 `table_changes[]` の `identity_action=new` をcanonical file order → section order → request row orderでrequest-wideに仮採番し、stable `draft_key → stable ID` mapを確定する。この時点ではpackage / historyへ保存せず、failure / no-opでは採番を消費しない
7. tracking row自身、`keyed_table_updates[]` のkey / stable reference、`extension_file_updates[].scope_refs / authority_refs / structure_refs / unknown_refs` にある全 `@draft:<draft_key>` をStep 6のmapで解決する。unknown / duplicate / extension draft namespace参照をrejectする
8. resolved済み `table_changes[]` をin-memory tracking modelへ適用する。reuse identity、new identity、prefix再分類、既存row保持、explicit retire intentの前提を検証する
9. resolved済み `keyed_table_updates[]` のfile × Scope ID applicabilityをparseし、`Trigger判定` からscope単位の状態を導出する。applicabilityをfile単位へ集約して条件付き標準file集合を確定する。Trigger=`あり`のrequired scopeは維持し、内容不足をTriggerへ逆流させない。identity確定済みdomain itemはcurrent / blocked row、identity未確定なら07のBlocking Scope ID + 関連Fileでclosureする
10. `extension_file_updates[]` のnew pathをexisting current extension最大番号+1からrequest順でbatch allocationし、`extension_file_retirements[]` をexisting current extensionとして検証する。Step 7でresolvedしたstable refsを使って00のextension宣言rowを生成する
11. remaining keyed table full-replacement、extension update / retirement、prose updateをin-memory file集合へ反映する。extension本文はparseしない
12. normal updateの `retire_ids[]` を検証してin-memory tracking modelから除去する。removal予定fileにtracked tracking rowが残る場合は対応retire intent不足としてblockedする。legacy-migrationの過去lifecycle eventは `legacy_lifecycle_events[]` だけから扱い、current row削除操作へ流用しない
13. `build-machine-evidence` 相当処理をprovisional current versionのまま実行し、Machine Entities sectionをcanonical生成する
14. normal updateでは、version metadata、CHANGELOGのversion heading / generated `Stable ID changes` / generated `影響file`、README generated controls、MANIFEST receipt / file tableを除いたprovisional payload bytesと、requested `change_summary` をcurrent packageのpayload / current version `変更概要`へ比較する。どちらも同一なら `changed=false / replayed=false` を返して書込みしない。仮採番したID / extension pathは保存・予約しない
15. changed normal update / normal create / legacy-migrationでtarget Package Version / Previous Package Versionを確定する。normal createはv00 / -、legacy-migrationはlegacy source contract、normal updateはStep 4のnext version候補を使う
16. normal updateではStep 3で再parseした `previous_model` + provisional current model + explicit retire intent、legacy-migrationではmigration retained / lifecycle mapping + current tracking modelから内部lifecycle / impact builderが差分を生成し、CHANGELOGのtarget version entryへ `変更概要 / Stable ID changes / 影響file` を生成する。normal createはv00 baseline entryを生成する
17. README controlsをcanonical生成・置換する
18. `request_fingerprint` と今回の確定割当 / retire / changed file / version結果から§12 `Last materialize receipt` を生成する
19. MANIFEST file tableを最後に再生成し、§7.4のcanonical bytesへencodeした完成file集合をsibling staging directoryへ書き出す
20. staging packageに対してfinal validateを実行する
21. commit直前にreceipt不一致updateのprevious snapshotをcurrent packageへ再照合し、§7.4のpackage commitを実行する。全file切替と旧backup cleanupまで成功した場合だけ成功responseを返す

payload:

```json
{
  "changed":true,
  "replayed":false,
  "request_fingerprint":"sha256:<lowercase-64-hex>",
  "completion_status":"partial",
  "current_scope_ids":["SCOPE-001","SCOPE-002"],
  "ready_scope_ids":["SCOPE-002"],
  "blocked_scope_ids":["SCOPE-001"],
  "scope_readiness":[{"scope_id":"SCOPE-001","status":"blocked","blocking_unknown_ids":["UNK-004"]},{"scope_id":"SCOPE-002","status":"ready","blocking_unknown_ids":[]}],
  "allocated_ids":[{"draft_key":"us-login","stable_id":"US-003"}],
  "allocated_extension_files":[{"draft_key":"domain-csv","path":"10_csv-export.md"}],
  "retired_ids":["PAGE-009"],
  "retired_extension_files":["10_legacy-domain.md"],
  "changed_files":["README.md","02_behavior_and_business_rules.md","CHANGELOG.md","MANIFEST.md"],
  "previous_package_version":"v14",
  "package_version":"v15"
}
```

`changed=false` のno-opでは `replayed=false`、`allocated_ids=[] / allocated_extension_files=[] / retired_ids=[] / retired_extension_files=[] / changed_files=[]` とし、`request_fingerprint` と `previous_package_version / package_version / completion_status / current_scope_ids[] / ready_scope_ids[] / blocked_scope_ids[] / scope_readiness[]` は今回request / current package値を返します。provisional処理で一時的に割り当てたID / extension pathは保存・予約しません。create / legacy-migrationは初回成功時 `changed=true / replayed=false` です。同一receipt replayではoriginal receiptの `changed / allocated_* / retired_* / changed_files / previous_package_version / package_version` を返し、`replayed=true` とします。

通常のUI target package更新は `materialize` を唯一のwrite pathとします。採番 / version / README controls / MANIFEST / lifecycle / impactは内部関数とし、production CLIへ公開しません。`build-machine-evidence` だけはmaterialized packageから下流handoffを再生成する独立用途があるためread-only production operationとして残します。

### materialize内部control / lifecycle生成

MANIFEST、Last materialize receipt、README controls、Stable ID changes、影響fileは `materialize` 内部で生成します。

- MANIFEST自身は自己hash対象にせず、canonical file orderの最終raw bytesをSHA-256でhashする
- Stable ID lifecycleはsnapshot hash一致後にhelperが再parseしたprevious current model / provisional current tracking row / explicit `retire_ids[]` から生成し、row消失だけでretireしない
- 影響fileはhelperが再導出したprevious/current tracking file + exact reference先unionとし、caller-provided derived indexを信頼しない。本文修正必須という意味判断は行わない
- legacy migrationではLLMが明示したretained ID / lifecycle eventだけを入力にし、legacy proseからidentityを推測しない

内部関数単体または `materialize / validate` 経由でrepository unit testし、これら専用のproduction operationは作りません。

### build-machine-evidence

stdin:

```json
{"operation":"build-machine-evidence","package_root":"<path>","scope_ids":null}
```

`scope_ids` は `null` またはcurrent ready Scope IDのnon-empty arrayです。duplicate / unknown / blocked scope IDを拒否し、helperがcanonical sortします。 `current_scope_ids[]` はread-only outputでcaller入力にはせず、helperがcurrent SCOPE rowから毎回再導出してretired SCOPE IDを含めません。canonical qa-workflowでdownstream `artifact:*:all` runtimeへ渡す場合は、`ready_scope_ids[]` が1件以上の時だけ `scope_ids[]` を渡し、その集合が `inspect.ready_scope_ids[]` とexact一致することを要求します。`ready_scope_ids=[]` ではこのoperationを空配列で呼ばずdownstream runtimeをdispatchしません。一部ready scopeだけのsubset実行をglobal `:all` artifactの代替にしません。

§9に従い09からnormalized Authority inputを生成して既存 `authority_entities.py` のbuilderを呼びます。linked domain itemはcurrent AC / 親Behavior / 親UC / 親USの `関連構造ID` に明示されたdomain item IDだけを対象にし、linked UIOPの `対象構造ID` からdomain itemを逆引きしません。linked UI structureは、同chainの `関連構造ID` にあるUI構造ID、linked UIOPの `対象構造ID`、linked domain itemの `対象構造ID / 関連構造ID` にあるUI構造IDをseedとし、`親構造ID` をrootまで辿ります。domain itemから別domain itemへ再帰展開しません。これらとscope、関連current INFからAcceptance Criterion Machine Entityを生成して統合し、missing parent / self-parent / cycleはrejectします。

payloadは `scope_ids` で分けます。

`scope_ids=null`:

```json
{
  "normalized_authorities":[],
  "normalized_skill_input":{"authorities":[],"acceptance_criteria":[]},
  "acceptance_criterion_entities":[],
  "machine_entities":[],
  "expected_entity_identities":[],
  "current_scope_ids":["SCOPE-001","SCOPE-002"],
  "ready_scope_ids":["SCOPE-002"],
  "blocked_scope_ids":["SCOPE-001"],
  "machine_entities_markdown":"### Machine Entities: spec-analysis\n\n\`\`\`json\n{...}\n\`\`\`\n"
}
```

`scope_ids=["SCOPE-001","SCOPE-002"]`:

```json
{
  "batch_handoff":{
    "scope_ids":["SCOPE-001","SCOPE-002"],
    "scope_index":[
      {"scope_id":"SCOPE-001","target":"ログイン","ui_operation":"あり","authority_refs":["SPEC-001"]},
      {"scope_id":"SCOPE-002","target":"自動更新","ui_operation":"なし","authority_refs":["SPEC-002"]}
    ],
    "normalized_skill_input":{"authorities":[],"acceptance_criteria":[]},
    "machine_entities":[],
    "expected_entity_identities":[]
  }
}
```

helperは各scopeを§9.3の固定reachabilityで内部projectionした後、Authority / current AC / Machine Entity / expected identityをstable identityでunion / dedupeします。同一identityが複数scopeから現れる場合、canonical contentが一致すれば1件へ統合し、不一致ならinternal contract violationとしてfail-closedします。blocked scope由来のrowはbatchへ入りません。`scope_index[]` はready scopeごとに `scope_id / target / ui_operation / authority_refs[]` を1 row持ち、Scope ID順でcanonical sortします。`target` と `ui_operation` は00のcurrent Scope rowから取得し、`authority_refs[]` はそのscopeの固定reachabilityで解決したcurrent SPEC / DECISION / approved ASMだけを重複除去・canonical sortします。これはtest-analysis / TRDがscope所属を意味判断するためのcompact provenanceであり、full scope payloadを複製しません。各Machine Entity / identity rowのschemaはshared runtime contractを正本とし、配列はentity identityの `skill / entity_type / entity_ref` 順でcanonical sortします。package-global responseはready / blocked scope IDだけを返し、batch responseはpackage-global Machine Entity / Markdownを重複返却しません。統合responseに独自の `implementation_fingerprint` fieldは持ちません。

`machine_entities_markdown` は既存shared `runtime_contract.py::render_machine_entities("spec-analysis", machine_entities)` の戻り値をそのまま使用します。standalone `build-machine-evidence` はread-onlyでありpackageを変更しません。09の `### Machine Entities: spec-analysis` sectionを書き換えるのはcanonical write pathである `materialize` 内部の同一projection処理だけです。Agent / callerがこの返却文字列をpackageへ書き戻しません。

### repository eval projection

multi-file packageを既存semantic / deterministic runnerへ渡すためのprojectionは、Skill production helperではなくrepository専用 `scripts/skills/evals/ui_target_projection.py` が担当します。

- projection modeは `semantic / deterministic`
- 各fileの前へ `<!-- FILE: <relative-path> -->` を付け、本文を要約・意味変更しない
- semanticでは過去CHANGELOG / MANIFESTを混ぜない
- deterministicではcurrent payload + MANIFESTをcanonical順で含める
- package root外path / symlink / duplicate / missing fileを拒否する
- raw SHA-256の正当性はproduction `validate` / repository unit testでraw bytesに対して検証する

これはrepository eval harness固有のtransportであり、Skill packageへ同梱しません。

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
- linked_ui_operations[] の uiop_id / actor_role / target_structure_id / operation / authority_refs[]。parent Behaviorの`関連操作ID`に明示されたmapped UIOPだけをprojectionし、同じUCに属するだけのUIOPは含めない
- behavior_id / result classification / behavior / postcondition
- uc_id / use case / trigger / preconditions / success postcondition
- user_stories[] の us_id / actor_role / goal
- scope の scope_id / target / authority_refs[]
- linked_structures[] の structure_id / type / name / state_axis / path_identifier / parent_structure_id / authority_refs[]。AC / Behavior / UC / USのUI構造ref + linked UIOPの `対象構造ID` + linked domain itemのUI構造refをseedにしたparent ancestor closure
- linked_domain_items[] の item_id / item_type / scope_refs[] / semantic content / authority_refs[] / structure_refs[]。AC / Behavior / UC / USの `関連構造ID` に明示されたFIELD / RULE / FLOW / NOTIFY / INTERACTだけ。UIOP targetや同一PAGE / Scopeから逆引きせず、domain item間の再帰展開もしない
- linked_inferences[] の inf_id / canonical analysis content。direct current INFだけ
- authority_refs[]

AC / Behavior / UC / US chainに加え、linked UIOP、scope、linked structures、linked domain itemsの `関連仕様項目ID` をAuthority unionへ含めます。AC Entityの `authority_refs[]` / `upstream_entity_dependencies[]` へ投影するのは09のCurrent Effective Authorityに存在するcurrent SPEC / DECISION / approved ASMだけです。linked current INFは `linked_inferences[]` のcontent fingerprintへ寄与させ、Machine Entity dependencyへは入れません。UNK、inactive Authority、存在しないIDもdependencyへ入れません。

current ACは、chain全体のstable refsを解決した結果としてcurrent Authorityを1件以上持つことを要求します。current Authorityが0件なら `build-machine-evidence / validate` は `state_transition_required` でblockedし、AC Entityを生成しません。helper自身はUNKNOWNやstate transitionを生成しません。LLMが不足の意味を判断し、AC semantic identityが同じなら既存UNK reuse / new UNKと同じAC IDのblocked化、Behavior自体も未確定ならBehavior blocked化、意味上廃止ならexplicit retireのいずれかを選んで再materializeします。helperはAuthority集合のfilter / existence / currentnessだけを判定し、どのAuthorityが意味上ACを支えるかはLLMがstructured rowへ記録します。

UIOP / US / UC / Behavior / UI構造 / FIELD / RULE / FLOW / NOTIFY / INTERACT / INFをMachine Entity typeへ追加しません。package-local rowをAC contentへ固定projectionするため、direct structure / ancestor、domain item、INF、UI操作または親意味変更でAC content fingerprintが変わります。repository由来のimplementation-only structureもtarget-model dependencyとしてfingerprintへ寄与しますがAuthorityにはなりません。無関係なpackage rowはprojectionへ含めません。

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

`authority_refs[]` はAC / Behavior / UC / US chain、linked UIOP、scope、linked structures、linked domain itemsのstable refsを09のCurrent Effective Authority集合へ解決した結果のunionであり、current SPEC / DECISION / approved ASMだけを残して重複除去・canonical sortします。linked INFはcontent-only projectionなので含めません。UNKも含めません。current ACではAuthorityを1件以上必須とします。

Agent / LLMがMarkdownからnormalized inputやexpected Entity一覧を再構築しません。

`build-machine-evidence(scope_ids=[...])` は指定された各scopeが `inspect.ready_scope_ids[]` に含まれることを要求します。canonical downstream pathではその集合がcurrent `ready_scope_ids[]` とexact一致します。helperは各ready scope `S` を次の固定規則で個別projectionし、その結果をbatch unionします。

scope所属seed row:

- `Scope ID=S` のSCOPE row
- `Scope ID=S` の4件のfile applicability row
- `Scope ID=S` のmapped UIOP / current US
- `UC → US → Scope ID=S` で到達するcurrent UC
- `Behavior → UC → US → Scope ID=S` で到達するcurrent Behavior
- `AC → Behavior → UC → US → Scope ID=S` で到達するcurrent AC
- `関連Scope ID` にSを明示するcurrent RULE / FIELD / FLOW / NOTIFY / INTERACT
- `関連Scope ID` にSを明示するcurrent extension declaration row。extension本文はparseしない

reference traversal:

- seed rowの `関連仕様項目ID` はstable IDとしてのみ読む
- seed rowの `関連構造ID` は `_05` のexact prefix集合でUI構造IDとdomain item IDへ分離する
- UIOPの `対象構造ID` はUI構造IDとしてだけ読む
- domain item IDはseed rowから直接参照されたitemだけを追加する。追加domain itemの `関連構造ID` から別domain itemへ再帰展開しない
- UI構造IDはseed row、linked UIOP、追加domain itemの明示参照をunionし、その `親構造ID` だけをrootまで辿る
- extension declarationはrowに明示されたstable refだけを使い、自由記述本文からedgeを抽出しない

Authority projection:

- 上記seed row、直接追加したdomain item、到達したUI構造rowの `関連仕様項目ID` と、scope所属current AC Entityの `authority_refs[]` をunionする
- 09のCurrent Effective Authorityに存在するcurrent SPEC / DECISION / approved ASMだけを残し、INF / UNK / inactive Authorityはhandoffの `authorities[]` へ入れない
- 同じAuthorityが複数scopeから明示参照される場合は各scope handoffへ入る

Acceptance Criterion projection:

- `AC → Behavior → UC → US → Scope` のparent chainでSへ到達するcurrent ACだけを `acceptance_criteria[]` / AC Entityへ含める
- UI操作なしscopeではAC集合が空でもよく、scope row / applicability / domain item / extension declaration / UI構造の明示refから必要Authorityをprojectionする

禁止:

- 09の `適用範囲` 自由記述、名称、Path、同一PAGE、本文類似、Authority共有から新しいedgeを作らない。scope所属は `Scope ID / 関連Scope ID` またはUS→UC→Behavior→ACの明示parent chainだけで決める
- ACとdomain itemの意味関係をhelperが推測しない。必要なedgeがsemantic inputに無い場合はsemantic quality gate側の不足であり、helperが補完しない

qa-workflow / test-analysisはpackage-global Machine Entity集合をMarkdownからfilterしません。current `inspect.ready_scope_ids[]` が1件以上なら全件を `build-machine-evidence(scope_ids=ready_scope_ids)` へ渡して1つのcanonical batch handoffを取得し、Authority / AC / Entityのmerge・dedupeをAgentが行いません。`ready_scope_ids=[]` ならbatch handoff自体を生成しません。batch handoffから `artifact:analysis_entities:all` / `artifact:requirement_structure:all` へ実際に渡すcanonical stdin JSON bytesを構成した**後**に16 MiB上限を事前検査します。2 MiBを超えても16 MiB以下なら1つの`:all` requestとして処理し、16 MiBを超える場合はruntimeを起動せず `limit_exceeded` とします。scopeごとの個別run・subset run・silent truncate・auto splitで回避しません。その他の通常runtime generatorは2 MiB上限を維持します。

blocked scopeをquestion-analysisへ送る場合は `inspect.scope_readiness[].blocking_unknown_ids[]` を使い、current UNKNOWN全件をAgentがfilterしません。

shared runtime contractの `acceptance_criterion` type / expected Entity / requirement-structure-v2連携は `_09_runtime-entity-and-test-requirement-contracts.md` を正本とします。

## 10. question-analysis / Project Context helper contract

### 10.1 question_ids.py

`skills/question-analysis/assets/output-template.md` の `不明点 / 質問一覧` と `質問ID履歴` を扱います。両tableはheader-onlyでplaceholder Q IDを持ちません。

公開operationは2つだけです。

#### validate-links

stdin:

```json
{
  "operation":"validate-links",
  "artifact_markdown":"<question-analysis output>",
  "current_unknown_ids":["UNK-001"],
  "resolved_unknown_ids":["UNK-002"]
}
```

helper自身が `不明点 / 質問一覧` の `ID / 関連UNKNOWN ID` をparseし、Q / UNK形式、同一Q内duplicate、current known UNKNOWNへの存在参照、resolved-only UNKNOWN参照を検証します。QとUNKの意味的対応はLLM判断です。

payload:

```json
{
  "question_links":[{"question_id":"Q-001","unknown_ids":["UNK-001"]}],
  "unknown_refs":["UNK-001"]
}
```

#### materialize

question-analysisのcurrent Q table / 質問ID履歴を決定論生成します。candidate artifactのその他sectionはそのまま保持します。

stdin:

```json
{
  "operation":"materialize",
  "artifact_mode":"update",
  "previous_artifact_markdown":"<previous question-analysis output>",
  "artifact_markdown":"<candidate artifact with narrative sections>",
  "current_unknown_ids":["UNK-001"],
  "resolved_unknown_ids":["UNK-002"],
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

- `artifact_mode=create / update` を区別し、createではprevious=null、updateではprevious artifact必須とする
- reuse rowは `identity_action=reuse / reuse_id=Q-xxx`、new rowは `identity_action=new / draft_key=<unique>`
- helperがprevious current Q + previous history + request内reuse/new割当済みQのunionからnew Qを採番する
- Q tableをID昇順、reference cellをcanonical `<br>` 形式でserializeする
- 同じrunで生成した全Q IDを含む `質問ID履歴` を生成する
- candidate artifact内の既存Q table / 質問ID履歴は正本にせず、2 section全体をhelper生成結果で置換する
- `materialize` 自身が生成後artifactへ `validate-links` と同じcurrent / resolved UNKNOWN存在検証を適用し、不存在・resolved-only・同一Q内duplicate参照を含むartifactを成功として返さない
- `validate-links` operationは既存artifactのstandalone検証用途として残す。canonical write pathでは別operation呼出しをAgentへ要求しない
- 分類や質問文、UNKNOWNとの意味対応、回答後正規化先の意味は判断しない

payload:

```json
{
  "allocated_ids":[{"draft_key":"q-login-role","question_id":"Q-003"}],
  "artifact_markdown":"<full artifact with current Q / 質問ID履歴 materialized>",
  "used_question_ids":["Q-001","Q-002","Q-003"]
}
```

### 10.2 project_context_ids.py

Project ContextのSection 12 / 13が案件の決定事項 / 仮定の正本ownerである場合に使うdefault allocatorです。Project Context ownerではstable ID rowをidentity履歴として保持し、撤回 / 置換済みでもID row自体を削除しません。内容・状態は更新できますが、previous Project Contextに存在したDEC / ASM IDをcandidateから消しません。

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
- canonical `DEC-xxx / ASM-xxx` lifecycleを提供できない外部ownerはPR #16の対応範囲外とする。Jira key / ADR番号等をcanonical Authority IDへ流用せず、current Authorityへ昇格させない。外部IDはsource / evidence metadataとしてのみ保持する
- ownerが新規canonical IDをまだ確定できない場合、LLMが番号を手計算・推測しない
- PR #16から任意の外部ownerへProject Contextのappend-only規則を強制しない
- 任意schemaを読むgeneric allocatorはPR #16では作らない

`skills/qa-workflow/assets/project-context-template.md` を正本ownerとして使う場合、Section 12 / 13はheader-onlyとし、placeholder `DEC-001` / `ASM-001` を配置しません。

## 11. filesystem safety

`ui_target_package.py` が読むpathに次を適用します。

- `inspect / validate / update` の `package_root` は存在するcurrent package directory。`materialize(create / legacy-migration)` の `package_root` は出力先で、不存在または空のnon-symlink directoryだけを許可する
- absolute / relativeどちらの入力でもresolve後のrootを固定
- payload / MANIFESTからのabsolute path禁止
- `..` によるroot外参照禁止
- symlink file / symlink directory拒否
- regular fileだけを読む
- completed current package root直下にはcanonical payload files + `MANIFEST.md` 以外のregular fileを許可せず、nested directoryも拒否する。helper-owned staging / backup / process lock fileはpackage rootのfixed siblingなのでpackage file setに含めない
- UTF-8 strict decode
- current `ui-target-v1` packageはBOMなしUTF-8、LFのみ、terminal LF exactly oneを要求する。legacy inputはmigration時に§7.4へcanonicalizeする
- current package全read bytes合計16 MiB以下。これはUI target packageのsupported hard limitとし、超過時は`limit_exceeded`でfail-closedする。helperが自動分割や複数package化を行わない
- `build-machine-evidence` のstdin / stdoutも16 MiB上限を維持する。package-global responseへscope別full handoffを複製しないことで不要な膨張を避ける。`scope_ids=ready_scope_ids` のbatch handoffを `artifact:analysis_entities:all` / `artifact:requirement_structure:all` へ接続する場合は、batchから構成した最終canonical stdin全体へ別途16 MiB上限を実行前に検証する。package read bytesが16 MiB以内でもruntime metadata等を含む最終requestが16 MiBを超える可能性があるため、package上限だけをdownstream実行可能性の保証にはしない
- duplicate normalized relative path拒否
- case-sensitive canonical filenameを要求
- filesystem read失敗を意味上のUNKNOWNへ変換せずblocked

network accessは行いません。package writeのprocess lockは同一host上のlocal filesystemだけをsupported coordination範囲とし、network / shared filesystem向けdistributed lockへ拡張しません。

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

file tableの後にexact heading `### Last materialize receipt` とcanonical JSON fenceを1つ持ちます。completed packageではexactly one必須です。

```json
{
  "receipt_version":"materialize-receipt-v1",
  "request_fingerprint":"sha256:<lowercase-64-hex>",
  "artifact_mode":"update",
  "change_mode":"normal",
  "changed":true,
  "allocated_ids":[{"draft_key":"us-login","stable_id":"US-003"}],
  "allocated_extension_files":[{"draft_key":"domain-csv","path":"10_csv-export.md"}],
  "retired_ids":["PAGE-009"],
  "retired_extension_files":["10_legacy-domain.md"],
  "changed_files":["README.md","02_behavior_and_business_rules.md","CHANGELOG.md","MANIFEST.md"],
  "previous_package_version":"v14",
  "package_version":"v15"
}
```

規則:

- receiptはhelper生成controlであり、LLM / Agentは入力・編集しない
- `request_fingerprint` は§7.3のcanonical materialize request fingerprint
- `allocated_ids[] / allocated_extension_files[]` はそのcommitで実際に確定したrequest内draft mappingだけを持つ
- `retired_ids[] / retired_extension_files[] / changed_files[]` は成功responseとexact一致する
- receipt自体はMANIFEST内にあるためpayload hash対象外。MANIFEST raw hashには当然含まれ、次回 `inspect.update_snapshot.manifest_sha256` へ反映される
- no-opはpackageを書き換えないためreceiptを更新しない
- validateはreceipt schema / fingerprint形式 / path / Stable ID形式と、receiptの `package_version` がMANIFEST / README current versionへ一致することを検証する。過去requestのsemantic正当性をreceiptから再判定しない
- replayはlast receiptとのexact request fingerprint一致だけを使い、過去CHANGELOGからreceiptを推測復元しない

## 13. CHANGELOG contract

最新versionを先頭に置き、version headingはexact `## vNN` とします。

各version entryは次の順序で持ちます。

`### 変更概要`

- 変更理由・意味はLLMが記述する
- helperは本文からstable IDを抽出しない

`### Stable ID changes`

| Stable ID | Change |
| --- | --- |

通常更新ではこのtable全体を `materialize` 内部lifecycle builderが生成します。Agent / LLMはrowを手入力しません。legacy migrationでも `materialize(change_mode=legacy-migration)` がLLMのsemantic mapping結果を受けてtableを生成します。

`Change` は次の5値だけを許可します。

- `added`
- `changed`
- `resolved`
- `retired`
- `migrated`

規則:

- fresh packageの `v00` はbaselineであり、templateどおり `Stable ID changes` tableを空で開始できる。v00時点でcurrent structured rowに存在するIDはbaseline identityとして扱う
- v01以降にpackageへ初登場するtracked stable IDは `added`。通常更新では `materialize` 内部lifecycle builderがsnapshot一致後に再parseした `previous_model` とprovisional current stateの差分から判定する。内部allocatorの採番結果自体はCHANGELOG rowの正本にせず、外部ownerのDEC / ASMもowner確定IDがpackageへ初登場した差分から `added` とする
- legacy packageからsemantic identityを維持してcurrent schemaへ持ち込んだtracked stable IDは、SRC / SPEC / INF / UNK / DEC / ASM / structural IDを問わずmigration versionで `migrated` とする
- 同一identityを維持したまま内容・状態・関係が変わり、current structured modelへ残る場合は `changed`
- `resolved` はUNKNOWN lineage専用。対象は `UNK-xxx` だけで、そのversionでUNKNOWNが `現在有効か=Yes` から `No` へ閉じたことを表す。DEC / ASMその他のprefixへ `resolved` を使用しない
- resolved UNKNOWNでresolver Authorityだけを変更して `現在有効か=No` を維持する場合、または同じUNKを `現在有効か=Yes / 解消先ID=空` へreopenする場合は `changed` を使う
- reopen後に同じUNKを再度閉じる場合は再び `resolved` を使用できる
- current structured modelからpackage-owned stable ID自体を外す場合、`retired` はLLMがそのidentityをpackage trackingから意図的に除去すると判断し `retire_ids[]` へ明示した場合だけ生成する。DEC / ASMはpackage-ownedではないため`retired`を生成せず、撤回・置換・scope離脱は09の分析項目へ履歴rowを残して`changed`として扱う
- 1 version内で同じStable IDを重複させない
- 1つのStable IDに `added` または `migrated` を記録できるのは履歴全体で最初の1回だけ
- `retired` だけをterminal eventとし、その後に `added / migrated / changed / resolved / retired` を再記録しない
- `retired` は明示 `retire_ids[]` によるsemantic decisionがある場合だけ生成し、row消失から自動推測しない
- `materialize` 内部allocatorはsnapshot一致後に再parseした `previous_model` のcurrent structured row、全versionのこのtable、provisional current model、legacy-migrationでは明示migration lifecycle入力のStable ID unionを使用済みIDとして扱う。hash-only snapshot自体からStable IDを読み取らない

`### 影響file`

`materialize` 内部impact builderが生成した `affected_files_markdown` を使用します。changed stable IDのprevious/current tracking fileとprevious/current exact reference先のunionであり、「実際に本文変更したfile」ではなく今回のsemantic変更に対する再確認候補fileです。stable ID採番の入力には使用しません。

helperは次を検証します。

- 最新version headingがPackage Versionと一致
- 各version entryに上記3 headingがexactly one存在
- `Stable ID changes` tableのheader / Change enum / Stable ID形式 / version内duplicate
- 履歴全体で `added / migrated` が同じStable IDへ複数回現れない
- `resolved` はUNK prefixだけに現れ、そのversionでUNKNOWNをresolved状態へ閉じるeventとして扱う
- current UNKNOWN rowが `現在有効か=No` の場合はcurrentな `解消先ID`、`Yes` の場合は空 `解消先ID` を要求する
- resolved後の `changed` によるresolver変更 / reopenと、reopen後の再 `resolved` を許可する
- `retired` 後に同じStable IDのeventが存在しない
- v01以降に初登場するDEC / ASMを `added` として追跡でき、既追跡DEC / ASMの内容・状態・scope変更を `changed` として受理し、DEC / ASMへの `retired` をrejectする
- current structured rowとStable ID履歴のID形式が§6.1のstandard prefix契約に一致する
- UI target packageの内部allocatorは§6.2の採番対象だけを許可し、DEC / ASM / Qを拒否する
- previous tracked ID消失に明示retire intentがない場合はcompleted packageとして受理しない

helperは内部allocatorの呼出し履歴を成果物から推測・検証しません。検証対象はcurrent packageとCHANGELOGに保存された成果物状態です。

`変更概要` だけをLLMが記述します。`Stable ID changes` と `影響file` はhelper生成です。

## 14. legacy / unversioned package migration

今回のmode導入前に作成済みの仕様理解packageに加え、通常spec-analysisの単一成果物を後から継続利用する必要が生じた場合もmigration入力として受け取れるようにします。

### 14.1 migrationの基本

schema versionがないpackageを自動変換する汎用migration engineは作りません。legacy file構成は案件ごとに意味が異なるため、semantic mappingはLLMが行います。

LLMは:

1. legacy packageまたは通常spec-analysis単一成果物のcurrent内容とstable IDを読む
2. 新schemaの00〜09 / domain fileへ意味をmapする
3. semantic identityが同じ既存SRC / SPEC / INF / UNK / DEC / ASM / structural IDは、実際の正本ownerを維持したままID維持する
4. retained current tracked ID集合と、legacy履歴から明示確認できるretired / resolved IDだけをsemantic mapping結果として確定する
5. new entity / extension / file applicability / narrativeをsemantic inputとして確定する。new ID番号、Markdown row、CHANGELOG eventはまだ手組みしない
6. assetから作った空のcurrent-schema target rootへ `materialize(change_mode=legacy-migration)` を1回実行し、`legacy_source_version / migration_retained_ids[] / legacy_lifecycle_events[] / table_changes[] / prose_updates[] / extension_file_updates[]` を渡す
7. helperがretained / terminal IDを採番前に予約し、reuse / new ID割当、Markdown serialization、`migrated / added / resolved / retired`、影響file、Machine Entity、README、MANIFESTまで生成する
8. legacyで未確定だった内容を推測で確定しない
9. current packageに不要な履歴説明はCHANGELOGの変更概要 / migration noteへ残し、current viewへ混ぜない

LLMがCHANGELOG row、stable ID番号、Markdown tableを手入力しません。legacy固有のsemantic mappingだけをLLMに残し、別registry / counter / generic migration engineは追加しません。

DEC / ASMは実際の正本ownerの既存IDを参照し、migrationを理由にUI target packageで再採番しません。Project Context以外の明示正本をProject Contextへ複製しません。

helperは変換後packageだけをvalidateします。

### 14.2 version

legacy packageに明示 `^v[0-9]{2,}$` がある場合、default policyでは`materialize`内部version builderの結果を新package versionとします。通常spec-analysis単一成果物はpackage versionを持たないため `legacy-unversioned` として扱います。

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

1. fixture packageをrepository専用 `scripts/skills/evals/ui_target_projection.py --projection deterministic` で1 Markdownへ投影
2. 既存deterministic runnerへ渡す
3. spec-analysis validatorが通常3 canonical tableに加え、mode structured table / stable ref / current UNKNOWN / schema versionを独立検証する

deterministic validatorはproduction helperをimportしてexpectedを生成しません。

production helperのfilesystem / raw hash / README control生成 / internal allocator / build-machine-evidenceはrepository unit testで評価し、eval projectionはrepository専用utilityのtestで独立に評価します。

## 16. CI / portability

次を追加:

- `skills/spec-analysis/scripts/ui_target_package.py` compile
- `skills/question-analysis/scripts/question_ids.py` compile
- `skills/qa-workflow/scripts/project_context_ids.py` compile
- spec-analysis package単体コピー + `runtime_contract.py` / `authority_entities.py` / `ui_target_package.py` 実行
- question-analysis package単体コピー + `question_ids.py` 実行
- qa-workflow package単体コピー + `project_context_ids.py` 実行
- valid minimal JSON fixture
- unknown top-level field
- malformed JSON / duplicate key
- 16 MiB境界 / 1 byte超過
- path traversal / absolute payload path / symlink
- missing required file
- invalid schema version
- materialize内部version builderのcurrent package読み取り / legacy migration source version / default vNN連続性
- materialize内部README control builderのPackage metadata / Current payload files exact MarkdownとREADME.md自身を含むcanonical file順
- materialize内部MANIFEST builderがREADME controls反映後のraw bytesをlowercase 64 hex SHA-256でhashし、`Last materialize receipt`をexactly one生成・検証すること
- materialize内部extension allocatorのlowercase kebab-case / max+1 / canonical path
- CHANGELOG `Stable ID changes` exact heading / header / Change enum / duplicate
- inspectのupdate_snapshotが `package_version / payload_file_sha256[] / manifest_sha256` だけをcanonical生成し、tracking row fingerprint / exact reference等のderived stateを含めないこと
- materializeがsnapshot hash一致後にcurrent packageを再parseして `previous_model` を構築し、stable ID allocatorがprevious structured row + historical Stable ID + provisional current rowから使用済みIDを導出して、更新途中でtracking rowから消えたIDも再利用しないこと
- materialize内部lifecycle builderが `previous_model` とprovisional current tracking row差分からadded / changed / resolvedを導出し、retiredだけは明示retire_idsから生成すること。row消失だけならstate_transition_requiredでblockedすること
- `validate(previous_snapshot=...)` はsnapshot hash一致だけを追加検証し、hash-only snapshotからlatest lifecycle / impactを再構築しないこと
- materializeが全new tracking IDをfile applicability判定前にrequest-wide仮採番し、tracking / keyed table / extension stable refsの`@draft`を先に解決してからscope applicability / file集合を導出すること。failure / no-opで仮採番を消費しないこと
- materializeがdraft_key / identity_action / @draft referenceを解決し、canonical table serialization、条件付き標準file同期、CHANGELOG controls、Machine Entities section、README controls、MANIFESTを1 write pathで生成すること
- package-local process lockで同一rootへの2 process同時materializeの一方だけがwriteへ進み、process kill / handle close後はstale owner cleanupなしで次runがlock取得できること。unsupported lock primitiveでは`write_lock_unavailable`、競合中は`write_locked`になること
- commit後response前crashを模擬し、同一create / update request replayがMANIFEST receiptから同じallocated ID / extension pathを返して二重採番・二重retireせず`replayed=true`になること。異なるrequestはreceipt replayせずcreate existing-target / update stale snapshot契約へ戻ること
- `Behavior Decomposition` をLLM入力として独立指定させず、`UI操作判定` からfixed mappingで生成すること
- PAGE→VIEW等のprefix変更再分類でreuseをrejectし、explicit retire + new IDを要求すること。同じPANEL prefix内はsemantic identity同一時だけreuseできること
- `prose_updates[]` が既存prose heading bodyだけを置換し、新規heading / heading削除 / structured・generated section上書きを拒否すること
- `extension_file_retirements[]` がexisting current extensionだけを受理し、実fileと00宣言rowを同時除去すること。extension proseからstable referenceを推測しないこと
- canonical bytes、sibling staging final validate、commit直前snapshot再照合、package単位commit、write failure rollback / recovery failureをrepository unit / portability testで固定すること
- duplicate canonical heading / table、row列数不一致、escaped pipe / `<br>` reference parse
- duplicate / unknown stable ref
- current UNKNOWNの `現在有効か / 解消先ID` 組合せ、resolved UNKNOWNのresolver変更、same-UNK reopen / re-resolve、`解消先ID` missing / invalid / non-current Authority
- scope applicability / conditional file Trigger判定→状態導出 / blocked carry-forward / completion status
- required UI operation decompositionのmissing table / parent / closure
- Behavior Decomposition=required scopeについて、UIOP 1件以上またはidentity未確定を示すBlocking UNKNOWN、current US→UC、current UC→Behavior / 未定義UNKNOWN、current Behavior→current / blocked ACの最低closure。row / blockerのどちらもない欠落はrejectすること
- UCごとの正常 / 準正常 / 例外3分類と定義あり / なし / 未定義整合。3分類すべて `なし` かつBehavior=0件のcurrent UCをreadyにしない
- MANIFEST hash mismatch
- repository eval utilityのsemantic / deterministic projection差分、current change summary control frame、transport separator
- projected deterministic evalではraw SHAを再計算せずMANIFEST SHA文字列形式 / file集合 / 順序を評価すること
- 09 table → normalized Authority固定projectionと既存authority_entities.py結果一致
- Authority projectionでscopeがtrim済み非空string、relationsが単一許可値の1要素arrayになること
- current AC Entity contentへlinked UIOP + 親US / UC / Behavior chainが固定projectionされること
- linked UIOP / 親US / UC / Behavior変更でAC fingerprintが変わること
- spec-analysis normalized_skill_input / expected identityがhelper結果から再現できること
- artifact `Machine Entities: spec-analysis` blockがexactly one存在し、runtime_contract.pyの `extract_machine_blocks(..., "Machine Entities")` で読め、helper再生成結果と完全一致すること
- question_ids.pyのexact `operation=validate-links` / payload / top-level issues contract
- question_ids.pyのheader-only current質問table + `質問ID履歴`、materialize create/update fail-closed、previous current Q + previous history + request current Qを使う内部allocator / history union、duplicate / Q-999
- `Q-001` 解消でcurrent質問0件になった後の新規質問がQ-002となり、過去Q IDを再利用しないこと
- project_context_ids.pyのSection 12 / 13 exact table、materialize内部でのDEC / ASM採番、validate-historyによるprevious ID削除拒否、canonical DEC / ASM namespace、kind / duplicate / 999 exhaustion
- Project Contextがownerでない案件ではproject_context_ids.pyを使わず、外部ownerのIDを維持し、owner未採番時にLLM hand-numberingへfallbackしないこと
- CHANGELOG / materialize lifecycle builderがDEC / ASMを追跡可能stable IDとして受理しつつ、UI target package内部allocatorではDEC / ASMを拒否すること
- fresh v00の空change table、v01以降のDEC / ASM初登場=added、既追跡内容・状態・scope変更=changedを区別し、DEC / ASMへのretiredをrejectすること
- resolvedをUNK以外へ使用するとrejectし、resolved後のchangedによるresolver変更 / reopenと再resolvedを許可し、retired後の後続eventだけをrejectすること
- legacy migrationでDEC / ASMを含むretained tracked IDをmigratedとして引き継ぐこと。legacy `retired` eventはpackage-owned IDだけを許可し、DEC / ASMの撤回・置換はowner currentnessを保持したchanged/historyとして移行すること。resolved / retired lifecycle IDは許可prefixを検証したうえでnew採番前に予約すること
- question-analysis output templateのcurrent Q table / `質問ID履歴` とProject Context template Section 12 / 13がheader-onlyでplaceholder IDを持たないこと
- legacy migration後fixtureのvalidate PASS

新しいGitHub Actions workflowは作りません。PR #14後の既存CIは `skills/*/scripts` を動的compileするため、helper compile目的のworkflow path追加は不要です。repository unit / runtime integration / portability testを既存test discoveryへ追加します。

## 17. 完了条件

- current packageを `ui-target-v1` として機械識別できる
- 1つのnormalized spec-analysis handoff / current Entity collectionが1つのcurrent canonical UI target packageだけを由来とし、複数packageのpackage-local IDを直接mergeしない
- production helperのoperation / input / output / failure contractが一意で、focused testだけを理由に公開operationを増やしていない
- current packageの `Machine Entities: spec-analysis` blockがexactly one存在し、helper再生成結果と一致する
- UNKNOWNがopen / resolved / resolver変更 / same-ID reopen / re-resolveの各状態で `現在有効か / 解消先ID` 契約を満たし、resolved時はcurrent Authorityへ機械検証可能に閉じる
- current packageの次versionをAgentが転記せずhelperが `package_root` から導出できる
- README metadata / UNKNOWN件数 / payload file tableをAgentが再構築せずcanonical Markdownとして生成できる
- extension fileの必要性 / 責務 / slug / 本文はLLMが判断し、file連番 / 宣言 / README / MANIFEST同期はhelperが決定できる。extension独自structured table / custom stable IDを追加しない
- Machine Entity sectionのheading / JSON fence / wrapperをAgentが組まず、`materialize` がshared render_machine_entities()由来のcanonical Markdown sectionを書き込む。standalone `build-machine-evidence` は同じsectionをread-onlyで再生成してhandoff / verify用に返すだけでpackage bytesを変更しない
- new ID採番時にAgentが既知ID集合を手組みせず、CHANGELOG stable ID履歴を含めて過去IDを再利用しない
- new Q / DEC / ASMのsemantic identityはLLM / stakeholder側に残す。Qはcurrent + 使用済み履歴からquestion-analysis helperが番号を決定して過去IDを再利用せず、Project ContextがDEC / ASM ownerの場合はqa-workflow helper、別ownerの場合はそのownerのdeterministic allocatorで番号を決定し、未採番時にLLM hand-numberingへfallbackしない
- semantic row / proseが決まった後のstable ID割当、Markdown escape、row serialization、known section置換、条件付き標準file作成 / 除去、control section更新をmaterializeが決定論実行し、Agentが完成Markdownを手組みしない
- helper所有fileがcanonical bytesでstagingされ、package commit失敗時に旧版 / 新版の混在を完成状態として残さない
- current extension domainを不要と判断した場合、canonical materialize経路で実fileと00宣言を廃止できる。extension本文の自由記述はparseせず、宣言rowのfile-level stable refをimpact / existence検証へ使う
- 後続QA工程の判断・期待挙動・test design・freshnessに影響する意味情報がextension本文だけに存在しない。該当Authority / FIELD / RULE / FLOW / NOTIFY / INTERACT等はstandard structured row / 09へ正規化されている
- standard structured tableのheader / ID / ref列が一意で、standard prose heading集合がasset registryと一致する
- scopeごとのUI操作適用判定と条件付き必須fileのTrigger判定→状態→file集合、completion statusを機械検証できる
- UI操作scopeでUIOP / US / UC / Behavior / AC hierarchyと3分類完全性を機械検証できる
- 09 → Authority Entity、02 → current AC EntityをLLM手組みなしで生成できる
- spec-analysis → question-analysisへUNKNOWN集合を手作業なしで渡せる
- semantic projectionへ過去CHANGELOGを混ぜない
- deterministic projectionでmulti-file contractを評価できる
- legacy vNN / unversioned packageと通常spec-analysis単一成果物を意味を失わずcurrent schemaへ移行できる
- filesystem root外を読まない
- workflow progressと仕様package progressの正本が混ざらない
