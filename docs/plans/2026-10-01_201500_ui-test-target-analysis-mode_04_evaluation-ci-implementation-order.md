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
- UI操作ありと確定したscopeは意味モデル上requiredのまま維持する。影響するUIOP / US / UC / Behavior / ACがblockedならworkflow readinessではそのscopeだけblockedとする。ACはsemantic identityが同じならcurrent ↔ blockedでstable IDを維持し、意味上廃止された場合だけretireする。semantic identity自体が未確定ならstable ID rowを作らず、07のBlocking Scope ID / 関連Fileへ閉じる
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

| LLM責務 | semantic case |
| --- | --- |
| SPEC / DECISION / INFERENCE / UNKNOWN分類・Authority競合 | 既存SPEC-SEM-001 / 002、SPEC-SEM-003 / 004 |
| PAGE / STATE / VIEW / MODAL等の意味分類 | SPEC-SEM-003 |
| scope UI操作有無 / 条件付きfile trigger / scope blocker判定 | SPEC-SEM-003 / 007 |
| US / UC / Behavior / AC分解と正常 / 準正常 / 例外 | SPEC-SEM-003 |
| semantic identity reuse / new / explicit retire | SPEC-SEM-005 / 006 |
| repository差分の意味 | SPEC-SEM-004 |
| same-UNK reopen / new UNK | SPEC-SEM-005 |
| legacy semantic mapping | SPEC-SEM-006 |
| extension fileの必要性・意味 | SPEC-SEM-006 |
| DEC / ASM owner判断 | SPEC-SEM-007 |
| 04 / 05責務境界 | SPEC-SEM-007 |
| required domainの意味上の母集団網羅 / content incomplete | SPEC-SEM-003 / 007 |
| repository baseline / implementation-only freshness | SPEC-SEM-004 |

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
- skills/spec-analysis/scripts/ui_target_package.pyの `inspect / validate / materialize` と内部allocator / version / README / MANIFEST / lifecycle / impactを実装。create / legacy-migrationはhelper内部でSkill-local assetからstaging初期化し、snapshotはhash identityだけ保持、derived tracking / refsはmaterializeが再parseする
- `prose_updates[]` はassetに存在するstandard exact heading本文だけを置換する。新規heading作成 / rename / deleteを許可しない
- canonical table cell encode、complete file set、sibling staging / backup、preflight orphan recovery、commit直前snapshot再照合、package単位切替 / rollbackを実装
- `ui_target_package.py` 内部だけにfixed sibling process lockを追加し、POSIX `fcntl.flock` / Windows `msvcrt.locking` の標準ライブラリ実装で同一packageをsingle writer化する。PR #14のclaim / reservation / CAS helperはpackage writeへ使わず、generic lock serviceも作らない
- canonical materialize request fingerprintとMANIFEST `Last materialize receipt` を追加し、commit後response前crashでも同一request replayが前回のID / extension割当・retire結果を返してmutationを再適用しない。createは事前inspect不要、updateはreceipt不一致時だけprevious snapshotを要求する
- normative rowのAuthority / UNKNOWN traceability、domain rowのhelper-derived state、Scope / Blocking Scope / 関連File、scope readiness、UIOP→UC scope一致、UNKNOWN lifecycle、extension lifecycle、Repository確認基準をvalidateする
- versionを `^v[0-9]{2,}$`、数値+1、最低2桁zero padding、上限なしに固定する。新設structural IDも最低3桁・上限なし、既存canonical IDは3桁契約を維持する
- legacy / unversioned packageに加え、通常spec-analysis単一成果物 → ui-target-v1 migrationを同じsemantic mapping + materialize経路で扱う

このStepではshared runtime versionをまだ変更しません。Machine Entity bridgeを含むruntime依存部分はStep 2で同時に成立させます。

### Step 2: runtime schema transition / AC bridge / requirement-structure-v2を原子的に反映

このStepは1つのruntime schema transitionとして扱い、`runtime-v2 / entity-state-v2` だけ先行した中間状態を完成checkpointにしません。

- PR #14後の9 Skill-local `runtime_contract.py` をbyte-identicalに更新し、`acceptance_criterion` / `acceptance_refs` / spec-analysis expected ACを追加
- `RUNTIME_CONTRACT_VERSION: runtime-v1 → runtime-v2`、`ENTITY_SCHEMA_VERSION: entity-state-v1 → entity-state-v2`。v1 validatorが `acceptance_criterion` を受理しないためentity type追加をschema意味変更として扱う
- envelope shape / freshness algorithmは維持
- independent `runtime_validator.py`、active code / Skill文書 / asset / fixture / repository testをv2へ同期
- active Machine Evidenceの手書き擬似schemaを削除し、runtime renderer / authority_entities.py / build-machine-evidence生成結果を正本にする。packageへのMachine Entities section書込みはmaterialize内部だけで行い、standalone build-machine-evidenceはread-onlyとする
- `authority_entities.py` の既存 `{authorities:[...]}` CLIを維持したまま、legacy移行用の排他的入力 `{source_artifact_markdown:"..."}` を追加する。exactly one `Machine Entities: spec-analysis` v1 blockをfrozen `entity-state-v1` 規則で検証し、各Authority Entityのcanonical `content`だけをcurrent v2 `build()`へ渡す。v1 `content_fingerprint` / dependency / wrapperはcarry-forwardせず、block missing / invalid時はhuman-readable table parserへfallbackせず通常spec-analysis semantic rerunを要求する
- `ui_target_package.py build-machine-evidence` を実装し、AC / Behavior / UC / USの明示 `関連構造ID` からlinked domain item、linked UIOPの `対象構造ID` と明示UI structure refからstructure + ancestor、linked INFをAC contentへ固定projectionする。同一PAGE / Scope等の逆引きを禁止する。Authorityだけdependency Entityとする。package-global callはready / blocked scope ID indexだけ、batch callはcurrent ready scope全件を `_06 §9.3` で内部projectionしてAuthority / current AC / Machine Entity / expected identityを1集合へunion / dedupeする
- `skills/test-analysis/scripts/analysis_entities.py` / `skills/test-requirement-design/scripts/requirement_structure.py` は既存 `artifact:*:all` runtime unit identityを維持したまま `run_cli(..., aggregate=True)` へ変更し、root input上限を16 MiBにする。transport上限を `input_mode` で分岐するwrapperは追加せず、この2 root unitはdirect / artifactとも同じ16 MiB上限を使う。その他の通常generatorは2 MiBを維持する
- generator contractを `requirement-structure-v1 → requirement-structure-v2`。top-level `acceptance_criteria[]` を `{ac_id, authority_refs[]}` のknown semantic AC集合としてraw input必須にし、各TRのsemantic `acceptance_refs[]` も必須とする。UI target packageからTRDへ進むcanonical workflowはartifact modeに固定し、upstream AC Entity集合とのexact一致 + AC/Authority dependency + semantic freshnessを要求する。direct modeはknown ID/closure検証を保証し、実在する参照AC Entityだけdependency化する。AC Entityなしdirect runのAC semantic cross-run freshnessは保証しない
- current ACをTRまたはDispositionへ閉じ、Authority closureは独立維持する
- TR EntityへAC EntityとACが参照するcurrent Authority Entity dependencyを保存する
- shared runtimeへSkill固有migration projectionを入れない。新規 `skills/test-requirement-design/scripts/runtime_v1_cutover.py`、`skills/test-condition-design/scripts/runtime_v1_cutover.py`、`skills/test-case-design/scripts/runtime_v1_cutover.py` がcomplete v2 generator inputを決定論生成する
- 各cutover helperはstdlib + 同Skill current `runtime_contract.py` だけをimportするが、v1 source artifactはhelper内のread-only legacy readerで `runtime-v1 / entity-state-v1` のfrozen schema / fingerprintを検証し、current v2 validatorへv1 Entityを渡さない。通常generatorへfield mergeを要求しない。TRD / TCはall、TCDはcondition-structure → models反復 → test-data-requirements → materialize-coverageのphase契約を持つ
- cutover外側stdinはhelper固有decoderでaggregate 16 MiBを許可し、top-level artifact Markdownだけ64 KiB string上限を免除する。embedded v1 JSON scalarは通常64 KiB、各v1 runtime JSON blockは旧2 MiB上限で検証する。current `strict_loads()` のverify専用例外を流用せず、cutover契約からgenerator上限を変更しない。別途ready-scope root runtime契約として `analysis_entities.py` / `requirement_structure.py` だけaggregate 16 MiBへ変更し、その他の通常generatorは2 MiBを維持する
- 内容不変cutoverでTR / TCN / model / CI / TC stable identity、deleted / inactive historyを維持する
- 既存v1 downstream artifactがある場合は `spec-analysis Authority v2再生成 → test-analysis v2再生成 → TRD → TCD → TC v2 full rebuild → coverage-analysis v2再生成 → 必要なusability-inspection / wcag-conformance-evaluation v2再生成 → qa-workflow final gate v2再生成 → UI target package migration / AC生成 → TRD通常semantic update → stale downstream通常再実行` の依存順に固定し、逆順をblockedにする
- v1 downstreamがない場合は直接UI target package migration / normal v2 workflowへ進める
- `_09` の9 Skill処置表どおり、TRD / TCD / TCだけstable identity cutover helperを使う。test-analysis / usability-inspection / wcag-conformance-evaluationにはSkill-local read-only `runtime_v1_input_reader.py` を追加し、pre-cutover baselineのfrozen v1規則で保存済みRuntime Input / Result pairのintegrityを検証してsemantic inputだけを返す。readerはcurrentnessを判定せず、v1 runtime metadata / dependency / fingerprint / Entityをv2へcarry-forwardしない。test-analysisはcurrent v2 upstream Entityとのidentity / content fingerprint整合後にv2 full rerun、usability-inspection / wcag-conformance-evaluationは既存artifact graph / handoff / evidence currentnessが成立する場合だけv2 deterministic rerunし、不成立なら通常rerun / re-observationへ戻す。coverage-analysisはcurrent upstream v2 evidence、qa-workflowはcurrent workflow state / routing inputから常に再生成し、保存v1 Runtime Inputを再利用しない。proseからinputを再構築しない
- artifact modeでUIOP / UIOP-only Authority / scope / 明示linked domain item / AC chain・UIOP・domain item由来structure + ancestor / linked INF / 親Behavior-UC-US / Authority変更によるAC / TR freshness regressionを追加し、同一PAGE / Scopeにあるだけで明示参照されないdomain item変更のnon-stale regressionも固定する。direct modeはAC Entityなしでこのsemantic freshnessを要求しない
- shared runtime 9-copy byte-identity、cutover helper portability、v1/v2混在拒否、semantic drift、phase dependency、mapping ambiguityをrepository integration testで固定する
- spec-analysis v1 Authority projectionはcanonical v1 wrapper / Entityの`schema_version=entity-state-v1`、skill / entity_type / entity_ref、content fingerprint、空dependency、`content.authority_id == entity_ref`をfrozen規則で検証し、valid v1 → v2 Authority再生成、改変v1 → reject、missing block → semantic rerunをrepository testで固定する
- 3つの `runtime_v1_input_reader.py` はpackage単体compile / portabilityを確認し、valid baseline v1 pairからsemantic inputを抽出できること、Input / Result identity・runtime-v1 version・generator contract・input/model/generation fingerprint・dependency・baseline implementation fingerprintの改変をrejectすることを固定する。readerがcurrentness=trueを返す契約は作らない
- test-analysisはreader出力からcurrent v2 dependent runtimeをfull rerunし、`analysis_entities` のmachine-owned result fieldをv1からcarry-forwardせずcurrent v2 resultで再構築する。current upstream Entity identity / content fingerprint不一致では保存input再利用を停止する
- usability-inspection / wcag-conformance-evaluationはreader成功だけでは保存inputを再利用せず、既存artifact graph / handoff / evidence currentnessが確認できた場合だけv2 runtimeを再実行する。currentness不明・不一致、reader invalid / missingは通常rerun / re-observationへ固定する
- coverage-analysis / qa-workflowはvalidなv1保存inputが存在しても再利用せず、それぞれcurrent upstream v2 evidence / current workflow state・routing inputからv2 evidenceを再生成する回帰を固定する
- `analysis_entities.py` / `requirement_structure.py` のaggregate root regressionとして、2 MiB超〜16 MiB以下のcanonical request成功、16 MiB + 1 byteの `limit_exceeded`、その他の通常generatorで2 MiB + 1 byteが従来どおり `limit_exceeded` になることを固定する
- legacy readerが改変v1 fingerprint / dependencyをrejectし、64 KiB超のtop-level artifact Markdownは16 MiB以内なら受理、artifact内scalarの64 KiB超はrejectするtransport回帰を固定する
- requirement-structure-v2 artifact回帰: semantic `acceptance_criteria[]` とcurrent upstream AC Entity集合のexact一致、参照AC + AC Authority dependency、missing Entity fail-closedを固定する
- requirement-structure-v2 direct回帰: upstream AC Entityが0件でもsemantic `acceptance_criteria[]` からknown ID / closureを検証でき、存在しないAC / AC由来Authority Entity dependencyを合成しない。AC EntityなしではAC本文 / 親chain変更のcross-run freshnessを保証しない。参照AC Entityが実在する場合だけAC dependencyを追加し、そのdependencyには既存freshnessを適用する

### Step 3: spec-analysis evaluation

- SPEC-SEM-003〜007を更新し、UI操作あり + Actor/Goal不足、identity未確定blocking UNKNOWN、non-blocker UNKNOWNを残したscope部分進行、Trigger required + content incomplete、required domainの無言欠落防止、通常spec-analysis→mode migration、外部owner対象外境界を含める
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
- helper unit / portability test、deterministic mapping、question semantic caseを追加

### Step 5: qa-workflow routing

- mode request routing / answer resume。小規模でも継続利用目的ならmodeを優先し、`scope_readiness[] / ready_scope_ids[]` を使ってblocked scopeを除外し、current ready scope全件を `build-machine-evidence(scope_ids=ready_scope_ids)` の1 batchへまとめて後続 `artifact:*:all` runtimeへ進める。blocked scopeのUNKNOWNをAgentが全件filterしない
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
- inspect snapshot → materialize → explicit retire lifecycle
- legacy vNN / unversioned packageとnormal spec-analysis single artifactのmigration fixture
- package migrationとruntime cutoverの相対順integration test

### Step 7: deterministic / semantic boundary validation

- semantic identity、explicit retire、same-UNK/new-UNK、file trigger、extension要否、DEC/ASM owner、UI分類、US/UC/Behavior/AC分解、AC→TR対応をscriptが決定していないこと
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
- runtime-v1 downstream → spec-analysis v1 Authority projection / v2再生成 → test-analysis v2再生成 → TRD/TCD/TC Skill-local cutover → coverage-analysis v2再生成 → 必要なusability-inspection / wcag-conformance-evaluation v2再生成 → qa-workflow final gate v2再生成 → UI target migration → AC semantic update → stale downstream rerunのscenario。coverage-analysis / qa-workflowは保存v1 inputを使わない
- 64 KiB超のv1 artifact Markdownを含むcutover requestが16 MiB以内で成功し、v1 fingerprint改変 / embedded scalar 64 KiB超をrejectするscenario
- artifact modeでUIOP / UIOP-only Authority / scope / structure ancestor / 明示linked domain item / linked INF / Behavior / UC / US / Authority変更によるTR staleと、同一PAGEにあるだけで未参照のdomain itemを含む無関係package row変更non-stale scenario
- ready scope A/BのAuthority分離、共有Authorityのbatch内dedupe、UI操作なしscopeのAuthority handoff、blocked scope非混入をready-scope batch smokeで確認する。既存 `artifact:analysis_entities:all / artifact:requirement_structure:all` をscopeごとに複数回起動しない
- package-global build responseがscope full payloadを複製せず、ready-scope batch runtime requestが2 MiBを超えても16 MiB未満なら既存 `artifact:analysis_entities:all / artifact:requirement_structure:all` を1回だけ起動して完遂できるscenario。16 MiB exactly / 1 byte超過の境界値はrepository testで固定する
- AC-001がcurrent → blocked → currentへ戻ってもstable IDを維持し、blocked期間はAC Entity / TRD handoffから外れ、既存TRがmissing dependency / staleになるscenario
- required scopeで0 UIOP + blockerなしをreject、0 UIOP + identity未確定Blocking UNKNOWNをpartial/blocked保存、完全なUIOP→US→UC→Behavior→AC closureをreadyにするscenario
- 同一packageへの2 process materializeがpackage-local OS lockで排他され、commit後response前crash後の同一request replayがMANIFEST receiptから二重new ID / extension / retireなしで完了できるscenario。create replay、update replay、別requestのstale拒否、lock holder process kill後の再取得も確認する
- process kill相当のorphan staging / backupをpreflight recoveryでき、一意に復旧不能ならfail-closedするscenario
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
## 12. 完了条件

- 新Skill追加なし
- mode assets / referenceが存在
- normal spec-analysisとmodeの選択境界が明確
- UI構造分類が定義済み
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
