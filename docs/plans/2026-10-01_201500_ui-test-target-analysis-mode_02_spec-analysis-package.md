# UIテスト対象分析モード: spec-analysis package

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

責務境界:
2026-10-01_201500_ui-test-target-analysis-mode_01_scope-and-responsibilities.md

LLM / deterministic責務境界:
2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md

package schema / helper I/O / legacy migration:
2026-10-01_201500_ui-test-target-analysis-mode_06_package-schema-and-helper-contracts.md

UI操作の振る舞い分解 / AC traceability:
2026-10-01_201500_ui-test-target-analysis-mode_08_behavior-decomposition-and-acceptance-traceability.md

この文書はspec-analysisへ追加するUIテスト対象分析packageの構造と更新契約を正本とします。

## 1. 変更対象

### 既存変更

- skills/spec-analysis/SKILL.md
- skills/spec-analysis/references/guidance.md

### 新規

- skills/spec-analysis/references/ui-test-target-analysis.md
- skills/spec-analysis/assets/ui-test-target-analysis/README.md
- skills/spec-analysis/assets/ui-test-target-analysis/00_scope-and_context.md
- skills/spec-analysis/assets/ui-test-target-analysis/01_ui_structure_and_navigation.md
- skills/spec-analysis/assets/ui-test-target-analysis/02_behavior_and_business_rules.md
- skills/spec-analysis/assets/ui-test-target-analysis/03_fields_and_validation.md
- skills/spec-analysis/assets/ui-test-target-analysis/04_flows_and_data.md
- skills/spec-analysis/assets/ui-test-target-analysis/05_notifications_and_external_interactions.md
- skills/spec-analysis/assets/ui-test-target-analysis/06_spec_inconsistencies_and_pending.md
- skills/spec-analysis/assets/ui-test-target-analysis/07_current_unknowns.md
- skills/spec-analysis/assets/ui-test-target-analysis/08_repository_implementation_status.md
- skills/spec-analysis/assets/ui-test-target-analysis/09_authority_and_traceability.md
- skills/spec-analysis/assets/ui-test-target-analysis/CHANGELOG.md
- skills/spec-analysis/assets/ui-test-target-analysis/MANIFEST.md
- skills/spec-analysis/scripts/ui_target_package.py

ファイル数を増やすこと自体を目的にしません。標準fileはrequired coreと条件付き必須へ分け、Agentの自由裁量による標準fileの作成可否判断は行いません。

exact heading / exact table header、package schema version、ID形式、Machine Entity bridge、MANIFEST schemaは `_06_package-schema-and-helper-contracts.md` を正本とし、本Planでは意味責務だけを定義します。

### required core payload

- README.md
- 00_scope_and_context.md
- 01_ui_structure_and_navigation.md
- 02_behavior_and_business_rules.md
- 06_spec_inconsistencies_and_pending.md
- 07_current_unknowns.md
- 09_authority_and_traceability.md
- CHANGELOG.md

### required control file

- MANIFEST.md

required package filesは `required core payload + required control file MANIFEST.md` です。MANIFEST自身はpayload / hash対象とREADMEのCurrent payload filesへ含めません。

### 条件付き必須

次のtriggerが1件でも成立した場合は必ず作成します。成立しない場合は作成しません。

| file | 作成trigger |
| --- | --- |
| 03_fields_and_validation.md | 入力・選択・検索・filter・sort・upload等のfield、入力制約、validation、enable/disable条件のいずれかが対象scopeに存在 |
| 04_flows_and_data.md | 複数step / 画面をまたぐflow、state transitionに必要なI/O、import/export**生成処理**、data transformation、非同期process / state flowのいずれかが対象scopeに存在 |
| 05_notifications_and_external_interactions.md | notification、email、browser dialog、user-visibleなexport / download delivery、外部画面遷移、外部destination / serviceとのinteractionのいずれかが対象scopeに存在 |
| 08_repository_implementation_status.md | current packageがrepository implementation evidenceを現在保持・利用している |

`00_scope_and_context.md` のfile applicability表は **file × Scope ID** 単位で持ちます。各rowに `Trigger判定=あり / なし / 未確定`、helperが導出した `required / not-applicable / blocked`、根拠、関連UNKNOWNを記録します。LLMは資料の意味からTrigger判定だけを行い、helperが `あり → required / なし → not-applicable / 未確定 → blocked` を決定論導出します。

情報不足を `not-applicable` にしません。trigger有無を判断できないscopeは関連UNKNOWNを作成し `Trigger判定=未確定` とします。**Triggerはdomainの存在判定であり、存在は確定しているが内容だけ不足する場合は `あり / required` のまま維持します。**

required domainでidentityまで確定できるFIELD / RULE / FLOW / NOTIFY / INTERACTはblocked row + UNKNOWNで保持します。identity自体を確定できずstable rowを作れない場合は07のCurrent UNKNOWNへ `関連Scope ID / Blocking Scope ID / 関連File` を明示します。current UNKNOWNの存在だけでpackage全体をblockedにせず、helperはこれらのmachine-readable blockerとblocked row / UC完全性 / applicabilityから `ready_scope_ids[] / blocked_scope_ids[]` と `completion_status=complete / partial / blocked` を決定論導出します。

08は「このversionでrepositoryを再確認したか」ではなくcurrent packageの依存有無で判定します。前versionの08を引き続き利用するだけの更新ではfileを削除せず、08に保存済みの基準branch / commit / revisionを維持します。current分析からrepository evidenceを明示的に外した場合だけnot-applicableへ変更します。

### 案件固有extension file

標準fileへ入れると責務を混在させる独立domainが存在する場合だけ追加を許可します。単に内容量が多い、好みで分けたい、Markdownを細かくしたいという理由では追加しません。

許可例:
- CSV / export仕様が独立したAuthority / flow / rule集合を持つ
- notification / email template群が05では独立管理が必要な規模・Authorityを持つ
- UI対象機能と別Authorityを持つdomain仕様を同じpackageで追跡する必要がある

extension fileを追加する場合は `00_scope_and_context.md` にfile名・責務・分割理由と、file-levelの `関連Scope ID / 関連仕様項目ID / 関連構造ID / 関連UNKNOWN ID` を記録し、README / MANIFESTへ登録します。extension本文は自由記述のままとし、helperは本文中のIDをparseしません。意味上の関連はLLMが明示列へ渡し、helperが存在参照とimpact候補を決定論検証します。

## 2. SKILL.mdの変更

SKILL.mdには次だけを追加します。

- テスト設計前の対象理解を継続成果物として残す場合、複数資料からUI構造・業務ルール・不明点を追跡可能に整理する場合、または既存UI target packageを更新する場合は `references/ui-test-target-analysis.md` を読む。単なるMarkdown出力要求だけではmodeを選ばない
- 通常の仕様分析では既存assets/output-template.mdを維持する
- mode利用時もSPEC / DECISION / INFERENCE / UNKNOWN、Authority解決、停止条件は既存契約を正本とする
- test requirement / condition / caseへ先回りしない
- packageを更新する場合は既存versionを入力として扱い、現在版の完全packageを生成する

詳細なPAGE分類やfile contractはSKILL.mdへ複製せずreferenceを正本とします。

## 3. ui-test-target-analysis.md

このreferenceに次を定義します。

### 起動条件

- テスト設計前の対象理解
- 複数資料統合
- UI画面 / modal / state構造整理
- 継続更新するMarkdown package
- 既存packageのrevision

### 情報源

既存spec-analysisのAuthority contractを再利用し、mode固有に新しい優先順位を作りません。

案件固有優先順位がある場合はそれを使用します。

### canonical Authority / traceability

mode packageでも既存 `assets/output-template.md` のcanonical契約を維持します。

- `09_authority_and_traceability.md` は既存output-templateの以下を正本として保持する
  - 情報源 / 正本参照一覧
  - 分析項目（UI target modeでは `現在有効か=Yes / No` を固定値として使用する）
  - 現在有効な仕様根拠
  - 後続Skillへの補足
  - Machine Entity（機械証拠）
- 業務ルール / 状態 / フロー / 制約は01〜05へ詳細ビューを持てるが、Authority item IDの正本は09
- 01〜08で新たな仕様判断を追加した場合、必ず09のSPEC / DECISION / INFERENCE / UNKNOWNへ閉じる
- 09のCurrent Effective Authorityを既存 `authority_entities.py` の入力へ変換できる状態を維持し、current ACを `ui_target_package.py` から下流handoff用Machine Entityへ固定projectionできるようにする
- Machine Entityのfingerprintは既存helperで生成し、テンプレートやAgentが手入力しない
- package version / file hashはMachine Entityのcontent fingerprintとは別物

### structural ID / traceability

具体的なstandard prefix、structured table列、`<br>`参照規則は `_06_package-schema-and-helper-contracts.md` を正本とします。`ui-target-v1` では案件固有stable ID prefixを追加しません。

- UI構造・業務ルール・入力項目・フロー等のstructured rowは、`05_llm-deterministic-boundaries.md` のprefix契約に従うstable structural IDを持つ
- 期待挙動・制約・ルールを表すnormative row（UIOP / US / UC / Behavior / AC / RULE / FIELD / FLOW / NOTIFY / INTERACT）は根拠を空にしない。current rowは `関連仕様項目ID` にcurrent SPEC / DECISION / approved ASM / INFを1件以上持ち、Authority不足で確定できないrowはcurrentにせずblocked + `関連UNKNOWN ID` へ閉じる。ACは `_08 / _09` のより厳しいcurrent Authority契約を優先する。PAGE等の純粋な構造rowとRepository実装状況は各table固有契約に従う
- UI構造間の関係は `関連構造ID` で追跡する
- 複数IDの区切りは `<br>` に固定する
- exact ID参照の存在・duplicateはui_target_package.pyで検証する
- semantic identity、reuse / new判断はLLMが行う。UI target mode内でnewと判断した `SRC / SPEC / INF / UNK` とstructural IDの次番号は `ui_target_package.py materialize` 内部allocatorを使用し、Agentが既知ID一覧を組み立てない。DEC / ASMは案件で実際に指定された正本ownerのIDを参照し、UI target packageでは採番しない。ただしpackage内stable reference / CHANGELOG / impactでは追跡対象に含める

### 正規UI分類

- PAGE
- STATE
- VIEW / STEP
- MODAL
- BROWSER-DIALOG
- PANEL / POPOVER / GLOBAL UI
- EXTERNAL
- SHARED PAGE

### package分割

1ファイルへ巨大な仕様を詰め込まず、責務単位で分割します。

固定ファイルは「保存場所」であり、新しいAuthority layerではありません。

各仕様項目のstable IDとsource refを保持し、同じ仕様を複数ファイルへコピーする場合は正本箇所と参照箇所を明確にします。

### 案件固有追加ファイル

次のような大きいdomainがある場合は追加ファイルを許可します。

- CSV / export
- email template
- notification
- billing
- permission matrix
- external API
- mobile-specific behavior

ただし追加ファイルは `10_<domain-slug>.md` 以降の連番 + lowercase kebab-caseで命名し、READMEとMANIFESTへ登録します。同じ責務を複数ファイルへ重複させません。domainの切り分け自体はLLMが意味判断し、helperは命名・重複・file orderだけを検証します。

## 4. package各ファイルの責務

### README.md

- package名
- version
- 対象
- 利用情報源
- authority方針
- ファイル一覧
- 現在の未解消件数
- 次の工程へ進める範囲 / ブロック中範囲

READMEを詳細仕様の複製場所にしません。

### 00_scope_and_context.md

- 対象機能
- 対象ユーザー / ロール
- 対象画面
- 対象情報源
- 正本 / 優先順位
- 対象外
- 用語
- repository実装確認基準がある場合の基準branch / commit
- 分析上の前提
- 分析対象機能scope一覧（SCOPE-xxx、対象機能 / 領域、UI操作判定、Behavior Decomposition、関連UNKNOWN ID、関連仕様項目ID、根拠 / 備考）
- 条件付き必須file applicability（03 / 04 / 05 / 08のrequired / not-applicable / blocked、関連仕様項目ID、根拠 / 備考、関連UNKNOWN ID）
- 案件固有extension fileを使う場合のfile名 / 責務 / 分割理由

### 01_ui_structure_and_navigation.md

- PAGE一覧
- path
- VIEW / STEP
- STATEまたは状態軸
- MODAL
- browser dialog
- panel / external / shared UI
- navigation / entry / exit

same-routeであることがAuthorityまたは確認済み事実から成立する場合はstep / viewを別PAGEへしません。routeが不明な場合は `PATH-TBD` を許可し、操作フローだけからsame-routeを推測しません。PAGE / VIEW分類自体が後続設計へ影響する場合はUNKNOWNとして保持します。

### 02_behavior_and_business_rules.md

UI操作を伴うscopeでは、`_08_behavior-decomposition-and-acceptance-traceability.md` に従い次を必須で持ちます。

- 振る舞い分解適用判定
- UI操作一覧
- User Story一覧
- Use Case一覧
- Behavior一覧
- Use Case振る舞い完全性（正常 / 準正常 / 例外）
- Acceptance Criteria一覧

scopeごとの適用判定は `_08_behavior-decomposition-and-acceptance-traceability.md` を正本とします。UI操作ありはrequired、なしはnot-applicable、UI操作有無自体が未確定ならblocked + UNKNOWNです。

上記に加えて既存の意味責務を保持します。

- lifecycle
- business rule
- status transition
- operation rule
- permission behavior
- success / failure behavior

### 03_fields_and_validation.md

- field
- required / 条件付き
- default
- format
- min / max
- boundary
- trim / normalization
- error
- enable / disable condition
- input method等

テスト技法の適用やテストケース化はしません。

### 04_flows_and_data.md

責務はprocess / data transformation / state flowです。

- user / business flow
- process flow
- data display / data originの仕様上の関係
- state transitionに必要なinput / output
- import / export生成処理、data transformation
- 非同期process

単純なdownload / delivery先だけでは04をrequiredにしません。DB値やAPI responseをUI期待結果としてテストケース化しません。

### 05_notifications_and_external_interactions.md

責務はuser-visible delivery / notification / external destination / interactionです。該当する場合のみ使用します。

- in-app notification
- email
- export / downloadのdelivery / user-visible result
- external documentation
- support / chat
- external destination
- recipient / timing / navigation

単純downloadは05のみ、export生成処理やdata transformationを伴ってその結果をdownloadする場合は04 + 05をrequiredにします。外部serviceとの内部data transformationは04、外部destination / user interactionとしての接続は05で扱い、同じ内容を両fileへ重複記載しません。

03 / 04 / 05がrequiredのscopeでは、LLMは入力資料・Authorityから識別できるin-scope FIELD / FLOW / NOTIFY / INTERACTを母集団として確認し、既知itemを無言で欠落させません。identityは分かるが内容不足ならblocked row + UNKNOWN、identity自体が不明なら07のblocking UNKNOWNへ閉じます。helperの「1 row以上」は構造closureであり、意味上の網羅性を代替しません。RULEについても02のbusiness rule母集団で同じ原則を適用します。

### 06_spec_inconsistencies_and_pending.md

- 資料間矛盾
- typoとして解消したもの
- 正式回答で解消したもの
- 未解消のissue
- source conflict
- pending external specification

解消済み履歴を保持しますが、current unknown一覧の正本にはしません。

### 07_current_unknowns.md

09の分析項目で `分類=UNKNOWN` かつ `現在有効か=Yes` のUNKNOWNだけを人間向けに一覧化します。解消済みUNKは09に `現在有効か=No` と `解消先ID` を残し、07のcurrent一覧から外します。

別節に回答反映済みを残してもよいですが、現在確認対象と解消済みを混ぜません。

各UNKNOWNはstable UNK IDを持ちます。UNKNOWN本文・影響・質問内容に加え、`関連Scope ID / Blocking Scope ID / 関連File` の意味対応をLLMが判断します。helperはscope/fileの存在、subset、duplicateを検証し、07に掲載されるUNK ID集合とREADMEの件数、scope readinessを09 / 07から導出します。

### 08_repository_implementation_status.md

current packageがrepository implementation evidenceを保持・利用している場合に使用します。live UIの観測結果そのものは`test-target-inspection`の責務であり、08へ直接保存しません。必要な場合は同Skillの成果物を補助Source / evidenceとして参照し、spec-analysisへ戻してAuthorityとの差分を整理します。

- `Repository確認基準` table（Repository、Branch / Ref、Commit / Revision、確認時点、関連Scope ID）
- Repository実装状況の各rowが参照するRepository key
- 実装確認できた範囲
- 未実装
- 仕様-実装差分
- 実装だけに存在する分岐
- 実装確認不能理由

前versionからcarry-forwardする場合、`Repository確認基準` をそのまま保持し、再確認していないのにbranch / revision / 確認時点をcurrent repositoryへ更新しません。repositoryを再確認したsemantic updateでだけbaselineと必要なIMPL rowを更新します。current分析からrepository evidenceを明示的に外した場合だけ08を除去します。

repository由来の事実はAuthorityへ昇格しません。ただしsame-route判定等で01のtarget modelへ採用したimplementation-only structureはtest target currentnessの一部なので、そのcanonical rowが変わればAC/TR freshnessの再確認契機にします。

このファイルの内容を仕様本文へ自動昇格させません。

### 09_authority_and_traceability.md

package全体のcanonical仕様モデル。

既存 `assets/output-template.md` の意味契約を再利用し、最低限次を含みます。

- 情報源 / 正本参照一覧
- SPEC / DECISION / INFERENCE / UNKNOWNの分析項目
- Current Effective Authority
- 各構造化ビューで使用するstable item ID
- 後続Skillへの補足
- Machine Entity

01〜08に記載した期待挙動は、09のstable item IDへ追跡できなければなりません。

### CHANGELOG.md

versionごとの差分と、どのUNKNOWN / issue / decisionを反映したかを記録します。

過去versionの全文を複製しません。

### MANIFEST.md

- package version
- current package file一覧
- 各fileのSHA-256

`ui_target_package.py materialize` の内部MANIFEST builderで生成します。MANIFEST自身は自己hash対象にせず、SHA-256はcurrent fileのraw bytesから計算します。Agent / LLMがhashを手入力しません。file orderはREADME → 00〜09 → 10以降のdomain file → CHANGELOGのcanonical順とします。

## 5. version contract

UI target mode packageは継続更新成果物としてversionを持ちます。

default policy:

1. 初回はv00
2. vNNの次は1増分したvNN
3. 同一versionを異なる完成内容で上書きしない。これは更新手順上の契約であり、current package単体のvalidateが過去内容との同一性を証明するものではない
4. README / CHANGELOG / MANIFESTのversionを一致させる
5. 変更後もcurrent versionの全fileを含む完全版を成立させる
6. 過去versionは履歴でありcurrent仕様の参照前提にしない

default policyでは、完成済みpackageのuser-managed / semantic payloadに永続差分を加えて再び完成状態として保存する場合、semantic / presentationを問わず必ず次のvNNへ進めます。LLMが入力するcurrent versionの `変更概要` もuser-managed narrativeとして差分判定に含めます。一方、Package Version / Previous Package Version、CHANGELOGのversion heading・`Stable ID changes`・`影響file`、README generated controls、MANIFESTのようにhelperが他の変更から導出するcontrol差分自体はversion up要否の原因に数えません。user-managed provisional payload + requested `change_summary` が同一のno-opだけversionを維持します。canonical更新経路では `ui_target_package.py materialize` がcontrol生成前に差分を判定し、変更がある場合だけ次versionをREADME / CHANGELOG / MANIFESTへ反映します。version導出は`materialize`内部処理とし、focused確認だけの公開operationは作りません。package schema versionはcontent versionと分離し、current schemaは `ui-target-v1` とします。

`ui-target-v1` のversion policyは上記defaultだけを正本とします。案件固有の別version policyはPR #16では扱わず、必要になった場合はpackage schema / helper contractの変更として別途設計します。「versionを上げるほど重要か」をLLMへ判断させません。

## 6. 作成・更新契約

### 初回作成

1. LLMがsource / Authority、scope、UI構造、file trigger、US / UC / Behavior / AC、UNKNOWN、extension要否等のsemantic判断を行う
2. LLMはstable ID番号や完成Markdown tableを手組みせず、`materialize` 用のsemantic row / prose inputへまとめる。new identityは `identity_action=new / draft_key=<unique>` を使う
3. **materialize前にsemantic quality gate**を行い、source / inference / UI分類 / semantic duplicate、domain itemの無言欠落、file trigger、UNKNOWNの影響scope、same-UNK / new UNK、US / UC / Behavior / ACの意味分解を確認する。NGならpackageを書き換えずsemantic inputを修正する
4. gateを通過したsemantic inputだけを `ui_target_package.py materialize` へ `artifact_mode=create / change_mode=normal / previous_snapshot=null` で渡す。helper自身がSkill-local `assets/ui-test-target-analysis/` からsibling staging packageを初期化し、default policyのv00 / Previous=-、new ID、条件付きfile、extension file、CHANGELOG、Machine Entities、README controls、MANIFESTを生成してpackage単位でcommitする。Agentがassetをtarget rootへ事前copyしない
5. materialize後はdeterministic validateとread-onlyの成果物確認を行う。semantic NGを検出した場合に、その不合格versionをcurrent packageとして残す運用にはしない

### 継続更新

回答や新資料が来た場合:

1. **内容を書き換える前に** `ui_target_package.py inspect` を実行し、返却された `update_snapshot` をこの更新runのprevious stateとしてそのまま保持する。Agent / LLMがsnapshotを編集・再構築しない
2. LLMがAuthority / DECISION / ASM、same-UNK reopen / new UNK、UI構造、US / UC / Behavior / AC、file applicability、extension要否、reuse / new / explicit retire等のsemantic判断を行う。completed Markdown rowやstable ID番号はまだ手書きしない
3. LLMは変更対象を `materialize` のsemantic inputへまとめる。既存identityは `identity_action=reuse / reuse_id=<ID>`、new identityは `identity_action=new / draft_key=<unique>` とし、新規row間参照は `@draft:<draft_key>` を使う。current modelから意図的に除去するidentityだけ `retire_ids[]` に入れる
4. 07のUNKNOWN説明、06の矛盾 / resolved説明、CHANGELOGの `変更概要` 等のnarrativeは `prose_updates[] / change_summary` として渡す。stable ID番号、Markdown escape、table separator、CHANGELOG control row、README control、Machine Entity wrapper、MANIFESTはAgentが組み立てない
5. **current package + source + proposed semantic inputをmaterialize前にsemantic quality gate**へ通す。domain itemの無言欠落、UNKNOWN blocking範囲、semantic duplicate、file trigger、same-UNK / new UNK等がNGならcurrent packageを変更せずinputを修正する
6. gateを通過したinputだけを `ui_target_package.py materialize` へ渡す。qa-workflow経由では既存mutable-operation claimを取得し、standaloneではsingle writerを保証する。helperがsnapshot hashを確認後current packageを再parseし、version、ID、canonical serialization、control、Machine Entity、MANIFESTをstagingへ生成・検証してからpackage単位でcommitする
7. `materialize` が `stale_snapshot / state_transition_required / reference_not_found / write_commit_failed / write_recovery_failed` 等でblockedした場合は成功済みとして扱わない。通常のhandled failureでは元packageを復旧・保持し、復旧不能ならstaging / backupを保全してblockedとする
8. materialize後はdeterministic validate / repository testsとread-only成果物確認を行う。semantic quality gateをcanonical write後の承認手段として使わない
helperが列挙したimpact候補は再確認対象であり、変更必須という意味判断ではありません。LLMが仕様意味を判断します。

同じ回答を複数ファイルへ機械コピーしません。canonical itemと構造化ビューの追跡を使い、必要な意味だけを反映します。

## 7. 案件固有extension fileの分割規則

標準fileへ入れることで責務を混在させる独立domainが存在する場合だけextension fileへ分割します。

分割可否は意味判断なのでLLMが決めます。ただし次をすべて満たします。

- domainが標準fileの責務とは独立している
- 独立したAuthority / rule / flow集合として継続更新する必要がある
- LLMは責務 / 分割理由 / lowercase kebab-case slugとextension本文を `materialize.extension_file_updates[]` へ渡す
- `ui-target-v1` のextension fileは自由記述Markdownだけを持ち、独自structured table / 独自stable ID / custom prefixを定義しない。構造化して追跡する必要があるFIELD / RULE / FLOW等は03〜05または09の既存standard tableへ置き、extension本文からそのstable IDを参照する
- canonical create / updateでは `materialize` がexisting 10+ fileの最大番号+1からrequest順に複数extensionをbatch採番し、実fileと00の `案件固有extension file一覧` を同時生成する。不要になったcurrent extensionはLLMが`extension_file_retirements[]`へ明示し、helperが残存参照を検証したうえで実fileと宣言rowを同時に除去する。Agentが10+番号・宣言rowを計算しない
- extension file番号は`materialize`内部でcurrent 10+ file集合からbatch採番し、番号計算だけの公開operationは作らない
- current UNKNOWNのcanonical正本は09、repository statusの正本は08、canonical Authority / traceabilityの正本は09のまま
- 同じ仕様項目を二重正本にしない

内容量だけを理由にextension fileを追加しません。

## 8. package品質ゲート

- source由来と推論が混在していない
- PAGEがpath単位である
- 同一route内step / viewを別PAGEへしていない
- MODALとbrowser dialogを分離している
- 直交する状態を無理に排他STATEへしていない
- 実装差分を仕様へ上書きしていない
- current unknown / resolved history / same-ID reopenが `現在有効か / 解消先ID` とCHANGELOG event上で矛盾しない
- 解消済みUNKNOWNを再質問していない
- versionが全packageで一致し、default policy利用時の次versionがhelper結果と一致する
- 07のcurrent UNK ID集合とREADME件数が09からhelperで導出したcurrent UNKNOWN集合 / 件数と一致する
- CHANGELOGが今回変更を説明できる
- required core payloadとrequired control file `MANIFEST.md` が存在し、03 / 04 / 05 / 08は00の条件付き必須file applicabilityと実file / MANIFESTのpayload一覧が一致する
- MANIFESTのfile order / SHA-256がhelper再計算結果と一致する
- structured rowのexact stable ID参照がすべて存在し、duplicate structural IDがない
- PAGE→VIEW等、canonical prefixが変わる構造種別変更では旧IDをreuseせず、旧IDのexplicit retire + new IDとする。同じPANEL prefixを共有するPANEL / POPOVER / GLOBAL UI間は、semantic identityが同一とLLMが判断した場合だけreuseできる
- downstreamへ渡すAuthority / AC Machine Entityは1つのcurrent canonical UI target packageから生成し、複数packageのpackage-local ID集合を同一current Entity collectionへ直接mergeしない
- 01〜08の期待挙動が09のstable item IDへ追跡できる
- UI操作scopeのUIOP / US / UC / Behavior / ACが `_08` のclosure contractを満たす
- current ACがAuthorityへ追跡でき、具体値 / 組合せへ先回りしていない
- 09のCurrent Effective Authorityが既存spec-analysisのcanonical schemaを維持している
- 09の「現在有効な仕様根拠」からnormalized Authorityへの固定projectionをhelperが行い、Authority Entityが既存 `authority_entities.py`、current AC Entityが `ui_target_package.py build-machine-evidence` から生成され、spec-analysis normalized_skill_input / expected identity / fingerprintを手入力していない
- `Machine Entities: spec-analysis` blockがexactly one存在し、helper再生成結果と一致する
- resolved UNKNOWNの `解消先ID` がcurrent SPEC / DECISION / 承認済みASMへ閉じ、resolver変更 / same-ID reopen / re-resolveを同じUNK lineageで表現できる
- new ID採番でAgentが既知ID集合を手組みしていない
- test requirement / condition / caseを先回りしていない
- UIで観測不能な内部挙動をUIテスト期待結果として確定していない

## 9. legacy package migration

mode導入前の既存仕様理解package、または通常spec-analysisの単一成果物を後から継続利用する必要が生じた場合は、semantic mappingをLLMが行いcurrent `ui-target-v1` へ移行します。UI操作を含む入力ではUS / UC / Behavior / AC分解もmigration完了条件に含めます。既存SRC / SPEC / INF / UNK / DEC / ASM等は意味的に同一なら維持し、自動migration engineは作りません。通常spec-analysis単一成果物はpackage versionを持たないため `legacy-unversioned → v00` として扱います。version継続、legacy progress fileの扱い、schema versionなしpackageの判定は `_06_package-schema-and-helper-contracts.md` を正本とします。

## 10. file artifact

UI target modeの正規成果物はpackage directory / file集合です。

ZIP化はSkillの意味契約・production helper責務に含めません。利用中Agent / workspaceがarchiveを要求された場合は、そのartifact機能でcurrent package全体をまとめられますが、ZIP作成可否をmode完了条件にはしません。
