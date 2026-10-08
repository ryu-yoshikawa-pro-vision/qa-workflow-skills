# PR #14 / PR #17 評価責務分担の更新

## 0. 依頼概要

- 依頼内容: PR #14を3 Skill実装と代表経路の成立確認に限定し、反復可能な全量実Agent品質評価をPR #17へ移管する責務分担を、PR #14の既存Planへ反映する。
- 背景: PR #14の長時間全量評価を再開せず、現在の実装・deterministic検証・代表的な実Agent/browser証拠を使ってPR #14を完了可能な範囲に再定義する。
- 期待成果: Plan間の矛盾をなくし、PR #14に残る必須検証とPR #17へ移す評価を追跡可能にする。

## 1. ゴール / 完了条件

- ゴール: PR #14とPR #17の評価責務を明記し、現行PR #14 Planの完了条件を証拠に対応付ける。
- 完了条件（DoD）:
  - root Plan、`_06`、`_06a`、`_06b`、`_06c`が同じ責務分担を示す。
  - PR #14ではrepository標準 validation、current-head CI、各Skillの最低限の実Agent smoke、代表live inspection、代表formal handoff/report/EARL、fail-closed behavior、description変更対象のtrigger regressionを完了条件とする。
  - Semantic dataset validationと既存 deterministic / runtime契約はPR #14に残し、83 case全件の実Agent candidate + Judge反復評価はPR #17へ移す。
  - Triggerの全量・反復統計評価は別継続課題とし、PR #17の成果と扱わない。PR #14では変更した3 queryを各3回評価し、明確な隣接negative boundaryだけを追加する。
  - fixture全criterionのWCAG closureを要求せず、不足をcompleteへ昇格しないpartial-blocked（部分結果を保持しreport closureを`blocked`とする状態）、missing evidenceの明示、Step 5.3 guard、現存結果に対するEARL validator、代表handoffを検証する。
  - case-004 / case-012 semantic referenceの未stage変更を入力・catalogから導出可能か確認し、Judge通過だけを目的にした変更を残さない。
  - targeted Trigger、focused deterministic、repository標準 validation、`git diff --check`、current PR head CIを実行し、変更と証拠を記録して通常commit / pushする。
  - PR #14本文とtitleを実装・更新後Planに合わせる。merge、force push、PR closeはしない。

## 2. 現状理解と前提

- 現状理解:
  - branch `feat/usability-evaluation-skill`、HEAD / origin PR branch `585f7a540d354ca827ee24afc0d2e8efd85ab739`。
  - `origin/main` は `dec3f7c764db2869dc24eb3d6f154712a6677068`、ahead 314 / behind 0。
  - `.codex/config.toml` は `gpt-6-luna` を選択している。
  - PR #17はopen。現行PR本文は既存Eval InputからのAgent candidate生成、既存grader接続、Skill/all-Skill batch、repeat、Skill revision比較を扱い、native Skill trigger評価を対象外としている。
  - PR #14作業treeには、validation report、2つのSkill description、2件のsemantic referenceに既存のunstaged変更がある。ユーザー所有のuntracked hash fileは対象外。
- 前提:
  - PR #17の現行scopeは継続評価の受け皿として参照し、実装済み機能とは表現しない。
  - `EVALS.md` の評価方法とtrigger thresholdは変更しない。
  - 既存browser/runtime/helper/fixtureが不変の経路は、その不変hashと限定された証拠範囲を記録して再利用できる。
- 対象外:
  - Semantic 83件の全量実Agent評価、Trigger 60×3全量、Holdout 8×3、全criterionを埋めるfixture WCAG evaluation。
  - 新機能、評価runner/frameworkの追加、全canonical browser組合せの反復。

## 3. 質問 / 曖昧性

- 必ず質問する不透明点: なし。PR #17の現行scopeとPR #14の実装状態から責務分担を確定できる。
- 仮定してよい細部: 対象Skillごとに評価する近接negativeは、変更したdescriptionが誤発火を誘発し得る既存queryが見つかった場合だけ含める。
- 未回答の重要質問: なし。

## 4. 影響範囲

- 影響範囲: PR #14 Plan、検証進捗記録、3 Skill descriptionが必要な場合、semantic reference監査、targeted trigger regression、repository検証、PR #14 metadata。
- 確認対象ファイル:
  - `docs/plans/2026-09-25_194200_usability-evaluation-skill.md`
  - `docs/plans/2026-09-25_194200_usability-evaluation-skill_06_evaluation-ci-implementation-order.md`
  - `docs/plans/2026-09-25_194200_usability-evaluation-skill_06a_usability-inspection-implementation-order.md`
  - `docs/plans/2026-09-25_194200_usability-evaluation-skill_06b_wcag-conformance-evaluation-implementation-order.md`
  - `docs/plans/2026-09-25_194200_usability-evaluation-skill_06c_canonical-live-validation.md`
  - `EVALS.md`
  - `docs/reports/2026-10-02-pr14-validation-progress.md`
  - `.codex/runs/20260928-234151-JST/REPORT.md`

## 5. 変更方針

- 変更方針:
  - 新しい短い責務分担Planを保存し、指定されたPR #14 Plan各文書の完了条件を整合させる。
  - `_06c` の細かな deterministic permutation はdeterministic test ownerとし、real browserは代表経路を通す。formal report不足はpartial-blocked（report closure `blocked`）のまま保持する。
  - `EVALS.md` の全repository評価契約は維持し、PR #14に必要なsubset gateのみ各Planへ明示する。
  - semantic reference差分はinput / source catalog事実との対応を確認し、期待候補を漏らさないことを確認する。
- 実行タスク:
  - [x] PR #17 scope、current git state、既存PR #14 evidenceを照合する。
  - [x] case-004 / case-012 reference差分を評価契約とinput/catalogから分類する。
  - [x] root Plan、`_06`、`_06a`、`_06b`、`_06c`の責務分担・gateを更新する。
  - [x] targeted Trigger 3 query各3回、および明確なnegative boundary、最低限のAgent smokeを取得する。
  - [x] focused deterministicとrepository標準 validationを実行し、reportを追記する。
  - [ ] PR title/bodyを更新し、明示pathのみcommit / 通常pushし、最新head CIを確認する。

## 6. 検証方法

- 検証計画:
  - Plan内で全量ゲートがPR #14の必須条件として残っていないことを横断検索する。
  - `EVALS.md`のSkill-read event、独立query実行、3回、`>0.5` / `<0.5` thresholdを使って対象triggerを評価する。
  - relevant focused deterministic tests、official `skills-ref validate`、compile、semantic dataset validator、shared/repository deterministic・semantic、trigger contract、runtime tests、`git diff --check`を実行する。
  - push後に最新PR headの3 GitHub Actionsを確認する。
- 成功判定:
  - targeted triggerで各positive `trigger_rate > 0.5`、追加したnegative boundaryは`trigger_rate < 0.5`、runner failure 0、Skill-read event証拠あり。
  - repository標準検証とcurrent-head CIがPASS。
  - 更新後Planの各PR #14必須条件に代表証拠または標準検証の証拠ownerがある。

## 7. リスクと未解決論点

- リスク: 既存canonical evidenceは旧tree fingerprintを持つ。runtime/helper/fixture hashが一致する範囲に限って代表証拠として再利用し、current final tree全ゲートPASSとは表現しない。
- 未解決の質問: なし。

## 8. 成果物

- 変更ファイル: root Plan、`_06` / `_06a` / `_06b` / `_06c`、progress report、必要なSkill / reference、PR metadata。
- 付随ドキュメント: 本責務分担Plan、active Run report。

## 9. 備考

- external product / account / URL / production data / assistive technology acceptanceはPR #14 repository fixture gateから分離する。
- native trigger全量・反復評価は別の継続評価課題であり、PR #17へ移管したとは記録しない。
