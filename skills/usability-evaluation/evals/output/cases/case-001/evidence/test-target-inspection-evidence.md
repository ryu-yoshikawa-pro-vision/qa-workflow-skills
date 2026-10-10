# テスト対象資料 — 保存済みfixture evidence

## 確認情報

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 | API token settings — remove dialog fixture | repository fixture |
| 対象URL / origin | http://127.0.0.1:8765/skills/usability-evaluation/evals/output/cases/case-001/dialog-focus-escape.html | local Playwright browser |
| version / build | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | saved fixture |
| 確認日時 | 2026-09-28T10:49:56+09:00 | Playwright CLI capture |
| role / 権限 | local fixture visitor | fixture |
| viewport | 1280x720 CSS px | browser |
| locale | en-US | fixture |
| feature flag | none | fixture |
| テストデータ条件 | test API token label only; no real token | fixture |
| 既存成果物参照 | none | fixture |
| 更新元revision / content identity | none | fixture |
| 永続保存要求 | いいえ | evaluation request |

## 画面 / 領域

| 対象キー | 画面 / 領域 | 到達経路 | 確認状態 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- |
| target-001 | API token settings | repository fixture direct load | 確認済み | local Chromium, 1280x720, en-US | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |

## UI要素

| 要素キー | 対象キー | UI要素 | 識別情報 | 操作可能性 / 状態 | 確認状態 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| element-001 | target-001 | Create API token button | `button#open` | 操作可能、dialogの背後に表示 | 確認済み | local Chromium, 1280x720 | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |
| element-002 | target-001 | Remove API token dialog | `section#dialog`, role=dialog, aria-modal=true | 開いた状態 | 確認済み | local Chromium, 1280x720 | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |
| element-003 | target-001 | Remove API token button | `.danger` | 操作可能、唯一のdialog内操作 | 確認済み | local Chromium, 1280x720 | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |

## 状態

| 状態キー | 対象キー | 状態 | 観測内容 | 到達条件 | 確認状態 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| state-001 | target-001 | Remove API token dialog open | Named modal dialog and description are present; dialog has one destructive action | fixture initial dialog state | 確認済み | local Chromium, 1280x720 | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |
| state-002 | target-001 | Keyboard focus escaped | After two Tab presses, `Create API token` behind the open dialog was active | keyboard trace from state-001 | 確認済み | local Chromium, keyboard | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |
| state-003 | target-001 | Escape did not dismiss dialog | Escape was pressed; dialog remained and background trigger remained active | keyboard trace from state-002 | 確認済み | local Chromium, keyboard | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |

## 操作・ふるまい

| 対象キー | 要素キー | 開始状態 | 操作 | 実対象の反応 / 遷移 | 到達状態 | 確認状態 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target-001 | element-002 | state-001 | Tab twice | Focus moved to the background `Create API token` button while dialog remained open | state-002 | 確認済み | local Chromium keyboard | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |
| target-001 | element-002 | state-002 | Escape | Dialog remained open; background trigger remained active | state-003 | 確認済み | local Chromium keyboard | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |

## 構造証跡

| 対象キー | 状態キー | 取得範囲 | 証跡参照 | 証跡revision / content identity | 前回証跡参照 | 前回証跡revision / content identity | 差分概要 | 証跡保存・比較の制約 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target-001 | state-001 | dialog role/name/description and visible controls | dialog-accessibility.yml | sha256:cb9a8a41b010ef96c6ccda7bd883d9faf9cef6480748c7c97573ba1e13cbb6a1 | none | none | initial saved evidence | CLI accessibility snapshot is not a screen-reader transcript | local Chromium | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |
| target-001 | state-003 | page-level accessible tree after keyboard interaction | dialog-keyboard-trace.md | sha256:c63fa2f3cdc6a50ff3ec0d72510cf6b98f168f047b5b1484ea2bd63f8552527c | none | none | focus is on background trigger while dialog remains open | browser snapshot only; no screen reader claim | local Chromium keyboard | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 |

## 視覚情報

| 対象キー | 要素キー / 状態キー | 確認観点 | 画像で観測した事実 | 画像参照 | 確認状態 | 確認条件 | 確認version / build | 確認日時 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target-001 | element-002 / state-001 | dialog placement and action visibility | Dialog is centered and its destructive action is visible; screenshot does not show keyboard focus | dialog-focus-escape.png (sha256:cd4399f821d353c9f8d99db1f04e587a017f87e4debeecca2049a8d5afe90c3f) | 確認済み | 1280x720 | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf | 2026-09-28T10:49:56+09:00 | Visual evidence only |

## データ・権限依存

| 対象キー | 要素キー / 状態キー | 条件 | 実対象で確認した差異 | 確認状態 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 既存テスト実装との対応（任意）

| 対象キー | 要素キー | 種別 | repo参照 | 関係 | 確認revision |
| --- | --- | --- | --- | --- | --- |
| target-001 | element-002 | fixture | skills/usability-evaluation/evals/output/cases/case-001/dialog-focus-escape.html | source of captured browser state | sha256:5719ebe78a17192ec8c6b2169a7761d21df5749c55a88cfd6210798d612906cf |

## 未確認 / 確認不能

| 対象 | 状態 | 理由 | 後続への影響 |
| --- | --- | --- | --- |
| real users / assistive technology | 未確認 | canonical repository fixture does not include participants or an AT environment | Do not infer user frequency or formal conformance |

## 副作用・cleanup

| 副作用scope | 1回の定義 | 最大回数 | 準備回数 | 観測操作回数 | cleanup回数 | 累計実施回数 | cleanup対象 / 方法 | cleanup結果 | 残存状態 | 根拠 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |

## 今回の更新

| 対象種別 | 対象キー | 要素キー / 状態キー | 更新区分 | 内容 | 確認条件 | 確認version / build | 確認日時 |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 保存結果

| 保存先 | 更新元revision / content identity | 更新方式 | 保存状態 | 保存後revision / content identity | 競合・制約 / 理由 | 確認元 |
| --- | --- | --- | --- | --- | --- | --- |
