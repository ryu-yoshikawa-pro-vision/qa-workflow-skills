# Eval Input
対象partitionは`quantity <= 10 AND price <= 1000`、料金合計は`quantity * price`。borderはclosedで、各relationは対象partition内側がtrueになる向きとする。quantity borderは`quantity=10`、anchorは`price=900`。price borderは`price=1000`、anchorは`quantity=9`。quantityとpriceはinteger、stepは両方1。各anchorは他方のborderについてpartition内部にある。
Domain Testingで各borderのON/OFF/IN/OUT Coverage Itemを、座標値とrelation付きで設計する。
