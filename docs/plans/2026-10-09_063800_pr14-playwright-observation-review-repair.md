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
- [ ] 通常push、PR本文更新、push後の最新PR head CI、最終Plan突合。

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

- 既存のuntracked user file、`.gitignore`、ignored overlay、保存済みRun Artifactを変更しない。semantic/trigger/holdout等の全量再評価は行わない。mergeは行わない。

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
