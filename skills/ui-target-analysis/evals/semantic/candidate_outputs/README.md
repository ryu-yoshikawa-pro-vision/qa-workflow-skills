# 意味評価candidate

各candidateは新設Skillを使った想定出力として、本branchの実装者が作成しました。`results/`のrating・reason・verdictは、各caseについて別のephemeral Codex CLI processで実行したJudgeの結果です（Codex CLI `0.167.0`、`--no-daemon --strict-config --ephemeral --sandbox read-only`）。UI-SEM-001〜004の4候補、適用対象10 criteriaはすべて`pass`です。

Judgeのevidenceがcandidateの内容を引用符付きでparaphraseした箇所は、回帰testが検証できるよう同じ根拠の連続したverbatim excerptへ整えています。rating、reason、verdictは変更していません。Candidate作者とJudgeは別process/sessionですが、これは全Skillを同時に読み込むfull-agent trigger、A runtime、実providerや他owner成果物との統合検証ではありません。共有EVALSへの登録後、PR #22で統合後の評価を再実行してください。
