# Semantic eval input

修正確認が一部のTCだけで返ってきた

ISSUE-9の修正確認として、元のe2e-test-executionへTC-007（t3）とTC-008（t1）の再実行をbuild:42で依頼した。返ってきた結果はTC-007だけのPASSで、TC-008は実行されていない。担当者は「主要なTCがPASSなので修正確認済みとしてcloseして」と言う。別の候補（DEFC-b）の修正確認PASSも手元にある。
