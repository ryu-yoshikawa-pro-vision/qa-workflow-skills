# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、実装時にSkill packageの `references/source-catalog.md` へ登録するseed sourceを、2026-09-26時点で確認できている公式URL付きで固定します。

source本文をこのPlanへ複製することが目的ではありません。

実装時は、

- `skills/usability-evaluation/references/source-catalog.md`
- `skills/usability-inspection/references/source-catalog.md`
- `skills/wcag-conformance-evaluation/references/source-catalog.md`

へ、source名、canonical URL、publisher、category、source status、適用範囲、checked_at、採用状態を保持します。

Plan内のseed keyは実装時の `SRC-...` IDではありません。package-local IDは実装時に決定論的scriptで採番します。

## 1. source-catalogの役割

`source-catalog.md` はreference本文そのものではなく、次を追跡する索引です。

- 何をsourceとして利用しているか
- canonical URL
- source owner / publisher
- standard / methodology / Design System / pattern library等のcategory
- normative / informative / advisory等のsource上の位置づけ
- projectへのbinding可否は別判断であること
- public / restricted / paid等のaccess state
- current / draft / proposed / archived等のstatus
- checked_at
- どのreference entry / inspection methodologyへ使ったか

catalogに載っているだけで、そのsource全体をbundled corpusへ収録済みとは扱いません。

## 2. usability-evaluation seed sources

### W3C / WAI

| Seed | Source | 公式URL | 既定の扱い |
| --- | --- | --- | --- |
| W3C-WCAG22 | WCAG 2.2 | https://www.w3.org/TR/WCAG22/ | normative standard |
| W3C-WCAG22-UNDERSTANDING | Understanding WCAG 2.2 | https://www.w3.org/WAI/WCAG22/Understanding/ | informative guidance |
| W3C-WCAG22-TECHNIQUES | Techniques for WCAG 2.2 | https://www.w3.org/WAI/WCAG22/Techniques/ | informative techniques |
| W3C-WCAGEM2 | WCAG Evaluation Methodology 2.0 | https://www.w3.org/TR/wcag-em-2/ | conformance evaluation methodology |
| W3C-WCAGEM-REPORT-TOOL | WCAG-EM Report Tool | https://www.w3.org/WAI/eval/report-tool/ | supplementary tool reference。2026-09-26確認時点のWAI Overviewではcurrent toolはWCAG-EM 1向け。WCAG-EM 2 schemaのAuthorityにはしない |
| W3C-WAI-ARIA12 | WAI-ARIA 1.2 | https://www.w3.org/TR/wai-aria-1.2/ | normative standard |
| W3C-ARIA-IN-HTML | ARIA in HTML | https://www.w3.org/TR/html-aria/ | normative author requirements |
| W3C-APG | WAI-ARIA Authoring Practices Guide | https://www.w3.org/WAI/ARIA/apg/ | informative guidance / examples |
| W3C-ACT-FORMAT11 | ACT Rules Format 1.1 | https://www.w3.org/TR/act-rules-format/ | normative rule-format standard |
| W3C-ACT-RULES | All ACT Rules | https://www.w3.org/WAI/standards-guidelines/act/rules/ | informative test rules |
| W3C-ACT-OVERVIEW | Accessibility Conformance Testing Overview | https://www.w3.org/WAI/standards-guidelines/act/ | informative overview |

WCAG-EM 2.0は2026-07-23公開のW3C Group Noteとして、WCAG conformance evaluationを明示要求された経路のmethodologyに使用します。一般的なpage inspectionへ無条件適用しません。

ACT Rulesはinformativeです。catalogへsourceとして保持しても、全ruleを本Skillで実装したとは扱いません。

### 公開Design System / platform guidance

| Seed | Source | 公式URL | 既定の扱い |
| --- | --- | --- | --- |
| GOVUK-DS | GOV.UK Design System | https://design-system.service.gov.uk/ | advisory / project採用時はAuthority候補 |
| GOVUK-COMPONENTS | GOV.UK Components | https://design-system.service.gov.uk/components/ | advisory |
| GOVUK-PATTERNS | GOV.UK Patterns | https://design-system.service.gov.uk/patterns/ | advisory |
| USWDS | U.S. Web Design System | https://designsystem.digital.gov/ | advisory / project採用時はAuthority候補 |
| USWDS-COMPONENTS | USWDS Components | https://designsystem.digital.gov/components/overview/ | advisory |
| USWDS-PATTERNS | USWDS Patterns | https://designsystem.digital.gov/patterns/ | advisory |
| CARBON | Carbon Design System | https://carbondesignsystem.com/ | advisory / project採用時はAuthority候補 |
| CARBON-COMPONENTS | Carbon Components | https://carbondesignsystem.com/components/overview/components/ | advisory |
| CARBON-PATTERNS | Carbon Patterns | https://carbondesignsystem.com/patterns/overview/ | advisory |
| FLUENT2 | Fluent 2 Design System | https://fluent2.microsoft.design/ | advisory / platform-specific |
| ATLASSIAN-DS | Atlassian Design System | https://atlassian.design/ | advisory / project-specific |
| SPECTRUM | Adobe Spectrum | https://spectrum.adobe.com/ | advisory / project-specific |
| PRIMER | GitHub Primer | https://primer.style/ | advisory / project-specific |
| SLDS2 | Salesforce Lightning Design System 2 | https://www.lightningdesignsystem.com/ | advisory / project-specific |
| SAP-FIORI | SAP Fiori Design | https://experience.sap.com/fiori-design-web/ | advisory / platform-specific |
| GNOME-HIG | GNOME Human Interface Guidelines | https://developer.gnome.org/hig/ | advisory / platform-specific |
| APPLE-HIG | Apple Human Interface Guidelines | https://developer.apple.com/design/human-interface-guidelines/ | advisory / platform-specific |
| MATERIAL3 | Material Design 3 | https://m3.material.io/ | advisory / platform-specific |
| SHOPIFY-POLARIS | Shopify Polaris references | https://shopify.dev/docs/api/polaris | advisory / project-specific |

Design System固有規約は、そのDesign Systemをprojectが採用している、または対象platform / productが直接該当する場合だけbinding候補にできます。catalog登録だけで一般Web UIへbindingにしません。

### usability / interaction principles / pattern libraries

| Seed | Source | 公式URL | 既定の扱い |
| --- | --- | --- | --- |
| ISO-9241-11 | ISO 9241-11:2018 | https://www.iso.org/standard/63500.html | usability definitions / concepts。公開metadata / previewを超える本文はreference-only |
| ISO-9241-110 | ISO 9241-110:2020 | https://www.iso.org/standard/75258.html | interaction principles。公開metadata / previewを超える本文はreference-only |
| ISO-9241-112 | ISO 9241-112:2025 | https://www.iso.org/standard/87518.html | information presentation principles。公開metadata / previewを超える本文はreference-only |
| ISO-9241-115 | ISO 9241-115:2024 | https://www.iso.org/standard/80773.html | user-system interaction / UI / navigation guidance。公開metadata / previewを超える本文はreference-only |
| ISO-9241-171 | ISO 9241-171:2025 | https://www.iso.org/standard/86308.html | software accessibility。公開metadata / previewを超える本文はreference-only |
| NNG-HEURISTICS | NN/g 10 Usability Heuristics | https://www.nngroup.com/articles/ten-usability-heuristics/ | advisory heuristic |
| NNG-HEURISTIC-EVAL | NN/g How to Conduct a Heuristic Evaluation | https://www.nngroup.com/articles/how-to-conduct-a-heuristic-evaluation/ | methodology |
| UI-PATTERNS | UI-Patterns.com Design Patterns | https://ui-patterns.com/patterns | advisory pattern library |
| WELIE | Welie Interaction Design Pattern Library | https://www.welie.com/patterns/ | advisory pattern library / historical context注意 |
| SOCIOMEDIA | ソシオメディア UIデザインパターン | https://www.sociomedia.co.jp/category/uidesignpatterns | advisory pattern library |

古いpattern libraryは公開されていること自体をcurrent best practiceの証明にせず、checked_at、年代、platform前提、current sourceとの整合をreference entryへ残します。

## 3. usability-inspection seed sources

inspection packageにはUI pattern本文を複製せず、live inspection / measurement / browser behaviorの契約に使うsourceだけをcatalog化します。

| Seed | Source | 公式URL | 用途 |
| --- | --- | --- | --- |
| PW-EMULATION | Playwright Emulation | https://playwright.dev/docs/emulation | viewport / device / locale / isMobile等 |
| PW-BROWSER | Playwright Browser API | https://playwright.dev/docs/api/class-browser | BrowserContext / hasTouch / isMobile / userAgent / viewport |
| PW-ACTIONABILITY | Playwright Actionability | https://playwright.dev/docs/actionability | auto-wait境界 |
| PW-LOCATORS | Playwright Locators | https://playwright.dev/docs/locators | locator利用境界 |
| W3C-ACT-RULES | All ACT Rules | https://www.w3.org/WAI/standards-guidelines/act/rules/ | supported ACT checkのsource |
| W3C-NAV-TIMING | Navigation Timing Level 2 | https://www.w3.org/TR/navigation-timing-2/ | navigation timing |
| W3C-PAINT-TIMING | Paint Timing | https://www.w3.org/TR/paint-timing/ | FCP等のpaint timing |
| WEBDEV-VITALS | Web Vitals | https://web.dev/articles/vitals | Core Web Vitals定義の補助 |
| WEBDEV-FIELD | Web Vitals field measurement best practices | https://web.dev/articles/vitals-field-measurement-best-practices | field / percentile境界 |

Core Web Vitalsはcatalogへsourceを置きますが、本SkillがLCP / CLS / INPの計算実装を独自に再実装することは意味しません。詳細は `_05e_performance-measurement.md` を正本とします。

## 4. wcag-conformance-evaluation seed sources

formal WCAG evaluation packageは次を最低限catalog化します。

| Seed | Source | 公式URL | 用途 |
| --- | --- | --- | --- |
| W3C-WCAG22 | WCAG 2.2 | https://www.w3.org/TR/WCAG22/ | normative conformance target |
| W3C-WCAGEM2 | WCAG Evaluation Methodology 2.0 | https://www.w3.org/TR/wcag-em-2/ | methodology |
| W3C-WCAGEM-REPORT-TOOL | WCAG-EM Report Tool | https://www.w3.org/WAI/eval/report-tool/ | supplementary report tool。2026-09-26確認時点ではWCAG-EM 1向け。EM 2 report schemaのAuthorityにはしない |
| W3C-ACT-FORMAT11 | ACT Rules Format 1.1 | https://www.w3.org/TR/act-rules-format/ | supported ACT implementation consistency |
| W3C-ACT-RULES | All ACT Rules | https://www.w3.org/WAI/standards-guidelines/act/rules/ | informative test rules |
| W3C-WAI-ARIA12 | WAI-ARIA 1.2 | https://www.w3.org/TR/wai-aria-1.2/ | applicable normative requirements |
| W3C-ARIA-IN-HTML | ARIA in HTML | https://www.w3.org/TR/html-aria/ | applicable author requirements |
| W3C-ACCESSIBILITY-SUPPORT | Understanding Accessibility Support | https://www.w3.org/WAI/WCAG22/Understanding/conformance#accessibility-support | accessibility support baseline reference |
| W3C-ESSENTIAL-COMPONENTS | Essential Components of Web Accessibility | https://www.w3.org/WAI/fundamentals/components/ | WCAG-EM required expertise background reading |
| W3C-PEOPLE-USE-WEB | How People with Disabilities Use the Web | https://www.w3.org/WAI/people-use-web/ | WCAG-EM required expertise background reading |
| W3C-EASY-CHECKS | Easy Checks – A First Review of Web Accessibility | https://www.w3.org/WAI/test-evaluate/preliminary/ | preliminary evaluation / WCAG-EM background reading |
| W3C-INVOLVING-USERS | Involving Users in Evaluating Web Accessibility | https://www.w3.org/WAI/test-evaluate/involving-users/ | WCAG-EM background reading。human participant study自体は本Skill対象外 |
| W3C-SELECTING-TOOLS | Selecting Web Accessibility Evaluation Tools | https://www.w3.org/WAI/test-evaluate/tools/selecting/ | WCAG-EM background reading |
| W3C-COMBINED-EXPERTISE | Using Combined Expertise to Evaluate Web Accessibility | https://www.w3.org/WAI/test-evaluate/combined-expertise/ | WCAG-EM required expertise background reading |

2026-09-26確認時点でWAI Overviewはcurrent WCAG-EM Report ToolをWCAG-EM 1向けとしています。リンクは既知の公式resourceとしてcatalogへ保持しますが、WCAG-EM 2のfield / JSON schemaを決めるAuthorityにはしません。WCAG-EM 2成果物はWCAG-EM 2.0本文、とくにStep 5.1を正本にします。tool自体もruntime dependencyにはしません。

## 5. 実装時のcatalog初期化

実装時はこのseed一覧を機械入力としてそのままコピーするのではなく、各URLを再確認して次を確定します。

- canonical URL
- current status
- public access
- checked_at
- adopted / reference-only / unavailable / replaced
- source-specific lifecycle
- license / terms上の扱い

redirect等でcanonical URLが変わった場合はcurrent URLをcatalogへ記録し、本PlanのURLとの差分を実装記録へ残します。

catalog / coverageの物理Markdown形式は `_02d_reference-artifact-schema.md` を正本とします。

このseed一覧にないsourceは、`_02a_source-acquisition-and-coverage.md` の能力coverageで不足が確認された場合に追加調査します。
