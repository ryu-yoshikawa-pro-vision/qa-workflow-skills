# 判定根拠
- 文法・production・mutationが仕様として定義されているためSyntax-Based Testingを採用する。
- reachable productionとunreachable productionを区別し、後者を黙ってCoverageから除外しない。
- Authorityが定めていない入力を製品上invalidと断定しない。
