# Reference

old baselineを黙ってfullとして使いません。current discovery / lifecycle / membershipをreconcileしてから新snapshotを確定します。currentnessが閉じるまではfull Runをblockし、old snapshotへ新TCを継ぎ足しません。
