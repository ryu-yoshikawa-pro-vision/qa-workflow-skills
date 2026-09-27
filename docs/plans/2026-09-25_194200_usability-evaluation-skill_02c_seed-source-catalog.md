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

この一覧は既知source inventoryです。全rowの再確認を実装完了条件にはしません。WCAG / ARIA / ACT / Playwright / Web timing / WCAG-EM等、current capability coverageを成立させるcore sourceは実装時に再確認します。Design System、platform guidance、一般pattern library等は、project採用、target platformへの直接適用、coverage gap解消、独立したAuthority / provenanceのいずれかで必要になった場合だけ確認・採否を閉じます。

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
| W3C-WCAG20 | WCAG 2.0 | https://www.w3.org/TR/WCAG20/ | normative standard |
| W3C-WCAG21 | WCAG 2.1 | https://www.w3.org/TR/WCAG21/ | normative standard |
| W3C-WCAG22 | WCAG 2.2 | https://www.w3.org/TR/WCAG22/ | normative standard |
| W3C-WCAG-OVERVIEW | WCAG Overview | https://www.w3.org/WAI/standards-guidelines/wcag/ | informative overview / WCAG-EM background reading |
| W3C-WCAG-QUICKREF | How to Meet WCAG 2 (Quick Reference) | https://www.w3.org/WAI/WCAG22/quickref/ | customizable supporting reference for WCAG 2.0 / 2.1 / 2.2 |
| W3C-WCAG20-UNDERSTANDING | Understanding WCAG 2.0 | https://www.w3.org/WAI/WCAG20/Understanding/ | informative guidance / W3C上でno longer maintained。2.0 requirementの正本にはしない |
| W3C-WCAG21-UNDERSTANDING | Understanding WCAG 2.1 | https://www.w3.org/WAI/WCAG21/Understanding/ | informative guidance |
| W3C-WCAG22-UNDERSTANDING | Understanding WCAG 2.2 | https://www.w3.org/WAI/WCAG22/Understanding/ | informative guidance |
| W3C-WCAG20-TECHNIQUES | Techniques for WCAG 2.0 | https://www.w3.org/WAI/WCAG20/Techniques/ | informative techniques |
| W3C-WCAG21-TECHNIQUES | Techniques for WCAG 2.1 | https://www.w3.org/WAI/WCAG21/Techniques/ | informative techniques |
| W3C-WCAG22-TECHNIQUES | Techniques for WCAG 2.2 | https://www.w3.org/WAI/WCAG22/Techniques/ | informative techniques |
| W3C-WCAG22-CONFORMANCE | Understanding Conformance | https://www.w3.org/WAI/WCAG22/Understanding/conformance | informative guidance for conformance requirements / alternate versions / partial conformance |
| W3C-WCAG2MOBILE22 | Guidance on Applying WCAG 2.2 to Mobile Applications | https://www.w3.org/TR/wcag2mobile-22/ | conditional guidance for mobile Web / responsive / touch scope。native app live automationを意味しない |
| W3C-WCAGEM2 | WCAG Evaluation Methodology 2.0 | https://www.w3.org/TR/wcag-em-2/ | conformance evaluation methodology |
| W3C-WCAGEM-REPORT-TOOL | WCAG-EM Report Tool | https://www.w3.org/WAI/eval/report-tool/ | supplementary tool reference。WCAG-EM 2.0本文と同一の成果物schemaを提供することは確認できていないため、WCAG-EM 2 schemaのAuthorityにはしない |
| W3C-WAI-ARIA12 | WAI-ARIA 1.2 | https://www.w3.org/TR/wai-aria-1.2/ | normative standard |
| W3C-ARIA-IN-HTML | ARIA in HTML | https://www.w3.org/TR/html-aria/ | normative author requirements |
| W3C-ACCNAME11 | Accessible Name and Description Computation 1.1 | https://www.w3.org/TR/accname-1.1/ | W3C Recommendation / accessible name・description computationのstable reference |
| W3C-ACCNAME12 | Accessible Name and Description Computation 1.2 | https://www.w3.org/TR/accname-1.2/ | 2026-09-27確認時点Working Draft。current draft差分確認用で、Recommendation相当のbinding sourceへ昇格しない |
| W3C-HTML-AAM10 | HTML Accessibility API Mappings 1.0 | https://www.w3.org/TR/html-aam-1.0/ | 2026-09-27確認時点Working Draft / user agent mapping reference。author requirementそのものへ昇格しない |
| W3C-APG | WAI-ARIA Authoring Practices Guide | https://www.w3.org/WAI/ARIA/apg/ | informative guidance / examples |
| W3C-ACT-FORMAT11 | ACT Rules Format 1.1 | https://www.w3.org/TR/act-rules-format/ | normative rule-format standard |
| W3C-ACT-RULES | All ACT Rules | https://www.w3.org/WAI/standards-guidelines/act/rules/ | informative test rules |
| W3C-EARL10 | Evaluation and Report Language (EARL) 1.0 Schema | https://www.w3.org/TR/EARL10-Schema/ | WCAG-EM Step 5.5 machine-readable report / W3C Note |
| W3C-JSON-LD11 | JSON-LD 1.1 | https://www.w3.org/TR/json-ld11/ | EARL JSON-LD serialization / context・IRI semantics |
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
| W3C-WCAG20 | WCAG 2.0 | https://www.w3.org/TR/WCAG20/ | general requirement checkで指定versionを使う場合のnormative source |
| W3C-WCAG21 | WCAG 2.1 | https://www.w3.org/TR/WCAG21/ | general requirement checkで指定versionを使う場合のnormative source |
| W3C-WCAG22 | WCAG 2.2 | https://www.w3.org/TR/WCAG22/ | general requirement checkで指定versionを使う場合のnormative source |
| W3C-WAI-ARIA12 | WAI-ARIA 1.2 | https://www.w3.org/TR/wai-aria-1.2/ | normative standard |
| W3C-ARIA-IN-HTML | ARIA in HTML | https://www.w3.org/TR/html-aria/ | normative author requirements |
| W3C-ACCNAME11 | Accessible Name and Description Computation 1.1 | https://www.w3.org/TR/accname-1.1/ | stable accessible name・description computation reference |
| W3C-ACCNAME12 | Accessible Name and Description Computation 1.2 | https://www.w3.org/TR/accname-1.2/ | current Working Draft。必要なcurrent差分確認時だけ利用しsource statusを保持 |
| W3C-HTML-AAM10 | HTML Accessibility API Mappings 1.0 | https://www.w3.org/TR/html-aam-1.0/ | current Working Draft / conditional user-agent mapping reference |
| W3C-ACT-FORMAT11 | ACT Rules Format 1.1 | https://www.w3.org/TR/act-rules-format/ | supported ACT implementation consistency |
| W3C-ACT-RULES | All ACT Rules | https://www.w3.org/WAI/standards-guidelines/act/rules/ | supported ACT checkのsource |
| W3C-CSS-CONDITIONAL5 | CSS Conditional Rules Module Level 5 | https://www.w3.org/TR/css-conditional-5/ | media / container size・style・scroll-state query semantics |
| W3C-CSS-VALUES4 | CSS Values and Units Module Level 4 | https://www.w3.org/TR/css-values-4/ | relative / container length、math function・computed value semantics |
| W3C-NAV-TIMING | Navigation Timing Level 2 | https://www.w3.org/TR/navigation-timing-2/ | navigation timing |
| W3C-PAINT-TIMING | Paint Timing | https://www.w3.org/TR/paint-timing/ | FCP等のpaint timing |
| WEBDEV-VITALS | Web Vitals | https://web.dev/articles/vitals | Core Web Vitals定義の補助 |
| WEBDEV-FIELD | Web Vitals field measurement best practices | https://web.dev/articles/vitals-field-measurement-best-practices | field / percentile境界 |

inspection packageはUI pattern corpusを複製しませんが、strict requirement checkとmachine observationの意味を追跡するために必要なWCAG / WAI-ARIA / ARIA in HTML / AccName / ACT sourceは自身の `references/source-catalog.md` から辿れるようにします。

AccName 1.2とHTML-AAM 1.0は2026-09-27確認時点でWorking Draftです。current browser observationの解釈やdraft差分確認に使う場合もsource statusを保持し、それだけを根拠にproject binding requirementやRecommendation相当のauthor requirementへ昇格しません。
Core Web Vitalsはcatalogへsourceを置きますが、本SkillがLCP / CLS / INPの計算実装を独自に再実装することは意味しません。詳細は `_05e_performance-measurement.md` を正本とします。

## 4. wcag-conformance-evaluation seed sources

formal WCAG evaluation packageは次を最低限catalog化します。

| Seed | Source | 公式URL | 用途 |
| --- | --- | --- | --- |
| W3C-WCAG20 | WCAG 2.0 | https://www.w3.org/TR/WCAG20/ | normative conformance target |
| W3C-WCAG21 | WCAG 2.1 | https://www.w3.org/TR/WCAG21/ | normative conformance target |
| W3C-WCAG22 | WCAG 2.2 | https://www.w3.org/TR/WCAG22/ | normative conformance target |
| W3C-WCAG-OVERVIEW | WCAG Overview | https://www.w3.org/WAI/standards-guidelines/wcag/ | WCAG-EM required background reading |
| W3C-WCAG-QUICKREF | How to Meet WCAG 2 (Quick Reference) | https://www.w3.org/WAI/WCAG22/quickref/ | WCAG-EM required background reading / supporting reference for 2.0 / 2.1 / 2.2 |
| W3C-WCAG20-UNDERSTANDING | Understanding WCAG 2.0 | https://www.w3.org/WAI/WCAG20/Understanding/ | informative / no longer maintained。2.0評価時の補助資料 |
| W3C-WCAG21-UNDERSTANDING | Understanding WCAG 2.1 | https://www.w3.org/WAI/WCAG21/Understanding/ | informative。2.1評価時の補助資料 |
| W3C-WCAG22-UNDERSTANDING | Understanding WCAG 2.2 | https://www.w3.org/WAI/WCAG22/Understanding/ | informative。2.2評価時の補助資料 |
| W3C-WCAG20-TECHNIQUES | Techniques for WCAG 2.0 | https://www.w3.org/WAI/WCAG20/Techniques/ | informative techniques |
| W3C-WCAG21-TECHNIQUES | Techniques for WCAG 2.1 | https://www.w3.org/WAI/WCAG21/Techniques/ | informative techniques |
| W3C-WCAG22-TECHNIQUES | Techniques for WCAG 2.2 | https://www.w3.org/WAI/WCAG22/Techniques/ | informative techniques |
| W3C-WCAG22-CONFORMANCE | Understanding Conformance | https://www.w3.org/WAI/WCAG22/Understanding/conformance | alternate version / accessibility support / non-interference / partial conformance guidance |
| W3C-WCAG2MOBILE22 | Guidance on Applying WCAG 2.2 to Mobile Applications | https://www.w3.org/TR/wcag2mobile-22/ | conditional source when current Web target includes responsive / touch / mobile Web behavior。native app live automationは対象外 |
| W3C-WCAGEM2 | WCAG Evaluation Methodology 2.0 | https://www.w3.org/TR/wcag-em-2/ | methodology |
| W3C-WCAGEM-REPORT-TOOL | WCAG-EM Report Tool | https://www.w3.org/WAI/eval/report-tool/ | supplementary report tool。WCAG-EM 2.0本文と同一の成果物schemaを提供することは確認できていないため、EM 2 report schemaのAuthorityにはしない |
| W3C-ACT-FORMAT11 | ACT Rules Format 1.1 | https://www.w3.org/TR/act-rules-format/ | supported ACT implementation consistency |
| W3C-ACT-RULES | All ACT Rules | https://www.w3.org/WAI/standards-guidelines/act/rules/ | informative test rules |
| W3C-WAI-ARIA12 | WAI-ARIA 1.2 | https://www.w3.org/TR/wai-aria-1.2/ | applicable normative requirements |
| W3C-ARIA-IN-HTML | ARIA in HTML | https://www.w3.org/TR/html-aria/ | applicable author requirements |
| W3C-ACCNAME11 | Accessible Name and Description Computation 1.1 | https://www.w3.org/TR/accname-1.1/ | applicable accessible name / description computation reference |
| W3C-ACCNAME12 | Accessible Name and Description Computation 1.2 | https://www.w3.org/TR/accname-1.2/ | current Working Draft。必要なcurrent差分確認時だけ利用 |
| W3C-HTML-AAM10 | HTML Accessibility API Mappings 1.0 | https://www.w3.org/TR/html-aam-1.0/ | current Working Draft / conditional user-agent mapping reference |
| W3C-ACCESSIBILITY-SUPPORT | Understanding Accessibility Support | https://www.w3.org/WAI/WCAG22/Understanding/conformance#accessibility-support | accessibility support baseline reference |
| W3C-ESSENTIAL-COMPONENTS | Essential Components of Web Accessibility | https://www.w3.org/WAI/fundamentals/components/ | WCAG-EM required expertise background reading |
| W3C-PEOPLE-USE-WEB | How People with Disabilities Use the Web | https://www.w3.org/WAI/people-use-web/ | WCAG-EM required expertise background reading |
| W3C-EASY-CHECKS | Easy Checks – A First Review of Web Accessibility | https://www.w3.org/WAI/test-evaluate/preliminary/ | preliminary evaluation / WCAG-EM background reading |
| W3C-INVOLVING-USERS | Involving Users in Evaluating Web Accessibility | https://www.w3.org/WAI/test-evaluate/involving-users/ | WCAG-EM background reading。human participant study自体は本Skill対象外 |
| W3C-SELECTING-TOOLS | Selecting Web Accessibility Evaluation Tools | https://www.w3.org/WAI/test-evaluate/tools/selecting/ | WCAG-EM background reading |
| W3C-COMBINED-EXPERTISE | Using Combined Expertise to Evaluate Web Accessibility | https://www.w3.org/WAI/test-evaluate/combined-expertise/ | WCAG-EM required expertise background reading |

WAI OverviewはWCAG-EM 2.0のresourceとしてWCAG-EM Report Toolを案内しています。一方、Report Toolのfield / export schemaがWCAG-EM 2.0本文のStep 5要件と完全に同一であることは確認できていません。そのため、toolは補助resourceとしてcatalogへ保持し、WCAG-EM 2の成果物契約はWCAG-EM 2.0本文を正本にします。tool自体もruntime dependencyにはしません。

## 5. 実装時のcatalog初期化

実装時はこのseed一覧を機械入力としてそのままコピーしません。core sourceと、project / target / coverage gapにより今回選定した条件付きsourceについてURLを再確認し、次を確定します。

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
