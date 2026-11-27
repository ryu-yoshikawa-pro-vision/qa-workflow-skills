# 判定根拠

requested_rangeはSEC-1〜5、actual_inspected_rangeはSEC-1〜2、scanはpartial。本文にある2事実だけなら不変partial batchにできる。SEC-3〜5の結果を空・存在しない・completeと扱わない。retention値はunknown。完全性チェック、保存結果、追加取得を別状態として説明する。

source本文の範囲を確定できないケースと、取得範囲が確定したpartialを混同しない。provider失敗や自己申告hashから完全取得としない。
