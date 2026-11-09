# Reference

Runでは、TC-401のrequired routeを`manual`と`testware`（testware ref・実行owner・実装revision・選択条件付き）として保持し、`app-config`補助を`completion_required=true`（根拠は利用者の明示指示）、`native-stores`補助を`completion_required=false`（参照のみ）として別集合に置きます。

Activityは`完了`にしません。TC-401は全required routeが開始済みで確定済みなのでexecutedですが、実施義務のある`app-config`補助がactual start前のblockedのため、開始済みの義務があることを踏まえ`部分完了（ブロック中あり）`（既存状態）にします。`native-stores`の未開始は完了を妨げない理由として明記します。

補助testwareにTC IDを作らず、`tc_member_count`・`executed_tc_count`・TC-based coverageへ加算しません。補助の件数と結果は別項目で保持します。source resultを再解釈せず、blockedを実行済みや結果確定にしません。「TCがPASSだから完了」と結論してはいけません。
