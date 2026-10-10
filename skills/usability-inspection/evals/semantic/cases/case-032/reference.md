# Expected semantic contract

必要な観測内容と理由を返し、usability-inspectionが既存side-effect / ownership契約の範囲でstateへ到達し、`observation_contract.py` のfixed field / probeへ変換して追加evidenceを取得できること。任意JavaScript、hidden DOM、test idによるshortcutへfallbackしないこと。同一requestをnew evidenceなしで反復しないこと。
