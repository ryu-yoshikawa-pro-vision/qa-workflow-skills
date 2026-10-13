# Execpolicy rules

The two files in this directory are the repository's Codex 0.160.0 command approval policy. The companion plan at docs/plans/2026-10-03_173600_formatter-lint_execpolicy-rules.md is the exact source for each prefix, decision, justification, match, and not_match example.

Risky Git and GitHub CLI command families require user approval. The small set of direct deletion and unsupported command families is forbidden. Read-only commands use the ordinary sandbox; there are no allow rules.

These rules do not parse complete shell scripts or all future CLI options. The PreToolUse hook blocks the unsupported command forms defined in the main plan. Runtime acceptance must verify full shell commands; an argv-only execpolicy check is not sufficient evidence.
