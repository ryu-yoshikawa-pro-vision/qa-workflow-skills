# Eval Input
ログイン判定は`role={guest, admin}`と`visibility={public, private}`の組合せで決まる。Authority `SPEC-017`は「guest × private board」をテスト実行可能なassignmentではないというcause-effect constraintとして定める。このconstraintはログイン拒否という期待actionを定義するものではない。constraintをDecision Tableへ渡し、成立不能assignmentとして扱う。他の組合せの期待結果は指定しない。don't-care候補を作るが、未定義のactionを推測しない。
