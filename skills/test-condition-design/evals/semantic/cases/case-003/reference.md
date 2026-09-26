# 判定根拠
各closed border（`<=`）についてON=border上、OFF=1 step外、IN=1 step内、OUT=2 steps外のrequired pointを、変数のcoordinatesとrelation付きで作る。quantity borderは(price=900を固定して)ON `(10,900)`、OFF `(11,900)`、IN `(9,900)`、OUT `(12,900)`。price borderは(quantity=9を固定して)ON `(9,1000)`、OFF `(9,1001)`、IN `(9,999)`、OUT `(9,1002)`。各点をpartition全体へ再代入し、ON/INは内側、OFF/OUTは外側であることを確認する。model内Coverageを仕様全体Coverageと混同しない。
