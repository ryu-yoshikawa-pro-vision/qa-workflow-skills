# Expected semantic contract

→ started claimを削除・再利用せず、`HANDOFF-002` を `retry_of_handoff_ref=HANDOFF-001` としてmaterializeし、新operation refで観測する。exact duplicate result再送はnew handoffを作らない。
