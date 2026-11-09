# PR #22 並行実装：C — UI分析・人間編集

## 位置付け

UI構造と期待仕様を分離し、既存ui-target-v1を破壊せず人間の編集案を正式なwriterへ取り込む。

- 作業branch：`feat/pr22-c-ui-human-editing`
- PRのbase／最終統合先：`feat/development-qa-traceability`（[PR #22](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)）
- 分岐元commit：`718005961ade89a848788e8ad3a354d4c711b84a`
- このbranchのPRは**実装準備のDraft**から始め、以下の完了条件を満たしてレビューできる状態にする。**実装完了・merge済みを意味しない**。
- 2026-11-08の利用者指示で、最終統合先はPR #22に変更された。既存Plan索引の「PR #22は文書変更PR」という作成時点の記載より、この統合指示を優先する。
- このファイルは担当別の作業ガイド。要件・完了条件の正本は以下のPlan。**15＋10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケースを削減しない**。全体の最終完了判定はPR #22で行う。

## 参照するPlan

- [PR #22：開発連動QA・QA全工程の実装Plan](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)
- [Plan索引](../../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)
- [開発連動QA Plan（15完了条件）](../../plans/2026-11-07_122247_development-qa-traceability.md)
- [QA全工程Plan（10完了条件）](../../plans/2026-11-07_170134_qa-full-process-implementation.md)
- [詳細08：人間編集・構成管理](../../plans/2026-11-07_170134_qa-full-process-implementation_08_human-artifact-editing.md)

関連完了条件の主な担当：開発連動QA 5・8・12・14、QA全工程 9。詳細08の全8受入はCが実証する。

## このbranchで変更する対象

- 新設`skills/ui-target-analysis/**` と `skills/spec-analysis/**` のUI mode／利用側接続
- `skills/spec-analysis/scripts/ui_target_package.py` とUI package関連の既存回帰テスト
- 人間の編集案の差分抽出・検証・正式materializeに必要なSkill局所helper／受入テスト

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 担当branchで実施する作業とPR #22で実施する作業

### このbranchで実施・検証する

- 本書の担当対象のSkill・runtime・helper・データ契約・既存consumerとの局所接続を実装し、担当範囲の既存テスト・回帰・負例・権限／保存・履歴互換性を検証する。
- 担当機能の受入に必要な実runner・実保存先・実Agentの**単独経路**は、利用可能な環境で実施する。外部権限・実接続が不足する場合はその条件を未検証／blockedと明示し、独立に検証できる部分は完成させる。
- 他branchの未統合実装は合意した契約と独立fixtureで代替して局所検証する。fixtureは他ownerの実成果物を統合した証拠にはしない。
- 担当が所有する実装不具合、局所結合・回帰不具合は**このbranchで修正**し、対応したテスト・実施証拠を残す。

### PR #22だけで実施・判定する

- A〜Jの実装PRの取り込み、競合解消・全体再検証、**各ownerが実際に保存した成果物同士**のID／revision／currentness／承認・run参照による横断接続。
- 全current Skill同時利用時の発火／routing、工程をまたぐ実Agent・実runner・実provider・製品CIの一連の受入、S1〜S17の総合試験、人間編集8ケースの**全体経路としての再検証**。
- 開発連動QAの15条件、QA全工程の10条件と詳細Plan 01〜08の最終照合、Plan詳細07の5シナリオの**変更前後の横断実測・効率化判定**、統合後の全CI・回帰評価。
- 横断試験で見つかった問題はownerを特定し、分割可能な実装・修正は対象branchに戻す。統合固有の接続・設定・複数owner間の確認作業だけをPR #22で実施する。

### PR #22へ引き渡す証拠

- 担当の変更ファイル、公開入出力契約、参照するowner／source／artifact IDとrevision、schema／fixture、保存・承認・失敗／再開条件。
- 局所検証のコマンドと結果、実runner／実providerの担当経路の証拠、回帰・負例、未実行／SKIP／blockedと再開条件。
- 他担当の実成果物が必要な横断検証項目。**これらの未実施は担当branchの局所検証を失敗扱いする理由にはしないが、PR #22の最終受入完了には必ず必要**とする。

## 共通契約が未確定の場合の着手範囲

- A（[PR #23](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/23)）のsource／artifact ID・revision・scope、runtime登録、保存・承認・CAS／readback、blocked／再開、評価・CI引継ぎ契約を**実コード・既存契約と照合し、PR #23で共有された内容**に従う。
- 上記に依存しない既存実装調査、担当Skill固有ロジック、独立fixture、局所テストは先行可能。Aによる確定・共有前に、未確定の共通schema・保存形式・承認・runtimeの接続方法を推測して確定しない。
- 契約未確定で停止する対象処理と理由・解決責任者・再開条件を記録し、独立して実施できる作業を止めない。Aが共有した契約を使う局所検証の後、他ownerの**実成果物を使う横断検証はPR #22**へ引き継ぐ。

## 着手基準

- [x] `ui_target_package.py`、既存UI modeの利用側・migration・legacy・関連テストを読み、A/B/Eの変更境界を確認した。PR #23の共有runtime契約とPR #24の独立検証状態も照合した。
- [ ] Q06の実合意・保存先・編集権限はBの実artifactで未確認。helper fixtureのrefは契約例であり、実接続証拠ではない。

## 作業内容

1. `ui-target-v1`の00〜09、scope readiness、stable ID、MANIFEST／CHANGELOG、Machine Entities、既存writer／consumerを確認し、新Skillへの移行で互換性を維持する。
2. UI構造・操作・状態・画面遷移だけをUI ownerとし、期待挙動・Authorization・業務状態のAuthorityは`spec-analysis`のままにする。
3. BのProject Context配置合意に基づき、人間が機能IDから編集可能な正本ファイル／行／stable IDへ辿れる導出参照を用意する。
4. 人間のbranch／copy編集差分を有効な元snapshotと照合し、生成部・手動採番・行削除・承認不足・意味上の衝突を検出する。
5. 採用差分は`materialize`の既存table/prose/retire更新契約に変換する。編集案のMANIFEST・生成物をそのまま正本へ取り込まない。
6. canonical root直接改変、古いManifest、競合、保存応答消失、権限不足で編集案を保全し、検証済みsnapshotからの復旧以外をblockedにする。

## 依存と引継ぎ

- B：Project Context Q06合意・feature ID・source refを受け取る。
- E：currentなUI構造と、別正本であるAuthority参照を渡す。
- A：shared runtimeへのUI Skill登録／保存・承認境界を依頼する。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [x] 独立`ui-target-analysis`を追加し、`spec-analysis`のUI modeをAuthority／期待仕様のownerとして維持しながら、既存`ui-target-v1`、stable ID、Manifest、CHANGELOG、conditional file、writer、migrationを壊さない局所検証を通した。
- [x] 詳細08の8ケースを独立package fixtureで実施した。通常編集と新規／廃止は既存writer・独立readbackまで実行し、禁止領域・無承認・競合・不正currentは正本不変を確認してblocked、失敗再開は同一fingerprint receiptで再送、正本探索はcurrent file／section／line／stable IDまで照合した。prepareとmaterializeの間にcurrentが変わるCAS競合もwriterのstructured `stale_snapshot`拒否で確認した。
- [ ] 承認ref・Authority参照・scopeをfixture内で検査したが、Q06実合意、認証された承認者、Bの実feature artifact／mappingは未接続。実artifactの意味currentnessはPR #22で再検証する。
- [x] Manifest不一致・canonical直接編集・不足承認・symlink・重複JSON keyをblockedにし、編集案とcanonical bytesを保全した。別copyからの再開、commit応答消失、同じrequestの再送も独立fixtureで検証した。
- [ ] feature indexは独立fixtureでcurrent package versionとfile／section／line／stable ID／changed rowを導出した。下流artifactのstale伝播・必要scopeのみの再検証はA runtimeとEの実成果物がなく未検証。
- [ ] isolated copyではshared writer不在時に書込みhelperがblockedになることを検証した。trigger dataset契約とsemantic candidateはローカル検証したが、実trigger rateと独立Judge実行、既存TC/E2E consumerの実成果物接続は未検証。

- [x] `SKILL.md`、入出力、停止条件、人間編集・互換性文書、isolated copy test、trigger dataset、semantic rubric/cases/candidate outputsを追加した。semantic結果は実装者と同一のsession LLMによる自己評価であり、独立Judge実行とは扱わない。
- [ ] 担当Skillとpackage/migrationの局所回帰はPASS。全runtime・deterministic suiteはローカル環境要件によりFAIL（結果表参照）。remote head `166f63299a4bcd51b3dce5fe5d5a265548c5e6ad`ではruntime unit/integration、deterministic、semantic、Codex HarnessがPASS。root READMEと`qa-workflow`に旧route記述が残り、shared owner修正前のSkill validationは完了しない。
- [ ] 専用unit／package／migration／semantic dataset・trigger datasetの各契約検証はPASS。Ruffと`skills-ref`はローカル環境にない。remote Code QualityはPASS。公式Skill形式validation step自体もPASSしたが、同jobのrepository eval structure stepはREADMEのcatalog不足でFAIL。
- [ ] source／artifact／承認認証／native CAS／保存readbackとshared runtime owner検証をAへ接続できていない。以下のPR #22 handoff契約で継続する。
- [x] 本branchの実装と可能な局所検証を完了し、未検証条件を分けて記録した。PR #22だけで行う横断検証、全Skill routing、15＋10条件とS1〜S17の最終判定は担当branchでPASS扱いしない。

## 実装と受入契約

- `skills/ui-target-analysis/`はUI構造、操作、表示状態、navigationの論理owner。UI package形式とsingle writerは既存`spec-analysis`側の`ui-target-v1`契約を再利用する。
- `scripts/human_editing.py prepare`は検証済みbase/current/edit copyを照合し、UI-owned tableとNavigation proseだけをexisting `materialize` requestへ変換する。正本へ直接書かず、外部承認refは認証済みidentityとみなさない。
- `feature-index`は明示的なfeature artifact ref/revision・feature-to-Scope mappingをcurrent package snapshotへ結合し、file／section／physical line／stable ID／changed rowを都度導出する。二次索引やfeature ID列を`ui-target-v1`へ追加しない。
- test 01〜08は`tests/skills/runtime/test_ui_human_editing.py`に対応する。test 09〜10はisolated packaging、symlink root、重複JSON key、invalid mappingの追加安全性回帰。

## 局所検証記録

環境はPython 3.14.2。本repositoryのGitHub ActionsはPython 3.11を使う。

| 検証                                 | コマンド                                                                                              | 結果                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 人間編集8受入＋追加安全性            | `python -m unittest discover -s tests/skills/runtime -p 'test_ui_human_editing.py'`                   | PASS 10 tests。01 normal edit/readback、02 draft/retire/history、03 generated/control拒否、04 Authority/approval/evidence拒否、05 same-ID conflict・independent rebase・stale CAS拒否、06 direct edit保全/reopen、07 lost response/fingerprint replay、08 feature index、09 isolated copy、10 symlink/duplicate JSON |
| 既存package regression               | `python -m unittest discover -s tests/skills/runtime -p 'test_ui_target_package.py'`                  | PASS 19 tests                                                                                                                                                                                                                                                                                                        |
| migration preflight                  | `python -m unittest discover -s tests/skills/runtime -p 'test_migration_preflight.py'`                | PASS 9 tests                                                                                                                                                                                                                                                                                                         |
| trigger dataset contract             | `python -m unittest discover -s tests/skills/evals/trigger`                                           | PASS 1 test。train 12件・validation 8件、各positive/negative均衡、重複なし                                                                                                                                                                                                                                           |
| semantic dataset                     | `python scripts/skills/evals/semantic/validate.py`                                                    | PASS。24 Skills / 169 cases                                                                                                                                                                                                                                                                                          |
| semantic repository tests            | `python -m unittest discover -s tests/skills/evals/semantic`                                          | PASS 13 tests                                                                                                                                                                                                                                                                                                        |
| semantic shared runtime tests        | `python -m unittest discover -s scripts/skills/evals/semantic/tests`                                  | PASS 27 tests                                                                                                                                                                                                                                                                                                        |
| semantic candidate evidence/結果形式 | `python -m unittest discover -s tests/skills/evals/semantic -p 'test_ui_target_candidate_results.py'` | PASS 1 test。4 cases / 12 criteria。candidate generatorと同じsession LLMによる自己評価。独立Judgeではない                                                                                                                                                                                                            |
| helper compile                       | `python -m compileall -q skills/ui-target-analysis/scripts`                                           | PASS                                                                                                                                                                                                                                                                                                                 |
| shared Skill catalog precondition    | `python`でcurrent `skills/*/SKILL.md`とREADMEのbacktick名を照合                                       | FAIL: `ui-target-analysis`。README所有者が共通catalogを更新するまで`validate-skills.yml`全体はPASSしない                                                                                                                                                                                                             |
| 全runtime suite                      | `python -m unittest discover -s tests/skills/runtime -p 'test_*.py'`                                  | FAIL 506 tests: 10 failures / 9 errors。担当testは修正後に個別10件PASS。残る失敗はCI handoffのPython 3.14 nesting差、Project Context workflow-state provider不足、SQLite履歴DBが作成されない環境エラー                                                                                                               |
| deterministic eval全suite            | `python -m unittest discover -s tests/skills/evals/deterministic`                                     | FAIL 290 tests中4 failures / 1 error。loopback socketのsandbox拒否、未提供Project Context state-root/providerでWCAG workflow testsがblocked。UI-target既存contract testsに今回由来の失敗なし                                                                                                                         |
| formatter/lint                       | `python scripts/format_tracked.py check`                                                              | BLOCKED exit 2。environmentに`ruff` executableがないためCIと同じformat/lint一式を開始できない                                                                                                                                                                                                                        |
| 公式Skill形式validator               | `skills-ref validate skills/ui-target-analysis`                                                       | 未実行。`skills-ref`未導入。GitHub Actionsのinstall済みrunnerで確認する                                                                                                                                                                                                                                              |

triggerデータはCI形式と均衡を検査しただけで、全Skillを同時に利用可能にしたtrigger rateは未測定。Codex CLI `0.167.0`による独立Judge probeとして`python scripts/skills/evals/semantic/run.py --skill ui-target-analysis --eval-id UI-SEM-001 --output skills/ui-target-analysis/evals/semantic/candidate_outputs/UI-SEM-001.md --judge-command codex --no-daemon --strict-config --ask-for-approval never exec --ephemeral --sandbox read-only -`を試したが、`failed to initialize in-process app-server client: Read-only file system`で開始できなかった。独立Judgeとruntime triggerの実測は未完了で、共有runtimeへ迂回していない。semantic candidateは本branch内の参考判定であり、独立Judge commandによる再採点が必要。上記のFAIL / BLOCKEDはPASSへ読み替えない。

### GitHub Actionsの記録

最新remote head `166f63299a4bcd51b3dce5fe5d5a265548c5e6ad`の[Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42556473373)、[Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42556473447)、[Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42556473374)、[Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42556473380)はPASS。[Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42556473293)はofficial `skills-ref` specification validationがPASS、repository eval structureがREADMEの`ui-target-analysis` catalog不足でFAILし、後続のform／semantic counts／trigger contract stepsはskip。Cの変更境界外のREADME・shared route更新はA/PR #22に引き継ぐ。

## PR #22への引継ぎとshared owner依頼

1. **A / PR #22**：shared runtimeに`ui-target-analysis`を登録し、`review_ref`等を認証するowner verifier、Project Context Q06、保存先native CAS、revision history、独立readback、blocked/reopenを接続する。local helper requestの証拠文字列だけでは認証やexternal writeを許可しない。
2. **B / PR #22**：実Project Context Q06 agreementと保存先権限、実feature artifact ref/revisionと明示feature-to-Scope mappingを渡す。fixture結果と実artifact横断結果を分けて記録する。
3. **A / qa-workflow shared owner**：`README.md`は現在も`spec-analysis`のUI modeがpackageを作ると説明し、`skills/qa-workflow/SKILL.md`・`references/guidance.md`もUI package要求を`spec-analysis`へrouteしている。新Skill名のREADME登録もCIで必須。UI構造要求を`ui-target-analysis`へrouteし、仕様Authorityだけを`spec-analysis`に残すshared説明・trigger/isolated validationを更新する。Cでは共有範囲のため変更していない。
4. **共有評価仕様owner / PR #22**：`EVALS.md`のfull-agent trigger対象一覧とsemantic責務表に`ui-target-analysis`がなく、`UI-SEM-001`〜`UI-SEM-006`の対応も未記載。共通文書へSkill・12/8 trigger dataset・4 semantic casesを登録し、既存`spec-analysis`行のUI構造owner記述を外して、期待仕様・Authority・US/UC/AC/UNKNOWNの責務を残す。全Skill同時利用時のtrigger rate（正例は`>0.5`、負例は`<0.5`）とcandidate outputsの独立Judge採点も実測する。shared fileのためCでは変更していない。検証条件はrepository eval structure、semantic dataset/runtime、trigger dataset、実Agentログの各結果を区別して記録すること。
5. **E / PR #22**：実UI package、Authority artifact、既存test-analysis／TC／E2E consumerを接続し、UI observationとcurrent Authority refの分離、changed scopeだけの下流staleness、legacy package読取を横断確認する。
6. **PR #22**：全Skill同時のtrigger/routing、独立Judge評価、実provider経路、人間編集8ケースの統合経路、全CI、開発連動QA 15条件・QA全工程10条件・S1〜S17を統合branch上で判定する。PR #25のfixtureをowner実成果物の証拠に置換しない。

このbranchのcandidate semantic結果と独立fixture証拠は再利用可能だが、共有owner修正・実artifact接続・実trigger/remote CAS/owner authenticationの完了まではPR #25全体を統合完了として扱わない。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。
