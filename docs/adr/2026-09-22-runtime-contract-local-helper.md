# ADR: Skill-local runtime contract helper

## 状態

Accepted

## Context

PR #11では、runtime unitの入力・結果・Machine Entity・fingerprint・freshnessを、Skill package単体のコピーでも検証可能にする必要がある。一方、技法固有generatorをrepository rootの共通module、別manifest、registryへ依存させると、Skill単体移植性と実装fingerprintの境界が崩れる。

## Decision

`spec-analysis`を含む7 Skillへ同一内容の`scripts/runtime_contract.py`を同梱する。共通helperはstrict JSON、canonicalization、exact value、fingerprint、Machine Entity、target post-process、expected runtime/entity builder、freshness、runtime evidence verifierだけを担当する。技法固有処理は同Skillのgenerator scriptに置き、generatorからimportできるSkill-local Python moduleは同じ`runtime_contract.py`だけとする。runtime dispatchはhelper内の固定dataとSkill instructionで閉じ、別manifest / registryは追加しない。

## Consequences

- Skill packageを単体コピーしてもruntime CLIと`verify_runtime_evidence`が動作する。
- helper変更は同Skillのruntime evidenceを安全側に広く再検証対象にできる。
- 技法間で共有したいロジックを新しい共通moduleへ逃がせないため、技法固有validatorは各generatorに保持する。
- 独立validatorはproduction helperをimportせず、保存blockとSkill-local sourceからfingerprintを再計算する。
