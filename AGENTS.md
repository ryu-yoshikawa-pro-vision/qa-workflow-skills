# Repository Agent Working Agreement

このrepositoryで作業するAgentは、ユーザーの明示指示と作業範囲を優先し、関連する正本の契約に従います。

## 常時必要な契約

- ユーザーの明示指示を最優先します。Plan-only、review-only、investigation-onlyの依頼では実装やGit mutationへ進みません。
- 変更前に関連するIssue、PR、Plan、code、test、CIを必要な範囲で確認します。Plan本文のscope、実装順序、検証、blocked条件、完了条件を正本とし、重要な制約を独自判断で変えません。
- QA Skillの仕様はREADME.md、EVALS.md、対象skills/<name>/SKILL.mdを正本として扱います。
- 新しい抽象化を加える前に、既存runtime、validator、helper、標準機能を確認します。
- default branchへの直接commit / push、force push、branch削除、merge、releaseは、ユーザーの明示指示なしに行いません。protected branchから作業する場合は、Plan所定のliteral canonical root形式で、現在のHEADから新しい非protected branchへ移るgit switch -c <branch>、または既存local非protected branchへ移るgit switch <branch>だけを使います。追加option、別start-point、破棄操作は使わず、execpolicyの承認を必要とします。
- file delete、rename、moveは、ユーザーが明示した対象範囲だけで行います。
- formatter、lint、関連test、CI契約を完了前に確認します。完了判定に使う独立validationは個別に実行・判定し、複数commandをまとめたaggregate exit codeだけでPASSにしません。
- Codex CLIは特定versionへ固定せず、利用中のversionを記録します。実runtimeの受入ではversion一致ではなく、対象tool modeでrepository-owned `PreToolUse` / execpolicyが機能することを確認します。Direct modeではdirect `exec_command`、Code Mode / CodeModeOnlyではnested `tools.exec_command()`を対象にします。required safety capabilityを確認できない範囲は未検証とし、Hook、execpolicy、sandbox、protected branch保護の拒否を維持して拒否を迂回しません。state-changing Gitは、ユーザーが明示した作業範囲とPlanが許可する場合だけ実行します。commandはcanonical repository rootへの移動とdirectなGit commandを同一command内に含めるPlan所定の形式を使います。
- PR #18の`chore/formatter-lint` branchでは、今回の明示依頼に基づき、改訂Main Planの検証・差分確認を満たした後、選択した対象ファイルのstage、commit、同branchへの通常pushを許可します。この例外はPR #18だけに適用し、他のbranchや作業へ広げません。`git add -A`、force push、merge、branch削除、権限拒否の迂回は禁止です。
- runtime受入はcodex --no-daemon --strict-configのembedded / non-shared runtimeに限ります。managed/shared app-serverを検証済み扱いしません。
- Codexのdisconnect / reconnect、recovered queue、別session由来と疑われるapprovalやoutputが出た場合は承認せず、新しいfresh sessionで作業状態を再確認します。
- root AGENTS.mdはCodex標準のcompact復元へ委ねます。独自SessionStart Hookや重複する指示再注入を追加しません。
- 人間向けのrepository文書は原則日本語で記述します。
- PR本文はレビューに必要な現在状態の要約として保ち、過去状態を追記して蓄積しません。本文だけにある重要な判断・検証根拠は、置換前に適切な既存Markdown文書へ保存し、本文は最新HEAD・CI・未達条件に置き換えます。

## 委譲と参照先

- Parent Agentはscope、検証、完了判定を保持します。custom subagentはParentが指定した役割・範囲に従い、別subagentを起動しません。
- Planの保存と完了契約はPLANS.md、review契約はCODE_REVIEW.md、Hookとexecpolicyの詳細はdocs/reference/codex-safety-harness.mdを参照します。
- QA workflow固有の詳細をこの文書へ複製しません。
