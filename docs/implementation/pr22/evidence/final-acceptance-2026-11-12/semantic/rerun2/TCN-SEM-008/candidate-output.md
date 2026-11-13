# テスト観点・条件 / カバレッジ項目 — TR-CTD-008（分類木・制約付き組合せ）

> 状態: **未完成（coverage未確定）**。分類木runtime・組合せruntimeを実行できなかったため、機械生成されたcoverage項目・組合せ行・Machine Entityは含みません。下記の母集団と基準は入力と制約から手作業で導出したものです。

## 観点範囲

- 対象テスト要求: `TR-CTD-008`
- テストレベル: システムテスト（入力どおり）
- 対象外: なし（入力に指定なし）
- 仮定 / 未解決事項:
  - Authority `SPEC-CTD-008` の本文は入力に含まれていない。入力の記述（制約 `Firefox + macOS + SAML` 成立不能、全factor pairwise + subset `{browser, os, auth}` の3-wise、採用理由）を根拠として使用した。
  - 分類木adapterのmodel keyは入力に記載がないため未採番。
  - 再利用対象の既存comb childは `comb-008` と入力にあるが、そのcurrent Machine Entity本体・fingerprintは入力に含まれず、本Skillでは照合できていない。入力の「確認済み」は申告として扱い、検証済みとはしない。
  - 関連プロダクトリスク、TR優先度は入力に無い。優先度は未提示として扱う（推定で埋めない）。
  - runtime未実行のため、TCN ID・CI IDは採番前のdraft。

## テスト要求の扱い

| テスト要求ID | 扱い                        | 理由 / 根拠                                                                                                                                                                                                                 |
| ------------ | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-CTD-008   | テスト条件へ展開（TCN-008） | 「browser・os・authの組合せを制約付きで確認すること」を、分類木 → 組合せ（pairwise＋3-wise）で展開。採用理由はSPEC-CTD-008の「設定依存の組合せ欠陥を、全factorはpairwise、subset {browser, os, auth} は3-wiseで確認する」。 |

## item × 共通condition候補の正式適用（formal_design入力）

- 入力に `formal_design` は無いため、本節は適用対象外。

## テスト観点・条件一覧

| 観点ID (draft) | テスト要求ID | テスト観点 / 条件                                                                                                           | カテゴリ | テスト技法 / 根拠                                                                           | カバレッジ基準                                                                                   | 関連仕様根拠 / プロダクトリスク             | 優先度                     | 備考                                                                                            |
| -------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------- | -------------------------- | ----------------------------------------------------------------------------------------------- |
| TCN-008        | TR-CTD-008   | browser（Chrome/Firefox）・os（Windows/Linux/macOS）・auth（password/SAML）の制約付き組合せが設定依存の欠陥を起こさないこと | 組合せ   | 分類木 → 組合せ（mixed-strength: global_strength=2、subset {auth, browser, os} strength=3） | CI01: 全factor pairwise（成立可能な全値ペア） / CI02: subset 3-wise（制約適用後の成立tuple全件） | SPEC-CTD-008 / 関連プロダクトリスク: 未提示 | 未提示（TR優先度を未確認） | 制約 `Firefox+macOS+SAML` は成立不能として除外。CI01とCI02は別criterionとして保持し統合しない。 |

## カバレッジ項目一覧

| カバレッジ項目ID (draft) | 観点ID  | カバレッジ項目                                                                                                            | 導出元の技法 / 基準                | 期待挙動の根拠                                                          | 優先度 | 備考                                                                                                         |
| ------------------------ | ------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ----------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------ |
| TCN-008-CI01             | TCN-008 | 全factor pairwise：成立可能な全値ペア16件を、少なくとも1つの生成行で覆う（browser×os 6件、browser×auth 4件、os×auth 6件） | 分類木 → 組合せ、global_strength=2 | SPEC-CTD-008（組合せ欠陥の確認）。個別の期待結果は本Skillでは定義しない | 未提示 | 全16ペアとも成立witnessあり（ペア単位の成立不能なし）。生成はruntime側。                                     |
| TCN-008-CI02             | TCN-008 | subset {browser, os, auth} 3-wise：制約適用後に成立するtuple 11件を、少なくとも1つの生成行で覆う                          | 分類木 → 組合せ、subset strength=3 | SPEC-CTD-008（subset 3-wiseで組合せ欠陥を確認）。個別の期待結果は未定義 | 未提示 | subsetが全3factorのため、このcriterionは制約適用後の全組合せと一致する。CI01の射影で満たされても統合しない。 |

## カバレッジ候補の扱い

| 候補                                                      | 導出元                          | 扱い       | 理由 / 根拠                                                                                                                              | カバー先 |
| --------------------------------------------------------- | ------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| browser=Firefox × os=macOS × auth=SAML（12組合せ中の1件） | 制約 `ff-macos-saml-infeasible` | 成立不能   | 入力がSPEC-CTD-008を根拠に成立不能と指定。3-wise criterionの母集団から除外する。                                                         | —        |
| 分類木adapter model key                                   | 入力                            | ブロック中 | 入力に未記載。adapterの採番・current Machine Entityを確認できないため、adapter経由のchild生成を保留。                                    | —        |
| 既存comb child `comb-008` の再利用                        | 入力                            | ブロック中 | 入力は「current Machine Entityで確認済み」と申告するが、Entity本体・fingerprintが無く照合できない。既存childの置換（新規採番）はしない。 | —        |

## 任意: Pairwise / 組合せ

### 因子 / 値 / 制約

| 因子    | 値                                  | 制約 / 備考                                                |
| ------- | ----------------------------------- | ---------------------------------------------------------- |
| browser | Chrome, Firefox                     |                                                            |
| os      | Windows, Linux, macOS               |                                                            |
| auth    | password, SAML                      |                                                            |
| 制約    | `Firefox + macOS + SAML` は成立不能 | SPEC-CTD-008（入力記述）。制約適用後の組合せ数 12 − 1 = 11 |

### 生成組合せ

生成行は未生成（組合せruntime未実行）。runtime結果が得られるまで、行ID・行番号・witnessは割り当てない。

### 要求tuple母集団（生成前・手作業導出）

CI02の母集団（制約適用後11件、browser / os / auth の順）:

1. Chrome / Windows / password
2. Chrome / Windows / SAML
3. Chrome / Linux / password
4. Chrome / Linux / SAML
5. Chrome / macOS / password
6. Chrome / macOS / SAML
7. Firefox / Windows / password
8. Firefox / Windows / SAML
9. Firefox / Linux / password
10. Firefox / Linux / SAML
11. Firefox / macOS / password

除外: Firefox / macOS / SAML（成立不能）

### 2-wiseカバレッジ確認

- 生成方法 / ツール: 未実行（分類木runtime `classification_tree.py` → 組合せruntime `combinatorial.py` を実行できなかった）。上記は母集団の手作業導出であり、生成済みcoverageではない。
- 制約: `Firefox + macOS + SAML` 成立不能（3因子の制約で、2因子ペアは単独では成立不能にならない）。
- 成立可能な全値ペアがカバレッジ項目でカバー済みか: **未確認（生成前）**。母集団は16ペア（全件に成立witnessあり）。
- 確認根拠: 手作業の母集団導出のみ。生成結果による確認は未実施。

## 統合候補

| 候補                       | 統合理由                                                                               | カバー先 |
| -------------------------- | -------------------------------------------------------------------------------------- | -------- |
| CI01 と CI02 の統合        | なし。CI02の射影がCI01を満たすが、入力で明示された2つのcriterionであるため統合しない。 | —        |
| TCN-008 とテスト実行の統合 | テストケース化・実行行の統合は `test-case-design` の担当。本Skillでは統合しない。      | —        |

## Machine Runtime / Entity / Target mapping（機械証拠）

- 未生成。`classification_tree.py` と `combinatorial.py` の実行を試みたが、Bash実行が権限拒否され実行できなかった。
- そのため `render_runtime_input()` / `render_runtime_result()` / `render_machine_entities()` の出力、target_ref、fingerprint、CI ID、materialization結果は本成果物に含めない。
- `verify_runtime_evidence` の最終gateも未実行。現時点で本成果物は完成扱いしない。

## 未解決事項（完成に必要）

1. 分類木runtime（`classification_tree.py`）を実行し、adapter model keyを採番したうえで `comb-008` のcurrent Machine Entityとfingerprintを照合する。
2. 組合せruntime（`combinatorial.py`）で CI01（16ペア）と CI02（11 tuple）の生成行とtargetを得て、2-wise／3-wise coverageを機械確認する。
3. `TR-CTD-008` の優先度と関連プロダクトリスクを確認し、TCN・CIへ継承する。
4. Authority `SPEC-CTD-008` の本文を確認する（入力記述との差異がないこと）。
5. 上記が揃った後、テストケース化は `test-case-design` へ渡す。
