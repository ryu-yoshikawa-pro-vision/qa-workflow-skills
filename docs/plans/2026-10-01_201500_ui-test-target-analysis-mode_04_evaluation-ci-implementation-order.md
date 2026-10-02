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
- US / UC / Behavior / AC
- 正常 / 準正常 / 例外で定義あり / なし / 未定義が混在
- 一部Behavior identityは既知だが結果未確定

期待:
- semanticなUI構造分類を行い、STATEを直交軸として整理する
- current ACへ到達するUS / UC / Behaviorは全てcurrentにする
- 未定義分類では既知current / blocked Behaviorを保持でき、identity自体不明ならBehavior rowを創作しない
- `なし` はcurrent Authority参照を持つ
- ACに具体テスト条件へ先回りしない

### SPEC-SEM-004: repository実装が仕様と違う

- 高Authority仕様を実装に合わせて変更しない
- spec-implementation gapとして分離する
- repository evidenceをAuthorityへ自動昇格しない
- 08を後続versionへcarry-forwardする場合、再確認していないcommitをcurrent commitへ更新しない

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
- retained / retired identity
- 標準fileへ混在させるべきでないCSV domain

期待:
- legacy/current semantic identity mappingを意味判断する
- 必要なextension fileと案件固有prefixの意味を判断する
- 過去retired IDをnew entityへ再利用しない
- generic migration / generic document frameworkへ拡張しない

### SPEC-SEM-007: file trigger / external owner境界

入力:
- simple downloadだけのscope
- export生成 + data transformation + downloadを伴うscope
- Project Context以外のDEC / ASM正本owner

期待:
- simple downloadは05のみ
- export生成 / transformation + user-visible downloadは04 + 05
- 外部ownerの意味上の正本性を判断するが、canonical Authority IDはDEC-xxx / ASM-xxxを維持し、Jira / ADR等の外部IDをauthority_idへ流用しない
- extension / conditional fileを必要以上にrequiredにしない

既存SPEC-SEM-001 / 002には「通常spec-analysisで足りる要求をUI target modeへ不要に昇格しない」回帰観点を維持します。

### spec-analysis semantic responsibility coverage

| LLM責務 | semantic case |
| --- | --- |
| SPEC / DECISION / INFERENCE / UNKNOWN分類・Authority競合 | 既存SPEC-SEM-001 / 002、SPEC-SEM-003 / 004 |
| PAGE / STATE / VIEW / MODAL等の意味分類 | SPEC-SEM-003 |
| scope UI操作有無 / 条件付きfile trigger | SPEC-SEM-003 / 007 |
| US / UC / Behavior / AC分解と正常 / 準正常 / 例外 | SPEC-SEM-003 |
| semantic identity reuse / new / explicit retire | SPEC-SEM-005 / 006 |
| repository差分の意味 | SPEC-SEM-004 |
| same-UNK reopen / new UNK | SPEC-SEM-005 |
| legacy semantic mapping | SPEC-SEM-006 |
| extension file / 案件固有prefixの必要性・意味 | SPEC-SEM-006 |
| DEC / ASM owner判断 | SPEC-SEM-007 |
| 04 / 05責務境界 | SPEC-SEM-007 |

repository testは、`05_llm-deterministic-boundaries.md` のLLM responsibility matrixで今回追加・変更した各行が最低1 semantic criterion / caseから参照されることを検証します。case数そのものよりcoverageを正本にします。

### 複数Markdown packageのevaluation projection

既存 `scripts/skills/evals/semantic/run.py` / deterministic runnerはいずれも1つの `--output` fileを受けるため、runner自体はdirectory対応へ変更しません。

production `skills/spec-analysis/scripts/ui_target_package.py project-eval` を使用し、projection modeを分けます。

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
- next-version
- next-id
- render-readme-controls
- next-domain-file
- build-manifest
- impact
- build-machine-evidence
- project-eval
- materialize

repository unit testで次を必須確認します。

- required core / 条件付き必須file applicability / extension file declaration
- mode assetのvariable tableがheader-onlyで例示stable IDを含まず、固定applicability rowだけ事前配置されること
- package root外path拒否
- package内version一致
- canonical / structural / 00宣言済み案件固有ID形式・duplicate
- 一度採番に使った案件固有prefix宣言の削除 / 意味変更を拒否すること
- UI構造の `状態軸` がSTATEでは必須・非STATEでは空であること、`種別` exact enumでPANEL / POPOVER / GLOBAL UIを区別しつつPANEL prefixを共有すること
- 00のscope / applicability tableで `関連仕様項目ID` と `根拠 / 備考` が別列であり、stable ID列にはIDだけ、prose列中のIDはreference扱いしないこと
- structured rowのexact stable ID参照
- 09のcurrent UNKNOWN集合と07 / README件数の一致
- MANIFEST file set / order / SHA-256
- README file一覧とMANIFESTの一致
- CHANGELOG最新version見出しとpackage versionの一致
- CHANGELOGのexact `Stable ID changes` table、Change enum、version内duplicate
- fresh v00の空change table、v01以降のDEC / ASM初登場=added、既追跡内容・状態変更=changed、明示 `retire_ids[]` でのみretiredを生成すること
- resolvedはUNKだけに許可し、resolved後のresolver変更 / same-ID reopenを `changed`、reopen後の再closeを再 `resolved` として許可すること
- retiredだけをterminal eventとして後続eventをrejectすること
- 履歴全体で同じStable IDへ `added / migrated` を複数回記録できないこと
- legacy migrationでDEC / ASMを含むretained tracked IDを `migrated` として引き継ぎ、確認できるretired / resolved履歴だけをterminal eventとして受理すること。materializeがこれらをnew ID採番前の使用済み集合へ予約すること
- current packageのnext-versionが `package_root` からcurrent versionを内部取得し、Agentへ `previous_version` の転記を要求しないこと
- default policyでREADMEのPackage Version / Previous Package Versionが初回または1 revision差として整合し、完成済みpackageへ永続差分を保存する場合はsemantic / presentationを問わず+1、完全no-opだけversion維持となること
- legacy migration用next-versionだけが明示 `previous_version` inputを受けること
- render-readme-controlsがcurrent UNKNOWN件数とpayload file tableのcanonical Markdownを返し、Agentが件数・file順・種別を再構築しないこと
- next-domain-fileがLLMのslug決定後に10+ fileの次番号とcanonical pathだけを決定し、同一更新で複数追加する場合は1件目の00登録 + file作成前に2件目を採番しないこと
- domain file命名
- inspectが更新前owner row fingerprint / UNKNOWN state / exact refs / payload hashを含むcanonical `update_snapshot` を返すこと
- next-id / materializeがsemantic identityを判断せず、UI target mode所有の `SRC / SPEC / INF / UNK` + standard structural prefix + 00宣言済み案件固有prefixについてcurrent row + CHANGELOG履歴 + previous snapshotから次番号を決め、更新途中で消えたprevious IDも再利用しないこと
- `DEC / ASM` をUI target modeのnext-idが採番しないこと
- DEC / ASMはCHANGELOG / impactの追跡可能stable IDとして受理し、Project Contextがownerの場合だけproject_context_ids.pyで採番すること
- Project Context以外の明示ownerをProject Contextへ複製せず、canonical Authority IDは `DEC-xxx / ASM-xxx` を維持し、Jira / ADR等の外部record IDをauthority_idへ流用しないこと。owner未採番時にLLM hand-numberingへfallbackしないこと
- focused next-idでは同一prefixの複数new IDを重複なく単調採番でき、canonical materializeでは複数new rowを1 request内のcanonical順でbatch allocationしてAgentによる逐次row書込みを不要にすること
- current viewから消えた過去IDをprevious snapshot / CHANGELOG履歴のどちらかで保持している限り再利用しないこと
- UNKNOWNのopen / resolved / resolver変更 / same-ID reopen / re-resolveで `現在有効か / 解消先ID` が整合し、resolved状態ではcurrent SPEC / DECISION / 承認済みASMへ閉じること
- canonical structured Markdownのduplicate heading / table、row列数、escaped pipe、`<br>` referenceを固定parse契約で検証すること
- impactがprevious snapshotとcurrent tracking row差分から `added / changed / resolved` を生成し、`retired` は明示 `retire_ids[]` だけから生成すること。previous ID消失のみなら `state_transition_required` でblockedすること
- impactの `影響file` がchanged IDのprevious/current owner + exact reference先unionであり、Agentへfile一覧再入力を要求せず、semantic本文変更の要否を勝手に決定しないこと
- legacy migrationではLLMが確定したretained ID / 明示lifecycle event / semantic rowsを `materialize(change_mode=legacy-migration)` へ渡し、helperがnew ID採番・canonical Markdown・`migrated / added / resolved / retired`・README / Machine Entity / MANIFESTまで1 write pathで生成すること
- scope applicability、UI操作scopeのUIOP / US / UC / Behavior / AC hierarchy / current AC chain全parent=current / closure / current UCの3分類整合
- `未定義` で既知current / blocked Behavior IDを0件以上保持できUNKNOWN必須、Behavior identity自体不明ならblocked Behaviorを創作しないこと
- `なし` は関連Behavior / UNKNOWNなし + 理由 + current Authorityの `関連仕様項目ID` 1件以上を要求すること
- 09の「現在有効な仕様根拠」からnormalized Authorityを固定projectionし、`適用範囲` を非空string、`関係` を単一許可値の1要素arrayとして一意にserializeすること
- build-machine-evidenceがAuthority + current AC Entity、spec-analysis normalized_skill_input、expected identity、shared `render_machine_entities()` 由来のcanonical `machine_entities_markdown` を決定論生成し、不要な統合implementation_fingerprintを公開しないこと
- AC chain refsからINF / UNK / inactive Authorityを除外し、current SPEC / DECISION / approved ASMだけをauthority_refs / dependencyへ投影すること。current Authorityが0件ならACをcurrent Entity化しないこと
- `Machine Entities: spec-analysis` blockがexactly one存在し、heading / JSON fence / wrapperを含めhelper再生成Markdownと一致すること
- 親US / UC / Behavior変更でAC Entity fingerprintが変わること
- project-evalがexact `projection / files[] / controls[] / markdown` payloadを返し、semantic projectionではcurrent versionの `変更概要` controlだけを追加し、過去CHANGELOG / Stable ID changes / 影響fileを混ぜないこと
- raw SHA-256はproject-eval outputから再計算せず、validate / repository unit testでraw bytesに対して検証すること

### 8.2 question-analysis / Project Context production helper

`skills/question-analysis/scripts/unknown_links.py`、`skills/question-analysis/scripts/question_ids.py`、`skills/qa-workflow/scripts/project_context_ids.py` を追加します。

`unknown_links.py`:
- `operation=validate-links`
- UNK ID形式
- current known UNKNOWNへの存在参照
- 同一Q内duplicate
- current / resolved集合が入力された場合のresolved-only参照
- issueをpayloadへ重複保持せず共通top-level `issues[]` だけへ返す

`question_ids.py`:
- create / updateを区別し、既存成果物更新でprevious artifact欠落をfail-closedにする
- next-id / build-historyは `previous current Q + previous history + current current Q` を同じ使用済み集合正本とし、candidate側の既存historyを採番入力へ含めない
- materializeはLLMが確定したQ semantic rowsからnew IDをbatch allocationし、current Q table + 質問ID履歴をcanonical生成する。AgentがQ ID / `<br>` / row順を手組みしない
- malformed / duplicate Q IDを拒否
- Q-999で `id_space_exhausted`
- `Q-001解消 → current質問0件 → 新規質問` でQ-002となり、Q-001を再利用しない

`project_context_ids.py`:
- Project Context Section 12 / 13が案件のDEC / ASM正本ownerである場合だけ対象tableをparse
- next-idはprevious + candidate両Project Contextの全状態rowを使用済み集合とし、semantic reuse / new判断をせずnew確定後の最大値+1を返す
- materializeはdecision / assumption semantic rowsからIDを割り当て、Section 12 / 13をcanonical生成する。AgentがDEC / ASM rowを手組みしない
- validate-historyはprevious DEC / ASM ID集合がcandidateから欠落した場合にrejectし、撤回 / 置換済みIDの削除と再利用を防ぐ
- canonical Authority IDは `DEC-xxx / ASM-xxx` に限定し、外部owner固有IDはauthority_idへ流用しない
- malformed / duplicate IDを拒否
- DEC-999 / ASM-999で `id_space_exhausted`
- 別ownerが明示されている場合はそのownerのcanonical ID lifecycleを使い、Project Contextへ複製・再採番しない

QとUNKの意味的同一性、Q / DEC / ASMのsemantic identity、DECISION内容、ASM承認可否、Project Context以外の正本schema解釈は検証しません。別ownerのIDが未確定ならLLM hand-numberingへfallbackせず正本登録をblockedとします。

question-analysis output templateのcurrent Q tableと `質問ID履歴` はheader-onlyに変更します。Project Contextが正本ownerであるdefault経路ではSection 12 / 13もheader-onlyに変更し、Q-001 / DEC-001 / ASM-001のplaceholder rowを置きません。

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
- 案件固有extension fileの必要性
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

### Step 1: mode責務とdeterministic helperをspec-analysisへ追加

- SKILL.mdに目的ベースの条件付きResource導線
- references/ui-test-target-analysis.md
- required core / 固定triggerの条件付き必須 / 宣言制extensionを分けたpackage assets
- variable structured tableはheader-only、固定applicability rowだけ事前配置し、例示stable IDを置かない
- 09_authority_and_traceability.mdで既存canonical spec-analysis contractを維持
- skills/spec-analysis/scripts/ui_target_package.py（inspect / validate / focused helper群 / materialize / project-eval）
- same package revisionはsingle writerとし、materialize前にinspect snapshotのversion / payload hash一致を確認してstale writeを拒否
- PR #14後の9 Skill-local `runtime_contract.py` へ `acceptance_criterion` / `acceptance_refs` / spec-analysis expected ACをbyte-identicalに追加し、意味契約変更として `RUNTIME_CONTRACT_VERSION` を `runtime-v1` → `runtime-v2`、`ENTITY_SCHEMA_VERSION` を `entity-state-v1` → `entity-state-v2` へ更新
- 09から既存authority_entities.pyへ入力できることを確認
- current ACだけをMachine Entity化し、US / UC / Behaviorをglobal Entity typeへしないことを確認
- helper unit / portability / 9-copy runtime contract byte-identity test
- independent `runtime_validator.py`、active code / Skill文書 / asset / eval fixture / repository testのshared runtime / Machine Entity schema referenceをv2へ同期
- active `skills/spec-analysis/assets/output-template.md`、`skills/test-analysis/assets/output-template.md`、`skills/test-condition-design/assets/output-template.md` の旧手書きMachine Evidence例をversion文字列だけ置換しない
- runtime Skillのtemplateでは、`render_runtime_input()` / `render_runtime_result()` / `render_machine_entities()` が生成するcanonical blockを正本とし、手書きの `runtime-contract-v1` / `runtime-envelope-v1` / `entity_schema_version` / `dependencies` 擬似schemaを削除する
- spec-analysis templateでは `authority_entities.py` / UI target modeの `build-machine-evidence` が生成するcanonical `schema_version / model_key / upstream_entity_dependencies / runtime_dependencies` shapeを正本とし、Machine Entity JSONをAgentに手組みさせない
- shared runtime direct CLIへ `project_v1_cutover` operationを追加し、通常verify / generator経路とは分離する。direct dispatcher、supported skill、16 MiB aggregate / 64 KiB artifact string例外、unknown operationをexact contract化する
- cutover helperはTRD / TCD / TCごとにAgent-side merge不要のcomplete `normalized_runtime_inputs[]` を返し、v1 identity / mapping stateを完成v2 inputへ埋め込む

この時点ではquestion-analysis / qa-workflowは変更しません。

### Step 2: spec-analysis eval

- SPEC-SEM-003～007
- LLM responsibility coverage表に対応するmode固有rubric差分
- production ui_target_package.py `project-eval` のsemantic / deterministic両projection unit test
- `SPEC-OUT-003` package fixtureをdeterministic projectionして既存deterministic runnerへ入力
- projectionしたpackageを既存semantic runnerへ渡せることを確認
- semantic countをspec-analysis=7へ同期
- Agent Skills structure validation

mode単体が成立してからworkflowへ接続します。

### Step 3: question-analysis連携 / DEC・ASM owner採番

- stable UNKNOWN参照
- 回答正規化後のspec-analysis resume
- output templateの関連UNKNOWN ID
- `不明点 / 質問一覧` と `質問ID履歴` をheader-onlyへ変更
- skills/question-analysis/scripts/unknown_links.py
- skills/question-analysis/scripts/question_ids.py（next-id / build-history / materialize）
- Project Context Section 12 / 13が案件の正本ownerであるdefault経路では同tableをheader-onlyへ変更
- skills/qa-workflow/scripts/project_context_ids.py（next-id / validate-history / materialize）
- Project Contextがownerの場合だけnew DEC / ASMの番号をprevious + candidate全状態rowからhelperで決定し、previous ID削除をvalidate-historyで拒否する。意味判断はquestion-analysis / stakeholder側に残す
- 別の決定事項 / 仮定の正本ownerが明示されている場合はそのownerを維持し、Project Contextへ複製・再採番しない
- owner側にdeterministic allocatorがなくID未確定ならLLM hand-numberingへfallbackせず正本登録をblockedにする
- production helper unit / portability test
- deterministic validatorのknown refs / expected mapping
- 既存output fixture 1件へmapping追加 + false-pass unit test
- question semantic caseを2件追加し合計4件へ

### Step 4: test-requirement-design AC traceability / requirement-structure-v2

- generator contractを `requirement-structure-v1` → `requirement-structure-v2` へ更新
- output templateへ `関連AC ID` と上流種別 `Acceptance Criteria` を追加
- guidanceへcurrent AC closure / ACとTRの責務差を追加
- requirement_structure top-levelへ `acceptance_criteria[]`（`ac_id / authority_refs[]`）、TR draftへ `acceptance_refs[]` を必須fieldとして追加
- `acceptance_criteria[].authority_refs[]` はspec-analysis helper結果をそのまま使用し、Agentが再構築しない
- ACなしworkflowは空arrayで明示し、field省略を許可しない
- UI target mode以外の既存spec-analysis normalized inputは `acceptance_criteria` key省略を空集合として許可し、既存Authority expected Entityだけを維持する
- artifact modeでcurrent `spec-analysis / acceptance_criterion` Entityへ依存し、input `authority_refs[]` とAC EntityのAuthority dependency集合をexact一致検証する
- ACをDisposition upstream typeとして許可し、ownerをspec-analysisへ固定
- test-requirement-designまで進むworkflowでcurrent ACをTRまたはDispositionへ閉じる
- AC linkはACだけをclosure済みにし、ACが参照するAuthorityを自動closeしない。Authorityは従来どおりTR `authority_refs[]` またはAuthority Dispositionで独立closureする
- AC→Authority展開はartifact modeのfreshness dependency用であり、Authority closure集合へ暗黙追加しない
- TR Entity contentへacceptance_refsを保存
- artifact modeのTR Entity dependencyへ参照AC Entityと、そのACが参照するcurrent Authority Entity unionを直接保存する。direct modeでは存在しないMachine Entity dependencyを生成しない
- repository内の `requirement-structure-v1` 固定参照をcurrent v2へ同期
- shared runtime-v1 / entity-state-v1 evidenceをruntime-v2 / entity-state-v2 current evidenceとして読み替えない
- cutover後の最初のTRD / TCD / test-case-design等の実行はfull rebuildで行い、v1 previous artifactを通常のpartial rerun / freshness evidenceとして渡さない
- `project_v1_cutover` はv1 Runtime Input / ResultからTRD / TCD / TCのcomplete `normalized_runtime_inputs[]` を生成し、callerがseed patchを元JSONへmergeする経路を作らない
- TR `draft_key ↔ tr_id_map`、TCN `draft_key ↔ tcn_id_map`、model `draft_key ↔ model_key_map`、TC `draft_key ↔ tc_id_map` をexact joinし、reuse ID / previous state / full rebuild scopeをhelperが完成inputへ固定projectionする。Agent / LLMにcutover時のreuse ID選択をさせない
- TCDは既存expected runtime unit builderでroot / model / `artifact:materialize_coverage:<TCN-ID>` 集合を導出し、missing / extra / duplicate / incomplete unitとTCN join不一致をblockedにする
- cutover direct CLIはv1 artifact全文を受けるため16 MiB aggregate transportとartifact string 64 KiB例外を使い、通常generator stdinは2 MiBのまま維持する
- canonical sequenceを `v1検出 → spec/test-analysis v2 evidence再生成 → TRD cutover/full rebuild/save → TCD cutover/full rebuild/save → TC cutover/full rebuild/save → downstream v2 evidence再生成 → validate → 通常update解禁` に固定する
- cutover helper出力だけをfirst v2 generator inputとして使うことで、schema移行とsemantic redesignの同時実行を構造的に禁止する
- v2 evidence成立後にのみ通常partial rerunへ戻す
- AC本文 / 親Behavior / 親UC / 親USのfreshness regressionを追加
- ACをTRへlinkしても、そのACのAuthorityをTR `authority_refs[]` / Authority Dispositionで別途closeしない場合はAuthority unclosedとなるregressionを追加
- artifact modeでAC本文・親chain不変のままAuthorityだけ変更しspec-analysisを再生成した後、未再実行TRが直接Authority dependencyによりstaleになるregressionを追加
- v1→v2 cutoverで内容不変ならTR / TCN / model / CI / TCのstable IDとdeleted / inactive identity historyが不変で、過去IDを再採番しないregressionを追加
- cutoverのdraft_key / *_id_map join不一致、missing / extra / duplicate runtime unit、v1以外のsource version、16 MiB超過、unknown direct operationをblockedにするregressionを追加
- 64 KiB超artifact stringはcutover direct CLIで許可し、通常generatorの2 MiB / string制限へ例外を波及させないregressionを追加
- returned `normalized_runtime_inputs[]` だけでv2 generatorを実行でき、Agent-side field mergeが不要なintegration testを追加
- partial rerunでscope外TRがchanged AC依存のままcurrentにならない regressionを追加
- TR-OUT-003 / TR-SEM-003を追加
- existing TR fixtures / runtime / portability / vertical integration testsをv2 schemaへ同期

### Step 5: qa-workflow routing

- mode request routing
- answer resume
- Step 3で確定したDEC / ASM owner / IDをそのまま利用し、routing段階で再採番しない
- test-target-inspection / usability-evaluation / usability-inspection / wcag-conformance-evaluationとの分岐
- routing_cases.jsonへ8件追加
- routing_candidate_outputs.jsonへ対応する独立candidate 8件追加
- routing fixture合計69件へ同期

### Step 6: package schema / migration / helper contract validation

- current packageが `ui-target-v1` として識別できること
- 全helper operationのexact input / output JSON shape、sort順、failure enum / limit / filesystem safety
- README control section / next-domain-file / Q / DEC / ASM allocator contract
- ui-target-v1専用materializeのdraft/reuse/new/@draft/explicit retire、single-writer stale snapshot、canonical table / known section / standard file materialization契約
- 00 scope / applicabilityのstable ref列とprose根拠列の分離
- 08 repository evidenceのversion間carry-forward / explicit removal契約
- inspect update_snapshot → materialize / focused next-id / impact → explicit retireを含むStable ID changes / 影響fileの更新契約
- build-machine-evidenceのcanonical Machine Entities Markdown section契約
- scope / file applicability、UI操作scopeのUS / UC / Behavior / AC exact schema / closure / AC-only Machine Entity
- exact table schema / stable ref / MANIFEST / Authority + AC Machine Entity bridge / normalized_skill_input
- legacy vNN / unversioned → current schema migration fixture。legacy migrationはempty current-schema target root + single materializeで完成し、暫定CHANGELOGやAgent-side row materializationを要求しないこと
- legacy progress情報がREADME / qa-workflow / CHANGELOGへ正しく分配されること

### Step 7: deterministic / semantic boundary validation

- LLMが意味判断すべき項目をhelperが自動決定していないこと。特にsemantic identity、explicit retire、same-UNK/new-UNK、file trigger、extension要否、DEC/ASM ownerをscriptが推測しないこと
- scope applicability / US / UC / Behavior / ACの意味分類とAC→TRの意味対応をscriptが決定していないこと
- helperがprevious snapshotとcurrent tracking row + LLM明示retire intentからStable ID lifecycle / impact対象ID / 影響fileを決定論生成し、row消失だけをretireにせず、返すimpactは再確認候補であり本文変更必須判定ではないこと
- semantic projectionがcurrent versionの変更概要だけを含み、legacy mapping / UNKNOWN reopen / extension / conditional file / owner判断等のLLM責務がsemantic caseで最低1回評価されること
- normal spec-analysisがmode依存になっていないこと
- helperがSkill package単体コピーで実行できること

### Step 8: cross-repository validation

- 全22 Skill構造
- trigger
- deterministic
- semantic
- routing
- docs current count
- git diff --check

### Step 9: 実Agent smoke

- UI target package scenario（canonical Authority + current AC Machine Entityを含む）
- question-analysis回答反映からspec-analysis package更新までのscenario
- 複数scopeの適用判定からUI操作→US / UC / Behavior / ACを分析しAC→TRまで追跡するscenario
- 親Behavior / UC / US変更でAC fingerprintが変わり関連TRがstaleになるscenario
- AC本文 / 親chain不変のままAuthorityだけ変更しspec-analysisを再生成しても、未再実行TRがstaleになるscenario
- partial rerunでscope外TRがchanged AC参照によりstaleになるscenario
- UI操作はあるが仕様不足のためUNKNOWN / blockedへ止めるscenario
- semantic evaluation projection scenario
- deterministic helperが構造エラーを返してもLLMの意味判断を勝手に上書きしないscenario

### Step 10: final review

次を確認します。

- 新Skillを不必要に追加していない
- spec-analysis / test-target-inspection境界が壊れていない
- repository実装をAuthorityへ昇格していない
- modeなしのspec-analysisが重くなっていない
- question-analysisの分類契約を変更していない
- qa-workflowが詳細ロジックを複製していない
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
- multi-file packageがproduction helperのevaluation projection経由で既存semantic runnerにより評価可能
- version / UNKNOWN件数 / stable ref / MANIFEST / SHA-256 / scope / file applicability / behavior hierarchy / current UCの3分類完全性等の定型整合をproduction helperで検証できる
- test-requirement-designまで進むworkflowではcurrent ACがrequirement-structure-v2でTRまたはDispositionへ閉じ、AC / 親Behavior / 親UC / 親US / Authority変更が関連TR freshnessへ伝播する。仕様理解packageだけの要求ではこのclosureを完了条件にしない
- PR #14後の9 Skill-local `runtime_contract.py` がbyte-identicalのままruntime-v2 / entity-state-v2でacceptance_criterionを扱える
- partial rerunでchanged ACへ依存するscope外TRをcurrent扱いしない
- spec-analysis / question-analysis production helperがSkill package単体で実行可能
- test-target-inspectionへのcurrent UI分岐が維持される
- existing CI / evalが全PASS
- 実Agent smokeがPASS
- current repository counts / docsが同期
- package schema / helper I/O / migration contractが `_06_package-schema-and-helper-contracts.md` と実装で一致
- current version / new stable ID / MANIFEST / hash等、packageから決定論導出できる値をAgentが手作業で再構築していない
- 意味判断を固定するrule engine / generic document framework / ZIP runtimeを追加していない
