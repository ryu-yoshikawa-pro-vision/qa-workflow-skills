# Eval Input

既定の `assets/output-template.md` 形式を使用してください。

TR-001をPairwiseで展開する。
Authority: SPEC-001。
Risk: RISK-001。
Factors:
- Role: admin, member
- Browser: Chrome, Edge
- Flag: on, off
Constraint: Role=member かつ Flag=off は成立不能。
生成組合せは `Factor=Value; Factor=Value` 形式で記載する。
Pairwiseと名乗るなら成立可能な全2-wise pairをカバーすること。
