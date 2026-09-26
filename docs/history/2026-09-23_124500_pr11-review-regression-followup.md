# PR #11 review regression follow-up

2026-09-23 JST、PR #11のレビュー指摘に対するローカル修正と最新作業ツリーの検証結果を記録する。

## 開始点

- 対象branch: feat/deterministic-test-technique-automation
- 開始時にPR #11 headを再取得した。FETCH_HEADと開始時HEADはどちらも c2f85961274a63e7a57cce8e44c9fde202d39c62 で、レビュー時点のSHAと一致した。
- commit、push、GitHub上のPR本文更新、mergeは実施していない。

## 修正

- target-specific test data requirementのsource target versionを、current targetのsource model、target ref、content fingerprint、generation fingerprintと完全一致で検証する。materialize側はapplicable target refsを再導出し、保存値があれば完全一致を要求する。
- typed value比較とrequirement intersectionをSkill-local runtime_contract.pyへ置き、7 SkillのコピーをLF正規化後に一致させた。environment、test data、materialize merge、TC統合が同じintersection規則を使う。
- blocking issueを含むready resultを共通runtime契約で拒否する。environment conflictとflow blockerはgenerator自身がunresolvedを返す。
- case_structure.pyでTC単位のenvironment key内intersectionと必要requirement refs一式を再検査する。
- duplicate target dispositionのchainはcurrent runtime mappingまたはversion一致したsemantic CIだけへ閉じる。非coverage disposition、stale version、cycle等をblockする。
- analysis_entities.pyをchange/environment → Product Risk → Technique Selection/contextの順にし、current同一invocation依存を解決する。下流QA Entityへの逆dependencyは作らない。
- schema_cases.pyでminProperties/maxPropertiesを対応subsetへ追加し、同じschema runからderived.test_data_requirementsを出す。
- combinatorialの探索budgetをinvocation内で共有し、Decision Table hard limitをlimit_exceededとして返す。
- workflow_runtime.pyとtraceability.pyでscopeごとにmaterialize completionを検証し、古い未使用独自closure実装を削除した。

## ローカル検証

- Python 3.11.5。
- 7対象Skillのcompileall: PASS。
- runtime unittest discovery: 177 tests PASS。
- deterministic shared tests: 12 PASS。repository deterministic tests: 54 PASS。
- semantic dataset validator: 14 Skill / 51 case。
- semantic shared tests: 27件中25 PASS、2 skip。skipはWindows symlink privilege不足によるもの。
- semantic repository tests: 4 PASS。
- trigger dataset test: 1 PASS。datasetは14 Skill / 328 query。
- deterministic output dataset: 14 Skill / 28 case。
- skills-ref validate: 14/14 PASS。
- 7個のruntime_contract.pyはLF正規化後に同一SHA-256。
- git diff --check: exit 0。Gitはworking-copy改行のCRLF変換警告を出したが、diff check errorはなかった。

## 実Agent runtime smoke

Codex CLIでtest-analysisとtest-condition-designのSkill文書を読ませ、各Agent出力からruntime入力を作り、ホストのPython 3.11.5で現行runtimeを起動した。stdout envelopeをstrict JSON parseし、その結果をAgentが最終Markdownへ反映した。Markdownは保存後に再読込して確認した。

- test-analysis: Agent入力 → risk_matrix.py → technique_candidates.py → analysis_entities.py。Product Riskからchange nodeへのdependency、Technique Selectionからcurrent Product Riskのcontent fingerprintへのdependency、下流TC/CIへの逆dependencyがないことを確認した。同一入力の再実行でgeneration fingerprintとpayloadが一致した。dummy secret値は入力、runtime evidence、保存Markdownに残らなかった。
- test-condition-design: Agentが作ったJSON Schema runtime input → schema_cases.py。derived.test_data_requirementsにenum、range、required由来booleanを含む5要件があり、同一入力の再実行fingerprint/payloadが一致した。
- 両smokeでruntime_status=ok、result_status=ready。最終Markdownが現行envelopeのfingerprintとMachine Entity/runtime resultを参照することを確認した。

## Semantic Judge

最新作業ツリー向けの候補出力24件を一時ディレクトリに生成し、既存semantic runnerへCodex CLI Judgeを接続した。候補とJudge JSONは次の一時ディレクトリに保存した。

    %TEMP%\pr11-semantic-candidates-20260923\outputs
    %TEMP%\pr11-semantic-candidates-20260923\judge-results

実行commandの形:

    python scripts/skills/evals/semantic/run.py --skill <skill> --eval-id <eval-id> --output <candidate.md> --judge-command C:\Users\sella\AppData\Roaming\npm\codex.cmd exec --ephemeral --sandbox read-only -C <repo> -

24件の判定はPASS 4、needs_review 15、fail 5だった。

- PASS: RISK-SEM-004, RISK-SEM-006, TC-SEM-002, REV-SEM-008
- needs_review: RISK-SEM-003, RISK-SEM-005, RISK-SEM-007, TCN-SEM-003, TCN-SEM-005, TCN-SEM-006, TCN-SEM-007, TCN-SEM-008, TCN-SEM-010, TCN-SEM-011, TCN-SEM-012, TCN-SEM-014, REV-SEM-003, REV-SEM-004, REV-SEM-007
- fail: TCN-SEM-004, TCN-SEM-009, TCN-SEM-013, REV-SEM-005, REV-SEM-006

TCN-SEM-013は初回にJudge response schema errorとなったため再試行し、再試行ではfailを得た。Gemini CLIも試したが、サービスの一時503とJSON-only protocolに適合しない応答があり、Judge結果には数えていない。Codex CLIはcandidate生成にも使っているため、今回の判定は独立vendor Judgeではない。

旧headで記録された24/24 PASSは、この作業ツリーの判定証拠として使用していない。最新候補の24/24 PASSは未達である。

## Plan / input schemaの不整合

分割Plan _02 のcanonical test-analysis context schemaはscope、objectives、test_levels、environment_constraints、exclusions、blockers、test_focus_items、testability_decisions、residual_risksだけを定義し、Authority / Product Risk identity refを持たない。一方、同Planのdependency規則はcontextの判断で実際に参照したAuthority / Product Riskへのdependencyを要求する。

inputに明示的なidentity refがないため、文章内容やartifact全体のmetadataから推測してdependencyを追加していない。この箇所はPlan内のschema/dependency契約の不整合として残る。解消にはcanonical inputのfield契約を確定する必要がある。

## 完了状態

runtime回帰修正とローカル検証は通過したが、Plan上のcontext dependency契約とsemantic Judge 24/24 PASSは未達である。semantic shared testsの2件も環境制約でskipになった。したがってPR #11の完了条件を満たしたとは扱わない。
