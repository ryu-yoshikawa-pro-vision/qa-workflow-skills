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
- [x] Bの公開実装からB→D入力契約を確認し、D→EについてはD所有の候補ref・履歴・根拠・未確認母集団のhandoff項目を定義した。Eの正式schema／採否契約は未提供のため未確定として扱う。

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

## 完了基準の再評価（2026-11-09）

| #  | 担当Dの条件                                      | 判定                           | 根拠・残る依存                                                                                                                                                                                                                                                                                                                             |
| -- | ------------------------------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1  | 2 Skillの独立発火と正常な入力処理                | 部分完了／trigger blocked      | Dの局所CLI・入力契約はPASS。実Agent試行はローカル25 Skill構成で120予定中3件（有効2、host connector混入1）を実行したが、最新の統合対象は27 Skillであり正規評価として採用しない。発火率・誤発火率は未測定。connectorのない公式Agent環境が必要。                                                                                              |
| 2  | stable ID、履歴、階層、多対多feature参照、再利用 | 局所完了                       | D runtime 38件、D deterministic契約4件がPASS。ID再利用・split／merge／retire・循環・履歴改変・同じ理由／根拠での連続更新後の再送を確認。                                                                                                                                                                                                   |
| 3  | 条件候補の独立識別と再利用                       | 局所完了                       | condition生成、再利用、履歴、unknown／blocked、item未確定時の独立候補、`no_change`後の未解決条件を局所テストで確認。                                                                                                                                                                                                                       |
| 4  | 不足、重複、未確認、blockedの検出                | 局所完了                       | missing／malformed／retired item参照、source競合、重複pair、部分母集団、stale／unknown／blocked、分母0、未解決状態の再materialize後のcrosscheck維持を負例で確認。                                                                                                                                                                          |
| 5  | 候補識別と正式設計・実行指標の分離               | 局所完了                       | crosscheckは明示pairのみを検査し、E所有の適用可否・Disposition・TCN／CI・期待結果を生成しない。D外指標はnullのまま。`no_change`は候補更新有無と分析状態を分離する。                                                                                                                                                                        |
| 6  | source変更と履歴互換性                           | 局所完了                       | current sourceの競合revision拒否、順序非依存、無関係sourceの更新分離、旧v1 eventの再読込、履歴非再生成を確認。source変更後・未再検証の状態も再送時にstale／recheckとして保持。実保存artifactとの照合はPR #22。                                                                                                                             |
| 7  | E向け正規ref、fixture、拒否例                    | D側局所完了                    | fixtureは`project:shop`／`feature-inventory:shop`／`feature-r1`／`commit:abc123`を使い、handoff hashをB形式から計算する。E実装・正式validatorが未提供のため実consumer接続はPR #22。                                                                                                                                                        |
| 8  | 正常系・負例・回帰                               | D側局所完了                    | Python 3.11.18でD runtime 38/38、全runtime 534/534、D deterministic 4/4、repository deterministic 294/294。item／condition出力評価10/10・11/11。Python 3.14.2では共有CI handoffの既存JSON nestingテストのみ1件失敗し、3.11.18ではPASS。                                                                                                    |
| 9  | Skill validation、isolated packaging、評価       | 部分完了                       | ローカルD branchの固定commit公式skills-refで25 Skill、semantic dataset／rubricで25 Skill・167 caseがPASS。最新PR merge CIでは27 Skill・171 caseもPASS。D helper byte-identical packaging、trigger dataset、semantic tests 13件、format・compileallはPASS。実Agent trigger全120件はblocked。保存済みITEM／COND semantic Judgeは各4/4 PASS。 |
| 10 | Aの公開契約との照合・引継ぎ                      | D局所契約完了／保存接続blocked | Dの`operation_claim_details`をAの公開validatorで直接検証するテストがPASS。provider、認可済みapproval、native CAS、immutable history、readbackはA側runtime登録・実providerが必要。                                                                                                                                                          |
| 11 | 必要な実runner／実Agentの担当単独経路            | 部分完了／外部依存blocked      | `codex-cli 0.167.0`でローカルcanonical 25 Skill workspaceを使った単独CLI試行でhost管理connectorが発火し、現行統合セット27 Skillの正規120件は未完了。timeout handlerのbytes／str対応もtimeoutを再現して検証できていない。実provider保存・承認・CAS・readbackも未接続。                                                                      |
| 12 | PR #22への検証証拠・未完了条件の引継ぎ           | D側引継ぎ完了                  | 本書にno_change修正、回帰証拠、評価結果、環境依存と再開条件を記録する。PR #22で実B artifact、E consumer、A provider、全体横断受入を行う。                                                                                                                                                                                                  |

15条件・10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケース、およびPlan詳細07の5シナリオはこの表で代替・縮小しない。全体の統合・総合受入はPR #22が担当する。

## 実装と6件のレビュー指摘

| 指摘                        | 原因                                                                                                       | Dでの修正                                                                                                                                                                                                                                 | 回帰証拠                                                                                                                                      |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| B→D入力契約                 | Dがsnapshotと分析reportの同一objectを期待し、Bのfeature_registry.analyze()が返す別object契約と違っていた。 | {snapshot, analysis}を受け、Bのreport／handoff field set、snapshot hash、owner／scope／artifact／revision、source inventory、feature IDs、boundary、metricsを相互照合。incompleteは不完全として保持し、stale／blocked／idempotentは拒否。 | B分割出力、revision/hash混在、source不一致、部分・未取得、unknown領域、欠損・型不正、契約driftのテスト。                                      |
| item artifact validator     | condition側crosscheck validatorがfingerprint一致を主に見て、item owner validatorの意味検証より弱かった。   | item owner契約と同等の意味検証をcondition Skill package内へbyte-identicalなread-only helperとして同梱。別Skill runtime importは追加しない。                                                                                               | kind/status、必須field、親参照／循環、feature、history、evidence、再fingerprint済み不正payloadについてowner／crosscheckの受入結果一致を比較。 |
| history event ID衝突        | event IDがevent bodyだけで決まり、別revisionで同じreason／evidenceを使うと衝突し得た。                     | 新規event IDにbody、sequence、previous event IDを結び付け、決定論と一意性を両立。replay／no_changeでは追記しない。旧event IDはそのまま検証し、過去historyは再生成しない。                                                                 | 同一reason/evidenceの連続更新、異なる変更、再送、no_change、旧history、重複／改変／欠落を検証。                                               |
| 未発見item参照              | 形式上有効な未登録IDが例外となりcrosscheck全体を停止していた。                                             | malformed IDは拒否し、形式有効で未発見のIDはunconfirmed不足として理由・recheck IDを返す。自動生成・condition ID変更・正式不採用扱いはしない。                                                                                             | 未発見→再登録後の再照合、retired、unknown、部分artifact、malformed IDのテスト。                                                               |
| source revision currentness | 同一論理sourceの競合revision/hashが格納順に依存し得た。                                                    | current集合は論理sourceごとに一revision/hashへ制限。historyには過去revisionを保持し、並び順に依存しない比較とする。source_changedは実revision変化時だけ追記。                                                                             | 重複／競合revision・hash、順序反転、履歴とcurrentの差、source欠落、無関係source更新、impact/materialize整合のテスト。                         |
| crosscheck集計・完了        | retiredを未提案へ混ぜ、condition stale／unknownでもitem currentだけでcompleteになり得た。                  | item／condition両側、source母集団、unknown／blocked、分母0、未解決参照、明示pairの機械矛盾を全てgate。retiredは別listへ分離。                                                                                                             | stale／retired／blocked／unknown、pairなし／重複／再利用、feature矛盾、明示外pair、formal E field拒否のテスト。                               |

追加で、B report statusをcandidate status変数で上書きしていた局所shadowingを修正し、Bの実statusを保持する回帰テストを追加した。型不正な配列status／classificationがTypeErrorや誤受入にならず契約エラーになること、同じ古いsourceを再送して不要なsource_changed historyを増やさないことも確認した。 JSON parserが標準外のNaN／Infinityを受け入れていたため両isolated helperで拒否し、invalid UTF-8、malformed JSON、duplicate key、16 MiB超過、deep schema-invalid payloadのfail-closed回帰も追加した。ITEM semantic caseはnarrativeしか与えない一方でreferenceがB snapshot／hash・stable IDを前提としていたため、最新B→D契約に合わせてinput／reference／rubricを修正した。

## 公開契約とowner境界

- **B→D**：Bの公開実装はsnapshotと分析reportを別々に扱う。D入力はこの2 objectを明示し、project_ref、artifact_ref、artifact_revision、source_revision、handoff.snapshot_sha256、source inventory、feature IDs、unknown areasをfeature_inventory_contextへ保持する。Bの保存済みrevision・source revision・snapshot hash・D candidate fingerprintは別概念として扱う。局所fixtureは公開契約準拠であり、Bの実保存artifactを使った横断証拠ではない。
- **D→E**：Dはowner／scope／artifact ref、stable ID、candidate fingerprint、current source revision、根拠、gaps、unknown／recheck state、明示candidate pairを提供する。PR #27のE実装・正式validatorが未提供のため、DはEのschema、採否、Disposition、TCN／CI、期待結果を独自確定しない。実consumer接続はPR #22で行う。
- **A storage handoff**：Dのclaim detailsはAの現在のvalidator契約（owner_skill、scope_ref、operation_type、target_ref、source_revisions、artifact_revisions、expected_revision、approval_ref、permission_scope、resume_owner）に合致する。D helperはperformed:false、provider_selected:false、approval unresolvedを返す。永続化、認可済みapproval、CAS成功、immutable history、readback成功を主張しない。
- **既存consumer**：DはAuthority、TR、TCN、CI、TC、実行結果を更新しない。candidate pairは明示されたものだけを機械照合し、全直積を生成しない。

## `no_change`再送で未解決状態が消える問題

### 原因と修正

- item／conditionの両`materialize()`は、前回artifactと今回候補のprojectionが一致すると、診断を計算する前に`status: no_change`、`valid: true`、`issues: []`を返していた。B分析がincomplete、source boundaryがpartial、候補currentnessがstale／unknown、conditionがunconfirmed／blockedでも、呼出元が最新結果だけを見ると未解決事項が見えなくなる。`test_no_change_replay_preserves_unresolved_analysis_state`で修正前の`issues=[]`を再現した。
- 早期returnを除き、毎回source・currentness・gap・状態診断と指標を計算してから`no_change`を返す。`status`は従来どおり候補内容の変更有無を示し、追加の`analysis_status`が`complete`／`incomplete`を表す。`valid`は構造検証のみを表す。
- itemは`issues`、stale／unknown／recheck item IDs、未表現feature IDs、候補識別率と測定不能理由を返す。conditionは`issues`、stale／unknown／unconfirmed／blocked／recheck condition IDsを返す。`crosscheck()`を同じ未完了artifactで再実行した結果も等価で、gap／incomplete状態を保持する。
- `candidate`は前回の検証済みpayloadをそのまま返し、stable ID・fingerprint・append-only historyを変更しない。履歴の連続イベント後の同一再送、旧v1のread-only読取、既存の誤artifact拒否テストも維持した。provider revision fixture（`provider-r1`／`provider-r2`）とcandidate fingerprintは別の値として扱う。
- `no_change`のwrite preconditionは`performed: false`／`provider_selected: false`のみで、provider write／CAS／readbackを要求しない。永続化成功や承認済みを意味しない。
- 両Skillの`SKILL.md`、`references/data-contract.md`、出力templateに意味を追記し、出力fixtureを更新した。`candidate_support.py`の共通処理変更は不要だったため両isolated packageの同一性を維持した。

### 回帰検証

追加したD runtime回帰は、B分析incomplete、partial source boundary、unknown area、未取得source、未表現feature、stale／unknown currentness、unconfirmed／blocked condition、無効previous artifact、completeな同一入力の複数再送を扱う。正常系ではstable ID・fingerprint・history・返却順序が変わらず、write要求が発生しないことを確認する。履歴同一性、source競合、旧v1互換性は従来の回帰テストでも再確認する。

## 検証証拠

作業開始時のPR #26 headは`a744fdae35360c2c44853e43e6045c16fbdfc9d9`。PR情報の`base_sha`／merge-baseは`d38b775e43f7f0a86a834fef4a122f04d30ef724`であり、対象branch `feat/development-qa-traceability`の最新tipは`4de27674abefdcb2275c810d786a18fc0defaffd`。変更前のPR merge test SHA `5d745ffdf6ca77aa9a6c27b2d5902f84527f3c6e`ではPython 3.11.18で全runtime 613/613だった。変更後のPR headは`244b53f4b923e87614b746a2d6d5a9a72692df12`、Actionsが実際にcheckoutした仮merge SHAは`080c63bd729dd91e0f49f9e2f6693123eb75c873`（head `244b53f`＋base tip `4de2767`）。このheadの5 ActionsはすべてPASS。merge結果では全runtime 619/619、deterministic 296/296、Validate Agent Skills 27 Skill、semantic dataset 27 Skill／171 case、Code Quality 241 files、Codex Harness Windows launcher 55 testsを確認した。ローカルD branchの検証件数（25 Skill／167 case、runtime 534、deterministic 294）とは対象treeが異なる。

| 検証                                                                                                                                                                                              | 結果・境界                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python -m unittest discover -s tests/skills/runtime -p 'test_test_item_condition_analysis.py' -v`                                                                                                | Python 3.11.18でD runtime 38 tests PASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `python -m unittest discover -s tests/skills/evals/deterministic -p 'test_d_item_condition_contracts.py' -v`                                                                                      | Python 3.11.18でD deterministic 4 tests PASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| D output eval（ITEM-OUT-001、COND-OUT-001）                                                                                                                                                       | item 10/10、condition 11/11 PASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`                                                                                                                           | Python 3.11.18で534/534 PASS。Python 3.14.2では共有`ci_handoff`の`test_json_nesting_failure_is_a_structured_input_error`だけが失敗（期待regex `nesting`、実際の例外`JSON document must be an object`）。D変更経路外で、3.11.18ではPASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `python -m unittest discover -s tests/skills/evals/deterministic -v`                                                                                                                              | Python 3.11.18で294/294 PASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| official `skills-ref validate`                                                                                                                                                                    | workflowと同じ固定commit `69ef37e9424c0a7ea9dd2293b559e43ec8176379`を使用し、全25 Skill PASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| trigger dataset tests                                                                                                                                                                             | 1/1 PASS。発火率評価とは別。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `python scripts/skills/evals/semantic/validate.py`／semantic tests                                                                                                                                | 25 Skill／167 cases検証PASS、repository tests 13/13 PASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| PR #26 latest GitHub Actions（head `244b53f4b923e87614b746a2d6d5a9a72692df12`、base tip `4de27674abefdcb2275c810d786a18fc0defaffd`、仮merge checkout `080c63bd729dd91e0f49f9e2f6693123eb75c873`） | [Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42590569915)、[Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42590569675)、[Validate Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42590569565)、[Validate Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42590569712)、[Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42590569592)はすべてPASS。merge treeでruntime 619/619、deterministic 296/296、27 Skill／171 semantic caseを確認。 |
| formatter・patch whitespace                                                                                                                                                                       | Ruff 0.16.8／dprint 0.55.2でtracked 226 files PASS。`test_format_tracked.py` 10件、patch whitespace test 3件、`git diff --check`もPASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| D scripts／runtime test `compileall`                                                                                                                                                              | Python 3.11.18でPASS。isolated package testはhelper byte-identical、CLI self-containedを含めPASS。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 保存済みの実Agent／Judge semantic評価                                                                                                                                                             | ITEM-SEM-001、COND-SEM-001とも実Agent出力とJudge resultを照合し4/4 PASS。実出力とresult JSONをSkill配下の既存`evals/semantic/candidate_outputs/`形式で保存。SHA-256と評価変更への影響は次の記録。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Codex CLI実Agent trigger試行                                                                                                                                                                      | 下記の記録参照。正規suiteは未完了でPASSではない。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

実Agent出力・Judge resultの対応:

- item output: `skills/test-item-analysis/evals/semantic/candidate_outputs/ITEM-SEM-001.md`、SHA-256 `eb43c435babd62798ce0ae7fef34d6171285d261d5f78cd65afc91a3f984fec8`。
- item Judge result: `skills/test-item-analysis/evals/semantic/candidate_outputs/results/ITEM-SEM-001.json`、SHA-256 `bdef63d826f2aff0b927c46b8ff706895e8adec182a46aa957b5dbac9e5afc15`。
- condition output: `skills/test-condition-analysis/evals/semantic/candidate_outputs/COND-SEM-001.md`、SHA-256 `4672012d8f4f7d7b9523fcff8aa780953cc0478512c2ee9631707e7a9b97fc3d`。
- condition Judge result: `skills/test-condition-analysis/evals/semantic/candidate_outputs/results/COND-SEM-001.json`、SHA-256 `74fb654ae37de1f632c042c233a88981d47453b08c41643025d5471aa7c56cb9`。
- Judge event logは各4 eventで、`item.completed`は`agent_message`。command/MCP tool eventなし。保存JSONのrubric IDsは対応するSkillの現在の`evals.json`／`rubric.json`と一致し、Judge evidenceは実出力の該当記述を意味的に支持する。新変更はmaterialize helperのno_change result説明であり、両narrative-only caseはmaterializeやno_change状態を要求しないため、意味評価への影響なしと判断して再実行していない。

### 実Agent trigger評価の結果と再開条件

`EVALS.md`の正規suiteはrepositoryの全canonical Skillを同時提供し、各D Skillのtrain 12 query（positive 6／negative 6）とvalidation 8 query（positive 4／negative 4）を、queryごとに独立contextで3回実行する。最新のPR merge CIで確認したcanonical集合は27 Skill。全40 query・120 invocationが必要で、回答文ではなく実際のSkill read eventで判定する。

repositoryのtrigger runtimeはdataset構造検証を提供するが、実Agent invocation runnerは提供していないため、一時runnerでread-only実行した。実行条件は`codex-cli 0.167.0`、`codex --no-daemon --strict-config`、`codex exec --json --ignore-user-config --ephemeral`、独立process/context、read-only sandbox、当時のローカルcanonical Skill 25 packageである。実行期間は2026-11-09 08:33:11〜08:34:26 UTC。後からPR #22側の2 Skillを含む統合セットが27 Skillと確認されたため、この試行は現行canonical集合を使った評価ではない。

120予定中3 invocationだけ実行した。`test-item-analysis`／`train-001`／repeat 1・2はexit 0、各21.81秒／23.11秒で、Skill read event `item_2`を記録したpositive triggerの診断行2件。repeat 3は30.65秒後にhost-managed `codex_document_control.list_document_sessions` と`mcp_tool_call`が観測され、該当invocationを`connector_invalid`として除外しsuiteを停止した。117 invocationは未実行。外部へのwriteはない。ローカル`codex mcp list`が空でもhost connector不在の証明にはならないことを確認した。この2行も全27 Skill構成での正規評価結果には数えない。

一時JSONLは`/tmp/pr26-trigger-eval-a744fda.jsonl`、summaryは`/tmp/pr26-trigger-eval-a744fda-summary.json`。本文・Agent応答は保存せずquery hashとevent IDのみを記録した。部分実行のため、正例発火率・負例誤発火率・query別合格率・反復間のばらつきは**未測定**。summaryにある部分・無効実行ベースの暫定rateは公式値として採用しない。過去の初回timeoutでは`TimeoutExpired.stdout`／`stderr`のbytes／str型不整合が報告されている。今回の3件ではtimeoutが発生しなかったため、その例外経路の修正確認にはならない。次のrunnerでは両型を扱えることを事前検証する。

再開条件は、host管理connectorが一切提供されない公式の隔離Agent環境を用意すること。設定を無断変更せず、最新canonical 27 Skill・40 query・各3反復のまま全120件を独立実行し、有効なread eventと失敗／timeout／未実行を記録したうえで、EVALS.mdの基準でrateと受入を再判定する。同じquery／repeatの重複を集計せず、connector呼出を検出したinvocationは無効化する。

## 互換性・移行・rollback

- test-item-candidates-v1／test-condition-candidates-v1の旧payloadは、feature_inventory_contextがないlegacy formをread-onlyで検証可能。crosscheckではsource populationを完全と推定せずincompleteにする。次の成功materializeで現在のB contextを追加するが、stable ID、id_history、既存history eventは書換えない。
- 新規event IDはbody／sequence／previous event IDに結び付く。新readerはlegacy body-fingerprint eventとchain eventの双方を検証する。旧writerは新規chain eventを理解しない可能性があるため、provider書込みを有効化する前にD reader/writerの対応versionをA／PR #22で統一する。Dは旧artifactへ一括migrationや再採番を行わない。
- Dにproviderは選択されず、実保存・approval・CASは未接続。repository内に実保存artifactがあるとは確認していない。外部保存artifactの有無・backup・rollback実証は未検証。PR #22で保存先を選ぶ前に旧historyをread-only validateし、forward-compatible readerを配備してから最初のwriteを行う。
- rollback時はD artifactを旧writerで更新しない。復旧は新readerを使うcode forward-fixを優先し、旧writerへ戻す必要があれば保存artifactをread-only保全してowner承認の移行計画を立てる。実providerがないため現時点でデータrollbackは発生していない。

## 未完了・blocked・再開条件

| 状態    | 項目／影響                                                             | 理由／再開条件                                                                                                                                                                                                                                                                               |
| ------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| blocked | 全40 trigger query×3の実Agent発火／routing評価                         | 25 Skill構成で120予定中3件を試し2件は診断read event、1件はhost connector混入で除外。最新canonical集合は27 Skillのため全3件とも正規評価へ算入しない。旧timeout bytes／str不整合は今回再現しておらず修正確認も未完了。connector-freeの隔離Agent環境とbytes／str対応runnerで全120件を実行する。 |
| 完了    | 実LLM Judge                                                            | ITEM-SEM-001／COND-SEM-001のAgent出力・Judge result JSONをSkill配下へ保存し、両方4/4 PASS。イベントログではJudgeの外部tool呼出なしを確認。                                                                                                                                                   |
| blocked | Aのruntime/provider、approval、native CAS、immutable history、readback | D claim validator整合は局所確認済み。A ownerがD操作登録とprovider／認可主体を接続し、実revision競合・readbackを証明後に再開。                                                                                                                                                                |
| blocked | B実保存artifact、E正式validatorとの横断接続                            | B契約準拠fixtureで局所検証済み。A/B/Eの成果物・Eの実装がPR #22へ統合された後に実refs/revisionsで再検証。                                                                                                                                                                                     |
| 完了    | Python 3.11全runtime                                                   | ローカルPython 3.11.18で全runtime 534/534 PASS。変更後PR head `244b53f`の仮merge checkout `080c63b`ではCI runtime 619/619 PASS。全5 Actionsの結果とbase/head SHAは上記に記録。                                                                                                               |
| 引継ぎ  | 全体受入                                                               | 15＋10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケース、Plan詳細07の5 scenarioはPR #22が横断接続後に実施する。                                                                                                                                                                                |

## PR #22へ引き渡す項目

1. Bの実snapshot/report pair、source/artifact revision、handoff hash、unknown／unretrieved stateを実D materializeに接続し、source変更時のD impactとcurrentnessを確認する。
2. D artifact ref／candidate fingerprintとEの実owner validatorを接続する。未発見・retired item、unconfirmed condition、明示pairのみの判断境界をEが受入／拒否できるか確認する。
3. AにD Skill operation登録・claim mapping・permission／approval・provider-native CAS・immutable history・readbackを接続し、実save/reload/競合/blocked-resumeを検証する。Dのcandidate fingerprintをprovider revisionとして使わない。
4. 新reader/writerを同一対応versionでproviderへ導入し、旧D historyをread-only validateする。実保存artifactとrollback可否は保存先確定後に判断する。
5. doc-only追補を含む最新PR #26 headのActionsを再確認し、repository全体regression、現行27 canonical Skill同時の実Agent発火、実Judge、S1〜S17、人間編集8ケース、15＋10条件、Plan詳細01〜08と5 scenarioをPR #22で再実施する。
