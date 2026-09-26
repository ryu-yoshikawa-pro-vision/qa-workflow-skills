# 判定根拠
開始state、reset execution、setup prefix、coverage sequence、transitionのfrom/event/toを自己完結させる。2-switch windowsは指定された`draft`開始path上に置き、2番目のwindowには`draft → editing` setup prefixを含める。round-tripは開始stateを保持し、n-switchと同一視しない。setup不能なrequired transitionを黙って除外しない。
