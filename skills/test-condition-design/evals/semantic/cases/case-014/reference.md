# 判定根拠

Aの`重複`chainはAのcurrent content / generationからBの指定current content / generationへ一致して進み、Bのcurrent mapping終端はCI-001のexecution fingerprintと一致し、self reference / cycleがない場合にだけ閉鎖済みとなる。Cは未閉鎖のまま保持し、別CIの存在で補わずmodel completionをfalseにする。

`TR-ORDERS-014`をテスト条件へ展開し、閉鎖の結果をCoverage Itemで表す。BはCI-001で確認済み、Aは`重複`のcover先としてCI-001を示す。Cは未到達のため、Cを確認するCoverage Itemが不足していることを示し、model completionをfalseのまま残す。
