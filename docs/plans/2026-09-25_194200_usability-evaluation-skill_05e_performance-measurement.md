# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-inspection` が扱うuser-facing responsiveness / performance measurementの範囲と取得元を固定します。

performance testing framework、RUM service、独自Core Web Vitals implementationは作りません。

## 1. 本Skillが直接測定するもの

browser ownerが現在のpage/sessionから取得できる次を対象にします。

### Navigation Timing

current browserのNavigation Timing APIから取得できるnavigation関連timestamp / durationを、必要な観測条件とともに保持します。

### FCP

Paint Timing APIからFirst Contentful Paintを取得できる場合に保持します。

### user-facing interaction timing

指定actionについて、同一clock domainで次を測定できます。

- actual user-facing input event → first visible feedback
- actual user-facing input event → task-ready state
- loading start → completion state

start event / end predicateはaction前に固定します。

Playwright action call開始からのwall-clockをそのままuser response timeにはしません。

## 2. Core Web Vitals

LCP / CLS / INPを本Skillの独自algorithmで再実装しません。

Core Web Vitalsとして報告できるのは、current公式定義に従うmetricを提供する既存measurement sourceが利用できる場合だけです。

利用可能な例:

- project既存のRUM
- Chrome User Experience Report等のfield source
- projectに既に導入された `web-vitals` instrumentation
- project既存のLighthouse等、metric provenanceを確認できる測定結果

本Skillのためだけに新しいRUM service、Lighthouse runner、`web-vitals` dependencyを追加しません。

利用できない場合、Core Web Vitals欄は `measurement-unavailable` とし、Navigation Timing / FCP / user-facing interaction timingは独立して続行できます。

## 3. field / labの境界

field percentileを要求する評価を単一Playwright runから作りません。

Core Web Vitalsのgood / needs improvement / poor等のfield判定を行う場合は、metric source、population、期間、device class、percentile等をsource側の定義に従って保持します。

lab値や単一session値をfield 75th percentileへ読み替えません。

## 4. measurement input

各measurementは次を入力として持ちます。

- measurement kind
- target / action
- start event
- start acquisition method
- end event / predicate
- end acquisition method
- clock domain
- browser / environment
- viewport / device profile
- input method
- cache / navigation state等、解釈に必要な条件
- project threshold（存在する場合）
- threshold Authority ref
- external metric source ref（Core Web Vitals等を外部sourceから受け取る場合）

## 5. measurement output

各measurement:

- measurement ref
- metric / measurement label
- metric source type
- target action / region
- start event
- start acquisition method
- end event / predicate
- end acquisition method
- clock domain
- method
- value
- unit
- browser / environment
- viewport / device profile
- input method
- cache / navigation state等
- threshold value
- threshold Authority ref
- result
- evidence refs
- limitation

result:

- `within-threshold`
- `over-threshold`
- `threshold-not-defined`
- `measurement-unavailable`

## 6. deterministic runtime

`measurement.py` が担当します。

決定論化するもの:

- canonical unit
- exact elapsed calculation
- start / end clock domain一致確認
- threshold比較
- result vocabulary
- missing field検証
- external metric source metadataの構造検証

意味判断へ残すもの:

- end predicateがuser-facing feedbackとして妥当か
- project thresholdのAuthorityが今回targetへapplicableか
- observed responsivenessがUX上の懸念か
- external field metricのpopulationが今回の判断へ適用可能か

measurement helperを `test-rule-catalog.json` へ登録しません。

## 7. metric名の保護

正式なmetric定義を満たさない値へ、既存metric名を付けません。

- 任意のclick elapsedをINPと呼ばない
- raw layout shift entryの単純加算をcurrent CLSとして断定しない
- LCP candidateだけをfield LCP達成判定へ使わない
- Playwright actionability waitをpost-input responsivenessへ含めない

独自measurementは、観測内容を表す名称で出力します。

## 8. 完了条件

- Navigation Timing取得経路が固定されている
- FCP取得経路が固定されている
- user-facing interaction timingのstart / end / clock domainが固定されている
- project thresholdなしでFAIL thresholdを創作しない
- Core Web Vitalsを独自再実装しない
- Core Web Vitalsの既存measurement sourceがない場合を `measurement-unavailable` へ閉じられる
- field / labを混同しない
- measurement helperをtest rule catalogへ混ぜない
