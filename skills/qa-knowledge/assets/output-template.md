# QA Knowledge decision / entry output

正規machine artifactはMarkdown内にJSON code blockをちょうど1つ置きます。owner routingだけなら`action: "route_to_owner"`、knowledge保存ならactionと`entry`に`assets/entry-template.md`のstructured identity、provenance、currentness dependency、適用scope、stateを含めます。CAS / create-if-absent / complete root listingを確認できない保存は`action: "blocked"`とし、別refの保存やsemantic auto-mergeに進みません。

```json
{
  "action": "route_to_owner | create | update | revalidation | replacement | lookup | history | blocked",
  "owner_skill": null,
  "entry": null,
  "currentness_status": "unresolved",
  "storage": {}
}
```
