# 判定根拠
operator固有のtyped valueを保持する。model-wide requirementは同一source modelのcurrent targets A/Bへ適用し、target-specific requirementは完全一致するcurrent source target version refsだけへ適用する。各target上で該当するrequirement unionをintersectionし、Aの`version >= 2.0 ∩ version <= 1.4`だけをconflictとして報告する。Bの`version = 1.3`とAのrequirementをcross-intersectしない。保存されたapplicable target refsがあれば再導出結果と照合する。environment key規則は適用しない。
