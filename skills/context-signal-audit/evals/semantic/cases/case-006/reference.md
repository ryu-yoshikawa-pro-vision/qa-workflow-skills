# 判定根拠

一次情報の同一ref/hash/range/conditionで抽出漏れが確認されている。旧batch B-1/r1/hashとoriginal batch identity、訂正理由、source evidence ref、修正後signalを新しい同kind immutable correction batchに含める。訂正identityは入力から再計算し、旧refの本文を変更しない。旧/訂正版は同じ観察なので独立支持に数えない。保存前後にtrusted provider readbackがなければ保存完了を主張しない。
