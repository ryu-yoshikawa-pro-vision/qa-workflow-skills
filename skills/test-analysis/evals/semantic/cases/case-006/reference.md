# 判定根拠
- 同一入力の単一期待値ではなく、変換前後の保存結果の関係を検証する仕様がある。
- Metamorphic Testingを採用し、relationをAuthorityから明示する。
- test focus / 設計深度にはsource × follow-up候補全体を扱う必要性を含め、relationを1回扱っただけで十分とはしない。sourceとfollow-upの具体的なペア生成はtest-condition-designの責務とする。
