# PR #27 E担当 実Agent発火評価

正式評価は、current tracked repository全体と24 current Skill packageを含めた一時snapshotから実施します。`trigger-evidence-v1.tar.gz`／`v2`はSkill packageだけのreduced snapshotによる予備証拠であり、最終発火率には含めません。元のtraceとarchiveは履歴として維持します。

最新checkpointの[README-v3.md](README-v3.md)／[evidence-index-v3.json](evidence-index-v3.json)／[trigger-evidence-v3.tar.gz](trigger-evidence-v3.tar.gz)には、full repository snapshotから実行したE2E train query 1の3独立試行を保存しています。対象Skill読込は3/3でしたが、これは1 queryのみのpartial resultで、train／validation全datasetやholdoutの受入ではありません。1試行で`qa-workflow`資料も読み込まれたため、追加routing観測として記録しています。

reduced-snapshotの予備試行の詳細は[README-v2.md](README-v2.md)と[evidence-index-v2.json](evidence-index-v2.json)、raw JSONL traceは各archiveに保存しています。
