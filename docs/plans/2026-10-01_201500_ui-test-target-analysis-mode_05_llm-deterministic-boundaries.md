# UIテスト対象分析モード: LLM / deterministic responsibility boundary

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

この文書は、UIテスト対象分析モードにおけるLLMと決定論的処理の責務境界を正本とします。helperの正確なCLI I/O、table schema、filesystem safety、legacy migrationは `2026-10-01_201500_ui-test-target-analysis-mode_06_package-schema-and-helper-contracts.md`、Acceptance Criterion Machine Entity / shared runtime / test-requirement-design連携は `2026-10-01_201500_ui-test-target-analysis-mode_09_runtime-entity-and-test-requirement-contracts.md` を正本とします。

目的はLLMを置き換えることではありません。LLMが仕様理解・文脈解釈・意味判断へ集中できるように、同じ入力から同じ結果を導出できる定型処理だけをSkill-local helper / validatorへ移します。

## 1. 基本原則

決定論的処理へ移すのは、次の条件をすべて満たす処理です。

1. 入力と出力を構造化できる
2. 同じ入力なら同じ結果になる
3. 製品・業務仕様の意味判断を必要としない
4. scriptの結果が仕様意味を新しく決定しない
5. script化してもLLMが情報源・文脈を解釈する自由度を失わない

上記を満たさない処理はLLMに残します。

「実装しやすいからscript化する」「validatorで判定できそうだから意味判断まで固定する」は行いません。

## 2. 責務マトリクス

| 処理 | 主担当 | 契約 |
| --- | --- | --- |
| SPEC / DECISION / INFERENCE / UNKNOWN分類 | LLM | 情報源・Authority・文脈から判断する |
| 現在有効なAuthority解決 | LLM | 既存spec-analysis契約を使用する |
| PAGE / STATE / VIEW / STEP / MODAL等の意味分類 | LLM | UI意味を判断する。scriptは分類結果の形式だけ検証できる |
| scopeごとのUI操作有無 / file applicability triggerの意味判断 | LLM | 資料の意味から判断する。scriptは宣言後の固定対応とfile存在だけ検証する |
| UI操作抽出 / US / UC / Behavior / ACの意味分解 | LLM | UI操作scopeでは必須工程。資料不足を推測補完しない |
| 正常 / 準正常 / 例外の意味分類 | LLM | scriptは3分類の完全性と許可値だけ検証する |
| AC→TRの意味対応 / TR分割統合 | LLM | ACの単純言い換えではなく検証責務として判断する |
| 既存項目と意味的に同一か | LLM | stable IDをreuseする意味判断はLLMが行う |
| repository差分の意味・重要性 | LLM | 実装事実をAuthorityへ自動昇格しない |
| 案件固有extension fileが必要か | LLM | 標準fileでは責務が混在する独立domainかを判断する。内容量だけを理由に分割しない |
| 質問がどのUNKNOWNに対応するか | LLM | QとUNKの意味対応を判断する |
| 仕様回答がどの項目へ影響するか | LLM | scriptが列挙した参照候補を補助情報として使える |
| ID形式 / duplicate /参照先存在 | deterministic validation | 意味を変えず拒否できる |
| SCOPE applicability / 条件付き必須fileと実fileの一致 | deterministic validation | LLMが意味判定した結果の固定対応を検証する |
| UIOP→UC / US→UC / UC→BH / BH→AC closure | deterministic validation | semantic relationを決めず、LLMが作った参照の完全性だけ検証する |
| UCごとの正常 / 準正常 / 例外3分類 | deterministic validation | 各1行、定義あり/なし/未定義の構造整合を検証する |
| current AC→TR / disposition closure | test-requirement deterministic runtime | ACを無言で落とさない |
| version形式 / package内version一致 | deterministic helper / validation | default version policy利用時は次versionも導出できる |
| required core / 条件付き必須file set | deterministic validation | trigger該当性はLLM、required / not-applicable / blockedと実file / MANIFEST一致はscript |
| MANIFEST file list / SHA-256 | deterministic helper | package内容から導出し、LLMに計算させない |
| current UNKNOWN ID集合 / 件数 | deterministic helper | canonical分析項目から導出する。UNKNOWN本文はLLMが作る |
| cross-file stable ID参照切れ | deterministic validation | exact ID参照だけを検証する |
| changed stable IDの参照file候補 | deterministic helper | exact参照から候補を列挙する。意味上の修正要否はLLM |
| Authority Machine Entity / fingerprint | 既存deterministic helper | authority_entities.pyを正本とする |
| Acceptance Criterion Machine Entity / spec-analysis normalized input | deterministic helper | ui_target_package.pyがcurrent AC + parent chainから固定projectionする |
| semantic eval用package projection | deterministic helper | package内容を要約・変更せず連結する |
| semanticな重複・矛盾・不足 | LLM / semantic eval |文字列一致だけで自動統合しない |

## 3. spec-analysis Skill-local helper

新規:

- skills/spec-analysis/scripts/ui_target_package.py

本helperはruntime dispatchではなく、既存authority_entities.pyと同じくSkill-local production helperです。Python標準ライブラリだけを使用し、spec-analysis package単体コピーで実行できるようにします。

### 3.1 helperが担当するoperation

次を提供します。operation名は実装時にこの名称で固定し、このPlanで未定義のoperationは追加しません。

#### inspect

package rootを読み、次をJSONで返します。

- package version
- current file list
- required coreのmissing
- file applicability状態
- extension domain file list
- canonical analysis item ID集合
- current UNKNOWN ID集合
- current UNKNOWN件数
- cross-file stable ID reference index
- unresolved structural issues

意味評価は返しません。

#### validate

次を決定論的に検証します。

- required core fileの存在
- package root外pathを参照していない
- package内version表記の一致
- canonical分析項目IDの形式・重複
- UI / rule / flow等、modeで定義するstructural IDの形式・重複
- exact stable ID参照先の存在
- 07_current_unknownsに含まれるUNK ID集合が09のcurrent UNKNOWN集合と一致
- READMEのcurrent UNKNOWN件数が09から導出した件数と一致
- MANIFESTのfile set / order / SHA-256がcurrent packageと一致
- READMEのCurrent payload filesがMANIFESTのpayload file listと一致
- CHANGELOGの最新version見出しがpackage versionと一致
- `Machine Entities: spec-analysis` blockがexactly one存在し、Authority + current ACのhelper再生成結果と一致すること
- resolved UNKNOWNの`解消先ID`が存在するcurrent SPEC / DECISION / 承認済みASMを参照すること

意味的な正しさ、Authority優先順位、PAGEかVIEWか等は検証しません。

#### next-version

default version policyを使うcurrent `ui-target-v1` packageでは、Agentがcurrent versionを読み取ってhelperへ渡しません。helperが `package_root` からPackage Versionを取得し、`previous_version / next_version` を返します。

mode導入前のlegacy packageをcurrent schemaへ移行する場合だけ、LLMがsemantic mappingで確定した明示versionをlegacy migration用inputとして渡せます。案件固有version policyが明示されている場合はnext-versionを使用せず、そのversion文字列がpackage内で一致することだけvalidateします。

#### next-id

LLMがsemantic identityを判断して `new` と決めた後だけ使用します。Agentから既知ID一覧を受け取らず、helperがpackage rootのcurrent structured rowとCHANGELOG各versionのexact `Stable ID changes` tableから既知IDを収集し、同prefixの既知最大番号+1を返します。

- reuse / newの意味判断は行わない
- Agent / LLMに`known_ids[]`を手組みさせない
- CHANGELOG本文のproseからIDを推測せず、exact tableだけを履歴として読む
- 現在存在しない過去IDもCHANGELOGのstable ID履歴から既知IDとして扱い、別entityへ再割当てしない
- UI target mode内でnewと判断した `SRC / SPEC / INF / UNK` とstructural IDの番号決定に使用する
- `DEC / ASM` は案件で実際に指定された決定事項 / 仮定の正本がownerであり、本helperで新規採番しない。Project Contextがownerの場合だけ `project_context_ids.py` を使う
- `next-id` で得たIDは、同じprefixの次の `next-id` 呼び出し前に対象structured rowへ反映する
- helper返却の `stable_id_change` をcurrent versionの `Stable ID changes` tableへ記録し、validate前に履歴を閉じる
- prefixはmodeで宣言済みのものだけ許可する

#### render-readme-controls

READMEの `Package metadata` と `Current payload files` をcanonical Markdownとして生成します。

- Package Schema Version / Package Version / Previous Package VersionはREADME current metadataを使う
- Current UNKNOWN Countは09のcurrent UNKNOWN集合から導出する
- Current payload filesはcurrent file setと00 applicability / extension宣言からcanonical orderで導出する
- Agent / LLMがmetadata table、UNKNOWN件数、payload file順、種別を再構築しない
- MANIFEST hash計算より前にREADME controlsへ反映する

#### next-domain-file

LLMが「標準fileへ混在させるべきでない独立domainが必要」と判断し、slugを決めた後だけ使用します。helperがexisting `10+` domain file番号の最大値+1を決め、canonical relative pathを返します。

- domain fileが必要かは判断しない
- slugの意味は判断しない
- Agent / LLMに次の連番を計算させない
- 返却pathを00へ登録して実fileを作成してから次の採番を行い、未materializeの番号をAgent側だけで予約しない
- 既存最大番号が999なら自動拡張せず `id_space_exhausted`

#### build-manifest

README controls反映後のcurrent package fileからMANIFEST bodyを生成します。

- MANIFEST自身は自己hash対象にしない
- SHA-256はfileのraw bytesから計算する
- file orderはmodeのcanonical orderに従う
- 条件付き必須fileは00のapplicabilityと一致するものだけ含める
- extension fileは00へ宣言済みのものだけ含める
- Agent / LLMがfile順・hashを再構築しない

#### inspect / impact

通常更新では、内容編集前の `inspect` が `update_snapshot` を生成します。snapshotはtracked stable IDのowner row fingerprint、UNKNOWN state、previous exact reference、payload file hashを保持し、Agent / LLMは編集・再構築しません。

semantic identity、same-UNK reopen / new UNK等をLLMが判断してowner structured rowへ反映した後、`impact` がprevious snapshotとcurrent stateを比較して次を決定論生成します。

- `added / changed / resolved / retired`
- changed stable ID集合
- `Stable ID changes` canonical Markdown
- previous/current owner + exact referenceから導出した再確認候補file / row
- `影響file` canonical Markdown

LLMがCHANGELOG lifecycle eventや影響file一覧を手入力しません。更新途中でstable ID owner rowを削除しても、`next-id` は同じprevious snapshotを使用済みID集合へ含めるため、そのrevision内で過去IDを再利用しません。

legacy migrationではsemantic identity mappingだけをLLMが行い、retained ID / 明示確認できるterminal eventを `impact(change_mode=legacy-migration)` へ渡します。helperが `migrated / added / resolved / retired` のtableを生成し、legacy proseからidentityを推測しません。

この結果は「本文修正が必要」という意味判断ではありません。LLMが再確認対象を漏らさないための候補集合です。

#### build-machine-evidence

09のCurrent Effective Authorityと02のcurrent AC + parent US / UC / Behavior chainを固定projectionします。

1. Authority rowを既存 `authority_entities.py` builderへ渡す
2. current ACだけを `acceptance_criterion` Machine Entityへ変換する
3. AC contentへ親US / UC / Behavior / Scope / Authority / structure refsを固定projectionする
4. Authority + AC Entityを1つの `Machine Entities: spec-analysis` blockへcanonical順で統合する
5. 既存shared `render_machine_entities()` を使ってheading + JSON fenceを含むcanonical Markdown sectionまで生成する
6. qa-workflow / coverage-analysisへ渡すcanonical `normalized_skill_input` と `expected_entity_identities` を同じsourceから生成する

US / UC / Behaviorをglobal Machine Entity typeへしません。何をAuthorityとするか、UI操作やUS / UC / Behavior / ACをどう意味分解するかはLLM判断です。wrapper / content / dependency / fingerprint / normalized machine input / expected identity / Markdown section serializationはhelperが生成します。
#### project-eval

projection modeを `semantic / deterministic` に固定します。

semantic:

- README / 00〜09 / 10+ current domain files
- CHANGELOG / MANIFESTは除外

deterministic:

- 全payload file
- MANIFESTを最後にcontrol fileとして追加

共通して各fileの前へ `<!-- FILE: <relative-path> -->` を付け、内容は要約・正規化・書換えしません。package root外path、symlink、duplicate / missing fileを拒否します。

projectionは評価transportです。raw file bytesのSHA-256再計算はproduction `validate` / repository unit testの責務とし、projected deterministic evalではMANIFEST schema、file集合・順序、SHA-256文字列形式、stable ref等を評価します。projectionからraw bytesを復元するframingは追加しません。

semantic / deterministic runnerのdirectory対応は追加せず、この固定projectionを1-file inputとして渡します。

### 3.2 helperが担当しないこと

- 仕様文章の生成
- UI操作母集団の意味抽出
- US / UC / Behavior / ACの意味分解
- 正常 / 準正常 / 例外の意味分類
- ACとTRの意味的対応 / TR分割統合
- SPEC / DECISION / INFERENCE / UNKNOWN分類
- PAGE / VIEW等の意味分類
- scopeのUI操作有無 / 条件付き必須file trigger該当性の意味判断
- 案件固有extension fileが必要かの判断
- semantic duplicateの統合
- Authority競合解消
- repository差分の意味判断
- 質問文生成
- stable IDをreuseする意味判断

## 4. structural ID契約

UI target packageでは、人間向け構造化ビューのentityをstable IDで参照できるようにします。

UI target modeで `next-id` が番号決定を担当するprefix:

canonical spec-analysis item:
- SRC-xxx
- SPEC-xxx
- INF-xxx
- UNK-xxx

structural item:
- SCOPE-xxx
- PAGE-xxx
- STATE-xxx
- VIEW-xxx
- STEP-xxx
- MODAL-xxx
- BDLG-xxx
- PANEL-xxx
- EXT-xxx
- SHARED-xxx
- FIELD-xxx
- RULE-xxx
- FLOW-xxx
- NOTIFY-xxx
- INTERACT-xxx
- ISSUE-xxx
- IMPL-xxx
- UIOP-xxx
- US-xxx
- UC-xxx
- BH-xxx
- AC-xxx

案件固有entity typeが必要な場合はLLMが追加のprefixを勝手に作らず、packageの `00_scope_and_context.md` にある `案件固有構造ID` tableへprefixと意味を宣言してから使用します。helperは宣言済みprefixだけを許可します。

IDが意味的に同一か、新IDにすべきかはLLM判断です。helperはIDを自動的に別entityへ再割当てしません。

## 5. canonical stable reference contract

01〜08のstructured tableで期待挙動・UI構造・ルール・不明点を表すrowは、少なくとも1件のcanonical itemへ根拠付けできる場合 `関連仕様項目ID` を必須とします。UI構造間の親子・遷移・関連を表すrowは、関係先が存在する場合 `関連構造ID` を持ちます。pure narrative / heading /説明専用rowには参照列を強制しません。

- `関連仕様項目ID`: SPEC / DEC / INF / UNK等、09_authority_and_traceability.mdのcanonical item
- `関連構造ID`: PAGE / STATE / VIEW / MODAL / FIELD / RULE / FLOW等

複数参照の区切りは `<br>` に固定します。

helperはexact ID参照の存在だけを検証します。文章中に偶然現れたIDらしき文字列を参照として抽出しません。

pure narrativeや説明用sectionへ無理に参照列を追加しません。参照整合を機械判定するtable / structured rowだけを対象にします。

## 6. current UNKNOWNの扱い

09_authority_and_traceability.mdの分析項目では、UI target mode利用時の `現在有効か` を `Yes / No` に固定します。分類=UNKNOWNかつ `現在有効か=Yes` の項目をcanonical current UNKNOWN集合とします。

07_current_unknowns.mdはその集合の人間向けビューです。

- UNKNOWN本文・影響・質問内容はLLMが記述する
- 07に載せるUNK ID集合と件数はhelperで検証する
- READMEの件数は同じ集合から検証する
- UNKNOWNが解消した場合、元のUNK rowは削除・再分類せず `現在有効か=No` とし、`解消先ID` でcurrent SPEC / DECISION / 承認済みASMのstable IDへlineageを残す
- `解消先ID`はLLMが意味上の解消先を決め、helperが形式・存在・current Authority種別だけを検証する
- 後続更新で解消先Authorityが変わっても同じ論点が解消済みなら、同じUNK rowの `解消先ID` を新しいcurrent Authorityへ更新する
- 解消根拠がなくなった場合、同じ論点なら同じUNKを `現在有効か=Yes / 解消先ID=空` へ戻す。別論点なら旧UNKはresolved historyとして維持しnew UNKを作る
- 同一論点 / 別論点の判断はLLM、`Yes / No` と `解消先ID` の組合せ・CHANGELOG event整合はhelperが担当する
- 新しい確定内容は分類に合う新しいstable IDで記録する。`UNK-xxx` をDECISIONへ分類変更しない
- resolved historyの説明はLLMがCHANGELOG / 06へ記載できる

scriptがUNKNOWNを意味的に解消しません。

## 7. version / MANIFEST

UI target mode packageは継続更新成果物のためversionを持ちます。

default policy:

- 初回: v00
- 次回: v01, v02 ... の1増分
- 同じversionを別内容で完成版として上書きしない

案件に別version policyがある場合はそちらを優先します。

MANIFESTはcurrent package fileのfile listとSHA-256を持ちます。

- MANIFEST自身はhash対象外
- README / 00〜09 / 案件固有domain / CHANGELOGのうち存在するfileを列挙
- file orderはmode referenceで固定する
- SHA-256はhelperが計算する
- Agentがhash値を手入力しない

version変更の要否をpresentationだけの差分まで機械判定しません。案件で「material update」の定義が必要な場合はLLM / project policyが判断します。default policyでmaterial updateと判断した場合は、内容を書き換える前に `next-version` を実行し、返却された `previous_version / next_version` をREADME / CHANGELOGへ反映してから更新します。

「同じversionを別内容で完成版として上書きしない」は更新手順上の契約です。current packageだけを見るvalidatorは過去の同version内容とのbyte比較を行わず、current / previous version metadataの形式・連続性・package内一致を検証します。

## 8. question-analysis / Project ContextのSkill-local helper

新規:

- skills/question-analysis/scripts/unknown_links.py
- skills/question-analysis/scripts/question_ids.py
- skills/qa-workflow/scripts/project_context_ids.py

いずれもPython標準ライブラリだけを使い、各Skill package単体で実行可能にします。

`unknown_links.py` の担当:

- 関連UNKNOWN IDの形式検証
- current known UNKNOWN集合に対する存在検証
- Q IDごとのduplicate UNKNOWN参照検出
- resolved-only UNKNOWNをcurrent questionへ関連付けた場合の検出

`question_ids.py` の担当:

- current `不明点 / 質問一覧` とmachine-readableな `質問ID履歴` の `Q-xxx` 形式・duplicate検証
- LLMがnew questionと決めた後、current + historyの使用済みID unionから次番号を決定
- previous artifactとcandidate current artifactから、過去に一度でも使ったQ IDを落とさないcanonical `質問ID履歴` tableを生成

`project_context_ids.py` の担当:

- Project Context Section 12 / 13が実際の正本ownerである場合だけ、existing `DEC-xxx / ASM-xxx` の形式・duplicateを検証
- question-analysis / stakeholder判断でnew DECISION / approved ASMと決まった後の次番号決定
- 別ownerが明示されている場合は処理せず、そのownerのIDをProject Contextへ複製・再採番しない

担当しない:

- QとUNKが意味的に同一かの判断
- Q / DEC / ASMのsemantic identity reuse / new判断
- resolved Qをcurrent質問一覧へ残すかどうかの意味判断
- 質問文生成
- 回答のSPEC / DECISION / ASM分類
- DECISIONの内容・関係・影響範囲
- ASM承認可否
- Project Context以外の正本schemaの解釈・採番
- 新しいUNKを作るべきかの判断

別ownerが明示されていてowner側IDが未確定の場合、LLMが番号を手計算せず正本登録をblockedとして扱います。任意schema向けgeneric allocatorは追加しません。

各helperのexact operation / input / output / failure contractは `_06_package-schema-and-helper-contracts.md` を正本とします。eval validator / repository testはproduction helperからexpectedを逆算しません。

## 9. route / PAGE / VIEWの曖昧さ

same-routeであることがAuthorityまたは確認済み実装事実から成立する場合だけVIEW / STEPへ統合します。

routeが不明な場合:

- pathは `PATH-TBD` として保持できる
- 別画面として資料上明示されているものを、推測でsame-route VIEWへ畳まない
- route不明だけを理由に別PAGEと断定もしない
- PAGE / VIEW分類自体がテスト設計へ影響するならUNKNOWNとして残す

この判断はLLMが行い、helperは `PATH-TBD` を許可値として扱うだけです。

## 10. repository調査の境界

repository sourceを読むこと自体はspec-analysisの補助入力収集です。

e2e-test-inspectionへroutingするのは、E2E実装・Playwright等の既存テスト資産の実装詳細を分析する責務が必要な場合だけです。

単に製品repositoryのUI / route / validation実装を確認したいだけでe2e-test-inspectionへroutingしません。

## 11. 対象外

今回の目的外として実装しません。

- 仕様意味を自動判定するrule engine
- semantic duplicateを自動mergeするscript
- PAGE / VIEW分類器
- User Story / Use Case / Behavior / Acceptance Criteria自動意味分類器
- US / UC / Behaviorのglobal Machine Entity化
- 汎用Markdown AST framework
- 任意文書merge engine
- ZIP専用runtime
- 特定AI製品向けintegration

これらを「初回だから後回し」にするのではなく、UIテスト対象分析modeの目的に不要、またはLLMの意味判断を不必要に制約するため対象外とします。
