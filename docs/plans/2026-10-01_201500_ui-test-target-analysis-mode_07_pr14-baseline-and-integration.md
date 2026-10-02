# UIテスト対象分析モード: PR #14 baseline / integration contract

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

この文書は、PR #16をPR #14マージ後のrepositoryへ実装するためのbaseline、依存関係、routing境界、評価・CI統合の正本です。

対象:
- PR #14: `feat/usability-evaluation-skill`
- PR #16: `feat/ui-test-target-analysis-profile`

## 1. 実装順序

PR #16はPR #14の機能に依存して成立するSkillではありません。

ただしPR #14はrepository baselineとして次を変更します。

- canonical Skill集合
- qa-workflow routing / state contract
- README / EVALS
- deterministic / semantic repository validation
- CIのSkill script compile方式
- UI/UX / live usability / formal WCAGの新しい責務境界

そのため実装順序は固定します。

1. PR #14を完成・mergeする
2. PR #16 branchをmerge後mainへrebaseする
3. Step 0でcurrent repositoryを再計測する
4. 本Planのbaseline contractと一致することを確認する
5. PR #16実装を開始する

PR #14未mergeの旧mainを基準にPR #16実装を開始しません。

## 2. PR #14後のcanonical Skill baseline

PR #14後のcanonical Skill数は22です。

既存19 Skillに次の3 Skillが追加されます。

- `usability-evaluation`
- `usability-inspection`
- `wcag-conformance-evaluation`

PR #16は新Skillを追加しないため、実装後も22 Skillです。

`scripts/skills/evals/deterministic/common.py` のCANONICAL_SKILLSはPR #14後のものをそのまま使用し、PR #16ではSkill追加目的で変更しません。

## 3. 評価baseline

PR #14後のcurrent repositoryで期待する観測値:

- Trigger queries: 488
- Deterministic output cases: 44
- Semantic cases: 155
- qa-workflow routing fixtures: 61

根拠:

PR #14が追加する3 Skill:

| Skill | Trigger | Deterministic | Semantic |
| --- | ---: | ---: | ---: |
| usability-evaluation | 20 | 2 | 12 |
| usability-inspection | 20 | 2 | 33 |
| wcag-conformance-evaluation | 20 | 2 | 38 |
| 追加合計 | 60 | 6 | 83 |

PR #16で追加する差分:

- Trigger: +0
- Deterministic: +2（SPEC-OUT-003 / TR-OUT-003）
- Semantic: +5（spec-analysis +3 / question-analysis +1 / test-requirement-design +1）
- qa-workflow routing: +8

したがってPR #16実装後の期待値:

- Trigger queries: 488
- Deterministic output cases: 46
- Semantic cases: 160
- qa-workflow routing fixtures: 69

ただしこれらはStep 0時点の観測baselineです。repository test / CIでは件数を固定値として正本化せず、PR #14で導入されたcurrent repository / manifestからの動的導出を維持します。

PR #14 merge後に他PRがmainへ入って値が変わっていた場合、実データを正としてPlan / docsの観測値だけ同期します。Skillごとの期待増分（PR #16はTrigger +0 / Deterministic +2 / Semantic +5 / routing +8）は変更理由がない限り維持します。

## 4. PR #14が追加するSkillとの責務境界

### 4.1 usability-evaluation

`usability-evaluation` は保存済みscreenshot / Figma / specification / evidenceをUI pattern、accessibility reference、heuristic等へ照合して評価するSkillです。

UIテスト対象分析モードと入力資料が重なる場合がありますが、目的で分けます。

UIテスト対象分析モード:
- 現在有効な仕様・UI構造・状態・業務ルール・UNKNOWNを整理する
- 後続テスト設計で再利用する対象理解packageを作る
- UI/UX品質の良し悪しを評価すること自体は目的ではない

usability-evaluation:
- 保存済みUI資料 / evidenceを使ってUI/UX上の懸念・適合性・heuristic上の意味評価を行う
- spec-analysisのcanonical Authorityを作るSkillではない

routing例:

- 「Figmaから画面構造、状態、仕様、不明点を整理して」 → spec-analysis UIテスト対象分析モード
- 「FigmaをUI/UX観点で評価して」 → usability-evaluation
- 「screenshotを対象理解packageへ反映して」 → spec-analysis UIテスト対象分析モード
- 「screenshotの情報階層・ラベル・UXを評価して」 → usability-evaluation

### 4.2 usability-inspection

`usability-inspection` はlive browserを操作し、ユーザビリティ、general accessibility、responsive、feedback、performance等を証拠付きで検査します。

境界:

- current UIの名称・構造・到達方法・現在のふるまいを対象理解のために観測 → test-target-inspection
- live UIを操作して使いやすさ、focus、responsive、feedback等を評価 → usability-inspection
- spec / Q&A / repositoryから期待挙動を整理 → spec-analysis UIテスト対象分析モード

UIテスト対象分析モードはbrowser/sessionを所有しません。

### 4.3 wcag-conformance-evaluation

`wcag-conformance-evaluation` はWCAG-EM 2.0に沿うformal Web conformance evaluationのownerです。

境界:

- accessibilityに関係する仕様要件・UI構造を対象理解packageへ整理 → spec-analysis UIテスト対象分析モード
- 特定画面をlive UIでgeneral accessibility検査 → usability-inspection
- WCAG version / levelを指定したformal適合性評価 → wcag-conformance-evaluation

UIテスト対象分析モードがformal WCAG評価やclaimを代替しません。

## 5. #14成果物とspec Authorityの関係

次の#14成果物は、それ自体ではSPEC / DECISION / approved ASMへ自動昇格しません。

- usability-evaluation finding
- usability-inspection observation / measurement
- wcag-conformance-evaluation result / report / EARL

扱い:

1. 対象理解の補助evidence、実装 / UI観測、issue候補として参照できる
2. 既存Authorityと矛盾する場合は差分 / pending / UNKNOWNとして扱う
3. product requirementを変更する必要がある場合はquestion-analysis / stakeholder decisionへ送る
4. 正規化されたSPEC / DECISION / approved ASMだけをspec-analysis canonical Authorityへ反映する

例外:
- project contextでformal WCAG requirement自体がAuthorityとして明示されている場合、そのrequirementはAuthorityとして扱える
- WCAG評価結果そのものをproduct仕様へ自動変換することはしない

## 6. qa-workflow routing追加

PR #14の61 routing fixturesをbaselineに、PR #16では8 caseを追加して69件を想定します。

既存5 case:
1. 対象理解packageだけ欲しい → spec-analysis mode
2. 回答反映後にpackage更新 → question-analysis → spec-analysis mode
3. current live target情報だけ必要 → test-target-inspection
4. repository実装確認だけ → spec-analysis補助入力
5. 対象理解後にテスト分析も要求 → spec-analysis mode → test-analysis

PR #14境界として追加する3 case:
6. 保存済みFigma / screenshotをUI/UX評価 → usability-evaluation
7. live browserで使いやすさ / focus / responsiveを検査 → usability-inspection
8. formal WCAG version / levelで適合性評価 → wcag-conformance-evaluation

`routing_cases.json` と `routing_candidate_outputs.json` の双方へ独立に追加します。

candidateをexpected routingから生成しません。

## 7. qa-workflow統合

PR #14後の `skills/qa-workflow/references/guidance.md` を編集baselineとします。

PR #16では次だけを追加します。

- 「仕様整理だけ」のうち、継続的なUI対象理解packageが必要な場合のspec-analysis mode選択
- question-analysis回答後のspec-analysis mode resume
- test-target-inspection / usability-evaluation / usability-inspection / wcag-conformance-evaluationとの目的境界
- #14成果物をAuthorityへ自動昇格しない規則

PR #14が追加した以下を複製・変更しません。

- WCAG observation handoff
- browser/session ownership
- claim / reservation / CAS
- usability-inspection runtime
- formal WCAG procedure
- artifact_graph.pyのhandoff lifecycle

UIテスト対象分析モードはspec-analysis内部modeであるため、新しいworkflow state row / handoff type / claim / reservationを追加しません。

## 8. CI統合

PR #14後の `.github/workflows/deterministic-output-evals.yml` はcurrent Skill packageの `skills/*/scripts` を動的探索してcompileします。

そのためPR #16では、`ui_target_package.py` / `unknown_links.py` をcompile対象へ追加するためのSkill固有workflow editを行いません。

追加するもの:

- repository unit test
- runtime / helper integration test
- standalone Skill package portability test
- SPEC-OUT-003
- semantic cases / criteria coverage
- routing fixture

既存workflowがcurrent script directoryを自動compileすることを利用します。

新しいGitHub Actions workflowは追加しません。

## 9. semantic repository test統合

PR #14後のsemantic repository testはcurrent repository / manifestからSkillとcase数を動的導出します。

PR #16では全体case数の固定assertを追加しません。

追加するrepository contract:

- spec-analysisで今回追加するcritical semantic criterionが最低1 caseにcoverageされる
- question-analysisで今回追加するcritical semantic criterionが最低1 caseにcoverageされる
- 既存normal spec-analysis caseが不要にUIテスト対象分析モードへ昇格しない

PR #14が追加した usability / WCAG semantic criteriaのcoverage logicを壊しません。

## 10. README / EVALS / PROJECT_CONTEXT

PR #14後の内容を編集baselineにします。

PR #16で追加するのは:

README:
- spec-analysisに条件付きUIテスト対象分析モードがあること
- 新Skillではないこと
- usability-evaluation等との目的境界を必要最小限に記載

EVALS:
- SPEC-OUT-003
- spec-analysis / question-analysis semantic差分
- qa-workflow routing 8件追加
- multi-file projection / helper評価境界

PROJECT_CONTEXT:
- current repository状態を保持している場合だけmode / helper / current evaluation観測値を同期

PR #14のUI/UX / WCAG説明を再記述・置換しません。

## 11. common deterministic runtime

PR #14後の `scripts/skills/evals/deterministic/common.py` をbaselineとします。

PR #16は新Skillを追加しないため `CANONICAL_SKILLS` を変更しません。

UIテスト対象分析モード固有のPAGE / STATE / VIEW / MODAL等のIDはspec-analysis mode固有validator / helperで扱い、既存共通 `ALL_ID_RE` を不用意に拡張しません。

共通IDとして全Skillが参照すべき要件が実装中に発生した場合だけ、目的と影響を明示してcommon変更を再検討します。現Planでは不要です。

### 11.1 shared runtime baseline

PR #14確認headにはSkill-local `runtime_contract.py` が9コピー存在します。

- PR #11由来の既存repository byte-identity test対象: spec-analysis / test-analysis / test-requirement-design / test-condition-design / test-case-design / coverage-analysis / qa-workflow の7コピー
- PR #14で追加された再利用copy: usability-inspection / wcag-conformance-evaluation の2コピー

確認headでは9コピーは同一blobですが、既存 `tests/skills/runtime/test_runtime_dispatch.py` のbyte-identity対象は7コピーだけです。PR #16では同じ `runtime-v1` helper契約をSkillごとに分岐させないため、current shared runtime 9コピーを同期対象へ統一し、repository byte-identity testも9コピーを対象にします。

Step 0で次を実測します。

- 9コピーの実path、byte identity、repository testの対象集合
- `ALLOWED_ENTITY_TYPES` に `acceptance_criterion` がまだ存在しないこと
- spec-analysis `_expected_entities()` がAuthorityだけを導出するbaselineであること
- test-requirement-designのgenerator contractが `requirement-structure-v1` であること
- Disposition upstream typeがAuthority / Product Risk中心のbaselineであること

PR #16はこのbaselineへ `_09_runtime-entity-and-test-requirement-contracts.md` の変更を適用します。#14 merge後mainで上記が既に変わっていた場合、実装を開始せずPlanをcurrent contractへ同期します。
## 12. rebase / conflict gate

PR #14 merge後、PR #16実装開始前に次を必須確認します。

1. #16 branchをlatest mainへrebase
2. textual conflictを解消
3. current Skill数をrepositoryから導出
4. trigger / deterministic / semantic case数をmanifestから導出
5. qa-workflow routing fixture数を確認
6. PR #14のREADME / EVALS / qa-workflow / CI contractがPlan記載と一致すること
7. spec-analysis / question-analysis / test-target-inspectionが#14後に追加変更されていないこと
8. 9 runtime_contract.py / requirement_structure.py / qa-workflow expected Entity contractが§11.1 baselineと一致すること
9. baselineに差分があれば、本Planを実データへ同期してから実装開始

rebase前の旧mainとの差分を正として実装判断しません。

## 13. 完了条件

- PR #14 merge後mainから実装されている
- canonical Skill集合22を壊さず、新Skillを追加していない
- #14のUI/UX / live inspection / WCAG責務を侵食していない
- #14のbrowser handoff / workflow state / artifact graphを複製していない
- #14成果物を仕様Authorityへ自動昇格していない
- routingで対象理解とUI/UX評価 / live inspection / formal WCAGを区別できる
- evaluation / CIは#14の動的導出方式を維持している
- #16固有のexpected増分がDeterministic +2 / Semantic +5 / routing +8で説明できる
- shared runtime / requirement-structure-v2の変更がPR #14後baselineとの差分として明示され、current shared runtime 9コピーbyte identityを維持している
