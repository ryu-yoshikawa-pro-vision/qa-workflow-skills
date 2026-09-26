# 判定根拠
mutation候補と製品仕様上のinvalid判定を分離する。Authorityがない断定をFalse Positiveとして指摘し、期待挙動が不明なら`qa-workflow`経由で`question-analysis`へ仕様根拠を確認する。仕様が確定した後に必要なCoverage分類を`test-condition-design`へ戻す。

## 重大度
- Authorityなしで製品上invalidと断定した問題は検出する。
- 入力に実利用時の影響や分類結果の適用先が示されていないため、重大度は`未判定`とし、具体的な影響を推測しない。
