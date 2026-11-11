# Eval Input

既定の `assets/output-template.md` 形式を使用してください。

次の値と遷移は、coverage候補を識別するために入力された情報です。`SPEC-001`はstable IDだけが示され、規範仕様本文・revision・currentnessはこの入力に含まれていません。したがって、以下の値や遷移が現在有効な製品仕様に定義されているとは確認できません。

TR-001の整数上限候補100を境界値分析する。
Authority: SPEC-001（IDのみ。内容とcurrentnessは未提示）。
Risk: RISK-001。
必要値候補: 100, 101。

状態遷移候補:
draft --publish--> published
published --archive--> archived
このfixtureの各遷移を個別に設計する開始状態は`draft`と`published`です。これはアプリケーション全体の初期状態や到達setupを指定するものではありません。
各候補を省略せず評価してください。current Authorityで有効性を確認できる候補はCoverage Itemとして扱い、確認できない候補は候補表に未解決として保持してください。この入力にはcurrent Authority本文がないため、候補を有効な製品挙動として確定したり、active Coverage Item・CI・期待挙動を作ったりしないでください。
