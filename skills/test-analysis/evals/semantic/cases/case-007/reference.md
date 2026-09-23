# 判定根拠
- 文法・production・mutationが仕様として定義されているためSyntax-Based Testingを採用する。
- reachable productionとunreachable productionを区別し、後者を黙ってCoverageから除外しない。
- Authorityが定めていない入力を製品上invalidと断定しない。
- このDSLは本番起動設定であり、誤受理時に全利用者の起動が阻害されrollbackが必要という明示影響に基づき、impactは標準matrixの4にする。
- 変更は独立した単一productionで、依存・分岐の増加、過去不具合、不安定性の根拠は示されていない。肯定的なLikelihood 1根拠もないため、ガイダンス既定のLikelihood 2を低信頼で用いる。impact由来の4をLikelihood根拠にしない。Risk Levelは標準matrixのHigh。
