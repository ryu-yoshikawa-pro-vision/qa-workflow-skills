# Eval Input

同一TCN / 同一modelのcurrent target A・Bは同じexecution fingerprintとexpected result rootを持ち、source modelも同じ。両source target versionはcurrent。Aのtest data requirementは`role=admin`、Bのrequirementは同じ`role` dimensionの`role=guest`で、両方がmerge後のCIへ適用される。別modelのtarget Cは同じexecution fingerprintとexpected result rootを持ち、source target versionはcurrentだが、別modelに属する。条件設計では製品behaviorの技法を選ぶ課題ではなく、materializationのdeterministic grouping predicateとrequirement union/intersection contractを検証する。

テスト要求`TR-MERGE-013`（システムテスト）は「merge後のCI materializationで、grouping predicateとtest data requirementの合成が決定的に働くこと」を求める。根拠は承認済みでcurrentな`SPEC-MAT-013`で、「同一TCN・同一model・current target version・同一execution fingerprint・同一expected result rootがすべて一致する場合だけmergeを許可し、同一dimensionのrequirementはintersectionしてconflictならmergeを拒否する」と定める。current modelのMachine Entityは確認済み。
