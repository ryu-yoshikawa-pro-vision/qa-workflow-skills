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

PR #16後の期待増分:
- Skill: +0
- Trigger: +0
- Deterministic: +2
- Semantic: +5
- routing: +8

したがってStep 0時点の期待値は 22 Skill / 488 trigger / 46 deterministic / 160 semantic / 69 routingです。ただしCI / repository testでは固定値を正本化せず、PR #14のcurrent repository / manifestからの動的導出を維持します。

## 2. 評価方針

新しい評価frameworkは作りません。

既存の4層を維持します。

1. Agent Skills仕様 / repository structure validation
2. trigger selection validation
3. deterministic output / routing validation
4. semantic evaluation

今回の中心は意味分析なのでsemantic evalを主とします。同時に、`05_llm-deterministic-boundaries.md` で定型処理とした形式・参照・件数・version・MANIFEST / hash等はSkill-local production helperとdeterministic / repository testで扱います。意味判断そのものはscriptへ移しません。

## 3. spec-analysis semantic eval

現在spec-analysisは2 semantic caseです。

3 caseを追加し、spec-analysisは現在2件から5件へ増やします。case IDは既存命名規則に合わせて `SPEC-SEM-003` ～ `SPEC-SEM-005` を使用します。

### case A: 複数資料からUI target packageを構成

入力:
- 複数PAGE
- same-routeであることが明示されたVIEW / STEP
- route未確定の別画面候補
- MODALとbrowser dialog
- 同時成立可能な直交STATE
- field validation
- notification / external interaction
- Q&A decision
- 複数の分析対象機能scope（UI操作あり / なし / 未確定を含む）
- 複数のユーザーUI操作
- 正常 / 準正常 / 例外のうち、定義あり / なし / 未定義が混在するUse Case
- repository補助情報と仕様-実装差分
- 1件以上のUNKNOWN
- 一部矛盾

期待:
- UI target modeを選ぶ
- SPEC / DECISION / INFERENCE / UNKNOWNを区別
- 明示same-routeはVIEW / STEPとして扱い、route不明は推測統合しない
- MODALとbrowser dialogを分離する
- 直交STATEを無理に排他化しない
- field / notification / external interactionを仕様上該当する構造化viewへ整理する
- repository差分を実装状況へ分離
- scopeごとのUI操作判定を行い、UI操作ありscopeでUI操作母集団を抽出してUS → UC → Behavior → ACの順で分解する
- UI操作があるのに資料不足の場合はnot-applicableへ逃げずUNKNOWN / blockedへする
- 各current UCで正常 / 準正常 / 例外を全て検討し、なし / 未定義を区別する
- blocked UCへ無意味な3分類を生成しない
- 非操作起点のUI挙動をnot-applicableを理由に落とさない
- ACで具体値・組合せ・テストケースへ先回りしない
- canonical stable itemへの追跡を維持する
- test condition / caseへ進まない

### case B: repository実装が仕様と違う

期待:
- 高Authority仕様を実装に合わせて変更しない
- spec-implementation gapとして分離
- 実装をAuthorityへ自動昇格しない
- 「不具合」と断定する必要がない場合は差分として扱う

### case C: versioned package更新

入力:
- v03 package
- 既存UNK
- 正式回答
- 新しい資料差分

期待:
- v04完全版
- 同じUNK lineage
- 解消済みをcurrent unknownから除外し、意味上そのUNKNOWNを解消したcurrent Authorityを`解消先ID`へ記録する
- README / current unknown / changelog / manifestの意味整合
- 差分だけを最終成果物にしない

semantic rubricへはmode固有の次の観点だけを追加し、既存SPEC criteriaと重複させません。既存SPEC-SEM-001 / 002にも「要求が通常spec-analysisで足りる場合に不要なUI target packageへ昇格しない」回帰観点を適用し、mode追加による過剰出力を防ぎます。

- canonical modelと構造化ビューの追跡性
- UI構造分類の妥当性
- implementation status分離
- versioned package更新の整合
- resolved UNKNOWNと`解消先ID`の意味的対応
- scope適用判定の妥当性
- UI操作scopeのUS / UC / Behavior / AC分解の完全性
- UI操作がないscopeでの非適用判断の妥当性
- 非操作起点UI挙動を通常spec-analysisへ残す妥当性

### 複数Markdown packageのevaluation projection

既存 `scripts/skills/evals/semantic/run.py` / deterministic runnerはいずれも1つの `--output` fileを受けるため、runner自体はdirectory対応へ変更しません。

production `skills/spec-analysis/scripts/ui_target_package.py project-eval` を使用し、projection modeを分けます。

semantic projection:

- README
- 00〜09
- 10+ current domain files
- CHANGELOG / MANIFESTは除外
- 過去仕様を含むCHANGELOGをsemantic Judgeへ混ぜない

deterministic projection:

- 全payload file
- MANIFESTを最後にcontrol fileとして追加
- version / file set / hash / stable ref等のmode contractを1 Markdown上で評価可能にする

共通:

1. package root外path / symlink / duplicate / missing fileを拒否する
2. canonical file orderを使用する
3. 各fileの前に `<!-- FILE: <relative-path> -->` markerを付ける
4. UTF-8 textをそのまま連結し、内容の要約・意味変換を行わない
5. projectionは評価用transportであり、production packageやAuthorityを変更しない

semantic / deterministicで同じprojection helperを使いますが、expected判定は各eval validator / rubricが独立して行い、production helper出力からexpectedを逆算しません。

## 4. question-analysis semantic eval

1 caseを追加し、question-analysisは現在2件から3件へ増やします。正式回答 / 暫定回答とUNKNOWN lineageを同時に扱うcaseを1件だけ追加します。

重点:

- 元UNK IDを保持する
- 暫定回答を勝手にDECISIONへしない
- 正式回答後にspec-analysisへ戻す
- 回答済み論点を再質問しない
- current unknownとresolved historyを混同しない

question-analysisの既存分類ロジックを変更しないため、trigger datasetは変更しません。関連UNKNOWN IDの意味的対応はsemantic case、形式・既知参照・duplicateはproduction `unknown_links.py`、fixture mappingは独立deterministic validatorで検証します。

spec-analysis / question-analysisで今回追加するcritical semantic criterionは、各criterionが最低1 semantic caseから参照されることをrepository testで検証します。既存normal spec-analysis caseにもmode非選択回帰を含めます。

## 5. test-requirement-design semantic eval

1 caseを追加し、test-requirement-designはPR #14後の2件から3件へ増やします。case IDは `TR-SEM-003` とします。

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
- build-manifest
- impact
- build-machine-evidence
- project-eval

repository unit testで次を必須確認します。

- required core / 条件付き必須file applicability / extension file declaration
- package root外path拒否
- package内version一致
- canonical / structural ID形式・duplicate
- structured rowのexact stable ID参照
- 09のcurrent UNKNOWN集合と07 / README件数の一致
- MANIFEST file set / order / SHA-256
- README file一覧とMANIFESTの一致
- CHANGELOG最新version見出しとpackage versionの一致
- domain file命名
- next-idがsemantic identityを判断せず、new指定後にpackage rootから既知IDを内部導出して次番号を返し、Agentへknown ID集合を要求しないこと
- resolved UNKNOWNの `解消先ID` がcurrent SPEC / DECISION / 承認済みASMへ閉じること
- canonical structured Markdownのduplicate heading / table、row列数、escaped pipe、`<br>` referenceを固定parse契約で検証すること
- impactがexact referenceだけから候補fileを返し、semantic変更を勝手に決定しないこと
- scope applicability、UI操作scopeのUIOP / US / UC / Behavior / AC hierarchy / closure / current UCの3分類整合
- 09の「現在有効な仕様根拠」からnormalized Authorityを固定projectionし、build-machine-evidenceがAuthority + current AC Entity、spec-analysis normalized_skill_input、expected identityを決定論生成すること
- `Machine Entities: spec-analysis` blockがexactly one存在し、helper再生成結果と一致すること
- 親US / UC / Behavior変更でAC Entity fingerprintが変わること
- project-evalが内容を変更せずcanonical順に連結すること

### 8.2 question-analysis production helper

`skills/question-analysis/scripts/unknown_links.py` を追加し、次を検証します。

- UNK ID形式
- current known UNKNOWNへの存在参照
- 同一Q内duplicate
- current / resolved集合が入力された場合のresolved-only参照

QとUNKの意味的同一性は検証しません。

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

最低限:

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
- semantic case: 155 → 160
  - spec-analysis: 2 → 5
  - question-analysis: 2 → 3
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
- 09_authority_and_traceability.mdで既存canonical spec-analysis contractを維持
- skills/spec-analysis/scripts/ui_target_package.py
- repository内のcurrent shared runtime 9 Skill-local `runtime_contract.py` へ `acceptance_criterion` / `acceptance_refs` / spec-analysis expected ACをbyte-identicalに追加
- 09から既存authority_entities.pyへ入力できることを確認
- current ACだけをMachine Entity化し、US / UC / Behaviorをglobal Entity typeへしないことを確認
- helper unit / portability / runtime contract byte-identity test

この時点ではquestion-analysis / qa-workflowは変更しません。

### Step 2: spec-analysis eval

- SPEC-SEM-003～005
- mode固有rubric差分
- production ui_target_package.py `project-eval` のsemantic / deterministic両projection unit test
- `SPEC-OUT-003` package fixtureをdeterministic projectionして既存deterministic runnerへ入力
- projectionしたpackageを既存semantic runnerへ渡せることを確認
- semantic countをspec-analysis=5へ同期
- Agent Skills structure validation

mode単体が成立してからworkflowへ接続します。

### Step 3: question-analysis連携

- stable UNKNOWN参照
- 回答正規化後のspec-analysis resume
- output templateの関連UNKNOWN ID
- skills/question-analysis/scripts/unknown_links.py
- production helper unit / portability test
- deterministic validatorのknown refs / expected mapping
- 既存output fixture 1件へmapping追加 + false-pass unit test
- question semantic caseを1件追加し合計3件へ

### Step 4: test-requirement-design AC traceability / requirement-structure-v2

- generator contractを `requirement-structure-v1` → `requirement-structure-v2` へ更新
- output templateへ `関連AC ID` と上流種別 `Acceptance Criteria` を追加
- guidanceへcurrent AC closure / ACとTRの責務差を追加
- requirement_structure top-levelへ `acceptance_criteria[]`、TR draftへ `acceptance_refs[]` を必須fieldとして追加
- ACなしworkflowは空arrayで明示し、field省略を許可しない
- artifact modeでcurrent `spec-analysis / acceptance_criterion` Entityへ依存
- ACをDisposition upstream typeとして許可し、ownerをspec-analysisへ固定
- test-requirement-designまで進むworkflowでcurrent ACをTRまたはDispositionへ閉じる
- TR Entity content / dependencyへacceptance_refsを保存
- repository内の `requirement-structure-v1` 固定参照をcurrent v2へ同期
- v1 evidenceをv2 current evidenceとして読み替えない
- AC本文 / 親Behavior / 親UC / 親US / Authority変更のfreshness regressionを追加
- partial rerunでscope外TRがchanged AC依存のままcurrentにならない regressionを追加
- TR-OUT-003 / TR-SEM-003を追加
- existing TR fixtures / runtime / portability / vertical integration testsをv2 schemaへ同期

### Step 5: qa-workflow routing

- mode request routing
- answer resume
- test-target-inspection / usability-evaluation / usability-inspection / wcag-conformance-evaluationとの分岐
- routing_cases.jsonへ8件追加
- routing_candidate_outputs.jsonへ対応する独立candidate 8件追加
- routing fixture合計69件へ同期

### Step 6: package schema / migration / helper contract validation

- current packageが `ui-target-v1` として識別できること
- helper CLI JSON contract / failure / limit / filesystem safety
- scope / file applicability、UI操作scopeのUS / UC / Behavior / AC exact schema / closure / AC-only Machine Entity
- exact table schema / stable ref / MANIFEST / Authority + AC Machine Entity bridge / normalized_skill_input
- legacy vNN → current schema migration fixture
- legacy progress情報がREADME / qa-workflow / CHANGELOGへ正しく分配されること

### Step 7: deterministic / semantic boundary validation

- LLMが意味判断すべき項目をhelperが自動決定していないこと
- scope applicability / US / UC / Behavior / ACの意味分類とAC→TRの意味対応をscriptが決定していないこと
- helperが返すimpactは再確認候補であり変更必須判定ではないこと
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
- repository内のcurrent shared runtime 9 Skill-local `runtime_contract.py` がbyte-identicalのままacceptance_criterionを扱える
- partial rerunでchanged ACへ依存するscope外TRをcurrent扱いしない
- spec-analysis / question-analysis production helperがSkill package単体で実行可能
- test-target-inspectionへのcurrent UI分岐が維持される
- existing CI / evalが全PASS
- 実Agent smokeがPASS
- current repository counts / docsが同期
- package schema / helper I/O / migration contractが `_06_package-schema-and-helper-contracts.md` と実装で一致
- 意味判断を固定するrule engine / generic document framework / ZIP runtimeを追加していない
