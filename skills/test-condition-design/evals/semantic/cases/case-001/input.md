# Eval Input
## Test Requirement
TR-001: 名称が1〜50文字の範囲でのみ保存され、保存後は一覧に新名称が表示されることを保証する。
TR-002: 編集状態draftから保存成功時savedへ遷移し、保存失敗時draftのままであることを保証する。

## Authority
- 名称1〜50文字。
- 空文字と51文字以上は保存不可。
- 保存成功時のみ一覧へ新名称を反映。
- 保存失敗時は変更を反映しない。

## 目的
Test Condition、技法、Coverage Criteria、Coverage Itemへ展開する。
