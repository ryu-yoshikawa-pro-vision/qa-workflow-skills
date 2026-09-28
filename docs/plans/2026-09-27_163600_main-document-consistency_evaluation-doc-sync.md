# 評価ランタイム文書整合Plan

この文書は、`docs/plans/2026-09-27_163600_main-document-consistency.md`のうち、E2E cleanup状態、評価ディレクトリ構成、deterministic Assertion一覧に関する文書不整合を扱います。

対象は文書整合だけです。validator、fixture、dataset、runtime、CI、test codeは変更しません。

## 対象

13. E2E execution / reportingのcleanup状態一覧を、現在のvalidator契約へ同期する
14. READMEとdeterministic評価READMEのディレクトリ構成図を現在のtreeへ同期する
15. `scripts/skills/evals/deterministic/ASSERTIONS.md`を現在のdeterministic validatorと一致させる

## 判断原則

この3件では、現在の実装・評価コードを正本として文書を同期します。

確認順序は次です。

1. 現在のvalidator / runtime
2. repository test
3. 現在のファイルtree
4. Skill / asset / guidance
5. `EVALS.md`
6. README / Assertion一覧

文書の記載に合わせてvalidator、fixture、dataset、testを変更しません。

過去Planや過去reportの記載は履歴として変更しません。

## 13. E2E cleanup状態の許可値

### 現在の不整合

`skills/e2e-test-execution/evals/deterministic/validator.py`の`CLEANUP_STATES`は次の6状態です。

- `成功`
- `失敗`
- `未確認`
- `対象なし`
- `意図的に残した状態`
- `一部失敗`

同validatorはcleanupに`失敗` / `未確認` / `一部失敗`がある場合、`実行成果物状態 = 完了`を拒否します。

一方、現在の次の文書では`一部失敗`だけが許可値一覧から抜けています。

- `skills/e2e-test-execution/SKILL.md`
- `skills/e2e-test-execution/assets/output-template.md`

`assets/output-template.md`自身も、許可値を示す表の直後では`一部失敗`を扱っているため、同一文書内で不一致です。

`skills/e2e-test-reporting/evals/deterministic/validator.py`も同じ6状態を`CLEANUP_STATES`として扱っています。

一方、次の文書では`一部失敗`が抜けています。

- `skills/e2e-test-reporting/SKILL.md`
- `skills/e2e-test-reporting/assets/output-template.md`

### 修正方針

E2E execution / reportingのcleanup状態一覧を、現在のvalidatorが受理する6状態へ揃えます。

変更は文言・templateの許可値表示だけに限定します。

`e2e-test-execution`では、

```text
成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 / 一部失敗
```

へ統一します。

`e2e-test-reporting`も同じ6状態を入力execution resultから失わず報告できるよう、SKILLとtemplateの一覧を同期します。

### 変更しないもの

- cleanup状態の意味
- cleanup完了判定
- `e2e-test-execution`の`実行成果物状態`
- `要再確認`と`qa-workflow`の`要再検証`の語彙
- validator
- deterministic fixture
- reporting集計ロジック

`要再確認`は現在の`e2e-test-execution` validatorでも独立した実行成果物状態として定義されているため、今回の文書整合だけを理由に`要再検証`へ変更しません。

## 14. 評価ディレクトリ構成図

### README.md

現在の`README.md`では、

```text
tests/skills/evals/
├── deterministic/
└── semantic/
```

と記載しています。

現在のtreeには次の3ディレクトリがあります。

```text
tests/skills/evals/
├── deterministic/
├── semantic/
└── trigger/
```

したがって`trigger/`を追加します。

また、`scripts/skills/evals/`の構成図は主要コードを列挙していますが、現在の文書資産である次が抜けています。

- `scripts/skills/evals/deterministic/ASSERTIONS.md`
- `scripts/skills/evals/deterministic/README.md`
- `scripts/skills/evals/semantic/README.md`

この節がディレクトリ構成図として現在treeを説明しているため、現在存在する評価ランタイム文書も構成へ反映します。

`__init__.py`等、従来から省略している実装上の補助ファイルまで全件列挙する形式へは変更しません。

### deterministic評価README

`scripts/skills/evals/deterministic/README.md`の構成図には現在のtreeに存在する次が抜けています。

共通runtime:

- `runtime_validator.py`
- `tests/test_runtime_validator.py`

repository deterministic test:

- `test_e2e_contracts.py`
- `test_new_skill_contracts.py`
- `test_qa_artifact_graph_skills.py`

現在存在する主要テストへ構成図を同期します。

### 変更しないもの

- ディレクトリ構成
- test配置
- 評価runtime
- `__init__.py`の列挙方針
- semantic dataset構造

## 15. ASSERTIONS.mdと現在validatorの同期

### 現在の不整合

`scripts/skills/evals/deterministic/README.md`は、

```text
Assertion IDの正本はASSERTIONS.md
```

と定義しています。

しかし現在のdeterministic validatorに存在するAssertion IDの一部が、`scripts/skills/evals/deterministic/ASSERTIONS.md`へ反映されていません。

確認済みの未記載IDは80件です。

#### coverage-analysis

- `COV-D013`

#### qa-workflow

- `WF-D018`
- `WF-D019`
- `WF-D020`
- `WF-D021`

#### question-analysis

- `QUESTION-D019`
- `QUESTION-D020`

#### e2e-test-inspection

- `E2E-INSP-D013`
- `E2E-INSP-D014`
- `E2E-INSP-D015`
- `E2E-INSP-D016`

#### e2e-test-implementation

- `E2E-IMPL-D014`
- `E2E-IMPL-D015`
- `E2E-IMPL-D016`
- `E2E-IMPL-D018`
- `E2E-IMPL-D019`
- `E2E-IMPL-D020`
- `E2E-IMPL-D021`
- `E2E-IMPL-D022`

#### e2e-test-execution

- `E2E-EXEC-D018`
- `E2E-EXEC-D019`
- `E2E-EXEC-D021`
- `E2E-EXEC-D022`
- `E2E-EXEC-D023`
- `E2E-EXEC-D024`
- `E2E-EXEC-D025`
- `E2E-EXEC-D026`
- `E2E-EXEC-D027`
- `E2E-EXEC-D028`
- `E2E-EXEC-D029`
- `E2E-EXEC-D030`
- `E2E-EXEC-D032`
- `E2E-EXEC-D033`
- `E2E-EXEC-D034`
- `E2E-EXEC-D035`
- `E2E-EXEC-D036`

#### e2e-test-result-analysis

- `E2E-AN-D011`
- `E2E-AN-D012`
- `E2E-AN-D013`
- `E2E-AN-D014`
- `E2E-AN-D015`

#### e2e-test-reporting

- `E2E-REPORT-D017`
- `E2E-REPORT-D018`
- `E2E-REPORT-D019`
- `E2E-REPORT-D020`
- `E2E-REPORT-D021`

#### regression-testing

- `REG-D001`〜`REG-D015`

#### exploratory-testing

- `EXP-D001`〜`EXP-D008`

#### qa-knowledge

- `KN-D001`〜`KN-D011`

連番の欠番は埋めません。例えば`E2E-EXEC-D020`、`E2E-EXEC-D031`、`E2E-IMPL-D017`等を、番号が連続していないことだけを理由に追加しません。

### 修正方針

現在の各`skills/<skill>/evals/deterministic/validator.py`に存在する`result.add(<Assertion ID>, ...)`を正本として、`ASSERTIONS.md`へ未記載IDと現在の説明を追加します。

説明文はvalidatorの判定内容を要約し、過去の意味へ合わせて書き換えません。

PR #13で追加した3 Skillについては、新しい節を追加します。

- `regression-testing`
- `exploratory-testing`
- `qa-knowledge`

既存Skillについては現在の節へ不足IDを追加します。

### 全件照合

13〜15の実装時には、今回列挙した80件だけを追加して終了せず、現在の全deterministic validatorと`ASSERTIONS.md`を再照合します。

確認条件:

- validatorに存在するAssertion IDが`ASSERTIONS.md`へすべて存在する
- `ASSERTIONS.md`のSkill別IDが現在のvalidatorに存在する
- 同一IDを複数の説明で重複記載しない
- validatorに存在しないIDを連番補完しない
- WARNING IDも現在validatorに存在するものは保持する
- 共通runtime Assertionは、現在のrepository test / runtime validatorの契約に基づく既存記載を維持する

既存`RT-D001`〜`RT-D015`は今回確認したSkill-local validatorの比較対象ではありません。共通runtime contractとして既存の検証経路に残し、この変更だけを理由に削除しません。

### 変更しないもの

- Assertion ID
- validatorの判定条件
- fixture
- expected.json
- runtime validator
- deterministic runner
- CI

## 変更対象

- `skills/e2e-test-execution/SKILL.md`
- `skills/e2e-test-execution/assets/output-template.md`
- `skills/e2e-test-reporting/SKILL.md`
- `skills/e2e-test-reporting/assets/output-template.md`
- `README.md`
- `scripts/skills/evals/deterministic/README.md`
- `scripts/skills/evals/deterministic/ASSERTIONS.md`

必要性が確認できないファイルは変更しません。

## 検証

### 文書検索

少なくとも次を確認します。

```bash
git grep -n '成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態' -- \
  skills/e2e-test-execution \
  skills/e2e-test-reporting
```

許可値一覧を示す箇所では`一部失敗`まで含むことを確認します。過去Planは対象外です。

### tree照合

現在treeと次を照合します。

- `README.md`の`tests/skills/evals/`
- `README.md`の`scripts/skills/evals/`
- `scripts/skills/evals/deterministic/README.md`の共通runtime構成
- 同READMEのrepository deterministic test構成

構成図を全ファイル一覧へ拡張せず、現在その図が説明している粒度で欠落だけをなくします。

### Assertion ID照合

全Skill-local deterministic validatorのAssertion IDを抽出し、`ASSERTIONS.md`と相互比較します。

判定:

- validatorにあるが`ASSERTIONS.md`にないID: 0件
- `ASSERTIONS.md`のSkill-local IDで、対応validatorに存在しないID: 0件

共通runtimeの`RT-Dxxx`は別契約として照合します。

### 既存評価

親Planの検証に加えて、少なくとも次を実行します。

```bash
python -m unittest discover -s tests/skills/evals/deterministic -v
python -m unittest discover -s tests/skills/evals/trigger -v
git diff --check
```

文書だけの変更なので、validator / fixture / datasetの期待値は変更しません。

## 完了条件

- E2E execution / reportingのcleanup許可値表示が現在の6状態と一致する
- `一部失敗`を入力で受け取れるvalidatorと文書表示が矛盾しない
- `README.md`の評価構成図に現在存在する`tests/skills/evals/trigger/`が反映されている
- root READMEの評価runtime構成図と現在の主要文書・runtime構成に説明不能な差がない
- deterministic READMEの構成図に`runtime_validator.py`と現在の主要repository testが反映されている
- 全Skill-local deterministic validatorのAssertion IDと`ASSERTIONS.md`が一致する
- `REG-Dxxx` / `EXP-Dxxx` / `KN-Dxxx`の節が`ASSERTIONS.md`に存在する
- 欠番を推測で追加していない
- validator / fixture / dataset / runtime / CI / test codeを変更していない
