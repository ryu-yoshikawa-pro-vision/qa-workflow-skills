# PR #27 E担当 実Agent発火評価

正式評価は、current tracked repository全体と24 current Skill packageを含めた一時snapshotから実施します。`trigger-evidence-v1.tar.gz`／`v2`はSkill packageだけのreduced snapshotによる予備証拠であり、最終発火率には含めません。元のtraceとarchiveは履歴として維持します。

最新checkpointの[README-v6.md](README-v6.md)／[evidence-index-v6.json](evidence-index-v6.json)／[trigger-evidence-v6.tar.gz](trigger-evidence-v6.tar.gz)には、Product Risk近接negative queryのtimeoutを保存しています。900秒でAgent turnが未完了のため、発火率へ算入していません。

[README-v5.md](README-v5.md)／[evidence-index-v5.json](evidence-index-v5.json)／[trigger-evidence-v5.tar.gz](trigger-evidence-v5.tar.gz)には、E2E train query 3の3試行を保存しています。対象読込0/3でした。

[README-v4.md](README-v4.md)／[evidence-index-v4.json](evidence-index-v4.json)／[trigger-evidence-v4.tar.gz](trigger-evidence-v4.tar.gz)には、E2E train query 2の3試行を保存しています。対象0/3、`e2e-test-execution`3/3でした。

[README-v3.md](README-v3.md)／[evidence-index-v3.json](evidence-index-v3.json)／[trigger-evidence-v3.tar.gz](trigger-evidence-v3.tar.gz)には、E2E train query 1の3試行を保存しています。対象読込3/3で、1試行では`qa-workflow`資料も読まれたためrouting観測に保持しています。

reduced-snapshotの予備試行の詳細は[README-v2.md](README-v2.md)と[evidence-index-v2.json](evidence-index-v2.json)、raw JSONL traceは各archiveに保存しています。
