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

また、決定論的であっても独立したproduction実行用途を持たない数行のdefault補完・値転送・別script呼び出しだけのwrapperは追加しません。既存production scriptの責務内で完結する処理はそのscriptへ統合します。storage / external API / connector / process起動 / timeout / lock / orchestration等の導入先project固有処理はSkill repoへ抽象wrapperを置かず、導入先project / harnessが担当します。production CLI operationはAgent / workflowが単独で呼ぶ現在用途があるものだけ公開し、unit testのためだけのfocused operationは内部関数として検証します。

## 2. 責務マトリクス

| 処理 | 主担当 | 契約 |
| --- | --- | --- |
| SPEC / DECISION / INFERENCE / UNKNOWN分類 | LLM | 情報源・Authority・文脈から判断する |
| 現在有効なAuthority解決 | LLM | 既存spec-analysis契約を使用する |
| PAGE / STATE / VIEW / STEP / MODAL等の意味分類 | LLM | UI意味を判断する。scriptは分類結果の形式だけ検証できる |
| scopeごとのUI操作有無 / file applicability triggerの意味判断 | LLM | 資料の意味から `あり / なし / 未確定` を判断する。Triggerはdomainの存在判定であり、内容不足だけで `未確定` へ戻さない。scriptはfile × Scope IDごとに `required / not-applicable / blocked` を導出する |
| UI操作抽出 / US / UC / Behavior / ACの意味分解 | LLM | UI操作scopeでは必須工程。資料不足を推測補完しない。semantic identity自体が未確定でrowを作れない場合はblocking UNKNOWNをScopeへ明示する |
| 正常 / 準正常 / 例外の意味分類 | LLM | scriptは3分類の完全性と許可値だけ検証する |
| AC→TRの意味対応 / TR分割統合 | LLM | ACの単純言い換えではなく検証責務として判断する |
| 既存項目と意味的に同一か | LLM | stable IDをreuseする意味判断はLLMが行う |
| repository差分の意味・重要性 | LLM | 実装事実をAuthorityへ自動昇格しない。target modelへ採用したimplementation-only structureが変わった場合はfreshness再確認対象になる |
| 案件固有extension fileが必要か | LLM | 標準fileでは責務が混在する独立domainかを判断する。内容量だけを理由に分割しない |
| 質問がどのUNKNOWNに対応するか | LLM | QとUNKの意味対応を判断する |
| 仕様回答がどの項目へ影響するか | LLM | scriptが列挙した参照候補を補助情報として使える |
| ID形式 / duplicate /参照先存在 | deterministic validation | 意味を変えず拒否できる |
| new stable ID番号 | deterministic helper | semantic identity確定後に採番する。既存SRC / SPEC / INF / UNK等は3桁契約を維持し、新設UI target structural IDは最低3桁・上限なしで採番する。extension独自prefixは追加しない |
| explicit retire intent | LLM | row消失を永久廃止と自動解釈しない。package-owned identityをcurrent modelから意図的に除去する場合だけretire判断する。DEC / ASMはpackage外ownerなのでpackage側terminal retire対象にしない |
| Markdown table / known section / standard file materialization | deterministic helper | semantic row / prose確定後のID注入、escape、sort、serialization、file同期をui-target-v1専用materializeで行う |
| SCOPE applicability / 条件付き必須fileと実fileの一致 | deterministic helper / validation | file × Scope IDの `あり / なし / 未確定` からfile状態を固定導出する。content completenessは別に、blocked domain rowまたは07のBlocking Scope ID + 関連Fileでclosureを検証する |
| UIOP→UC / US→UC / UC→BH / BH→AC closure | deterministic validation | semantic relationを決めず、LLMが作った参照の完全性だけ検証する。UIOP.Scopeと対応UCからderivedしたScopeの一致も検証する |
| UCごとの正常 / 準正常 / 例外3分類 | deterministic validation | 各1行、定義あり/なし/未定義の構造整合を検証する |
| current AC→TR / disposition closure | test-requirement deterministic runtime | ACを無言で落とさない |
| version形式 / package内version一致 | deterministic helper / validation | default policyでは完成packageへ永続差分を保存するたびsemantic / presentationを問わず次versionへ進める。no-opだけ維持する |
| required core / 条件付き必須file set | deterministic helper / validation | trigger該当性だけLLM。状態・create/update時のfile集合・MANIFEST・completion statusはscript |
| MANIFEST file list / SHA-256 | deterministic helper | package内容から導出し、LLMに計算させない |
| current UNKNOWN ID集合 / 件数 | deterministic helper | canonical分析項目から導出する。UNKNOWN本文、関連Scope、Blocking Scope、関連FileはLLM / question-analysisが判断し、helperがexact参照とscope readinessを集計する。UNKNOWNの存在だけではcompletionをblockedにしない |
| cross-file stable ID参照切れ | deterministic validation | exact ID参照だけを検証する。extension本文はparseせず、00のextension宣言rowにLLMが明示したfile-level refだけを検証する |
| changed stable IDの参照file候補 | deterministic helper | exact参照から候補を列挙する。意味上の修正要否はLLM |
| Authority Machine Entity / fingerprint | 既存deterministic helper | authority_entities.pyを正本とする |
| Acceptance Criterion Machine Entity / spec-analysis normalized input | deterministic helper | ui_target_package.pyがcurrent AC + parent chain + linked UIOP / scope / direct package item / structure ancestor / linked INFから固定projectionする。Authority以外はcontent fingerprintへ寄与しglobal Entity typeを増やさない |
| semantic eval用package projection | repository eval utility | package内容を要約・変更せず連結する。Skill production CLIには含めない |
| semanticな重複・矛盾・不足 | LLM / semantic eval | 文字列一致だけで自動統合しない。required domainでは資料から識別可能なFIELD / RULE / FLOW / NOTIFY / INTERACT等を無言で欠落させず、未確定はUNKNOWNへ閉じる |

## 3. spec-analysis Skill-local helper

新規:

- skills/spec-analysis/scripts/ui_target_package.py

本helperはruntime dispatchではなく、既存authority_entities.pyと同じくSkill-local production helperです。Python標準ライブラリだけを使用し、spec-analysis package単体コピーで実行できるようにします。

### 3.1 helperが担当するoperation

production CLIは次の4 operationだけを公開します。

#### inspect

package rootを読み、package version、current file list、file × Scope ID applicability、extension file、canonical ID集合、current / resolved UNKNOWN集合、cross-file stable reference index、`scope_readiness[] / ready_scope_ids[] / blocked_scope_ids[] / completion_status`、更新用snapshotを返します。snapshotはversion / file hash / manifest hashだけを持ち、tracking / reference indexはmaterializeがcurrent packageから再導出します。意味評価は返しません。

#### validate

required file、version、ID形式・duplicate、exact reference、UNKNOWN整合、MANIFEST / README controls、CHANGELOG lifecycle、Machine Entities等のcurrent package契約を決定論的に検証します。意味的な正しさ、Authority優先順位、PAGEかVIEWか等は判定しません。

#### materialize

通常のUI target package作成 / 更新とlegacy migrationのcanonical write pathです。LLMがsemantic row / prose、reuse / new、explicit retire、file trigger、extension要否を決めた後、helper内部で次をまとめて実行します。

- create / legacy-migrationではSkill-local assetからsibling staging packageを内部初期化する。Agentへasset copyを要求しない
- snapshot hash一致後にhelper自身が再parseしたcurrent tracking/historyからのstable ID batch allocation
- default vNN version導出
- `@draft`参照解決
- Markdown escape / canonical row order / table serialization
- asset固定のstandard heading本文置換
- 条件付き標準fileのfile × Scope ID Trigger判定→file状態導出、domain row / blocking UNKNOWN closure、create/update同期、ready / blocked scope算出
- extension file番号batch allocation、作成 / 更新 / 明示廃止とfile-level stable refの存在検証
- Stable ID lifecycle / 再確認候補file算出
- README controls
- Machine Entities section
- MANIFEST / SHA-256
- final validate
- staging + package単位commit

これらは`materialize`内部関数としてrepository unit testから直接検証し、`next-version / next-id / render-readme-controls / next-domain-file / build-manifest / impact` のproduction CLI operationは作りません。

#### build-machine-evidence

09のCurrent Effective Authorityと02のcurrent AC + parent chainからpackage-global Machine Evidenceを再生成し、あわせて `ready_scope_handoffs[]` をscope別に固定projectionします。linked package item / structure ancestor / INFもAC contentへ含めます。blocked scopeはhandoffを生成しません。これはmaterialized packageからqa-workflow / test-analysis / coverage-analysisへ渡す独立production用途があるため公開operationとして残します。

semantic / deterministic eval用multi-file projectionはproduction helperへ入れず、repository専用 `scripts/skills/evals/ui_target_projection.py` が担当します。既存runnerへ1-file inputを渡すためのrepository test utilityであり、導入先Skill packageへ同梱しません。

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
- extension本文の意味生成
- semantic duplicateの統合
- Authority競合解消
- repository差分の意味判断
- 質問文生成
- stable IDをreuseする意味判断

## 4. structural ID契約

UI target packageでは、人間向け構造化ビューのentityをstable IDで参照できるようにします。

UI target modeで `materialize` 内部allocatorが番号決定を担当するprefix:

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

`ui-target-v1` では案件固有stable ID prefixを追加しません。標準tableで構造化して追跡できない独立domainはextension fileへ説明として分離しますが、extension file自身は新しいstructured ID namespaceを作りません。

IDが意味的に同一か、新IDにすべきかはLLM判断です。helperはIDを自動的に別entityへ再割当てしません。

## 5. canonical stable reference contract

UIOP / US / UC / Behavior / AC / RULE / FIELD / FLOW / NOTIFY / INTERACTのように期待挙動・制約・ルールを表すnormative rowは根拠を空にしません。current rowは `関連仕様項目ID` にcurrent SPEC / DECISION / approved ASM / INFを1件以上持ちます。根拠不足で確定できない場合はcurrent rowとして成立させず、blocked + `関連UNKNOWN ID` へ閉じます。ACはcurrent Authority 1件以上を要求する `_08 / _09` のより厳しい契約を優先します。PAGE等の純粋な構造row、Repository実装状況、pure narrative / headingは各table固有契約に従います。

- `関連仕様項目ID`: current SPEC / DECISION / approved ASM / INF等、09_authority_and_traceability.mdのcanonical item。UNKNOWNは専用の `関連UNKNOWN ID` で追跡する
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

- format: `^v[0-9]{2,}$`
- 初回: v00
- 次回: 数値部分を1増分し最低2桁でzero paddingする。v09→v10、v99→v100
- 上限は設けない
- 同じversionを別内容で完成版として上書きしない

`ui-target-v1` はこのdefault policyだけを使用します。案件固有version policyは非対応です。

MANIFESTはcurrent package fileのfile listとSHA-256を持ちます。

- MANIFEST自身はhash対象外
- README / 00〜09 / 案件固有domain / CHANGELOGのうち存在するfileを列挙
- file orderはmode referenceで固定する
- SHA-256はhelperが計算する
- Agentがhash値を手入力しない

default policyでは、完成済みpackageのuser-managed / semantic payloadへ永続差分を加えて再び完成状態として保存するならsemantic / presentationを問わずversionを1増分します。LLMが入力するcurrent versionの `変更概要` はuser-managed narrativeなので差分に含めます。version metadata、CHANGELOGのversion heading / `Stable ID changes` / `影響file`、README generated controls、MANIFEST等のhelper生成controlはversion up要否の原因に数えません。control生成前のprovisional payload + requested `change_summary` が同一ならno-opとしてversionを維持します。canonical更新経路では `materialize` が差分確定後にだけ次versionをREADME / CHANGELOG / MANIFESTへ反映します。`ui-target-v1` はdefault vNN policyだけを使用し、案件固有version policyはPR #16で扱いません。

「同じversionを別内容で完成版として上書きしない」は更新手順上の契約です。current packageだけを見るvalidatorは過去の同version内容とのbyte比較を行わず、current / previous version metadataの形式・連続性・package内一致を検証します。

## 8. question-analysis / Project ContextのSkill-local helper

新規:

- skills/question-analysis/scripts/question_ids.py
- skills/qa-workflow/scripts/project_context_ids.py

いずれもPython標準ライブラリだけを使い、各Skill package単体で実行可能にします。UNKNOWN参照だけを検証する別scriptや、採番結果だけを返す公開operationは追加しません。

`question_ids.py` の公開operation:

- `materialize`: current Q tableと `質問ID履歴` をparseし、LLMがnew questionと決めた後にprevious current Q + previous履歴 + request内current Qからnew Q IDを内部batch allocationして2 sectionをcanonical生成する
- `validate-links`: `関連UNKNOWN ID` の形式、current known UNKNOWNへの存在、同一Q内duplicate、resolved-only参照を検証する

Qの次番号計算・使用済み履歴unionは内部関数です。QとUNKが意味的に同一か、質問文、回答後の正規化先、reuse / newの意味判断は行いません。

`project_context_ids.py` の公開operation:

- `materialize`: Project Context Section 12 / 13が実際のDEC / ASM正本ownerの場合だけ、LLM / stakeholderが確定したsemantic rowsへnew IDを内部batch allocationしてcanonical生成する
- `validate-history`: previous DEC / ASM ID削除を拒否し、撤回 / 置換済みIDの再利用を防ぐ

別ownerが明示されている場合はProject Contextへ複製・再採番せず、そのownerが発行するcanonical `DEC-xxx / ASM-xxx` を使用します。外部owner用generic allocator / adapterは追加しません。owner側IDが未確定ならLLM hand-numberingへfallbackせず正本登録をblockedとします。

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
