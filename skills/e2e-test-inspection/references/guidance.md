# E2E対象inspection 詳細判断基準

## 入力と対象決定

必須入力は、対象repo / workspaceと、詳細TC、明示E2E対象、既存E2E実装参照のいずれかです。未指定で具体対象を決める場合は、利用可能な`test-analysis`（対象: `E2E対象選定`）とTCの追跡を照合します。候補を機械的に全採用せず、既存E2E重複、データ準備、外部依存、不可逆操作を確認します。

TCが存在しない対象では、対象説明・既存test file / title path・仕様根拠で識別します。存在しないTC IDを作りません。

## 事実確認

inspectionの主な確認元は`repo`、`実対象`、`ユーザー提供情報`です。未確認事項を確認済みとして補いません。実UI確認が必要な範囲だけURLと操作能力を要求し、repo構造や既存specの確認は可能な範囲で続けます。

implementationへ渡す実装参照は対象repoの既存識別子を優先し、なければrepo-relative test file + Playwright title pathで表します。

## 安全境界

指定URLと必要なOAuth / SSO遷移を区別し、指定外環境への切替を許可しません。データ削除、メール、外部通知、決済、権限変更、ロック等は明示許可がない限り該当対象をブロックします。trace、HTML report、network、storageState等は機密情報を含み得るため、保護・共有制約を記録します。

## 鮮度

branch / commit / working treeと実対象確認日時を残します。implementation開始時は関連repo構造・実対象の変更を軽量確認し、実装判断に影響する差分があるときだけ該当範囲を再inspectionします。
