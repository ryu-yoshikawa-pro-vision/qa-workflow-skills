// The existing Playwright CLI evaluates this file as a parenthesized function expression.
// prettier-ignore
async (page) => {
  const requestSlot = "__usabilityInspectionFixedWcagProbeRequest";
  const currentDocumentIdentity = async () =>
    page.evaluate(async () => {
      try {
        if (!globalThis.crypto?.subtle || typeof TextEncoder === "undefined") return null;
        const identityKeySlot = Symbol.for("qa-workflow-skills.document-identity-key.v1");
        let keyPromise = window[identityKeySlot];
        if (!keyPromise) {
          keyPromise = crypto.subtle.generateKey({ name: "HMAC", hash: "SHA-256" }, false, [
            "sign",
          ]);
          Object.defineProperty(window, identityKeySlot, {
            value: keyPromise,
            enumerable: false,
            configurable: false,
            writable: false,
          });
        }
        const key = await keyPromise;
        const signature = await crypto.subtle.sign(
          "HMAC",
          key,
          new TextEncoder().encode(location.href),
        );
        const hex = Array.from(new Uint8Array(signature), (byte) =>
          byte.toString(16).padStart(2, "0"),
        ).join("");
        return `hmac-sha256:${hex}`;
      } catch {
        return null;
      }
    });
  const initialDocumentIdentity = await currentDocumentIdentity();
  const request = await page.evaluate((slot) => {
    const value = window[slot];
    delete window[slot];
    return value;
  }, requestSlot);

  const requestFields = [
    "request_kind",
    "observation_request_ref",
    "request_signature",
    "criterion_evaluation_ref",
    "procedure_execution_ref",
    "machine_probe_key",
    "sample_ref",
    "variation_ref",
    "process_ref",
    "requirement_ref",
    "currentness_dependency",
    "target_identity",
    "required_browser_capability",
  ].sort();
  const identityFields = [
    "observation_request_ref",
    "request_signature",
    "criterion_evaluation_ref",
    "procedure_execution_ref",
    "machine_probe_key",
    "sample_ref",
    "variation_ref",
    "process_ref",
    "requirement_ref",
    "target_identity",
    "currentness_dependency",
  ];
  const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
  const validText = (value) => typeof value === "string" && value.trim().length > 0;
  const identityPattern = /^hmac-sha256:[0-9a-f]{64}$/u;
  const fingerprintPattern = /^sha256:[0-9a-f]{64}$/u;
  const evidenceRefs = [];
  const identity = isObject(request)
    ? Object.fromEntries(
        identityFields.map((key) => [
          key,
          key === "target_identity" && !identityPattern.test(request[key] || "")
            ? null
            : key === "currentness_dependency" &&
                (!isObject(request[key]) ||
                  Object.keys(request[key]).sort().join("\u0000") !==
                    ["sample_identity_fingerprint", "variation_identity_fingerprint"]
                      .sort()
                      .join("\u0000") ||
                  !fingerprintPattern.test(request[key].sample_identity_fingerprint || "") ||
                  !fingerprintPattern.test(request[key].variation_identity_fingerprint || ""))
              ? null
              : request[key],
        ]),
      )
    : {};
  const fixedProbeKeys = new Set([
    "mp-audio-autoplay-run",
    "mp-change-trigger-run",
    "mp-component-semantics",
    "mp-computed-color-context",
    "mp-control-value-history",
    "mp-document-language",
    "mp-document-title",
    "mp-error-scenario-run",
    "mp-focus-appearance-evidence",
    "mp-focus-obscuring-geometry",
    "mp-focus-sequence-run",
    "mp-form-control-inventory",
    "mp-heading-label-inventory",
    "mp-hover-focus-content-run",
    "mp-keyboard-functionality-run",
    "mp-link-inventory",
    "mp-media-inventory",
    "mp-moving-updating-inventory",
    "mp-multipage-signature",
    "mp-neighbor-geometry",
    "mp-nontext-content-inventory",
    "mp-orientation-run",
    "mp-part-language-inventory",
    "mp-pointer-interaction-run",
    "mp-purpose-metadata",
    "mp-reflow-run",
    "mp-resize-text-run",
    "mp-sequence-inventory",
    "mp-shortcut-inventory",
    "mp-status-candidate-inventory",
    "mp-structure-inventory",
    "mp-target-geometry",
    "mp-text-presentation-values",
    "mp-text-spacing-run",
    "mp-timer-inventory",
    "mp-viewport-state",
  ]);
  const failure = async (status, limitation, limitationCode = null) => ({
    ...identity,
    status,
    current_document_identity: await currentDocumentIdentity(),
    evidence_refs: evidenceRefs,
    limitation,
    ...(limitationCode ? { limitation_code: limitationCode } : {}),
  });

  if (
    !isObject(request) ||
    Object.keys(request).sort().join("\u0000") !== requestFields.join("\u0000") ||
    request.request_kind !== "wcag-machine-probe" ||
    !fixedProbeKeys.has(request.machine_probe_key) ||
    request.required_browser_capability !== request.machine_probe_key ||
    identityFields.some((key) => !Object.prototype.hasOwnProperty.call(request, key)) ||
    !identityPattern.test(request.target_identity || "") ||
    !isObject(request.currentness_dependency) ||
    Object.keys(request.currentness_dependency).sort().join("\u0000") !==
      ["sample_identity_fingerprint", "variation_identity_fingerprint"].sort().join("\u0000") ||
    !fingerprintPattern.test(request.currentness_dependency.sample_identity_fingerprint || "") ||
    !fingerprintPattern.test(request.currentness_dependency.variation_identity_fingerprint || "")
  ) {
    return failure("blocked", "typed fixed WCAG machine probe request is invalid");
  }
  if (!initialDocumentIdentity) {
    return failure("blocked", "browser cannot create an in-memory keyed current-document identity");
  }
  if (initialDocumentIdentity !== request.target_identity) {
    return failure("blocked", "typed WCAG machine probe request is stale for the current document");
  }

  const resultFor = async (observation) => ({
    ...identity,
    status: observation.status,
    current_document_identity: await currentDocumentIdentity(),
    evidence_refs: evidenceRefs,
    ...(observation.value ? { value: observation.value } : {}),
    ...(observation.limitation ? { limitation: observation.limitation } : {}),
    ...(observation.limitation_code ? { limitation_code: observation.limitation_code } : {}),
  });

  const captureFocusSequence = async (maxSteps) => {
    const originalFocus = await page.evaluateHandle(() => document.activeElement);
    const originalScroll = await page.evaluate(() => ({ x: scrollX, y: scrollY }));
    const sequence = [];
    const seen = new Set();
    let cycleDetected = false;
    let captureError = null;
    try {
      const focusableCount = await page.evaluate(() => {
        const selector = "a[href],button,input,select,textarea,[tabindex]:not([tabindex='-1'])";
        return Array.from(document.querySelectorAll(selector)).filter((element) => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return (
            !element.disabled &&
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            rect.width > 0 &&
            rect.height > 0
          );
        }).length;
      });
      const limit = Math.min(Math.max(1, maxSteps), Math.max(1, focusableCount + 1), 64);
      for (let index = 0; index < limit; index++) {
        await page.keyboard.press("Tab");
        const row = await page.evaluate(() => {
          const element = document.activeElement;
          if (!element || element === document.body || element === document.documentElement) {
            return {
              target_ref: null,
              role: "document",
              tag_name: "body",
              visible: true,
              rect_css_px: null,
              outline_style: null,
              outline_width: null,
              outline_color: null,
              border: null,
              background_color: null,
              background_image_present: false,
              box_shadow_layer_count: 0,
              fixed_overlay_overlap_refs: [],
            };
          }
          const pathFor = (node) => {
            const parts = [];
            let current = node;
            while (current && current.nodeType === Node.ELEMENT_NODE) {
              const parent = current.parentElement;
              const peers = parent
                ? Array.from(parent.children).filter((peer) => peer.tagName === current.tagName)
                : [current];
              parts.push(
                current.tagName.toLowerCase() +
                  ":nth-of-type(" +
                  (peers.indexOf(current) + 1) +
                  ")",
              );
              current = parent;
            }
            return parts.reverse().join(" > ");
          };
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          const splitShadows = (value) => {
            let depth = 0;
            let count = value && value !== "none" ? 1 : 0;
            for (const character of value || "") {
              if (character === "(") depth += 1;
              else if (character === ")") depth = Math.max(0, depth - 1);
              else if (character === "," && depth === 0) count += 1;
            }
            return count;
          };
          const overlays = Array.from(document.querySelectorAll("body *"))
            .filter((candidate) => {
              if (candidate === element || candidate.contains(element)) return false;
              const candidateStyle = getComputedStyle(candidate);
              if (
                !["fixed", "sticky"].includes(candidateStyle.position) ||
                candidateStyle.display === "none" ||
                candidateStyle.visibility === "hidden" ||
                Number(candidateStyle.opacity) <= 0
              )
                return false;
              const overlayRect = candidate.getBoundingClientRect();
              return (
                overlayRect.width > 0 &&
                overlayRect.height > 0 &&
                overlayRect.left < rect.right &&
                overlayRect.right > rect.left &&
                overlayRect.top < rect.bottom &&
                overlayRect.bottom > rect.top
              );
            })
            .slice(0, 20)
            .map((candidate) => "dom-overlay:" + pathFor(candidate));
          return {
            target_ref: "focused-element:" + pathFor(element),
            role: element.getAttribute("role") || element.tagName.toLowerCase(),
            tag_name: element.tagName.toLowerCase(),
            visible:
              style.display !== "none" &&
              style.visibility !== "hidden" &&
              rect.width > 0 &&
              rect.height > 0,
            rect_css_px: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
            outline_style: style.outlineStyle,
            outline_width: style.outlineWidth,
            outline_color: style.outlineColor,
            border: {
              width: style.borderWidth,
              style: style.borderStyle,
              color: style.borderColor,
              radius: style.borderRadius,
            },
            background_color: style.backgroundColor,
            background_image_present: style.backgroundImage !== "none",
            box_shadow_layer_count: splitShadows(style.boxShadow),
            fixed_overlay_overlap_refs: overlays,
          };
        });
        if (row.target_ref && seen.has(row.target_ref)) {
          cycleDetected = true;
          break;
        }
        if (row.target_ref) seen.add(row.target_ref);
        sequence.push({ state_index: sequence.length, ...row });
        if (row.target_ref === null) break;
      }
    } catch (error) {
      captureError = "fixed keyboard focus sequence could not be captured";
    } finally {
      try {
        await originalFocus.evaluate((element) => {
          if (element && element.isConnected && typeof element.focus === "function")
            element.focus();
        });
        await page.evaluate((position) => window.scrollTo(position.x, position.y), originalScroll);
      } catch {
        captureError = captureError || "focus restoration could not be verified";
      }
      await originalFocus.dispose().catch(() => {});
    }
    return {
      sequence,
      cycle_detected: cycleDetected,
      capture_error: captureError,
      restored_focus: captureError === null,
    };
  };

  if (
    request.machine_probe_key === "mp-focus-sequence-run" ||
    request.machine_probe_key === "mp-keyboard-functionality-run"
  ) {
    const trace = await captureFocusSequence(64);
    const value = {
      schema: "wcag-keyboard-focus-sequence-v1",
      ...trace,
      ...(request.machine_probe_key === "mp-keyboard-functionality-run"
        ? {
            declared_flow_outcome: null,
            observation_completeness: {
              state: "partial",
              reason: "declared-flow-not-materialized",
            },
          }
        : {}),
    };
    if (request.machine_probe_key === "mp-focus-sequence-run" && trace.capture_error === null) {
      return resultFor({ status: "ok", value });
    }
    if (
      request.machine_probe_key === "mp-keyboard-functionality-run" &&
      trace.capture_error === null
    ) {
      return resultFor({
        status: "incomplete",
        value,
        limitation:
          "keyboard reachability trace is fixed and complete, but the typed request does not contain a declared functionality flow or expected outcome",
      });
    }
    return resultFor({
      status: "blocked",
      value,
      limitation: trace.capture_error || "fixed keyboard focus sequence did not complete",
    });
  }

  if (request.machine_probe_key === "mp-focus-obscuring-geometry") {
    const trace = await captureFocusSequence(1);
    if (
      trace.capture_error !== null ||
      trace.sequence.length === 0 ||
      trace.sequence[0].target_ref === null
    ) {
      return resultFor({
        status: "blocked",
        value: { schema: "wcag-focus-obscuring-geometry-v1", ...trace },
        limitation:
          trace.capture_error || "fixed keyboard operation did not resolve a focusable target",
      });
    }
    return resultFor({
      status: "ok",
      value: {
        schema: "wcag-focus-obscuring-geometry-v1",
        focused_target: trace.sequence[0],
        viewport: await page.evaluate(() => ({
          width_css_px: innerWidth,
          height_css_px: innerHeight,
        })),
      },
    });
  }

  if (request.machine_probe_key === "mp-text-spacing-run") {
    const styleId = "__qa_fixed_wcag_text_spacing_probe";
    const baseline = await page.evaluate(
      (id) => ({
        style_collision: Boolean(document.getElementById(id)),
        viewport: { width_css_px: innerWidth, height_css_px: innerHeight },
        document_overflow: {
          horizontal_css_px: Math.max(0, document.documentElement.scrollWidth - innerWidth),
          vertical_css_px: Math.max(0, document.documentElement.scrollHeight - innerHeight),
        },
        control_count: document.querySelectorAll(
          "a[href],button,input,select,textarea,[role='button'],[role='link']",
        ).length,
      }),
      styleId,
    );
    if (baseline.style_collision) {
      return resultFor({
        status: "blocked",
        limitation: "the fixed text-spacing probe marker already exists in the current document",
      });
    }
    let styleHandle = null;
    let after = null;
    let cleanupError = null;
    try {
      styleHandle = await page.addStyleTag({
        content:
          "* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; }" +
          "p { margin-block-end: 2em !important; }",
      });
      await styleHandle.evaluate((element, id) => {
        element.id = id;
      }, styleId);
      after = await page.evaluate(() => {
        const clipped = [];
        const pathFor = (element) => {
          const parts = [];
          let current = element;
          while (current && current.nodeType === Node.ELEMENT_NODE) {
            const parent = current.parentElement;
            const peers = parent
              ? Array.from(parent.children).filter((peer) => peer.tagName === current.tagName)
              : [current];
            parts.push(
              current.tagName.toLowerCase() + ":nth-of-type(" + (peers.indexOf(current) + 1) + ")",
            );
            current = parent;
          }
          return parts.reverse().join(" > ");
        };
        for (const element of Array.from(document.querySelectorAll("body *"))) {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          if (
            style.display === "none" ||
            style.visibility === "hidden" ||
            rect.width <= 0 ||
            rect.height <= 0
          )
            continue;
          const overflowX =
            ["hidden", "clip"].includes(style.overflowX) &&
            (element.scrollWidth > element.clientWidth + 1 || rect.right > innerWidth + 1);
          const overflowY =
            ["hidden", "clip"].includes(style.overflowY) &&
            (element.scrollHeight > element.clientHeight + 1 || rect.bottom > innerHeight + 1);
          if (overflowX || overflowY)
            clipped.push({
              target_ref: "dom-text-spacing:" + pathFor(element),
              horizontal: overflowX,
              vertical: overflowY,
            });
        }
        return {
          document_overflow: {
            horizontal_css_px: Math.max(0, document.documentElement.scrollWidth - innerWidth),
            vertical_css_px: Math.max(0, document.documentElement.scrollHeight - innerHeight),
          },
          clipped_targets: clipped.slice(0, 100),
          control_count: document.querySelectorAll(
            "a[href],button,input,select,textarea,[role='button'],[role='link']",
          ).length,
          applied_values: {
            line_height: "1.5",
            letter_spacing: "0.12em",
            word_spacing: "0.16em",
            paragraph_spacing: "2em",
          },
        };
      });
    } catch {
      cleanupError = "fixed text-spacing observation could not be completed";
    } finally {
      if (styleHandle) {
        try {
          await styleHandle.evaluate((element) => element.remove());
        } catch {
          cleanupError = cleanupError || "fixed style cleanup could not be verified";
        }
        await styleHandle.dispose().catch(() => {});
      }
    }
    if (cleanupError === null) {
      const markerRemains = await page.evaluate(
        (id) => Boolean(document.getElementById(id)),
        styleId,
      );
      if (markerRemains)
        cleanupError = "fixed text-spacing override remained in the document after cleanup";
    }
    if (!after || cleanupError !== null) {
      return resultFor({
        status: "blocked",
        value: {
          schema: "wcag-text-spacing-v1",
          baseline,
          after,
          cleanup: cleanupError === null ? "not-required" : "unverified",
        },
        limitation: cleanupError || "the fixed text-spacing observation did not return a result",
      });
    }
    return resultFor({
      status: "ok",
      value: { schema: "wcag-text-spacing-v1", baseline, after, cleanup: { status: "restored" } },
    });
  }

  const specializedProbeKeys = new Set([
    "mp-resize-text-run",
    "mp-computed-color-context",
    "mp-focus-appearance-evidence",
    "mp-target-geometry",
  ]);
  const catalogued = specializedProbeKeys.has(request.machine_probe_key)
    ? null
    : await page.evaluate((key) => {
        const pathFor = (element) => {
          const parts = [];
          let current = element;
          while (current && current.nodeType === Node.ELEMENT_NODE) {
            const parent = current.parentElement;
            const peers = parent
              ? Array.from(parent.children).filter((peer) => peer.tagName === current.tagName)
              : [current];
            parts.push(
              current.tagName.toLowerCase() + ":nth-of-type(" + (peers.indexOf(current) + 1) + ")",
            );
            current = parent;
          }
          return parts.reverse().join(" > ");
        };
        const visible = (element) => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.visibility !== "collapse" &&
            Number(style.opacity) > 0 &&
            rect.width > 0 &&
            rect.height > 0
          );
        };
        const safeText = (value, limit = 180) =>
          String(value || "")
            .replace(/\s+/gu, " ")
            .trim()
            .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/giu, "[redacted-email]")
            .replace(
              /\b(bearer|token|password|secret|api[-_ ]?key)\s*[:=]\s*\S+/giu,
              "$1=[redacted]",
            )
            .replace(/\b(?:\d[ -]?){9,}\d\b/gu, "[redacted-number]")
            .slice(0, limit);
        const textOf = (element) => safeText(element?.innerText || element?.textContent || "");
        const refOf = (element, prefix = "dom-target") => prefix + ":" + pathFor(element);
        const allVisible = (selector) =>
          Array.from(document.querySelectorAll(selector)).filter(visible);
        const interactiveSelector =
          "a[href],button,input,select,textarea,[role='button'],[role='link'],[role='checkbox'],[role='radio'],[role='slider'],[tabindex]:not([tabindex='-1'])";
        const interactive = allVisible(interactiveSelector);
        const statesOf = (element) => ({
          disabled: Boolean(element.disabled || element.getAttribute("aria-disabled") === "true"),
          required: Boolean(element.required || element.getAttribute("aria-required") === "true"),
          invalid:
            element.getAttribute("aria-invalid") === "true" ||
            (element.validity ? !element.validity.valid : false),
          expanded: element.getAttribute("aria-expanded"),
          checked: typeof element.checked === "boolean" ? element.checked : null,
          selected: typeof element.selected === "boolean" ? element.selected : null,
          pressed: element.getAttribute("aria-pressed"),
          current: element.getAttribute("aria-current"),
        });
        const roleOf = (element) =>
          element.getAttribute("role") ||
          {
            A: "link",
            BUTTON: "button",
            INPUT:
              element.type === "checkbox"
                ? "checkbox"
                : element.type === "radio"
                  ? "radio"
                  : element.type === "range"
                    ? "slider"
                    : "textbox",
            SELECT: "combobox",
            TEXTAREA: "textbox",
            IMG: "img",
          }[element.tagName] ||
          element.tagName.toLowerCase();
        const accessibleName = (element) => {
          const aria = element.getAttribute("aria-label");
          if (aria) return safeText(aria);
          const ids = (element.getAttribute("aria-labelledby") || "").split(/\s+/u).filter(Boolean);
          if (ids.length)
            return safeText(
              ids
                .map((id) => document.getElementById(id))
                .filter(Boolean)
                .map(textOf)
                .join(" "),
            );
          if (element.labels && element.labels.length)
            return safeText(Array.from(element.labels).map(textOf).join(" "));
          return safeText(
            element.getAttribute("alt") || element.getAttribute("title") || textOf(element),
          );
        };
        const rectOf = (element) => {
          const rect = element.getBoundingClientRect();
          return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
        };
        const rows = (elements) =>
          elements.map((element, index) => ({
            target_ref: refOf(element),
            tag_name: element.tagName.toLowerCase(),
            role: roleOf(element),
            dom_order: index,
          }));
        const value = (payload) => ({ schema: "wcag-" + key.slice(3) + "-v1", ...payload });
        switch (key) {
          case "mp-document-title": {
            const titleElement = document.querySelector("title");
            const titleText = titleElement?.textContent || "";
            return {
              status: "ok",
              value: value({
                is_html_document:
                  document.documentElement?.namespaceURI === "http://www.w3.org/1999/xhtml",
                has_title_element: Boolean(titleElement),
                first_title_children_are_text: Boolean(
                  titleElement && titleElement.firstChild?.nodeType === Node.TEXT_NODE,
                ),
                has_non_whitespace_text: Boolean(titleText.trim()),
              }),
            };
          }
          case "mp-document-language":
            return {
              status: "ok",
              value: value({
                lang: document.documentElement?.getAttribute("lang") || null,
                xml_lang: document.documentElement?.getAttribute("xml:lang") || null,
                has_language_metadata: Boolean(
                  document.documentElement?.getAttribute("lang") ||
                  document.documentElement?.getAttribute("xml:lang"),
                ),
              }),
            };
          case "mp-part-language-inventory":
            return {
              status: "ok",
              value: value({
                parts: allVisible("[lang],[xml\\:lang]")
                  .filter((element) => element !== document.documentElement)
                  .map((element) => ({
                    target_ref: refOf(element),
                    lang: element.getAttribute("lang"),
                    xml_lang: element.getAttribute("xml:lang"),
                    rendered_text_length: textOf(element).length,
                  })),
              }),
            };
          case "mp-purpose-metadata":
            return {
              status: "ok",
              value: value({
                controls: interactive.map((element) => ({
                  target_ref: refOf(element),
                  role: roleOf(element),
                  type: element.getAttribute("type"),
                  autocomplete: element.getAttribute("autocomplete"),
                  input_mode: element.getAttribute("inputmode"),
                  has_aria_label: element.hasAttribute("aria-label"),
                  has_aria_labelledby: element.hasAttribute("aria-labelledby"),
                })),
              }),
            };
          case "mp-nontext-content-inventory": {
            const candidates = allVisible(
              "img,svg,canvas,object,embed,iframe,video,audio,input[type='image'],[role='img']",
            );
            return {
              status: "ok",
              value: value({
                candidates: candidates.map((element) => ({
                  target_ref: refOf(element),
                  tag_name: element.tagName.toLowerCase(),
                  role: roleOf(element),
                  alt_present: element.hasAttribute("alt"),
                  aria_label_present: element.hasAttribute("aria-label"),
                  aria_hidden: element.getAttribute("aria-hidden") === "true",
                  width_css_px: rectOf(element).width,
                  height_css_px: rectOf(element).height,
                })),
              }),
            };
          }
          case "mp-media-inventory": {
            const media = Array.from(document.querySelectorAll("audio,video"));
            return {
              status: "ok",
              value: value({
                candidates: media.map((element) => ({
                  target_ref: refOf(element),
                  media_type: element.tagName.toLowerCase(),
                  controls: element.controls,
                  autoplay_attribute: element.hasAttribute("autoplay"),
                  autoplay_property: element.autoplay,
                  loop: element.loop,
                  muted: element.muted,
                  paused: element.paused,
                  rendered: visible(element),
                  duration_seconds: Number.isFinite(element.duration) ? element.duration : null,
                  tracks: Array.from(element.querySelectorAll("track")).map((track) => ({
                    kind: track.kind,
                    language: track.srclang || null,
                    label_present: Boolean(track.label),
                    default_track: track.default,
                  })),
                })),
              }),
            };
          }
          case "mp-moving-updating-inventory": {
            const moving = allVisible(
              "marquee,blink,[aria-live],svg animate,svg animateMotion,svg animateTransform",
            ).map((element) => ({
              target_ref: refOf(element),
              tag_name: element.tagName.toLowerCase(),
              role: roleOf(element),
              aria_live: element.getAttribute("aria-live"),
              aria_atomic: element.getAttribute("aria-atomic"),
              animation_name: getComputedStyle(element).animationName,
              animation_duration: getComputedStyle(element).animationDuration,
              paused_control_present: Boolean(element.querySelector("button,[role='button']")),
            }));
            for (const element of allVisible("*")) {
              const style = getComputedStyle(element);
              if (
                style.animationName !== "none" ||
                style.animationDuration.split(",").some((item) => parseFloat(item) > 0)
              ) {
                moving.push({
                  target_ref: refOf(element),
                  tag_name: element.tagName.toLowerCase(),
                  role: roleOf(element),
                  aria_live: element.getAttribute("aria-live"),
                  aria_atomic: element.getAttribute("aria-atomic"),
                  animation_name: style.animationName,
                  animation_duration: style.animationDuration,
                  paused_control_present: Boolean(element.querySelector("button,[role='button']")),
                });
              }
            }
            return { status: "ok", value: value({ candidates: moving.slice(0, 200) }) };
          }
          case "mp-timer-inventory": {
            const timers = allVisible(
              "time,meter,progress,[role='timer'],[role='progressbar'],[role='countdown']",
            ).map((element) => ({
              target_ref: refOf(element),
              tag_name: element.tagName.toLowerCase(),
              role: roleOf(element),
              datetime_present: element.hasAttribute("datetime"),
              has_minimum: element.hasAttribute("min"),
              has_maximum: element.hasAttribute("max"),
              has_value: element.hasAttribute("value"),
              value_text_length: textOf(element).length,
              aria_live: element.getAttribute("aria-live"),
              aria_label_present: element.hasAttribute("aria-label"),
            }));
            const refresh = document.querySelector("meta[http-equiv='refresh' i]");
            return {
              status: "ok",
              value: value({ candidates: timers, document_refresh_present: Boolean(refresh) }),
            };
          }
          case "mp-shortcut-inventory":
            return {
              status: "ok",
              value: value({
                candidates: allVisible("[accesskey]").map((element) => ({
                  target_ref: refOf(element),
                  role: roleOf(element),
                  key_length: Array.from(element.accessKey || "").length,
                  key_is_single_printable_character:
                    Array.from(element.accessKey || "").length === 1 &&
                    !/[\u0000-\u001f\u007f]/u.test(element.accessKey),
                  accessible_name_present: Boolean(accessibleName(element)),
                })),
              }),
            };
          case "mp-form-control-inventory":
            return {
              status: "ok",
              value: value({
                controls: allVisible(
                  "input,select,textarea,button,[role='checkbox'],[role='radio'],[role='slider'],[role='switch']",
                ).map((element) => ({
                  target_ref: refOf(element),
                  tag_name: element.tagName.toLowerCase(),
                  type: element.getAttribute("type"),
                  role: roleOf(element),
                  accessible_name: accessibleName(element),
                  label_count: element.labels ? element.labels.length : 0,
                  required: Boolean(
                    element.required || element.getAttribute("aria-required") === "true",
                  ),
                  invalid: statesOf(element).invalid,
                  disabled: statesOf(element).disabled,
                  autocomplete: element.getAttribute("autocomplete"),
                  constraints: {
                    min_present: element.hasAttribute("min"),
                    max_present: element.hasAttribute("max"),
                    step_present: element.hasAttribute("step"),
                    pattern_present: element.hasAttribute("pattern"),
                    min_length: element.getAttribute("minlength"),
                    max_length: element.getAttribute("maxlength"),
                  },
                })),
              }),
            };
          case "mp-heading-label-inventory":
            return {
              status: "ok",
              value: value({
                headings: allVisible("h1,h2,h3,h4,h5,h6,[role='heading']").map((element) => ({
                  target_ref: refOf(element),
                  level:
                    Number(element.getAttribute("aria-level") || element.tagName.slice(1)) || null,
                  rendered_text: textOf(element),
                  accessible_name: accessibleName(element),
                })),
                labels: allVisible("label").map((element) => ({
                  target_ref: refOf(element),
                  for_present: element.hasAttribute("for"),
                  associated_control_count: element.control ? 1 : 0,
                  rendered_text: textOf(element),
                })),
              }),
            };
          case "mp-link-inventory":
            return {
              status: "ok",
              value: value({
                links: allVisible("a[href],[role='link']").map((element) => {
                  let safeTarget = "unresolvable";
                  let hasQuery = false;
                  let hasFragment = false;
                  let pathSegmentCount = null;
                  try {
                    const target = new URL(element.getAttribute("href") || "", location.href);
                    safeTarget = !["http:", "https:"].includes(target.protocol)
                      ? "non-http"
                      : target.origin === location.origin
                        ? "same-origin"
                        : "external-origin";
                    hasQuery = target.search.length > 0;
                    hasFragment = target.hash.length > 0;
                    pathSegmentCount = target.pathname.split("/").filter(Boolean).length;
                  } catch {
                    /* Keep only the fixed non-sensitive classification. */
                  }
                  return {
                    target_ref: refOf(element),
                    safe_target: safeTarget,
                    has_query: hasQuery,
                    has_fragment: hasFragment,
                    path_segment_count: pathSegmentCount,
                    rendered_text: textOf(element),
                    accessible_name: accessibleName(element),
                    role: roleOf(element),
                    has_programmatic_context: Boolean(
                      element.getAttribute("aria-describedby") ||
                      element.closest("nav,main,header,footer"),
                    ),
                  };
                }),
              }),
            };
          case "mp-structure-inventory": {
            const nodes = allVisible(
              "main,nav,header,footer,aside,section,article,form,fieldset,ul,ol,dl,table,thead,tbody,tr,th,td,h1,h2,h3,h4,h5,h6,[role='main'],[role='navigation'],[role='list'],[role='table'],[role='row'],[role='cell'],[role='columnheader']",
            );
            return {
              status: "ok",
              value: value({
                nodes: nodes.map((element) => ({
                  target_ref: refOf(element, "dom-structure"),
                  tag_name: element.tagName.toLowerCase(),
                  role: roleOf(element),
                  parent_ref: element.parentElement
                    ? refOf(element.parentElement, "dom-structure")
                    : null,
                  child_element_count: element.children.length,
                  heading_level: /^H[1-6]$/u.test(element.tagName)
                    ? Number(element.tagName.slice(1))
                    : Number(element.getAttribute("aria-level")) || null,
                  labelledby_present: element.hasAttribute("aria-labelledby"),
                  legend_present: Boolean(element.querySelector(":scope > legend")),
                })),
              }),
            };
          }
          case "mp-sequence-inventory": {
            const sequence = allVisible(
              "main,nav,header,footer,h1,h2,h3,h4,h5,h6,a[href],button,input,select,textarea,[role='button'],[role='link'],[tabindex]:not([tabindex='-1'])",
            );
            return { status: "ok", value: value({ sequence: rows(sequence) }) };
          }
          case "mp-component-semantics":
            return {
              status: "ok",
              value: value({
                components: interactive.map((element) => ({
                  target_ref: refOf(element),
                  tag_name: element.tagName.toLowerCase(),
                  role: roleOf(element),
                  accessible_name: accessibleName(element),
                  description_present: Boolean(element.getAttribute("aria-describedby")),
                  states: statesOf(element),
                  host_type: element.getAttribute("type"),
                  included_in_accessibility_tree: !element.closest("[aria-hidden='true'],[inert]"),
                  programmatically_hidden:
                    element.closest("[aria-hidden='true'],[hidden],[inert]") !== null,
                })),
              }),
            };
          case "mp-status-candidate-inventory":
            return {
              status: "ok",
              value: value({
                candidates: allVisible("[role='status'],[role='alert'],[aria-live]").map(
                  (element) => ({
                    target_ref: refOf(element),
                    role: roleOf(element),
                    aria_live: element.getAttribute("aria-live"),
                    aria_atomic: element.getAttribute("aria-atomic"),
                    aria_relevant: element.getAttribute("aria-relevant"),
                    rendered_text_length: textOf(element).length,
                    has_accessible_name: Boolean(accessibleName(element)),
                  }),
                ),
              }),
            };
          case "mp-neighbor-geometry": {
            const targets = interactive
              .filter((element) => {
                const rect = element.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
              })
              .map((element) => ({
                target_ref: refOf(element),
                role: roleOf(element),
                geometry_css_px: rectOf(element),
              }));
            const pairs = [];
            for (let index = 0; index < targets.length; index++) {
              const first = targets[index];
              for (let nextIndex = index + 1; nextIndex < targets.length; nextIndex++) {
                const second = targets[nextIndex];
                const a = first.geometry_css_px,
                  b = second.geometry_css_px;
                const horizontalGap = Math.max(
                  0,
                  Math.max(a.x - (b.x + b.width), b.x - (a.x + a.width)),
                );
                const verticalGap = Math.max(
                  0,
                  Math.max(a.y - (b.y + b.height), b.y - (a.y + a.height)),
                );
                const overlapX = Math.max(
                  0,
                  Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x),
                );
                const overlapY = Math.max(
                  0,
                  Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y),
                );
                if (
                  horizontalGap <= 48 &&
                  verticalGap <= 48 &&
                  (overlapX > 0 || overlapY > 0 || horizontalGap < 48 || verticalGap < 48)
                ) {
                  pairs.push({
                    first_target_ref: first.target_ref,
                    second_target_ref: second.target_ref,
                    horizontal_gap_css_px: horizontalGap,
                    vertical_gap_css_px: verticalGap,
                  });
                  if (pairs.length >= 500) break;
                }
              }
              if (pairs.length >= 500) break;
            }
            return { status: "ok", value: value({ targets, neighboring_pairs: pairs }) };
          }
          case "mp-text-presentation-values": {
            const owners = new Set();
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
              if (
                node.nodeValue &&
                /\S/u.test(node.nodeValue) &&
                node.parentElement &&
                visible(node.parentElement)
              )
                owners.add(node.parentElement);
            }
            return {
              status: "ok",
              value: value({
                targets: Array.from(owners)
                  .slice(0, 500)
                  .map((element) => {
                    const style = getComputedStyle(element),
                      rect = element.getBoundingClientRect();
                    return {
                      target_ref: refOf(element, "dom-text-owner"),
                      font_size_css: style.fontSize,
                      line_height_css: style.lineHeight,
                      letter_spacing_css: style.letterSpacing,
                      word_spacing_css: style.wordSpacing,
                      text_align: style.textAlign,
                      white_space: style.whiteSpace,
                      overflow_wrap: style.overflowWrap,
                      width_css_px: rect.width,
                    };
                  }),
              }),
            };
          }
          case "mp-viewport-state":
            return {
              status: "ok",
              value: value({
                viewport: {
                  width_css_px: innerWidth,
                  height_css_px: innerHeight,
                  device_pixel_ratio: devicePixelRatio,
                },
                document: {
                  scroll_x_css_px: scrollX,
                  scroll_y_css_px: scrollY,
                  scroll_width_css_px: document.documentElement.scrollWidth,
                  scroll_height_css_px: document.documentElement.scrollHeight,
                  client_width_css_px: document.documentElement.clientWidth,
                  client_height_css_px: document.documentElement.clientHeight,
                },
              }),
            };
          case "mp-reflow-run": {
            const overflowTargets = allVisible("*")
              .filter((element) => {
                const rect = element.getBoundingClientRect();
                return (
                  rect.right > innerWidth + 1 ||
                  rect.left < -1 ||
                  ((getComputedStyle(element).overflowX === "hidden" ||
                    getComputedStyle(element).overflowX === "clip") &&
                    element.scrollWidth > element.clientWidth + 1)
                );
              })
              .slice(0, 200)
              .map((element) => ({
                target_ref: refOf(element),
                geometry_css_px: rectOf(element),
                scroll_width_css_px: element.scrollWidth,
                client_width_css_px: element.clientWidth,
              }));
            return {
              status: "ok",
              value: value({
                required_viewport_css_px: { width: innerWidth, height: innerHeight },
                document_overflow_css_px: Math.max(
                  0,
                  document.documentElement.scrollWidth - innerWidth,
                ),
                overflow_targets: overflowTargets,
              }),
            };
          }
          case "mp-orientation-run":
            return {
              status: "incomplete",
              value: value({
                observation_completeness: {
                  state: "partial",
                  reason: "paired-orientation-not-materialized",
                },
                current_viewport_css_px: { width: innerWidth, height: innerHeight },
                current_orientation:
                  screen.orientation?.type ||
                  (innerWidth >= innerHeight ? "landscape-primary" : "portrait-primary"),
                overflow_css_px: Math.max(0, document.documentElement.scrollWidth - innerWidth),
                paired_orientation_observed: false,
              }),
              limitation:
                "the fixed request identifies one current variation but does not provide a paired alternate-orientation sample identity",
            };
          case "mp-audio-autoplay-run": {
            const audio = Array.from(document.querySelectorAll("audio,video"));
            if (audio.length === 0) {
              return {
                status: "ok",
                value: value({
                  candidates: [],
                  observed_after_page_load: true,
                  playback_start_origin_instrumented: false,
                }),
              };
            }
            return {
              status: "incomplete",
              value: value({
                candidates: audio.map((element) => ({
                  target_ref: refOf(element),
                  media_type: element.tagName.toLowerCase(),
                  autoplay_attribute: element.hasAttribute("autoplay"),
                  autoplay_property: element.autoplay,
                  paused: element.paused,
                  current_time_seconds: element.currentTime,
                  duration_seconds: Number.isFinite(element.duration) ? element.duration : null,
                  rendered: visible(element),
                  muted: element.muted,
                  controls: element.controls,
                })),
                observed_after_page_load: true,
                playback_start_origin_instrumented: false,
              }),
              limitation:
                "the fixed current-page observation does not instrument media playback origin or time from document load",
            };
          }
          case "mp-control-value-history":
            return {
              status: "incomplete",
              value: value({
                observation_completeness: {
                  state: "partial",
                  reason: "prior-control-observation-not-materialized",
                },
                controls: interactive
                  .filter(
                    (element) =>
                      ["checkbox", "radio", "range"].includes(element.type) ||
                      element.tagName === "SELECT",
                  )
                  .map((element) => ({
                    target_ref: refOf(element),
                    role: roleOf(element),
                    state: statesOf(element),
                  })),
                previous_value_state_available: false,
              }),
              limitation:
                "the typed request does not include a prior control-state observation reference",
            };
          case "mp-multipage-signature":
            return {
              status: "incomplete",
              value: value({
                observation_completeness: { state: "partial", reason: "page-set-not-materialized" },
                current_page_signature: {
                  title_present: Boolean(document.title.trim()),
                  language_present: Boolean(document.documentElement?.lang),
                  controls: interactive.map((element) => ({
                    target_ref: refOf(element),
                    role: roleOf(element),
                    accessible_name: accessibleName(element),
                    has_help_relationship: Boolean(element.getAttribute("aria-describedby")),
                  })),
                },
                selected_page_set_available: false,
              }),
              limitation:
                "the typed request does not identify the selected multipage page set required for cross-page comparison",
            };
          case "mp-hover-focus-content-run":
            return {
              status: "incomplete",
              value: value({
                observation_completeness: { state: "partial", reason: "target-not-materialized" },
                candidate_targets: interactive.map((element) => ({
                  target_ref: refOf(element),
                  role: roleOf(element),
                  accessible_name: accessibleName(element),
                  focused: element === document.activeElement,
                })),
                transition_observed: false,
              }),
              limitation:
                "the typed request does not identify the exact target whose hover or focus content transition may be exercised",
            };
          case "mp-change-trigger-run":
            return {
              status: "incomplete",
              value: value({
                observation_completeness: { state: "partial", reason: "trigger-not-materialized" },
                candidate_targets: interactive
                  .filter((element) =>
                    ["input", "select", "textarea"].includes(element.tagName.toLowerCase()),
                  )
                  .map((element) => ({
                    target_ref: refOf(element),
                    role: roleOf(element),
                    state: statesOf(element),
                  })),
                transition_observed: false,
              }),
              limitation:
                "the typed request does not identify a declared focus, input, or request trigger to execute",
            };
          case "mp-error-scenario-run":
            return {
              status: "incomplete",
              value: value({
                observation_completeness: {
                  state: "partial",
                  reason: "error-scenario-not-materialized",
                },
                form_candidates: Array.from(document.forms).map((form) => ({
                  target_ref: refOf(form, "dom-form"),
                  control_refs: Array.from(form.elements)
                    .filter((element) => element instanceof HTMLElement)
                    .map((element) => refOf(element)),
                  native_invalid_control_count: Array.from(form.elements)
                    .filter(
                      (element) =>
                        element instanceof HTMLInputElement ||
                        element instanceof HTMLSelectElement ||
                        element instanceof HTMLTextAreaElement,
                    )
                    .filter((element) => !element.checkValidity()).length,
                })),
                scenario_executed: false,
              }),
              limitation:
                "the typed request does not identify a declared error scenario and exact target; no form submission or input mutation was started",
            };
          case "mp-pointer-interaction-run":
            return {
              status: "incomplete",
              value: value({
                observation_completeness: {
                  state: "partial",
                  reason: "pointer-action-not-materialized",
                },
                candidate_targets: interactive.map((element) => ({
                  target_ref: refOf(element),
                  role: roleOf(element),
                  accessible_name: accessibleName(element),
                  draggable: element.draggable,
                  input_type: element instanceof HTMLInputElement ? element.type : null,
                })),
                pointer_action_executed: false,
              }),
              limitation:
                "the typed request does not contain a materialized target and authorized pointer action; no pointer side effect was started",
            };
          default:
            return {
              status: "blocked",
              limitation: "fixed WCAG machine probe key is not dispatched by this package",
            };
        }
      }, request.machine_probe_key);

  if (catalogued?.status === "ok") return resultFor(catalogued);
  if (catalogued?.status === "incomplete") return resultFor(catalogued);
  if (catalogued?.status === "blocked") return resultFor(catalogued);

  if (request.machine_probe_key === "mp-computed-color-context") {
    const context = await page.evaluate(() => {
      const pathFor = (element) => {
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
          const parent = current.parentElement;
          const peers = parent
            ? Array.from(parent.children).filter((peer) => peer.tagName === current.tagName)
            : [current];
          parts.push(`${current.tagName.toLowerCase()}:nth-of-type(${peers.indexOf(current) + 1})`);
          current = parent;
        }
        return parts.reverse().join(" > ");
      };
      const rendered = (element) => {
        const style = getComputedStyle(element);
        return (
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          style.visibility !== "collapse" &&
          Number(style.opacity) > 0 &&
          element.getClientRects().length > 0
        );
      };
      const owners = new Set();
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let textNode;
      while ((textNode = walker.nextNode())) {
        const owner = textNode.parentElement;
        if (textNode.nodeValue && /\S/u.test(textNode.nodeValue) && owner && rendered(owner))
          owners.add(owner);
      }
      const reasons = new Set();
      const affectedTargets = new Set();
      const computedSamples = [];
      const inspectStyle = (style, targetRef) => {
        const image = style.backgroundImage;
        if (image && image !== "none") {
          reasons.add(/(?:linear|radial|conic)-gradient\(/i.test(image) ? "gradient" : "image");
          affectedTargets.add(targetRef);
        }
        if (style.mixBlendMode && style.mixBlendMode !== "normal") {
          reasons.add("blend");
          affectedTargets.add(targetRef);
        }
      };
      for (const owner of owners) {
        const targetRef = `dom-text-owner:${pathFor(owner)}`;
        let current = owner;
        const ownerStyle = getComputedStyle(owner);
        const backgroundLayers = [];
        while (current && current.nodeType === Node.ELEMENT_NODE) {
          const style = getComputedStyle(current);
          inspectStyle(style, targetRef);
          if (
            style.backgroundColor !== "rgba(0, 0, 0, 0)" ||
            (style.backgroundImage && style.backgroundImage !== "none")
          ) {
            backgroundLayers.push({
              target_ref: "dom-background:" + pathFor(current),
              color: style.backgroundColor,
              image_present: style.backgroundImage !== "none",
              opacity: style.opacity,
              blend_mode: style.mixBlendMode,
            });
          }
          for (const pseudo of ["::before", "::after"]) {
            const pseudoStyle = getComputedStyle(current, pseudo);
            if (
              !pseudoStyle.content ||
              ["none", "normal", '""', "''"].includes(pseudoStyle.content)
            )
              continue;
            inspectStyle(pseudoStyle, targetRef);
          }
          if (current === document.documentElement) break;
          current = current.parentElement;
        }
        if (computedSamples.length < 500) {
          const borderColors = {};
          for (const side of ["Top", "Right", "Bottom", "Left"]) {
            borderColors[side.toLowerCase()] = ownerStyle["border" + side + "Color"];
          }
          computedSamples.push({
            target_ref: targetRef,
            foreground: ownerStyle.color,
            backgrounds: backgroundLayers,
            border_colors: borderColors,
            outline: {
              color: ownerStyle.outlineColor,
              style: ownerStyle.outlineStyle,
              width: ownerStyle.outlineWidth,
            },
          });
        }
      }
      return {
        rendered_text_owner_count: owners.size,
        unresolvable_background_kinds: [...reasons].sort(),
        affected_target_count: affectedTargets.size,
        computed_samples: computedSamples,
      };
    });
    if (!context || context.rendered_text_owner_count === 0) {
      return failure(
        "blocked",
        "the fixed computed-color probe could not establish a rendered text population",
      );
    }
    if (context.unresolvable_background_kinds.length > 0) {
      return {
        ...identity,
        status: "unavailable",
        current_document_identity: await currentDocumentIdentity(),
        evidence_refs: evidenceRefs,
        value: {
          schema: "wcag-computed-color-context-v1",
          rendered_text_owner_count: context.rendered_text_owner_count,
          unresolvable_background_kinds: context.unresolvable_background_kinds,
          affected_target_count: context.affected_target_count,
          computed_samples: context.computed_samples,
        },
        limitation:
          "a rendered text background uses a gradient, image, or blend context that cannot be resolved to one machine contrast value",
        limitation_code: "background-not-machine-resolvable",
      };
    }
    return {
      ...identity,
      status: "ok",
      current_document_identity: await currentDocumentIdentity(),
      evidence_refs: evidenceRefs,
      value: {
        schema: "wcag-computed-color-context-v1",
        rendered_text_owner_count: context.rendered_text_owner_count,
        unresolvable_background_kinds: [],
        affected_target_count: 0,
        computed_samples: context.computed_samples,
      },
    };
  }

  if (request.machine_probe_key === "mp-target-geometry") {
    const targets = await page.evaluate(() => {
      const pathFor = (element) => {
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
          const parent = current.parentElement;
          const peers = parent
            ? Array.from(parent.children).filter((peer) => peer.tagName === current.tagName)
            : [current];
          parts.push(`${current.tagName.toLowerCase()}:nth-of-type(${peers.indexOf(current) + 1})`);
          current = parent;
        }
        return parts.reverse().join(" > ");
      };
      const selector =
        "a[href],button,input,select,textarea,[role='button'],[role='link'],[role='slider'],img,svg,canvas,video,iframe";
      return Array.from(document.querySelectorAll(selector))
        .filter((element) => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.visibility !== "collapse" &&
            Number(style.opacity) > 0 &&
            rect.width > 0 &&
            rect.height > 0
          );
        })
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return {
            target_ref: `dom-target:${pathFor(element)}`,
            tag_name: element.tagName.toLowerCase(),
            role: element.getAttribute("role"),
            focused: element === document.activeElement,
            geometry_css_px: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          };
        })
        .sort((left, right) =>
          left.target_ref < right.target_ref ? -1 : left.target_ref > right.target_ref ? 1 : 0,
        );
    });
    if (!Array.isArray(targets) || targets.length === 0) {
      return failure(
        "blocked",
        "the fixed geometry probe could not establish visible target geometry",
      );
    }
    return {
      ...identity,
      status: "ok",
      current_document_identity: await currentDocumentIdentity(),
      evidence_refs: evidenceRefs,
      value: { schema: "wcag-target-geometry-v1", targets },
    };
  }

  if (request.machine_probe_key === "mp-focus-appearance-evidence") {
    const trace = await captureFocusSequence(1);
    const focus = trace.sequence[0] || null;
    const value = {
      schema: "wcag-focus-appearance-observation-v1",
      ...trace,
      focused_target: focus,
      visual_screenshot_required: true,
    };
    if (
      trace.capture_error !== null ||
      !focus ||
      focus.target_ref === null ||
      !focus.rect_css_px ||
      focus.rect_css_px.width <= 0 ||
      focus.rect_css_px.height <= 0
    ) {
      return resultFor({
        status: "blocked",
        value,
        limitation:
          trace.capture_error ||
          "the fixed keyboard focus probe did not resolve one visible focused target",
      });
    }
    if (focus.box_shadow_layer_count > 1 || focus.background_image_present) {
      return resultFor({
        status: "incomplete",
        value,
        limitation:
          "the focused indicator uses layered shadow or image styling whose shape and visual area require manual observation",
        limitation_code: "focus-indicator-not-machine-resolvable",
      });
    }
    return resultFor({ status: "ok", value });
  }

  if (request.machine_probe_key !== "mp-resize-text-run") {
    return failure("blocked", "the fixed WCAG machine probe key has no package dispatch");
  }

  const slider = page.getByRole("slider", { name: "Text size", exact: true });
  const sliderCount = await slider.count();
  if (sliderCount === 0) {
    return failure(
      "unsupported",
      "the current browser owner cannot operate a documented user-agent text scaling control",
      "text-scaling-mechanism-not-machine-executable",
    );
  }
  if (sliderCount !== 1 || !(await slider.isVisible()) || !(await slider.isEnabled())) {
    return failure("blocked", "the fixed accessible Text size control is ambiguous or unavailable");
  }

  const control = await slider.evaluate((element) => {
    if (!(element instanceof HTMLInputElement) || element.type !== "range") return null;
    return {
      target_ref: "accessible-control:slider:Text size",
      role: "slider",
      accessible_name: "Text size",
      input_type: element.type,
      minimum_value: element.min || "0",
      maximum_value: element.max || "100",
      step_value: element.step || "1",
      baseline_value: element.value,
    };
  });
  const decimal = (value) =>
    typeof value === "string" && /^\d+(?:\.\d+)?$/.test(value) ? Number(value) : Number.NaN;
  if (
    !control ||
    ![
      control.minimum_value,
      control.maximum_value,
      control.step_value,
      control.baseline_value,
    ].every((value) => Number.isFinite(decimal(value))) ||
    decimal(control.step_value) <= 0 ||
    decimal(control.minimum_value) > decimal(control.baseline_value) ||
    decimal(control.baseline_value) >= decimal(control.maximum_value)
  ) {
    return failure("blocked", "the fixed Text size range has invalid or non-progressing bounds");
  }

  const captureState = async () =>
    page.evaluate(async () => {
      const elementPath = (element) => {
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
          const parent = current.parentElement;
          const sameTag = parent
            ? Array.from(parent.children).filter((item) => item.tagName === current.tagName)
            : [current];
          parts.push(
            `${current.tagName.toLowerCase()}:nth-of-type(${sameTag.indexOf(current) + 1})`,
          );
          current = parent;
        }
        return parts.reverse().join(" > ");
      };
      const rendered = (element) => {
        const style = getComputedStyle(element);
        return (
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          style.visibility !== "collapse" &&
          Number(style.opacity) > 0 &&
          element.getClientRects().length > 0
        );
      };
      const contentBox = (element) => {
        const rect = element.getBoundingClientRect();
        return {
          left: rect.left + element.clientLeft,
          top: rect.top + element.clientTop,
          right: rect.left + element.clientLeft + element.clientWidth,
          bottom: rect.top + element.clientTop + element.clientHeight,
        };
      };
      const candidates = [];
      const unsupportedRoots = [];
      const roots = [{ root: document.body, prefix: "" }];
      for (let rootIndex = 0; rootIndex < roots.length; rootIndex++) {
        const { root, prefix } = roots[rootIndex];
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let textNode;
        let textIndex = 0;
        while ((textNode = walker.nextNode())) {
          textIndex += 1;
          if (!textNode.nodeValue || !/\S/u.test(textNode.nodeValue)) continue;
          const owner = textNode.parentElement;
          if (!owner || !rendered(owner)) continue;
          const style = getComputedStyle(owner);
          const range = document.createRange();
          range.selectNodeContents(textNode);
          const rects = Array.from(range.getClientRects())
            .filter((rect) => rect.width > 0 && rect.height > 0)
            .map((rect) => ({
              left: rect.left,
              top: rect.top,
              width: rect.width,
              height: rect.height,
            }));
          if (!rects.length) continue;
          const targetRef = `dom-text:${prefix}${elementPath(owner)}/text[${textIndex}]`;
          const size = /^\d+(?:\.\d+)?px$/.test(style.fontSize)
            ? style.fontSize.slice(0, -2)
            : null;
          if (size === null || !(Number(size) > 0)) unsupportedRoots.push(targetRef);
          let clipped = false;
          let ancestor = owner;
          while (ancestor && ancestor.nodeType === Node.ELEMENT_NODE) {
            const ancestorStyle = getComputedStyle(ancestor);
            if (
              ["hidden", "clip"].includes(ancestorStyle.overflowX) ||
              ["hidden", "clip"].includes(ancestorStyle.overflowY)
            ) {
              const box = contentBox(ancestor);
              if (
                rects.some(
                  (rect) =>
                    rect.left < box.left - 0.5 ||
                    rect.top < box.top - 0.5 ||
                    rect.left + rect.width > box.right + 0.5 ||
                    rect.top + rect.height > box.bottom + 0.5,
                )
              )
                clipped = true;
            }
            ancestor = ancestor.parentElement;
          }
          const obscured = rects.some((rect) => {
            const left = Math.max(0, rect.left);
            const top = Math.max(0, rect.top);
            const right = Math.min(window.innerWidth, rect.left + rect.width);
            const bottom = Math.min(window.innerHeight, rect.top + rect.height);
            if (right <= left || bottom <= top) return false;
            const hit = document.elementFromPoint(
              left + (right - left) / 2,
              top + (bottom - top) / 2,
            );
            return !hit || (hit !== owner && !owner.contains(hit) && !hit.contains(owner));
          });
          candidates.push({
            target_ref: targetRef,
            present: true,
            used_font_size_css_px: size,
            rects,
            clipped,
            obscured,
          });
        }
        const elements = root.querySelectorAll ? Array.from(root.querySelectorAll("*")) : [];
        for (const element of elements) {
          if (element.shadowRoot)
            roots.push({ root: element.shadowRoot, prefix: `shadow(${elementPath(element)}) > ` });
        }
      }

      const controls = [];
      for (const { root, prefix } of roots) {
        const elements = root.querySelectorAll ? Array.from(root.querySelectorAll("*")) : [];
        for (const element of elements) {
          if (!rendered(element)) continue;
          const path = `${prefix}${elementPath(element)}`;
          const elementRef = `dom-element:${path}`;
          for (const pseudo of ["::before", "::after"]) {
            const pseudoStyle = getComputedStyle(element, pseudo);
            if (["none", "normal", '""', "''"].includes(pseudoStyle.content)) continue;
            const size = /^\d+(?:\.\d+)?px$/.test(pseudoStyle.fontSize)
              ? pseudoStyle.fontSize.slice(0, -2)
              : null;
            if (size === null || !(Number(size) > 0))
              unsupportedRoots.push(`${elementRef}${pseudo}`);
            const rect = element.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0)
              candidates.push({
                target_ref: `${elementRef}${pseudo}`,
                present: true,
                used_font_size_css_px: size,
                rects: [{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }],
                clipped: false,
                obscured: false,
              });
          }

          const style = getComputedStyle(element);
          const inputType = element instanceof HTMLInputElement ? element.type : null;
          const isTextControl =
            element instanceof HTMLTextAreaElement ||
            element instanceof HTMLSelectElement ||
            (element instanceof HTMLInputElement &&
              !["checkbox", "color", "file", "hidden", "image", "radio", "range"].includes(
                inputType,
              ));
          if (isTextControl) {
            const size = /^\d+(?:\.\d+)?px$/.test(style.fontSize)
              ? style.fontSize.slice(0, -2)
              : null;
            const rect = element.getBoundingClientRect();
            if (size === null || !(Number(size) > 0)) unsupportedRoots.push(`dom-control:${path}`);
            if (rect.width > 0 && rect.height > 0)
              candidates.push({
                target_ref: `dom-control:${path}`,
                present: true,
                used_font_size_css_px: size,
                rects: [{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }],
                clipped: false,
                obscured: false,
              });
          }
          const role =
            element.tagName.toLowerCase() === "a"
              ? "link"
              : element.tagName.toLowerCase() === "button"
                ? "button"
                : element instanceof HTMLInputElement && element.type === "range"
                  ? "slider"
                  : element.tagName.toLowerCase();
          const isInteractive = element.matches(
            "a[href],button,input,select,textarea,[role='button'],[role='link'],[role='slider']",
          );
          if (isInteractive)
            controls.push({
              target_ref: `dom-control:${path}`,
              role,
              enabled:
                element.disabled !== true && element.getAttribute("aria-disabled") !== "true",
            });
        }
      }

      const viewport = { width_css_px: window.innerWidth, height_css_px: window.innerHeight };
      const overflow = {
        scroll_width_css_px: document.documentElement.scrollWidth,
        client_width_css_px: document.documentElement.clientWidth,
        scroll_height_css_px: document.documentElement.scrollHeight,
        client_height_css_px: document.documentElement.clientHeight,
      };
      const unsupportedVisibleCanvas = roots.some(({ root }) =>
        Array.from(root.querySelectorAll?.("canvas") || []).some((element) => rendered(element)),
      );
      const visibleFrame = roots.some(({ root }) =>
        Array.from(root.querySelectorAll?.("iframe,frame") || []).some((element) =>
          rendered(element),
        ),
      );
      const ids = new Set();
      let unique = true;
      for (const candidate of candidates) {
        if (ids.has(candidate.target_ref)) unique = false;
        ids.add(candidate.target_ref);
      }
      let documentIdentity = null;
      try {
        if (globalThis.crypto?.subtle && typeof TextEncoder !== "undefined") {
          const identityKeySlot = Symbol.for("qa-workflow-skills.document-identity-key.v1");
          let keyPromise = window[identityKeySlot];
          if (!keyPromise) {
            keyPromise = crypto.subtle.generateKey({ name: "HMAC", hash: "SHA-256" }, false, [
              "sign",
            ]);
            Object.defineProperty(window, identityKeySlot, {
              value: keyPromise,
              enumerable: false,
              configurable: false,
              writable: false,
            });
          }
          const signature = await crypto.subtle.sign(
            "HMAC",
            await keyPromise,
            new TextEncoder().encode(location.href),
          );
          const hex = Array.from(new Uint8Array(signature), (byte) =>
            byte.toString(16).padStart(2, "0"),
          ).join("");
          documentIdentity = `hmac-sha256:${hex}`;
        }
      } catch {
        documentIdentity = null;
      }
      return {
        document_identity: documentIdentity,
        viewport,
        overflow,
        text_candidates: candidates.sort((left, right) =>
          left.target_ref < right.target_ref ? -1 : left.target_ref > right.target_ref ? 1 : 0,
        ),
        interactive_controls: controls.sort((left, right) =>
          left.target_ref < right.target_ref ? -1 : left.target_ref > right.target_ref ? 1 : 0,
        ),
        population_complete:
          unique &&
          candidates.length > 0 &&
          unsupportedRoots.length === 0 &&
          !unsupportedVisibleCanvas &&
          !visibleFrame,
        unmeasurable_target_refs: unsupportedRoots.sort(),
        unsupported_visible_canvas: unsupportedVisibleCanvas,
        inaccessible_visible_frame: visibleFrame,
      };
    });

  const sequence = [];
  const baselineRefs = new Set();
  let populationComplete = true;
  let captureFailure = null;
  let stateSequenceComplete = false;
  let restoreValue = control.baseline_value;
  try {
    const baseline = await captureState();
    if (
      baseline.document_identity !== request.target_identity ||
      baseline.text_candidates.length === 0
    ) {
      return failure(
        "blocked",
        "the current document or rendered text population could not be established",
      );
    }
    for (const candidate of baseline.text_candidates) baselineRefs.add(candidate.target_ref);
    populationComplete = baseline.population_complete;
    sequence.push({
      state_index: 0,
      control_value: control.baseline_value,
      ...baseline,
      content_loss_refs: [],
      newly_clipped_target_refs: baseline.text_candidates
        .filter((row) => row.clipped)
        .map((row) => row.target_ref),
      newly_obscured_target_refs: baseline.text_candidates
        .filter((row) => row.obscured)
        .map((row) => row.target_ref),
      functionality_loss_refs: [],
    });

    const maxSteps = 100;
    for (let stepIndex = 0; stepIndex < maxSteps; stepIndex++) {
      const currentControlValue = await slider.inputValue();
      if (decimal(currentControlValue) >= decimal(control.maximum_value)) {
        stateSequenceComplete = true;
        break;
      }
      await slider.press("ArrowRight");
      await page.waitForTimeout(40);
      const nextControlValue = await slider.inputValue();
      if (nextControlValue === currentControlValue) {
        captureFailure =
          "the fixed author resize control did not advance through its keyboard operation";
        break;
      }
      const captured = await captureState();
      if (captured.document_identity !== request.target_identity) {
        captureFailure = "the author resize control changed the current document identity";
        break;
      }
      populationComplete = populationComplete && captured.population_complete;
      const currentRefs = new Set(captured.text_candidates.map((row) => row.target_ref));
      const contentLossRefs = [...baselineRefs].filter((ref) => !currentRefs.has(ref)).sort();
      if ([...currentRefs].some((ref) => !baselineRefs.has(ref))) populationComplete = false;
      const observedCandidates = [
        ...captured.text_candidates,
        ...contentLossRefs.map((target_ref) => ({
          target_ref,
          present: false,
          used_font_size_css_px: null,
          rects: [],
          clipped: false,
          obscured: false,
        })),
      ].sort((left, right) =>
        left.target_ref < right.target_ref ? -1 : left.target_ref > right.target_ref ? 1 : 0,
      );
      const previous = sequence[sequence.length - 1];
      const previousControls = new Map(
        previous.interactive_controls.map((row) => [row.target_ref, row.enabled]),
      );
      const currentControls = new Map(
        captured.interactive_controls.map((row) => [row.target_ref, row.enabled]),
      );
      const functionalityLossRefs = [...previousControls]
        .filter(
          ([ref, enabled]) => enabled && (!currentControls.has(ref) || !currentControls.get(ref)),
        )
        .map(([ref]) => ref)
        .sort();
      const previousClipped = new Set(
        previous.text_candidates.filter((row) => row.clipped).map((row) => row.target_ref),
      );
      const previousObscured = new Set(
        previous.text_candidates.filter((row) => row.obscured).map((row) => row.target_ref),
      );
      const newlyClippedTargetRefs = captured.text_candidates
        .filter((row) => row.clipped && !previousClipped.has(row.target_ref))
        .map((row) => row.target_ref);
      const newlyObscuredTargetRefs = captured.text_candidates
        .filter((row) => row.obscured && !previousObscured.has(row.target_ref))
        .map((row) => row.target_ref);
      sequence.push({
        state_index: sequence.length,
        control_value: nextControlValue,
        ...captured,
        text_candidates: observedCandidates,
        content_loss_refs: contentLossRefs,
        newly_clipped_target_refs: newlyClippedTargetRefs.sort(),
        newly_obscured_target_refs: newlyObscuredTargetRefs.sort(),
        functionality_loss_refs: functionalityLossRefs,
      });

      const baselineByRef = new Map(
        sequence[0].text_candidates.map((row) => [row.target_ref, row.used_font_size_css_px]),
      );
      const reachedTarget =
        populationComplete &&
        sequence[sequence.length - 1].text_candidates.length === baselineRefs.size &&
        sequence[sequence.length - 1].text_candidates.every((row) => {
          const base = baselineByRef.get(row.target_ref);
          if (!row.present || base === undefined || row.used_font_size_css_px === null)
            return false;
          const parse = (text) => {
            const [whole, fraction = ""] = text.split(".");
            return { value: BigInt(whole + fraction), scale: fraction.length };
          };
          const current = parse(row.used_font_size_css_px);
          const baselineSize = parse(base);
          return (
            current.value * 10n ** BigInt(baselineSize.scale) >=
            2n * baselineSize.value * 10n ** BigInt(current.scale)
          );
        });
      if (reachedTarget || decimal(nextControlValue) >= decimal(control.maximum_value)) {
        stateSequenceComplete = true;
        break;
      }
    }
    if (!stateSequenceComplete && captureFailure === null)
      captureFailure = "the fixed resize state sequence exceeded its bounded step count";
  } catch {
    captureFailure = "fixed Resize Text observation could not be completed";
  } finally {
    try {
      let current = await slider.inputValue();
      for (let index = 0; current !== restoreValue && index < 100; index++) {
        await slider.press(decimal(current) > decimal(restoreValue) ? "ArrowLeft" : "ArrowRight");
        await page.waitForTimeout(40);
        const next = await slider.inputValue();
        if (next === current) break;
        current = next;
      }
      if (current !== restoreValue)
        captureFailure =
          captureFailure || "the resize control did not restore its baseline state during cleanup";
    } catch {
      captureFailure = captureFailure || "resize control cleanup could not be verified";
    }
  }

  const value = {
    schema: "wcag-resize-text-observation-v1",
    resize_mechanism: "author-provided-resize-control",
    control,
    mechanism_state_sequence: sequence,
    text_population_complete: populationComplete,
    mechanism_state_sequence_complete: stateSequenceComplete,
    cleanup: {
      status: captureFailure === null ? "restored" : "unverified",
      baseline_control_value: restoreValue,
      current_control_value: await slider.inputValue().catch(() => null),
    },
  };
  const resultIdentity = Object.fromEntries(identityFields.map((key) => [key, request[key]]));
  const unreadableTextState = sequence.some(
    (row) => row.unsupported_visible_canvas || row.unmeasurable_target_refs.length > 0,
  );
  const inaccessibleFrame = sequence.some((row) => row.inaccessible_visible_frame);
  if (
    captureFailure === null &&
    stateSequenceComplete &&
    unreadableTextState &&
    !inaccessibleFrame &&
    value.cleanup.status === "restored" &&
    value.cleanup.current_control_value === restoreValue
  ) {
    return {
      ...resultIdentity,
      status: "unavailable",
      current_document_identity: await currentDocumentIdentity(),
      evidence_refs: evidenceRefs,
      value,
      limitation:
        "the author text-scaling control completed its bounded state sequence, but rendered canvas or non-pixel text metrics prevent machine-readable scale closure",
      limitation_code: "text-scaling-state-not-machine-readable",
    };
  }
  if (
    captureFailure !== null ||
    !populationComplete ||
    !stateSequenceComplete ||
    value.cleanup.status !== "restored" ||
    value.cleanup.current_control_value !== restoreValue
  ) {
    return {
      ...resultIdentity,
      status: "blocked",
      current_document_identity: await currentDocumentIdentity(),
      evidence_refs: evidenceRefs,
      value,
      limitation:
        captureFailure || "the fixed text population or mechanism state sequence is incomplete",
    };
  }
  return {
    ...resultIdentity,
    status: "ok",
    current_document_identity: await currentDocumentIdentity(),
    evidence_refs: evidenceRefs,
    value,
  };
}
