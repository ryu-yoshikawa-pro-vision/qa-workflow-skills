# 判定根拠
adapter自身をCI化せず、採番済みchild modelへfactor/class skeletonを渡す。strengthごとのfeasible tupleを制約適用後に計算し、同じ意味の組合せを重複生成しない。
