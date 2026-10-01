# UIテスト対象分析モード: behavior decomposition / acceptance traceability

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

関連Plan:
- 2026-10-01_201500_ui-test-target-analysis-mode_02_spec-analysis-package.md
- 2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md
- 2026-10-01_201500_ui-test-target-analysis-mode_06_package-schema-and-helper-contracts.md

この文書は、UI操作を伴う対象に対する User Story / Use Case / Behavior / Acceptance Criteria の分析手順、完全性、下流traceabilityの正本です。

目的はテストケースを早期生成することではありません。仕様をテスト設計へ渡す前に、UI操作の目的・利用シナリオ・振る舞い・受入可能な結果を安定した意味単位へ分解し、切り分け漏れとLLMごとの分割ぶれを減らします。

## 1. 適用契約

適用可否は自由選択にしません。

### required

対象scopeにユーザー / operatorが行うUI操作が1つ以上存在する場合、behavior decompositionは必須です。

UI操作には少なくとも次を含みます。

- button / link / menu / tab等による操作
- form入力 / 選択 / submit
- modal / dialog内操作
- upload / download開始操作
- 検索 / filter / sort / pagination
- drag / drop、toggle、selection等の直接操作
- 複数PAGE / VIEW / STEPをまたぐユーザーフロー
- UIから開始する外部遷移 / external interaction

### not-applicable

対象scopeにユーザー操作がなく、表示専用情報・静的表示・背景処理・非UI仕様だけで構成される場合のみ `not-applicable` とします。

「資料不足でUS / UC / Behavior / ACを書けない」はnot-applicableではありません。

UI操作は存在するが意味を確定できない場合:
- modeはrequiredのまま
- 不足内容をUNKNOWNとして記録する
- 該当US / UC / Behavior / AC closureをblocked扱いにする
- 推測で補完しない

### applicability table

`02_behavior_and_business_rules.md` にexact tableを持ちます。

#### 振る舞い分解適用判定

| 項目 | 値 | 根拠 / 関連仕様項目ID |
| --- | --- | --- |
| Behavior Decomposition | required / not-applicable |  |

helperは許可値とrequired時の下位table存在だけを検証し、適用可否の意味判断はLLMが行います。

## 2. 分析順序

UI操作を含むscopeでは、次の順序を省略しません。

1. current Authority / UNKNOWNを解決する
2. UI構造（PAGE / VIEW / STATE / MODAL等）を整理する
3. UI操作一覧を抽出する
4. Actor / Roleと達成目的をUser Storyへ整理する
5. 各User StoryからUse Caseを識別する
6. 各Use CaseをBehaviorへ分解する
7. 各Use Caseについて正常 / 準正常 / 例外の3分類を全て確認する
8. 各BehaviorのAcceptance Criteriaを定義する
9. US / UC / Behavior / ACをcanonical Authorityへ追跡する
10. 不明点をUNKNOWNへ閉じる
11. deterministic helperでID / parent / completeness / reference / Machine Entityを検証する
12. semantic quality gateで切り分け漏れ・過剰分割・意味重複・仕様創作がないか確認する
13. 完了したcurrent ACをtest-requirement-designへ渡す

test requirement / test condition / test caseをこの工程内で作りません。

## 3. UI操作一覧

User Storyへ進む前に、対象scopeのUI操作母集団を明示します。

#### UI操作一覧

| 操作ID | Actor / Role | 対象構造ID | 操作 | 目的 / 結果 | 関連仕様項目ID | 対応UC ID | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- |

ID: `UIOP-001` ～ `UIOP-999`

状態:
- mapped
- blocked

required modeでは、各current UI操作を1つ以上のUCへmapするか、UNKNOWNを根拠にblockedへします。

操作を無言で落としません。

## 4. User Story

User StoryはUI操作のActorと達成目的を安定化する上位単位です。

#### User Story一覧

| US ID | Actor / Role | Goal | Value / 目的 | 関連仕様項目ID | 関連構造ID | 状態 |
| --- | --- | --- | --- | --- | --- | --- |

ID: `US-001` ～ `US-999`

状態:
- current
- blocked

規則:
- UI操作があるrequired modeではUS tableを必須とする
- Actor / Role、Goalを仕様根拠から確定できない場合は推測せずblocked + UNKNOWN
- Value / 目的が仕様上明示されず、GoalだけでUser Story identityを成立させられる場合はGoalと同じ意味を重複記載せず `-` を許可する
- 仕様にないビジネス価値を創作しない
- 1つのUSは少なくとも1つのcurrent UCまたはblocked UCへ接続する

## 5. Use Case

Use Caseは「Actorが1つの目的を達成するための意味あるUI利用シナリオ」です。

#### Use Case一覧

| UC ID | 関連US ID | Use Case | Trigger | Preconditions | Success Postcondition | 関連仕様項目ID | 関連構造ID | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

ID: `UC-001` ～ `UC-999`

規則:
- 関連US IDは1件以上必須。複数USが同じUCを共有する場合は `<br>` 区切りで参照し、UCを意味なく複製しない
- 1つのcurrent UCは少なくとも1つのcurrent Behaviorを持つ
- Trigger / Preconditions / Success Postconditionが仕様上未定義で、後続のBehavior / ACへ影響する場合はUNKNOWN
- 各UIOPは1つ以上のUCへmapする
- 単なる画面PAGEとUse Caseを同一視しない

## 6. Behavior

BehaviorはUse Case内の意味ある振る舞い単位です。

#### Behavior一覧

| Behavior ID | UC ID | フロー種別 | 結果分類 | 振る舞い | Postcondition / Result | 関連仕様項目ID | 関連構造ID | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

ID: `BH-001` ～ `BH-999`

フロー種別:
- 基本
- 代替
- 例外

結果分類:
- 正常
- 準正常
- 例外

状態:
- current
- blocked

フロー種別と結果分類は別軸です。例えば代替flowが正常結果へ到達することを許可します。

LLMが意味分類し、helperは許可値だけを検証します。

## 7. 正常 / 準正常 / 例外の完全性確認

これはテスト技法ではありません。Use Case仕様の検討漏れを見える化するための上流完全性確認です。

各current / blocked UCについて3分類を必ず1行ずつ持ちます。

#### Use Case振る舞い完全性

| UC ID | 結果分類 | 判定 | 関連Behavior ID | 関連UNKNOWN ID | 理由 / 根拠 |
| --- | --- | --- | --- | --- | --- |

結果分類:
- 正常
- 準正常
- 例外

判定:
- 定義あり
- なし
- 未定義

deterministic contract:

- 各UCについて正常 / 準正常 / 例外が各1行存在する
- `定義あり` → 関連Behavior IDが1件以上、UNKNOWN IDは空
- `なし` → Behavior / UNKNOWN IDは空、理由 / 根拠が必須
- `未定義` → UNKNOWN IDが1件以上必須
- `未定義`を `なし` として扱わない
- `なし`は「確認した結果、該当振る舞いなし」を意味し、単なる未記載に使わない

## 8. Acceptance Criteria

Acceptance CriteriaはBehaviorが仕様上成立したと判断できる受入可能な結果・条件を表します。

#### Acceptance Criteria一覧

| AC ID | Behavior ID | Acceptance Criteria | 可変要素 | 関連仕様項目ID | 関連構造ID | 状態 |
| --- | --- | --- | --- | --- | --- | --- |

ID: `AC-001` ～ `AC-999`

状態:
- current
- blocked

規則:
- current Behaviorは1件以上のcurrent ACを持つ
- expected behaviorを仕様根拠から確定できないBehaviorは、ACを創作せずblocked + UNKNOWN
- ACは観測可能な振る舞い / 結果の意味を表す
- ACへ具体的な境界値、全入力値、組合せ表、テストデータ一覧を展開しない
- 仕様上、特定値そのものが期待挙動の一部である場合は値を除去しない
- `可変要素` は仕様上振る舞いを変え得る軸を人間向けに明示するだけで、test-condition-designの因子母集団を制限しない
- current ACは1件以上のcurrent Authority itemへ追跡する
- 元Authorityに存在しない期待値をACに追加しない。必要ならINFERENCE / UNKNOWNへ戻す


## 9. ID / semantic identity

IDへActor、分類、flow種別等のmutable semanticsを埋め込みません。

使用:
- UIOP-xxx
- US-xxx
- UC-xxx
- BH-xxx
- AC-xxx

semantic identityのreuse / new判断はLLMが行います。

LLMがnewと判断した後の採番は `ui_target_package.py next-id` を使用します。

分類変更だけでstable IDを再採番しません。

## 10. Authorityとの関係

US / UC / Behavior / ACは新しいAuthority種別ではありません。

各rowは `関連仕様項目ID` により09のcurrent SPEC / DECISION / approved ASM、必要に応じINF / UNKへ追跡します。

- US / UC / Behavior / ACを書いたこと自体をSPECへ昇格しない
- repository実装やlive UIから期待結果を補完しない
- Authorityで定義されていない内容はINF / UNKNOWNのまま扱う
- ACの表現がAuthorityの意味を変更しない

## 11. spec-analysis behavior Machine Entity

US / UC / Behavior / ACは下流traceabilityとfreshnessのためMachine Entityを持ちます。

entity_type:
- user_story
- use_case
- behavior
- acceptance_criterion

`ui_target_package.py build-machine-evidence` が決定論生成します。

依存:
- User Story → 参照Authority Entity
- Use Case → User Story Entity + 参照Authority Entity
- Behavior → Use Case Entity + 参照Authority Entity
- Acceptance Criterion → Behavior Entity + 参照Authority Entity

UIOPは分析母集団の閉鎖確認用であり、下流設計のidentityとして使用しないためMachine Entity化しません。

artifactの `### Machine Entities: spec-analysis` blockはAuthority Entityと上記4種を同じ `entities[]` へcanonical orderで保存します。

`expected_entity_identities` / fingerprintをLLMが手組みしません。

## 12. test-requirement-design連携

Acceptance CriteriaはTest Requirementそのものではありません。

- AC: product behaviorを受け入れ可能と判断する仕様上の条件 / 結果
- TR: 何を検証・保証すればよいかというQA検証責務

1:1を強制しません。

許可:
- 1 AC → 複数TR
- 複数AC → 1 TR（同じ検証責務へ安全に統合できる場合）

### test-requirement output

`テスト要求一覧` に `関連AC ID` を追加します。

| テスト要求ID | 関連AC ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |

UI target mode由来のcurrent ACが存在する場合:
- 各TRは関連するACを `<br>` 区切りで記録する
- ACに関係しない横断的TRは `-` を許可するが、現在有効な仕様根拠への追跡は必須
- 各current ACは1つ以上のTRまたは明示的dispositionへ閉じる

UI target mode由来ACが存在しないworkflowでは `関連AC ID=-` とし、既存Authority / Risk closureだけを使います。

### test-requirement runtime

`requirement_structure` inputを明示的に拡張します。

必須field:
- `acceptance_criteria`: list。ACがないworkflowでは `[]`
- 各 `test_requirements[]` の `acceptance_refs`: list。該当なしは `[]`

artifact mode:
- `acceptance_criteria` の各IDはcurrent `spec-analysis / acceptance_criterion` Machine Entityへ解決できること
- TR Entity dependencyへAC Entityを追加する

direct mode:
- `acceptance_criteria[]` の既知ID集合に対して参照存在を検証する

closure:
- current ACはTRへlinked、またはdispositionのどちらか一方へ閉じる
- disposition種別は既存 `別テストレベル / 残存リスク / 対象外 / ブロック中`
- ACをlinkedかつdisposedにしない
- 無言でcurrent ACを落とさない

通常workflowを曖昧なoptional fieldにしないため、field自体は常に存在させ、ACなしを空arrayで明示します。

## 13. test-condition-designとの境界

変更しません。

因子 / 値 / 境界 / 制約 / Decision Table / Pairwise / State等は引き続きtest-condition-designがownerです。

ACの `可変要素` は参考情報であり、候補母集団を制限しません。

test-condition-designはTRから問題構造を分析し、ACに明示されていない条件軸も仕様 / Risk / 状態 / 業務ルールに根拠があれば識別できます。

正常 / 準正常 / 例外の3分類をテスト技法として扱いません。

## 14. deterministic validation

`ui_target_package.py validate` に追加:

- required時の4階層table存在
- UIOP / US / UC / BH / AC ID形式・duplicate
- parent reference存在
- UIOP → UC closure
- US → UC closure
- UC → Behavior closure
- UCごとの正常 / 準正常 / 例外3行
- 定義あり / なし / 未定義の整合
- current Behavior → current AC closure
- current AC → current Authority ref
- blocked row → UNKNOWN ref
- broken structural ref
- build-machine-evidence結果とartifact Machine Entity blockの一致

意味判断は行いません。

`test-requirement-design/evals/deterministic/validator.py` に追加:

- `関連AC ID` format
- known AC存在
- current AC closure
- linked + disposed重複禁止

`requirement_structure.py` に追加:

- acceptance_criteria / acceptance_refs strict schema
- current AC Machine Entity dependency
- current AC closure / disposition

## 15. semantic validation

semanticでは次を確認します。

- UI操作があるのにdecompositionを省略しない
- UI操作がない対象へUS / UC / BH / ACを創作しない
- UI操作母集団がUCへ閉じている
- US / UC / Behaviorの粒度が過剰統合 / 過剰分割されていない
- 正常 / 準正常 / 例外を仕様に反して創作していない
- `なし` と `未定義` を区別している
- ACが具体テストケース / 組合せへ先回りしていない
- ACがAuthorityから期待結果を創作していない
- TRがACの単なる言い換えではなく検証責務になっている
- AC→TRが1:1であることを不必要に強制していない

## 16. evaluation

既存caseを壊さず、新契約を専用caseで評価します。

spec-analysis:
- SPEC-OUT-003へbehavior decomposition deterministic contractを追加
- SPEC-SEM-003の複雑UI packageにUS / UC / Behavior / ACを含める
- 既存normal spec-analysis caseでUI操作がない場合にdecompositionを生成しない回帰を確認

test-requirement-design:
- TR-OUT-003を追加
  - known current AC
  - linked AC
  - disposed AC
  - missing closure / unknown AC negativeを評価
- TR-SEM-003を追加
  - AC→TR traceability
  - ACの単純言い換えを避ける
  - 複数AC統合 / 1AC複数TRを意味に応じて扱う

PR #14後baselineからPR #16全体の増分:
- Skill: +0
- Trigger: +0
- Deterministic output: +2
  - spec-analysis +1
  - test-requirement-design +1
- Semantic: +5
  - spec-analysis +3
  - question-analysis +1
  - test-requirement-design +1
- qa-workflow routing: +8

PR #14 baselineが22 Skill / 488 trigger / 44 deterministic / 155 semantic / 61 routingなら、PR #16後は:
- 22 Skill
- 488 trigger
- 46 deterministic
- 160 semantic
- 69 routing

## 17. legacy migration

legacy UI target packageにUS / UC / Behavior / ACが存在しない場合でも、UI操作を含むならcurrent `ui-target-v1` へのmigration時に本contractを適用します。

- legacyの操作 / flow / expected behaviorをLLMがsemantic mappingする
- 仕様にないUser Story / ACを創作しない
- 必要情報不足はUNKNOWN
- new ID採番はhelper
- migration後packageがrequired decompositionを満たさないscopeは完成扱いしない

## 18. 対象外

- US / UC / ACを別Skillへ分離すること
- 正常 / 準正常 / 例外を新しいテスト技法にすること
- ACからテストケースを直接生成すること
- ACの可変要素を唯一のfactor母集団として固定すること
- UI操作のない仕様へUser Storyを無理に生成すること

## 19. 完了条件

- UI操作を伴うscopeでUS → UC → Behavior → ACの順序が必ず実行される
- UI操作があるのに情報不足の場合、not-applicableへ逃げずUNKNOWN / blockedになる
- 全UI操作がUCまたはblockedへ閉じる
- 全UCで正常 / 準正常 / 例外を検討済みと判別できる
- current BehaviorがACまたはblockedへ閉じる
- ACがcurrent Authorityへ追跡できる
- US / UC / Behavior / ACのMachine Entityが決定論生成される
- current AC変更がTRのfreshnessへ伝播する
- current ACがTRまたは明示的dispositionへ閉じる
- factor / value / combinationはtest-condition-designへ残る
