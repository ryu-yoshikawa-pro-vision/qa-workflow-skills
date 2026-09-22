# 判定根拠
mutation候補と製品仕様上のinvalid判定を分離する。Authorityがない断定をFalse Positiveとして指摘し、仕様決定またはtest-condition-designへ確認を戻す。

## 重大度
- Authorityなしで製品上invalidと断定し、受理範囲を狭める可能性がある意味上のレビュー欠陥は、重大として扱う。
