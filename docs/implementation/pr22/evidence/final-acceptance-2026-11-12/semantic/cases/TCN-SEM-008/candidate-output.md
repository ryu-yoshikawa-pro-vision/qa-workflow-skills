# テスト観点・条件 / カバレッジ項目 出力

## 観点範囲

- 対象テスト要求: 分類木factor（browser / os / auth）の組合せカバレッジ（全factor pairwise、subset `{browser, os, auth}` の3-wise）
- テストレベル: 未指定
- 対象外: なし
- 仮定 / 未解決事項: 下記「ブロック中」を参照

## 状態

ブロック中。Classification Tree adapterから既存combinatorial child `comb-008` へ展開する正式なruntime結果は作成していません。カバレッジ項目、TCN、Machine Entityは確定していません。

## テスト条件へ展開しないテスト要求

| テスト要求ID | 扱い       | 理由 / 根拠                                                              |
| ------------ | ---------- | ------------------------------------------------------------------------ |
| 未指定       | ブロック中 | 入力にテスト要求IDと、この組合せ検証が対応するテストレベルがありません。 |

## テスト観点・条件一覧

該当なし（ブロック中のため確定したTCNはありません）。

## カバレッジ項目一覧

該当なし（child runtimeを実行していないため、確定したカバレッジ項目はありません）。

## カバレッジ候補の扱い

| 候補                                                        | 導出元                 | 扱い       | 理由 / 根拠                                                                                                                   | カバー先 |
| ----------------------------------------------------------- | ---------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------- | -------- |
| Firefox + macOS + SAML                                      | SPEC-CTD-008           | 成立不能   | Authority `SPEC-CTD-008` により成立しないと入力で指定されています。制約として保持し、実行可能なカバレッジ項目には含めません。 | なし     |
| 全factor pairwise（16ペア）                                 | 入力の factor 値       | ブロック中 | 16ペアはいずれも制約を単独では満たさないことを手計算で確認しました。ただし、child runtimeで確定した母集団ではありません。     | なし     |
| subset `{browser, os, auth}` の3-wise（制約適用後11 tuple） | 入力の factor 値と制約 | ブロック中 | 全直積12件から成立不能1件を除いた11件が母集団の見込みです。ただし、`coverage_selection_reason` が未提示のため採用できません。 | なし     |

## 任意: Pairwise / 組合せ

### 因子 / 値 / 制約

| 因子    | 値                    | 制約 / 備考                                      |
| ------- | --------------------- | ------------------------------------------------ |
| browser | Chrome, Firefox       | 入力に class key / classification key の指定なし |
| os      | Windows, Linux, macOS | 同上                                             |
| auth    | password, SAML        | 同上                                             |

- 制約: `Firefox + macOS + SAML` は成立不能（Authority `SPEC-CTD-008`）。
- 採用基準（入力の指定どおり）: 全factorに対するstrength 2、およびsubset `{browser, os, auth}` に対するstrength 3。

### 生成組合せ

該当なし（runtime child未実行のため）。

### 2-wiseカバレッジ確認

- 生成方法 / ツール: 未実行（`classification_tree.py` の child 入力を作れず、`combinatorial` runtime は未実行）
- 制約: `Firefox + macOS + SAML` を除外
- 成立可能なすべての値ペアをカバレッジ項目でカバー済みか: 未確認
- 確認根拠: 手計算では全16ペアが単独で成立可能であることのみ確認。カバレッジ項目は未生成。

## 統合候補

該当なし。

## Machine Runtime / Entity / Target mapping（機械証拠）

runtime結果、Machine Entity、target mappingは作成していません。`comb-008` のcurrent Machine Entity内容と fingerprint は入力に含まれていないため、既存childの再利用を検証できていません。

## 未解決事項（ブロック理由）

1. `coverage_selection_reason` が未提示です。subset の strength が 3 のため、`classification_tree.py` の `_validate_combinatorial_input` は理由文を必須としています。理由を推測して補いません。
2. Classification Tree の model key、classification key、class key（class と value の対応）、classes の authority_refs が未提示です。adapter は model key と class key を必要とします。
3. 既存child `comb-008` の current Machine Entity の内容と generation fingerprint が未提示です。入力の「確認済み」という記述だけでは、既存childの再利用を機械的に検証できません。
4. テスト要求ID、テストレベル、対応する期待挙動の根拠（authority）のうち SPEC-CTD-008 以外のものが未提示です。

上記1〜3が解消されるまで、child生成、カバレッジ項目、TCN、materializationを保留します。
