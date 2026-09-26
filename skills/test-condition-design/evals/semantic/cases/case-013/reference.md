# 判定根拠
merge groupは同一TCN・同一model・current target version・同一execution・同一expected rootだけを許可する。merge後もtest data requirementのunionをintersectionし、conflictなら拒否する。
