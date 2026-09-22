# 判定根拠
Dispositionはcurrent target content / generation / execution versionと一致し、self参照やcycleを作らない場合だけ有効。未閉鎖targetを別CIの存在だけでcompleteにせず、model completionをfalseにする。
