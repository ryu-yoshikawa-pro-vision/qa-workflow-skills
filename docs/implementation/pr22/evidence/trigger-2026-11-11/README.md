# PR #27 E担当 実Agent発火評価

`trigger-evidence-v2.tar.gz`は24 current Skill packageだけを使ったreduced-snapshotの予備routing checkpointです。worktree同等のroot repository filesが含まれていなかったため、v1／v2のthreshold観測は最終受入へ使いません。raw traceと旧archiveは履歴として維持し、正式評価はcurrent tracked tree全体をcopyした一時snapshotからやり直します。旧archive集計は[README-v2.md](README-v2.md)と[evidence-index-v2.json](evidence-index-v2.json)、raw JSONL traceはarchive内に保存しています。
