# 評価入力：非E2E testwareの独立assertionレビュー

## 有効な仕様Authority

- 権限viewerによる設定更新APIは403を返し、保存済み設定を変更しない。
- editorで有効な設定を更新すると200と更新された設定内容を返し、永続化される。

## 元TC

TC-API-004、revision `tc-r4`：viewerの更新拒否について、HTTP 403と設定値が変わらないことを確認する。

## 非E2E testware

`tests/api/setting.test.ts`、revision `test-r2`。fixture `viewer` と既存保存状態は実装側が作成したもの。

```ts
it("viewer cannot update", async () => {
  const response = await api.updateSetting("viewer", "changed");
  expect(response.status).toBe(200);
  expect(true).toBe(true);
});
```

runnerのraw結果はPASS。上記testwareに対し、実装者の説明やraw PASSを根拠にせず、TCと仕様Authorityから独立レビューを実施する。
