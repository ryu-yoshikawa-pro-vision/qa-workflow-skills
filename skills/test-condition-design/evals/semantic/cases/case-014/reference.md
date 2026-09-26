# 判定根拠
Aの`重複`chainはAのcurrent content / generationからBの指定current content / generationへ一致して進み、Bのcurrent mapping終端はCI-001のexecution fingerprintと一致し、self reference / cycleがない場合にだけ閉鎖済みとなる。Cは未閉鎖のまま保持し、別CIの存在で補わずmodel completionをfalseにする。
