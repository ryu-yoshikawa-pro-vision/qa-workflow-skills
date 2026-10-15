# UIテスト対象分析モード: evaluation / CI / implementation order

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

この文書は評価、CI、実装順序、完了条件を正本とします。

## 1. PR #14 baseline

実装・評価はPR #14 merge後のlatest mainをbaselineとします。詳細は `_07_pr14-baseline-and-integration.md` を正本とします。

PR #14後の期待観測値:

- Skill: 22
- Trigger queries: 488
- Deterministic output cases: 44
- Semantic cases: 155
- qa-workflow routing fixtures: 61

PR #16後の現在Plan上の期待増分:

- Skill: +0
- Trigger: +0
- Deterministic: +2
- Semantic: +8
- routing: +8

したがってStep 0時点の期待値は 22 Skill / 488 trigger / 44 deterministic / 155 semantic / 61 routingです。PR #16実装後の現在Plan期待値は 22 Skill / 488 trigger / 46 deterministic / 163 semantic / 69 routingです。ただしcase数を受入条件そのものにはせず、下記LLM responsibility coverageを満たす具体caseを正本とします。CI / repository testでは固定totalではなくPR #14のcurrent repository / manifestから動的導出します。

## 2. 評価方針

新しい評価frameworkは作りません。

既存の4層を維持します。

1. Agent Skills仕様 / repository structure validation
2. trigger selection validation
3. deterministic output / routing validation
4. semantic evaluation

今回の中心は意味分析なのでsemantic evalを主とします。同時に、`05_llm-deterministic-boundaries.md` で定型処理とした形式・参照・件数・version・MANIFEST / hash等はSkill-local production helperとdeterministic / repository testで扱います。意味判断そのものはscriptへ移しません。

## 3. spec-analysis semantic eval

現在spec-analysisは2 semantic caseです。今回5 caseを追加し、確認head前提では7件とします。case IDは `SPEC-SEM-003` ～ `SPEC-SEM-007` を使用します。

### SPEC-SEM-003: 複数資料からUI target packageを構成

入力:

- 複数PAGE / same-route VIEW / STEP / route未確定候補
- MODAL / browser dialog / PANEL / POPOVER / GLOBAL UI
- 同時成立可能な複数STATE軸
- field validation、notification、外部interaction
- UI操作あり / なし / 未確定scope
- UI操作ありだがActor / RoleまたはGoalがAuthorityから確定できないscope
- US / UC / Behavior / AC
- 正常 / 準正常 / 例外で定義あり / なし / 未定義が混在
- 一部Behavior identityは既知だが結果未確定
- 03のfield存在は確定しているがvalidation値だけUNKNOWN
- 同一scopeに複数FIELD / RULE / FLOW候補があり、一部だけを出すcandidate
- semantic identity自体が未確定でstable rowを作れないUNKNOWN

期待:

- semanticなUI構造分類を行い、STATEを直交軸として整理する
- UI操作ありと確定したscopeは意味モデル上requiredのまま維持する。影響するUIOP / US / UC / Behavior / ACがblockedならworkflow readinessではそのscopeだけblockedとする。ACはsemantic identityが同じならcurrent ↔ blockedでstable IDを維持し、意味上廃止された場合だけretireする。semantic identity自体が未確定ならstable ID rowを作らず、07へBlocking UNKNOWNを記録したうえで `_08 §3.1` の階層別配置に従う。UCは親US、BehaviorはUse Case振る舞い完全性、ACは親Behaviorへclosureし、Scopeだけへ一律退避しない
- non-blocker UNKNOWNが残るscopeと独立ready scopeを同時に含め、UNKNOWN件数だけで全scopeを止めない
- Trigger=`あり / required` とcontent incompleteを分離し、FIELD等のidentityが既知ならblocked row + UNKNOWN、identity不明ならblocking UNKNOWNで表す。内容不足を理由にTriggerを未確定へ戻さない
- inputから識別可能なFIELD / RULE / FLOW / NOTIFY / INTERACTを無言で欠落させない
- AC / Behavior / UC / USの意味を制約するdomain itemは `関連構造ID` に明示し、同一PAGE / 同一Scopeだからという理由でhelperへ逆引きさせない。semanticに必要なedge欠落をquality gateでrejectする
- current ACへ到達するUS / UC / Behaviorは全てcurrentにする
- 未定義分類では既知current / blocked Behaviorを保持でき、identity自体不明ならBehavior rowを創作しない
- `なし` はcurrent Authority参照を持つ
- ACに具体テスト条件へ先回りしない

### SPEC-SEM-004: repository実装が仕様と違う

- 高Authority仕様を実装に合わせて変更しない
- spec-implementation gapとして分離する
- repository evidenceをAuthorityへ自動昇格しない
- 08を後続versionへcarry-forwardする場合、`Repository確認基準` の各Repositoryについてbranch / revision / 確認時点を勝手に更新しない
- frontend / backend等の複数Repository baselineを同時に保持し、Aだけ再確認した更新でBのbaseline / IMPL rowを変更しない
- repository由来target-model structureはAuthorityへ昇格しないが、structure currentnessの変更はAC/TR freshness再確認へ伝播できる

### SPEC-SEM-005: versioned package更新 / UNKNOWN lifecycle

入力:

- v03 package
- resolved UNKNOWN
- resolver失効または置換
- 新しい資料差分

期待:

- same論点なら同じUNKをreopenし、別論点ならnew UNK
- row消失を自動retireとみなさず、retireはsemanticに明示する
- default policyでは完成package変更をv04として保存する
- current version `変更概要` が今回のsemantic変更を説明する

### SPEC-SEM-006: legacy migration / extension domain

入力:

- schema versionなしのlegacy package
- 後から継続利用対象になった通常spec-analysis単一成果物
- retained / retired identity
- 標準fileへ混在させるべきでないCSV domain

期待:

- legacy/current semantic identity mappingを意味判断する
- 通常spec-analysis単一成果物は同一semantic identityを維持し、package versionなし入力として `legacy-unversioned → v00` へmigrationする
- 必要なextension fileの責務・分割理由とfile-levelの関連Scope / Authority / structure / UNKNOWN refsを判断する
- 後続QA工程の判断・期待挙動・test design・freshnessへ影響する意味情報をextension proseだけに残さず、Authority / FIELD / RULE / FLOW / NOTIFY / INTERACT等のstandard structured row / 09へ正規化する
- 過去retired IDをnew entityへ再利用しない
- generic migration / generic document frameworkへ拡張しない

### SPEC-SEM-007: file trigger / external owner境界

入力:

- simple downloadだけのscope
- export生成 + data transformation + downloadを伴うscope
- conditional file trigger有無をAuthorityから確定できないscope
- Project Context以外のDEC / ASM正本owner

期待:

- simple downloadは05のみ
- export生成 / transformation + user-visible downloadは04 + 05
- trigger不明をnot-applicableへ落とさず `Trigger判定=未確定` + UNKNOWNとして保持し、helperがblockedを導出できるsemantic inputにする
- 外部ownerの意味上の正本性を判断するが、canonical Authority IDはDEC-xxx / ASM-xxxを維持し、Jira / ADR等の外部IDをauthority_idへ流用しない。canonical DEC / ASM lifecycleを提供できないownerはPR #16の対応範囲外としてcurrent Authorityへ昇格しない
- extension / conditional fileを必要以上にrequiredにしない

既存SPEC-SEM-001 / 002には「通常spec-analysisで足りる要求をUI target modeへ不要に昇格しない」回帰観点を維持します。

### spec-analysis semantic responsibility coverage

| LLM責務                                                     | semantic case                              |
| ----------------------------------------------------------- | ------------------------------------------ |
| SPEC / DECISION / INFERENCE / UNKNOWN分類・Authority競合    | 既存SPEC-SEM-001 / 002、SPEC-SEM-003 / 004 |
| PAGE / STATE / VIEW / MODAL等の意味分類                     | SPEC-SEM-003                               |
| scope UI操作有無 / 条件付きfile trigger / scope blocker判定 | SPEC-SEM-003 / 007                         |
| US / UC / Behavior / AC分解と正常 / 準正常 / 例外           | SPEC-SEM-003                               |
| semantic identity reuse / new / explicit retire             | SPEC-SEM-005 / 006                         |
| repository差分の意味                                        | SPEC-SEM-004                               |
| same-UNK reopen / new UNK                                   | SPEC-SEM-005                               |
| legacy semantic mapping                                     | SPEC-SEM-006                               |
| extension fileの必要性・意味                                | SPEC-SEM-006                               |
| DEC / ASM owner判断                                         | SPEC-SEM-007                               |
| 04 / 05責務境界                                             | SPEC-SEM-007                               |
| required domainの意味上の母集団網羅 / content incomplete    | SPEC-SEM-003 / 007                         |
| repository baseline / implementation-only freshness         | SPEC-SEM-004                               |

repository testは、`05_llm-deterministic-boundaries.md` のLLM responsibility matrixで今回追加・変更した各行が最低1 semantic criterion / caseから参照されることを検証します。case数そのものよりcoverageを正本にします。

### 複数Markdown packageのevaluation projection

既存 `scripts/skills/evals/semantic/run.py` / deterministic runnerはいずれも1つの `--output` fileを受けるため、runner自体はdirectory対応へ変更しません。

repository eval専用 `scripts/skills/evals/ui_target_projection.py` を使用し、projection modeを分けます。これはSkill packageへ同梱するproduction helperではありません。

semantic projection:

- README
- 00〜09
- 10+ current domain files
- CHANGELOG全体 / MANIFESTは除外
- current Package VersionのCHANGELOG `変更概要` bodyだけを `CHANGELOG.current_change_summary` control frameとして末尾に追加
- 過去versionのCHANGELOG、Stable ID changes、影響fileをsemantic Judgeへ混ぜない

deterministic projection:

- 全payload file
- MANIFESTを最後にcontrol fileとして追加
- version / file set / MANIFEST schema / SHA-256文字列形式 / stable ref等のmode contractを1 Markdown上で評価可能にする
- raw file bytesのSHA-256再計算はprojectionから行わず、production validate / repository unit testで独立検証する

共通:

1. package root外path / symlink / duplicate / missing fileを拒否する
2. canonical file orderを使用する
3. 各fileの前に `<!-- FILE: <relative-path> -->` markerを付ける
4. semantic change summaryは `<!-- CONTROL: CHANGELOG.current_change_summary -->` markerを使う
5. UTF-8 textをそのまま連結し、内容の要約・意味変換を行わない
6. projectionは評価用transportであり、production packageやAuthorityを変更しない

semantic / deterministicで同じprojection helperを使いますが、expected判定は各eval validator / rubricが独立して行い、production helper出力からexpectedを逆算しません。

## 4. question-analysis semantic eval

2 caseを追加し、確認head前提ではquestion-analysisを2件から4件へ増やします。

### QUESTION-SEM-003: 正式回答 / 暫定回答

- 元UNK IDを保持する
- 暫定回答を勝手にDECISIONへしない
- 正式回答後にspec-analysisへ戻す
- 回答済み論点を根拠currentの間は再質問しない

### QUESTION-SEM-004: reopen後の質問 / 別論点

- spec-analysisがsame-ID reopenを先にcurrent UNKNOWNへ戻した場合、そのUNKへ新Qを関連付けられる
- resolved-only UNKをreopen前にcurrent Qへ関連付けない
- 別論点としてnew UNKになった場合、旧resolved UNKへ質問を再接続しない
- Q ID履歴とUNKNOWN semantic identityを混同しない

## 5. test-requirement-design semantic eval

1 caseを追加し、確認head前提ではtest-requirement-designを2件から3件へ増やします。case IDは `TR-SEM-003` とします。

入力:

- current ACを持つUI target mode成果物
- 1 ACから複数の検証責務が必要な例
- 複数ACを1つの検証責務へ統合できる例
- dispositionへ送るAC

期待:

- `関連AC ID` を追跡する
- ACの文章をそのままTRへ言い換えず、「何を検証・保証するか」へ変換する
- ACとTRの1:1対応を強制しない
- current ACをTRまたは明示的dispositionへ閉じる
- ACにない具体条件 / 値 / 組合せをTRへ先回りしない
- current AC Entityをartifact modeの依存として保持する
- ACをlinkしただけで参照Authorityをclosure済みと解釈せず、Authority→TRの意味対応は別途LLMが判断する

既存TR-SEM-001 / 002はACなしworkflowの回帰として維持し、`関連AC ID=-` / `acceptance_criteria=[]` で従来責務が変わらないことを確認します。

`TR-SEM-003` はartifact modeのAC→TR意味対応を評価します。direct modeとの差はLLMの意味判断ではなくMachine Entity解決契約なので、semantic case数は増やさずStep 2のrepository runtime regressionで固定します。

## 6. qa-workflow routing eval

既存routing fixtureへmode routing caseを追加します。

8 caseを追加し、routing fixtureはPR #14後の61件から69件へ増やします。各caseは `routing_cases.json` と `routing_candidate_outputs.json` の双方へ独立に追加します。

対象:

1. UI仕様理解packageのみ
2. UI仕様理解package + 質問あり
3. 回答反映後のresume
4. current live UIの対象情報観測要求
5. 仕様理解完了後もtest design不要
6. 保存済みFigma / screenshotのUI/UX評価
7. live browserでのusability inspection
8. formal WCAG conformance evaluation

expected start / resume Skillを明示し、全Skill固定順実行へ回帰しないことを確認します。

## 7. trigger eval

今回のmode選択はspec-analysis内部の出力mode選択であり、Skill間trigger境界を変更しません。現在のspec-analysis trigger datasetには、複数資料統合・テスト分析前の仕様整理・repository/Figma/Q&A統合のpositive queryが既にあるため、frontmatter descriptionとtrigger datasetは変更しません。mode選択境界はspec-analysis semantic evalで検証します。

特に次の誤選択を防ぎます。

- 「実画面を見てcurrent UIの対象情報を記録」→ test-target-inspection
- 「保存済みFigma / screenshotをUI/UX評価」→ usability-evaluation
- 「live browserで使いやすさ / focus / responsiveを検査」→ usability-inspection
- 「WCAG version / levelでformal適合性評価」→ wcag-conformance-evaluation
- 「テスト重点を決めたい」→ test-analysis
- 「テストケースを作りたい」→ test-case-design
- 「テスト設計前の対象理解を継続成果物として作りたい」→ spec-analysis

## 8. 決定論的support / validation

`05_llm-deterministic-boundaries.md` で定型処理としたものは今回実装対象とします。「初回なので後回し」という扱いはしません。

### 8.1 spec-analysis production helper

`skills/spec-analysis/scripts/ui_target_package.py` を追加し、次のoperationを実装します。このPlanで定義していないoperationは追加しません。

- inspect
- validate
- materialize
- build-machine-evidence

version算出、stable ID採番、README controls、extension file番号、MANIFEST、Stable ID lifecycle / 影響file算出は`materialize` / `validate` が使う内部関数にします。focused testのためだけのproduction CLI operationは追加しません。

repository unit testで次を必須確認します。

- required core payload / required control file MANIFEST / file × Scope ID条件付き必須file applicability / extension file declaration
- mode assetのvariable tableがheader-onlyで例示stable IDを含まないこと。create / legacy-migrationではAgentがassetをcopyせず、materializeがSkill-local assetからsibling stagingを内部初期化すること
- package root外path拒否
- package内version一致
- canonical / structural ID形式・duplicate。既存SRC / SPEC / INF / UNK等は3桁固定、PR #16新設structural IDは最低3桁で999→1000を許可すること
- UI構造の `状態軸` がSTATEでは必須・非STATEでは空であること、`種別` exact enumでPANEL / POPOVER / GLOBAL UIを区別しつつPANEL prefixを共有すること
- canonical prefixが変わるUI構造種別変更では同じstable IDのreuseを拒否し、旧ID retire + new IDを要求すること。同じPANEL prefix内の再分類はsemantic identityが同一ならreuseを許可すること
- UI構造の存在は識別できるがPAGE / VIEW等のexact種別が未確定なcaseでは、仮typed row / `UNKNOWN`種別 / 仮prefixを作らず07 UNKNOWNだけを保持すること。分類解消後に初めてtyped IDを採番し、既存typed IDの分類根拠失効ではexplicit retire + same-UNK open / reopen後、再分類時にretired IDをreuseしないこと
- 00のscope / applicability tableで `関連仕様項目ID` と `根拠 / 備考` が別列であり、stable ID列にはIDだけ、prose列中のIDはreference扱いしないこと。applicabilityはcurrent Scope IDごとに4file exactlyを持つこと
- structured rowのexact stable ID参照
- 09のcurrent UNKNOWN集合と07 / README件数の一致
- MANIFEST file set / order / SHA-256
- helper所有fileがUTF-8 without BOM / LF / terminal LFのcanonical bytesで保存され、CRLF / BOM / terminal LF不整合をcurrent `ui-target-v1` validateで拒否すること
- staging packageをfinal validateした後だけpackage単位commitし、commit途中failureで旧版 / 新版が混在しないこと。commit失敗時は旧packageを復旧し、復旧失敗は`write_recovery_failed`でblockedになること
- README file一覧とMANIFESTの一致
- CHANGELOG最新version見出しとpackage versionの一致
- CHANGELOGのexact `Stable ID changes` table、Change enum、version内duplicate
- fresh v00の空change table、v01以降のDEC / ASM初登場=added、既追跡内容・状態変更=changed。`retire_ids[]` はpackage-owned identityだけを受け、DEC / ASMはterminal retireを拒否すること
- resolvedはUNKだけに許可し、resolved後のresolver変更 / same-ID reopenを `changed`、reopen後の再closeを再 `resolved` として許可すること
- retiredだけをterminal eventとして後続eventをrejectすること
- 履歴全体で同じStable IDへ `added / migrated` を複数回記録できないこと
- legacy migrationでDEC / ASMを含むretained tracked IDを `migrated` として引き継ぐこと。legacy `retired` eventはpackage-owned IDだけを許可し、DEC / ASMはowner currentness/historyとして移行すること。許可されたresolved / retired eventだけを使用済み集合へ予約すること
- materialize内部version算出が `package_root` / previous snapshotからcurrent versionを取得し、Agentへ `previous_version` の転記を要求しないこと
- default policyでREADMEのPackage Version / Previous Package Versionが初回または1 revision差として整合し、user-managed / semantic payloadまたはLLM入力のcurrent `変更概要`へ永続差分を保存する場合はsemantic / presentationを問わず+1となること。version metadata / generated `Stable ID changes` / generated `影響file` / README controls / MANIFESTだけの派生差分を変更原因に数えず、provisional payload + requested change_summaryが同一ならno-opでversion維持となること
- legacy migrationでは`materialize(change_mode=legacy-migration)`だけが明示legacy source versionを受け、通常更新用version計算と混在しないこと
- materialize内部README control builderがcurrent UNKNOWN件数、`completion_status`、ready / blocked scope counts、payload file tableをcanonical生成すること。Current UNKNOWN件数だけではcompletionをblockedにしないこと
- materialize内部extension allocatorがLLMのslug決定後にcurrent 10+ fileの次番号をrequest順にbatch採番し、request-wide stable draft解決後のfile-level refsを使って00の `案件固有extension file一覧` と実fileを同時生成すること
- extension declaration exact table、domain file命名、duplicate path / slug、reuse時slug変更拒否。extension本文をparseせず、00宣言rowの関連Scope / Authority / structure / UNKNOWN refsだけを存在検証・impact対象にすること。semantic evalでtest-relevant semanticsがextension proseだけに残っていないことを確認する
- `extension_file_retirements[]` はexisting current extensionだけを受理し、成功時は実fileと00宣言rowを同時に除去すること。extension本文を参照解析せず、宣言rowのfile-level stable refはfile削除と同時に除去されること
- `materialize` のartifact_mode=create / updateを検証し、normal create / legacy-migrationはprevious_snapshot=null、normal updateはnon-null hash-only snapshotをrequestとして必須とすること。lock取得後はreceipt一致をcreate target / update snapshot preconditionより先に判定し、receipt不一致createだけ不存在または空destinationから内部asset初期化、receipt不一致updateだけsnapshot照合後にprevious_modelを再parseすること。no-opでは `changed=false / replayed=false`、ID / file allocationとchanged_filesが空でversionを上げないこと
- inspectの `update_snapshot` はpackage version / payload hashes / MANIFEST hashだけを持ち、materializeがhash一致後にcurrent packageを再parseしてtracking / UNKNOWN / exact refsを再導出すること。callerがderived indexを持ち回らない
- materialize内部allocatorがsemantic identityを判断せず、UI target mode所有の `SRC / SPEC / INF / UNK` + standard structural prefixについて再parseしたcurrent row + CHANGELOG履歴から次番号を決め、更新途中で消えたprevious IDも再利用しないこと
- UI target package内部allocatorが `DEC / ASM` を採番しないこと
- DEC / ASMはCHANGELOG / lifecycle差分の追跡可能stable IDとして受理し、Project Contextがownerの場合だけproject_context_ids.pyで採番すること。package scopeから外れるだけではretiredにしないこと
- Project Context以外の明示ownerをProject Contextへ複製せず、canonical Authority IDは `DEC-xxx / ASM-xxx` を維持し、Jira / ADR等の外部record IDをauthority_idへ流用しないこと。canonical DEC / ASM lifecycleを提供できないownerはPR #16対象外とし、LLM hand-numberingやgeneric mappingへfallbackしないこと
- materialize内部allocatorが同一prefixの複数new IDを1 request内のcanonical順で重複なくbatch allocationし、keyed viewの `@draft` 参照まで解決してAgentによる逐次row書込みを不要にすること
- current viewから消えた過去IDを、snapshot一致後に再parseしたprevious current modelまたはCHANGELOG履歴で確認できる限り再利用しないこと。hash-only snapshot自体からStable IDを読み取らない
- UNKNOWNのopen / resolved / resolver変更 / same-ID reopen / re-resolveで `現在有効か / 解消先ID` が整合し、resolved状態ではcurrent SPEC / DECISION / 承認済みASMへ閉じること
- canonical structured Markdownのduplicate heading / table、row列数、backslash→pipe→LFのtable-cell encode、literal `<br>` scalar拒否、`<br>` referenceを固定parse契約で検証すること
- stable ID sortがprefix + numeric suffix integerであり、SCOPE-999よりSCOPE-1000が後になること
- extension filenameが10以上の10進連番 + lowercase kebab slugのexact grammarで、leading zeroを拒否すること
- completed package rootがcanonical payload + MANIFEST以外のregular file / nested directoryを拒否すること
- materializeのstable owner `table_changes[]` とfull-replacement `keyed_table_updates[]` を区別し、file applicability / Use Case振る舞い完全性 / Current UNKNOWN / Current Effective Authority / 後続Skill補足のexact key registryを検証すること
- keyed tableのkey / stable referenceとextensionの `scope_refs / authority_refs / structure_refs / unknown_refs` で同requestのstable `@draft:<draft_key>` をfile applicability判定前に解決でき、未解決draft / extension draft namespace参照をrejectすること
- materialize内部lifecycle builderがsnapshot hash照合後に再parseしたprevious current modelとprovisional tracking row差分から `added / changed / resolved` を生成し、`retired` は明示 `retire_ids[]` だけから生成すること。previous ID消失のみなら `state_transition_required` でblockedすること
- materialize内部impact builderの `影響file` がchanged IDのprevious/current owner + exact reference先unionであり、Agentへfile一覧再入力を要求せず、semantic本文変更の要否を勝手に決定しないこと
- legacy migrationではLLMが確定したretained ID / 明示lifecycle event / semantic rowsを `materialize(change_mode=legacy-migration)` へ渡し、helperがnew ID採番・canonical Markdown・`migrated / added / resolved / retired`・README / Machine Entity / MANIFESTまで1 write pathで生成すること
- scope applicability、UI操作scopeのUIOP / US / UC / Behavior / AC hierarchy / current AC chain全parent=current / closure / current UCの3分類整合。UIOP / US / UC / Behavior / ACの状態はhelper導出とし、semantic identity未確定時はIDを発行せず07のBlocking Scope IDへ閉じること。UIOP.Scopeは対応UCのderived Scopeとexact一致すること
- known UIOPでUS / UC identity未確定により対応先を完成できない場合、既存の同Scope Blocking UNKNOWNを `関連UNKNOWN ID` に再利用してsame UIOP IDをblockedで保持し、原因UNKNOWN解消後にsame IDをmappedへ戻せること。blocked UIOPに専用UNKNOWNの新規作成を強制しないこと
- required scope + UIOP 0件 + Blocking UNKNOWNなしをrejectし、required scope + identity未確定Blocking UNKNOWNをvalid/blocked、mapped UIOP → current US / UC → Behavior → current AC closureをreadyとして導出すること
- current UCで正常 / 準正常 / 例外がすべて `なし` かつBehavior=0件をreadyにせず、`未定義 + UNKNOWN` はvalid/blockedとして扱うこと
- current Behaviorがblocked ACだけを持つ場合はscope blocked、current AC 1件以上かつblocked ACなしでready条件を満たせること。AC-001 current → blocked → currentで同じstable IDを維持し、explicit retireなしでAC-002を採番しないこと
- file × Scope ID applicability、blocked UIOP / US / UC / Behavior / AC / RULE / FIELD / FLOW / NOTIFY / INTERACT、UC完全性=`未定義`、07 Blocking Scope IDから `scope_readiness[] / ready_scope_ids[] / blocked_scope_ids[] / complete|partial|blocked` を導出し、non-blocker UNKNOWNが残っても独立scopeをreadyにできること
- Trigger=`あり`のrequired scopeで内容不足をTrigger=`未確定`へ戻さないこと。identity既知ならblocked domain row、identity不明で0 rowなら07のBlocking Scope ID + 関連Fileによりclosureできること。standard conditional fileの関連Fileは物理file未作成でもstandard registry pathならvalid、extensionはcurrent宣言 + 実file必須とすること
- `未定義` で既知current / blocked Behavior IDを0件以上保持できUNKNOWN必須、Behavior identity自体不明ならblocked Behaviorを創作しないこと
- `なし` は関連Behavior / UNKNOWNなし + 理由 + current Authorityの `関連仕様項目ID` 1件以上を要求すること
- 09の「現在有効な仕様根拠」からnormalized Authorityを固定projectionし、`適用範囲` を非空string、`関係` を単一許可値の1要素arrayとして一意にserializeすること
- `build-machine-evidence(scope_ids=null)` がpackage-global Authority + current AC Entityと `ready_scope_ids[] / blocked_scope_ids[]` を返し、scope別full payloadを重複返却しないこと。`build-machine-evidence(scope_ids=ready_scope_ids)` は `_06 §9.3` の固定seed / edgeから各ready scopeを内部projectionし、1つのbatch normalized input / Entity / expected identityへunion / dedupeすること。duplicate / blocked / unknown scope指定をrejectし、canonical qa-workflowではcurrent ready_scope_ids全件とのexact一致を要求すること
- ready SCOPE-001 / SCOPE-002、blocked SCOPE-003で、SCOPE-001→SPEC-001,SPEC-002,AC-001、SCOPE-002→SPEC-002,SPEC-003,AC-002なら、batchがSPEC-001/002/003 + AC-001/002をexactly once含み、SCOPE-003由来rowを含めず、Agent mergeなしで既存 `artifact:*:all` runtimeを1回だけ起動すること
- batch handoffから `artifact:analysis_entities:all` / `artifact:requirement_structure:all` のcanonical stdinを構成し、2 MiB + 1 byteでも16 MiB以下なら通過、16 MiB exactlyも通過、1 byte超過ではruntimeを起動せず `limit_exceeded` になること。その他の通常generatorは2 MiB + 1 byteを従来どおりrejectすること。scope別個別run / subset run / silent truncate / auto splitで回避しないこと
- scope A / Bで別Authorityを持つ場合にbatch内で混在先を誤らず、明示共有Authorityは1件へdedupeされ、UI操作なしscopeでもscope-owned RULE / FLOW等のAuthorityをACなしでhandoffできること
- UIOP `対象構造ID` はUI構造prefixだけを許可し、domain item prefixをrejectすること。linked domain itemはAC / Behavior / UC / USの `関連構造ID` に明示されたIDだけで、同一PAGE / 同一Scopeから逆引きしないこと
- AC / Behavior / UC / USの明示domain ref、linked UIOPのUI target、scope、linked domain itemのUI structure refからcurrent SPEC / DECISION / approved ASMをAuthority dependencyへ投影し、linked INFはcontent-only projectionへ入れること。current Authorityが0件なら `state_transition_required` でblockedし、helper自身はUNKNOWN / blocked rowを生成しないこと
- parent_structure_id missing / self / cycleをrejectすること。artifact modeではancestor・明示linked domain item・linked INF変更でAC/TRがstaleになり、同一PAGEにあるだけで明示参照されないFIELD等の変更ではAC fingerprint / TR freshnessが変わらないこと
- `Machine Entities: spec-analysis` blockがexactly one存在し、heading / JSON fence / wrapperを含めhelper再生成Markdownと一致すること
- 1つのnormalized spec-analysis handoff / current Entity collectionへ複数UI target packageのpackage-local Machine Entity blockを直接mergeしない契約をrepository testで固定すること
- linked UIOP / UIOP-only Authority / scope / direct structure + ancestor / linked FIELD-RULE-FLOW-NOTIFY-INTERACT / linked INF / 親US-UC-Behavior変更でAC Entity fingerprintまたはAuthority dependencyが変わり、無関係package row変更では変わらないこと
- repository eval専用 `ui_target_projection.py` がsemantic / deterministic projectionを生成し、semantic projectionではcurrent versionの `変更概要` controlだけを追加し、過去CHANGELOG / Stable ID changes / 影響fileを混ぜないこと
- raw SHA-256はeval projectionから再計算せず、production validate / repository unit testでraw bytesに対して検証すること

### 8.2 question-analysis / Project Context production helper

`skills/question-analysis/scripts/question_ids.py` と `skills/qa-workflow/scripts/project_context_ids.py` を追加します。UNKNOWN link検証だけの `unknown_links.py`、採番だけの公開 `next-id` operationは追加しません。

`question_ids.py`:

- `operation=materialize`: create / updateを区別し、previous current Q + previous history + request内reuse/newからnew Q IDを内部batch allocationしてcurrent Q table + 質問ID履歴をcanonical生成し、同じcall内でcurrent / resolved UNKNOWN link validationまで完了する
- `operation=validate-links`: 既存artifactのstandalone検証用としてUNK ID形式、current known UNKNOWNへの存在参照、同一Q内duplicate、resolved-only参照を検証する
- candidate側の既存historyを採番正本にせず、Q-001解消後の新規QでQ-001を再利用しない
- malformed / duplicate Q ID、Q-999 exhaustionをfail-closedにする

`project_context_ids.py`:

- `operation=materialize`: Project Context Section 12 / 13がDEC / ASM正本ownerの場合だけ、previous + candidate全状態rowからnew IDを内部batch allocationしてcanonical tableを生成する
- `operation=validate-history`: previous DEC / ASM ID集合の欠落をrejectし、撤回 / 置換済みIDの削除と再利用を防ぐ
- canonical Authority IDは `DEC-xxx / ASM-xxx` に限定し、外部owner固有IDをauthority_idへ流用しない
- 別ownerが明示されている場合はそのownerのcanonical ID lifecycleを使い、Project Contextへ複製・再採番しない

QとUNKの意味的同一性、Q / DEC / ASMのsemantic identity、DECISION内容、ASM承認可否、Project Context以外の正本schema解釈は検証しません。canonical DEC / ASM lifecycleを提供できない別ownerはPR #16の対応範囲外であり、LLM hand-numbering / generic mappingへfallbackせずcurrent Authority登録を行いません。

### 8.3 deterministic output eval

既存spec-analysis / question-analysis / test-requirement-design validatorへ、production helperとは独立したfixture検証を追加します。

- spec-analysis: UI target packageのcanonical table / stable ref contractを評価
- question-analysis: known_unknown_ids / expected_related_unknownsを評価
- production helperをimportしてexpectedを生成しない
- spec-analysisはmode固有 `SPEC-OUT-003` を追加して2→3件、test-requirement-designは `TR-OUT-003` を追加して2→3件、question-analysisは既存2件のfixture拡張で維持する。PR #14後baseline 44件から全体46件とする

### 8.4 semanticに残すもの

次はLLM / semantic evalの責務として今回から明示的に対象外とします。

- SPEC / DECISION / INFERENCE / UNKNOWNの意味分類
- PAGE / VIEW / STATE / MODAL等の意味分類
- semantic identity / reuse判断
- Authority競合解消
- scopeのUI操作有無 / 条件付き必須file trigger該当性
- 案件固有extension fileの必要性・責務
- semantic duplicate /矛盾の判定
- repository差分の意味的な重要性
- US / UC / Behavior / ACの意味分解
- 正常 / 準正常 / 例外の意味分類
- ACとTRの意味的対応 / TR分割統合

これらは「後からvalidator化する候補」ではありません。機械化するとLLMの柔軟性を損なうため、意味判断として残します。

## 9. CI

既存workflowを再利用します。

runtime / Machine Entity version cutoverでは、current repository内のactive referenceをexact searchで確認します。

- `runtime-v1` がshared runtime contractを指すcurrent code / Skill文書 / asset / eval fixture / test metadataは `runtime-v2` へ同期する
- `entity-state-v1` がactive Machine Entity schemaを指すcurrent code / asset / eval fixture / deterministic validatorは `entity-state-v2` へ同期する
- active output template / fixtureに `entity_schema_version`、単一 `dependencies`、`runtime-contract-v1`、`runtime-envelope-v1` の旧擬似schemaを残さず、runtime helperのcanonical block shapeと一致させる
- template / fixtureのMachine Evidence例はcurrent v2 validatorでparse / validateできることをrepository testで確認する
- `docs/history/**` と完了済み旧Planは変更しない
- `workflow-runtime-v1`、`schema-cases-v1`、`usability-inspection-runtime-v1`、`wcag-em-runtime-v1` 等のgenerator contract identifierはshared runtime versionではないため変更しない
- `schema_cases.py` / `flow_paths.py` 等の「runtime-v1未対応」表現がgenerator対応範囲を意味する箇所はshared runtime v2へ機械置換せず、必要なら `schema-cases-v1` / `flow-paths-v1` 等のgenerator contract名へ言い換える
- 単純な文字列全置換ではなく、上記区分をrepository test / reviewで確認する

今回必須:

- Validate Agent Skills
- Validate Semantic Output Evals
- Validate Deterministic Output Evals
- production helper unit / portability tests
- repository unit tests
- git diff --check

新しいGitHub Actions workflowは追加しません。

今回の計画どおり実装した場合の想定現在値:

- Skill数: 22のまま
- trigger query: 488のまま
- deterministic output case: 44 → 46
  - spec-analysis: 2 → 3
  - test-requirement-design: 2 → 3
  - question-analysis: 2のまま
- semantic case: 155 → 163
  - spec-analysis: 2 → 7
  - question-analysis: 2 → 4
  - test-requirement-design: 2 → 3
  - その他Skill: 変更なし
- qa-workflow routing fixture: 61 → 69

Step 0でmainの現在値を再確認し、上記差分がそのまま適用可能な場合は次を同期します:

- EVALS.md
- docs/PROJECT_CONTEXT.md
- `tests/skills/evals/semantic/test_semantic_datasets.py` のSkill別件数とtotal
- routing fixtureの固定件数を検証するrepository test / 文書
- README.mdは件数またはmode説明を実際に持つ箇所だけ更新
- PR #14後の `.github/workflows/deterministic-output-evals.yml` は `skills/*/scripts` を動的compileするため、helper compile目的のSkill固有workflow editは行わない

歴史文書の過去値は変更しません。

## 10. 実Agent smoke

実装完了前に少なくとも1回、実Agentクライアント相当で次を確認します。

入力:

- 複数の仕様根拠
- 1件以上の正式decision
- 1件以上のUNKNOWN
- repository補助事実
- 「テスト設計へ進まず対象理解packageまで」の要求

確認:

- 通常の小規模spec-analysis要求ではmodeへ不要に昇格しない
- UI target用途ではspec-analysis modeを選択する
- mode referenceを読む
- repository事実を仕様Authority化しない
- package構造を作れ、`ui_target_package.py build-machine-evidence` でAuthority + current AC Machine Entity、spec-analysis normalized_skill_inputへ閉じられる
- question-analysisが必要論点だけ扱う
- test-analysisへ自動進行しない
- outputがmodeの品質ゲートを満たす
- `ui_target_package.py` により形式・参照・件数・version・MANIFEST / hash・behavior decomposition closureを検証できる
- MANIFEST順evaluation projectionを通して既存semantic runnerへ入力できる

AIエージェント上で、既存Agent Skillsの読み込み方法に従い `spec-analysis` → mode reference / assetsを利用して成果物を生成できることを確認します。

特定製品のtool名やconnectorを評価条件にはしません。

## 11. 実装順序

### Step 0: PR #14 merge後rebase / current repository再確認

- main headがPlan基準から動いていないか確認
- PR #14 merge済みlatest mainへrebase
- 22 Skill / 488 trigger / 44 deterministic / 155 semantic / 61 routingが観測baselineと一致するか確認
- spec-analysis / question-analysis / qa-workflow / test-target-inspection / usability-evaluation / usability-inspection / wcag-conformance-evaluationのcurrent契約確認
- semantic / routing datasetの現在件数確認
- README / EVALS / PROJECT_CONTEXTの現在値確認

mainが動いていてもPlanを盲目的に適用せず、責務契約が変わっていれば差分を再評価します。

### Step 1: UI target package schema / materialize基盤

- SKILL.mdに目的ベースの条件付きResource導線
- references/ui-test-target-analysis.md
- required core payload / MANIFEST / 条件付き必須file / 宣言制extensionを分けたpackage assets
- standard 00〜09のheading集合をassetで固定し、LLMは既存heading本文だけを更新する。新規standard headingを追加しない
- extensionは自由記述Markdownだけとし、独自structured table / custom stable IDを追加しない。00の宣言rowへfile-level関連Scope / Authority / structure / UNKNOWN refsを持たせる
- variable structured tableはheader-onlyで例示stable IDを置かない。file applicabilityもassetへ固定scope rowを事前配置せず、materializeがcurrent Scope IDごとに4row生成する
- 条件付きfileはfile × Scope IDでLLMの `Trigger判定=あり / なし / 未確定` からhelperが `required / not-applicable / blocked` を導出する
- Current UNKNOWN件数ではなく明示blocked状態から `ready_scope_ids[] / blocked_scope_ids[]` と `completion_status=complete / partial / blocked` を導出する。blocked scopeがあってもready scopeは後続へ進める
- Trigger=`あり`のdomainはrequiredのまま維持する。identity既知ならFIELD / FLOW / NOTIFY|INTERACT等をcurrent / blocked rowで保持し、identity不明なら07のBlocking Scope ID + 関連Fileでclosureする。内容不足をTriggerへ逆流させない
- UI構造はexact種別を確定できる時だけtyped structural row / IDを作る。分類未確定では07 UNKNOWNへScope / `01_ui_structure_and_navigation.md`を記録し、後続を止める時だけBlocking Scopeとする。既存typed rowの分類根拠失効はexplicit retire + same-UNK open / reopenで扱い、仮種別や汎用structural prefixを追加しない
- skills/spec-analysis/scripts/ui_target_package.pyの `inspect / validate / materialize` と内部allocator / version / README / MANIFEST / lifecycle / impactを実装。create / legacy-migrationはhelper内部でSkill-local assetからstaging初期化し、snapshotはhash identityだけ保持、derived tracking / refsはmaterializeが再parseする
- `table_changes[]` のprimary prefix決定を `_06` のmaterialize内 `primary prefix selector contract` へ固定する。固定prefix tableはstandard registry、UI構造は`種別`、通知・外部連携は`種別`、09分析項目は`分類`からhelperがprefixを導出し、callerの`primary_prefix`入力を許可しない
- packageへ初登場するowner確定済みDEC / ASMは `identity_action=external` で取り込み、package allocatorは番号を発行しない。同requestの`@draft`をowner IDへ解決し、既追跡IDは`reuse`だけを許可する。09分析項目ではDEC=`分類=DECISION`、approved ASM=`分類=承認済みASM`とし、後者をspec-analysis通常分類の追加候補としてLLMに生成させない
- `prose_updates[]` はassetに存在するstandard exact heading本文だけを置換する。新規heading作成 / rename / deleteを許可しない
- canonical table cell encode、complete file set、sibling staging / backup、preflight orphan recovery、commit直前snapshot再照合、package単位切替 / rollbackを実装
- `ui_target_package.py` 内部だけにfixed sibling process lockを追加し、POSIX `fcntl.flock` / Windows `msvcrt.locking` の標準ライブラリ実装で同一packageをsingle writer化する。PR #14のclaim / reservation / CAS helperはpackage writeへ使わず、generic lock serviceも作らない
- canonical materialize request fingerprintとMANIFEST `Last materialize receipt` を追加し、commit後response前crashでも同一request replayが前回のID / extension割当・retire結果を返してmutationを再適用しない。createは事前inspect不要、updateはreceipt不一致時だけprevious snapshotを要求する
- normative rowのAuthority / UNKNOWN traceability、domain rowのhelper-derived state、Scope / Blocking Scope / 関連File、scope readiness、UIOP→UC scope一致、UNKNOWN lifecycle、extension lifecycle、Repository確認基準をvalidateする
- applicabilityの逆方向整合をvalidateする。03/04/05/08が`not-applicable`のScopeを対応FIELD/FLOW/NOTIFY|INTERACT/IMPL rowが参照する状態、またはBehavior Decomposition=`not-applicable`のScopeにUIOP / US / UC / Behavior / ACが残る状態をrejectする。helperはScope参照除去・row split・retireを自動推測しない
- BehaviorへLLM明示の`関連操作ID`を追加し、current Behaviorは1件以上のmapped UIOPへ接続する。helperはUIOP存在・Scope・親UC整合だけを検証し、AC Entityのlinked UIOPはparent Behaviorの`関連操作ID`からだけprojectionする
- UIOP identityが既知でもUS / UC identity blockerで `対応UC ID` が未確定なら、原因となる既存Blocking UNKNOWNをUIOP自身から参照してblocked stateを維持する。helperはUNKNOWNのcurrent / same-Scope Blocking / 関連File整合を検証し、解消後はsame UIOP IDをmappedへ戻す
- versionを `^v[0-9]{2,}$`、数値+1、最低2桁zero padding、上限なしに固定する。新設structural IDも最低3桁・上限なし、既存canonical IDは3桁契約を維持する
- legacy / unversioned packageに加え、通常spec-analysis単一成果物 → ui-target-v1 migrationを同じsemantic mapping + materialize経路で扱う

このStepではshared runtime versionをまだ変更しません。Machine Entity bridgeを含むruntime依存部分はStep 2で同時に成立させます。

### Step 2: runtime schema transition / AC bridge / requirement-structure-v2を原子的に反映

このStepは1つのruntime schema transitionとして扱い、`runtime-v2 / entity-state-v2` だけ先行した中間状態を完成checkpointにしません。ただし実行中断時の再開まで禁止する意味ではなく、固定依存順に沿ってcurrent v2 verification済みとなった先行Skill / TCD phaseは再開用evidenceとして利用します。依存順に反する混在はfail-closedし、qa-workflow final gate成立前の部分完了をv2 baselineへ昇格させません。

- PR #14後の9 Skill-local `runtime_contract.py` をbyte-identicalに更新し、`acceptance_criterion` / `acceptance_refs` / spec-analysis expected ACを追加
- `RUNTIME_CONTRACT_VERSION: runtime-v1 → runtime-v2`、`ENTITY_SCHEMA_VERSION: entity-state-v1 → entity-state-v2`。v1 validatorが `acceptance_criterion` を受理しないためentity type追加をschema意味変更として扱う
- envelope shape / freshness algorithmは維持
- independent `runtime_validator.py`、active code / Skill文書 / asset / fixture / repository testをv2へ同期
- active Machine Evidenceの手書き擬似schemaを削除し、runtime renderer / authority_entities.py / build-machine-evidence生成結果を正本にする。packageへのMachine Entities section書込みはmaterialize内部だけで行い、standalone build-machine-evidenceはread-onlyとする
- `authority_entities.py` の既存 `{authorities:[...]}` CLIを維持したまま、legacy移行用の排他的入力 `{source_artifact_markdown:"..."}` を追加する。exactly one `Machine Entities: spec-analysis` v1 blockをfrozen `entity-state-v1` 規則で検証し、各Authority Entityのcanonical `content`だけをcurrent v2 `build()`へ渡す。v1 `content_fingerprint` / dependency / wrapperはcarry-forwardせず、block missing / invalid時はhuman-readable table parserへfallbackせず通常spec-analysis semantic rerunを要求する
- `ui_target_package.py build-machine-evidence` を実装し、AC / Behavior / UC / USの明示 `関連構造ID` からlinked domain item、linked UIOPの `対象構造ID` と明示UI structure refからstructure + ancestor、linked INFをAC contentへ固定projectionする。同一PAGE / Scope等の逆引きを禁止する。Authorityだけdependency Entityとする。package-global callはready / blocked scope ID indexだけ、batch callはcurrent ready scope全件を `_06 §9.3` で内部projectionしてAuthority / current AC / Machine Entity / expected identityを1集合へunion / dedupeし、ready scopeの `scope_id / target / ui_operation / authority_refs[]` をcompact `scope_index[]` で返す
- `skills/test-analysis/scripts/analysis_entities.py` / `skills/test-requirement-design/scripts/requirement_structure.py` は既存 `artifact:*:all` runtime unit identityを維持したまま `run_cli(..., aggregate=True)` へ変更し、root input上限を16 MiBにする。transport上限を `input_mode` で分岐するwrapperは追加せず、この2 root unitはdirect / artifactとも同じ16 MiB上限を使う。その他の通常generatorは2 MiBを維持する
- generator contractを `requirement-structure-v1 → requirement-structure-v2`、`condition-structure-v1 → condition-structure-v2`、`materialize-coverage-v1 → materialize-coverage-v2`、`case-structure-v1 → case-structure-v2` へ更新する。4 generatorへrequired machine-owned `zero_scope_terminal` booleanを追加し、normal path=false、全SCOPE retire terminal pathだけtrueとする。TRDはtop-level `acceptance_criteria[] / scope_ids[]`、各TRのsemantic `acceptance_refs[] / scope_refs[]` を追加し、4 generator共通でstable ID stateへ `inactive` を追加する。artifact modeでは各TRの参照AC Entity `content.scope.scope_id` unionを`required_scope_refs[]`としてdeterministicに導出し、TR `scope_refs[]`へ必ず含める。LLMはそれ以外の追加ownershipだけを判断する。TCNは参照TR、modelは親TCN、CIは親TCN / model、TCは参照TCN / CIからscope_refsを決定論伝播する。UI target packageからTRDへ進むcanonical workflowはartifact modeに固定し、upstream AC Entity集合とのexact一致 + AC/Authority dependency + semantic freshnessを要求する。direct / non-UI-target v2 baselineは `scope_ids=[] / scope_refs=[]` を許可する
- current ACをTRまたはDispositionへ閉じ、Authority closureは独立維持する
- TR EntityへAC EntityとACが参照するcurrent Authority Entity dependencyを保存する
- shared runtimeへSkill固有migration projectionを入れない。新規 `skills/test-requirement-design/scripts/runtime_v1_cutover.py`、`skills/test-condition-design/scripts/runtime_v1_cutover.py`、`skills/test-case-design/scripts/runtime_v1_cutover.py` がcomplete v2 generator inputを決定論生成する
- 各cutover helperはstdlib + 同Skill current `runtime_contract.py` だけをimportするが、v1 source artifactはhelper内のread-only legacy readerで `runtime-v1 / entity-state-v1` のfrozen schema / fingerprintを検証し、current v2 validatorへv1 Entityを渡さない。通常generatorへfield mergeを要求しない。TRD / TCはall、TCDはcondition-structure → models反復 → test-data-requirements → materialize-coverageのphase契約を持つ
- cutover外側stdinはhelper固有decoderでaggregate 16 MiBを許可し、top-level artifact Markdownだけ64 KiB string上限を免除する。embedded v1 JSON scalarは通常64 KiB、各v1 runtime JSON blockは旧2 MiB上限で検証する。current `strict_loads()` のverify専用例外を流用せず、cutover契約からgenerator上限を変更しない。別途ready-scope root runtime契約として `analysis_entities.py` / `requirement_structure.py` だけaggregate 16 MiBへ変更し、その他の通常generatorは2 MiBを維持する
- 内容不変cutoverでTR / TCN / model / CI / TC stable identityと既存deleted履歴を維持する。v1にはdownstream `inactive` stateが無いためcutover時にinactiveを推測生成せず、v2通常workflowでready→blocked遷移が発生した時点から使用する
- `workflow_runtime.py` のruntime-v2 input / result payloadへexisting `workflow_ref`を追加し、`workflow-state-template.md`へmachine-owned `last_completed_qa_workflow_artifact={artifact_ref,artifact_revision,artifact_sha256}` を1 field追加する。
- 新規 `skills/qa-workflow/scripts/migration_preflight.py` を追加し、runtime-v1残存、current v2 verification済みSkill、cutover途中状態、current v2 baseline、UI target package有無、active downstreamのscope ownership、current ready / blocked scopeからcutover / UI target migration / ownership normalization / `scope_ownership_baseline_required` / partial progressionのnext actionを決定論生成する。runtime cutover中は固定依存順に沿う部分完了だけを受理し、最初の未完了Skillを`cutover_next_action`として返す。TCD内部phaseはqa-workflowへ持ち込まず、Skill-local `runtime_v1_cutover.py phase=resume`へ委譲する。`workflow_runtime.py` はcurrent v2 aggregate verifierのまま維持し、pre-runtime migration判定や再開位置をLLMへ残さない
- `artifact_graph.py` へqa-workflow専用local single-hostの `commit_qa_workflow_baseline_local()` / `read_qa_workflow_artifact_revision_local()` を追加し、既存 `qa.workflow_state_root` 配下のcontent-addressed immutable snapshot、workflow-ref固定process lock、lock内expected state revision再確認、same-directory temporary + fsync + `os.replace` でlocal commitを成立させる。provider-nativeではactual historical refetch + native CASを使う。どちらもcurrent verification PASS → artifact exact refetch / SHA確認 → conditional state update成功をdownstream baselineのcommit境界とし、CAS / locked update前のartifactは未commitでprevious snapshotへ使用しない。既存 `local_exact_content_token_not_a_cas_condition` の意味は変えず、新しいworkflow lineage ID、artifact registry、generic transaction framework、generic storage adapter、handoff typeは追加しない
- 新規 `skills/qa-workflow/scripts/downstream_state.py` を追加する。current workflow state bindingからexact previous qa-workflow artifactを解決し、state / runtime Input双方の`workflow_ref`一致とraw Markdown SHA-256を検証する。historical runtime pairはqa-workflow専用のfrozen runtime-v2 integrity readerで保存Input / Result schema、pair、stored fingerprint、dependency、Entity fingerprint、保存済みcurrent structure stateの自己整合を検証する。previous active / inactive TR / TCN / model / CI / TCのscope removal影響を抽出し、semantic ownerにはvalidated current Entityまたはinactive history由来の`last_active_content / content_fingerprint`を返す。owner LLMはreuse時の`resolved_scope_refs[]`またはsemantic deletionだけを返し、意味上のsplitはold=`deleted` + replacement=`new` draftとして通常generator updateで表す。resolution後はexpected stateを返し、generator適用後のvalidated root/materialize resultからqa-workflowがprojectした`scope_removal_applied_states[]`とのexact一致まで`requires_materialization=true`を維持する。`current_scope_ids=[]`ではLLM判断なしで全scoped non-deleted downstreamをterminal deletedへ導出する。単一用途helperとしてoperation dispatchは追加せず、`_09 §12.3` のexact stdin/stdout、strict duplicate-key / unknown-field rejection、16 MiB transport、fixed issue type、handled failure exit 0 / unexpected internal error exit 1をproduction contractにする
- shared runtimeのprevious state validator / carry-forward projectionを `active / inactive / deleted` に同期し、activeだけをcurrent Entityとexact一致させる。inactive / deletedはcurrent Entity・expected Entity・carry-forward対象外とし、inactive自体をstale issueへ変換しない。inactive state rowのscope_refsはlatest resolved semantic ownership、`inactive_*_history[]` はlast-active Entity snapshotを保持するため、SCOPE removal後のreuseではscope_refs exact一致を要求せずidentity / stored fingerprint /各ownershipの個別整合を検証する
- zero-scope terminalではTRD / TCD / materialize-coverage / TCをdeletion-onlyで実行し、previous active / inactive state全件をterminal deletedへ閉じる。TCDはvalidated previous current/inactive materialize stateからCI state / mappingもterminal cleanupし、coverage-analysisをcurrent downstream 0件で再生成する。qa-workflow runtimeの`workflow_scopes[]`は空にせず、spec-analysis zero-scope package + terminal structure state + coverage resultをcurrent Skill scopeとして検証し、PASS後にterminal baselineをcommitする
- test-analysisはPR #16でもcurrent ready-scope batchごとのfull rerunを維持し、Product Riskへ `scope_refs / inactive / history` を追加しない。同一runのTRDはcurrent Product Risk集合を使ってclosure / priorityを再評価する。blocked scope由来Riskのcarry-forward用stateful partial rerunを新設しない
- 既存v1 downstream artifactがある場合は `spec-analysis Authority v2再生成 → test-analysis v2再生成 → TRD → TCD → TC v2 full rebuild → coverage-analysis v2再生成 → 必要なusability-inspection / wcag-conformance-evaluation v2再生成 → qa-workflow final gate v2再生成 → UI target package migration / AC生成 → active downstream全件のscope ownership正規化を含むTRD→TCD→TC semantic update → coverage-analysis / qa-workflow再生成` の依存順に固定する。UI target migration時点で既存active downstreamのscope_refsが空なら、全scope readyの1回だけをownership normalization gateとし、blocked scopeがある間は `scope_ownership_baseline_required` で停止する。baseline成立後は通常のpartial readinessへ進める。downstream未作成の新規workflowにはこのgateを課さない
- v1 downstreamがない場合は直接UI target package migration / normal v2 workflowへ進める
- `_09` の9 Skill処置表どおり、TRD / TCD / TCだけstable identity cutover helperを使う。test-analysis / usability-inspection / wcag-conformance-evaluationにはSkill-local read-only `runtime_v1_input_reader.py` を追加し、pre-cutover baselineのfrozen v1規則で保存済みRuntime Input / Result pairのintegrityを検証してsemantic inputだけを返す。readerはcurrentnessを判定せず、v1 runtime metadata / dependency / fingerprint / Entityをv2へcarry-forwardしない。test-analysisはcurrent v2 upstream Entityとのidentity / content fingerprint整合後にv2 full rerun、usability-inspection / wcag-conformance-evaluationは既存artifact graph / handoff / evidence currentnessが成立する場合だけv2 deterministic rerunし、不成立なら通常rerun / re-observationへ戻す。coverage-analysisはcurrent upstream v2 evidence、qa-workflowはcurrent workflow state / routing inputから常に再生成し、保存v1 Runtime Inputを再利用しない。proseからinputを再構築しない
- artifact modeでUIOP / UIOP-only Authority / scope / 明示linked domain item / AC chain・UIOP・domain item由来structure + ancestor / linked INF / 親Behavior-UC-US / Authority変更によるAC / TR freshness regressionを追加し、同一PAGE / Scopeにあるだけで明示参照されないdomain item変更のnon-stale regressionも固定する。direct modeはAC Entityなしでこのsemantic freshnessを要求しない
- shared runtime 9-copy byte-identity、cutover helper portability、固定依存順に沿うruntime-v1/v2部分完了のresume、順序違反の混在拒否、Skill内source artifactのv1/v2混在拒否、semantic drift、phase dependency、mapping ambiguityをrepository integration testで固定する
- spec-analysis v1 Authority projectionはcanonical v1 wrapper / Entityの`schema_version=entity-state-v1`、skill / entity_type / entity_ref、content fingerprint、空dependency、`content.authority_id == entity_ref`をfrozen規則で検証し、valid v1 → v2 Authority再生成、改変v1 → reject、missing block → semantic rerunをrepository testで固定する
- 3つの `runtime_v1_input_reader.py` はpackage単体compile / portabilityを確認し、valid baseline v1 pairからsemantic inputを抽出できること、Input / Result identity・runtime-v1 version・generator contract・input/model/generation fingerprint・dependency・baseline implementation fingerprintの改変をrejectすることを固定する。readerがcurrentness=trueを返す契約は作らない
- test-analysisはreader出力からcurrent v2 dependent runtimeをfull rerunし、`analysis_entities` のmachine-owned result fieldをv1からcarry-forwardせずcurrent v2 resultで再構築する。current upstream Entity identity / content fingerprint不一致では保存input再利用を停止する
- usability-inspection / wcag-conformance-evaluationはreader成功だけでは保存inputを再利用せず、既存artifact graph / handoff / evidence currentnessが確認できた場合だけv2 runtimeを再実行する。currentness不明・不一致、reader invalid / missingは通常rerun / re-observationへ固定する
- coverage-analysis / qa-workflowはvalidなv1保存inputが存在しても再利用せず、それぞれcurrent upstream v2 evidence / current workflow state・routing inputからv2 evidenceを再生成する回帰を固定する
- `analysis_entities.py` / `requirement_structure.py` のaggregate root regressionとして、2 MiB超〜16 MiB以下のcanonical request成功、16 MiB + 1 byteの `limit_exceeded`、その他の通常generatorで2 MiB + 1 byteが従来どおり `limit_exceeded` になることを固定する
- legacy readerが改変v1 fingerprint / dependencyをrejectし、64 KiB超のtop-level artifact Markdownは16 MiB以内なら受理、artifact内scalarの64 KiB超はrejectするtransport回帰を固定する
- requirement-structure-v2 artifact回帰: semantic `acceptance_criteria[]` とcurrent upstream AC Entity集合のexact一致、参照AC + AC Authority dependency、missing Entity fail-closedを固定する。`AC-002.scope=SCOPE-B`を参照するTRからSCOPE-Bを`scope_refs[]`で欠落させる入力をrejectし、AC由来required scopeに加えて別ready ScopeをLLMが追加する入力は許可する
- requirement-structure-v2 direct回帰: upstream AC Entityが0件でもsemantic `acceptance_criteria[]` からknown ID / closureを検証でき、存在しないAC / AC由来Authority Entity dependencyを合成しない。AC EntityなしではAC本文 / 親chain変更のcross-run freshnessを保証しない。参照AC Entityが実在する場合だけAC dependencyを追加し、そのdependencyには既存freshnessを適用する

### Step 3: spec-analysis evaluation

- SPEC-SEM-003〜007を更新し、UI操作あり + Actor/Goal不足、identity未確定blocking UNKNOWN、UI構造の存在は既知だがPAGE / VIEW等の分類未確定、known UIOP + US / UC identity blocker、non-blocker UNKNOWNを残したscope部分進行、Trigger required + content incomplete、required domainの無言欠落防止、通常spec-analysis→mode migration、外部owner対象外境界を含める
- canonical write前にsemantic inputをquality gateし、semantic NG candidateをcurrent packageへcommitしない契約をsemantic / integration caseで固定する
- LLM responsibility coverage表を更新
- repository eval専用 `scripts/skills/evals/ui_target_projection.py` のsemantic / deterministic projection unit test
- `SPEC-OUT-003` package fixtureをdeterministic projectionして既存runnerへ入力
- projectionしたpackageをsemantic runnerへ渡せることを確認
- semantic countをspec-analysis=7へ同期
- Agent Skills structure validation

### Step 4: question-analysis連携 / DEC・ASM owner採番

- stable UNKNOWN参照、回答正規化後のspec-analysis resume
- `不明点 / 質問一覧` と `質問ID履歴` をheader-onlyへ変更
- skills/question-analysis/scripts/question_ids.py（materialize / validate-links）。materializeはcurrent / resolved UNKNOWN集合を受けてlink validationまで同callで完了する
- Project Contextが実際のDEC / ASM正本ownerの場合だけ skills/qa-workflow/scripts/project_context_ids.py（materialize / validate-history）を使用
- 別ownerではProject Contextへ複製・再採番せず、導入先ownerがcanonical `DEC-xxx / ASM-xxx` を供給する。供給できない場合はfail-closedとし、generic external registry / adapterを追加しない
- ownerで確定したDEC / ASMをUI target packageへ初回反映する時だけ`ui_target_package.py materialize`の`identity_action=external`を使い、以後は`reuse`へ切り替える。Project Context ownerでは`project_context_ids.py materialize`結果、別ownerではそのownerのcanonical IDをそのまま渡し、LLM hand-numberingへ戻さない
- helper unit / portability test、deterministic mapping、question semantic caseを追加

### Step 5: qa-workflow routing

- mode request routing / answer resume。小規模でも継続利用目的ならmodeを優先し、通常downstreamへ入る前に `migration_preflight.py` のstatusを確認する。cutover / UI target migration / ownership normalizationが必要ならそのnext actionだけへ進み、`scope_ownership_baseline_required` なら停止する。partial progression ready後は `scope_readiness[] / current_scope_ids[] / ready_scope_ids[] / blocked_scope_ids[]` を使う。`current_scope_ids[]` non-empty + ready 0件は全blockedとしてbaseline維持、`current_scope_ids=[]` はzero-scope terminalへ分岐する。previous downstreamがあるrunではcommit済みbinding + exact historical artifact + current scope universeを `downstream_state.py` へ渡す。retired SCOPE参照はvalidated last-active snapshotをowner LLMへ渡し、resolution→generator適用→applied-state再検証まで閉じる。zero-scopeではsemantic resolutionを挟まずterminal deletionを決定論適用する
- qa-workflowはUI target packageのwrite state / reservation rowを追加せず、`ui_target_package.py materialize` のrequest fingerprint / receipt / package-local process lockをそのまま利用する。updateはinspect snapshotを渡し、createはsnapshotなしでmaterializeする。resumeで同一semantic requestを再構成できた場合は同一fingerprint replayを利用し、再構成できない場合はreceiptを根拠に別requestを推測せずspec-analysisのsemantic input再作成へ戻る
- batch handoffから `artifact:analysis_entities:all` / `artifact:requirement_structure:all` のcanonical stdinを1つ構成し、batch全体を16 MiB上限へ検証する。超過時はruntime未起動のままblockedにし、scope別個別run / subset run / auto splitを行わない。その他の通常generatorは2 MiB上限を維持する
- 継続利用目的を単発規模より優先するmode precedenceをroutingへ反映
- runtime-v1 downstreamが残る状態でUI target migration済み、または必要なv2 baselineが未成立ならblockedにし、Step 2の依存順へ戻す
- test-target-inspection / usability-evaluation / usability-inspection / wcag-conformance-evaluationとの分岐
- routing_cases.json / routing_candidate_outputs.jsonへ8件追加し合計69件へ同期

### Step 6: package schema / migration / helper contract validation

- `ui-target-v1` schema、helper I/O、sort、failure enum、filesystem safety
- standard heading registry、conditional file Trigger判定→状態導出、blocked packageの構造valid / completion blocked分離
- extension自由記述-only契約、extension create/update/retire、test-relevant semanticsをextension proseだけに残さないsemantic contract
- request-wide draft allocation / stable ref / normative traceability / MANIFEST receipt / Authority + AC Machine Entity bridge
- mixed-prefix tableのselector、`identity_action=new / reuse / external`、owner発行済みDEC / ASM初回取込、同request`@draft`解決、`承認済みASM` mirror row、DEC / ASMのpackage allocator拒否を検証する
- public `inspect / validate / build-machine-evidence / materialize` が同じpackage-local exclusive lockへ参加し、lock取得後に共通preflight recoveryを通してからcommitted rootを読むこと。readerはroot→backup途中やcrash後backup-only状態で一時不存在 / mixed-versionを返さない。materialize内部validator / parserはlock済み内部関数を使って再lockしない
- inspect snapshot → materialize → explicit retire lifecycle
- legacy vNN / unversioned packageとnormal spec-analysis single artifactのmigration fixture
- package migrationとruntime cutoverの相対順integration test

### Step 7: deterministic / semantic boundary validation

- semantic identity、explicit retire、same-UNK/new-UNK、file trigger、extension要否、DEC/ASM owner、UI分類、US/UC/Behavior/AC分解、AC→TR対応をscriptが決定していないこと。一方でmixed-prefixのprefix選択、owner確定済みDEC/ASM IDの非採番取込、参照ACから必須になるTR scope包含は意味判断後の決定論処理としてscript側に残すこと
- exact UI構造種別を確定できない状態でhelperが仮type / 仮prefixを作らず、LLMがUNKNOWNとして保持すること。known UIOPとUS / UC identity blockerの意味対応もLLMが既存UNKNOWNを選び、helperは参照整合とstate導出だけを担当すること
- helperはtrigger状態、ID、serialization、file materialization、lifecycle、reference、Machine Entity projectionだけを決定論化すること
- helperがAuthority不足等を検出した場合はblocked resultだけを返し、AC除去 / Behavior blocked化 / UNKNOWN reuse/new等のsemantic transitionを実行しないこと
- normal spec-analysisがmode依存になっていないこと
- production helperがSkill package単体で実行できること

### Step 8: cross-repository validation

- 全22 Skill構造 / trigger / deterministic / semantic / routing
- docs current count
- git diff --check

### Step 9: 実Agent smoke

- UI target package scenario（canonical Authority + current AC Machine Entity）
- non-blocker UNKNOWNを残したままready scopeだけ後続へ進み、blocked scopeだけquestion-analysis待ちになるscenario
- question-analysis回答反映 → spec-analysis package更新
- UI操作あり + Actor/Goal不足でscope=requiredのまま下位rowだけblocked + UNKNOWNになるscenario
- conditional file trigger未確定のscopeを保持したpackageが`partial`で保存でき、別ready scopeは継続できるscenario
- required conditional fileでidentity既知itemがblocked + UNKNOWNとして保存でき、identity未確定で0 rowの場合は07のBlocking Scope ID + 関連Fileでscopeをblockedにできるscenario。Triggerはrequiredのまま維持する
- runtime-v1 downstream → spec-analysis v1 Authority projection / v2再生成 → test-analysis v2再生成 → TRD/TCD/TC Skill-local cutover → coverage-analysis v2再生成 → 必要なusability-inspection / wcag-conformance-evaluation v2再生成 → qa-workflow final gate v2再生成 → UI target migration → 全scope readyでscope ownership normalization → coverage-analysis / qa-workflow再生成 → partial readinessの順序を確認するscenario。ownership baseline前にblocked scopeがある場合は `scope_ownership_baseline_required`、downstream未作成の新規workflowではこのgateなしでready scopeだけ進める。coverage-analysis / qa-workflowは保存v1 inputを使わない
- 上記migration scenarioでは `migration_preflight.py` の5 statusが各checkpointで期待値どおり遷移し、`runtime_v2_cutover_required` 中は固定依存順の最初の未完了Skillが `cutover_next_action` と一致することを確認する。Agentがruntime version、再開位置、ownership baseline要否を意味判断しないことを確認する
- runtime-v1 → v2 migrationをspec-analysis / test-analysis / TRD / TCD / TC / coverage-analysis / 必要なinspection・WCAGの各境界で中断して再実行し、current v2 verification済みの先行Skillを再利用して最初の未完了Skillから再開するscenarioを追加する。後続Skillだけv2の順序違反状態はfail-closedする
- TCDは `condition-structure` 完了後、`models` の一部unit完了後、`test-data-requirements` 完了後、`materialize-coverage` 完了直後で中断するscenarioを追加する。`phase=resume` がvalidated partial v2 artifactから最初の未完了phaseを選び、verified済みphase / model unitを再生成せず、invalid / out-of-order partial artifactをrejectする
- 64 KiB超のv1 artifact Markdownを含むcutover requestが16 MiB以内で成功し、v1 fingerprint改変 / embedded scalar 64 KiB超をrejectするscenario
- artifact modeでUIOP / UIOP-only Authority / scope / structure ancestor / 明示linked domain item / linked INF / Behavior / UC / US / Authority変更によるTR staleと、同一PAGEにあるだけで未参照のdomain itemを含む無関係package row変更non-stale scenario
- ready scope A/BのAuthority分離、共有Authorityのbatch内dedupe、UI操作なしscopeのAuthority handoff、blocked scope非混入をready-scope batch smokeで確認する。既存 `artifact:analysis_entities:all / artifact:requirement_structure:all` をscopeごとに複数回起動しない
- package-global build responseがscope full payloadを複製せず、ready-scope batch runtime requestが2 MiBを超えても16 MiB未満なら既存 `artifact:analysis_entities:all / artifact:requirement_structure:all` を1回だけ起動して完遂できるscenario。16 MiB exactly / 1 byte超過の境界値はrepository testで固定する
- SCOPE-A/B readyでTRD→TCD→TCまでscope_refs付きで生成後、Bだけblockedにするscenario。`scope_refs`がBと交差する旧TR / TCN / model / CI / TCだけが`inactive`へ遷移してcurrent Entity/runtimeから外れ、A専用Entityはcurrentのまま後続を完遂する。AuthorityをA/Bで共有していてもscope_refsで正しく分離できること、A/B両方をscope_refsに持つcross-scope Entityは保守的にinactiveになること、B再ready時はlast-active Entity historyとTCD materialize historyからsemantic identity / CI mappingを復元し、同じstable IDへ戻せることを確認する
- artifact modeで `AC-B → SCOPE-B` を参照するTRに `scope_refs=[SCOPE-A]` だけを与えるnegative scenarioを追加し、required AC scope欠落としてTRDがrejectすることを確認する。`scope_refs=[SCOPE-A,SCOPE-B]` はAへの追加ownershipが意味上妥当なら許可する
- 上記scenarioではprevious snapshotをcurrent `workflow_ref` のcommit済み `last_completed_qa_workflow_artifact` からだけ復元する。local pathではtemporary directory上へ実際にimmutable revisionを保存・refetchし、保存済みworkflow runtime pair / `current_entities[]` / `current_structure_state`の改変をrejectする。spec-analysis更新後に旧artifactをcurrent inputで再検証して`current_structure_state=null`になることとは独立して、当時のvalid snapshotを抽出できることを確認する。previous artifactが必要なのに欠落する場合はfail-closedする
- historical integrity regressionとして、旧runtime-v2 implementation fingerprintで生成・current verification PASS済みのqa-workflow artifactは、現行implementation fingerprintが変わった後でもstate binding / stored fingerprint / dependency / Entity / structure stateが自己整合ならhistorical readerで受理する。一方、同artifactをcurrent evidenceとして `verify_runtime_evidence()` へ渡すとstaleになることを確認する
- workflow binding regressionとして、正しいcurrent `workflow_ref` + latest completed `artifact_ref/revision/sha256`だけを受理し、別workflow artifact、1世代古いartifact、SHA不一致、previous bindingありなのにMarkdown=null、binding=nullなのにMarkdownあり、historical refetch unavailableをrejectする
- downstream baseline commit regressionとして、local temporary rootでbaseline Aをcommit後もAのexact revisionをrefetchできること、同一expected state revisionから競合する2更新を試みると一方だけがcommitされ他方がconflictになること、snapshot作成後state commit前failureでは旧bindingを維持すること、state replace後response前retryではdesired state exact一致なら`committed_replay`になることを確認する。provider-native pathはactual historical refetch / native CAS capabilityが無ければfail-closedする
- `downstream_state.py` production CLI regressionとして、duplicate JSON key、unknown top-level field、16 MiB + 1 byte、artifact Markdown以外の64 KiB + 1 string、workflow_ref mismatch、binding/Markdown null不整合、SHA mismatch、historical runtime invalid、scope ownership unavailable、inactive materialize history missing、scope removal history missingをfixed `valid=false / payload=null / issues[]` + exit 0で検証し、unexpected internal errorだけexit 1とする
- scope removal semantic ownerのaffected rowへvalidated `last_active_content / last_active_content_fingerprint`を返し、inactive ownerではhistory欠落を`scope_removal_history_missing`でrejectする。resolution後もgenerator適用前は`requires_materialization=true`、validated applied state一致後だけfalseになる3-phase regressionを追加する
- `resolution=split`はschemaでrejectし、意味上のsplitをold=`deleted` + replacement通常`new` draftとして同じowner updateでmaterializeする。新しいsplit lineage / replacement registryを追加しない
- 同一UCにUIOP-A/BとBehavior-A/B、AC-A/Bが存在し、Behavior-AだけがUIOP-A、Behavior-BだけがUIOP-Bを`関連操作ID`で参照するscenarioを追加する。UIOP-A変更ではAC-A/TR-Aだけがstaleになり、AC-B/TR-Bはcurrentを維持する
- SCOPE-Aの03がrequired、SCOPE-Bの03がnot-applicableで03 file自体は残るpackageに、SCOPE-Bを参照するFIELDを残したnegative scenarioを追加する。同様に04/05/08とBehavior Decomposition not-applicableのUIOP / US / UC / Behavior / AC残存をrejectする
- `UC-001 → BH-001 → AC-001` がcurrentの状態からUCだけにUNKNOWNが発生するscenarioを追加し、LLMがidentity reuseを選んだ場合はhelperがUC / BH / ACを同じIDのままeffective blockedへ伝播し、ancestor由来だけのBH / ACへ新規UNKNOWNを作らず、解消後に同IDでcurrentへ戻すことを確認する
- child identity未確定の3経路を固定する。UC identity不明では親USへBlocking UNKNOWNを置いてUS blocked + UC 0件、Behavior identity不明ではcurrent UCの該当完全性rowを`未定義 + UNKNOWN` + Behavior 0件、AC identity不明では親BehaviorへBlocking UNKNOWNを置いてBehavior blocked + AC 0件とする。UC/AC identity不明をScopeだけへ置いてparentをcurrentのまま残す状態と、Behavior identity不明をblocked Behavior rowで捏造する状態をrejectする
- UI構造の存在は識別済みだがPAGE / VIEW分類を確定できないscenarioを追加し、typed row / IDを作らずUNKNOWNで保持、解消時にnew typed ID発行とsame-UNK resolve、既存typed IDの分類根拠失効時はexplicit retire + same-UNK reopenとなることを確認する
- mixed-prefix materialize scenarioを追加し、同一`UI構造一覧`内のPAGE / VIEW、同一`通知・外部連携一覧`内のNOTIFY / INTERACT、同一`分析項目`内のSPEC / INF / UNKがselector fieldから正しいprefixへ決まり、owner確定済みDEC / ASMは`external`で初回取込・`reuse`で更新されることを確認する。approved ASMは`分類=承認済みASM`で追跡し、package allocatorによるDEC / ASM採番をrejectする
- known UIOP + US identity unknown、known UIOP + UC identity unknownを追加し、root causeの既存Blocking UNKNOWNをUIOPが参照してsame ID blocked、解消後same ID mappedとなり、UNKNOWNを複製しないことを確認する
- SCOPE-A/B readyでcompleted baseline作成 → A/Bともblockedで `ready_scope_ids=[]` → downstream runtime無起動 / last completed binding維持 → Bだけreadyへ復帰 → baseline artifactからAだけinactive、Bは同じstable IDで再開、というintegration regressionを追加する
- SCOPE-Aだけのownership済みcompleted baseline → A retire → `current_scope_ids=[]` のscenarioを追加する。全blocked early returnへ入らず、previous active / inactive TR / TCN / model / CI / TCをdeletion-only generator pathでdeletedへ閉じ、coverage / qa-workflowをzero-scope current baselineとしてcommitする。binding=nullならruntime不要、unscoped active downstreamが残る場合は`scope_ownership_unavailable`でfail-closedする
- A/B baseline → B blockedでB-only downstreamがinactiveになったcompleted baseline → A readyのままB retireするscenarioを追加し、previous current Entityに無いinactive identityもvalidated inactive historyからscope-removal affectedへ抽出し、ownerへlast-active contentを渡せることを確認する。history欠落はfail-closedする
- SCOPE-A/B readyでcompleted baseline作成後、Bをexplicit retireするscenarioを追加する。previous `scope_refs[]` にBを含むTR / TCN / model / CI / TCを `scope_removal_affected_entities[]` へ抽出し、自動でA-onlyへ縮退しない。ownerがreuse resolutionを返した場合はresolved ownershipからavailability stateをhelperが導出する。特にA+B → B retire + A blocked + C readyでA ownershipへreuseした旧IDをA ownershipのinactiveとして保持し、last-active historyは旧A+B snapshotを維持、C専用downstreamは完遂、A再readyで同IDをactiveへ戻す
- readyのまま内容だけ変更されたACは従来どおりscope外carry-forward TRをstaleにし、`inactive`経路でfreshness違反を隠さないscenario。inactive中に意味上廃止された成果物は`deleted`へ遷移し、再利用しない。inactive前にdeletedだったCI IDも `inactive_materialize_history[].ci_id_state[]` へ残り、再ready後のallocatorが再利用しないことを確認する
- required scopeで0 UIOP + blockerなしをreject、0 UIOP + identity未確定Blocking UNKNOWNをpartial/blocked保存、完全なUIOP→US→UC→Behavior→AC closureをreadyにするscenario
- 同一packageへの2 process materializeがpackage-local OS lockで排他され、commit後response前crash後の同一request replayがMANIFEST receiptから二重new ID / extension / retireなしで完了できるscenario。create replay、update replay、別requestのstale拒否、lock holder process kill後の再取得も確認する
- process kill相当のorphan staging / backupをpreflight recoveryでき、一意に復旧不能ならfail-closedするscenario
- materializeがroot→backup後・staging→root前に停止した状態で、最初の次operationがinspect / validate / build-machine-evidenceでも共通package lock取得後にbackupから復旧してlast committed packageを読めるscenario
- materialize commitとinspect / build-machine-evidenceを競合させ、readerがcommit前またはcommit後の完全な1 versionだけを読み、root不存在や旧/new file混在を観測しないscenario
- deterministic helperが構造エラーを返してもLLMの意味判断を上書きしないscenario

### Step 10: final review

- 新Skillや不要wrapper / generic registryを追加していない
- spec-analysis / test-target-inspection境界が壊れていない
- repository実装をAuthorityへ昇格していない
- modeなしのspec-analysisが重くなっていない
- qa-workflowがSkill-local cutover処理を複製していない
- shared runtimeがTRD / TCD / TC固有migration schemaを保持していない
- 特定AI製品固有のtool / connector / bootstrapをSkill契約へ入れていない
- 実装時に参照すべき正本fileが一意に分かる

## 11.1 実装チェックリスト

- [x] Step 0: PR #14後の最新main統合とcurrent repository baselineを確認。既存merge commitに最新mainが含まれるためrebaseは行わず、418 commitの公開履歴を書き換えない。実測値と確認した契約は `_07 §12` の2026-10-13結果を参照。
- [x] Step 1: UI target package schema / materialize基盤
- [x] Step 2: runtime-v2 / entity-state-v2 transition、AC bridge、generator v2、migration runtime。2026-10-13継続確認: 3 cutover helper / 3 input reader、downstream scope/history、migration preflightとzero-scope pathを実装・runtime suiteで再検証済み。詳細は本節末の追補を参照。
- [ ] Step 3: spec-analysis semantic / deterministic evaluation
- [x] Step 4: question-analysis UNKNOWN lifecycle / DEC・ASM owner helper
- [x] Step 5: qa-workflow routing / resume / scope readiness統合。69 routing fixture、partial / historical / retired / zero-scope経路を再検証済み。詳細は本節末の追補を参照。
- [x] Step 6: package schema・migration・helper contract validation。package runtime、migration preflight、projectionの再検証を完了。詳細は本節末の追補を参照。
- [ ] Step 7: deterministic / semantic責務境界の検証
- [ ] Step 8: cross-repository validation（2026-10-15 local refresh: runtime 366 passed / 2 Windows symlink privilege skips、deterministic shared 12 passed、deterministic repository 290 passed、semantic dataset 22 Skills / 163 cases、semantic shared 27 passed / 2 skips、semantic repository 13 passed / 1 skip、trigger 1 passed、Agent Skills validation 25/25 passed、Ruff / formatter / compileall passed。Codex Harnessは31 tests passed後、`test_execpolicy_cli` class setupがsandbox内の`codex.cmd`アクセス拒否でerrorとなり、CLI試験は開始できなかった。local CLI runtime acceptanceは未確認。GitHub API / remote socketも拒否され、最新head CIは確認不能。）
- [ ] Step 9: 実Agent smoke（41項目を維持。最新local matrixは37 PASS / 4 PARTIAL、`step9_complete=false`。item 15のcross-Skill blocked/inactive/resume、item 24のartifact-mode freshness / persisted baseline gate、item 32のcurrent CI rowを含むactive baselineからzero-scope terminalへのexact-revision branchはPASS。item 7 / 9 / 34 / 35はPARTIAL。）
- [ ] Step 10: final review（本追補時点でPR全体は未完了。Step 3 / 7 Semantic Judge、Step 8 local CLI acceptance、Step 9の4 PARTIALと最新CIが未確認のため、最終レビュー完了条件は未成立。）

2026-10-13時点でStep 2は未完了です。3つの`runtime_v1_input_reader.py`、TRD / TC cutover helper、関連runtime contractは存在しますが、`skills/test-condition-design/scripts/runtime_v1_cutover.py`が未実装で、TCDの4 phase / `resume` / partial model unit検証を完了していません。このためTCD cutoverを含むStep 2、migration preflightからfinal gateまでのStep 5、および依存する全体完了条件を満たしていません。Step 3 / 7もSemantic Judgeによる意味評価が未実施のため完了扱いにしません。

### 2026-10-13 継続作業結果

- Step 2: `skills/test-condition-design/scripts/runtime_v1_cutover.py`とTCD cutover回帰testを追加し、condition-structure / models / test-data-requirements / materialize-coverageのphase、`resume`、partial model unit、frozen v1 integrityを検証した。既存TRD / TC cutoverと3つのread-only input readerを含むruntime suiteは339件成功、Windows symlink privilegeによるskipは2件。
- Step 5: qa-workflow routing、migration preflight、historical / inactive ownership、scope removal適用確認、all-blocked保持、zero-scope terminal pathを含むruntime・repository regressionを再実行した。routing fixture 69件とcase / candidate identityの同期、8つのUI target routing boundaryを専用test 2件で確認した。
- Step 6: UI target package runtime、legacy / normal spec-analysis migration、Machine Entity projection、MANIFEST / filesystem契約、repository projectionをruntime・deterministic・semantic repository testsで再検証した。実Agent packageの`SPEC-OUT-003` deterministic evaluationは21/21 PASS。
- Step 3 / 7: deterministic boundary testsは通過したが、Semantic Judge呼び出しは外部APIへの評価対象送信がauto-reviewで拒否されたため未実施。別経路では再試行せず、意味評価のPASSとは扱わない。
- Step 8: current retestはruntime 339 passed / 2 Windows symlink privilege skips、deterministic shared 12 passed、deterministic repository 290 passed、semantic dataset 22 Skill / 163 cases、semantic shared 27 passed / 2 Windows symlink privilege skips、semantic repository 13 passed / 1 Windows symlink privilege skip、routing 2 passed、Codex Harness 36 passed（installed `codex-cli 0.162.0-alpha.17.2`）。`python scripts/format_tracked.py check`は207 tracked targetsでPASS。PR head `f45ef4741c2759178c4eab1f1c68b9da12e677ff` とPlan更新後head `557bc10c351d518818e0ac9db86201ff6c4c3260` のlatest CIは全5 workflow success: Codex Harness Linux / Windows `codex-cli 0.162.1`、各36件成功（LinuxはWindows-only 8件skip）、Code Quality、Deterministic Output、Semantic Output、Agent SkillsがPASS。
- Step 9: real AgentはUI target packageを1 scenario生成し、blocked UNKNOWNを保持したpartial package、Authority 2件 / current AC 3件のMachine Entity evidence、`SPEC-OUT-003` 21/21 PASSを確認した。migration、routing、resume、複数scope lifecycle等の残りのPlan scenarioは未実施。
- Step 10: 最終差分・安全契約レビューを実施し、continuation差分にactionable findingがないことを確認した。`format_tracked.py check`と`git diff --cached --check`は成功。Semantic Judge・残りのAgent scenarioはレビュー結果と分離して未完了とする。

### 2026-10-14 残検証の継続結果

この追補は検証状況を記録するもので、Planの仕様、検証要求、完了条件は変更しない。Step 3 / 7 / 9は未完了のままとする。

- Python環境: system Pythonと既存venvはいずれも3.11.9。テストは既存venvを使用し、新規依存の導入は行っていない。
- Step 8 tests: runtime 345 passed / 2 Windows symlink privilege skips、deterministic shared 12 passed、deterministic repository 290 passed、semantic dataset validation 22 Skills / 163 cases、semantic shared 27 passed / 2 skips、semantic repository 13 passed / 1 skip、qa-workflow routing 2 passed / 69 fixtures synchronized、trigger contract 1 passed、Agent Skills validation 22/22 passed。
- package transaction regression: create replay、process lock release、backup-only / ambiguous recovery、reader / materialize commit atomicity、not-applicable scopeの残存FIELD拒否、semantic split拒否を追加した。POSIXで追加reader race testがpipeを二重flushしたテスト不具合を修正し、最新headで再実行した。今回の検証では製品runtimeの不具合を確認していない。
- local formatter: format_tracked.py checkはRuff段階通過後、dprint executableが見つからず完了できなかった。最新headのCode Quality CIはpass。変更Python fileのRuff check / format checkとdiff whitespace checkはpass。
- local Codex Harness: 31 tests pass。sandbox内でCodex CLIのexecpolicy起動が拒否されたため、そのCLI setup検証は未実施。権限拒否を迂回していない。最新headのcodex-contract / windows-launcher CIはpass。
- Semantic candidate: 対象8 caseはSPEC-SEM-003〜007、QUESTION-SEM-003〜004、TR-SEM-003。SPEC-003 / 007とQUESTION-003 / 004の4 caseはhelper validationが有効。SPEC-004 / 005は更新元package不足、SPEC-006はretained ID mapping不足、TR-003はcanonical Scope ID不足でblocked / incomplete。input copyとcandidate artifactのhashを記録した。
- Semantic Judge: 実行しておらず、外部送信はない。run.pyは任意のjudge-commandを受け取るがprovider / endpoint / modelは選定していない。送信する場合、promptにcase input、criteria / rubric、reference、candidateが含まれ得る。case dataはsyntheticで顧客PII / secretは見つけていないが、認証情報の環境継承、providerの保持条件、概算費用はprovider / model選択前には確定できない。今回のAPI費用は0。実行前にprovider / endpoint、model、認証方式、保持条件、cost capの承認が必要。
- Step 9 matrix: .artifacts/pr16-step9-matrix.jsonに41項目それぞれのscenario、existing / added tests、deterministic evidence、real Agent evidence、missing conditionを記録した。2項目がPASS、39項目がPARTIALで、step9_completeはfalse。matrixとsmoke artifactはignored local evidenceであり、PRには添付していない。
- Real Agent: current sessionでscenario 01はpackage / Authority / AC Machine Entity生成までpass。scenario 02はready / blocked scope、question回答反映、package更新 / resumeとMachine Entity projectionまでpassしたが、qa-workflow downstream dispatch / baseline commitは未検証。scenario 07はhelperの構造参照エラーを意味判断から分離して修復し、materialize / inspect / Machine Entity projectionがpass。scenario 03〜06相当の完全経路、migration / cutover、完全なrouting、scope inactive / reactivate / retire / zero-scope、splitとidentity-unknown placementは未検証。artifact、input、helper結果、hashは .artifacts/pr16-agent-smoke/ に保存した。
- latest verification head 661136e90e329febe088aceb90bb275ca32c895e: Analyze、Code Quality、Codex Harness（codex-contract / windows-launcher）、Deterministic Output、Semantic Output、Agent Skills validation、CodeQL status checkがすべてpass。通常push後のPR #16で確認した。
- Step 10: 追加差分とテストのレビューは行ったが、Plan所定のfinal reviewはStep 3 / 7 / 9の完了後に再確認する。

### 2026-10-14 継続検証

この追補は検証結果を記録するもので、実装仕様やPlanの完了条件は変更しない。

- Python: system Pythonと既存`.venv`はいずれも3.11.9。runtime suiteは346 passed / 2 Windows symlink privilege skips。deterministic repository suiteはsystem PythonではPyYAML未導入により失敗したため、依存を追加せず既存`.venv`で再実行し290 passed。UI target deterministic output contractは2 passed、semantic dataset validatorは22 Skills / 163 casesでpass。
- 修正した不具合: 条件付き必須file applicabilityのTriggerが`未確定`で、同一materialize request内の`@draft:unk-*`を参照すると、keyed input validationがdraftをstable IDとして誤拒否した。`_keyed_row_from_input`でrequestの`allow_draft`契約に従ってUNKNOWN参照を解析するよう修正し、`test_uncertain_file_trigger_accepts_same_request_unknown_draft`を追加した。修正後のruntime / deterministic testsはpass。
- Step 9 scenario 03: 現sessionのAgentがspec-analysis Skillとui target guidanceを読み、Scope A/B ready、Scope CのGoal UNKNOWN、既知UI操作、未確定03/04 applicabilityを判断した。package materialize / inspect / ready-only Machine Entity projectionがpassし、Goal・UC identityを捏造せず、SCOPE-003をUNK-001でblocked、completionをpartialに保持した。入力、判断、request、response、artifact、verificationとSHA-256は`.artifacts/pr16-agent-smoke/scenario-03-rerun/`に保存した。
- Step 9 scenario 04: qa-workflow / TCD Skillを読み、migration preflightの`test-condition-design / resume`に従った。production TCD cutover helperがcondition-structureを選択し、v2 runtime後のresumeがmodelsを選択した。ただしv1入力はfrozen test fixtureから生成したため、real-Agent smokeはpartialとし、Plan項目7の完了根拠にはしない。証拠は`.artifacts/pr16-agent-smoke/scenario-04/`。
- Step 9 matrix: 41項目は削除せず、Plan項目5のconditional-file partial progressionをPASSへ更新した。現在3 PASS / 38 PARTIAL、`step9_complete=false`。migration全境界、qa-workflow full routing、scope inactivity/reactivation/retirement/zero-scope、split / identity-unknown placement等は未達。
- Step 9 scenario 05: current-session Agentがscenario 03のcurrent Authority / AC Machine Entitiesを参照して2 scopeのtest requirementを作成し、TRD runtimeでblock / inactive、同一ID・fingerprintでreactivate、explicit retire、zero-scope terminalを確認した。実TRD runtimeと証拠は`.artifacts/pr16-agent-smoke/scenario-05/`に保存した。qa-workflow baseline commit、TCD / TC、cross-skill freshnessとdownstream inactive historyは未実施なのでcomposite scenarioはpartial。
- Step 3 / 7: 対象8 semantic caseのcandidate準備記録は既存どおり。Semantic Judgeは実行せず、外部送信もしていない。dataset validatorやhelper検証をSemantic Judge PASSとして扱わない。
- formatter / CI: local `format_tracked.py check`はRuff段階と変更Python fileの形式確認後、dprint executable不在により完了できない。実装・Plan更新をpushした後にCode Quality CIで確認する。Step 3 / 7 / 9未完了のためStep 10最終レビューとPR全体の完了判定は未実施。

### 2026-10-14 実行環境復旧後の実Agent smoke追補

この追補は現在の検証証拠を記録する。Step 3 / 7 / 9の完了条件は変更せず、Semantic Judge未実施のためStep 3 / 7とPR全体を完了扱いしない。

- 環境: system Pythonと既存`.venv`はPython 3.11.9。追加依存の導入は行っていない。system PythonではPyYAML不足でdeterministic repository suiteが失敗したため、追加installせず既存`.venv`で290件pass。runtime 346件pass / Windows symlink privilege skips 2件、deterministic shared 12件pass、UI target output contract 2件pass、semantic shared 27件pass / 2 skips、semantic repository 13件pass / 1 skip、semantic dataset validation 22 Skills / 163 cases pass。qa-workflow routing 69 fixtures / 2 tests、Trigger 1 test、Agent Skills validation 22/22 pass。
- Step 9 scenario 01 / 02 / 03 / 07: 既存Agent証拠の全hashを確認。scenario 02はsynthetic approved answerをquestion-analysisからpackageへ反映し、partialから全scope readyへのresumeまでpass。scenario 03ではActor既知 / Goal UNKNOWN / UI操作既知のScope Cをrequiredのままblockedにし、Scope A/BのみMachine Entityへ進めた。
- Step 9 scenario 04: 前回のtest fixture入力によるrunはpartialの履歴として保持し、PASS根拠には使用しない。current-session Agentがspec-analysis / test-requirement-designのTR-001を意味判断し、synthetic legacy v1 TCD semantic inputを作成。frozen v1 pair serializerはruntime envelope / fingerprintの生成に限って使用した。production migration_preflightが`test-condition-design / resume`を選択し、production cutoverがcondition-structureを指定。runtime-v2実行後、cutover resumeがmodelsを指定し、TCN-001 / ep-001を維持した。focused helper chainはpassだが、歴史的v1 artifactのprovenanceと固定順全Skill migrationは未検証のためcomposite Agent smokeはpartial。入力・artifact・helper request / responseとhashは`.artifacts/pr16-agent-smoke/scenario-04-agent-authored/`。
- Step 9 scenario 05: Agentが作成したupstream EntityからTRD runtimeを実行し、Scope B inactive、同一TR ID / fingerprintでreactivate、retire、zero-scope terminalをpass。qa-workflow completed baseline、TCD / TC、cross-skill freshness / inactive historyが未実施のためcompositeはpartial。
- Step 9 scenario 06: unclassified ellipsisをtyped UI IDなしのUNKNOWNとして保持し、question ID / UNKNOWN links、mixed prefix、ready/blocked projection、Project Context ownerのDEC / ASM判断を実行。追加のsplit updateではv00のcombined UIOP-002をretireし、v01でselection / exportのUIOP-004 / UIOP-005を新規採番、意味が変わらないUC-002 / US-002 / BH-002 / AC-002 / SCOPE-002 / SPEC-002をreuseした。Scope C UNKNOWNはblockedのまま、A/Bはreadyでcompletion partial。証拠は`.artifacts/pr16-agent-smoke/scenario-06/`と`scenario-06-split/`。Behavior / AC identity-unknown placement等の残分岐は未検証で、compositeはpartial。
- Step 9 matrix: 41項目を維持し、Agent証拠に基づく項目3 / 4とsplit contract項目23をPASSへ更新。PASSは1 / 3 / 4 / 5 / 11 / 12 / 17 / 18 / 19 / 23 / 39 / 41の12項目、29項目はPARTIAL、`step9_complete=false`。pure helper test、意味判断、cross-Skill workflowの証拠区分をmatrixに保持し、未検証条件を削除していない。matrixは41項目すべてにagent_judgment_required / deterministic_test_required / validation_route / test evidence / missing conditionを記録し、28項目をAgentと決定論testの両方、13項目を決定論testのみで評価した。計画条件や項目数は変更していない。matrixと全smokeのhash manifestはignored local evidence。
- Step 3 / 7 candidate: SPEC-SEM-003〜007、QUESTION-SEM-003〜004、TR-SEM-003の8候補Markdownをcase inputとSkillから用意し、input copyとcandidate群の102ファイルhashを検証。4 case（SPEC-003 / 007、QUESTION-003 / 004）はhelper validation済み。SPEC-004 / 005は更新元package不足、SPEC-006はretained identity mapping不足、TR-003はcanonical Scope ID不足でruntime適合candidateはblocked。`semantic/run.py`は任意の`--judge-command`を必要とする。Judge provider / endpoint / modelは未選定で、run.pyも実行しておらず、外部送信はない。実際の費用は0、将来費用はmodel選択前のため未算出。run.pyは任意のjudge-commandを起動し、criteria / case input / reference / candidateをstdinで渡す。judge subprocessには親環境変数が継承されるため、認証情報の供給元・secret handling・provider保持条件も未確定。実行前にprovider / endpoint / model、認証方式、送信data範囲、保持条件、cost capの選択・承認が必要。caseはsyntheticで顧客PII / secretは確認されていないが、reference / rubric / input / candidateが送信promptに含まれ得る。
- CI: remote head `8300f56b1f2084c146dd8377a4ecd7d979eb1841`でCode Quality、Agent Skills、Deterministic Output、Semantic Output、Codex Harness（codex-contract / windows-launcher）、CodeQL各languageとstatus checkがすべてsuccess。local `format_tracked.py check`はRuff後にdprint executable不在で完了不能だがremote Code Qualityはpass。local Codex Harnessは31 tests passだが、sandbox内CLI起動拒否でexecpolicy実CLI契約はローカル未検証。remote Codex Harnessはpass。Step 10はStep 3 / 7 / 9未完了のためfinal review未完了。

### 2026-10-14 決定論的残検証の追補

この追補は実行証拠を追記するもので、仕様、検証要求、完了条件は変更しない。

- Python: 既存`.venv`のPython 3.11.9を使用し、依存関係を追加していない。runtime 349 tests pass / Windows symlink privilege skips 2、deterministic shared 12 pass、deterministic repository 290 pass、semantic dataset 22 Skills / 163 cases pass、semantic shared 27 pass / 2 skips、semantic repository 13 pass / 1 skip、qa-workflow routing 2 pass、trigger dataset 1 pass。
- package transaction回帰test: `test_ui_target_package.py` 14 tests pass。update commit後のresponse-loss replayでhelper採番SPEC-003、11_replacement.md追加、10_retained.md retirementを重複適用せず、異なるrequestによる古いsnapshotは`stale_snapshot`で拒否した。create replay、lock holder process kill後のlock再取得もpass。
- not-applicable scopeのdeterministic gateはFIELDだけでなくFLOW / INTERACT / IMPL、UIOP→US→UC→Behavior→ACの一式をrejectする。orphan staging cleanupはinspect / validate / build-machine-evidenceで確認し、既存backup recovery / ambiguous recoveryと組み合わせた。materialize commit時はinspectとMachine Entity readerがcommit前に完全なv00を読み、root→backup期間はwrite lockでfail-closedし、commit後に完全なv01を読める。
- Step 9 matrixは41項目を維持し、25 / 37 / 38 / 40の決定論的完了条件を上記testで確認した。状態は16 PASS / 25 PARTIAL、`step9_complete=false`。41項目すべてにtest / Agent evidenceの区分、証拠path、SHA-256、残条件を記録した。matrixとtest logはignored local artifactであり、PRへ実行ログや候補packageを追加しない。matrixは`.artifacts/pr16-step9-matrix.json`、run recordは`.artifacts/pr16-step9-deterministic/RUN_RECORD.md`（SHA-256 `06d49b1489f5bfb5efaae8f913aa3a3119718ec880c37465d182d4ff472976b5`）、focused test logは同directoryの`ui_target_package_tests.log`（SHA-256 `77f0ce82250b5dace015e72743f3f9b8a556548a58aa18aa9872fa40389cbc5f`）。
- Semantic candidate 8件: SPEC-SEM-003 / 007、QUESTION-SEM-003 / 004の4件はproduction helper / runtime / projectionで引き続き適合。SPEC-SEM-004には更新元package一式とinspect snapshot、SPEC-SEM-005には完全なv03 package / MANIFEST / prior rows / resolved history、SPEC-SEM-006にはlegacy source全文とSPEC-007 / UNK-012 / retired SPEC-008の根拠付きidentity mapping、TR-SEM-003にはAC-101 / AC-102を所有するcanonical Scope IDとupstream Machine Entityがない。別scenarioのstable IDを流用するとidentityを捏造するためruntimeへ渡さず、4件は未適合のままとした。候補SHA manifest `.artifacts/pr16-semantic-candidates/SHA256SUMS.json`を含み、既存Agent smokeと合わせて405個のartifact hashを再検証し不一致0件だった。
- Step 9のAgent compositeはscenario 04（固定順全Skill migration / ownership baseline / qa-workflow final gate）、scenario 05（TRD→TCD→TC→coverage→qa-workflow baseline）、scenario 06（Behavior / AC identity UNKNOWN等の残分岐）が引き続きPARTIAL。前回のruntime fixture testを実Agent証拠へ読み替えていない。semantic candidate生成時のAgent判断とdeterministic helper実行も、semantic Judgeの代用にしない。
- Semantic Judgeは未実行で、外部送信なし、費用0。`semantic/run.py`の任意`--judge-command`はcriteria、case input、reference、candidateをstdinへ送り、親環境変数をJudge subprocessへ継承する。caseはsyntheticでPII / secretは確認されていないが、実行前にprovider / endpoint / model、認証情報の供給方法、data retention、送信対象範囲、cost capの選択・承認が必要。provider未選定のため将来費用は未算出。
- local `format_tracked.py check`はRuffと207 tracked fileのformat確認を通過した後、dprint executableが見つからず完了しなかった（WinError 2）。変更Python fileのRuff check / format checkはpass。push後のhead `84f2f4de9cc3f9660c0d8ce7529a7024e7740e29`でCode Quality、Deterministic Output、Semantic Output、Codex Harnessのcodex-contract / windows-launcher、Agent Skills、CodeQL 3 language jobsはすべてsuccess。Step 3 / 7 / 9未完了のためStep 10最終レビューも未完了。

### 2026-10-15 追加検証

この追補は新しい検証証拠を記録する。Step 3 / 7 / 9の要求と完了条件は変更しない。

- Semantic candidate: SPEC-SEM-003〜007、QUESTION-SEM-003〜004、TR-SEM-003の8件すべてを、production helper / runtime / projectionで再確認し、8/8がruntime適合した。SPEC-SEM-004 / 005 / 006とTR-SEM-003には評価用の合成previous state / canonical identityを明示して用意した。reference、rubric、Judge結果はcandidate生成Agentへ渡していない。候補の217 evidence hashは欠落・不一致0件。manifestは`.artifacts/pr16-semantic-candidates/candidate-manifest.json`（SHA-256 `699230d4529206ef6bf06906e296899c925d6040ef158d2823b3ed45957ba056`）。
- Semantic Judge: 未実行、外部送信なし、費用0。`semantic/run.py --judge-command`はcriteria、case input、reference、candidateをJudge subprocessへ渡し、親環境変数を継承する。provider / endpoint / model、認証情報の供給方法、data retention、送信対象とcost capの選定・承認が必要。Judgeを使わないvalidationやcandidate生成をJudge PASSとして扱わない。
- Step 9 matrix: 41項目と個別要求を維持し、21 PASS / 20 PARTIAL、`step9_complete=false`。項目14は実runtimeで2 MiB超〜16 MiB未満のready-scope batch、16 MiBちょうど、16 MiB + 1 byte拒否を確認。項目16はscenario 05 AgentのAC-002 / TR-002 / SCOPE-002所有判断と、required scope欠落を拒否するartifact runtime testを確認。項目21は全listed CLI error / byte-limit envelopeとunexpected internal error exitを固定するtestを追加。項目27はscenario 08 AgentのUC / Behavior / AC identity UNKNOWN配置3分岐とruntime regressionを確認した。matrixは`.artifacts/pr16-step9-matrix.json`（SHA-256 `bb7a45b75bf1278324f7f7b4465a95e88c57803f6b69a3ca39dc82fb7aab2209`）。matrix、candidate、smoke原本はignored local evidenceであり、このPRへ生artifactは追加しない。
- Python検証: 現在のworking treeでruntime suite 353件PASS、Windows symlink privilegeによるskip 2件。downstream_state suite 11件と、CLI error / UNKNOWN配置 / aggregate size境界のfocused regression 4件もPASS。ログは`.artifacts/pr16-step9-deterministic/runtime-suite-final-2026-10-15.log`、`downstream-state-suite-2026-10-15.log`、`focused-regressions-final-2026-10-15.log`に保存した。
- Step 9 item 6: synthetic required conditional-file scenarioをcurrent Codex sessionで実行した。AgentはFIELD identity既知・validation不明をFIELD-001 blocked + UNK-001で保持し、required TriggerのFLOW identity不明時はFLOW行を作らず、UNK-002へBlocking Scope ID=SCOPE-001とRelated File=04_flows_and_data.mdを記録した。materialize / inspect / validate / build-machine-evidenceが成功し、再実行verifierの22 assertionが通過。input・Agent判断・production helper request/response・生成packageのhashを `.artifacts/pr16-agent-smoke/scenario-09-required-file-gaps/attempt-03/` に保存した（verification SHA-256 `ec0ba2c4b03dd70aaedb26da6d09259579cb8376d8d34eed8a0f0e9708ce982a`、hash manifest SHA-256 `67531155f521316aea78a6bee1d3a1110049670deb94cdd40c5b14e67f2d9edc`）。合成データのみで、下流workflow完了は主張しない。
- Step 9 composite smoke: scenario 04の全Skill固定順migration、全境界cutoverとownership baseline、qa-workflow final gate、scenario 05のTRD→TCD→TC→coverage→qa-workflow completed baseline、scenario 06のUNKNOWN解消・same-ID復帰等は未完了。各シナリオのPARTIALを維持し、決定論testで実Agent条件を代替しない。
- Formatter / CI: `format_tracked.py check`はRuff段階を通過したが、local dprint実行ファイル不在で完了できない。repositoryのCode Quality workflowはdprint 0.55.2を導入してから同じcheckを実行する。通常sandboxからのGitHub接続は拒否されたが、承認レビュー済みread-only接続でremote branch HEAD `37d68bdbe22bbef8fcfe002bcaccfff7b10df0cc`と最新main `dcabbb218cf79f6920f5c8303e60140ab9c15f23`を確認し、mainが対象branchの祖先であることを確認した。変更をpushした後に最新headのCIを再確認する。
- 完了判定: Step 3 / 7はSemantic Judge未実施のため未完了。Step 9は22項目と複合Agent smokeが未完了。したがってStep 10最終レビューとPR全体は未完了。

### 2026-10-15 non-blocking UNKNOWN routing と UI structure UNKNOWN lifecycle

この追補は新しい実装・検証事実を記録する。41項目、仕様、完了条件は変更しない。

- Step 9 item 2: current-session Agentは`spec-analysis`、`question-analysis`、`qa-workflow`のSkillとguidanceを読み、synthetic Scope BのCSV通貨行順UNKNOWNを非blocking、Scope CのSave Goal UNKNOWNをblockingと判断した。production `ui_target_package.py`でv00を作成し、SCOPE-001 / 002をready、SCOPE-003をblockedに保った。`build-machine-evidence`はready scopeだけを受け取った。`question_ids.py`はblockingなUNK-001だけにQ-001を割り当て、synthetic owner answerの後にspec-analysis packageをv01へ更新した。別論点のUNK-002はcurrentのまま、全scopeがreadyとなり、Machine Entity projectionと質問link再検証がpassした。54ファイルのlocal evidence manifestはSHA-256 `0e69ec94555392bb379fd1be871a602010a0590e2493ad5b0473b00d73c94fc9`。入力・Agent判断・helper入出力・packageは`.artifacts/pr16-agent-smoke/scenario-11-nonblocking-unknown/attempt-03/`に保存。fixtureとowner answerはsyntheticであり、実製品の履歴ではない。永続qa-workflow baseline transactionはこのpackage-only要求で必要とせず、実行・主張していない。
- Step 9 item 28: current-session Agentは未分類のsaved-view ellipsisにtyped IDを付けずUNK-002として保持した。synthetic owner clarification後、helperは同じUNKNOWNを解決してPANEL-001を採番し、取り消し後はPANEL-001を明示retireしUNK-002を同じIDで再openした。production helperのinspect / validate / Machine Entity projectionを含む15 assertionがpassした。verification SHA-256 `90b4a1879186690537fb49756d486c91003db4548ac9474252907dd02b51872b`、local artifact manifest SHA-256 `1c39704b03575883eb7383ff4371bdc72d7c95250db03d195715763298ace8e9`。証拠は`.artifacts/pr16-agent-smoke/scenario-10-ui-unknown-lifecycle/attempt-10/`。
- 検証中に`question-analysis/assets/output-template.md`の質問表と質問ID履歴のseparatorがproduction `question_ids.py`のMarkdown契約に不適合と判明した。既定templateをmaterializeできず、該当2 separatorを修正し、template実入力のround-trip regression testを`tests/skills/runtime/test_question_ids.py`へ追加した。既存helper schemaや期待条件は緩和していない。失敗したscenario-11 attempt 01 / 02は残し、PASS証拠にはattempt 03だけを使う。
- current working tree runtime suite: 355 tests PASS、Windows symlink権限による2 testsだけSKIP。log SHA-256 `21aef5c169120d40101548d9a88b47967ed3013314607f3279d9a4af24dcadd9`。question_ids suite 5 PASS、deterministic shared 12 PASS、deterministic repository 290 PASS、UI target routing contract 2 PASS、semantic dataset 22 Skills / 163 cases valid、semantic shared 27 PASS / 2 SKIP、semantic repository 13 PASS / 1 Windows symlink privilege SKIP、trigger 1 PASS、formatter contract 10 PASS、CI patch whitespace contract 3 PASS。変更Python 3 files Ruff check / format check PASS、`git diff --check` PASS。
- Local tooling: `skills-ref` executableはこのsandboxに存在せず、Agent Skills validationはlocal未実施。`format_tracked.py check`のRuff phaseはpassするが、dprint executableはWinError 2で起動できない。formatter契約testとCI patch whitespace testはpass。dprintやskills-refのglobal installは行わず、push後のCode Quality / Agent Skills CIで結果を確認する。
- Step 9 matrixは41項目を維持し、23 PASS / 18 PARTIAL、`step9_complete=false`。matrix SHA-256 `9fc1daf2fcf1118a699a472c8383135603e1b0d9ac3a56fa96303384a1d60f68`。migration全Skill固定順、cross-skill downstream lifecycle、残るidentity / owner経路のPARTIALは維持した。matrixとsmoke raw artifactsはignored local evidenceで、Gitへ追加しない。
- Semantic candidatesは現在も8/8 runtime適合の既存証拠を再利用し、candidateへのreference / rubric / Judge出力の混入はない。Semantic Judgeは未実行、外部送信なし、費用0。Step 3 / 7はJudge未実施のため未完了。
- Step 10の差分・証拠レビューでは新規runtime契約変更はなく、発見したtemplate不整合の修正と回帰testを確認した。Step 9に18 PARTIALが残り、Step 3 / 7も未完了なので、Plan所定のfinal sign-offとPR全体は未完了。最新CIはpush後に確認する。

### 2026-10-15 question-analysis regression commit and local Codex Harness recheck

- `skills/question-analysis/assets/output-template.md` の質問表・質問ID履歴区切りを production `question_ids.py` が受け付ける形式へ修正し、既定templateのmaterialize round-trip回帰testを追加した。runtime regressionを含む変更はcommit `5ba1647d32cbcef15bcf371cf1166eec2d5a86ff`。
- Codex Harnessをローカルで再実行し、31 testsはpassした。`test_execpolicy_cli.ExecpolicyCliTests.setUpClass` はCodex CLIをsandboxから起動できずerrorとなった。versionによるskipや期待値緩和は行っていない。ログはignored local evidence `.artifacts/pr16-step9-deterministic/codex-harness-final-2026-10-15.log`（SHA-256 `91443b87fa8561c9ffef84786e96ae05eacf45be7c76f327770c0b5997064905`）。実CLIのexecpolicy契約と最新remote Codex Harness CIはpush後に別途確認する。
- Step 9 matrixは41項目を維持し23 PASS / 18 PARTIAL、`step9_complete=false`。matrixの検証対象headは上記source/test commit、SHA-256 `367890bc1769f2abe48f860ede82f5ab8ff14fa9b31408d8304eb38c6a6c2eed`。matrixとraw evidenceはignored local evidenceでありGit管理対象へ追加しない。
- Semantic candidateは8/8 runtime適合の既存証拠を再利用する。Semantic Judgeは未実行で外部送信なし。Step 3 / 7は未完了、Step 9に18 PARTIALが残るためStep 10とPR全体の完了判定も未完了。
- Push前のGitHub CI結果はこの変更を含まない。Local formatterのdprint executableと`skills-ref`は引き続き利用不能であり、CI Code Quality / Agent Skills結果で確認する。

### 2026-10-15 Code Quality failureの修正

- pushしたhead `8db1cc453564a38834d4333578514f995a888f6f` のCode Quality CIが失敗した。dprint 0.55.2は短い`ID`列のseparatorを`--`へ再整形し、GitHub Flavored Markdownの3-hyphen delimiterとproduction `question_ids.py`のschema validationに反した。またPlan末尾に改行がなかった。
- CIと同じdprint 0.55.2をignored local `.artifacts/pr16-dprint/`へ一時配置して挙動を再現した。質問一覧と質問ID履歴の`ID` headerにNBSPを置き、parserの既存`.strip()`でheader値を従来どおり`ID`へ正規化することで、dprint後も`---` separatorを保つようにした。helper契約やseparator検証は緩和していない。既定template materialize regressionと `question_ids` 5 testsがpassした。
- dprint 0.55.2でPlan末尾改行と対象templateを整形後、`python scripts/format_tracked.py check`はRuff / dprintともpassし、207 tracked filesは整形済み。runtime suiteは355 pass / Windows symlink privilege skips 2。`git diff --check`もpass。runtime log SHA-256 `f1fe401f509b4c32121eef23289251a9e3992430d67c581eb5a3051e70efb776`。
- Step 9 matrixは41項目、24 PASS / 17 PARTIAL、`step9_complete=false`を維持。item 8のpreflight checkpoint routing smokeを追加。検証対象head `77e492d53a9fbe6e7c61b8435e6e07e7f2863c3a`。ignored local matrix SHA-256 `44a3fe4579a2c544fd4cf87e315059859f509c7617be60d06bc8cacd2ded357d`。raw `.artifacts`をGitへ追加しない。
- Step 9 item 8: current-session Agentは`qa-workflow/SKILL.md`、guidance、production `migration_preflight.py`を参照し、6 synthetic checkpoint inputから5 distinct statusを確認した。`runtime_v2_cutover_required`のTCD `resume`とqa-workflow final baseline action、`ui_target_migration_required`、`scope_ownership_baseline_required`、`scope_ownership_normalization_required`、`partial_progression_ready`をhelper出力どおり追跡し、Agentがversion / phase / ownership / ready scopeを再判断しないことを確認した。verification SHA-256 `c1cf185f034d0d55733730d7651c4d330ffb09f8284bfaaa6f7a9b1ce125ff4e`, hash manifest SHA-256 `43dbf0ee57c8f69ffe8526c1a650765d00e5241a4e526023a3bb9e3dcedaabe8`. Synthetic checkpoint routingだけを対象にし、historical artifact、全Skill migration、final gateの証明には使わない。
- Head `97e6eced95eeda6548abbce16c29a7edc63aacb2` のCIはCode Quality、Analyze、Codex Harness、Deterministic Output、Semantic Output、Agent Skills、CodeQLの全checkがsuccess。修正を含む次のPlan commit push後に、その最新headのCIも再確認する。Step 3 / 7はSemantic Judge未実施、Step 9に17 PARTIALが残るためStep 10とPR全体は未完了。

## 12. 完了条件

- 新Skill追加なし
- mode assets / referenceが存在
- normal spec-analysisとmodeの選択境界が明確
- UI構造のexact分類が確定済み、または分類未確定項目が仮typed IDを持たずUNKNOWNへ閉じている
- versioned complete package契約が定義済み
- package内にcanonical Authority / traceability正本があり、Authority + current ACだけを既存Machine Entity契約へ閉じる
- UNKNOWN answer lifecycleが定義済み
- repo implementation status分離が定義済み
- question-analysisのUNKNOWN lineageがsemantic + production helper + deterministic evalで確認済み
- qa-workflow routing / resumeと#14の3 Skillとの誤routing境界がrouting case / independent candidateで確認済み
- multi-file packageがrepository eval専用projection経由で既存semantic runnerにより評価可能
- version / UNKNOWN件数 / stable ref / MANIFEST / SHA-256 / complete file set / scope blocker / file applicability / ready・blocked scope / completion status / blocked domain row / 0..N Repository確認基準 / behavior hierarchy / current UCの3分類完全性等の定型整合をproduction helperで検証できる
- UI target packageからtest-requirement-designまで進むcanonical artifact workflowではcurrent ACがrequirement-structure-v2でTRまたはDispositionへ閉じ、AC / linked UIOP / scope / 明示linked FIELD-RULE-FLOW-NOTIFY-INTERACT / direct structure + ancestor / linked INF / 親Behavior-UC-US / Authority変更が関連TR freshnessへ伝播し、無関係package row変更は伝播しない。direct modeはknown ID / closureを保証し、AC Entity dependencyが無い場合のAC semantic cross-run freshnessは完了条件にしない。仕様理解packageだけの要求ではAC→TR closure自体を完了条件にしない
- PR #14後の9 Skill-local `runtime_contract.py` がbyte-identicalのままruntime-v2 / entity-state-v2でacceptance_criterionを扱う。spec-analysis v1 Authorityは既存 `authority_entities.py` のfrozen read-only projectionでv2再生成し、TRD / TCD / TC固有cutoverは各Skill-local `runtime_v1_cutover.py`、test-analysis / usability-inspection / wcag-conformance-evaluationのv1保存input integrity検証は各Skill-local `runtime_v1_input_reader.py` に分離される。coverage-analysisはcurrent upstream v2 evidence、qa-workflowは全必要current v2 evidenceが揃った最後にcurrent workflow state / routing inputから再生成し、9 Skillすべてのv1 evidence処置と依存順が `_09` の表どおり一意に決まる
- `artifact:analysis_entities:all` / `artifact:requirement_structure:all` がaggregate 16 MiB root runtimeとして動作し、他の通常generatorの2 MiB上限を広げずにready-scope全件batchを1回で処理できる
- artifact modeのpartial rerunでchanged ACへ依存するscope外TRをcurrent扱いしない
- spec-analysis / question-analysis production helperがSkill package単体で実行可能
- test-target-inspectionへのcurrent UI分岐が維持される
- existing CI / evalが全PASS
- 実Agent smokeがPASS
- current repository counts / docsが同期
- package schema / helper I/O / migration contractが `_06_package-schema-and-helper-contracts.md` と実装で一致
- current version / new stable ID / MANIFEST / hash等、packageから決定論導出できる値をAgentが手作業で再構築していない
- 意味判断を固定するrule engine / generic document framework / ZIP runtimeを追加していない

### 2026-10-15 継続作業結果（TCD migration fail-closed / scenario 13）

- branch `feat/ui-test-target-analysis-profile` のHEAD `b95f198a4430c432242ee0d75b183e636147fc95` で確認した。TCD `runtime_v1_cutover.py` が構造化blocking errorを返す箇所で、`InvalidInput`へ未対応の`issue_type`引数を渡し、`TypeError`から`internal_error`になっていた。TCD helper内の該当例外を`RuntimeErrorBase`へ修正し、out-of-order materializeが`valid=false / cutover_dependency_incomplete / blocking=true`、exit 0でfail-closedする回帰assertionを追加した。共通runtime contractは変更していない。
- Step 9 item 10をcurrent-session Agentで実行した。Agentは`test-condition-design/SKILL.md`を参照し、評価専用の合成summary/detail・CSV/PDF入力からv1 checkpointを用意した。`condition_structure`、TCD cutover、`equivalence_partitions`、`test_data_requirements`、`materialize_coverage`のproduction helperを呼び、途中のmodel / materialize後にresumeが未完了unitだけを再開することと、最終resume、out-of-order拒否を確認した。合成checkpointは実際の過去成果物ではない。実行記録、入力、artifact、検証結果は`.artifacts/pr16-agent-smoke/scenario-13-tcd-migration-phases-agent/`に保持した。
- TCD cutover focused suiteは9 tests PASS、runtime suiteは355 PASS / 2 Windows symlink privilege skips。`python scripts/format_tracked.py check`は207 tracked filesでPASS。`git diff --check`もPASS。
- Step 9 matrixは41項目を保持し、25 PASS / 16 PARTIAL、`step9_complete=false`。matrixの`verification_head`は上記HEADへ同期した。matrix SHA-256は`0fd52e10e5c97963b8cffe4c404e96b118e41be74cbca5d7c4d3c9a956dfd826`。Step 9 item 7、9、13、15、20、22、24、26、29–36などに統合workflow / semantic identity / ownership / provider-nativeなどの未確認条件が残る。matrixと詳細Agent evidenceはignored local artifactであり、このPlan更新だけでは公開・再現されない。
- Semantic candidateは`SPEC-SEM-003`〜`007`、`QUESTION-SEM-003`〜`004`、`TR-SEM-003`の8件がproduction helper/runtime適合済み。SPEC-SEM-004〜006とTR-SEM-003の評価専用previous state / canonical identityは合成fixtureとして明示し、歴史的成果物とは扱っていない。candidate manifest SHA-256は`699230d4529206ef6bf06906e296899c925d6040ef158d2823b3ed45957ba056`で、217件の保存hashを照合した。Semantic Judgeは未実行である。
- Step 3 / Step 7は独立Semantic Judge待ちのため未完了。未承認外部API送信は実施していない。provider / endpoint / model / 認証 / retention / 費用上限の選定と外部送信承認が残る。
- HEAD `b95f198a4430c432242ee0d75b183e636147fc95` の最新CIはAnalyze（3 jobs）、CodeQL、Code Quality、Codex Harness（codex-contract / windows-launcher）、Deterministic Output、Semantic Output、Agent Skills validationがすべてPASS。PR checksで再確認した。
- Step 10最終レビューとStep 9完了判定は、上記PARTIALとSemantic Judgeが残るため未完了。

### 2026-10-15 継続作業結果（Step 9 scenario 14）

- 検証headは`5f6bfd948328378bf903edbf37aa6b39d92fb58c`。Step 9 item 36について、current-session Agentが`spec-analysis/SKILL.md`とUI target guidanceを読み、評価専用の合成入力から「required UI scopeだが操作・画面・UC identityは不明」と判断した。production `ui_target_package.py materialize`はPAGE / UIOP / US / UC / Behavior / ACを捏造せず、zero-UIOP scopeとBlocking UNKNOWNを`valid=true / completion_status=blocked`で保存した。
- 同じrequired scopeからblocking UNKNOWNと参照を除いた対照requestは`valid=false`で拒否された。clarified synthetic branchではproduction helperがPAGE / UIOP / US / UC / Behavior / ACを採番し、scopeをreadyにし、`build-machine-evidence`がcanonical Authority / AC Machine Entity handoffを生成した。各inputとpackageは評価用合成データであり、実際の過去成果物やproject recordではない。
- scenario14のinput、Agent判断、3 request、runtime response、projection、source SHAは`.artifacts/pr16-agent-smoke/scenario-14-required-uiop-unknown-agent/`に保存した。evidence manifest SHA-256は`5d6fc3f470bf0a60dc48f5b19fc19c9ad37e9ce52446cdbbb778f79febdff959`。
- matrix内171件の個別evidence file hashを再照合した。TCD test sourceの変更によりitem 7 / 9 / 11のsource hashが古かったためcurrent hashへ同期し、171件すべて一致することを確認した。matrixのPASS数や未完了条件は変えていない。
- matrixは41項目を維持し、item 36をPASSに更新した。現在は26 PASS / 15 PARTIAL、`step9_complete=false`、`verification_head=5f6bfd948328378bf903edbf37aa6b39d92fb58c`。matrix SHA-256は`3bacf19afad5a7408291a5b5fc0493312c8cfcb694105046c8ef813388585bdb`。残る固定順migration、cross-skill downstream lifecycle、semantic identity / owner経路、provider-native capabilityをPASSへ繰り上げていない。
- HEAD `5f6bfd948328378bf903edbf37aa6b39d92fb58c` のPR checksはAnalyze 3 jobs、CodeQL status、Code Quality、Codex Harness 2 jobs、Deterministic Output、Semantic Output、Agent Skills validationがPASS。code-qualityは207 tracked targetsを確認した。
- Semantic candidateは引き続き8/8 runtime適合。Semantic Judgeは未実施であり、Step 3 / 7と最終Step 10は未完了。Step 9の15 PARTIALも残るためPR全体を完了扱いにしない。

### 2026-10-15 継続作業結果（scope removal runtime / Agent smoke）

この追補は検証・修正結果を記録する。Planの仕様、41項目、Semantic Judgeおよび実Agent smokeの完了条件は変更しない。

- 開始時点はbranch `feat/ui-test-target-analysis-profile`、local / upstream HEAD `f21a7dc4deaf356af1a4b5e5bc69c128353e08c1`。`origin/main` はmerge-baseであり、local branchはmainより444 commit ahead。既存unrelated `.gitignore`差分を保持し、未stageのままにした。
- Scenario 20の実Agent実行で、`downstream_state.py` がproduction `model_key_state`の完全なmetadata rowを拒否し、またTCD scope内の複数runtime resultごとにprevious CI stateを重複処理する不具合を確認した。shared `runtime_contract._state_row_map`を再利用してrowを厳格検証し、CI stateをscope単位で一度だけ適用するよう修正した。`test_downstream_state.py`へproduction-shaped stateと複数runtime-result回帰を追加した。
- Step 9 item 22はPASS。current-session Agentが`test-condition-design` / `qa-workflow` Skill contractを参照し、SCOPE-B removal後も同一意味のTCN-001 / ep-001をSCOPE-001へreuseすると判断した。validated last-active rows 4件、production helper出力、適用後state、qa-workflow materialization gateを確認し、`requires_materialization=true`から`false`への遷移を得た。証拠は`.artifacts/pr16-agent-smoke/scenario-20-scope-removal-agent/attempt-06/`。この結果はscope removalの1経路のみをPASSとし、他のcross-Skill lifecycleは主張しない。
- Step 9 matrixは41項目のまま32 PASS / 9 PARTIAL、`step9_complete=false`。未完了はitem 7 / 9 / 15 / 24 / 31 / 32 / 33 / 34 / 35。matrixとraw smoke artifactはignored local evidenceでGitへ追加しない。
- Semantic candidateは8件をrefreshし、production helper / runtime / projection適合8/8、candidate evidence hash欠落・不一致0件を確認した。candidate manifest SHA-256は`ad6b9d8950560d733d212024dfdf46353e53363fa56bbed4263c966ca3596503`（source/test commit `68179a0bba7392c97357cda799a3934704598d97`でrefresh）。candidate生成時にreference、rubric、Judge結果は渡していない。
- Local validationはruntime 360 pass / 2 Windows symlink privilege skips、修正後focused downstream 12 pass、deterministic shared 12 pass、deterministic repository 290 pass（`PYTHONUTF8=1`を子processへ継承）、semantic validator 22 Skills / 163 cases、semantic shared 27 pass / 2 skips、semantic repository 13 pass / 1 skip、routing 2 pass、trigger 1 pass、`SPEC-OUT-003` 21/21 pass、Hook syntax pass、formatter contract 10 pass、patch whitespace tests 3 pass。既存ignored `.artifacts/pr16-dprint`のCI-pinned dprint 0.55.2 binaryを使い`format_tracked.py check`は207 tracked filesでpassした。
- Agent Skills inline CI structure checkは22 Skill / 488 trigger queryでpassし、CI-pinned official `skills-ref validate`もcanonical 22 Skill + development 3 Skillの25/25 pass（`PYTHONUTF8=1`）。Codex Harnessは31 test pass後、実CLIをsandbox内で解決できず`test_execpolicy_cli` setupがerror（skipなし）。`node --check`はpass。この記録時点ではGitHub APIがsandbox socket policyで拒否されremote CI未確認だったが、後続でpushしたhead `ba4898f3a3eab822f450f0c064815e9b1b4a27db`の全10 checksが成功した。
- Semantic Judgeは未実行、外部送信なし。Step 3 / 7は独立Judge未実施のため未完了。Step 8はremote CI全PASSだがlocal実CLI runtime acceptanceが未確認のため未完了。Step 9は9項目PARTIALが残り、Step 10も未完了。詳細run recordは`.artifacts/pr16-step9-deterministic/RUN_RECORD-2026-10-15-continuation.md`（source/test実行部分のSHA-256 `f928418220824c2aad17a66fc0542289b2f0707ed864b856d16803b2e0bb5ea6`）。

### 2026-10-15 継続作業結果（PR #16 head CI）

- `ba4898f3a3eab822f450f0c064815e9b1b4a27db`（base `dcabbb218cf79f6920f5c8303e60140ab9c15f23`）に対しGitHub上の10 checksを確認し、Code Quality、CodeQL（actions / javascript-typescript / python / aggregate）、Codex Harness（codex-contract / windows-launcher）、Validate Agent Skills、Deterministic Output、Semantic OutputがすべてSUCCESSだった。実行run: [Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38622757506)、[CodeQL](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38622753313)、[Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38622757509)、[Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38622757511)、[Deterministic Output](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38622757423)、[Semantic Output](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38622757512)。
- 個別check結果のローカル証拠は`.artifacts/pr16-final-validation/latest-ci-ba4898f3.json`（SHA-256 `047f32554ed5d22cffbcd858aed128bf300695b3fb940d08c84e259905b480ff`）。このraw evidenceはignored local artifactとして保持し、Gitへ追加しない。
- このCI結果はcommit `68179a0bba7392c97357cda799a3934704598d97`の修正とその後のPlan evidence hash-only commitを含むheadを検証する。local Codex Harnessの`test_execpolicy_cli` setup errorは別の実行範囲として残し、remote CI成功をlocal embedded runtime acceptanceの代替とは扱わない。Step 8はこの未確認条件のため未完了とする。
- Step 3 / 7は独立Semantic Judge未実施、Step 9は41項目中32 PASS / 9 PARTIAL、Step 10は最終レビュー未完了。仕様、検証対象、完了条件は変更していない。PR本文を実装・検証結果とこのCI結果へ同期する。

### 2026-10-15 継続作業結果（zero-scope terminal persistence / current runtime）

この追補は検証・修正結果を記録する。Planの仕様、Step 9の41項目、実Agent smokeとSemantic Judgeの完了条件は変更しない。

- current-session Agentは`test-condition-design/SKILL.md`と`qa-workflow/SKILL.md`を再参照した。scenario 21 attempt-10はscenario 20の評価用completed baselineから開始し、全scope retire後のTCN / model / CI削除をAgent判断とproduction generatorで処理した。`downstream_state.py`のretirement pending/apply gate、TCD condition-structure、materialize-coverage、qa-workflow runtime final gateを実行し、final runtimeは`ready / can_complete=true`となった。
- attempt-09の保存試行は、深いartifact pathでWindowsの`os.link`が`FileNotFoundError`を返し、production helperがfail-closedした。リポジトリ設定やhelperの上限は変更せず、同じfixtureをより短い`.artifacts/pr16-s21-store` rootで再実行した。initial synthetic baselineとzero-scope terminal baselineをlocal immutable storeへcommitし、それぞれexact revisionでstateとartifactを再読込した。binding revision、再読込本文、active scope空集合の一致を確認した。入力の出所はsynthetic evaluation historyであり、製品の実履歴ではない。
- attempt-10ではTRD / test-case-design / coverage-analysisのzero-scope経路を実行していない。このためStep 9 item 32はPARTIALを維持する。item 7 / 9 / 15 / 24 / 31 / 33 / 34 / 35も各記載のcross-Skill migration、freshness、ownership、resume条件が未達であり、PARTIALのままとする。41項目matrixは32 PASS / 9 PARTIAL、`step9_complete=false`。
- 上記実行中に確認したゼロscope terminal stateの不具合を修正した。`requirement_structure.py`と`condition_structure.py`は、zero-scope deletionで生成するTR / TCN / model rowの`scope_refs`を空集合にする。9 Skillの共有`runtime_contract.py`は、TCD zero-scope parent resultに対して前状態から期待されるmaterialize cleanup child unitを導出し、parent terminal stateとの整合を検証する。対応する回帰testはTRD / TCD generator stateとchild resultの欠落・不一致を確認する。
- `downstream_state.py`のfrozen runtime-v2 history readerは、保存済みruntime / generator implementation fingerprintを現行コードfingerprintとの完全一致で判定しない。Plan `_09 §10.27–28`に従い、保存fingerprintのdigest形式を検証し、その保存値からgeneration fingerprintを再計算する。currentnessと過去artifact integrityを分離する回帰testを追加した。
- latest local runtime suiteは既存`.venv` / Python 3.11で362 tests PASS、Windows symlink privilege skip 2件。zero-scope / frozen historyを含むfocused runtime suiteは80 tests PASS。実行ログは`.artifacts/pr16-step9-deterministic/runtime-final-post-zero-scope.log`。Semantic candidateはreference / rubric / Judge結果を生成Agentに渡さず、production helper / runtime / projectionで8/8適合をrefreshした。Semantic Judgeは未実行、外部送信はない。
- 追加の独立検証はdeterministic shared 12 tests、deterministic repository 290 tests、semantic dataset 22 Skills / 163 cases、semantic shared 27 tests / 2 Windows symlink privilege skips、semantic repository 13 tests / 1 skip、qa-workflow routing 2 tests、trigger 1 test、official `skills-ref validate` 22 canonical SkillsがPASS。`python scripts/format_tracked.py check`は207 tracked files、`git diff --check`もPASS。各実行ログは`.artifacts/pr16-step9-deterministic/`に保持した。
- local Codex Harnessは31 testsがPASSした後、`test_execpolicy_cli.ExecpolicyCliTests.setUpClass`がCodex CLIをsandboxから解決できずERRORとなった。versionによるskipや拒否の迂回は行っていない。このローカル実CLI契約は未確認であり、過去headのremote CI PASSで代用しない。ログは`.artifacts/pr16-step9-deterministic/codex-harness-local-final.log`。
- Scenario 21 attempt-10のrequest、response、state、immutable artifact、verification、およびhashは`.artifacts/pr16-agent-smoke/scenario-21-zero-scope-terminal-agent/attempt-10/`と`.artifacts/pr16-s21-store/`にある。manifestは36ファイルのSHA-256を記録する。これらはignored local evidenceであり、Gitへ追加していない。
- Step 3 / 7は独立Semantic Judge待ちで未完了。Step 8はローカルの実CLI execpolicy runtime受入が未確認のため未完了。Step 9は9項目PARTIALのため未完了。Step 10最終レビューもこれらの未達が残るため未完了。既存remote CI結果を今回の未push差分のCI結果とは扱わない。

### 2026-10-15 継続作業結果（zero-scope修正head CI）

- commit `192f165034920c3345b9bb9a89678543b24b40bf` のGitHub checksは10/10 SUCCESS。Code Quality、CodeQL（actions / javascript-typescript / python / aggregate）、Codex Harness（codex-contract / windows-launcher）、Validate Agent Skills、Deterministic Output、Semantic Outputが成功した。
- 実行run: [Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38630538998)、[CodeQL](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38630534351)、[Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38630540160)、[Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38630539005)、[Deterministic Output](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38630538994)、[Semantic Output](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/38630539117)。
- local `test_execpolicy_cli` setup errorは別範囲のままであり、CI successでsandbox内CLIアクセスを確認済みとは扱わない。Step 8はlocal runtime受入条件が未確認のため未完了。Step 3 / 7のSemantic Judge、Step 9の9 PARTIAL、Step 10も未完了。

### 2026-10-15 継続作業結果（TRD zero-scope / shared-scope pause-resume）

この追補は現在の検証証拠だけを追加し、Step 9の41項目、意味仕様、完了条件を変更しない。

- 開始時のlocal / remote PR headは`d6582c2606f6937b94d61aa184652778accdc3b6`。GitHub上の最新`main`は`dcabbb218cf79f6920f5c8303e60140ab9c15f23`であり、PR headはmainから449 commit ahead / 0 behindだった。ローカルの既存`.gitignore`変更は未stageのまま保持した。
- Semantic candidate manifestは8件すべてproduction helper / runtime / projectionに適合している。current sourceの最終コード変更はancestorの`192f165034920c3345b9bb9a89678543b24b40bf`で、以後はPlanのみの変更である。candidate manifest SHA-256は`5c185ccccb7b2e5010044f5e4fd2d823b086b9c9156e02c96637ea3b8adfcfaf`。candidate生成時にreference、rubric、Judge結果を渡していない。これはSemantic Judge PASSではない。
- Step 9 item 32ではscenario 22がproduction `requirement_structure.py`を実行し、全scope retire後のTR-001 / TR-002を`deleted`、`scope_refs=[]`、current Entityなしとして検証した。既存scenario 21のTCD terminal / qa-workflow commit・refetchとは別実行であり、TRD / TCD / TC / coverage-analysis / qa-workflowを一つの履歴で通した証拠ではないためitem 32はPARTIALを維持する。scenario 22 manifest SHA-256は`40c9b9e7aaa9bcc10b36d42e1567c296f83e818d5e728ca63c5e6de74f8986c0`。
- Step 9 item 15ではcurrent-session Agentが`test-condition-design` / `qa-workflow` Skillとworkflow guidanceを読み、評価専用A/B共有TCN-001 / ep-001の意味を変えずに再利用すると判断した。B blocked時は両scope共有EntityとCIをinactiveに保ち、再開時には同じTCN / model / CI IDsを復元した。`condition_structure.py`、`equivalence_partitions.py`、`materialize_coverage.py`、`workflow_runtime.py`を実行し、qa-workflow ready、blocked中のlast-completed binding保持、再開後のlocal baseline commitとexact revision refetchを確認した。実行記録は`.artifacts/pr16-agent-smoke/scenario-23-blocked-shared-scope/attempt-05/`、manifest SHA-256は`e131dd14c1ed9dfb7b91f6f59532c4b39af9d5c1371c636ccdf80263fc8ed7f8`。これはsynthetic baselineであり、TRD / TC / coverage-analysisの統合やB-only owner lifecycleを検証していないためitem 15はPARTIALのままとする。
- 同じsynthetic committed artifactに対し、attempt 06はB retire後のowner resolutionをproduction `downstream_state.py`へ渡した。Agentは変更後もSCOPE-Aに適用される同一Entityをreuseと判断し、helperは検証済みlast-active A/B snapshotとSCOPE-Aへのtransitionを返した。`requires_materialization=true`でowner generator未適用の状態を停止できたが、B-only inactive historyからの復旧、owner generator適用、欠落historyのAgent経路は未検証のためitem 33はPARTIAL。manifest SHA-256は`5d944ed6dfb692e14497d9229f47463cb79502cc2ace26b09c3c8b960105872a`。
- 関連する既存runtime testsはTRD 9、TCD 7、TC 8、traceability 12の計36件を個別実行してすべてPASSした。inactive identityの再有効化、zero-scope state、scope-removal applied-state gate、missing last-active history fail-closedは既存runtime testsにも含まれ、この作業では重複testを追加していない。証拠は`.artifacts/pr16-step9-deterministic/item32-focused-runtime-2026-10-15/`にある。
- 41項目matrixは32 PASS / 9 PARTIALのまま。未完了itemは7 / 9 / 15 / 24 / 31 / 32 / 33 / 34 / 35で、matrix SHA-256は`9c27938d2c9fd72c664e86289c0588a02b87929c7680006c794a613383a8fa62`。matrix、synthetic input、execution artifact、hash manifestはignored local evidenceであり、PRには含めない。再実行に必要なlocal入力と各hashはmatrixおよび上記artifact directoryに記録した。
- PR head `d6582c2606f6937b94d61aa184652778accdc3b6`のGitHub CIは10/10 SUCCESSだった。今回のPlan追補commit後のCIはpush後に別途確認する。Semantic Judgeの外部送信は行っていない。Step 3 / 7は未完了、local Codex CLI execpolicy acceptanceが未確認のStep 8も未完了、Step 9は9 PARTIALのためStep 10最終レビューも未完了とする。

### 2026-10-15 検証環境再確認

- current code head `d6582c2606f6937b94d61aa184652778accdc3b6`、Python 3.11.9でruntime 362 tests（Windows symlink privilege skip 2）、deterministic shared 12、deterministic repository 290、semantic dataset 22 Skills / 163 cases、semantic shared 27（skip 2）、semantic repository 13（skip 1）、trigger 1、UI target routing 2を個別実行し、すべてPASSした。deterministic repository suiteのsystem Python実行はPyYAML不足で失敗したが、既存`.venv`内のPyYAML 6.0.3を使って成功した。依存は追加していない。
- `skills-ref validate`はcanonical 22 + development 3 Skillsの25/25、Ruff 0.16.8、dprint 0.55.2と207 tracked file formatter、formatter contract 10、patch whitespace 3、Hook `node --check`、`git diff --check`がPASSした。Windows localeの影響を避けるためskills-ref実行時だけ`PYTHONUTF8=1`を指定した。
- Codex Harnessは31 testsが成功した後、`test_execpolicy_cli` setupでCodex CLIをsandboxから解決できずerrorとなった。実CLI version差によるskipや別経路起動は行っていない。このためStep 8 local runtime acceptanceは未確認。
- Semantic candidate 8件はすべてruntime適合。manifest配下272 candidate / evidence fileのSHA-256を再照合し、missing / mismatchは0件。candidate manifestは`5c185ccccb7b2e5010044f5e4fd2d823b086b9c9156e02c96637ea3b8adfcfaf`。
- Step 9 matrix 41項目の既存証拠590行はすべて存在しhash一致。新しいAgent scenarioは今回追加していないため、32 PASS / 9 PARTIALを維持した。current matrix SHA-256は`9c27938d2c9fd72c664e86289c0588a02b87929c7680006c794a613383a8fa62`。詳細はignored local run record `.artifacts/pr16-step9-deterministic/RUN_RECORD-2026-10-15-validation-refresh.md`（SHA-256 `f763247cc30bb6808e202f1ef40fcde97f969ab4feaf08a79f4ddf9d0b57f557`）。
- Semantic Judgeは実行しておらず、外部送信はない。Step 3 / 7は独立Judge待ちで未完了。Step 9の9項目PARTIALを維持し、Step 10最終レビューも未完了とする。

### 2026-10-15 同一UC内の枝別impact検証

- current-session Agentが`test-analysis` Skillのchange-impact契約を読み、評価用の合成入力でUC-001配下のUIOP-A / Behavior-A / AC-A / TR-AとUIOP-B / Behavior-B / AC-B / TR-Bを別identityとして扱った。Aだけを変更対象にしたproduction `skills/test-analysis/scripts/change_impact.py`の実行結果はUIOP-A / BH-A / AC-A / TR-Aのみで、B側と共有UCはimpact集合に含まれなかった。
- 対応する`tests.skills.runtime.test_test_analysis_change_impact`を個別再実行し、2 tests passed。request、helper response、Agent判断、verification、test logとhash manifestは`.artifacts/pr16-agent-smoke/scenario-24-same-uc-branches/attempt-01/`にある。manifest SHA-256は`bded7ea6f3c110d2e26a9547a70c9eb9cf3e95ffcddc1a5c992dd43922068e14`。
- matrix item 24はPARTIALのまま。artifact-mode Machine EntityでAC-A / TR-Aのstale遷移とAC-B / TR-Bのcurrent維持、およびpersisted baseline比較が未確認である。41項目は32 PASS / 9 PARTIALを維持し、`step9_complete=false`。matrix SHA-256は`3b3d1ea13a704c49cdd2ec105cfb332ce2480b15525dfa685c6873a186895254`。
- 仕様、検証条件、完了条件に変更はない。Step 3 / 7のSemantic Judge、Step 8 local Codex CLI acceptance、Step 9の他8 PARTIAL、Step 10 final reviewは未完了。Judge向けcandidate / referenceの外部送信は行っていない。

### 2026-10-15 Scenario 31: all-blocked baseline retention and B-only resume

- current-session Agentが`qa-workflow` routingと`test-condition-design` Skillを確認し、合成A/B completed baselineをimmutable revisionからexact-refetchした。両scope blocked時は`ready_scope_ids=[]`として下流Skill runtimeを起動せず、`downstream_state.py`のinactive projection後もlast-completed bindingが同一であることを確認した。
- Bだけを再開する際は、committed baselineから検証したinactive historyをTCDへ渡し、同じ`TCN-001` / `ep-001`をreuseしつつcurrent ownershipを`SCOPE-002`だけにした。`condition_structure.py`、`equivalence_partitions.py`、`materialize_coverage.py`、`workflow_runtime.py`がreadyとなり、B-only baseline commitとimmutable artifact exact-refetchまでPASSした。
- deterministic suitesを独立実行: migration preflight 9 passed、qa-workflow baseline 7 passed / Windows symlink privilege 2 skipped、test-condition structure 7 passed。実Agent / helper evidenceは`.artifacts/pr16-agent-smoke/scenario-31-both-blocked-b-resume/attempt-06/`、hash manifest SHA-256 `5c072748145408f156023ae9842ea1d443347470791380fa411754550ffc51eb`。Windowsの長いnested artifact pathでatomic createが失敗した試行は保持し、短いworkspace-local storeで標準helperを使って再実行した。sandboxやsecurity設定は変更していない。
- matrix item 31をPASSに更新。Step 9は41項目中33 PASS / 8 PARTIAL、`step9_complete=false`、未完了item 7 / 9 / 15 / 24 / 32 / 33 / 34 / 35、matrix SHA-256 `4cc5c13e240f83570d10e96b120818df22d76838462e431127cbb9f3bbfa614d`。この更新は検証結果の反映であり、41項目や完了条件の変更ではない。
- item 31の残条件はない。他のStep 9 PARTIAL、Step 3 / 7 Semantic Judge、Step 8 local Codex CLI acceptance、Step 10 final reviewは未完了。外部Judgeへのcandidate送信はしていない。

### 2026-10-15 Scenario 33: B-only inactive-history owner resolution

- item 31でcommit / exact-refetchしたB-only qa-workflow baselineをproduction `downstream_state.py`へ渡した。B blocked時はSCOPE-BだけがTCN-001 / ep-001 / CI01–02をinactiveへ移し、validated inactive historyにB-only last-active contentを保持した。intermediate blockedではcompleted bindingを変更していない。
- B retire後、current scope Aだけを指定したproduction preflightは、immutable baselineからremoved SCOPE-Bと4 affected entitiesのlast-active contentを抽出した。AgentはB専用条件に他scopeのownerがないためTCN-001 / ep-001をdeletedと判断し、helperはCI childrenもdeletedへ導いた。generatorへの適用前に`requires_materialization=true`を維持した。missing materialize historyのfail-closed testも含む`test_downstream_state` 12件を個別実行して全件PASS。
- synthetic Agent/helper request、response、owner判断、verification、hashは`.artifacts/pr16-agent-smoke/scenario-33-b-only-inactive-retire/attempt-01/`、manifest SHA-256 `0d22610f47275b5f8dfc65c19843e67ffb323a2f2ef6c9ae1d63373abdef2f45`。item 33をPASSとし、41項目は34 PASS / 7 PARTIAL、未完了 item 7 / 9 / 15 / 24 / 32 / 34 / 35、`step9_complete=false`。matrix SHA-256 `9ecd0e74ffee86a8d2f3aefb9d5b59d183d32261581c7795d8feeb4fdeecd826`。
- item 33のowner source / fail-closed条件は完了。generator適用そのものはitem 22のthree-phase testで別途検証済み。全scopeのTRD/TCD/TC/coverage cross-Skill chain等、他7 PARTIALは残る。Semantic Judgeと外部送信は未実施。

### 2026-10-15 Scenario 32 / 35 follow-up

- item 32では、current-session Agentが`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`qa-workflow`のSkillを参照し、全scope retireを意味判断した。TRD / TCD / TCのzero-scope helper、coverage terminal projection、qa-workflow final gateとproduction verifierは成功した。synthetic terminal artifactはlocal baselineへcommitし、stateとartifact revisionを再読込して一致を確認した。focused testはTRD 9、TCD 7、TC 8、coverage 12、qa-workflow 7 passed / Windows symlink privilege 2 skipped。
- item 32のactive baseline作成attemptではTRD / TCD / TCがreadyになったが、coverage-analysisは`missing_authority_or_risk_edge`および`orphan_node`でunresolvedとなった。Authority / Risk関係を評価入力にないまま追加してbaselineを成立させることはせず、このattemptはcompleted baseline証拠に採用しない。zero-scope terminalとrefetchは確認したが、同じ完成済みcross-Skill TRD / TCD / TC / coverage baselineからterminal transitionまで通したことは未証明のためitem 32はPARTIALを維持する。synthetic input、全request / response、verifier、commit / refetch、focused logsはignored local evidence `.artifacts/pr16-agent-smoke/scenario-32-integrated-zero-scope/attempt-01/`と`.artifacts/pr16-step9-deterministic/item32-integrated-zero-scope-2026-10-15/`に保存した。attempt-01 manifest SHA-256は`8e16d7074f9dd09080628026d8bbb2ac31a52dad419986536e8b203b6a2ff3f7`。
- item 35ではAgentが、readyのままcontentだけ変更されたAC-Aに依存するscope外TR-001はstaleにし、未変更AC-B / TR-002はcurrentに保ち、inactiveでfreshness違反を隠さないと判断した。production `change_impact.py`はAC-A / BH-A / TR-A / UIOP-Aだけを返し、shared runtime `evaluate_entity_freshness`はTR-001を`upstream_entity_fingerprint_mismatch`でstale、TR-002をcurrentとした。change-impact 2 tests、stale carry-forward 1 test、CI inactive / zero-terminal history 2 testsはそれぞれPASS。artifact-modeのcommit済みbaseline比較と、inactive / deleted CI historyからの同一Agent reactivation sequenceは未検証のためitem 35はPARTIALを維持する。証拠はignored local evidence `.artifacts/pr16-agent-smoke/scenario-35-ac-content-freshness/attempt-01/`、manifest SHA-256 `ac7da0f5d815ead8a15fa4614ef8853d7b7c87fc597e5a98cc99b20bb036ce19`。
- item 24はscenario 35のcurrent Machine Entity freshness evidenceを追加したが、artifact-mode test-requirement-designとpersisted baseline comparisonが未検証のためPARTIALのままとする。検証対象41項目、完了条件、責務境界は変更していない。matrixは41項目中34 PASS / 7 PARTIAL、`step9_complete=false`。最新の対象コードは`360f45ddde3a42766c97ad9f65c6a718848b9c0a`で、matrixの既存evidence rowと今回のlocal evidenceを照合した。
- Step 3 / 7 Semantic Judgeは未実行で外部送信なし。Step 8のsandbox内Codex CLI execpolicy runtime acceptanceも未確認。Step 9は7項目PARTIAL、Step 10 final reviewは未完了。`.artifacts/`証拠とmatrixはignored local dataで、PRへ追加しない。

### 2026-10-15 Scenario 15 / 24 / 32 / 35 verification refresh

- 現在のlocal source headは`6551d85ca26d27bcbc186748d17c1392a03bf111`。working treeには`downstream_state.py`と対応runtime regression testの未commit差分があり、root `.gitignore`には今回の作業と無関係な既存`.venv`差分がある。後者は対象外として保持する。
- item 15はsynthetic A/B baselineを使い、B blocked時にB依存TR / TCN / model / CI / TCをinactive化、A entitiesのcurrent維持、history保持、intermediate binding不変、同じidentityの復元、TRD→TCD→TC→coverage→qa-workflow final gate、completed baseline commit / exact refetchを再確認した。verification SHA-256 `1fb6d2f0319556b0ac8ef7f851f133f7f340c37586a1b48468a190ba1697bf97`、manifest SHA-256 `bfd27c7b0440a9bfa22122db53b90876889dac8c291b8005814c389380a7a6c8`。item 15はPASS。
- item 24はsynthetic packageでAC-001だけを更新し、AC-002 fingerprint維持、production test-analysis / TRDを実行した。TR-002はAC-001 / R-001依存fingerprintによりstale、TR-001はcurrentを維持した。qa-workflowはstale TCD / TCを理由にunresolvedとなり、前のcompleted bindingは変更されずexact-refetchされた。これは期待するfreshness gateである。verification SHA-256 `c77961f7936353398634e0c8a2e0ea8568e14d41102788cb208588c28ba1719b`、manifest SHA-256 `76b221f2cdb3e1a5bbf6671e22ecde58a0289de350e1dc483ff1a609db3e62af`。item 24はPASS。
- item 32では、attempt-03のexact-baseline retryがproduction `downstream_state.py`の`requires_materialization=true`で止まった。保存済みQA artifactにcurrent CI rowsが不足していたため、scenario 15のcompleted A/B baselineを別storeへ複製し、TCD production verifierが出した2つのmaterialize runtime rowとCI ID stateを各該当scopeへ反映して`workflow_runtime.py`を再実行した。Authority / Risk / TR / TCN / model / CI / TC / coverage参照が整合し、qa-workflowはready / can_completeとなった。active baseline revision `sha256:839d2d616c80ce5d64326cb108990c1c4761a79c6336f59ba763e16e44919a7b`をcommit / exact-refetchした。別storeへそのstateとimmutable artifactを複製した後、current scopeを空にし、Agentが明示retirementの意味を判断してTRD→TCD condition/materialize→TC→coverage→qa-workflowの削除専用経路を実行した。各independent verifier、applied-state materialization gate、zero-scope final gate、terminal commit / exact-refetchはPASS。terminal artifact SHA-256 `3565b4bb5f4f5dae2b14361e9e7cd1ae43835dd5be1473105df1492ba0b5c8d3`。統合manifest SHA-256 `0973669ab5fa4aea93dff53107541544aef0d12730dd32335411ede253bf37be`。attempt-03失敗証拠は保持し、後続の正しいCI projectionを含むcurrent baselineからterminal成功を確認したためitem 32はPASS。
- item 35のattempt-02はTCD production runtimeとindependent verifierで削除済みCI IDの再利用を拒否し、CI01/02→CI03/04、CI01→CI02を確認した。ただしこの履歴はitem 24のartifact-mode freshness / committed baselineと接続されず、TC / coverage / qa-workflowまで伝播してbaselineを再保存していないためPARTIAL。
- Step 9 matrixは41項目、37 PASS / 4 PARTIAL（7 / 9 / 34 / 35）、`step9_complete=false`。matrix SHA-256 `392db8e412a4a61c02de3a2644d54cf139c5ff30758c2b459989a44a7616346b`。詳細な検証file hashはignored local `.artifacts/pr16-step9-validation-2026-10-15/final-review/current-review.json`（SHA-256 `5ff835b2cab0d20556ffdde482ad001fbf67431ea911a0926a4bfc1e521a339b`）と`.artifacts/pr16-agent-smoke/common-baseline/attempt-02/sha256.txt`（SHA-256 `0973669ab5fa4aea93dff53107541544aef0d12730dd32335411ede253bf37be`）を参照する。
- Step 3 / 7の独立Semantic Judgeは未実施で、評価データの外部送信も行っていない。Step 8 local Codex CLI runtime acceptanceはsandbox identityからの`codex.cmd`アクセス拒否で未確認。remote CI / PR headの再取得はGitHub APIとremote socketへのnetwork denialにより不能。Step 10は未完了。Planの仕様、41項目、完了条件は変更していない。

### 2026-10-15 残検証の最終再確認

- Step 9 matrixは41項目中37 PASS / 4 PARTIAL（7 / 9 / 34 / 35）。item 15 / 24 / 32のPASSはそれぞれの保存revision内で検証済み。item 7 / 9 / 34 / 35は既存Agent subscenario、production helper、deterministic testを照合したが、要求される連続した全Skill経路は未成立である。単独のPASSや異なるhistoryを連結してPASSにしない。
- `skills/qa-workflow/scripts/downstream_state.py`で同一aggregate TCD / CI stateのscope間重複をdeduplicateし、競合を拒否する。inactive TCNのmaterialize runtime結果も全TCD scopeから検索し、同じidentityの結果が異なる場合をfail-closedにした。対応回帰を含む`tests.skills.runtime.test_downstream_state` 16件PASS、runtime suite 366件PASS / Windows symlink privilege 2件skip。
- `python scripts/format_tracked.py check`、対象Ruff、`git diff --check`はPASS。formatterはexisting `.venv` とignored `.artifacts`内のdprint 0.55.2 binaryを一時的なcommand PATHで実行した。
- local Codex CLI確認ではsandbox identity `MYCOMPUTER\CodexSandboxOffline`から`Get-Command codex`が解決せず、インストール済み`codex.cmd`へのアクセスが拒否された。`test_execpolicy_cli` class setupがerrorとなり、`execpolicy check`実CLI assertionへ到達していない。Step 8は未確認。
- 作業開始時のlocal headと最後に取得済みtracking refは`6551d85ca26d27bcbc186748d17c1392a03bf111`。runtime / test差分はlocal commit `081197565e54ab21b452dd18aea51f068026dd7f`、push結果のPlan記録はlocal commit `fbf134e`にある。通常pushは`github.com:443`のconnection failureで完了せず、これらのcommitはremote branchへ届いていない。PR body / latest CIはGitHub APIとremote socketのnetwork denialで取得不能のため未更新・未確認。権限・sandboxの迂回はしていない。
- Semantic Judgeは未実行で外部送信なし。Step 3 / 7 / 8 / 9と、それらを含むStep 10は未完了。仕様、41項目、完了条件を変更していない。
