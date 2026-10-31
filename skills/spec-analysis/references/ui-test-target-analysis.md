# UIテスト対象分析モード

このreferenceは、テスト設計前に継続利用する対象理解packageを作成・更新する場合のspec-analysis契約です。通常の単発仕様分析は既存の`assets/output-template.md`と通常ガイダンスを使います。単にMarkdownを要求されたことだけではmodeを選びません。

## 起動条件と目的

次のいずれかに該当する場合にこのmodeを選びます。

- テスト設計へ進まず、仕様理解・対象整理を完了成果物として残す
- 複数の仕様資料、Q&A、決定事項、既存の対象理解packageを継続的に統合・更新する
- UI構造、状態、業務ルール、入力制約、通知・外部連携、UNKNOWN、実装状況を相互参照できるpackageが必要
- 通常spec-analysisの単一成果物を、同じ意味IDを保って継続packageへ移行する

このmodeはspec-analysisの条件付き出力です。新Skill、別Authority、テスト要求、テスト条件、テストケースを作りません。packageの実データは案件側のartifactとして保存し、このrepositoryへ書き込みません。

## 責務と情報源

- Authorityの優先順位、用語、対象範囲は案件コンテキストと既存spec-analysis契約に従い、このmode独自のsource順位を作りません。
- `SPEC / DECISION / INFERENCE / UNKNOWN`、Current Effective Authority、source、解消関係の正本は`09_authority_and_traceability.md`です。他fileの行は09のstable IDを参照します。
- repositoryや既存QA成果物は補助証拠です。project contextが明示的にAuthorityと指定しない限り、repository実装、live UI観測、usability finding、WCAG resultを仕様Authorityへ昇格させません。
- 実装との差分は`08_repository_implementation_status.md`へ分けます。確認していないRepositoryのbranch / revision / 確認時点はcarry-forwardし、現在値へ推測更新しません。
- 質問への回答は`question-analysis`で正式決定、更新済みAuthority、承認済みASM、または未確定として正規化した後に反映します。

## packageの選択とfile構成

package schemaは`ui-target-v1`、内容revisionは`vNN`です。required core payloadは`README.md`、`00`、`01`、`02`、`06`、`07`、`09`、`CHANGELOG.md`です。`MANIFEST.md`は必須control fileです。`03`、`04`、`05`、`08`はScopeごとのTriggerからhelperが導出し、必要なfileだけをpackageへ含めます。10以降は00で宣言した案件固有extensionだけを許可します。

standard fileのheading集合とstructured tableはassetsの固定schemaを使い、headingの追加・削除・renameはしません。extensionは自由記述Markdownであり、独自tracking tableやstable ID prefixを追加しません。後続QAの判断、期待挙動、test design、freshnessへ影響する情報をextension proseだけに閉じ込めず、09または03〜05のstandard rowへ正規化します。

## 分析手順

1. 対象、scope、実際に利用できるAuthorityと正本一覧を特定します。範囲や根拠が足りず判断できない場合は推測せず、既存の停止条件を適用します。
2. 情報源、SPEC / DECISION / INFERENCE / UNKNOWN、Current Effective Authorityを09へ整理します。通常のspec-analysisと同じAuthority解決を適用します。
3. ScopeごとにUI操作の有無を意味判断します。`あり → Behavior Decomposition=required`、`なし → not-applicable`、`未確定 → blocked`はhelperが固定対応で生成します。
4. UI構造を意味分類します。PAGE、STATE、VIEW、STEP、MODAL、BROWSER-DIALOG、PANEL、POPOVER、GLOBAL UI、EXTERNAL、SHARED PAGEのexact種別を安全に決められるときだけtyped rowを作ります。構造の存在は分かるが種別が未確定なら仮種別・仮prefix・IDを作らず、07にUNKNOWNを記録します。後続を止める場合は該当Scopeを`Blocking Scope ID`にします。分類解決後に同じUNKNOWNをresolveし、そこで確定したtypeのnew IDを割り当てます。
5. routeが不明なら`PATH-TBD`を使えます。操作フローだけからsame-routeを推定せず、STATEは独立状態軸として記述します。STATEの`状態軸`は必須、その他の種別では空です。
6. Scopeごとに03 / 04 / 05 / 08のTriggerを`あり / なし / 未確定`で意味判断します。helperがそれぞれ`required / not-applicable / blocked`を導出します。Triggerはfileが担当する情報の適用性を表し、UI操作や同じScopeにあることだけから決めません。03はfield、制約、validation等、04は複数step / state transitionに必要なI/O、生成処理、data transformation、非同期process / state flow等、05は通知、browser dialog、user-visibleなdownload delivery、外部destination / interaction等、08は利用するrepository evidenceを扱います。単純な既存fileの選択・downloadは05の対象であり、それだけでは04の業務flow rowを作らず、04を`required`にしません。入力に明記された保存・検証・状態遷移等の業務flowがあれば04を適用します。生成・変換が未確定なら、その事実を04の`Trigger判定=未確定`と同一論点のUNKNOWNで表し、既知のdownload deliveryを05から落としません。未確定なのは影響を受けるfileのTriggerだけに局所化し、該当fileを`blocked`にして同じ論点のUNKNOWNをScopeへ結びます。identityが分かるdomain rowはblocked + UNKNOWNで保持します。identity自体が分からずrowを出せない場合だけ、07のBlocking UNKNOWNにScopeと関連fileを記録します。
7. 入力資料から識別できるFIELD / RULE / FLOW / NOTIFY / INTERACTを無言で落としません。05が適用されるScopeでは、入力に明記されたuser-visibleなdownload deliveryや外部interactionを05の対応する標準rowへ記録します。UIOPはユーザー操作を表し、INTERACTはdelivery / external interactionを表すため、downloadでは責務に応じて両方を保持できます。04と05へ同一の生成・変換内容を重複記載しません。domainの意味上の母集団と必要性はLLMが判断し、helperの構造closureは意味上の網羅性を代替しません。
8. UI操作ありのScopeではUS → UC → Behavior → ACを完全に意味分解します。UI操作なしはnot-applicable、未確定はblocked + UNKNOWNです。US / UC / Behavior / ACのsemantic identity、new / reuse / explicit retire、正常 / 準正常 / 例外の意味分類はLLMが判断します。
9. current Behaviorごとに意味上関係するmapped UIOPを`関連操作ID`で1件以上明示します。同じUC、PAGE、Scopeにあるだけでは関連付けません。ACへのlinked UIOPは親Behaviorの`関連操作ID`からだけ導出されます。
10. current UCは正常 / 準正常 / 例外を各1行で説明します。`定義あり`はcurrent Behaviorへつなぎ、`なし`はcurrent Authorityと理由を持たせます。`未定義`にはUNKNOWNを結び、対象Scopeをblockedにします。
11. child identityを特定できないときは階層ごとの配置に従います。UC identity不明は親USをblockedにしてUCを作らず、Behavior identity不明はUCの該当完全性を`未定義 + UNKNOWN`にしてBehaviorを作らず、AC identity不明は親BehaviorをblockedにしてACを作りません。これらをScopeだけへ退避しません。
12. semantic identityが既知のrowがancestor blockerの影響を受ける場合は同じstable IDのままblockedにします。helperはancestor状態を子へ伝播し、ancestor由来だけのUNKNOWNを子へ複製しません。意味上の廃止だけを明示retireします。
13. repository evidenceを使う場合は08の確認基準をRepositoryごとに保持します。確認したRepositoryだけを更新し、他Repositoryのbaselineや実装rowを変えません。
14. test設計へ先回りせず、明示された期待挙動、制約、状態、根拠、未知事項をpackageへ閉じます。

## stable IDとUNKNOWN lifecycle

stable identityと同一論点の再利用はLLMが判断します。新規ID番号、exact prefix選択、重複、参照、現在状態、Markdown serializationは`ui_target_package.py materialize / validate`が決定します。AgentがIDを手で採番したり、既知ID一覧から番号を計算したりしません。

- package-owned IDはrequest-wideに割り当てられます。新規row間の参照には`@draft:<draft_key>`を使えます。
- UI構造・通知 / 外部連携・分析項目のprefixはそれぞれ`種別`または`分類`からhelperが選びます。callerの`primary_prefix`は渡しません。
- `DEC / ASM`は正本ownerが発行したcanonical IDを使い、package helperは採番しません。初回取込だけ`identity_action=external`、以後は`reuse`です。packageから外れてもowner IDをterminal retireしません。
- UNKNOWNの同じ論点は同じUNK IDでreopen / 再解決します。別論点だけ新規UNKです。current UNKNOWNは07と09で一致し、resolved historyは09に残します。
- `retire_ids[]`はpackage-owned identityだけに使います。過去retired IDは再利用できません。

legacy移行では、入力にある全stable identityを意味単位で照合し、current identityのretained mapping、新しいidentity、明示retireを分けます。retired IDは正確なIDを`legacy_lifecycle_events[]`へ渡し、helperが生成するCHANGELOGのStable ID changesに`<exact-id> | retired`として残します。「retired identity event」のようなIDを特定しない要約だけでは不十分です。retired IDをcurrent Authority / Machine Entityとして残さず、同じ番号を新しい意味へ割り当てません。materialize後は、current table、CHANGELOG、MANIFESTとsemantic projectionを照合し、retired IDが正確に記録されていることを確認します。

## materialize前の意味crosswalk

canonical writeの前に、各current Behavior / ACについて、意味上依存するFIELD / RULE / FLOW / NOTIFY / INTERACTを対応付けます。package schemaの`関連構造ID`欄は、Plan `_06`の契約上、UI構造IDに加えて該当domain item IDを明示参照できます。関連するdomain itemはその欄へstable IDまたは`@draft:<draft_key>`で直接加えます。関連を同一Scope、Authority、画面、UIOPから推測したり、helperに意味上の対応付けをさせたりしません。関連しないdomain rowは無理に結び付けず、その意味上の理由を判断します。helperの`build-machine-evidence`が返す`linked_domain_items`が空の場合は、意図的な非関連を確認してから続行します。

各Scope・条件付きfileのTrigger判定は、canonical writeの前にapplicability matrixとして一度に見直します。各判定に根拠となる入力・Authorityを対応付け、`あり / なし / 未確定`と関連UNKNOWNを一致させます。「download / export」と書かれていることだけで04を`あり`にせず、生成・変換・集計等が未確定なら04のTriggerも確定しません。逆にdownload actionが明記されているのに、download / external-interactionを扱う05を無言で`not-applicable`にしません。表の出力後は`ui_target_package.py inspect`でhelperの導出結果がAgentの根拠判断と一致することを確認し、不一致なら意味判断へ戻します。

## 作成・更新の実行

### 新規作成

1. 必要なら`ui_target_package.py inspect`で既存packageを確認します。create自体は事前inspectを必須としません。
2. Skill-local assetsをhelperがstagingへ展開します。Agentがtemplateをcopyしてpackageを作りません。
3. source、Authority、scope、semantic identityを確認したうえで`materialize`へsemantic updatesを渡します。形式不備やsemantic quality gate不通過のcandidateをcurrentへcommitしません。
4. helperの`validate`が構造、参照、file applicability、UNKNOWN、Behavior closure、Machine Entity、version、MANIFESTを検証した後だけ全packageを切り替えます。

### 更新

1. `inspect`を呼び、そのresponseの`update_snapshot`をそのまま保持します。snapshotはpackage version、payload hash、MANIFEST hashだけを含むため、callerがderived indexを再構成しません。
2. package全文をcurrent stateとして読み、既存stable identityを意味判断して`reuse`、新規を`new`、明示廃止を`retire_ids[]`へ分けます。package更新は差分fragmentではなく完全版です。
3. `table_changes[]`、必要な`keyed_table_updates[]`、`prose_updates[]`、extension更新を一度の`materialize` requestへ渡します。新旧IDの対応や未確認のrepository evidenceを落としません。
   - `table_changes[]`の各tableは、該当する`assets/ui-test-target-analysis/*.md`にある完全な固定header配列を順序も含めてそのまま指定します。一部の列だけをheadersとして送らず、各rowも全列分のcellを持たせ、値がない列は空cellにします。
   - 同じrequestで作成するrow間のstable ID参照は、対象cellへ`@draft:<draft_key>`を使います。helperが割り当てるstable IDを推測・採番して参照しません。既存rowの参照はpackageに存在する正確なcanonical IDを使います。
4. no-opならversionとpackage bytesを変えません。user-managed payloadまたはcurrent変更概要が変わる更新だけ`vNN`を1つ進めます。README controls、MANIFEST、generated lifecycle差分だけを変更原因にしません。
5. stale snapshot、参照不整合、意味更新が必要な状態はhelperのblocked issueに従い、現在packageを壊しません。同じrequestのcommit後replayはMANIFEST receiptで二重適用を防ぎます。

helperは同じpackage rootへの`inspect / validate / build-machine-evidence / materialize`で同じpackage-local process lockとrecoveryを使います。lock不可、stale update、commit / recovery失敗をLLM補完で成功扱いしません。

## scope readinessと次工程

helperはcurrent Scope集合から`current_scope_ids[]`、`ready_scope_ids[]`、`blocked_scope_ids[]`、`scope_readiness[]`、`completion_status`を導出します。`valid`はschema / referenceの構造妥当性でありcompletionとは異なります。構造validなblocked packageは保存できます。

blocking UNKNOWNのない局所UNKNOWNだけでScopeやpackage全体を止めません。UNKNOWNの影響を受けるrequired fileやrequired rowが`blocked`なら、そのUNKNOWNを「non-blocking」と説明してScopeをready扱いしません。known rowはcurrentのまま保持できますが、Scope readinessは`inspect`が返す派生状態と説明を一致させます。`not-applicable`や別Scopeへの切り分けは、入力根拠がある場合だけ選びます。blocked scopeがあってもready scopeは進められます。`current_scope_ids[]`がnon-emptyでreadyが0件なら全blockedとして後続runtimeを起動せず、最後のcompleted baselineを維持します。Scopeが0件になった場合はUI target packageだけからdownstream terminal cleanupを判断せず、`qa-workflow`へ返します。

`build-machine-evidence`を使ってcanonical handoffを生成します。

- `scope_ids=null`はpackage-global Authority + current AC Entityとscope indexを返し、scope別full payloadを重複しません。
- `scope_ids`には全current `ready_scope_ids[]`を渡します。helperがseed / explicit edgeからscopeごとに固定projectionし、Authority / AC / Machine Entity / expected identityをunion・dedupeした1 batchを返します。Agent / callerはscope別結果をmergeしません。
- blocked、unknown、duplicate scope IDの指定や、ready集合の一部だけのcanonical dispatchは拒否します。
- current UNKNOWN、blocked AC、package-local stable IDの衝突を隠して複数packageのEntity blockをmergeしません。

下流test-requirement-designへ進む場合はcanonical artifact modeを使い、current ACをTest Requirementまたは明示Dispositionへ閉じます。ACの対応だけでAuthority closureを代用しません。ACから必須になるScope ownershipやfreshnessはhelper / runtime契約に従います。仕様理解packageだけを要求された場合は下流closureへ進みません。

## legacy migration

schemaなし、通常spec-analysis単一成果物、legacy version付きpackageはcurrent `ui-target-v1`として直接validateしません。LLMがsemantic identityとretained / new / explicit retired mappingを決め、`materialize(change_mode=legacy-migration, artifact_mode=create)`へ渡します。helperが`v00`またはlegacy source versionからのnext version、stable ID、canonical file、CHANGELOG、README、Machine Entity、MANIFESTを一括生成します。proseだけからsemantic IDやscopeを推測復元せず、曖昧なmappingはblockします。

## Skill境界

- 現在の実画面名・到達方法・ふるまいを観測する必要がある → `test-target-inspection`
- 保存済みFigma / screenshotの使いやすさを評価する → `usability-evaluation`
- live browserで使いやすさ、focus、responsive、feedbackを検査する → `usability-inspection`
- formal WCAG-EM適合性評価を行う → `wcag-conformance-evaluation`
- UNKNOWNを質問・回答正規化する → `question-analysis`
- テスト重点を決める → `test-analysis`

current UI observationをAuthorityへ自動昇格せず、各Skill固有の保存、browser/session、WCAG procedureを複製しません。

## 出力前品質確認

canonical write前に意味品質を判断します。identity、Authority、期待挙動、scope、Trigger、unknown lifecycle、extension要否、Behavior hierarchy、linked UIOPを確認し、意味不明の状態を`not-applicable`やhelperへ委ねません。その後、`ui_target_package.py validate`で機械検査します。helperが返す形式 / 参照エラーは意味判断の代わりではなく、semantic updateへ戻る根拠として扱います。
