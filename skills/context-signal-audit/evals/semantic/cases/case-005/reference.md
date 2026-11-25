# 判定根拠

`impl_observation`として、source ref/revision/hash、screen/state locator、build、environment、role、timezoneを保持する。これはstagingの観察であり期待仕様ではない。Restoreがarchive状態以外に存在しない、productionも同じ、adminでの状態も同じとは一般化しない。
