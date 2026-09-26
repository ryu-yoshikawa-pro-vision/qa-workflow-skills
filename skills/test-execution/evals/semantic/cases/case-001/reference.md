# Reference
- 1つの入力元snapshot内で成果物ローカル参照を一意に割り当て、重複source IDをそのまま保持する。重複だけでは未実行にしない。
- 入力元identityがない場合は独自hashを作らず、成果物内のTC集合と実行前YAMLをsnapshot正本にする。
- 操作前にGiven / When / Thenを整理する。中間期待結果と操作を結び付け、判定に影響する観測タイミングはunresolvedに残して該当TCを開始しない。
- MCPが契約を満たすためPlaywright MCPを選び、実操作と観測を入力順に完了してから次TCへ進む。
- screenshotが必要な視覚期待結果は画像で確認し、TC外の崩れを理由なくFAILへ変えない。
- workflow全体の状態と個別TCの結果を分ける。
