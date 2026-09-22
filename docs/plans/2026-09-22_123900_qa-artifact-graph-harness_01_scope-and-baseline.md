# Regression Suite / QA Activity 統合Plan

## 1. 目的

PR #11 / #12後に残る課題だけを扱います。

- 新規・改修で作成したTCを、そのセッションだけで終わらせず、継続Regressionへ再利用できるようにする
- 現在のRegression対象範囲を網羅する基準集合と、各回のRunを分離する
- Regressionごとのcandidate / selected / excluded / rationale / residual risk / executionを履歴として残す
- Exploration / InvestigationのCharter / Session / Finding / Follow-upを第一級成果物として扱う
- release / sessionを跨いで過去activityを発見できるようにする
- direct refでは不足する横断queryだけ、必要性確認後に決定論的に支援する

次はPR #13で再実装しません。

- SPEC → TR → TCN → CI → TCのdesign traceability
- design change impact
- freshness / stale / `要再検証`
- TC snapshot
- execution / result / rerun lineage

## 2. 実装開始時の確認

PR #11 / #12 merge後に次を確認します。

1. latest `main`のMachine Entity、traceability、change impact、freshness、execution、rerunの実契約を取得する。
2. PR #11からproject全体のcurrent TC集合を決定論的に列挙できるか確認する。
3. current TCのlifecycleをPR #11だけでcurrent / deleted / superseded相当に判断できるか確認する。
4. 実成果物で次を確認する。
   - current TC → design root
   - changed design node → affected TC
   - TC → current E2E testware
   - execution → TC snapshot / target version / previous execution
5. activity成果物を既存の固定保存場所から列挙できるか確認する。
6. direct refだけで次を回答できるか試す。
   - Regression activity → selected TC → execution → result
   - Finding → follow-up
   - TC →過去activity / execution
7. 2〜6で不足するものだけをPR #13の追加実装対象にする。

### Regression Suiteのmaterialization gate

project全体のcurrent TCと加入判断を既存成果物から再構成できる場合、Regression Suiteは派生viewとして扱い、TC本文やlifecycleを別artifactへ複製しません。

直接再構成できない場合だけ、project-localなRegression Suite artifactへ次の最小情報を保持します。

- Regression対象範囲ref
- member TC ref
- source artifact ref / revision
- membershipの判断結果と理由
- 明示的な一時検証 / 対象外の理由

どちらの場合も、Regression SuiteをPR #11と競合する第二のTC正本にしません。

## 3. Regression対象範囲

「全機能」はSuiteに登録されたfeature tag一覧から定義しません。

Regression対象範囲は次を入力として定めます。

- 案件コンテキストの対象機能 / 対象業務フロー / 対象role
- test level
- 現在有効な仕様根拠
- Product Risk
- 明示された非機能テスト範囲
- ユーザーが指定した対象外

本Planの既定対象は、案件でRegression対象としたcurrentな機能テスト範囲です。性能、アクセシビリティ、セキュリティ等は案件コンテキストでRegression対象に含めた場合だけ同じ基準集合へ含めます。

Suite自身のmember / tag集合を「全機能」の母集団に使いません。

## 4. QA活動別の位置づけ

### 4.1 新規・改修

既存flowを維持します。

```text
仕様根拠
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
→ 必要時 adversarial-review / E2E
```

各セッションの完了時に、current TCごとに継続Regression対象か一時的な検証かを確認し、Regression Suiteへ反映します。

### 4.2 Regression

```text
Regression対象範囲
        ↓
Regression Suite
        ↓ snapshot
full / selected Run
        ↓
execution route
        ↓
PR #12 / E2E execution
        ↓
Result / Evidence
```

SuiteのcoverageとRunのscopeを分離します。

### 4.3 Exploration / Investigation

既存SkillにはCharter / Session / Observation / Finding / Evidence / Follow-upを第一級成果物として扱う責任Skillがありません。

`exploratory-testing`を1 Skillだけ追加します。

- `mode=exploration`: charterに基づく探索
- `mode=investigation`: 既存責任Skillがない実対象の仮説駆動調査

E2E failureは引き続き`e2e-test-result-analysis`を優先します。

## 5. 責務境界

### 既存Skill

意味判断を担当します。

- current仕様根拠
- Product Risk
- Test Requirement / Condition / Case
- 継続Regression対象か一時的な検証か
- selected Regressionの意味上のscope
- TC → E2E実装のcoverage
- Exploration / Findingの意味
- 修正routing

### qa-workflow

オーケストレーションと記録を担当します。

- Suite更新の起動
- full / selected routing
- activity artifact作成
- execution route受け渡し
- activity discovery
- query不完全時の安全側routing

意味上のcoverageやRiskを再判定しません。

### 決定論的補助runtime

必要な場合だけ追加します。

- Suite / activity artifactのschema検証
- duplicate / dangling ref検出
- activity発見
- direct refで不足するrelation query
- query completeness判定

PR #11のdesign impact / freshnessを再計算しません。
