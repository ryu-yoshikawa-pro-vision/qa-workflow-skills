---
name: ui-target-analysis
description: UIの構造・操作・画面状態・ナビゲーションを、仕様Authorityと分けて分析・更新する。「画面の階層・領域・操作対象・遷移・UI状態の整理」「既存ui-target-v1の読取・移行」「人間が作業用copyで編集したUI差分の検証」を求められたら、自分で整理する前に必ずこのSkillを読み込む。
---

# UI対象分析

## 実行契約

1. UI要素、操作、表示状態、画面遷移の正本だけを扱います。期待挙動、業務状態、認可、仕様Authority、AC、UNKNOWNの解決は`spec-analysis`へ戻します。
2. UI source、対象機能、source revision、Project Contextで合意された正本・編集範囲が特定できない場合は推測せず、読取できる独立範囲を分析して不足範囲をblockedにします。
3. UIの構造・操作・状態は画面観測やrepositoryの補助情報から記述できますが、それらを仕様上の期待挙動へ昇格させません。期待値には`spec-analysis`のcurrent Authorityを参照します。
4. 既存`ui-target-v1`を受け取った場合は`00`〜`09`、条件付きfile、stable ID、Manifest、CHANGELOG、scope readiness、Machine Entityを維持します。新形式へ物理移行しません。
5. 既存packageの正本更新は`spec-analysis/scripts/ui_target_package.py materialize`だけを使います。人間編集helperは差分とmaterialize requestを準備するだけで、正本を書き込みません。
6. 変更案は有効な元snapshot、現行revision、UI ownerの意味確認、編集可能範囲、根拠refと照合します。手入力ID、行削除だけの廃止、generated/control fileの変更、Authorityの無承認変更、意味衝突を受理しません。
7. `ui-target-v1`の一つのpackageにはUI ownerとspec ownerのデータが同居します。package全体のwriterは一つのままにし、各ownerは自身が所有する変更だけを意味確認します。
8. feature IDからUI scopeへの参照は、`feature-analysis`が保存した実artifact ref／revisionから受け取ります。IDや名前の類似で関連を推測しません。索引はpackage revisionとsource revisionから都度導出し、保存済みの二次一覧を作りません。
9. 保存先のCAS、履歴readback、承認者の認証またはruntime owner検証を確認できない場合、helper fixtureの成功を実接続の成功とみなさず、対象の正式保存・承認をblockedにします。
10. 最終出力前に`references/guidance.md`と`references/human-editing.md`の品質確認を適用します。未確認の変更、scope、参照、失敗・再開条件は未確認のまま記録します。

## 入力・出力

- **入力**: currentなUI sourceとrevision、対象scope、既存`ui-target-v1`のref・version・snapshot、必要な`feature-analysis`の機能IDとsource ref、Project Contextの配置・編集合意、人間の作業用branch／copyとそのbase。
- **処理**: UI構造・操作・画面表示状態・ナビゲーションを意味単位で識別し、仕様Authorityへの参照と人間が編集する正本位置を示します。人間編集はownerが差分を検証し、採用分だけ既存writerの更新入力へ変換します。
- **出力**: UI分析、source・feature・scope・stable IDの参照、current package revision、編集差分と採否、生成されたmaterialize requestまたはblocked理由、独立readback結果。

## 停止条件

- currentな元snapshotや保存先revisionを検証できない
- 作業copyの由来、scope、owner、許可された編集範囲を確認できない
- Authority・source・関連stable ID・廃止根拠に意味上の競合がある
- canonical rootが直接変更され、独立した有効baselineを検証できない
- 必要な承認・保存先native CAS・readback・owner runtimeが利用できない

個別scopeだけに影響する停止は局所化し、独立して根拠が揃ったscopeを継続します。

## リソース

- UI分析とAuthority境界: `references/guidance.md`
- 人間編集、差分抽出、競合・失敗再開: `references/human-editing.md`
- 人が確認する分析記録: `assets/output-template.md`
- `ui-target-v1`のreader/writer: sibling Skill `spec-analysis/scripts/ui_target_package.py`（同一repository runtimeでのみ利用。未配置時は正本更新をblockedにする）
- 決定論的差分helper: `scripts/human_editing.py`
