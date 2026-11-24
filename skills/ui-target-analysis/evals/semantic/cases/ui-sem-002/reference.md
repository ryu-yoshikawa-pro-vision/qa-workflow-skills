# 判定根拠

## Source of Truth

- Use the explicitly provided feature artifact ref/revision and `FEATURE-021` → `SCOPE-004` mapping. Do not infer a mapping from the feature name.
- Derive a fresh index from current `ui-target-v1` and its `inspect` snapshot. Include only the referenced scope's UI operation rows, their target structures, required parent structures, and the scope row. Use each exact file, section, line, and stable ID.
- Preserve package version `v12` and source revision `feature-r3`. Distinguish the `02` operation rows from the `01` structure rows and `00` scope row.
- Report no changed UI rows because none is stated. Do not persist a second feature index or invent a changed-ID list.
- After a materialize, derive the index again from the new package version, compare only the changed stable IDs and affected scopes, and leave unrelated scopes current.
