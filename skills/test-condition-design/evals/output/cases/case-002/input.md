# Eval Input

既定の `assets/output-template.md` 形式を使用してください。

TR-001の整数上限100を境界値分析する。
Authority: SPEC-001。
Risk: RISK-001。
必要値: 100, 101。

状態遷移:
draft --publish--> published
published --archive--> archived
このfixtureの各遷移を個別に設計する開始状態は`draft`と`published`です。これはアプリケーション全体の初期状態や到達setupを指定するものではありません。
全有効遷移をCoverage Itemへ閉じる。
