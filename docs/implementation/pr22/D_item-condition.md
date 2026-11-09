# PR #22 並行実装：D — テストアイテム・共通条件

## 位置付け

製品機能とは別のテストアイテム、正式TCNとは別の共通テスト条件候補を、それぞれ独立の正本として管理する。

- 作業branch：`feat/pr22-d-item-condition`
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

関連完了条件の主な担当：開発連動QA 12・13・14の候補識別部分。正式設計への採否・期待結果はEが担当する。

## このbranchで変更する対象

- 新設`skills/test-item-analysis/**` と `skills/test-condition-analysis/**`
- 各Skillのstable ID・source fingerprint・候補対応・履歴・validator・評価／fixture

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

- [x] 既存feature・SCOPE・TR／TCN／CI・Disposition・ID管理・当該ownerのsource revision契約を確認した。
- [x] B・Eと機能ref、item ID、condition ID、候補根拠、非採用判断の受渡しを固定した。

## 作業内容

1. テストアイテムの独立ID、親子・多対多機能参照、UI／API／バッチ等の種類、予定／未実装／実装済み／廃止／不明、改版・循環検出を実装する。
2. 共通条件候補に安定ID、意図・根拠・Authority参照・適用可能種別・source revision・変更履歴を付与し、アイテム確定前でも独立識別できるようにする。
3. item候補とcondition候補を独立収集して、不足・重複・未発見母集団・未確認状態を相互照合する。全組合せを正式採用しない。
4. 条件候補／アイテムの再利用と再採番の違い、分割／統合／廃止／同名異義・異名同義、partial input、変更影響を検証する。
5. 正式item×condition採否・TCN／CI／期待結果候補の確定はEへ渡し、DではAuthorityや正式カバレッジを更新しない。

## 依存と引継ぎ

- B→D：feature ID・source inventory・revision。
- D→E：アイテム／共通条件候補のref・履歴・根拠と未確認母集団。
- A：runtime登録・provider保存契約を依頼する。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 2 Skillが独立に発火し、根拠付きのstable ID・履歴・階層／多対多・再利用を扱う。
- [x] 相互不足検出と候補／適用判断／正式設計／実行の別指標が成立し、未確認・blocked・分母0を100%にしない。
- [x] 同名別ID、ID誤統合、循環、分割・廃止、source欠落、旧revision、CAS競合の負例がPASSする。
- [x] E向けに正規のitem・condition refと固定fixture・revision・拒否例を提供し、D側の契約を局所検証した。Eの実成果物との接続試験はPR #22に引き継いだ。
- [ ] 新Skillの構造・isolated/trigger・決定論的・意味・局所回帰を実行した。

- [x] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、isolated packaging・決定論的テスト・意味評価・trigger評価のデータを揃えた。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [ ] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [ ] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をAと接続し、統合時に再取得できる証拠を残した。
- [ ] 担当branch内の実装・局所検証は完了し、PR #22のみで行う横断検証と15＋10条件の最終判定を**担当branchの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。

## 実装・担当内検証結果（2026-11-09）

### 実装

- `skills/test-item-analysis/` と `skills/test-condition-analysis/` を新設し、独立した`ITEM-*`／`COND-*`、履歴・source fingerprint・revision影響・候補照合を実装した。
- itemは階層・多対多feature ref・planned／unimplemented／implemented／unknown／retiredを扱う。conditionは意図・種別・Authority／evidence ref・候補状態・未確認理由を保持し、item確定前に独立識別できる。
- IDはhistoryから単調採番し、reuseは既存IDだけに限定する。split／mergeは関連元を記録する。merge元は同じ更新で証拠付き明示retireしない限り拒否する。retired IDは再利用しない。
- condition crosscheckは呼出元が明示した候補ペアだけを検証し、全組合せを生成しない。candidate／applicability／formal TCN・CI／executionの指標を分離し、Dの契約外件数は`null`のままにする。
- Aの現在のsource／artifact／operation claim項目に対応する未実行のwrite preconditionを出力する。D helperは候補のmaterializeとhash照合までで、provider保存・認証・CAS・readback・承認を実行したとは報告しない。

### 担当Dの独立検証

| 検証                                                                                                                                                                                       | 結果                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python -m unittest discover -s tests/skills/runtime -p 'test_test_item_condition_analysis.py' -v`                                                                                         | PASS、19 tests。stable ID、親子循環、reuse／split／merge／retire、source影響、partial／0分母、旧revision不一致、CAS競合、readbackの非認証性、明示pair、blocked条件のformal promotion拒否を検証。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `python -m unittest discover -s tests/skills/evals/deterministic -p 'test_d_item_condition_contracts.py' -v`                                                                               | PASS、4 tests。両出力fixture、0分母の誤った100%、正式Disposition拒否、isolated helper同一性を検証。負例mutationの列位置をfixtureの実際のMarkdown表に合わせて修正した。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `python scripts/skills/evals/deterministic/run.py --skill test-item-analysis --eval-id ITEM-OUT-001 --output skills/test-item-analysis/evals/output/cases/case-001/reference.md`           | PASS、10/10 assertions。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `python scripts/skills/evals/deterministic/run.py --skill test-condition-analysis --eval-id COND-OUT-001 --output skills/test-condition-analysis/evals/output/cases/case-001/reference.md` | PASS、11/11 assertions。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `python -m unittest discover -s tests/skills/evals/trigger -p 'test_trigger_datasets.py' -v`                                                                                               | PASS。両Skillともtrain 12件（positive 6／negative 6）、validation 8件（positive 4／negative 4）、集合は重複なし。これはdataset検査であり、実Agent上の発火測定ではない。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `python scripts/skills/evals/semantic/validate.py`                                                                                                                                         | PASS、25 Skills／167 semantic casesの構造検査。実LLM Judgeによる意味採点は未実施。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `python -m unittest discover -s tests/skills/evals/semantic -v`                                                                                                                            | PASS、13 tests。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `python -m unittest discover -s scripts/skills/evals/deterministic/tests -v`                                                                                                               | PASS、12 tests。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `python -m unittest discover -s scripts/skills/evals/semantic/tests -v`                                                                                                                    | PASS、27 tests。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `skills-ref validate`（CI固定commit `69ef37e9424c0a7ea9dd2293b559e43ec8176379`）                                                                                                           | PASS、全25 Skill。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `python scripts/format_tracked.py check`（Ruff 0.16.8／dprint 0.55.2）                                                                                                                     | PASS、tracked 226 files。固定toolchainを`/tmp`の隔離領域へ用意して実行。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `python -m compileall -q`（担当D scripts、validators、tests）                                                                                                                              | PASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `Validate Agent Skills`のrepository eval structure条件                                                                                                                                     | D frontmatter／trigger datasetの個別契約はPASS。workflow全体は共有`README.md`のSkill一覧に`test-item-analysis`と`test-condition-analysis`が未登録のためFAIL。A／PR #22へ登録を引き継ぐ。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| PR #26 Actions（実装head `aa7ddd2e7ac759202c231f470f00dae7c846e0b8`）                                                                                                                      | [Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42555181778)、[Validate Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42555182059)、[Validate Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42555181786)、[Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42555181775)はPASS。[Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42555181891)はDの仕様検証成功後、repository一覧条件で共有`README.md`に新設2 SkillがないためFAIL。 |

### 未完了・blocked・再開条件

| 状態    | 項目・影響                                                                | 理由／再開条件                                                                                                                                                                                                                                                                                                                                                                            |
| ------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 未完了  | Skillの実Agent発火・意味品質                                              | trigger datasetとsemantic rubric／fixtureの構造は用意したが、実Agent選択評価と実LLM Judgeを実行していない。対象Agent／Judge runnerが使えるCIまたは受入環境で実行し、結果を追加する。                                                                                                                                                                                                      |
| blocked | Skillのrepository一覧登録（`Validate Agent Skills` workflow）             | 公式`skills-ref validate`は全25 SkillでPASSし、Dのfrontmatter／triggerも個別契約を通過した。一方、workflowのrepository eval structure条件は共有`README.md`のSkill一覧に新設2 SkillがないためFAIL。AがREADMEを更新した後、PR #22でworkflowを再実行する。Dでは共有ファイルを変更しない。                                                                                                    |
| blocked | A runtime登録、実operation claim、provider保存／承認／CAS／履歴／readback | Aの`workflow_runtime.py`登録は現在6 Skillで、新設D Skillは未登録。保存provider・認証された承認主体も未選定。A／PR #22で登録とadapterを接続し、provider・権限・revision・readbackを実証後に再開する。Dのlocal `validate_readback`はtuple/hash検査に限る。                                                                                                                                  |
| 未完了  | B／Eの実成果物との横断接続                                                | Bの`feature-inventory-v1`合意fixtureとE向け拒否fixtureで局所検証した。実B artifactとEの正式validator／正本との接続はPR #22で両ownerが統合した後に実施する。                                                                                                                                                                                                                               |
| 未完了  | repository全体runtime回帰                                                 | `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`は515 tests中514 PASS／1 FAIL。残る`test_ci_handoff.test_json_nesting_failure_is_a_structured_input_error`はローカルPython 3.14.2で1100段配列の例外が`nesting`ではなく`JSON document must be an object`となる環境差で、D変更を通らない。CIはPython 3.11のため該当CI結果を確認する。Dの19 runtime testsは全件PASS。 |
| 完了    | repository全体deterministic regression                                    | `python -m unittest discover -s tests/skills/evals/deterministic -v`は294 testsすべてPASS。以前sandbox制限で失敗したsocket／SQLite／WCAG保存テストを含め、現在の環境で再実行済み。                                                                                                                                                                                                        |
| 完了    | PR #26 branch反映と関連Actions                                            | PR head `aa7ddd2e7ac759202c231f470f00dae7c846e0b8`へ担当Dの38ファイルを反映し、base `feat/development-qa-traceability`とDraft状態を維持。4 ActionsはPASS。`Validate Agent Skills`のREADME一覧FAILはAへ引き継ぐ。                                                                                                                                                                          |

### 互換性・PR #22への引継ぎ

- 既存のD artifact／legacy schemaはrepositoryに存在しない。DはB feature inventoryをread-onlyで参照し、既存Authority／TR／TCN／CI／TC artifactや既存consumerを更新していない。新D artifactはschema v1として追加し、source refとprovider CAS revisionを分離する。
- PR #22で、実B source revision／hash、実D artifact owner／revision、E validator拒否fixtureとの接続、A runtime登録・認証されたsave claim・provider履歴readbackを再取得して検証する。未接続のfixture成功を実owner保存の証拠にしない。
- PR #22で行う全owner横断統合、実Agent／実runner／provider、S1〜S17、人間編集8ケース、15＋10完了条件の最終受入はこの担当branchの完了扱いに含めない。
