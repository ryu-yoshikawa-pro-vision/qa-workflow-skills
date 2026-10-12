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
- Codex 0.160.0 primary profileではfeatures.unified_exec = true、unified_exec_tty = falseを使います。POSIX positive smokeの失敗だけを理由にfallbackへ切り替えず、Plan所定の比較と再受入条件に従います。
- 原則としてstate-changing Gitは、Codex versionがcodex-cli 0.160.0と完全一致し、実際のtool modeに応じたrepository-owned Bash PreToolUseとexecpolicyのruntime受入がPASSした環境でのみ実行します。Direct modeではdirect exec_command、Code Mode / CodeModeOnlyではnested tools.exec_command()を確認します。未検証またはFAILのmodeでは実行しません。canonical repository rootへの移動とdirectなGit commandを同一command内に含めるPlan所定の形式を使います。
- ただし、PR #18の`chore/formatter-lint` branchでは、Main Planの中間checkpoint条件を満たす場合に限り、明示的に選んだPR対象ファイルのstage、中間commit、同branchへの通常pushを許可します。この例外は今回のPRのレビュー用中間成果物だけを対象とし、他のbranchや作業へ適用しません。必須runtime受入を省略したまま最終完了とする根拠にはしません。Plan変更の理由は、ローカルにPython 3.11および必要な対話runtime環境がなく、CIとGitHubレビューで検証を進めるためです。Hook、execpolicy、sandbox、通常の承認は引き続き有効であり、これらの拒否を迂回しません。
- runtime受入はcodex --no-daemon --strict-configのembedded / non-shared runtimeに限ります。managed/shared app-serverを検証済み扱いしません。
- Codexのdisconnect / reconnect、recovered queue、別session由来と疑われるapprovalやoutputが出た場合は承認せず、新しいfresh sessionで作業状態を再確認します。
- root AGENTS.mdはCodex標準のcompact復元へ委ねます。独自SessionStart Hookや重複する指示再注入を追加しません。
- 人間向けのrepository文書は原則日本語で記述します。

## 委譲と参照先

- Parent Agentはscope、検証、完了判定を保持します。custom subagentはParentが指定した役割・範囲に従い、別subagentを起動しません。
- Planの保存と完了契約はPLANS.md、review契約はCODE_REVIEW.md、Hookとexecpolicyの詳細はdocs/reference/codex-safety-harness.mdを参照します。
- QA workflow固有の詳細をこの文書へ複製しません。
