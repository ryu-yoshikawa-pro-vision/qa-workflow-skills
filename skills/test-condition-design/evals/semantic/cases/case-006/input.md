# Eval Input
画像変換のrelation `resize-preserves-aspect` があり、source `IMG-001`はwidth=800、height=400。follow-up `FU-2X`はwidth/heightを各2倍し1600×800、`FU-3X`は各3倍し2400×1200にする。expected relationは各follow-up出力で`output.width / output.height = source.width / source.height`。Metamorphic Coverage Itemを作る。
