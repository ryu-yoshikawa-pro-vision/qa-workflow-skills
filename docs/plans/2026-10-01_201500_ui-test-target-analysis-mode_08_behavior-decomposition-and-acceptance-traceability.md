# UIテスト対象分析モード: behavior decomposition / acceptance traceability

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

関連Plan:
- 2026-10-01_201500_ui-test-target-analysis-mode_02_spec-analysis-package.md
- 2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md
- 2026-10-01_201500_ui-test-target-analysis-mode_06_package-schema-and-helper-contracts.md
- 2026-10-01_201500_ui-test-target-analysis-mode_09_runtime-entity-and-test-requirement-contracts.md

この文書は、UI操作を伴う対象に対する User Story / Use Case / Behavior / Acceptance Criteria の分析手順、完全性、下流traceabilityの正本です。

目的はテストケースを早期生成することではありません。仕様をテスト設計へ渡す前に、UI操作の目的・利用シナリオ・振る舞い・受入可能な結果を安定した意味単位へ分解し、切り分け漏れとLLMごとの分割ぶれを減らします。

## 1. 適用契約

behavior decompositionの適用単位はpackage全体ではなく、`00_scope_and_context.md`で確定した分析対象機能scopeです。

Scope ID:
- `SCOPE-001` から開始し、最低3桁で連番採番する。`SCOPE-999` の次は `SCOPE-1000`

各scopeについて次を判定します。

| UI操作判定 | Behavior Decomposition | 扱い |
| --- | --- | --- |
| あり | required | US → UC → Behavior → ACを実施 |
| なし | not-applicable | UIOP / US / UC / Behavior / ACを作らない |
| 未確定 | blocked | UNKNOWNを作成し、適用可否を推測しない |

UI操作の有無自体はLLMが資料の意味から判断します。`Behavior Decomposition` はその結果から `あり → required / なし → not-applicable / 未確定 → blocked` とhelperが決定論生成し、LLMへ別判断として入力させません。ID形式、UNKNOWN参照、下位tableの有無もhelperが決定論検証します。

`資料不足でUS / UC / Behavior / ACを書けない` はnot-applicableの理由になりません。Behavior Decomposition=blockedのscopeでは下位UIOP / US / UC / Behavior / ACを確定済みとして生成せず、関連UNKNOWN解消後にrequired / not-applicableを再判定します。

UI操作ありと確定したscopeは意味モデル上 `Behavior Decomposition=required` のまま維持します。Actor / Role、Goal、操作対象、結果等の下位情報がAuthorityから確定できない場合は、影響するUIOP / US / UC / Behavior / AC rowを `blocked + 関連UNKNOWN ID` で表現します。ACもsemantic identityが既知なら同じ `AC-xxx` をblockedで保持し、解消後に同IDをcurrentへ戻します。semantic identity自体を確定できずrowを発行できない場合は、07のCurrent UNKNOWNに `Blocking Scope ID` と `関連File=02_behavior_and_business_rules.md` を明示します。

ここで `Behavior Decomposition=required` は適用状態でありworkflow readinessではありません。blocked下位row、identity未確定のblocking UNKNOWN、current UCの `判定=未定義` 等が残る間、そのSCOPEは後続工程に対してblockedです。scope-level `Behavior Decomposition=blocked` はUI操作有無そのものが `未確定` の場合だけです。

UI操作には少なくとも次を含みます。
- button / link / menu / tab等による操作
- form入力 / 選択 / submit
- modal / dialog内操作
- upload / download開始操作
- 検索 / filter / sort / pagination
- drag / drop、toggle、selection等の直接操作
- 複数PAGE / VIEW / STEPをまたぐユーザーフロー
- UIから開始する外部遷移 / external interaction

ユーザー操作を起点としない自動更新、session timeout、非同期処理完了表示、push / system notification、自動redirect、background processingの結果表示等はUS / UCを無理に作りません。該当するstate / behavior / business rule / notification / external interactionとして通常のspec-analysisへ残し、Authorityからtest-requirement-designへ進めます。not-applicableはテスト対象外を意味しません。

## 2. 分析順序

UI操作を含むscopeでは、次の順序を省略しません。

1. current Authorityと未解決UNKNOWNを確定する
2. UI構造（PAGE / VIEW / STATE / MODAL等）を整理する
3. scopeごとのUI操作母集団を抽出する
4. Actor / Roleと達成目的をUser Storyへ整理する
5. 各User StoryからUse Caseを識別する
6. 各current Use CaseをBehaviorへ分解する
7. 各current Use Caseについて正常 / 準正常 / 例外の3分類を全て確認する
8. 各current BehaviorのAcceptance Criteriaを定義する
9. US / UC / Behavior / ACをcanonical Authorityへ追跡する
10. 情報不足をUNKNOWNへ閉じる
11. deterministic helperでID / parent / scope / completeness / referenceを検証する
12. semantic quality gateで切り分け漏れ・過剰分割・意味重複・仕様創作がないか確認する
13. current ACをtest-requirement-designへ渡す

未解決UNKNOWNが存在しても、影響しないscopeまで全体停止しません。UNKNOWNの影響scopeだけをblockedにし、独立して確定できるscopeは分析を継続します。

test requirement / test condition / test caseをこの工程内で作りません。

## 3. UI操作一覧

User Storyへ進む前に、required scopeのUI操作母集団を明示します。

#### UI操作一覧

| 操作ID | Scope ID | Actor / Role | 対象構造ID | 操作 | 関連仕様項目ID | 対応UC ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

ID: `UIOP-001` から開始し、最低3桁で連番採番する。999の次は1000

状態:
- mapped
- blocked

規則:
- mapped: **AC freshnessでいうcurrent UIOP**。対応UC IDが1件以上、関連UNKNOWN IDは空
- blocked: 対応UC IDは空を許可し、関連UNKNOWN IDが1件以上必須
- `対象構造ID` は `_05` のUI構造ID exact prefix集合だけを許可する。FIELD / RULE / FLOW / NOTIFY / INTERACTを入れず、同一PAGE上のdomain itemをhelperが逆引きしない
- UIOPからdomain itemへの意味リンクは新しい列を追加せず、必要な場合は親US / UC / Behavior / ACの `関連構造ID` にLLMが明示する
- `状態` はcaller入力ではなく、helperがfield充足と `関連UNKNOWN ID` から `mapped / blocked` を導出する
- 既知のUI操作を無言で落とさない
- 同一操作が複数UCに関係する場合は意味上必要なUCを全て参照する
- 操作の目的 / 結果をこの表で再定義しない。目的はUS / UC、結果はBehavior / ACを正本とする

### 3.1 current / blocked rowのfield契約

blocked rowは「semantic identityまでは確定しているが、完成に必要なfieldが未確定」の場合だけstable IDを持ちます。semantic identity自体を確定できない場合はIDを発行せず、親scopeまたは既知の親rowからUNKNOWNへ閉じます。identityの同一性判断はLLM、下記のfield充足はhelperが検証します。

| row | current / mappedで必須 | blockedで必須 | blockedで空を許可 | IDを発行しない条件 |
| --- | --- | --- | --- | --- |
| UIOP | Scope ID、Actor / Role、対象構造ID、操作、関連仕様項目ID、対応UC ID。関連UNKNOWN IDは空 | Scope ID、操作、関連UNKNOWN ID。Actor / Role・対象構造ID・対応UC ID・関連仕様項目IDは確定済み分だけ保持 | Actor / Role、対象構造ID、対応UC ID、関連仕様項目ID | LLMがscope内の操作identity自体を区別できない |
| US | Scope ID、Actor / Role、Goal、関連仕様項目ID。関連UNKNOWN IDは空 | Scope ID、Actor / RoleまたはGoalの少なくとも一方、関連UNKNOWN ID。確定済み関連仕様項目IDは保持 | Actor / RoleまたはGoalの未確定側、関連仕様項目ID | LLMがActor / Goalの組としてUser Story identityを確定できない |
| UC | 関連US ID、Use Case、Trigger、Success Postcondition、関連仕様項目ID。Preconditionsは該当なしなら空可。関連UNKNOWN IDは空 | 関連US ID、Use Case、関連UNKNOWN ID。Trigger / Preconditions / Success Postcondition / 関連仕様項目IDは確定済み分だけ保持 | Trigger、Preconditions、Success Postcondition、関連仕様項目ID | LLMが親USに対するUse Case identityを確定できない |
| Behavior | UC ID、関連操作ID1件以上、結果分類、振る舞い、Postcondition / Result、関連仕様項目ID。関連UNKNOWN IDは空 | current UC ID、結果分類、振る舞い、関連UNKNOWN ID。関連操作ID / Postcondition / Result / 関連仕様項目IDは確定済み分だけ保持 | 関連操作ID、Postcondition / Result、関連仕様項目ID | Behaviorの存在・identity自体を確定できない |
| AC | Behavior ID、Acceptance Criteria、current SPEC / DECISION / approved ASMの関連仕様項目ID。関連UNKNOWN IDは空 | currentまたはblocked Behavior ID、関連UNKNOWN ID。Acceptance Criteria / 関連仕様項目ID / 関連構造IDは確定済み分だけ保持 | Acceptance Criteria、関連仕様項目ID、関連構造ID | ACの存在・identity自体を確定できない |

`current / mapped` rowの関連仕様項目IDは `_06` のnormative traceability contractに従います。US / UC / Behavior / ACの `関連構造ID` は `_05` のUI構造ID + domain item ID exact prefix集合だけを許可し、ACの意味を制約するdomain itemはLLMがこの明示edgeへ含めます。blocked rowはUNKNOWNが正本であり、未確定fieldを推測して埋めません。UIOP / US / UC / Behaviorの `状態` はこのfield充足と関連UNKNOWNからhelperが生成し、materialize callerは `状態` を送信しません。

## 4. User Story

User StoryはUI操作のActorと達成目的を安定化する上位単位です。

#### User Story一覧

| US ID | Scope ID | Actor / Role | Goal | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- |

ID: `US-001` から開始し、最低3桁で連番採番する。999の次は1000

状態:
- current
- blocked

規則:
- required scopeではUser Story一覧を必須とする
- current: Actor / Role、Goal、仕様参照が確定し、関連UNKNOWN IDは空
- blocked: 確定できない意味を推測せず、関連UNKNOWN IDを1件以上持つ
- 仕様にないビジネス価値を追加しない
- current USは1つ以上のcurrentまたはblocked UCへ接続する
- USの `状態` はhelperがActor / Role、Goal、仕様参照、関連UNKNOWNから `current / blocked` を導出する

独立したValue列は持ちません。仕様に価値・目的の記載がある場合はGoalまたは関連Authorityの意味として保持します。

## 5. Use Case

Use CaseはActorが1つの目的を達成するための意味あるUI利用シナリオです。

#### Use Case一覧

| UC ID | 関連US ID | Use Case | Trigger | Preconditions | Success Postcondition | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

ID: `UC-001` から開始し、最低3桁で連番採番する。999の次は1000

規則:
- 関連US IDは1件以上必須
- 複数USが同じUCを共有する場合はUCを意味なく複製しない
- 1つのUCが参照するUSは同じScope IDに属する
- current UCが参照するUSはすべてcurrentである。blocked USをcurrent UCの親にしない
- UIOPの `Scope ID` は、その `対応UC ID` が参照するUSから決定論導出したScope IDとexact一致する。cross-scope UIOPは許可しない
- current UCはTrigger / Preconditions / Success Postconditionが後続分析に必要な範囲で確定している
- current UCはBehavior完全性3分類を持ち、各分類のclosure状態は§7で表す。current Behaviorだけでなく、存在・identityは追跡できるが結果未確定のblocked Behaviorを持てる
- blocked UCは関連UNKNOWN IDを1件以上持ち、Behavior完全性3分類をまだ生成しない
- UCの `状態` はhelperが必須fieldと関連UNKNOWNから `current / blocked` を導出する
- 単なるPAGEとUse Caseを同一視しない

## 6. Behavior

BehaviorはUse Case内の意味ある振る舞い単位です。

#### Behavior一覧

| Behavior ID | UC ID | 関連操作ID | 結果分類 | 振る舞い | Postcondition / Result | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

ID: `BH-001` から開始し、最低3桁で連番採番する。999の次は1000

結果分類:
- 正常: ユーザーの主目的が仕様どおり達成される振る舞い
- 準正常: 入力、権限、業務条件、状態等の仕様上想定された条件により通常成功とは異なるが、製品が制御された結果を返す振る舞い
- 例外: システム、外部連携、環境等の異常・失敗条件により通常処理を完了できず、仕様上定義されたエラー / 回復結果となる振る舞い

仕様資料が分類を明示している場合はその用語・意味を優先します。明示がない場合は上記定義でLLMが意味判断し、helperは分類値と構造整合だけを検証します。

別の「基本 / 代替 / 例外」分類軸は導入しません。必要なflow差はBehavior自体の意味として分離します。

状態:
- current
- blocked

規則:
- current Behavior / blocked Behaviorはいずれもcurrent UCだけを親に持つ
- current Behaviorは意味上関係するmapped UIOPを`関連操作ID`へ1件以上明示する。各UIOPは同じScopeに属し、`対応UC ID`にそのBehaviorのUC IDを含む。どのUIOPを関連付けるかはLLMが判断し、helperは存在・state・UC / Scope整合だけを検証する
- blocked Behaviorは確定済みの`関連操作ID`だけを保持でき、関係自体が未確定なら空を許可する。blocked UIOPを参照する場合は同じScopeだけを許可し、current Behaviorからblocked UIOPを参照しない
- current Behaviorは1件以上のcurrentまたはblocked ACを持つ。ready scopeではcurrent Behaviorごとにcurrent ACが1件以上あり、blocked ACが残っていないことを要求する
- Behaviorの意味自体が未確定ならblocked Behavior rowを作る。BehaviorはcurrentだがACのsemantic identityが既知で期待条件だけ一時的に未確定なら、親Behaviorを不要にblockedへ落とさず同じAC IDをblockedで保持できる
- Behaviorの存在・identity自体をまだ確定できない場合はblocked Behavior rowを作らず、§7の `未定義` + UNKNOWNだけで表す
- blocked Behaviorはcurrent ACを持たない。AC semantic identityが既知ならblocked ACを同じIDで保持できる
- blocked Behaviorをcurrent ACの親にしない
- Behaviorの `状態` はhelperが必須fieldと関連UNKNOWNから `current / blocked` を導出する

## 7. 正常 / 準正常 / 例外の完全性確認

これはテスト技法ではありません。current Use Caseの仕様検討漏れを見える化するための上流完全性確認です。

#### Use Case振る舞い完全性

| UC ID | 結果分類 | 判定 | 関連Behavior ID | 関連仕様項目ID | 関連UNKNOWN ID | 理由 / 根拠 |
| --- | --- | --- | --- | --- | --- | --- |

判定:
- 定義あり
- なし
- 未定義

deterministic contract:
- current UCについて正常 / 準正常 / 例外が各1行存在する
- blocked UCについてこの表のrowを生成しない
- `定義あり` → 関連Behavior IDが1件以上で、すべてcurrent Behavior。関連UNKNOWN IDは空
- `なし` → 関連Behavior ID / 関連UNKNOWN IDは空、理由 / 根拠と `関連仕様項目ID` が1件以上必須。関連仕様項目IDはcurrent SPEC / DECISION / approved ASMだけを許可し、「該当振る舞いなし」という判断根拠を機械追跡できるようにする
- `未定義` → 関連Behavior IDは0件以上を許可し、関連UNKNOWN IDが1件以上必須。Behavior IDを持つ場合は、その分類で既知のcurrent / blocked Behaviorを列挙できる
- 1分類にcurrent Behaviorが存在しても、別の未確定条件が残る場合は `未定義` とし、既知Behavior ID + UNKNOWNを同じrowで保持できる
- `未定義`を `なし` として扱わない
- `なし`は資料とAuthorityを確認した結果、該当振る舞いなしを意味し、単なる未記載に使わない

## 8. Acceptance Criteria

Acceptance CriteriaはBehaviorが仕様上成立したと判断できる受入可能な結果・条件を表します。

#### Acceptance Criteria一覧

| AC ID | Behavior ID | Acceptance Criteria | 関連仕様項目ID | 関連構造ID | 状態 | 関連UNKNOWN ID |
| --- | --- | --- | --- | --- | --- | --- | --- |

ID: `AC-001` から開始し、最低3桁で連番採番する。999の次は1000

状態:
- current
- blocked

規則:
- current Behaviorは1件以上のcurrentまたはblocked ACを持つ
- current ACはcurrent Behaviorだけを親に持ち、ACへ到達するBehavior / UC / 関連USはすべてcurrentであることを要求する
- blocked ACはsemantic identityが既知のACが一時的に確定できない場合だけ使用し、親Behaviorはcurrentまたはblockedを許可する。関連UNKNOWN IDを1件以上持つ
- ACは観測可能な振る舞い / 結果の意味を表す
- AC identityが既知でexpected behavior / Authorityだけ不足する場合は同じAC IDをblockedで保持する。解消後は同じIDをcurrentへ戻す
- AC identity自体を確定できない場合はAC rowを作らず、既知のBehaviorまたはScopeからBlocking UNKNOWNへ閉じる
- 意味上本当に廃止された場合だけLLMが `retire_ids[]` を明示し、current / blocked切替をretireとして扱わない
- ACへ境界値一覧、入力値一覧、組合せ表、テストデータ一覧を展開しない
- 仕様上の特定値そのものが期待挙動の一部である場合は除去しない
- current ACは1件以上のcurrent Authority itemへ追跡する
- 元Authorityに存在しない期待値をACへ追加しない。必要ならINFERENCE / UNKNOWNとして上流へ戻す

因子候補をACで別管理しません。因子 / 値 / 境界 / 制約 / Decision Table / Pairwise / State等は引き続きtest-condition-designがownerです。

## 9. ID / semantic identity

IDへActor、結果分類等のmutable semanticsを埋め込みません。

使用:
- SCOPE-xxx
- UIOP-xxx
- US-xxx
- UC-xxx
- BH-xxx
- AC-xxx

semantic identityのreuse / new / explicit retire判断はLLMが行います。

通常package更新では、LLMはstable ID番号をMarkdownへ書かず、既存identityを `identity_action=reuse / reuse_id=<ID>`、new identityを `identity_action=new / draft_key=<key>` として `ui_target_package.py materialize` へ渡します。helperがstandard prefixの使用済みIDから採番し、`@draft`参照を解決してcanonical tableを生成します。採番処理は`materialize`内部allocatorとしてunit testし、focused CLI operationは追加しません。

分類変更だけでstable IDを再採番しません。rowが消えただけでretiredとせず、semantic identityをcurrent modelから意図的に除去する場合だけLLMが `retire_ids[]` を明示します。

`SRC / SPEC / INF / UNK / DEC / ASM / Q` 等の既存canonical IDは既存repository契約どおり3桁固定です。PR #16で新設するUI target structural ID（SCOPE / PAGE / STATE / VIEW / STEP / MODAL / BDLG / PANEL / EXT / SHARED / FIELD / RULE / FLOW / NOTIFY / INTERACT / ISSUE / IMPL / UIOP / US / UC / BH / AC）は**最低3桁・上限なし**とし、999の次を1000として採番します。既存canonical IDは1 prefix 999件を**意図したsupported hard limit**として維持し、超過時はfail-closedします。PR #16で既存canonical ID体系全体の桁契約は変更しません。

## 10. Authorityとの関係

SCOPE / UIOP / US / UC / Behavior / ACは新しいAuthority種別ではありません。

UIOP / US / UC / Behavior / ACのnormative rowは根拠を空にしません。current rowは `関連仕様項目ID` にcurrent SPEC / DECISION / approved ASM / INFを1件以上持ち、根拠不足でsemantic identityが既知なら同じstable IDのblocked row + `関連UNKNOWN ID` へ閉じます。ACだけはcurrent SPEC / DECISION / approved ASMのAuthorityを1件以上要求し、INFだけではcurrent ACにしません。blocked ACはUNKNOWNを必須とし、Machine Entity / `acceptance_criteria[]` 対象外です。UNKNOWNは専用の `関連UNKNOWN ID` で追跡し、`関連仕様項目ID` への代用にしません。

- structured rowを書いたこと自体をSPECへ昇格しない
- repository実装やlive UIから期待結果を補完しない
- Authorityで定義されていない内容はINF / UNKNOWNのまま扱う
- structured viewがAuthorityの意味を変更しない

blocked rowは専用の関連UNKNOWN IDでcurrent UNKNOWNへ接続します。関連仕様項目IDへUNKNOWN lineageを隠して代用しません。

## 11. Machine Entity境界

US / UC / Behavior自体はMachine Entity化しません。

下流test-requirement-designへのhandoff pointであるcurrent ACだけを `spec-analysis / acceptance_criterion / AC-xxx` Machine Entityへ決定論変換します。

AC Entityのcanonical contentには、AC自身だけでなくそのACへ到達するcurrent US / UC / Behavior chain、Scope、Authority refs、構造refsに加え、**parent Behaviorの`関連操作ID`に明示された状態=`mapped`のUIOP集合**を固定projectionします。同じUCに属するだけでBehaviorから参照されないUIOPは含めません。linked UIOPには `uiop_id / actor_role / target_structure_id / operation / authority_refs[]` を含めます。さらに直接参照するFIELD / RULE / FLOW / NOTIFY / INTERACTを確定し、AC chain / linked UIOP / それらdomain itemが直接参照するUI構造rowと、その `親構造ID` をrootまで辿ったancestor closure、関連INF、scope内容をcanonical projectionします。helperはmissing parent / self-parent / cycleをrejectし、current ACへ到達する全parentがcurrentであることを決定論検証します。

これによりUIOPの操作対象 / 操作内容 / Authority、scopeの対象意味、同一stable IDのUI構造とancestor、linked FIELD / RULE / FLOW / NOTIFY / INTERACT、linked INF、US / UC / Behaviorの意味変更でもAC Entityのcontent fingerprintまたはAuthority dependencyが変わり、AC IDや本文が同じでも関連TRをstaleにできます。無関係なpackage rowはprojectionへ入れません。UIOPやpackage-local item自体をglobal Machine Entity typeへ追加しません。

Authority Entityは既存 `authority_entities.py`、AC Entityは `ui_target_package.py build-machine-evidence` が生成します。Machine Entity wrapper / content fingerprint / expected identityをLLMが手組みしません。

shared runtimeのexact contractは `_09_runtime-entity-and-test-requirement-contracts.md` を正本とします。

## 12. test-requirement-design連携

Acceptance CriteriaはTest Requirementそのものではありません。

- AC: product behaviorを受け入れ可能と判断する仕様上の条件 / 結果
- TR: 何を検証・保証すればよいかというQA検証責務

1:1を強制しません。

許可:
- 1 AC → 複数TR
- 複数AC → 1 TR（同じ検証責務へ安全に統合できる場合）

ユーザー要求がtest-requirement-designまで進むworkflowでは、current ACを必ず1件以上のTRまたは明示的dispositionへ閉じます。仕様理解packageだけを要求された場合は、current ACをAuthorityへ追跡しMachine Entity化できれば本工程は完了でき、AC→TR / disposition closureを要求しません。

ACに関係しない横断的TRも許可します。その場合も現在有効なAuthorityへの追跡は必須です。

runtime / closure / generator versionは `_09_runtime-entity-and-test-requirement-contracts.md` を正本とします。

## 13. test-condition-designとの境界

変更しません。

因子 / 値 / 境界 / 制約 / Decision Table / Pairwise / State等は引き続きtest-condition-designがownerです。

test-condition-designはTRから問題構造を分析し、仕様 / Risk / 状態 / 業務ルールに根拠がある条件軸を識別します。

正常 / 準正常 / 例外の3分類をテスト技法として扱いません。

## 14. deterministic validation

`ui_target_package.py validate` に追加:

- SCOPE / UIOP / US / UC / BH / AC ID形式・duplicate
- scope適用判定の許可値と対応関係
- Behavior Decomposition=required scopeはUIOP rowを1件以上持つか、UIOP identity自体を確定できないBlocking UNKNOWNが当該Scope + `02_behavior_and_business_rules.md` を指す。どちらもなければrejectする
- current USは1件以上のcurrent / blocked UCへ接続する
- current UCは正常 / 準正常 / 例外3rowを持ち、少なくとも1分類が `定義あり` でcurrent Behaviorへ到達するか、1分類以上が `未定義 + UNKNOWN` でscope blockedになる。3分類すべて `なし` かつBehavior=0件をreadyにしない
- current Behaviorは1件以上のcurrent / blocked ACへ接続し、blocked ACが残るscopeをreadyにしない
- current Behaviorは`関連操作ID`を1件以上持ち、全参照先がmapped UIOPで同じUC / Scopeへ閉じる。blocked Behaviorの関連操作参照は確定済み分だけを許可する
- required scope内では不足情報をblocked UIOP / US / UC / Behavior / AC + UNKNOWN、またはidentity未確定のBlocking UNKNOWNとして保持できる
- not-applicable scope、またはUI操作有無自体が未確定のblocked scopeにUIOP / US / UC / Behavior / ACを確定済みとして生成していないこと
- blocked applicability / rowのUNKNOWN参照
- UIOP → UC closure
- US → UC closure
- UC → Behavior closure
- current UCだけに正常 / 準正常 / 例外3行が存在すること
- 定義あり / なし / 未定義の構造整合
- current Behavior → AC closure
- `なし` completeness row → current Authority ref 1件以上
- current AC chainのBehavior / UC / USがすべてcurrent
- blocked ACは関連UNKNOWN IDを1件以上持ち、Machine Entity / `acceptance_criteria[]` 対象外であること
- current ↔ blocked AC state transitionでstable IDを維持し、explicit retireがない限りAC IDを再採番しないこと
- current AC → current SPEC / DECISION / approved ASM ref 1件以上。INF / UNK / inactive Authorityだけではcurrent ACにしない
- current / blockedとUNKNOWN参照の整合
- broken structural ref
- `Machine Entities: spec-analysis` blockのexactly-one存在とbuild-machine-evidence結果との一致

意味判断は行いません。

test-requirement-design側の決定論契約は `_09_runtime-entity-and-test-requirement-contracts.md` を正本とします。

## 15. semantic validation

semanticでは次を確認します。

- UI操作の有無とscope適用判定が妥当
- UI操作があるのにdecompositionを省略しない
- UI操作あり + Actor / Goal等不足ではscopeをrequiredのまま維持し、影響下位rowだけをblocked + UNKNOWNにする
- UI操作がないscopeへUS / UC / Behavior / ACを創作しない
- 非操作起点のUI挙動をテスト対象外として落としていない
- UI操作母集団がUCへ閉じている
- Behaviorの`関連操作ID`が意味上必要なUIOPだけを結び、同一UC内の無関係UIOPを各Behavior / ACへ一律関連付けしていない
- US / UC / Behaviorの粒度が過剰統合 / 過剰分割されていない
- 正常 / 準正常 / 例外を仕様に反して創作していない
- `なし` と `未定義` を区別し、`なし` のAuthority根拠が意味上妥当である
- Behavior identityが既知だが結果未確定な場合のblocked Behaviorと、identity自体未確定でBehavior rowを作らない場合を区別している
- `未定義` で既知Behaviorがあっても未解消条件をUNKNOWNとして残している
- blocked UCを無理に3分類していない
- ACが具体テストケース / 組合せへ先回りしていない
- ACがAuthorityから期待結果を創作していない
- TRがACの単なる言い換えではなく検証責務になっている
- AC→TRが1:1であることを不必要に強制していない

## 16. evaluation

既存caseを壊さず、新契約を専用caseで評価します。

spec-analysis:
- SPEC-OUT-003へbehavior decomposition deterministic contractを追加
- SPEC-SEM-003の複雑UI packageに複数scope、UIOP / US / UC / Behavior / AC、current / blocked、正常 / 準正常 / 例外を含める。同一UC内に複数UIOP / Behavior / ACを置き、Behaviorの`関連操作ID`が意味上必要なUIOPだけを結ぶことを評価する
- 既存normal spec-analysis caseでUI操作がない場合にdecompositionを生成しない回帰を確認

test-requirement-design:
- TR-OUT-003を追加
  - known current AC
  - linked AC
  - disposed AC
  - missing closure / unknown AC negative
  - parent Behavior / UC / US変更によるAC fingerprint変化
  - partial rerunでscope外TRがchanged ACによりstaleになること
- TR-SEM-003を追加
  - AC→TR traceability
  - ACの単純言い換えを避ける
  - 複数AC統合 / 1AC複数TRを意味に応じて扱う

PR #14後baselineからPR #16全体の現在Plan増分:
- Skill: +0
- Trigger: +0
- Deterministic output: +2
  - spec-analysis +1
  - test-requirement-design +1
- Semantic: +8
  - spec-analysis +5
  - question-analysis +2
  - test-requirement-design +1
- qa-workflow routing: +8

PR #14 baselineが22 Skill / 488 trigger / 44 deterministic / 155 semantic / 61 routingなら、PR #16後の現在Plan期待値は:
- 22 Skill
- 488 trigger
- 46 deterministic
- 163 semantic
- 69 routing

semantic case数自体を目的にはせず、`_04_evaluation-ci-implementation-order.md` のLLM responsibility coverageを正本とします。

## 17. legacy migration

legacy UI target packageにUS / UC / Behavior / ACが存在しない場合でも、UI操作を含むscopeはcurrent `ui-target-v1` へのmigration時に本contractを適用します。

- legacyの操作 / flow / expected behaviorをLLMがsemantic mappingする
- 仕様にないUser Story / ACを創作しない
- 必要情報不足はUNKNOWN
- new ID採番はhelper
- migration後packageがrequired decompositionを満たさないscopeは完成扱いしない

## 18. 対象外

- US / UC / ACを別Skillへ分離すること
- US / UC / Behaviorをglobal Machine Entity typeへすること
- 正常 / 準正常 / 例外を新しいテスト技法にすること
- ACからテストケースを直接生成すること
- UI操作のない仕様へUser Storyを無理に生成すること

## 19. 完了条件

- UI操作を伴うscopeでUS → UC → Behavior → ACの順序が必ず実行される
- UI操作があるのに情報不足の場合、not-applicableへ逃げずUNKNOWN / blockedになる
- scopeごとの適用状態がrequired / not-applicable / blockedのいずれかに一意に決まる
- 全UI操作がUCまたはblockedへ閉じる
- current UCで正常 / 準正常 / 例外を検討済みと判別できる
- blocked UCで無意味な3分類を生成しない
- current Behaviorがcurrent ACへ閉じる
- current Behaviorが1件以上のmapped UIOPへ`関連操作ID`で閉じ、同一UC内の無関係UIOPをAC Entityへ混入させない
- current ACがcurrent Authorityへ追跡できる
- ACだけが下流handoff用Machine Entityとして決定論生成される
- US / UC / Behavior変更でも関連AC Entity fingerprintが変わる
- test-requirement-designまで進むworkflowではcurrent ACがTRまたは明示的dispositionへ閉じる。仕様理解packageだけの要求ではこのclosureを完了条件にしない
- factor / value / combinationはtest-condition-designへ残る

