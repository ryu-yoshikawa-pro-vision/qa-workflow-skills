# FEATURE-021 UI導出索引

- feature artifact: `artifact://feature/checkout` / `feature-r3`
- UI package: `artifact://ui-target/checkout` / `ui-target-v1 v12`
- explicit mapping: `FEATURE-021` → `SCOPE-004`
- indexはcurrent `inspect` snapshotから導出しました。保存済みfeature indexは作成しません。

| stable ID | 種別 | 正本file | section | line | 関係 |
| --- | --- | --- | --- | ---: | --- |
| SCOPE-004 | scope | `00_scope_and_context.md` | 分析対象機能scope一覧 | 19 | 明示mapping |
| UIOP-012 | 操作 | `02_behavior_and_business_rules.md` | UI操作一覧 | 44 | SCOPE-004、PAGE-008 |
| UIOP-013 | 操作 | `02_behavior_and_business_rules.md` | UI操作一覧 | 51 | SCOPE-004、DIALOG-004 |
| NAV-002 | 親構造 | `01_ui_structure_and_navigation.md` | UI構造一覧 | 8 | PAGE-008の親 |
| PAGE-008 | 画面 | `01_ui_structure_and_navigation.md` | UI構造一覧 | 27 | UIOP-012の対象 |
| DIALOG-004 | dialog | `01_ui_structure_and_navigation.md` | UI構造一覧 | 36 | UIOP-013の対象 |

このrevisionではchanged UI rowはありません。materialize後は新versionから再導出し、変更stable IDと影響scopeだけ再確認します。提示されたlineはこのfixtureのcurrent package位置です。
