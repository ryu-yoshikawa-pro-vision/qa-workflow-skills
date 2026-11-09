# 非E2E testware実装の判断

## 対象と根拠

- 有効な正式TCを使用する場合、TC revision、仕様Authority、期待結果、テスト方式、対象buildを固定する。
- TCなしの場合、明示した自動testwareの対象、採用基準と検証する期待挙動、source revisionを記録し、TC IDを作らない。
- API-only Playwright Testも非E2E。ブラウザpage/locator/操作を含むE2Eは既存E2E Skillの正本へ戻す。
- 方式を無断でブラウザE2Eに置換しない。非機能の測定条件・品質特性・閾値がない場合、適合判定を実装しない。

## 書込みの安全確認

1. 変更対象repo、branch/HEAD、許可path、作業用隔離copy、既存dirty対象、既存コード・helper・fixture・依存設定を保存する。
2. 作業開始時点の各対象pathの内容hashと欠落状態、共通設定・lockfileを含む変更対象集合を固定する。既存利用者変更の上書きは不可。
3. 隔離copyで実装・lint等の非破壊検証を行う。commandのpre/post chain、既存fixtureのside effectを先に検査する。Product SUTと正式仕様には書かない。
4. 共有先へ反映する直前にbranch HEADと対象ファイル全てを再取得してhashを照合する。snapshot_guard.check_snapshot()は競合の早期検知に使えるが、原子的なcommit/pushは保証しない。
5. 反映はGitHub APIの期待HEAD更新やgit pushのfast-forward等、実際の保存先の条件付き確定と独立readbackを必要とする。HEADや対象内容が変われば新しい前提で再計画し、元の変更を上書きしない。
6. 直接共有workspaceを編集する場合、全書込み主体が同じ排他手段を守ると確認できなければblocked。予約ownerとcleanupを確認できない場合も編集しない。
7. commitの応答が消失したら同じoperation_refで変更先HEADとファイル内容を調べ、成功・失敗を推測しない。force push、reset --hard、強制cleanを使わない。

## 独立品質

生成したassertionと各期待結果、データ・mock・fixture依存、分岐、観測方法の対応をadversarial-reviewで独立確認する。runner成功だけではassertion品質を満たさない。正式TCとのcoverageの正本はcoverage-analysisに残す。実runner実行結果はtestware-executionが保存する。

既存E2E側の同時編集と変更反映の保証は詳細Plan 05に従うが、共有e2e-test-implementationの編集ownerとの照合を要するため、このSkillの安全検査だけで全体保証としない。
