# PR #14 Playwright観測レビュー修正計画

## 0. 依頼概要

- 依頼内容: 既存ツール・標準APIを優先する開発原則を既存文書へ反映し、formal WCAG固定probeの名前・ロール、Shadow DOM、可視性、フォーカス、ページタイトル、データ最小化を実行結果に基づいて修正・検証する。
- 背景: PR #14のレビューで独自DOM推定とブラウザ観測契約の不整合が指摘された。
- 期待成果: 必要な範囲だけ実装修正し、Playwright実ブラウザ回帰、production normalizer経路、repository標準検証、最新PR headのCIを証拠化する。

## 1. ゴール / 完了条件

- ゴール: Playwright、ブラウザ標準API、既存repo helperを優先し、取得できない値は推測せず未確定にする。
- 完了条件（DoD）:
  - README、`usability-inspection` Skill、Playwright observation referenceに開発・観測原則が追記され、routing descriptionは変わらない。
  - Role/nameはブラウザ計算値を使い、取得不能と空値を区別する。Shadow DOM対象とrefが誤って欠落・衝突せず、完全性未確認を完了扱いしない。
  - Locator visibility、DOM存在、AX tree包含、操作可能性、視覚観測の意味を混同しない。
  - フォーカス順は実際のPlaywright Tab遷移から取得し、上限・循環・復元失敗を区別する。
  - formal title判定が通常title probeと整合し、raw title textを保存しない。
  - 不要な任意画面テキスト・snapshotを追加保存しない。既存の固有決定論的契約を保持する。
  - 実ブラウザ回帰、production normalizer/procedureの統合検証、標準repository検証が成功する。
  - PR本文・検証記録を更新し、通常commit/push後の最新PR head CI 3件が成功する。

## 2. 現状理解と前提

- 現状理解: branch/local/PR headは`feat/usability-evaluation-skill` / `ebee4278060a4423c3d11d5afbe99ab94cc2cc38`で一致し、mainとの差はahead 323 / behind 0。tracked変更はなく、ユーザー所有の未追跡ファイル1件がある。現在headの3 CI jobは成功。
- 現状の固定formal probeは、DOM属性と`textContent`からrole/nameを独自推定し、`document.querySelectorAll()`によりopen Shadow DOM対象を落とし得る。`visible()`はopacity 0を除外する。Focus sequenceはDOM候補数から探索回数を決めている。formal titleは通常title probeより条件が弱い。
- 前提: 正式に利用可能なPlaywright Locator/`ariaSnapshotJSON()`を実ブラウザで確認し、結果は必要なrole/name predicateだけに縮約して保存する。Playwright APIで必要情報を安定して結び付けられない範囲は未確定として閉じる。
- 対象外: Semantic 83全量、Trigger 180全量、Holdout 24、全WCAG fixture closure、PR #17評価基盤、全Skill改修、依存追加、browser framework、CDP、汎用ARIA計算やDOM crawler。

## 3. 質問 / 曖昧性

- 必ず質問する不透明点: なし。APIで取れる情報は実結果で確定し、取れない範囲はfail-closedとする方針が依頼内で定義済み。
- 仮定してよい細部: 現在の固定probeの有限dispatch/schemaと既存Playwright起動経路を維持し、対応するテストfixtureを最小限拡張する。
- 未回答の重要質問: なし。

## 4. 影響範囲

- 影響範囲: README / `usability-inspection`の開発規則、Playwright observation guide、formal machine browser observation plan、fixed probe、formal result consumer、canonical fixtureと既存deterministic/browser tests、PR validation report。
- 確認対象ファイル:
  - `README.md`
  - `skills/usability-inspection/SKILL.md`
  - `skills/usability-inspection/references/playwright-observation.md`
  - `skills/wcag-conformance-evaluation/SKILL.md`
  - `skills/usability-inspection/scripts/fixed_wcag_machine_probes.js`
  - `skills/usability-inspection/scripts/fixed_browser_probes.js`
  - `skills/usability-inspection/scripts/observation_contract.py`
  - `skills/usability-inspection/scripts/inspection_runtime.py`
  - `skills/usability-inspection/scripts/criterion_checks.py`
  - `docs/plans/2026-09-25_194200_usability-evaluation-skill_05j_wcag-machine-browser-observation-contract.md`
  - focused tests and `tests/skills/fixtures/usability-canonical/`
  - `docs/reports/2026-10-02-pr14-validation-progress.md`

## 5. 変更方針

- 変更方針:
  1. 現行のPlaywright実行環境、version/API、fixed dispatchとschemaを確認し、synthetic fixtureで問題を再現する。
  2. Locator/ARIA snapshotで正確に取れるrole/nameやopen-shadow対象だけを既存結果へ結合し、snapshot全体・任意画面テキストは保存しない。
  3. 可視性用途を分け、opacity 0を理由に一般観測母集団から除外しない。AX tree包含は実際のアクセシビリティ情報から記録する。
  4. DOM候補数依存を除き、実Tab遷移を記録する。循環、cap到達、操作失敗、cleanupを個別に扱う。
  5. formal titleを通常title契約と整合させ、最小限のPlan・Skill・README記述を更新する。
  6. 対象の決定論的規約（refs、security、CAS、sampling、WCAG procedures、EARL等）は既存所有者のまま維持する。
  7. targeted browser/integration tests後に標準検証を実行し、reportとPR本文を更新してcommit/push/CI確認する。
- 実行タスク:
  - [x] 現行Playwright API・関連probe経路・標準検証commandを確認。以前のprobe実装はcurrent HEADのdiffで確認し、実ブラウザではfixtureを使って修正後挙動を確認した。修正前の固定probe一式をブラウザで再実行する前後比較は行っていないため、source-levelの原因確認と修正後の実ブラウザ結果を区別して記録する。
  - [x] 原因を確認したprobe・文書・fixture・テストだけを変更。新しい依存関係、ARIA計算、Shadow DOM crawler、browser frameworkは追加していない。
  - [x] 実Chromiumで固定probe結果を確認し、formal production normalizerを経由させた。57 focused contract testではなく、該当5 suite計67件がPASSした。
- [x] repository標準検証: official `skills-ref` 22 packages、semantic dataset 22 Skills / 155 cases、shared deterministic 12、repository deterministic 257、shared semantic 27 PASS / 2 Windows symlink SKIP、repository semantic 4、trigger contract 1、runtime 271、Python compile 17 roots、Node syntax 2 files、Prettier 12 files、changed Markdown lint 6 files / 0 issue、text lint 6 files、`git diff --check`がPASS。`npm run validate:skills`はignored local overlayの`AGENTS.md`が参照する未存在`docs/reference/run-artifacts.md`で失敗した。overlayは変更しない。
- [x] 対象19 tracked pathsを明示stageし、通常commit `053f70094a5ed0cf13186e599d7a8c46d290c580`を作成。pre-commit hook内のskills-ref、semantic dataset、shared/repository deterministic、semantic、trigger、runtime validationがPASS。
- [x] report-only commit `3bb1806922271ab31334473d36bc9717870b6097`を作成し、対象PR branchへ通常push。PR head `3bb1806922271ab31334473d36bc9717870b6097`のAgent Skills / Deterministic Output Evals / Semantic Output Evals CIがsuccess。
- [x] PR本文を今回の変更、検証範囲、PR #17との責務分担、外部受入境界へ更新。更新時head `3bb1806922271ab31334473d36bc9717870b6097`の3 Actions successも確認済み。
- [x] report / Planのみを更新する最終checkpointを作成し、同じ実装commit `053f70094a5ed0cf13186e599d7a8c46d290c580`を維持。次の通常push後はreport-onlyの最新head CIを再確認し、そのSHA / run結果をPR本文と最終報告へ反映する。

## 10. 実装・ツール選択の記録

- Playwright MCPの現行Chromiumで`Locator.ariaSnapshotJSON()`、`Locator.isVisible()`、`Locator.isEnabled()`、`Locator.boundingBox()`と`page.keyboard`が利用できることを実行確認した。公式資料は[Locator API](https://playwright.dev/docs/api/class-locator)、[actionability / visibility](https://playwright.dev/docs/actionability)、[accessibility testing](https://playwright.dev/docs/accessibility-testing)。`ariaSnapshotJSON()`はPlaywright 1.63以降のAPIだが、repositoryはPlaywright packageを直接pinしておらず、MCPのPlaywright package semverは公開されていない。active browser ownerでAPIの実動作を確認し、APIがない実行経路はfixed probeの非成功として扱う。
- `package.json`と`pnpm-lock.yaml`に`@axe-core/playwright` / `axe-core`の導入はない。Dequeの現在のrule tableではACT 2779a5、97a4e1、23a2a8に対応するaxe ruleがある。一方、このformal pathはaxe verdictだけでなく、型付きrequest、current document identity、target/evidence refs、immutable observation resultを既存normalizer・CAS/handoff・procedureへ渡す必要がある。rule verdictを同等のtyped observationへ変換する契約を確認できなかったため、axe-coreへの置換・追加は行わない。参照: [axe-core ACT rule mapping](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)、[axe-core ACT conformance test convention](https://github.com/dequelabs/axe-core/blob/develop/test/act-rules/README.md)。
- 固有の決定論的責務（target/evidence refs、typed request/currentness、schema validation、procedure/applicability、cleanup、CAS、sampling、EARL）は既存所有者のままとした。

## 6. 検証方法

- 検証計画: 実Chromiumでsubmit/image inputs、ARIA naming、opacity/display/visibility/aria-hidden、open nested shadow roots、Tab traversal/cap/restore、HTML/SVG/multiple/non-text title casesを確認する。Production fixed-probe outputを`observation_contract.py`、`inspection_runtime.py`、該当procedure consumerへ通す。focused deterministic testsの後、skills-ref、semantic dataset、shared/repository deterministic、shared/repository semantic、trigger contract、runtime、compile、Node syntax、format/Markdown lint、`git diff --check`をCI定義に沿って実行する。
- 成功判定: 未確認をcompleteに昇格しない。runner/environment failureは製品PASSと区別する。latest pushed PR headの`Validate Agent Skills`、`Validate Deterministic Output Evals`、`Validate Semantic Output Evals`を再取得して確認する。

## 7. リスクと未解決論点

- リスク: Playwrightはopen Shadow DOMを探索できるがclosed rootsは対象外。ARIA snapshotは役割・名前・tree inclusionに関する情報を提供するが、生snapshotを保存すると個人情報を含み得る。locatorと既存finite target_refの確実な対応付けができない場合は、母集団をcompleteとして返せない。
- 未解決の質問: 実ブラウザと現行schemaの検証で明らかになった取得不能範囲だけをundeterminedとして記録する。

## 8. 成果物

- 変更ファイル: 調査で不整合が確認された既存実装、テスト、fixture、README/Skill/reference/Plan、progress report、および本計画。
- 付随ドキュメント: 今回の調査結果と対応範囲を追記したPR #14 validation report。

## 9. 備考

- 既存のuntracked user file、`.gitignore`、ignored overlay、過去Run Artifactを変更しない。active Runへの追記は続行記録として行う。semantic/trigger/holdout等の全量再評価は行わない。mergeは行わない。

## 11. 追加レビュー指摘の統合確認（2026-10-09）

### 目的

- 複数モデルのレビュー所見を確認済み不具合と決めつけず、現行コード、固定schema、WCAG procedure、実ブラウザ結果に照らして分類する。
- 実際に誤った結果または契約不一致が成立した範囲だけを既存処理へ最小限修正し、回帰テストと検証記録を揃える。

### 対象と判定順

1. 各fixed probeの母集団、明示サンプル、診断上限、結果完全性を分け、上限超過が「完全な証拠」として扱われる場合だけ部分観測へ修正する。
2. ARIA候補集合はprocedureごとの対象を確認し、`switch` / `tab` / `menuitem`等の漏れが当該probeの対象欠落を生む場合だけ、そのprobeに追加する。
3. media要素の存在と視認性を分離し、非表示mediaがprocedure対象から落ちる経路だけを修正する。
4. open Shadow Root直下の兄弟順位を含む既存path builderを確認し、同一観測内のtarget ref衝突を再現した場合だけ修正する。
5. ページ群・動作対象が未確定のpartial候補に任意のaccessible name本文が保存されるか確認し、識別・評価に不要な本文だけを除く。
6. `mp-audio-autoplay-run`の`incomplete`結果をproduction normalizer/runtimeへ通し、既存のpartial reason契約を欠く場合だけ既存enumへ有限理由を追加する。
7. Text Spacingの注入範囲と観測対象rootを実ブラウザで比較し、open Shadow DOMへCSSが届かず成功扱いされる場合だけ、対象rootに限定した注入・cleanupを行う。
8. `close_report()`、runtime caller、step applicability、sample/criterion closureを確認し、不正な必須step・未完了評価をcompleteと返す再現時だけ既存入力契約を強制する。

### 変更制約

- 既存Playwright Locator、ブラウザ標準API、finite probe schema、completeness contract、validator、runtime、procedure ownerを優先する。
- 新しい依存、汎用crawler/parser/ID管理/state framework、probe横断の一律処理は追加しない。
- 個々のprobeでcomplete populationが契約でない場合、上限の存在だけを理由に`incomplete`へ変更しない。
- Semantic 83、Trigger 180、Holdout 24、full WCAG fixture closureは今回実施しない。
- `3b77866a0b52347ce6201959f97492f197a61365`、`.gitignore`、ignored overlay、既存Run artifactsを変更・削除しない。mergeしない。

### 検証と完了

- 修正前の契約違反を、既存synthetic fixtureまたはfocused runtime callで再現する。再現不能はコード上の根拠と限界を分けて記録する。
- 変更したprobeはPlaywright Chromiumで値を確認し、production normalizer/runtimeおよび該当procedureまで通す。
- focused testsの後、official skills-ref、semantic dataset、shared/repository deterministic、runtime、shared/repository semantic、trigger contract、Python compile、Node syntax、format/lint、`git diff --check`を実行する。
- 修正対象の各項目に、`修正`または`修正不要`の根拠、回帰テスト、残る制約を記録する。
- normal commit/pushと最新PR headの3 CI successを目指す。G10等のpolicy gateがGit操作を拒否した場合、迂回せず、実装・検証成果を保持して正確に報告する。

## 12. 2026-10-09 — 複数モデルレビュー8指摘の最終突合

### 開始状態の訂正

この作業再開時に再取得した値は以下。上記「初期Evidence」にある`ebee...`のbaselineおよび「Git status再取得を実行しない」という記述は前タスクの記録であり、この追記が今回の正本となる。過去記録は履歴として保持する。

- branch `feat/usability-evaluation-skill`、local HEAD / `origin/feat/usability-evaluation-skill` / PR #14 head `3018f5beb94df17a2367ba9387f60333d234038c`。
- `origin/main=dec3f7c764db2869dc24eb3d6f154712a6677068`、ahead 327 / behind 0。
- Git statusを再取得し、stagedなし、今回のtracked変更11 file、追加fixture 1 fileを確認。既存の未追跡`3b77866a0b52347ce6201959f97492f197a61365`と`.pr14-formal-probe-1791501932895.json`は保持し、今回のstage対象から除外する。`.gitignore`、ignored overlay、既存Run Artifactも変更しない。
- PRはopen / mergeable、baseは`main`。開始時headの3 CIはsuccess。Git config変更やhook回避は行わない。

### 各指摘の再判定・対応

| 指摘 | 実コードでの確認 | 対応と根拠 | 実行証拠 |
|---|---|---|---|
| 件数上限による母集団欠落 | 200 / 500 / 100件の`slice()`が母集団全体のように`ok`を返す経路があった。moving/updating候補は`aria-live`とanimation探索の重複もあった。 | 評価対象全件を必要とするprobeだけ、total/returned countを分け、上限超過を既存partial completeness契約の`incomplete` + `probe-result-limit-reached`へ変更。moving candidateは同一DOM要素を`Set`で重複排除。computed-colorは既存`rendered_text_owner_count`を再利用し、sample数と全件性を明示。 | 実Chromium: moving 199/200は`ok`、201件は200返却で`incomplete`; neighbor 499/500は`ok`、501は500返却で`incomplete`; text presentation 499/500/501; computed color 500/501; reflow 199/200/201; text spacing 99/100/101を実行。各境界の件数と状態を確認。 |
| ARIA component探索漏れ | 候補selectorに`switch`、`tab`、`menuitem`等のwidget roleが不足し、visibilityだけで対象を絞る経路があった。 | 固定probeの有限selectorへ対象roleを追加。component/form inventoryはPlaywright-visibleまたは実際のAX tree inclusionを使い、role/name計算器は追加しない。procedureごとの対象集合を保ち、geometry selectorにも必要なwidgetを追加。 | 実Chromiumのcomponent 53件、form 51件、purpose 53件でswitch/tab/menuitem/checkbox/radio等を確認。target refsは各集合内で一意。component結果をproduction normalizer/runtimeへ通し、HMAC currentness一致、`ready/supported`、issues 0を確認。 |
| 非表示media | `allVisible("audio,video")`が画面表示状態を要件としないmediaを落としていた。 | media存在列挙を可視性から分離し、`located("audio,video")`でDOM/open Shadow DOM内の対象を保持。autoplay属性は実再生と同一視せず、開始時刻を観測していないrunは部分結果とする。 | 実Chromiumでvisible/hidden混在の4 mediaを取得し、hidden 3件を含むことを確認。audio runは`incomplete / media-playback-origin-not-instrumented`、候補4件。ページ読込後の一時点から過去の自動再生を推定しない。 |
| Shadow DOM target ref衝突 | ShadowRoot直下では`parentElement=null`により兄弟集合が自己のみとなり、同tag siblingの順位が衝突し得た。 | 既存path builderでShadowRootの`children`を兄弟順位に使用し、`::shadow`とhost境界を保持。新しいID frameworkは追加しない。 | 実Chromiumで同一host内の同tag兄弟、別host、nested open roots、通常DOMを観測しref一意を確認。focus sequence内の重複も既存fixtureで確認。 |
| partial結果のaccessible name本文 | page-set/actionが確定していない3 probeが、任意ARIA nameを`candidate_targets`等へ保存していた。既存redaction regexでは任意値を守れない。 | 3つのpartial summaryでは本文を返さず`accessible_name_present`だけを保持。normalizerにも同一有限probeの契約を追加し、partial rowsに`accessible_name`があれば拒否。別probeの評価に必要なname本文は一律削除しない。 | 架空の任意形式文字列をARIA labelへ設定。production result、normalized/runtime payload、handoff可能なpartial outputに本文がなく、name-presenceが保持されることを実Chromiumとruntime testsで確認。 |
| audio `incomplete`とnormalizer | audio probeの一部partial結果に`observation_completeness`理由がなく、normalizerのfinite contractと不一致だった。 | 既存partial enumに`media-playback-origin-not-instrumented`を追加。取得済み有限情報は残し、実行していない再生開始観測を成功へ昇格しない。 | media候補ありのproduction probe resultをnormalizer/runtimeへ通すfocused tests PASS。候補なしでも過去再生有無を断言しない契約をPlanへ明記。 |
| Text SpacingのShadow DOM適用漏れ | documentへの`addStyleTag()`だけではopen Shadow Root内のcomputed styleを変更できない一方、Locatorでその対象を観測できる。 | 既存固定CSSをLocatorで発見したopen Shadow Rootへ限定適用し、実際の値を検証。適用不一致はpartial、marker/handle cleanup不明または失敗はblocked。closed root / scope外frameは対象外。 | 実Chromiumで4 open rootsを含むfixtureの適用不一致0、cleanup `restored`を確認。99/100 clipped targetは`ok`、101件では100返却の`incomplete`; 全caseでcleanup restored。 |
| `close_report()`完了条件 | 修正前に全15 stepを`not-applicable`、空sample results / coverage、全accessible checks trueで`complete`となることを再現。必須step結果とStep 4.2のcriterion results不足を閉じていなかった。 | `required_steps`を空でない一意なknown step集合として検証し、全required outcomeを`complete`に限定。Step 4.2がrequiredならcriterion-plan由来のexpected ref集合を要求し、欠落/余分/重複、`undetermined`またはstale/unknown resultをblockedにする。適法なN/Aはrequired外で維持。runtime callerは既存close-report経路を利用。 | `wcag_em_structure` direct testおよび実`wcag_runtime.handler`経由で偽の全N/A closureが`blocked`、current resultと許可N/Aの正常caseが`complete`。missing result、stale、undeterminedもblocked。 |

### 検証記録

- Production fixed probeを既存Playwright Chromium 154.0.8037.95で実行。使用したAPIはrepository既存のPlaywright Locatorとブラウザ標準API。fixture server/browserは再利用し、新依存、runner、generic crawler、role/name engineは追加していない。
- focused suites: canonical fixture 17、inspection contract 17、inspection runtime 14、WCAG formal 11、report closure 16、WCAG runtime 12。合計87 tests PASS。
- repository gates: official `skills-ref validate` 22/22; semantic dataset 22 Skill / 155 cases; shared deterministic 12; repository deterministic 265; shared semantic 27 PASS / Windows symlink permission 2 SKIP; repository semantic 4; trigger contract 1; runtime 271; Python compile 39 roots; changed JS Node syntax PASS.
- 変更ファイルPrettier、対象Markdown lint、text quality、`git diff --check`の最終実行をcommit前に行う。`npm run validate:skills`がignored overlayだけを理由に失敗する既知ケースは別記し、overlayは変更しない。
- Semantic Judge 83、Trigger 180、Holdout 24、full fixture WCAG closureは今回の契約外で、実施しない。PR #17への全量Semantic移管とnative Trigger全量継続評価の境界を維持する。

### 残作業

- 検証結果をprogress reportへ追記し、明示的に対象tracked filesのみをstageする。
- 通常commit/push、PR本文追記、最終head取得を行い、最終headで3 CI successを確認してからSHAとworking treeを本節へ追記する。
- Mergeは行わない。

### 初期Evidence（修復前）

- GitHubの現行PR情報ではhead `3018f5beb94df17a2367ba9387f60333d234038c`、base `main` (`dec3f7c764db2869dc24eb3d6f154712a6677068`)、PR open / mergeable、inline review threads 0件。headの3 CIはsuccess。
- Local `.git/refs/heads/feat/usability-evaluation-skill` とorigin remote-tracking refは`3018f5beb94df17a2367ba9387f60333d234038c`、`origin/main`は`dec3f7c764db2869dc24eb3d6f154712a6677068`。前回Run最終記録ではworking tree cleanで、未追跡user fileを保持。現環境のGitはrepository ownership checkで停止し、コマンド単位の`safe.directory`設定もG10に拒否されたため、現時点ではGit status/stage再取得と後続Git mutationを実行しない。
- Focused baseline suitesはcanonical fixture 14、inspection contract 17、inspection runtime 13、WCAG formal 11、report closure 13件がPASS。
- 直接再現: `close_report(required_steps=REPORT_STEPS, step_outcomes={全step:not-applicable}, sample_results=[], example_coverage={}, accessible_output_closure={全check:true})` が`status=complete`を返した。必須step不適用と空の評価結果を完了へ通す疑義は実際に成立。
- Python Launcher `py -3.11`に登録Pythonがなく、workspace外実行はsandbox拒否。既存Python 3.11実行ファイルを検証commandで使うにはsandbox escalationが許可された。repositoryには絶対pathを追加しない。

## 2026-10-09 JST — 最終実ブラウザ・標準検証

- Final baseline before commit: `ebee4278060a4423c3d11d5afbe99ab94cc2cc38`; local `origin/feat/usability-evaluation-skill` is the same; `origin/main=dec3f7c764db2869dc24eb3d6f154712a6677068`; ahead 323 / behind 0. No files are staged. User-owned untracked hash file remains untouched.
- Targeted browser inspection used repository fixed probe files in the existing Playwright Chromium session (Chromium 154.0.8037.95). `Locator.ariaSnapshotJSON`, `getByRole`, `isVisible`, `isEnabled`, `boundingBox`, and `page.keyboard` were exercised. The browser MCP does not expose its exact Playwright library semver; `ariaSnapshotJSON` requires Playwright 1.63 or newer. No dependency was added.
- Actual fixed formal `mp-component-semantics` and `mp-document-title` results were normalized through the current production observation/runtime path and consumed by the ACT procedure helper. Both returned `status=ok`, current HMAC identity matched, and no raw fixture secret was present. The component fixture deliberately includes an empty-name button, so the ACT helper returned the expected `failed`; the title fixture returned `passed`. This synthetic result is probe-path evidence, not a claim about external product conformance.
- Integration surfaced one real default-value mismatch: a DOM `input` without a `type` attribute has browser `HTMLInputElement.type === "text"`, while `getAttribute("type")` is null. The fixed probe now reads the standard property so ACT applicability is evaluated instead of being left as missing evidence. A regression test asserts that behavior.
- Browser checks also confirmed: submit/image input implicit button role; browser-computed names for `aria-label` and `aria-labelledby`; `aria-hidden` exclusion; empty name distinct from a missing result; opacity-zero and aria-hidden elements remain Playwright-visible, whereas `display:none` / `visibility:hidden` do not; enabled state is separate; open nested Shadow DOM locators produce distinct refs; focus cycle/limit/deleted target are distinct and cleanup is checked; title handling ignores SVG-only title, checks the first HTML title and all child nodes, and does not treat XML as HTML.
- `tests/skills/evals/deterministic/test_canonical_usability_fixture.py`: 14 PASS. Full repository deterministic suite: 257 PASS. Shared deterministic: 12 PASS. Runtime: 271 PASS. Shared semantic: 27 PASS / 2 Windows symlink-privilege SKIP. Repository semantic: 4 PASS. Trigger dataset contract: 1 PASS. Semantic dataset validator: 22 Skills / 155 cases. Official `skills-ref validate`: 22/22 PASS. Python compile: 17 current roots. Node syntax: both changed fixed probe scripts PASS. Prettier: all changed files with configured parsers PASS; the `.xml` fixture is not supported by this Prettier configuration and was validated by browser execution instead. Changed-file Markdownlint: 6 files / 0 issues. Text quality: 6 changed Markdown files PASS. `git diff --check`: PASS.
- `npm run validate:skills` could not complete in this workspace because the ignored local `AGENTS.md` overlay links to absent `docs/reference/run-artifacts.md`. The overlay and referenced repository files were not changed. The independent official `skills-ref`, dataset and CI-equivalent tests above passed.
- Axe-core comparison: repository package manifests contain no `axe-core` / `@axe-core/playwright`. Its ACT rule mapping can produce rule verdicts, but it does not supply this repository's typed per-request observation, current HMAC identity, target/evidence refs, immutable result and normalizer/handoff contract. No dependency or replacement was added. References: [axe-core rule descriptions](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md), [ACT rule test convention](https://github.com/dequelabs/axe-core/blob/develop/test/act-rules/README.md).
- The temporary probe JSON and user-owned untracked file remain untracked and are excluded from the PR changes. `.gitignore`, ignored overlay, existing Run Artifacts, Skill description/routing and PR #17 evaluation ownership were not changed. The existing `.codex/runs/` directory is read-only to this task; this tracked plan/report retains the checkpoint.
- Remaining: explicit-path normal commit and normal push, PR body update, then all three Actions on the latest PR head. Full Semantic 83, Trigger 180, Holdout 24, and full fixture WCAG closure remain intentionally out of scope per the PR #14 / PR #17 split.
