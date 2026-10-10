# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` の実装順と完了条件を固定します。

## PR #14 validation scope amendment（2026-10-08）

root Planの「PR #14 / PR #17 評価責務の追補」を優先します。WCAG version / level、WCAG-EM、procedure、sample、report / EARL、fail-closedの意味上の契約は変更しません。

- `_05f` / `_05h` の全semantic caseはdatasetとrepository contract testに保持し、全caseの実Agent candidate / Judge評価はPR #17の継続評価へ移管します。PR #14ではsemantic dataset validation、deterministic / runtime / repository semantic tests、および最低1件のreal-Agent smokeを行います。
- `wcag-conformance-evaluation` descriptionを変更した`WCAG-TR-TRA-002`を3回fresh実行します。明確に隣接する既存negative boundaryがある場合だけ各3回追加し、Skill-read eventと`EVALS.md` thresholdで判定します。full native trigger統計・holdoutはPR #14 gateではなく、PR #17にも含めません。
- repository fixtureの全criterion / procedure resultを埋めることはcompletion gateではありません。current result不足時は部分結果とmissing evidence / procedure resultを明示したままreport closureを`blocked`で保つpartial-blocked状態とし、Step 5.3のrequired input不足時はStatementを生成せず、与えられたcurrent formal resultからEARLを生成・独立検証することをfail-closed gateとします。
- browser E2Eは代表formal handoff lifecycleを1経路確認し、finite inventory、全version / SC / procedure permutation、集合演算とclosure boundaryの全組合せはdeterministic testsをownerとします。

## 1. 実装開始条件

- PR #11 merge済みcurrent runtime確認
- PR #12はmainへmerge済みでcurrent実装を確認済み
- PR #13 main merge済み
- usability-inspectionのgeneral accessibility / `_05g` browser observation request / probe contract成立
- 実装開始前にbranchをcurrent main `dec3f7c764db2869dc24eb3d6f154712a6677068` 以降へ同期し、PR #15反映後のqa-workflow template / guidance / deterministic contractを再確認する。`workflow-state-template.md` のenvelope同期は既にmainで完了しているため再実装しない。`_04c` formal observation handoff state / CAS contractをそのcurrent qa-workflowへ適用し、production local filesystemはconditional writeを提供しない事実を維持し、canonical E2E用test-only SQLite providerをproduction能力と混同しない
- WCAG-EM 2.0 / WCAG 2.0 / 2.1 / 2.2 current official source確認
- repository標準eval / CI確認

## 2. Step 0: baseline

latest mainで、

- Skill一覧
- Activity / artifact identity
- browser ownership
- evidence safety
- side-effect / cleanup
- Finding
- qa-workflow routing
- Playwright execution path

を再確認します。

## 3. Step 1: package / source

`_05f_wcag-conformance-evaluation-package-and-runtime.md` のpackageを作ります。

source-catalogへ少なくとも、

- WCAG 2.0
- WCAG 2.1
- WCAG 2.2
- WCAG-EM 2.0
- WCAG-EM Report Tool。WAI Overview上の公式resourceとして保持するが、WCAG-EM 2.0本文と同一の成果物schemaを提供することは前提にせず、WCAG-EM 2 schema Authorityにはしない
- WCAG Overview
- How to Meet WCAG 2 (Quick Reference)
- Understanding Conformance
- Guidance on Applying WCAG 2.2 to Mobile Applications（current Web targetへresponsive / touch / mobile Webが含まれる場合）
- ACT Rules Format 1.1 / All ACT Rules
- EARL 1.0 Schema
- Understanding Accessibility Support

をcurrent URL / status / checked_at付きで登録します。

## 4. Step 2: output contract

browser操作前にoutput-templateとvalidator最小schemaを実装します。

WCAG-EM 2のoutput contractはReport ToolのschemaではなくWCAG-EM 2.0本文を正本にします。Step 5.1 outcome closure、Step 5.2 Evaluation Specifics、Step 5.3 Evaluation Statement、Step 5.5 machine-readable reportを別契約として固定します。Step 5.4 aggregated scoreだけは目的外です。

先に次をfixtureで固定します。

- required Input
- supported WCAG version = 2.0 / 2.1 / 2.2 / explicit unsupported or out-of-scope version / missing versionの状態分離
- version別static requirement catalog / target level expected set / canonical hash
- runtime envelope / input / generation fingerprint / freshness
- canonical sample identity registry
- candidate population fingerprint
- evaluation header / previous evaluation lineage
- Step 1.1 scope coverage rows
- Step 1.4 additional evaluation requirement ref / affected step / status / output closure
- accessibility support baseline revision / extension
- exploration
- sampling procedure used / skipped
- selected sample set
- sampling used時のstructured / random sample
- 再評価時のretained / replaced / added / unavailable sample lineage
- sampling skipped時のcomplete inventory closure
- complete process
- Conforming Alternate Version / Non-Interference固定rule
- Step 4.2 unchanged-result reuse
- sample result
- sampling used時のStep 4.3 comparison
- Step 5.1 report outcome closure / not-satisfied example coverage / accessible output contract
- Step 5.2 Evaluation Specifics / archive identity / tool metadata / secret safety
- Step 5.3 Evaluation Statementはtarget WCAG 2.2だけでfull / partial minimum fields / generation guard。2.0 / 2.1ではsection非生成
- WCAG Conformance Claim required / optional fields / version別claim URI / full-scope coverage / third-party 2-business-day monitoring-repair guard
- WCAG Statement of Partial Conformance - Third Party Content / Language required fields / canonical wording / generation guard
- Step 5.5 EARL JSON-LD output / assertion coverage

## 5. Step 3: production helper

`runtime_contract.py`、`wcag_requirements.py`、`wcag_criterion_plan.py`、`sampling.py`、`wcag_em_structure.py`、`earl_report.py` を実装します。`runtime_contract.py` はPR #11のcurrent契約を再利用し、独自runtime frameworkは追加しません。

### requirements

- supported WCAG versionを2.0 / 2.1 / 2.2へ固定
- `assets/wcag-2.0-requirements.json` / `wcag-2.1-requirements.json` / `wcag-2.2-requirements.json` からtarget versionだけを選択
- A / AA / AAAごとのrequired Success Criteria集合と5つのconformance requirement集合を導出
- Conforming Alternate Version required condition keys / reachability alternatives、Non-Interference固定Success Criteria refs、Full Pages / Complete Processes / Accessibility-Supportedの固定rule metadataを導出
- source canonical URLとは別にversion別claim guideline title / version / URI、third-party repair window = 2 business daysを保持
- versionごとのcanonical JSON SHA-256を `static_data_versions.wcag_2_0_requirements` / `wcag_2_1_requirements` / `wcag_2_2_requirements` へ出力
- validatorは選択versionのassetからhashを独立再計算
- 3 requirement catalogそれぞれについてW3C正本と照合済みの承認済みhashをcontract testで固定
- `wcag-evaluation-procedure-catalog.json` のcanonical hashを `static_data_versions.wcag_evaluation_procedures` へ保持し、承認済みhashをcontract testで固定
- version未指定・不明は `unresolved`、現在catalogを持たない将来version等は `unsupported`、WCAG 3はout-of-scope
- actual result coverageをLLM supplied listではなくtarget versionのstatic expected setと比較

### Success Criterion evaluation plan

`_05h_wcag-criterion-evaluation-contract.md`、`_05i_wcag-success-criterion-procedure-inventory.md`、`_05j_wcag-machine-browser-observation-contract.md`、`_05k_wcag-semantic-procedure-contract.md` を実装します。

- `_05i` のversion別集合からWCAG 2.0=61 / 2.1=78 / 2.2=86件を固定し、2.2から4.1.1を除外する
- `_05i` の生成規則から全Success Criterionのexpected `procedure_keys` をscriptで導出し、3 versionのrequirements assetへ設定する。実装時にcriterionごとのprocedure構成を再設計しない
- `assets/wcag-evaluation-procedure-catalog.json` を追加し、`_05i` に現れる全procedureを `machine / semantic / manual / assistive-technology / external-evidence` の有限inventoryへ固定する。各rowに `_05h` の `applicability_mode / applicability_decision_key / activation_source_procedure_key / activation_limitation_codes` を持たせる。external-evidence procedureは3件とも `applicability_mode=external-evidence-available` に固定する
- procedure catalogに `TBD / other / custom` 等のcatch-allを置かず、`_05i` §3のmachine procedureは全件明示dispatch / fixtureを実装する。各machine procedureのbrowser入力はprocedure catalog内で `_05j` machine probe keyへ全件mappingし、`wcag_criterion_plan.py` がtyped `wcag-machine-probe` requestをmaterializeする。formal runtimeはinspection sibling assetをreadしない。cross-packageのprobe key missing / extra / unused 0はrepository-level contract testで検証する
- `_05k` のversioned semantic contract assetを全supported Success Criterionへ作成し、normative clause / definition / exception refs、semantic evaluation point、required evidence role、forbidden shortcutをapproved hashで固定する。1.3.1 / 1.3.2 / 4.1.2 / 4.1.3には `_05i` のfixed AT applicability decision keyに対応する `procedure_applicability_contracts[]` をversion別に追加し、AT result / final semantic resultをInputへ含めない。実装時にcriterion固有procedureを再設計しない
- 4.1.1はWCAG 2.2でrowを作らず、WCAG 2.0 / 2.1 + HTML/XMLでは `always-satisfied-html-xml`、その他technologyではsemantic contractへ戻す
- machine化できる数値計算、集合演算、固定enum / state比較、supported ACT Ruleをsemantic / manualへ逃がしていないことをsemantic reviewで確認する
- assistive technologyはSuccess Criterion固定booleanにせず、selected procedure + current content / technology + accessibility support baselineから**AT実行前**のfixed semantic applicability decisionを閉じる。`unknown → applicability decision → AT execution（applicable時だけ）→ final s-wcag semantic` の順序を固定し、final semantic resultをAT applicabilityのInputへ戻さない
- procedure executionごとに `applicable / not-applicable / unknown` とbasisをmaterializeし、`unknown` のままcriterionをsatisfied / not-satisfiedへ閉じない。final semantic required evidence roleはcurrent applicable procedure集合から導出し、not-applicable sibling resultを要求しない
- external evidence candidate refsをsource / revision / environment / freshness / scopeでscript検証し、candidate 0件またはcurrent scope matching evidence 0件ならexternal procedureをnot-applicableへ閉じる。valid current evidenceが1件以上ある場合だけapplicable化し、外部証拠不足だけでcriterionをundetermined / blockedにしない
- semantic assetのstatic `required_evidence_roles` にはprocedure-result roleを書かず、machine / manual / AT / external result roleはcurrent applicable procedure集合からruntime effective roleとしてscript追加する
- `_05i` のcontrast / Resize Text / Focus Appearance conditional manual fallbackをsource machine limitation codeからscriptが起動し、machine limitationだけでcriterionをblockedへ短絡しない
- selected sampleごとのrequired presentation variation集合を入力にし、`wcag_criterion_plan.py` がsample × variation × required Success Criterion rowを全件materializeする
- execution status `pending / in-progress / complete / blocked` とresult `satisfied / not-satisfied / undetermined / null` を分離する
- applicable population `present / none / unknown` はcriterion-specific semantic population discovery / applicability resultから導出し、procedure applicabilityから逆算しない。単一ACT Ruleのinapplicableだけでcriterion satisfiedにしない
- live observation requirementをformal handoffへ渡す
- target geometry / spacing、contrast ratio、viewport overflow / reflow数値、elapsed / threshold、supported ACT Rule等、入力が揃えば決定論的な処理をscriptへ移す
- required criterion × variation集合とactual row集合の差分0をdeterministic validatorで検証する
- supported ACT Ruleがないcriterionもsemantic / manual / AT procedureで評価対象から落とさない。external evidenceはcurrent valid evidenceがある場合だけ補助procedureとして追加closureし、存在を必須条件にしない
- external evidence candidateなし、全candidate stale / scope mismatch、valid candidateありの3caseをfixture化し、前2caseはnot-applicable +他procedureでclosure継続、valid caseだけexternal procedure resultを要求する
- `external_evidence_allowed=false` のcriterionへexternal procedureが混ざるassetをinvalidとしてrejectする
- required evidence不足は `undetermined / blocked` とし、LLM推測で閉じない
- final Success Criterion resultはcurrent criterion evaluation refからだけmaterializeし、LLM supplied result listを別経路で受け付けない

`presentation variation registry → criterion plan → observation handoff → returned evidence → procedure closure → criterion result → sample / conformance requirement result` の順序を固定します。

### sampling

- current `test-target-inspection` の対象 / 状態キー、またはsemantic同一性decisionからcanonical artifact-local sample identity registryをmaterialize
- duplicate / overlap / union / process membershipをcanonical sample identityで判定
- 再評価ではprevious sample identityをcurrent targetへ解決し、structured sampleをretained / replaced / added / unavailableへmaterializeする。replacement ratioは固定せず、significant change / representativenessはsemantic判断、random replacementはscript / external random mechanismへ委ねる
- complete inventoryとsemantic decisionから製品全体をselected sample setへmaterializeし、sampling procedureをskipする経路
- sampling skippedではstructured / random / Step 4.3をnot-applicableとして閉じるが、complete process / Step 4.2評価は継続
- 10% count計算。WCAG-EM本文の丸め規則ではなく本Planの `ceil` 規則として扱い、structured count 1 / 9 / 10 / 11の境界fixtureを持つ
- finite inventoryからrandom candidate集合を導出し、structured sampleを除外
- candidate scope / inventory / provenanceからcandidate population fingerprintを導出
- target全体を有限列挙できない場合、LLMはmethod / provenanceだけを判断し、candidate listがあればscript、外部tool自体がrandom selectionする場合は外部random mechanismにsample identity選択を任せる
- duplicate / overlap検証
- optional random select
- fixed seed禁止
- complete process sequenceからsample union / process-added sampleを導出
- normalized content type / Finding group keyの集合差分からStep 4.3 boolean / actionを導出
- structured sample更新後のrandom target再計算。population fingerprint同一ならoverlap除外 / current random保持 / 不足分top-up、population変更なら旧random setをstaleとして再選択
- process再materialize
- 既存sample resultはPR #11 freshnessがcurrentの場合だけ再利用し、version / level / scope / baseline / environment / sample identity / evidence / catalog hash / upstream dependency変更では再評価
- Step 4.2ではidentity / evidence / freshnessでcurrentなunchanged content resultだけを再利用し、changed / unknown contentとinteraction / feedbackを再評価
- selection method記録
- random selection status `target-met / exhausted-no-new-view / blocked`。complete finite inventoryまたはscope-wide exhaustion evidenceがある場合だけ `exhausted-no-new-view` でStep 3.2を閉じ、candidate取得不完全は `blocked`。status / exhaustion evidence / blocked reasonをcanonical Random Sample sectionへ保存する

### runtime / structure

- Step 1.1 scope coverage rowsをmaterializeし、third-party / language / responsive-device / separately-hosted / authenticated-restricted領域を明示的に閉じる
- selected sampleごとにproject / Design System Authority、responsive boundary inventory、current observationからpresentation variation candidateをmaterializeし、`VAR-001` 等のrequired variation set / completeness / evidenceを閉じる。unknown / unreachable / incomplete variationをFull Pages satisfiedへ数えない
- additional evaluation requirementsのsemantic inputから `ADDREQ-001` 等を採番し、affected step / output、`applied / blocked / out-of-scope`、required evidence / output refsをmaterializeする。目的内要件のout-of-scopeは禁止
- formal evidenceへinitial baseline外environmentを使った場合、baseline revisionを拡張してfreshnessを再計算する。diagnostic-only environmentは追加しない
- random selectionそのものはdeterministic runtimeへ含めず、method / provenance / selected refsを後続Machine Runtime Inputへ渡す
- PR #11 runtime input / generation fingerprint / static_data_versions / current verifierでfreshnessを管理
- formal runtimeがinspection Machine Runtime resultを消費する場合は `metadata.upstream_runtime_units` へ `usability-inspection + runtime_unit_key + generation_fingerprint` を必須登録する。inspectionの `static_data_versions.wcag_machine_probes` をformal static dataへ複製せず、dependency generation mismatchを既存verifierでstale伝播させる
- semantic decisionからfixed machine rowをmaterialize
- draft ref採番
- cross-reference
- Step closure
- static expected requirement coverage
- Conforming Alternate Version condition / Non-Interference fixed Success Criteria closure
- handoff expected / returned closure
- browser開始済みhandoffの再観測はstarted claimを再利用せずnew handoff ref + `retry_of_handoff_ref` + new operation refで実行する。CAS再試行 / exact duplicate result再送は同じhandoffのidempotent処理としてbrowserを再実行しない
- comparison iteration chain
- criterion planのexecution status / result / applicable population closureと、current criterion evaluation refからのsample result materialize
- sample result freshness closure
- not-satisfied example coverage / Step 1.4 all-occurrence coverage
- human-readable report / Evaluation Statement / accompanying documentationのaccessible output closure
- Evaluation Specifics safe materialization
- Evaluation Statement full / partial generation guard
- WCAG Conformance Claim required / optional fields / version別claim URI / third-party 2-business-day monitoring-repair / Statement of Partial Conformance generation guard
- EARL 1.0 JSON-LD materialization
- machine-owned Markdown render
- summary

production helperとdeterministic validatorは別実装にします。

## 6. Step 4: methodology vertical slice

小さいWeb targetでまずsamplingを使う経路を、

1. scope
2. exploration
3. structured sample
4. random sample
5. complete process
6. sample evaluation
7. comparison
8. report

まで1本通します。

同じrepository-controlled fixture内の小さいself-enclosed product scopeで、製品全体をselected sample setとしてsamplingをskipする経路も1本通します。新しいserver / frameworkは追加しません。

この時点では全repo integrationへ広げません。

## 7. Step 5: qa-workflow observation handoff

canonical repository E2Eでは `_04c` のtest-only `tests/skills/evals/deterministic/wcag_handoff_cas_provider.py` を実装し、Python標準 `sqlite3` のtransactionでworkflow state conditional writeと**external reservation provider**のacquire / conditional releaseを実際に通します。`artifact_graph.py` には既存external reservation経路へprovider revisionを返すoptional `external_reservation_revision` だけを追加し、SQLite adapter / generic storage interface / claim providerは追加しません。production providerがnative CAS / conditional releaseを提供しない場合はcurrent契約どおりblockします。

selected sampleごとにlive accessibility observationが必要なcaseで、

- wcag-conformance-evaluationがsample / process / requirement / observation request scope、originating evaluation / revision、resume operationを固定してnormalized handoffを出す
- qa-workflowが `_04c` のhandoff recordを `pending` としてnative CASでworkflow stateへ保存する。CASできるまでbrowser操作を開始しない
- qa-workflowがorigin artifact ref / revision / handoff refからdeterministic `operation_ref` を導出し、そのidentityでmutable operation claimを取得する
- canonical happy pathのrequired shared resourceはtest-only SQLite providerでexternal reservationとして取得し、そのreservation ref / provider revisionを既存 `reserve_shared_resource()` external pathへ渡す。claim / reservation refsを含む `in-progress` をCAS保存した後だけusability-inspectionを開始する
- resource取得途中失敗または `in-progress` CAS conflictではbrowserを開始せず、取得済みreservationを逆順にprovider-native conditional releaseする。その後 `recover_claim()` を呼ぶが、current local claim storageはnative conditional releaseを持たないためcanonical negative fixtureでは `atomic_claim_release_unavailable` のblockedを正しい安全結果とする。成功するclaim recoveryをcompletion条件にしない
- usability-inspectionがbrowser ownerとして `_05g` / `_05j` fixed observation requestを直列実行する
- immutable evidence / inspection artifact refをhandoff ref / sample ref / variation ref / observation request ref / origin revision付きでqa-workflowへ返す
- formal runtimeがreturned inspection runtimeを消費する時点で、そのinspection runtime unit identity / current generation fingerprintを `metadata.upstream_runtime_units` へmaterializeする
- qa-workflow helperがreturned resultからobservation keyを導出し、result currentness、exact duplicate、supersedes lineage、expected-current-valid-returned集合を照合する
- returned resultがstale / 不足でbrowser再観測が必要なら、started claimを削除・再利用せず次の `HANDOFF-NNN` を `retry_of_handoff_ref` 付きでmaterializeしてnew operation refを取得する。exact duplicate returnやCAS retryではnew handoffを作らない
- owner complete / cleanup成功後、`release_shared_resource()` のowner / revision / cleanup decisionを通してrequired external reservationを逆順にprovider-native conditional releaseし、release failure / revision conflictではcloseしない
- helperが `close_ready` を導出し、`closed` をCAS保存した後にstateを再読込して `may_resume` を判定する
- origin stale、claim / CAS / release failure、conflicting current return、未充足expected observationがある場合はresumeしない
- re-read後のcurrent stateで `may_resume=true` の場合だけ元evaluation / revision / resume operationへcurrent result refsをhandoffする
- wcag-conformance-evaluationが同じevaluation revisionをresumeしてaggregationする

ことを確認します。

handoff stateの物理field、status、CAS順序、recovery / duplicate / stale handlingは `_04c_wcag-observation-handoff-state-contract.md` を正本とします。`wcag-conformance-evaluation` に第二のstate storeを作りません。

sample selectionをusability-inspectionへ移しません。formal Skillからsibling Skillのscriptsを直接import / 実行しません。

formal Skillが直接発火した場合も、同一Agent環境で `qa-workflow` が利用可能ならhandoff requirementをworkflowへ返し、`usability-inspection` の結果を受けてformal evaluationをresumeします。`qa-workflow` を利用できない真のstandalone環境でcurrent evidenceがInputに不足する場合だけ、handoff requirementを出してblockedへ閉じます。

## 8. Step 6: random sampling

W3C WCAG-EM 2.0 Step 3.2へ合わせて確認します。

- target count = ceil(structured * 0.10)
- unique
- structured sampleと非重複
- finite inventoryがある場合はcurrent inventoryからcandidate集合をscript導出し、LLMがcandidate refsを手列挙しない
- finite inventoryがない場合はcandidate scope / provenance付きの別random methodを記録する
- finite candidate listを得られる場合はscriptがrandom選択する
- 外部tool自体がrandom selectionする場合だけselected refsを外部random resultとして受ける
- LLMがindividual sample identityをrandom sampleとして手選択する経路を持たない
- target scope全体をselection scopeとする
- predictable fixed patternを使わない
- selection method記録
- unique candidate exhaustionはcomplete finite inventoryまたはscope-wide exhaustion evidenceがある場合だけ `exhausted-no-new-view`。candidate取得不完全は `blocked`

selection結果そのものをdeterministic fixtureへ固定して「random性」を証明しません。

## 9. Step 7: complete process

default sequenceとcommonly accessed / critical branch sequenceはsemantic layerがsequenceとして識別し、`sampling.py materialize-process` がsample union、duplicate除去、process-added分類、membershipを生成します。LLMがsequenceとsample setを二重管理しません。

全interactionをStep 4.2契約へ結び付けます。Step 4.2ではprocess中に変化したcontentとinteraction / input / notification / feedbackを評価し、current identity / evidence / freshnessで同一と確認できるcontent resultは再利用します。確認できないcontentは再評価します。

## 10. Step 8: Step 4.3 loop

random sampleに新content type / findingがないcaseと、あるcaseを実装します。

semantic layerはcontent type / Findingのartifact-local grouping keyだけを確定し、`sampling.py compare` がstructured / random集合差分、detected boolean、new refs、`closed / return-to-step-2-3` を導出します。

差分がある場合:

- exploration update
- semantic layerによる追加structured sample選定
- scriptによるnew structured revision生成
- new structured countからrandom target再計算
- structuredへ移った旧random sampleを除外
- candidate population fingerprintを再計算
- populationが同じ場合だけcurrentな旧random sampleを保持し、target不足分だけ追加random selection
- populationが変わった場合は旧random selectionをstaleとして再選択
- 追加random sampleのcomplete processを再materialize
- PR #11 freshness判定でcurrentな既存sample resultだけ再利用し、stale resultは再評価
- 新たに必要になったsample / processだけを評価
- comparison iteration chain

を閉じます。

## 11. Step 9: report / statement

Step 5.1に従い、Step 1〜4のrequired outcomeをreportへ記録します。各 `not-satisfied` Conformance Requirement / Success Criterionへ最低1exampleを対応付け、Step 1.4でall-occurrence reportingを要求した場合は全occurrence closureも検証します。human-readable report / Evaluation Statement / accompanying documentationは、本Skillが所有する形式についてheading / table header / image text description / color-independent status / meaningful link textを満たします。

`close-report`は、適用可能性処理から導出した空でない`required_steps`について各outcomeが`complete`であることを確認します。`not-applicable`はrequired stepを閉じる値ではありません。Step 4.1または4.2がrequiredなら、現在のcriterion planから得た`required_criterion_evaluation_refs`とsample resultの集合が一致し、全resultがcurrentかつ`satisfied` / `not-satisfied`であることを確認します。さらにStep 4.1または4.2のoutcomeが`complete`なら、callerがそのstepを`required_steps`から省いても、同じcurrent result scopeを必須にします。Step 3.1 / 3.2 / 3.3でsampleまたはcomplete processの選定が`complete`なら、選定済み対象があるためcriterion result scopeも必須です。したがってStep 4.2の適法な`not-applicable`はStep 4.1の初期sample結果を免除しません。一方、Step 4.1が適法に適用外でStep 4.2がrequiredの場合は、complete processに対応するcurrent resultsで閉じます。期待refなし、欠落・余分なref、`undetermined` / stale / unknown resultがあればreport closureを`blocked`に保ちます。Step applicability自体は既存の判断主体が確定し、`close-report`は新しい適用性エンジンを作らず、その確定済み入力とcurrent criterion resultsを照合します。全scope / variation / criterion結果の作成には既存ownerを使います。

Step 5.2 Evaluation Specificsは要求・合意があるcaseでsample archive ref、path / settings / actions、tool / browser / AT / software / methodを記録し、secretや不要PIIを保存しません。

Evaluation Statementはtarget WCAG 2.2だけでfull / partial /生成不可を分け、`_05f_wcag-conformance-evaluation-package-and-runtime.md` のStep 5.3 contractを閉じます。WCAG 2.0 / 2.1のformal evaluationではStep 5.1 reportを生成しますが、Step 5.3 Evaluation Statementは生成しません。

WCAG Conformance Claimはcomplete claim scope evidenceとversion別required fields / claim guideline URIが揃うcaseだけ生成します。representative sampleだけでは生成しません。W3C optional claim componentsもevidenceがある場合に保持します。third-party contentをmonitoring / repairによりfull claimへ含めるcaseでは、all affected pagesでの識別、monitoring可能性、2 business days以内のremove / bring-into-conformance evidenceをmachine guardで検証します。

WCAG Statement of Partial Conformanceはthird-party content / languageを別caseとして実装し、Conformance Claimと混同せず、canonical wordingをscriptでrenderします。

Step 5.5を要求するcaseでは `_05l_earl-jsonld-serialization-contract.md` を実装し、`earl_report.py` が固定 `@context` / stable IRI / Assertion・TestResult node shape / property orderingでEARL 1.0 JSON-LDを生成します。formal result + applicable population → EARL outcome / modeを固定mappingし、`applicable_population=none` + complete closureは `earl:inapplicable`、applicableな `satisfied` は `earl:passed` とします。graph reference closure、deterministic byte再render、human-readable assertion coverageをvalidatorで照合します。

aggregated scoreは目的外として生成しません。

## 12. Step 10: repository integration

latest mainを基準に、

- CANONICAL_SKILLS
- MULTI_USE_SKILL_TARGETSへの影響
- qa-workflow
- README
- EVALS
- ASSERTIONS
- validation workflow
- dataset counts

を同期します。

件数をPlanの古い値で固定しません。

## 13. eval

### trigger

formal WCAG要求 / general accessibility要求の境界をdatasetに保持し、dataset contract testsで検証します。current PR #14の実Agent trigger gateはdescriptionを変更した`WCAG-TR-TRA-002`と直接関係する既存negative boundaryだけです。各queryを3回、Skill-read eventで判定し、`EVALS.md` thresholdを使います。full native trigger統計は独立した継続評価であり、PR #17の出力品質評価にも含めません。

### deterministic

- schema
- supported WCAG version 2.0 / 2.1 / 2.2 / explicit unsupported or out-of-scope / missing unresolvedの状態分離
- version別static requirement catalog / `static_data_versions` / approved hash contract
- target version / level expected Success Criteria / conformance requirement set
- finite procedure catalog key / kind / dispatch / hash
- formal procedure catalog内のmachine procedure → `_05j` finite machine probe key mapping / typed request schema / capability
- formal machine probeを処理したinspection runtimeが `static_data_versions.wcag_machine_probes` を保持すること
- formal consumerの `metadata.upstream_runtime_units` がinspection `runtime_unit_key / generation_fingerprint` をexactly-onceで保持し、missing / generation mismatchでformal freshnessがstaleになること。formal `static_data_versions` へsibling hashを複製しない
- repository-level contract testでformal required machine probe keyとinspection catalog keyのmissing / extra / unused 0
- `_05k` versioned semantic contract coverage / normative clause・exception refs / required evidence role / AT `procedure_applicability_contracts[]` / approved hash
- WCAG 2.0 / 2.1 4.1.1 HTML/XML shortcut / other technology semantic path / WCAG 2.2 removal
- SC 1.4.4のvalid text scaling mechanism inventory、baseline / mechanism scale / used font sizeからrendered text scale ratioを計算して全applicable textの2.0x到達を確認、responsive breakpointを跨ぐcase、target到達までのincremental state、`deviceScaleFactor` / viewport resize / CSS injectionを代替としてreject
- machine ownerがvalid text scaling mechanismを操作 / scale取得できないcaseではfixed limitation codeから `manual-wcag-1.4.4` をapplicable化し、manual evidenceでclosureできること。manualも実施不能な場合だけblocked / undetermined
- 1.4.3 / 1.4.6 / 1.4.11のmachine contrast unavailableと2.4.13 complex focus indicatorで、対応するconditional manual fallbackを決定論的に起動できること
- semantic procedure resultの判断理由 / uncertainty / additional observation request refs
- additional observationがrequired criterion / procedure集合を変更せず、fixed observation contractへ解決されること。解決不能またはno-progressではundetermined / blockedへ閉じること
- semantic判断で発見した別のusability / business flow concernをWCAG resultへ混ぜず別routingできること
- required presentation variation registry / Full Pages coverage
- criterion evaluation execution status / result / applicable population / final result linkage
- required Success Criterion全件のevaluation metadata / criterion plan row / required step closure / missing・duplicate detection
- Conforming Alternate Version / Non-Interference / Full Pages / Complete Processes / Accessibility-Supported fixed rule metadata
- version別claim guideline title / URI / third-party repair contract
- runtime input / generation fingerprint / freshness
- canonical sample identity registry
- Step 1.1 scope coverage / baseline revision extension
- sampling procedure used / skippedとselected sample set closure
- rerun retained / replaced / added / unavailable sample lineage
- observation handoff origin / resume identity / expected observation materialization
- `_04c` physical `state.handoffs` schema、composite operation identity、state CAS、mutable operation claim、external reservation acquisition / rollback / normal release、current local claim recovery unavailable時のsafe block、started handoff rerun lineage、duplicate / conflicting return、stale origin、close-ready → closed CAS → re-read → resume guard
- test-only SQLite providerでworkflow state same expected revisionのconcurrent writeは1件だけ成功し、external reservationのstale revision / wrong-owner releaseはconflict。current local claim storageではpre-start recoveryが `atomic_claim_release_unavailable` でblockedとなり、production local filesystemではstate conditional write unavailableのままfail-closed
- ref
- sample count
- finite inventory candidate derivation / recorded method provenance
- candidate population fingerprint
- random selection status / exhaustion evidence / blocked reason / canonical Random Sample section closure
- duplicate / overlap
- process sequence → process-added sample materialization
- Step 4.2 unchanged-result reuse eligibility
- Conforming Alternate Version full-page grouping / Non-Interference fixed SC coverage
- Step 4.3 set difference → boolean / action derivation
- structured revision更新 → candidate population fingerprint再計算 / population同一時のoverlap除外・retained random・top-up / population変更時のreselection / process再materialize
- sample result freshness / stale再評価
- non-finite sourceでもLLMがrandom sample identityを選ばないこと
- machine-owned structured section materialization
- closure
- report / not-satisfied example coverage / all-occurrence追加要件 / accessible output contract
- Evaluation Specifics / archive ref / secret safety
- Evaluation Statementはtarget WCAG 2.2だけでfull / partial guardを検証し、2.0 / 2.1ではsection不存在を検証
- WCAG Conformance Claim required / optional fields / version別claim URI / third-party 2-business-day monitoring-repair / Statement of Partial Conformance guard
- EARL JSON-LD fixed `@context` / node shape / stable IRI / result reference closure / `applicable_population=none → earl:inapplicable` を含むoutcome・mode mapping / deterministic property ordering・byte rendering / assertion coverage

### semantic

`_05f` Case A〜Z、Case C2、Case AA〜AFと`_05h` のsemantic追加観測 / no-progress / 別usability concern routing fixtureをsemantic dataset・contract testsに保持します。repository dataset validator / testsで全件構造を検証し、全caseの実Agent candidate / JudgeはPR #17へ移管します。

### real Agent / browser

`_06c_canonical-live-validation.md` のrepository-controlled fixtureで、最低1件のreal-Agent smokeと代表的なformal direct request → scope/sample → observation handoff → `qa-workflow` → `usability-inspection` → formal resume → report / EARL経路を通します。successful representative handoffではSQLite CAS、reservation、browser observation、cleanup、closed state reread、`may_resume`を確認します。

fixture全体のStep 4.2 / Step 5.1を埋めることは要求しません。未取得のcurrent resultをcompleteへ昇格せず、missing evidence / procedure resultを明記し、部分結果を保持してreport closureを`blocked`とするpartial-blocked状態、`owner_commitment_ref`等Step 5.3 required input不足時のStatement非生成、および提供されたcurrent result subsetでEARL renderer / independent validatorが正しく動くことを確認します。EARL subset validationはformal evaluation全体のclosureとは扱いません。

外部実対象・実アカウント・特定assistive technologyを必要とするacceptanceは別ゲートです。それらが提供されていないことだけでrepository implementationを未完了にしません。

## 14. 完了条件

- Skill責務がusability-inspectionと分離
- qa-workflowがmulti-Skill observation handoffを直列オーケストレーションし、physical state schema / composite operation identity / CAS / claim / reservation lifecycle / started handoffのnew-handoff rerun lineage / closureを `_04c` どおり実装
- standalone packageがsibling Skill scriptsへruntime依存しない
- WCAG-EM Step 1〜5 traceability
- Step 1.4 additional evaluation requirementsをref採番し、目的内要件をaffected step / outputへ反映してappliedまたはblocked、明示目的外だけを理由付きout-of-scopeへ閉じる
- WCAG-EM 2 output schemaがReport Toolへ依存せず、WCAG-EM 2.0本文を正本としている
- accessibility support baseline必須。formal evidenceへinitial baseline外environmentを使った場合はbaseline revisionを拡張してfreshnessを再計算
- Step 1.1でthird-party / language / responsive-device / separately-hosted / authenticated-restricted scope coverageを明示的に閉じる
- WCAG 2.0 / 2.1 / 2.2をsupported versionとし、missing / unresolved、unsupported / out-of-scopeを分離
- target version / levelからrequired Success Criteria / conformance requirement集合を該当versionのstatic catalogだけで独立導出し、3 catalogのcanonical hashを既存static data契約で検証
- 全required Success Criterionにfinite procedure keyがあり、sample × required variation × criterion evaluation rowをscriptでmaterializeし、procedure / criterionをLLMが選択・省略しない。machine化可能なprocedureは明示dispatchし、`_05j` fixed machine probeをscript導出する。criterion固有semantic判断は `_05k` static contractを使用し、AT要否はselected procedure + current content / technology + baselineから閉じる
- semantic procedureは判断理由・uncertainty・追加観測要求を保持でき、finite procedure catalogを意味判断の上限にしない。追加観測はrequired criterion / procedure集合を変えずexisting fixed observation contractで取得する
- `runtime_contract.py` でPR #11 Machine Runtime / freshness契約を再利用し、random selectionそのものはdeterministic runtimeへ含めない
- Step 2 exploration closure
- sampling procedure used / skippedの両経路
- sampling skippedではcomplete inventoryから全in-scope sampleをselected sample setへmaterializeし、structured / random / Step 4.3をnot-applicableとして閉じる
- sampling usedではStep 3.1 structured sample
- 再評価ではprevious sampleをcurrent identityへ解決し、retained / replaced / added / unavailable lineageをscriptでmaterializeする。replacement ratioは固定しない
- canonical sample identity registryをscriptがmaterializeし、duplicate / overlap / union / process membershipを機械判定
- selected sampleごとのrequired presentation variation registryをscriptがmaterializeし、unknown / unreachable / incomplete variationをFull Pages satisfiedへ数えない
- final Success Criterion resultはcurrent criterion evaluation refからだけmaterializeし、LLM supplied result listを受け付けない
- sampling usedではStep 3.2 random sample。finite inventory時のcandidate集合とcandidate population fingerprintはscript導出し、非finite時もLLMがsample identityを選ばない
- complete process。sequenceからprocess-added sample / membershipをscript導出
- Step 4.1でConforming Alternate Versionを別sampleに数えず、Non-Interference fixed SC集合をcatalogから導出する
- Step 4.2ではcurrent unchanged resultだけを再利用し、changed / unknown contentとinteractionを再評価する
- Step 4.3 retry loop。semantic grouping keyから集合差分 / boolean / actionをscript導出し、structured revision変更後のcandidate population fingerprint再計算、population同一時のrandom target再計算 / overlap除外 / retained random / 不足分top-up、population変更時のreselection、process再materializeまで閉じる
- 既存sample resultはPR #11 freshnessがcurrentの場合だけ再利用する
- Step 5.1のStep 1〜4 required outcome closure
- 各not-satisfied Conformance Requirement / Success Criterionを最低1exampleへ対応付け、all-occurrence追加要件も別closureで検証する
- human-readable report / Evaluation Statement / accompanying documentationを本Skill所有形式ではaccessible output contractへ閉じる
- Step 5.2 Evaluation Specificsのsafe archive / environment / method record
- Step 5.3 Evaluation Statementはtarget WCAG 2.2だけでfull / partial minimum fields / generation guardを検証し、2.0 / 2.1では非生成
- WCAG 2.0 / 2.1 / 2.2 Conformance Claim required / optional fields / version別claim URI / full-scope guard
- third-party monitoring / repair full-claim caseでall affected pages identification / monitoring / 2 business days repair guard
- WCAG Statement of Partial Conformance - Third Party Content / Language required fields / canonical wording / guard
- Step 5.5 EARL 1.0 JSON-LD fixed graph / stable IRI / `applicable_population=none → earl:inapplicable` / deterministic serialization / assertion coverage
- Step 5.4 aggregated scoreは目的外として生成しない
- requirements / sampling / structure helperでmachine-owned fieldをmaterializeし、Agentがfinal refs / expected集合 / derived status / countを手作成しない
- independent deterministic validator
- semantic dataset validation、deterministic / runtime / repository semantic tests PASS
- description変更対象のtargeted trigger regression PASS。full native trigger statistics / holdoutは本PR gateではなく、PR #17にも含めない
- `_06c_canonical-live-validation.md` の代表repository-controlled formal Web E2Eとfail-closed report / EARL path PASS
- representative happy-path handoffでunresolved blocked 0。部分fixture reportの正しい`partial-blocked`状態とexpected safety blockedは区別する。外部acceptanceは別statusとして記録する

## 16. Canonical closure and formal output guards (2026-10-09)

- `close_criterion()`は入力procedure rowsをversioned Success Criterion requirement assetとfinite procedure catalogのprocedure key集合へ照合し、欠落・余剰・重複を拒否する。applicability判定、manual fallback、AT、external evidenceの既存条件は維持する。
- `validate_random_selection()`とfinite selectorは`target_count == random_target_count(current_structured_count)`を検証する。partial candidate inventory、exhaustion、sampling skip、population changeの既存status境界は維持する。
- `close-report`は、渡されたbasisから`materialize_plan()`を再実行し、Plan内部の全件性と結果集合を照合する。この照合は入力Planの内部整合性を保証するが、basisが保存済みの現行evaluation / scope / sample selectionに由来することまでは証明しない。partial result materializationは許容し、missing / extra / duplicate / stale / unknown / undetermined resultが残るreportはcompleteにしない。
- 正式なreport completionには、信頼できる保存先からevaluation ref / revision、WCAG version / level、承認済みscope、選定済みsample / variation / process集合を独立に取得し、Planと結果の出所・現行性を照合する必要がある。現在の汎用workflow-state readerとWCAG `close-report` runtime dispatchにはこの正本読込・照合経路がないため、このprovenance条件は未達であり、内部整合性のみを根拠にPlan provenanceをPASSとしてはならない。新しいstore / CASを追加せずに既存APIで取得可能になった場合に限り、この条件を閉じる。
- Step 5.3はcompleteなreport closureと同一evaluation revision / target / exact criterion ref setのformal conformance resultsを要求する。full statementには全sampleとconformance requirementのcurrent satisfied結果、owner commitmentを要求し、partial statementにはcurrent nonconformance evidenceを要求する。
- EARLは各結果のevaluation ref / revisionと`freshness_status=current`を要求してからpassed / failedを出力する。明示的untested、cantTell、inapplicable mappingと固定serializationは維持する。
- all-pages-evaluated Claimで非列挙`scope_expression`を全件評価済みと扱わない。既存assurance-process経路はcomplete-process evidence refsがevidence setに含まれる場合に維持する。

## 17. Canonical evaluation provenance owner boundary (2026-10-10)

- At head `7d7f9873a726b8b98a706ebe9ae9cd71f4e65e53`, re-running the same-revision WCAG 2.2 AA → A plan reduction still made direct `close_report()` return `complete`; the `wcag_runtime.py` `close-report` operation returned `ready` with a `complete` closure. The plan is internally self-consistent, but its `plan_basis` is not independently tied to the approved current evaluation and selected scope.
- `qa-workflow` owns persisted workflow state, while WCAG owns evaluation semantics. `artifact_graph.py` currently provides generic envelope create/read and a decision helper. `create_workflow_state()` labels its local content digest `local_exact_content_token_not_a_cas_condition`; `read_workflow_state()` returns caller-supplied state content after envelope/workflow-ref checks; `state_update_decision()` returns `blocked / atomic_conditional_write_unavailable` when native conditional write capability is absent. The template defines no canonical WCAG evaluation state schema or independent owner of its fields.
- No production state conditional-write implementation or WCAG canonical evaluation reader is present in the tracked repository. The `SQLiteHandoffCASProvider` exists only under deterministic tests and proves only the test handoff fixture; it is not a production provider and does not establish canonical WCAG evaluation provenance.
- Do not treat a caller-provided plan, basis, ref, revision, digest, or `verified` field as provenance. Do not add a WCAG store/CAS layer or report this gate as passed. Until the existing workflow owner can independently read the current evaluation/scope/sample/variation/process source and atomically update against its expected storage revision, the canonical-plan provenance requirement remains unmet. Formal completion without that proof must not be accepted.
- A valid future path must persist the owner-approved evaluation ref/revision, WCAG version/level, approved scope refs and evidence, selected sample/variation/process membership, and source artifact correspondence through the existing workflow owner; read them independently at final closure; compare the complete required Plan/result sets; and use the provider's native conditional write and reread for any state update. A test-only provider may exercise this contract in tests but cannot establish production availability.
- Status at head `08aab5d9c562794ce81f74109610b3635e5d0d72`: `UNMET — production provider/owner read path unavailable`. Section 18 supersedes this historical status with the approved single-host SQLite exception and its validation evidence.

## 18. Canonical WCAG evaluation state and formal report completion (2026-10-10)

The previously unmet provenance requirement is implemented through `qa-workflow`'s existing `artifact_graph.py` owner boundary using Python standard-library `sqlite3`. This is a narrow production provider for WCAG evaluation state and final report completion, not a general workflow-state or handoff/reservation provider. It uses the existing `qa.workflow_state_root`, preserves the `workflow_ref / schema_version / state` envelope, stores `state.wcag_evaluations`, and keeps SQLite provider revision distinct from WCAG `evaluation_revision`.

Registration stores the evaluation reference and revision, target version/level, scope decisions and evidence refs, selected sample identities, variations, process membership, source artifact refs/revisions, canonical plan basis/fingerprint, and report status. It excludes raw URLs, secrets, DOM text, scope prose, and semantic narratives. Same-revision scope or Plan changes conflict; a legitimate change requires a new evaluation revision. Registration is performed from the existing WCAG evaluation inputs and finite scope/source evidence; persistence alone is not described as proof of user authorization.

`wcag_runtime.py` reads the current saved record through a current QA workflow runtime dependency and verifies the canonical materialized Plan and complete current result set before returning only an `unresolved / pending-persistence` candidate. The candidate carries the finite WCAG-EM step/applicability, example-coverage, and accessible-output inputs used by that invocation. `workflow_runtime.py` rereads the provider state, checks provider revision and candidate identity/fingerprints, then independently reruns the existing pure `close_report()` with those inputs plus the owner-read canonical Plan and current result set. Candidate status or matching generation fingerprints alone are not closure evidence. The declared upstream runtime dependency also carries the full envelope `result_fingerprint`; the existing Machine Runtime freshness check compares it to the current runtime row. The QA workflow owner binds the submitted candidate envelope to that declared result fingerprint before consuming its closure inputs; Machine Runtime freshness establishes that the declared fingerprint matches the current row. Thus a candidate whose payload alone changed under the same generation is rejected. Only if all WCAG-EM outcomes and accessible-output checks are complete does the owner perform SQLite `BEGIN IMMEDIATE` + conditional `UPDATE ... WHERE provider_revision = expected`, then independently reread the saved complete state. Only this successful owner path returns formal `ready / complete`. The pure `close_report()` remains an internal semantic validator; the owner-side rerun connects its result to persisted workflow completion.

Provider scope is one host with a local filesystem at the existing `qa.workflow_state_root`. Network filesystems, multi-host/distributed execution, unset or in-repository state roots, corrupt state, SQLite lock/transaction failures, stale provider revisions, and missing CAS capability fail closed. This provider does not replace generic JSON state CAS, handoff reservation, claim, or release; the test-only `wcag_handoff_cas_provider.py` remains test-only. SQLite provides transaction/revision consistency for this supported local deployment, not cryptographic protection against a privileged DB writer or distributed-host coordination.

Local validation at the working tree based on head `08aab5d9c562794ce81f74109610b3635e5d0d72` passed: focused WCAG contracts (124 tests), repository deterministic (282), runtime (271), shared deterministic (12), shared semantic (27; 2 Windows symlink-privilege skips), repository semantic (4), trigger contract (1), semantic dataset validation (22 Skills / 155 cases), official `skills-ref validate` (23 Skills with `PYTHONUTF8=1`), Python compile, changed-Markdown Prettier / Markdownlint / text quality, and `git diff --check`. The whole-repository Markdownlint invocation reports 882 issues across 157 files; the eight changed Markdown files pass the same rules when linted directly. Detailed provider/CAS tests, runtime cases, environment notes, and publication evidence are recorded in `docs/reports/2026-10-02-pr14-validation-progress.md`. This local evidence does not substitute for checking all three GitHub Actions against the pushed final head.
