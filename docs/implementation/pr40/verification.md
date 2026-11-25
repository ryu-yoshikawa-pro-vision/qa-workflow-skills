# PR #40 実装・受入検証記録

## 実施条件と現在状態

- 対象: `feat/context-rule-synthesis`
- 実装基準: main `197f1e0e1abe870b0cc793355e7abf73bf241d87`、PR branch pull後の基準 `a222e0e1f51e725c36db9be814885789e5ac9251`
- 最終反映前に `origin` をfetchして確認し、PR branchは同じ `a222e0e1f51e725c36db9be814885789e5ac9251`（ahead/behind 0/0）、mainも `197f1e0e1abe870b0cc793355e7abf73bf241d87` で変更なし。
- 対象PR #40は既存PRを維持する。PR #38/#39/#17と共通原則PRの内容を確認した。
- 正式保存の認可host/rootは未選定。実provider保存/readback、hostが供給する認可・実在性、一意性の実証は未実施であり、未接続部分をPASSとしない。
- 実Provider/Judgeと正式な3構成比較は未実施。Codex CLIのtarget-only positive trigger smokeは2件実行したが、全Skill横断・negative・反復測定ではなく、実Agent縦断受入でもない。
- Pythonは3.12.3。CI指定のPython 3.11はこの環境にない。`skills-ref`、dprint 0.55.2、Ruff 0.16.8は`/tmp`へ用意してローカル検証した。

状態の意味: **PARTIAL** は実装とローカル検証があるが、設計チェック項目全体は未確認。**BLOCKED** はhost/provider/認可接続を必要とするが未選定。**NOT RUN** は実Agent、独立Judge、または比較実測を実行していない。全状態は受入PASSを意味しない。

## 設計書13.2と結果の対応

### A. 不変ログ・データ契約・識別・状態遷移

| ID | 設計13.2の対象                                                           | 状態              | 実装・証拠                                                                                                                                                         |
| -- | ------------------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A1 | 抽出失敗/再実行、partial→complete identity、保存後readback失敗時の再利用 | PARTIAL / BLOCKED | batch/run identity、range/condition binding、訂正identityは `context_artifacts.py` のpure helperで検証。実保存・readbackとworkflow再利用はhost未選定のため未接続。 |
| A2 | Aの失敗状態を第4 storeなしでworkflow stateに記録                         | BLOCKED           | A試行stateの永続保存・再開は実装/実測されていない。保存先と信頼境界が未選定。                                                                                      |
| A3 | 自己申告ではなく実provider readbackで完了                                | PARTIAL / BLOCKED | helper/verifierは読取証拠の整合と自己申告のみの拒否を検証する。実readbackはhostが供給するため未実証。                                                              |
| A4 | resolution 7状態と鮮度/完全性軸の分離                                    | PARTIAL           | 候補schema/state validationと関連unit testを実装。変更伝播を含む全状態・一時障害の組合せは未検証。                                                                 |
| A5 | rejected/deferred/blocked/resolvedからの安全な再評価                     | PARTIAL           | state/currentness helperとSkill手順を実装。実環境の再開・一時障害解消は未検証。                                                                                    |
| A6 | candidate/operation/handoff identityの再計算と条件差の識別               | PARTIAL           | semantic input、requested scope、source/hash/range/condition、owner/scope/intentをbindingする単体テストはPASS。root境界での実保存一意性はBLOCKED。                 |
| A7 | competing/alternativeの相互参照と後継循環・自己参照拒否、0変更run        | PARTIAL           | candidate関係・cycle検証と0変更runのreadback契約をpure helperで検証。実run保存/readbackはBLOCKED。                                                                 |

### B. 並行実行・永続化・認可・再開

| ID | 設計13.2の対象                                               | 状態              | 実装・証拠                                                                                                                |
| -- | ------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------- |
| B1 | semantic handoff keyと並行workflowの重複防止                 | BLOCKED           | key生成はpure helperで検証。既存ownerの実保存単位・atomic dedupe/共有writerは未選定・未接続。                             |
| B2 | merge/split中の根拠保持、revision照合、循環回避              | PARTIAL / BLOCKED | candidate relationとscope/identityの決定論的検証はある。実保存層の条件更新・統合/分割競合を確認していない。               |
| B3 | planned payload/hash/metadataからの中断再開と新operation識別 | BLOCKED           | helperはrun identityとcompletion/readback整合を確認。providerの履歴、CAS再開、operation receiptは未接続。                 |
| B4 | root内kind更新・履歴readback・依存差分・別root拒否           | BLOCKED           | root相対ref/外部root境界は契約に反映。list/history/実revision/依存readbackのhost接続がない。                              |
| B5 | 通常保存、認可失効、共有更新、権限自己申告拒否               | BLOCKED           | Skillはhostからのroot/権限入力を要求し、自己申告を認証として扱わない。正式host/rootが未選定で実保存・失効を実測できない。 |
| B6 | QA書込み認可とAuthority承認の分離、root/path/symlink制限     | PARTIAL / BLOCKED | 境界要件とcanonical相対ref検証を実装。trusted hostのroot許可・symlink・実権限テストは未実施。                             |

### C. 横断検索・起動制御・鮮度・再評価

| ID | 設計13.2の対象                                               | 状態              | 実装・証拠                                                                                                      |
| -- | ------------------------------------------------------------ | ----------------- | --------------------------------------------------------------------------------------------------------------- |
| C1 | not_checkedの起動制御と完全0件の扱い                         | PARTIAL           | Skill guidanceとA/B契約で処理方針を定義。workflowへの実発火・未処理判定はAgent/host未接続。                     |
| C2 | 別scopeからの過去候補/Authority/Knowledge/Q発見とbatch再利用 | BLOCKED           | Skillの横断検索指示は実装。外部root/owner検索・別workflowでの再利用を実測していない。                           |
| C3 | run snapshotから直接参照根拠/evidence linksを復元            | PARTIAL / BLOCKED | snapshot/evidence schemaとref検証をpure helperで実装。実データのlist/readbackと再開は未接続。                   |
| C4 | 自己更新と外部変更、新反例、古いrunの採用拒否                | PARTIAL           | impact/currentness helperとchanged authority/addition testを実装。実provider変更後の採用gate/反例追加は未検証。 |
| C5 | 独立支持・Authority失効/置換による再評価、重複根拠排除       | PARTIAL           | data contract/Skill手順に独立性と再評価条件を記載。実Agent意味評価・複数workflowは未実施。                      |
| C6 | 却下scope外の仮説維持と必要質問の省略防止                    | PARTIAL           | scope-bound rejection/質問要件をSkill契約に記載。実Agent/既存owner handoffで未確認。                            |

### D. 帰納的推論・Authority・既存owner連携・変更伝播

| ID | 設計13.2の対象                                              | 状態    | 実装・証拠                                                                          |
| -- | ----------------------------------------------------------- | ------- | ----------------------------------------------------------------------------------- |
| D1 | 法則/差異条件/仮説比較とnot_checkedの意味品質               | NOT RUN | semantic evaluation cases/rubricsを追加。実Agent candidate出力と独立Judgeは未実行。 |
| D2 | 同じ観察の複数候補評価、5分類/反例分類とunclassified        | NOT RUN | Skill/data contractとsemantic fixturesを追加。実Agent評価・抽出品質測定は未実行。   |
| D3 | 情報源・componentの独立性と局所仕様の過一般化防止           | NOT RUN | guidance/semantic rubricに規則を定義。実Agentの意味評価は未実行。                   |
| D4 | 有効SPECを維持し、実装適合/不一致/未確認を区別              | NOT RUN | guidanceと例示で規則を定義。全9.2判定の実Agent受入は未実施。                        |
| D5 | PRODUCT_RISK/ASM/PROJECT_CONTEXT/回答承認をAuthorityと区別  | NOT RUN | Skill/data contractで区別。既存ownerからの実 readback/承認試験は未実施。            |
| D6 | UNKNOWN/Q、exploratory investigation、no_new_info終了と再開 | NOT RUN | routing/guidance契約を更新。既存ownerへの実handoff/一時障害後の再開は未実施。       |
| D7 | 候補更新と正式Authority/Risk等の下流変更伝播                | NOT RUN | 既存変更伝播契約をSkillで参照。実Machine Entity依存経路での受入は未実施。           |

### E. workflow完了判定・セキュリティ・効率・回帰

| ID | 設計13.2の対象                                            | 状態              | 実装・証拠                                                                                                                                     |
| -- | --------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| E1 | 無指定/補助/必須/単体モードの完了規則                     | PARTIAL           | routing/state/QA guidanceとdeterministic fixtureを更新。全modeの実workflow host試験は未実施。                                                  |
| E2 | owner verifier、複数input/readback/範囲/必須handoffと再開 | PARTIAL / BLOCKED | 新規owner verifier、runtime copy、64 KiB超の登録済みcontext本文transportを実装しunit test。実provider readback/host gate/v1-v2全再開は未確認。 |
| E3 | secret/PII、prompt injection、既存runtime/変更伝播の回帰  | PARTIAL           | fixtureは架空情報、対象unit/既存runtime suiteを実行。全秘密漏えい監査、実Agentの悪意ある資料試験、正式な3構成比較は未完了。                    |

## ローカル検証記録

| 検証                                                            | 結果                                     | 注記                                                                                                                                                                                                                                                                                                                                                                                             |
| --------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Context helper/owner/transport/deterministic contract 4 modules | PASS: 24 tests                           | `python3 -m unittest tests.skills.runtime.test_context_artifacts tests.skills.runtime.test_context_owner_verifiers tests.skills.runtime.test_context_runtime_transport tests.skills.evals.deterministic.test_context_rule_contracts -v`                                                                                                                                                          |
| owner verifier registry更新テスト                               | PASS                                     | 新規2 ownerを既存registryの期待集合に同期。                                                                                                                                                                                                                                                                                                                                                      |
| loopback HTTP統合テスト                                         | PASS（sandbox外で個別実行）              | sandbox内はsocket作成が拒否された。loopback許可の同一テストで再実行しPASS。                                                                                                                                                                                                                                                                                                                      |
| 全runtime回帰suite                                              | FAIL: 1,475 tests、10 failures・9 errors | 18件のSQLite履歴失敗は、環境の`/tmp/.git`をDB保護判定がworktreeと誤認したことが原因。隔離tmpfsでSQLite履歴module単体20件を再実行しPASS。残る1件はPython 3.12.3で既存JSON 1,100段nesting testが標準parserに受理され、期待regex `nesting` と不一致。test/codeはPR基準commitから未変更。CIはPython 3.11。                                                                                           |
| deterministic eval repository suite                             | PASS: 675 tests                          | 初回はrouting fixtureを83→87件へ増やした後に`test_ui_target_routing_contract.py`の期待件数が83のまま残っていたため1件失敗。期待値を87へ同期し、full suiteを隔離tmpfsで再実行して675件PASS。                                                                                                                                                                                                      |
| deterministic output eval manifests                             | PASS: 37 Skills・89 cases                | CIのmanifest gateをローカルでも再実行。新規2 case inputに`assets/output-template.md`の指定が不足していた問題を、各Skillに出力templateを追加して修正した。                                                                                                                                                                                                                                        |
| official `skills-ref`                                           | PASS: 全39 Skill                         | CI pinned Git commit `69ef37e...`を`/tmp`へinstallし、`skills/*`全てにvalidateを実行。                                                                                                                                                                                                                                                                                                           |
| semantic dataset validator/tests                                | PASS: 39 Skill・227 cases、14 tests      | 実Agentのcandidate/Judge評価結果ではない。                                                                                                                                                                                                                                                                                                                                                       |
| deterministic runner tests                                      | PASS: 12 tests                           | runner/loader/validator契約。                                                                                                                                                                                                                                                                                                                                                                    |
| trigger contract tests                                          | PASS: 17 tests                           | datasetの構造・balance・train/validation分離を含む。実発火評価ではない。                                                                                                                                                                                                                                                                                                                         |
| deterministic new-Skill example runner                          | PASS: 2 example × 3 assertions           | assetsをcanonical bytesとして `/tmp` に出力して検証。生成Agent outputの代替とは扱わない。                                                                                                                                                                                                                                                                                                        |
| formatter/whitespace/security CI contract tests                 | PASS: 19 + 3 + 2 tests                   | formatter script contractとsecurity contract。実版checkは別項目。                                                                                                                                                                                                                                                                                                                                |
| Codex CLI trigger target-only smoke                             | PARTIAL: 2 positive queries              | `codex-cli 0.172.0`を`codex --no-daemon --strict-config exec --json --ephemeral --sandbox read-only`で実行し、2件とも対象Skillの`SKILL.md`読込をJSONLで観測。各回で対象Skill 1件だけを提示し、他のQA Skill本文は渡していない。negative、反復、誤発火、正式trigger rateは未測定。model名はJSONLから取得できなかった。                                                                             |
| Codex CLI runtime safety                                        | NOT VERIFIED                             | CLIは`Untrusted project-local configuration is disabled`と警告し、repository `.codex/config.toml`のHook/execpolicy設定を無効化した。`--trust`等でユーザー設定を永続変更して迂回していないため、Hook dispatch・execpolicyは受入未確認。                                                                                                                                                           |
| formal trigger評価 / semantic実Agentと独立Judge                 | BLOCKED / NOT RUN                        | 既存`scripts/skills/evals/trigger/run.py`はClaude Code headless専用で、Codex CLIのJSONL計測と同一方式ではない。Claudeは起動していない。全39 Skill本文をCodexへ送る正式評価要求は自動承認審査で拒否された（理由: private repository由来の全39 Skill本文を認証済み外部サービスへ送る範囲が広く、対象Skill限定または宛先・送信内容の明示承認が必要）。経路を迂回せず、Judge candidate評価も未実施。 |
| trigger正式実行の事前見積り                                     | 見積のみ                                 | 既存Claude runnerのvalidation 16 query × 3回 = 48、train 24 query × 3回 = 72、計120 run。15秒/run・並列3の過去測定値による約10分の推定で、Codex CLIの実測時間や発火結果ではない。                                                                                                                                                                                                                |
| 実provider保存/readback・通常回帰                               | BLOCKED                                  | 認可host/root未選定。                                                                                                                                                                                                                                                                                                                                                                            |
| 3構成比較・最終構成測定                                         | BLOCKED                                  | 実Agent/providerと公平な同一環境の確保待ち。                                                                                                                                                                                                                                                                                                                                                     |
| Ruff pinned lint/format checks                                  | PASS: 0.16.8                             | tracked全体checkと対象Pythonの再checkがPASS。共通runtime_contract 9コピーは同一SHA-256。tracked全体checkで検出した既存3ファイルのformat差も正規化した。                                                                                                                                                                                                                                          |
| dprint pinned version                                           | PARTIAL: 0.55.2                          | `/tmp`へ用意し、今回変更したMarkdown/JSONの明示対象checkはPASS。全tracked checkでは、指定Plan 01の箇条書き前空行を整形した後も、変更対象外18ファイルでworktree CRLF（index/属性はLF）による改行差が残った。無関係ファイルは一括変換せず、clean checkoutのGitHub CIで再確認する。                                                                                                                 |
| GitHub Actions CI                                               | 修正後再実行待ち                         | 初回pushのdeterministic output workflowがmanifest gateで失敗。新規2 case inputが`assets/output-template.md`を参照していなかったため、Skillのoutput templateと参照を追加し、同gateのローカル再実行はPASS。修正commit後のCI結果を別途確認する。                                                                                                                                                    |

## ドキュメントと実装の差異

- Plan 01/02/03は指定rootの保存/list/history/readback、ownerとの実縦断接続を要求するが、実装は純粋contract/helperとreadback証拠検証までで、保存境界は未接続。認可host/root未選定のため実保存・実readbackをPASSにせず、該当するPlan受入を未完了に保つ。
- 基本設計13.2とPlan 03の受入は実Agent/独立Judgeおよび3構成実測を要求する。semantic/triggerデータセットとlocal validatorは追加したが、実行結果ではない。これらは未実施/blockedとしている。
- Plan 03は既存trigger runnerを指定するが、[run.py](../../../scripts/skills/evals/trigger/run.py)はClaude Code headless/Claude model固定である。Codex CLIへの切替要求に基づき新規Skillごとにtarget-only positive smokeを1件実行し、対象`SKILL.md`読込を観測した。これは既存runnerと同一条件のrate測定ではない。
- Codex CLIの実行中に未信頼project warningが出てrepository-local Hook/execpolicyが無効化されたため、実Agent smokeの安全境界は未検証。`--trust`等で永続設定を変更していない。
- 既存Claude runnerを使う初回trigger要求は自動承認審査で拒否され、Claudeは起動していない。提示理由は、認証済み実Agent実行がrepository由来のquery/Skill本文を外部Claudeサービスへ送る点。ユーザーはClaude利用を指示しておらず、Codex CLIでのtrigger確認へ切り替えた。
- 全39 Skillを同時に使うCodex正式trigger要求も自動承認審査で拒否された。提示理由はprivate repository由来の全Skill本文を認証済み外部サービスへ送る範囲が広く、対象Skill限定または宛先・送信内容の明示承認が必要というもの。拒否を迂回していない。
- `routing_cases.json`と`routing_candidate_outputs.json`は87件だが、追加変更後も`test_ui_target_routing_contract.py`が83件を期待していた。期待件数を87へ同期し、2件の該当testを再実行してPASS。
- `EVALS.md`は通常Skillの決定論的出力に`assets/output-template.md`を要求するが、新規2 Skillに該当templateとeval inputからの参照がなかった。各Skillへ出力templateを追加し、CIと同じmanifest gateで37 Skills/89 casesを確認した。
- tracked全体のRuff checkが既存の未整形3ファイルを検出したため、format-onlyで`deterministic/__init__.py`、`deterministic/result.py`、`semantic/__init__.py`を正規化した。dprint全体checkに残る未変更ファイルのCRLF差は、このWSL worktreeだけの状態としてclean CIで確認する。
- dprint checkがPlan 01の箇条書き前の空行不足も検出したため、意味を変えない整形だけを適用した。残る18件は全て変更対象外ファイルの改行差である。
- Python 3.12.3では `json.loads` が1,100段のJSON arrayを受理するため、既存test `test_json_nesting_failure_is_a_structured_input_error` の期待（`nesting`）と不一致となった。テストと実装はPR基準commitで未変更。CI指定Python 3.11の結果を別に確認する。
- その他に文書/実装間の不一致を確認した場合は、レビュー完了後ここへ追記する。
