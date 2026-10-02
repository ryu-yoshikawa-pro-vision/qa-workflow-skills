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

### required core

- README.md
- 00_scope_and_context.md
- 01_ui_structure_and_navigation.md
- 02_behavior_and_business_rules.md
- 06_spec_inconsistencies_and_pending.md
- 07_current_unknowns.md
- 09_authority_and_traceability.md
- CHANGELOG.md
- MANIFEST.md

### 条件付き必須

次のtriggerが1件でも成立した場合は必ず作成します。成立しない場合は作成しません。

| file | 作成trigger |
| --- | --- |
| 03_fields_and_validation.md | 入力・選択・検索・filter・sort・upload等のfield、入力制約、validation、enable/disable条件のいずれかが対象scopeに存在 |
| 04_flows_and_data.md | 複数step / 画面をまたぐflow、state transitionに必要なI/O、import/export、data transformation、非同期処理flowのいずれかが対象scopeに存在 |
| 05_notifications_and_external_interactions.md | notification、email、browser dialog、外部画面遷移、外部service連携、外部interactionのいずれかが対象scopeに存在 |
| 08_repository_implementation_status.md | current package versionの分析でrepository / product implementation evidenceを実際に確認・利用した |

`00_scope_and_context.md` のfile applicability表に4fileすべての `required / not-applicable / blocked` と根拠を記録します。LLMは資料の意味からtrigger該当性を判断し、helperは宣言と実file / MANIFESTの一致を決定論検証します。

情報不足を `not-applicable` にしません。trigger有無を判断できない場合は関連UNKNOWNを作成し、そのfile applicabilityをblockedとしてpackage completionを止めます。

### 案件固有extension file

標準fileへ入れると責務を混在させる独立domainが存在する場合だけ追加を許可します。単に内容量が多い、好みで分けたい、Markdownを細かくしたいという理由では追加しません。

許可例:
- CSV / export仕様が独立したAuthority / flow / rule集合を持つ
- notification / email template群が05では独立管理が必要な規模・Authorityを持つ
- UI対象機能と別Authorityを持つdomain仕様を同じpackageで追跡する必要がある

extension fileを追加する場合は `00_scope_and_context.md` にfile名・責務・分割理由を記録し、README / MANIFESTへ登録します。

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

具体的なstandard prefix、案件固有prefix宣言場所、structured table列、`<br>`参照規則は `_06_package-schema-and-helper-contracts.md` を正本とします。

- UI構造・業務ルール・入力項目・フロー等のstructured rowは、`05_llm-deterministic-boundaries.md` のprefix契約に従うstable structural IDを持つ
- 期待挙動・仕様判断を表すnormative rowは、必要に応じ `関連仕様項目ID` で09のSPEC / DEC / INF / UNKへ追跡する
- UI構造間の関係は `関連構造ID` で追跡する
- 複数IDの区切りは `<br>` に固定する
- exact ID参照の存在・duplicateはui_target_package.pyで検証する
- semantic identity、reuse / new判断はLLMが行う。UI target mode内でnewと判断した `SRC / SPEC / INF / UNK` とstructural IDの次番号は `ui_target_package.py next-id` を使用し、Agentが既知ID一覧を組み立てない。DEC / ASMはquestion-analysis / project側の正本IDを参照する

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
- generated / updated date
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
- 分析対象機能scope一覧（SCOPE-xxx、対象機能 / 領域、UI操作判定、Behavior Decomposition、関連UNKNOWN ID、根拠）
- 条件付き必須file applicability（03 / 04 / 05 / 08のrequired / not-applicable / blockedと根拠）
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

- user / business flow
- process flow
- data display / data originの仕様上の関係
- state transitionに必要なinput / output
- external interactionの入口

DB値やAPI responseをUI期待結果としてテストケース化しません。

### 05_notifications_and_external_interactions.md

該当する場合のみ使用します。

- in-app notification
- email
- export / download
- external documentation
- support / chat
- external destination
- recipient / timing / navigation

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

各UNKNOWNはstable UNK IDを持ちます。UNKNOWN本文・影響・質問内容はLLMが記述し、07に掲載されるUNK ID集合とREADMEの件数は `ui_target_package.py` が09から導出・検証します。

### 08_repository_implementation_status.md

repository確認を行った場合のみ使用します。

- 基準branch / commit
- 実装確認できた範囲
- 未実装
- 仕様-実装差分
- 実装だけに存在する分岐
- 実装確認不能理由

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

`ui_target_package.py build-manifest` で生成します。MANIFEST自身は自己hash対象にせず、SHA-256はcurrent fileのraw bytesから計算します。Agent / LLMがhashを手入力しません。file orderはREADME → 00〜09 → 10以降のdomain file → CHANGELOGのcanonical順とします。

## 5. version contract

UI target mode packageは継続更新成果物としてversionを持ちます。

default policy:

1. 初回はv00
2. vNNの次は1増分したvNN
3. 同一versionを異なる完成内容で上書きしない。これは更新手順上の契約であり、current package単体のvalidateが過去内容との同一性を証明するものではない
4. README / CHANGELOG / MANIFESTのversionを一致させる
5. 変更後もcurrent versionの全fileを含む完全版を成立させる
6. 過去versionは履歴でありcurrent仕様の参照前提にしない

default policyでは `ui_target_package.py next-version` が次versionを導出します。package schema versionはcontent versionと分離し、current schemaは `ui-target-v1` とします。

ユーザー / projectが別version policyを明示した場合はそちらを優先し、helperは指定versionのpackage内一致だけを検証します。何をmaterial updateとしてversion upするかの意味判断はproject policyまたはLLMに残し、presentationだけの差分までhelperが自動判定しません。

## 6. 更新契約

回答や新資料が来た場合:

1. LLMが変更されたAuthority / DECISION / ASMを解決し、project policyに従ってmaterial updateかを判断する
2. default version policyでversion upする場合は、**内容を書き換える前に**既存current packageへ `ui_target_package.py next-version` を `package_root` だけで実行する。返却された `previous_version / next_version` を使い、READMEの `Previous Package Version / Package Version` とCHANGELOGのcurrent version headingを更新する。Agentがcurrent versionを手で転記しない
3. LLMが影響するcanonical stable item / UNKを更新する。semantic identityがnewの場合だけ `next-id` を使う。UI target modeがownerの `SRC / SPEC / INF / UNK` とstructural IDはhelperで採番し、DEC / ASMはproject側正本の既存IDを参照する。返却IDを対象structured rowへ反映してから同prefixの次の採番へ進み、返却された `stable_id_change` はcurrent versionのCHANGELOGへ記録する。UNKNOWN解消時は元UNKを `現在有効か=No` にし、確定内容を分類に合うnew / reuse stable IDへ接続して `解消先ID` を保持する
4. 09_authority_and_traceability.mdのcanonical modelを更新する
5. `ui_target_package.py impact` を `package_root` だけで実行し、current versionの `Stable ID changes` からhelperが導出したchanged IDのexact参照先を再確認候補として列挙する
6. LLMが候補fileを確認し、意味上変更が必要な01〜08 / domain fileだけを更新する
7. LLMが07のUNKNOWN本文、06の矛盾 / resolved説明、CHANGELOGの変更概要・stable ID change・影響fileを更新する
8. repository確認を実施した場合だけ08を更新する
9. helperでcurrent UNKNOWN ID集合 / 件数を取得し、07 / READMEとの整合を確認する
10. `ui_target_package.py build-machine-evidence` で09のAuthority Entityとcurrent AC Entity、spec-analysis canonical `normalized_skill_input` を決定論生成する
11. helperでMANIFEST / SHA-256を生成する
12. helperのvalidateを実行し、形式・参照・件数・version・CHANGELOG・file set・hashの決定論違反を解消する
13. semantic quality gateでsource / inference / UI分類 / 意味重複等を最終確認する

helperが列挙したimpact候補は再確認対象であり、変更必須という意味判断ではありません。LLMが仕様意味を判断します。

同じ回答を複数ファイルへ機械コピーしません。canonical itemと構造化ビューの追跡を使い、必要な意味だけを反映します。

## 7. 案件固有extension fileの分割規則

標準fileへ入れることで責務を混在させる独立domainが存在する場合だけextension fileへ分割します。

分割可否は意味判断なのでLLMが決めます。ただし次をすべて満たします。

- domainが標準fileの責務とは独立している
- 独立したAuthority / rule / flow集合として継続更新する必要がある
- 00にfile名 / 責務 / 分割理由を記録する
- README / MANIFESTへ登録する
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
- current unknownとresolved historyが矛盾しない
- 解消済みUNKNOWNを再質問していない
- versionが全packageで一致し、default policy利用時の次versionがhelper結果と一致する
- 07のcurrent UNK ID集合とREADME件数が09からhelperで導出したcurrent UNKNOWN集合 / 件数と一致する
- CHANGELOGが今回変更を説明できる
- required coreが全て存在し、03 / 04 / 05 / 08は00の条件付き必須file applicabilityと実file / MANIFESTが一致する
- MANIFESTのfile order / SHA-256がhelper再計算結果と一致する
- structured rowのexact stable ID参照がすべて存在し、duplicate structural IDがない
- 01〜08の期待挙動が09のstable item IDへ追跡できる
- UI操作scopeのUIOP / US / UC / Behavior / ACが `_08` のclosure contractを満たす
- current ACがAuthorityへ追跡でき、具体値 / 組合せへ先回りしていない
- 09のCurrent Effective Authorityが既存spec-analysisのcanonical schemaを維持している
- 09の「現在有効な仕様根拠」からnormalized Authorityへの固定projectionをhelperが行い、Authority Entityが既存 `authority_entities.py`、current AC Entityが `ui_target_package.py build-machine-evidence` から生成され、spec-analysis normalized_skill_input / expected identity / fingerprintを手入力していない
- `Machine Entities: spec-analysis` blockがexactly one存在し、helper再生成結果と一致する
- resolved UNKNOWNの `解消先ID` がcurrent SPEC / DECISION / 承認済みASMへ閉じている
- new ID採番でAgentが既知ID集合を手組みしていない
- test requirement / condition / caseを先回りしていない
- UIで観測不能な内部挙動をUIテスト期待結果として確定していない

## 9. legacy package migration

mode導入前の既存仕様理解packageを更新する場合、semantic mappingはLLMが行い、current `ui-target-v1` へ変換後にhelperで検証します。UI操作を含むlegacy packageではUS / UC / Behavior / AC分解もmigration完了条件に含めます。既存stable IDは意味的に同一なら維持し、自動migration engineは作りません。version継続、legacy progress fileの扱い、schema versionなしpackageの判定は `_06_package-schema-and-helper-contracts.md` を正本とします。

## 10. file artifact

UI target modeの正規成果物はpackage directory / file集合です。

ZIP化はSkillの意味契約・production helper責務に含めません。利用中Agent / workspaceがarchiveを要求された場合は、そのartifact機能でcurrent package全体をまとめられますが、ZIP作成可否をmode完了条件にはしません。
