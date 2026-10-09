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
  const interactiveSelector =
    "a[href],button,input,select,textarea,[role='button'],[role='link'],[role='checkbox'],[role='radio'],[role='slider'],[role='switch'],[role='tab'],[role='menuitem'],[role='menuitemcheckbox'],[role='menuitemradio'],[role='option'],[role='combobox'],[role='listbox'],[role='textbox'],[role='searchbox'],[role='spinbutton'],[tabindex]:not([tabindex='-1'])";

  const elementPathFor = (element) => {
    const parts = [];
    let current = element;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      const parent = current.parentElement;
      const root = current.getRootNode();
      const siblingContainer = parent || (root instanceof ShadowRoot ? root : null);
      const peers = siblingContainer
        ? Array.from(siblingContainer.children).filter((peer) => peer.tagName === current.tagName)
        : [current];
      parts.unshift(
        current.tagName.toLowerCase() + ":nth-of-type(" + (peers.indexOf(current) + 1) + ")",
      );
      if (parent) {
        current = parent;
      } else if (root instanceof ShadowRoot) {
        parts.unshift("::shadow");
        current = root.host;
      } else {
        current = null;
      }
    }
    return parts.join(" > ");
  };

  const captureFocusSequence = async (maxSteps, singleTarget = false) => {
    const focusedLocators = page.locator(":focus");
    const originalFocus = await focusedLocators
      .last()
      .elementHandle()
      .catch(() => page.evaluateHandle(() => document.activeElement));
    const originalScroll = await page.evaluate(() => ({ x: scrollX, y: scrollY }));
    const sequence = [];
    const seen = new Map();
    let cycleDetected = false;
    let cycleStartIndex = null;
    let cycleKind = null;
    let limitReached = false;
    let focusLeftDocument = false;
    let focusTargetRemoved = false;
    let captureError = null;
    const limit = Math.min(Math.max(1, maxSteps), 64);
    try {
      for (let index = 0; index < limit; index++) {
        const previousFocus = await page.locator(":focus").last().elementHandle().catch(() => null);
        await page.keyboard.press("Tab");
        if (previousFocus) {
          try {
            if (!(await previousFocus.evaluate((element) => element.isConnected))) {
              focusTargetRemoved = true;
              break;
            }
          } catch {
            focusTargetRemoved = true;
            break;
          } finally {
            await previousFocus.dispose().catch(() => {});
          }
        }
        const activeLocators = page.locator(":focus");
        const activeCount = await activeLocators.count();
        if (activeCount === 0) {
          focusLeftDocument = true;
          sequence.push({
            state_index: sequence.length,
            target_ref: null,
            role: null,
            tag_name: "document",
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
          });
          break;
        }
        const focused = activeLocators.last();
        const isDocumentFocus = await focused.evaluate(
          (element) => element === document.body || element === document.documentElement,
        );
        if (isDocumentFocus) {
          focusLeftDocument = true;
          sequence.push({
            state_index: sequence.length,
            target_ref: null,
            role: null,
            tag_name: "document",
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
          });
          break;
        }
        const targetPath = await focused.evaluate(elementPathFor);
        const targetRef = "focused-element:" + targetPath;
        if (seen.has(targetRef)) {
          cycleDetected = true;
          cycleStartIndex = seen.get(targetRef);
          cycleKind = cycleStartIndex === 0 && sequence.length > 1 ? "returns-to-start" : "focus-loop";
          break;
        }
        const semanticTree = await focused.ariaSnapshotJSON({ depth: 0, timeout: 1000 });
        if (
          !Array.isArray(semanticTree) ||
          semanticTree.length > 1 ||
          (semanticTree.length === 1 && typeof semanticTree[0]?.role !== "string")
        ) {
          captureError = "focused target accessibility role could not be confirmed";
          break;
        }
        const role = semanticTree.length === 1 ? semanticTree[0].role : null;
        const visible = await focused.isVisible();
        const box = await focused.boundingBox();
        const style = await focused.evaluate((element) => {
          const computed = getComputedStyle(element);
          return {
            tag_name: element.tagName.toLowerCase(),
            outline_style: computed.outlineStyle,
            outline_width: computed.outlineWidth,
            outline_color: computed.outlineColor,
            border: {
              width: computed.borderWidth,
              style: computed.borderStyle,
              color: computed.borderColor,
              radius: computed.borderRadius,
            },
            background_color: computed.backgroundColor,
            background_image_present: computed.backgroundImage !== "none",
            box_shadow: computed.boxShadow,
          };
        });
        const overlays = await page.locator("body *").evaluateAll(
          (elements, target) => {
            const pathFor = (element) => {
              const parts = [];
              let current = element;
              while (current && current.nodeType === Node.ELEMENT_NODE) {
                const parent = current.parentElement;
                const root = current.getRootNode();
                const siblingContainer = parent || (root instanceof ShadowRoot ? root : null);
                const peers = siblingContainer
                  ? Array.from(siblingContainer.children).filter(
                      (peer) => peer.tagName === current.tagName,
                    )
                  : [current];
                parts.unshift(
                  current.tagName.toLowerCase() + ":nth-of-type(" + (peers.indexOf(current) + 1) + ")",
                );
                if (parent) {
                  current = parent;
                } else if (root instanceof ShadowRoot) {
                  parts.unshift("::shadow");
                  current = root.host;
                } else {
                  current = null;
                }
              }
              return parts.join(" > ");
            };
            const rect = target.rect;
            if (!rect) return [];
            return elements
              .filter((candidate) => {
                const candidatePath = pathFor(candidate);
                if (
                  candidatePath === target.path ||
                  target.path.startsWith(candidatePath + " > ")
                ) return false;
                const style = getComputedStyle(candidate);
                if (!["fixed", "sticky"].includes(style.position) ||
                    style.display === "none" ||
                    style.visibility === "hidden" ||
                    style.visibility === "collapse") return false;
                const overlayRect = candidate.getBoundingClientRect();
                return overlayRect.width > 0 && overlayRect.height > 0 &&
                  overlayRect.left < rect.x + rect.width &&
                  overlayRect.right > rect.x &&
                  overlayRect.top < rect.y + rect.height &&
                  overlayRect.bottom > rect.y;
              })
              .slice(0, 20)
              .map((candidate) => "dom-overlay:" + pathFor(candidate));
          },
          { path: targetPath, rect: box },
        );
        const shadows = style.box_shadow;
        let shadowDepth = 0;
        let shadowCount = shadows && shadows !== "none" ? 1 : 0;
        for (const character of shadows || "") {
          if (character === "(") shadowDepth += 1;
          else if (character === ")") shadowDepth = Math.max(0, shadowDepth - 1);
          else if (character === "," && shadowDepth === 0) shadowCount += 1;
        }
        seen.set(targetRef, sequence.length);
        sequence.push({
          state_index: sequence.length,
          target_ref: targetRef,
          role,
          tag_name: style.tag_name,
          visible,
          rect_css_px: box,
          outline_style: style.outline_style,
          outline_width: style.outline_width,
          outline_color: style.outline_color,
          border: style.border,
          background_color: style.background_color,
          background_image_present: style.background_image_present,
          box_shadow_layer_count: shadowCount,
          fixed_overlay_overlap_refs: overlays,
        });
        if (singleTarget) break;
      }
      limitReached = !singleTarget && !cycleDetected && sequence.length >= limit &&
        sequence.at(-1)?.target_ref !== null;
    } catch {
      captureError = "fixed keyboard focus sequence could not be captured";
    } finally {
      try {
        await originalFocus.evaluate((element) => {
          if (element && element.isConnected && typeof element.focus === "function") element.focus();
          let active = document.activeElement;
          while (active?.shadowRoot?.activeElement) active = active.shadowRoot.activeElement;
          if (active !== element) throw new Error("focus restoration did not match");
        });
        await page.evaluate((position) => window.scrollTo(position.x, position.y), originalScroll);
        const restoredScroll = await page.evaluate(() => ({ x: scrollX, y: scrollY }));
        if (restoredScroll.x !== originalScroll.x || restoredScroll.y !== originalScroll.y)
          throw new Error("scroll restoration did not match");
      } catch {
        captureError = captureError || "focus or scroll restoration could not be verified";
      }
      await originalFocus.dispose().catch(() => {});
    }
    const partialReason = focusTargetRemoved
      ? "focus-target-removed"
      : focusLeftDocument
        ? "focus-left-document"
        : limitReached
      ? "focus-observation-limit-reached"
      : cycleDetected
        ? cycleKind === "returns-to-start"
          ? "focus-cycle-not-complete"
          : "focus-loop-detected"
        : null;
    return {
      sequence,
      cycle_detected: cycleDetected,
      cycle_start_index: cycleStartIndex,
      cycle_kind: cycleKind,
      limit_reached: limitReached,
      focus_left_document: focusLeftDocument,
      focus_target_removed: focusTargetRemoved,
      ...(partialReason
        ? { observation_completeness: { state: "partial", reason: partialReason } }
        : {}),
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
      return resultFor({
        status: trace.observation_completeness ? "incomplete" : "ok",
        value,
        ...(trace.observation_completeness
          ? { limitation: "the fixed keyboard focus observation reached its documented limit or detected a focus loop" }
          : {}),
      });
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
    const trace = await captureFocusSequence(1, true);
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
    const styleMarker = "data-qa-fixed-wcag-text-spacing-probe";
    const styleText =
      "* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; }" +
      "p { margin-block-end: 2em !important; }";
    const baseline = await page.evaluate(
      (id) => ({
        style_collision: Boolean(document.getElementById(id)),
        viewport: { width_css_px: innerWidth, height_css_px: innerHeight },
        document_overflow: {
          horizontal_css_px: Math.max(0, document.documentElement.scrollWidth - innerWidth),
          vertical_css_px: Math.max(0, document.documentElement.scrollHeight - innerHeight),
        },
      }),
      styleId,
    );
    baseline.control_count = await page.locator(interactiveSelector).count();
    baseline.style_collision =
      baseline.style_collision || (await page.locator(`style[${styleMarker}]`).count()) > 0;
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
      styleHandle = await page.addStyleTag({ content: styleText });
      await styleHandle.evaluate((element, id) => {
        element.id = id;
        element.setAttribute("data-qa-fixed-wcag-text-spacing-probe", "");
      }, styleId);
      const shadowRootCount = await page.locator("body *").evaluateAll((elements, args) => {
        const roots = new Set();
        for (const element of elements) {
          const root = element.getRootNode();
          if (root instanceof ShadowRoot) roots.add(root);
        }
        for (const root of roots) {
          const style = root.ownerDocument.createElement("style");
          style.setAttribute(args.marker, "");
          style.textContent = args.css;
          root.appendChild(style);
        }
        return roots.size;
      }, { marker: styleMarker, css: styleText });
      after = await page.locator("body *").evaluateAll((elements, args) => {
        const clipped = [];
        let visibleTextOwnerCount = 0;
        let overrideMismatchCount = 0;
        const pathFor = (element) => {
          const parts = [];
          let current = element;
          while (current && current.nodeType === Node.ELEMENT_NODE) {
            const parent = current.parentElement;
            const root = current.getRootNode();
            const siblingContainer = parent || (root instanceof ShadowRoot ? root : null);
            const peers = siblingContainer
              ? Array.from(siblingContainer.children).filter((peer) => peer.tagName === current.tagName)
              : [current];
            parts.unshift(
              current.tagName.toLowerCase() + ":nth-of-type(" + (peers.indexOf(current) + 1) + ")",
            );
            if (parent) {
              current = parent;
            } else if (root instanceof ShadowRoot) {
              parts.unshift("::shadow");
              current = root.host;
            } else {
              current = null;
            }
          }
          return parts.join(" > ");
        };
        for (const element of elements) {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          if (
            style.display === "none" ||
            style.visibility === "hidden" ||
            rect.width <= 0 ||
            rect.height <= 0
          )
            continue;
          const hasDirectText = Array.from(element.childNodes).some(
            (node) => node.nodeType === Node.TEXT_NODE && /\S/u.test(node.nodeValue || ""),
          );
          if (hasDirectText) {
            visibleTextOwnerCount += 1;
            const fontSize = Number.parseFloat(style.fontSize);
            const lineHeight = Number.parseFloat(style.lineHeight);
            const letterSpacing = Number.parseFloat(style.letterSpacing);
            const wordSpacing = Number.parseFloat(style.wordSpacing);
            if (
              !Number.isFinite(fontSize) ||
              !Number.isFinite(lineHeight) ||
              !Number.isFinite(letterSpacing) ||
              !Number.isFinite(wordSpacing) ||
              Math.abs(lineHeight - fontSize * 1.5) > 0.5 ||
              Math.abs(letterSpacing - fontSize * 0.12) > 0.5 ||
              Math.abs(wordSpacing - fontSize * 0.16) > 0.5
            ) {
              overrideMismatchCount += 1;
            }
          }
          if (
            element.tagName.toLowerCase() === "p" &&
            Math.abs(Number.parseFloat(style.marginBlockEnd) - Number.parseFloat(style.fontSize) * 2) > 0.5
          ) {
            overrideMismatchCount += 1;
          }
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
          open_shadow_root_count: args.shadowRootCount,
          visible_text_owner_count: visibleTextOwnerCount,
          override_mismatch_count: overrideMismatchCount,
          clipped_target_count: clipped.length,
          returned_clipped_target_count: Math.min(clipped.length, 100),
          clipped_targets: clipped.slice(0, 100),
          applied_values: {
            line_height: "1.5",
            letter_spacing: "0.12em",
            word_spacing: "0.16em",
            paragraph_spacing: "2em",
          },
        };
      }, { shadowRootCount });
      after.control_count = await page.locator(interactiveSelector).count();
    } catch {
      cleanupError = "fixed text-spacing observation could not be completed";
    } finally {
      try {
        await page.locator(`style[${styleMarker}]`).evaluateAll((styles) => {
          styles.forEach((element) => element.remove());
        });
        if ((await page.locator(`style[${styleMarker}]`).count()) > 0) {
          cleanupError = cleanupError || "fixed text-spacing override remained after cleanup";
        }
      } catch {
        cleanupError = cleanupError || "fixed text-spacing cleanup could not be verified";
      }
      if (styleHandle) {
        try {
          await styleHandle.dispose();
        } catch {
          cleanupError = cleanupError || "fixed style cleanup could not be verified";
        }
      }
    }
    if (cleanupError === null) {
      const markerRemains = await page.locator(`style#${styleId}`).count();
      if (markerRemains > 0) cleanupError = "fixed text-spacing override remained in the document after cleanup";
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
    if (after.override_mismatch_count > 0 || after.visible_text_owner_count === 0) {
      return resultFor({
        status: "incomplete",
        value: {
          schema: "wcag-text-spacing-v1",
          observation_completeness: { state: "partial", reason: "text-spacing-override-not-applied" },
          baseline,
          after,
          cleanup: { status: "restored" },
        },
        limitation: "the requested text-spacing values could not be verified on the observed text population",
      });
    }
    if (after.clipped_target_count > 100) {
      return resultFor({
        status: "incomplete",
        value: {
          schema: "wcag-text-spacing-v1",
          observation_completeness: { state: "partial", reason: "probe-result-limit-reached" },
          baseline,
          after,
          cleanup: { status: "restored" },
        },
        limitation: "the clipped-target list exceeded its fixed result limit",
      });
    }
    return resultFor({
      status: "ok",
      value: { schema: "wcag-text-spacing-v1", baseline, after, cleanup: { status: "restored" } },
    });
  }

  const locatorSelectorsByProbe = {
    "mp-document-title": [],
    "mp-document-language": [],
    "mp-part-language-inventory": ["[lang],[xml\\:lang]"],
    "mp-purpose-metadata": [interactiveSelector],
    "mp-nontext-content-inventory": [
      "img,svg,canvas,object,embed,iframe,video,audio,input[type='image'],[role='img']",
    ],
    "mp-media-inventory": ["audio,video"],
    "mp-moving-updating-inventory": [
      "marquee,blink,[aria-live],svg animate,svg animateMotion,svg animateTransform",
      "*",
    ],
    "mp-timer-inventory": [
      "time,meter,progress,[role='timer'],[role='progressbar'],[role='countdown']",
      "meta[http-equiv='refresh' i]",
    ],
    "mp-shortcut-inventory": ["[accesskey]"],
    "mp-form-control-inventory": [
      "input,select,textarea,button,[role='checkbox'],[role='radio'],[role='slider'],[role='switch'],[role='combobox'],[role='listbox'],[role='textbox'],[role='searchbox'],[role='spinbutton']",
    ],
    "mp-heading-label-inventory": ["h1,h2,h3,h4,h5,h6,[role='heading']", "label"],
    "mp-link-inventory": ["a[href],[role='link']"],
    "mp-structure-inventory": [
      "main,nav,header,footer,aside,section,article,form,fieldset,ul,ol,dl,table,thead,tbody,tr,th,td,h1,h2,h3,h4,h5,h6,[role='main'],[role='navigation'],[role='list'],[role='table'],[role='row'],[role='cell'],[role='columnheader']",
    ],
    "mp-sequence-inventory": [
      "main,nav,header,footer,h1,h2,h3,h4,h5,h6," + interactiveSelector,
    ],
    "mp-component-semantics": [interactiveSelector],
    "mp-status-candidate-inventory": ["[role='status'],[role='alert'],[aria-live]"],
    "mp-neighbor-geometry": [interactiveSelector],
    "mp-text-presentation-values": ["*"],
    "mp-viewport-state": [],
    "mp-reflow-run": ["*"],
    "mp-orientation-run": [],
    "mp-audio-autoplay-run": ["audio,video"],
    "mp-control-value-history": [interactiveSelector],
    "mp-multipage-signature": [interactiveSelector],
    "mp-hover-focus-content-run": [interactiveSelector],
    "mp-change-trigger-run": [interactiveSelector],
    "mp-pointer-interaction-run": [interactiveSelector],
    "mp-error-scenario-run": ["form"],
  };
  const semanticProbeKeys = new Set([
    "mp-purpose-metadata",
    "mp-nontext-content-inventory",
    "mp-moving-updating-inventory",
    "mp-timer-inventory",
    "mp-shortcut-inventory",
    "mp-form-control-inventory",
    "mp-heading-label-inventory",
    "mp-link-inventory",
    "mp-structure-inventory",
    "mp-sequence-inventory",
    "mp-component-semantics",
    "mp-status-candidate-inventory",
    "mp-neighbor-geometry",
    "mp-control-value-history",
    "mp-multipage-signature",
    "mp-hover-focus-content-run",
    "mp-change-trigger-run",
    "mp-pointer-interaction-run",
  ]);
  const locatorRegistrySymbol = "qa-workflow-skills.fixed-wcag-locator-observations.v1";
  const pathsForLocatorElements = (elements) =>
    elements.map((element) => {
      const parts = [];
      let current = element;
      while (current && current.nodeType === Node.ELEMENT_NODE) {
        const parent = current.parentElement;
        const root = current.getRootNode();
        const siblingContainer = parent || (root instanceof ShadowRoot ? root : null);
        const peers = siblingContainer
          ? Array.from(siblingContainer.children).filter((peer) => peer.tagName === current.tagName)
          : [current];
        parts.unshift(
          current.tagName.toLowerCase() + ":nth-of-type(" + (peers.indexOf(current) + 1) + ")",
        );
        if (parent) {
          current = parent;
        } else if (root instanceof ShadowRoot) {
          parts.unshift("::shadow");
          current = root.host;
        } else {
          current = null;
        }
      }
      return parts.join(" > ");
    });
  const specializedProbeKeys = new Set([
    "mp-resize-text-run",
    "mp-computed-color-context",
    "mp-focus-appearance-evidence",
    "mp-target-geometry",
  ]);
  let catalogued = null;
  const locatorSelectors = locatorSelectorsByProbe[request.machine_probe_key];
  if (!specializedProbeKeys.has(request.machine_probe_key) && locatorSelectors) {
    try {
      await page.evaluate((slot) => {
        Object.defineProperty(window, Symbol.for(slot), {
          configurable: true,
          value: { elements: new Map(), metadata: new WeakMap() },
        });
      }, locatorRegistrySymbol);
      const needsAccessibility = (selector) =>
        semanticProbeKeys.has(request.machine_probe_key) &&
        !(request.machine_probe_key === "mp-moving-updating-inventory" && selector === "*");
      for (const selector of new Set(locatorSelectors)) {
        const locator = page.locator(selector);
        const paths = await locator.evaluateAll(pathsForLocatorElements);
        await locator.evaluateAll(
          (elements, args) => {
            const registry = window[Symbol.for(args.slot)];
            if (!registry) throw new Error("fixed locator registry unavailable");
            registry.elements.set(args.selector, elements);
          },
          { slot: locatorRegistrySymbol, selector },
        );
        const metadata = [];
        for (let index = 0; index < paths.length; index += 1) {
          const item = locator.nth(index);
          const record = { path: paths[index], visible: await item.isVisible() };
          if (needsAccessibility(selector)) {
            record.enabled = await item.isEnabled();
            const snapshot = await item.ariaSnapshotJSON({ depth: 0, timeout: 1000 });
            if (!Array.isArray(snapshot) || snapshot.length > 1) {
              throw new Error("fixed accessibility projection is ambiguous");
            }
            if (snapshot.length === 1) {
              const node = snapshot[0];
              if (!node || typeof node.role !== "string") {
                throw new Error("fixed accessibility role unavailable");
              }
              record.accessibility_tree_includes_element = true;
              record.accessible_role = node.role;
              record.accessible_name_present =
                typeof node.name === "string" && node.name.trim().length > 0;
              if (request.machine_probe_key !== "mp-component-semantics") {
                record.accessible_name = typeof node.name === "string" ? node.name : "";
              }
            } else {
              record.accessibility_tree_includes_element = false;
              record.accessible_role = null;
              record.accessible_name_present = null;
              if (request.machine_probe_key !== "mp-component-semantics") {
                record.accessible_name = null;
              }
            }
          }
          metadata.push(record);
        }
        const currentPaths = await locator.evaluateAll(pathsForLocatorElements);
        if (
          currentPaths.length !== paths.length ||
          currentPaths.some((path, index) => path !== paths[index])
        ) {
          throw new Error("fixed locator population changed during observation");
        }
        await page.evaluate(
          ({ slot, selector: query, rows }) => {
            const registry = window[Symbol.for(slot)];
            const elements = registry?.elements.get(query);
            if (!Array.isArray(elements) || elements.length !== rows.length) {
              throw new Error("fixed locator metadata could not be matched");
            }
            elements.forEach((element, index) => registry.metadata.set(element, rows[index]));
          },
          { slot: locatorRegistrySymbol, selector, rows: metadata },
        );
      }
      catalogued = await page.evaluate(({ key, slot, interactive }) => {
        const registry = window[Symbol.for(slot)];
        const observationFor = (element) => registry?.metadata.get(element) || null;
        const located = (selector) => {
          const elements = registry?.elements.get(selector);
          if (!Array.isArray(elements)) throw new Error("fixed locator selector was not materialized");
          return elements;
        };
        const allVisible = (selector) =>
          located(selector).filter((element) => observationFor(element)?.visible === true);
        const allVisibleOrInAccessibilityTree = (selector) =>
          located(selector).filter((element) => {
            const observation = observationFor(element);
            return (
              observation?.visible === true ||
              observation?.accessibility_tree_includes_element === true
            );
          });
        const pathFor = (element) => {
          const observedPath = observationFor(element)?.path;
          if (typeof observedPath === "string") return observedPath;
          const parts = [];
          let current = element;
          while (current && current.nodeType === Node.ELEMENT_NODE) {
            const parent = current.parentElement;
            const root = current.getRootNode();
            const siblingContainer = parent || (root instanceof ShadowRoot ? root : null);
            const peers = siblingContainer
              ? Array.from(siblingContainer.children).filter(
                  (peer) => peer.tagName === current.tagName,
                )
              : [current];
            parts.unshift(
              current.tagName.toLowerCase() + ":nth-of-type(" + (peers.indexOf(current) + 1) + ")",
            );
            if (parent) current = parent;
            else if (root instanceof ShadowRoot) {
              parts.unshift("::shadow");
              current = root.host;
            } else current = null;
          }
          return parts.join(" > ");
        };
        const visible = (element) => {
          const observation = observationFor(element);
          if (observation) return observation.visible;
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.visibility !== "collapse" &&
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
        const textOf = (element) => safeText(element?.innerText || "");
        const refOf = (element, prefix = "dom-target") => prefix + ":" + pathFor(element);
        const interactiveElements = () => allVisibleOrInAccessibilityTree(interactive);
        const statesOf = (element) => ({
          disabled:
            typeof observationFor(element)?.enabled === "boolean"
              ? !observationFor(element).enabled
              : Boolean(element.disabled || element.getAttribute("aria-disabled") === "true"),
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
        const roleOf = (element) => observationFor(element)?.accessible_role ?? null;
        const accessibleName = (element) => {
          const name = observationFor(element)?.accessible_name;
          return typeof name === "string" ? safeText(name) : null;
        };
        const accessibleNamePresent = (element) => {
          const observation = observationFor(element);
          if (typeof observation?.accessible_name_present === "boolean") {
            return observation.accessible_name_present;
          }
          const name = observation?.accessible_name;
          return typeof name === "string" && safeText(name).trim().length > 0;
        };
        const accessibilityTreeIncludes = (element) =>
          observationFor(element)?.accessibility_tree_includes_element === true;
        const composedParent = (element) =>
          element.parentElement ||
          (element.getRootNode() instanceof ShadowRoot ? element.getRootNode().host : null);
        const hasComposedAncestor = (element, selector) => {
          let current = element;
          while (current) {
            if (current.matches(selector)) return true;
            current = composedParent(current);
          }
          return false;
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
            const htmlNamespace = "http://www.w3.org/1999/xhtml";
    const htmlContentType = ["text/html", "application/xhtml+xml"].includes(
      document.contentType?.toLowerCase(),
    );
    const isHtmlDocument =
      htmlContentType &&
      document.documentElement?.namespaceURI === htmlNamespace &&
      document.documentElement?.localName === "html";
            const titleElement = isHtmlDocument
              ? Array.from(document.getElementsByTagNameNS(htmlNamespace, "title"))[0] || null
              : null;
            const firstTitleChildrenAreText = Boolean(
              titleElement &&
                titleElement.childNodes.length > 0 &&
                Array.from(titleElement.childNodes).every((node) => node.nodeType === Node.TEXT_NODE),
            );
            const hasNonWhitespaceText = Boolean(
              titleElement && /\P{White_Space}/u.test(titleElement.textContent || ""),
            );
            return {
              status: "ok",
              value: value({
                is_html_document: isHtmlDocument,
                has_title_element: Boolean(titleElement),
                first_title_children_are_text: firstTitleChildrenAreText,
                has_non_whitespace_text: hasNonWhitespaceText,
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
                controls: interactiveElements().map((element) => ({
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
            const media = located("audio,video");
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
            const movingElements = new Set(allVisible(
              "marquee,blink,[aria-live],svg animate,svg animateMotion,svg animateTransform",
            ));
            for (const element of allVisible("*")) {
              const style = getComputedStyle(element);
              if (
                style.animationName !== "none" ||
                style.animationDuration.split(",").some((item) => parseFloat(item) > 0)
              ) {
                movingElements.add(element);
              }
            }
            const candidates = Array.from(movingElements, (element) => {
              const style = getComputedStyle(element);
              return {
                target_ref: refOf(element),
                tag_name: element.tagName.toLowerCase(),
                role: roleOf(element),
                aria_live: element.getAttribute("aria-live"),
                aria_atomic: element.getAttribute("aria-atomic"),
                animation_name: style.animationName,
                animation_duration: style.animationDuration,
                paused_control_present: Boolean(element.querySelector("button,[role='button']")),
              };
            });
            const resultValue = value({
              candidate_count: candidates.length,
              returned_candidate_count: Math.min(candidates.length, 200),
              candidates: candidates.slice(0, 200),
              ...(candidates.length > 200
                ? { observation_completeness: { state: "partial", reason: "probe-result-limit-reached" } }
                : {}),
            });
            return candidates.length > 200
              ? {
                  status: "incomplete",
                  value: resultValue,
                  limitation: "the moving-content candidate list exceeded its fixed result limit",
                }
              : { status: "ok", value: resultValue };
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
            const refresh = located("meta[http-equiv='refresh' i]")[0] || null;
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
                controls: allVisibleOrInAccessibilityTree(
                  "input,select,textarea,button,[role='checkbox'],[role='radio'],[role='slider'],[role='switch'],[role='combobox'],[role='listbox'],[role='textbox'],[role='searchbox'],[role='spinbutton']",
                ).map((element) => ({
                  target_ref: refOf(element),
                  tag_name: element.tagName.toLowerCase(),
                  type: element.getAttribute("type"),
                  role: roleOf(element),
                  accessible_name: accessibleName(element),
                  included_in_accessibility_tree: accessibilityTreeIncludes(element),
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
                components: interactiveElements().map((element) => ({
                  target_ref: refOf(element),
                  tag_name: element.tagName.toLowerCase(),
                  role: roleOf(element),
                  accessible_name_present: accessibilityTreeIncludes(element)
                    ? accessibleNamePresent(element)
                    : null,
                  description_present: Boolean(element.getAttribute("aria-describedby")),
                  states: statesOf(element),
                  host_type:
                    element instanceof HTMLInputElement
                      ? element.type
                      : element.getAttribute("type"),
                  included_in_accessibility_tree: accessibilityTreeIncludes(element),
                  programmatically_hidden: hasComposedAncestor(
                    element,
                    "[aria-hidden='true'],[hidden],[inert]",
                  ),
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
            const targets = interactiveElements()
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
            let neighboringPairCount = 0;
            let resultLimitReached = false;
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
                  neighboringPairCount += 1;
                  if (pairs.length < 500) {
                    pairs.push({
                      first_target_ref: first.target_ref,
                      second_target_ref: second.target_ref,
                      horizontal_gap_css_px: horizontalGap,
                      vertical_gap_css_px: verticalGap,
                    });
                  } else {
                    resultLimitReached = true;
                    break;
                  }
                }
              }
              if (resultLimitReached) break;
            }
            const resultValue = value({
              targets,
              neighboring_pairs: pairs,
              neighboring_pair_count_lower_bound: neighboringPairCount,
              neighboring_pair_count_complete: !resultLimitReached,
              returned_pair_count: pairs.length,
              ...(resultLimitReached
                ? { observation_completeness: { state: "partial", reason: "probe-result-limit-reached" } }
                : {}),
            });
            return resultLimitReached
              ? {
                  status: "incomplete",
                  value: resultValue,
                  limitation: "the neighboring-pair result exceeded its fixed limit",
                }
              : { status: "ok", value: resultValue };
          }
          case "mp-text-presentation-values": {
            const owners = allVisible("*").filter((element) =>
              Array.from(element.childNodes).some(
                (node) => node.nodeType === Node.TEXT_NODE && /\S/u.test(node.nodeValue || ""),
              ),
            );
            const targets = owners.slice(0, 500).map((element) => {
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
                  });
            const resultValue = value({
              text_owner_count: owners.length,
              returned_target_count: targets.length,
              targets,
              ...(owners.length > 500
                ? { observation_completeness: { state: "partial", reason: "probe-result-limit-reached" } }
                : {}),
            });
            return owners.length > 500
              ? {
                  status: "incomplete",
                  value: resultValue,
                  limitation: "the text-presentation target list exceeded its fixed result limit",
                }
              : { status: "ok", value: resultValue };
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
            const allOverflowTargets = allVisible("*")
              .filter((element) => {
                const rect = element.getBoundingClientRect();
                return (
                  rect.right > innerWidth + 1 ||
                  rect.left < -1 ||
                  ((getComputedStyle(element).overflowX === "hidden" ||
                    getComputedStyle(element).overflowX === "clip") &&
                    element.scrollWidth > element.clientWidth + 1)
                );
              });
            const overflowTargets = allOverflowTargets.slice(0, 200).map((element) => ({
                target_ref: refOf(element),
                geometry_css_px: rectOf(element),
                scroll_width_css_px: element.scrollWidth,
                client_width_css_px: element.clientWidth,
              }));
            const resultValue = value({
                required_viewport_css_px: { width: innerWidth, height: innerHeight },
                document_overflow_css_px: Math.max(
                  0,
                  document.documentElement.scrollWidth - innerWidth,
                ),
                overflow_target_count: allOverflowTargets.length,
                returned_overflow_target_count: overflowTargets.length,
                overflow_targets: overflowTargets,
                ...(allOverflowTargets.length > 200
                  ? { observation_completeness: { state: "partial", reason: "probe-result-limit-reached" } }
                  : {}),
              });
            return allOverflowTargets.length > 200
              ? {
                  status: "incomplete",
                  value: resultValue,
                  limitation: "the reflow overflow-target list exceeded its fixed result limit",
                }
              : { status: "ok", value: resultValue };
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
            const audio = located("audio,video");
            return {
              status: "incomplete",
              value: value({
                observation_completeness: {
                  state: "partial",
                  reason: "media-playback-origin-not-instrumented",
                },
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
                media_candidate_count: audio.length,
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
                controls: interactiveElements()
                .filter(
                  (element) =>
                    ["checkbox", "radio", "range"].includes(element.type) ||
                    element.tagName === "SELECT" ||
                    [
                      "checkbox",
                      "radio",
                      "switch",
                      "slider",
                      "spinbutton",
                      "combobox",
                      "listbox",
                      "option",
                      "textbox",
                      "searchbox",
                    ].includes(roleOf(element)),
                )
                .map((element) => ({
                  target_ref: refOf(element),
                  role: roleOf(element),
                  state: {
                    ...statesOf(element),
                    aria_checked: ["true", "false", "mixed"].includes(
                      element.getAttribute("aria-checked"),
                    )
                      ? element.getAttribute("aria-checked")
                      : null,
                    aria_selected: ["true", "false"].includes(
                      element.getAttribute("aria-selected"),
                    )
                      ? element.getAttribute("aria-selected")
                      : null,
                  },
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
                controls: interactiveElements().map((element) => ({
                    target_ref: refOf(element),
                    role: roleOf(element),
                    accessible_name_present: accessibilityTreeIncludes(element)
                      ? accessibleNamePresent(element)
                      : null,
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
                candidate_targets: interactiveElements().map((element) => ({
                  target_ref: refOf(element),
                  role: roleOf(element),
                  accessible_name_present: accessibilityTreeIncludes(element)
                    ? accessibleNamePresent(element)
                    : null,
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
                candidate_targets: interactiveElements()
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
                form_candidates: allVisible("form").map((form) => ({
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
                candidate_targets: interactiveElements().map((element) => ({
                  target_ref: refOf(element),
                  role: roleOf(element),
                  accessible_name_present: accessibilityTreeIncludes(element)
                    ? accessibleNamePresent(element)
                    : null,
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
      }, { key: request.machine_probe_key, slot: locatorRegistrySymbol, interactive: interactiveSelector });
    } catch {
      catalogued = {
        status: "blocked",
        limitation:
          "the fixed Playwright locator or browser accessibility projection could not be matched to a stable target population",
      };
    } finally {
      await page
        .evaluate((slot) => {
          delete window[Symbol.for(slot)];
        }, locatorRegistrySymbol)
        .catch(() => {});
    }
  } else if (!specializedProbeKeys.has(request.machine_probe_key)) {
    catalogued = {
      status: "blocked",
      limitation: "fixed WCAG machine probe key is not dispatched by this package",
    };
  }

  if (catalogued?.status === "ok") return resultFor(catalogued);
  if (catalogued?.status === "incomplete") return resultFor(catalogued);
  if (catalogued?.status === "blocked") return resultFor(catalogued);

  if (request.machine_probe_key === "mp-computed-color-context") {
    const context = await page.locator("body *").evaluateAll((locatedElements) => {
      const pathFor = (element) => {
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
          const parent = current.parentElement;
          const root = current.getRootNode();
          const siblingContainer = parent || (root instanceof ShadowRoot ? root : null);
          const peers = siblingContainer
            ? Array.from(siblingContainer.children).filter((peer) => peer.tagName === current.tagName)
            : [current];
          parts.unshift(`${current.tagName.toLowerCase()}:nth-of-type(${peers.indexOf(current) + 1})`);
          if (parent) current = parent;
          else if (root instanceof ShadowRoot) {
            parts.unshift("::shadow");
            current = root.host;
          } else current = null;
        }
        return parts.join(" > ");
      };
      const composedParent = (element) =>
        element.parentElement ||
        (element.getRootNode() instanceof ShadowRoot ? element.getRootNode().host : null);
      const composedContains = (ancestor, descendant) => {
        let current = descendant;
        while (current) {
          if (current === ancestor) return true;
          current = composedParent(current);
        }
        return false;
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
      for (const element of locatedElements) {
        if (
          Array.from(element.childNodes).some(
            (node) => node.nodeType === Node.TEXT_NODE && /\S/u.test(node.nodeValue || ""),
          ) &&
          rendered(element)
        ) {
          owners.add(element);
        }
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
          current = composedParent(current);
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
        computed_sample_count: computedSamples.length,
        computed_samples_complete: computedSamples.length === owners.size,
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
          computed_sample_count: context.computed_sample_count,
          computed_samples_complete: context.computed_samples_complete,
          unresolvable_background_kinds: context.unresolvable_background_kinds,
          affected_target_count: context.affected_target_count,
          computed_samples: context.computed_samples,
        },
        limitation:
          "a rendered text background uses a gradient, image, or blend context that cannot be resolved to one machine contrast value",
        limitation_code: "background-not-machine-resolvable",
      };
    }
    const resultValue = {
      schema: "wcag-computed-color-context-v1",
      rendered_text_owner_count: context.rendered_text_owner_count,
      computed_sample_count: context.computed_sample_count,
      computed_samples_complete: context.computed_samples_complete,
      unresolvable_background_kinds: [],
      affected_target_count: 0,
      computed_samples: context.computed_samples,
    };
    if (!context.computed_samples_complete) {
      return resultFor({
        status: "incomplete",
        value: {
          ...resultValue,
          observation_completeness: { state: "partial", reason: "probe-result-limit-reached" },
        },
        limitation: "the computed text-style sample list exceeded its fixed result limit",
      });
    }
    return {
      ...identity,
      status: "ok",
      current_document_identity: await currentDocumentIdentity(),
      evidence_refs: evidenceRefs,
      value: resultValue,
    };
  }

  if (request.machine_probe_key === "mp-target-geometry") {
    const selector =
      "a[href],button,input,select,textarea,[role='button'],[role='link'],[role='checkbox'],[role='radio'],[role='slider'],[role='switch'],[role='tab'],[role='menuitem'],[role='menuitemcheckbox'],[role='menuitemradio'],[role='option'],[role='combobox'],[role='listbox'],[role='textbox'],[role='searchbox'],[role='spinbutton'],img,svg,canvas,video,iframe";
    const locator = page.locator(selector);
    const targets = [];
    const targetRefs = new Set();
    const partialGeometryValue = (reason) => ({
      schema: "wcag-target-geometry-v1",
      observation_completeness: { state: "partial", reason },
      targets,
    });
    try {
      const initialCount = await locator.count();
      for (let index = 0; index < initialCount; index += 1) {
        const target = locator.nth(index);
        if (!(await target.isVisible())) continue;
        const rect = await target.boundingBox();
        if (!rect) {
          return resultFor({
            status: "incomplete",
            value: partialGeometryValue("target-not-materialized"),
            limitation: "Playwright could not resolve geometry for a visible target",
          });
        }
        const snapshot = await target.ariaSnapshotJSON({ depth: 0, timeout: 1000 });
        if (!Array.isArray(snapshot) || snapshot.length > 1) {
          return resultFor({
            status: "incomplete",
            value: partialGeometryValue("target-not-materialized"),
            limitation: "Playwright could not resolve one accessibility-tree projection for a target",
          });
        }
        const targetRef = `dom-target:${await target.evaluate(elementPathFor)}`;
        if (targetRefs.has(targetRef)) {
          return resultFor({
            status: "incomplete",
            value: partialGeometryValue("target-not-materialized"),
            limitation: "the fixed geometry probe could not uniquely identify each target",
          });
        }
        targetRefs.add(targetRef);
        targets.push({
          target_ref: targetRef,
          tag_name: await target.evaluate((element) => element.tagName.toLowerCase()),
          role:
            snapshot.length === 1 && typeof snapshot[0]?.role === "string"
              ? snapshot[0].role
              : null,
          included_in_accessibility_tree: snapshot.length === 1,
          focused: await target.evaluate((element) => element.matches(":focus")),
          geometry_css_px: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
        });
      }
      if ((await locator.count()) !== initialCount) {
        return resultFor({
          status: "incomplete",
          value: partialGeometryValue("population-changed-during-observation"),
          limitation: "the target population changed during geometry observation",
        });
      }
    } catch {
      return resultFor({
        status: "incomplete",
        value: partialGeometryValue("target-not-materialized"),
        limitation: "Playwright could not complete the fixed target geometry observation",
      });
    }
    if (targets.length === 0) {
      return failure(
        "blocked",
        "the fixed geometry probe could not establish visible target geometry",
      );
    }
    targets.sort((left, right) =>
      left.target_ref < right.target_ref ? -1 : left.target_ref > right.target_ref ? 1 : 0,
    );
    return resultFor({ status: "ok", value: { schema: "wcag-target-geometry-v1", targets } });
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

  const captureState = async () => {
    const locator = page.locator("body *");
    const state = await locator.evaluateAll(async (locatedElements) => {
      const elementPath = (element) => {
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
          const parent = current.parentElement;
          const root = current.getRootNode();
          const siblingContainer = parent || (root instanceof ShadowRoot ? root : null);
          const sameTag = siblingContainer
            ? Array.from(siblingContainer.children).filter((item) => item.tagName === current.tagName)
            : [current];
          parts.unshift(
            `${current.tagName.toLowerCase()}:nth-of-type(${sameTag.indexOf(current) + 1})`,
          );
          if (parent) current = parent;
          else if (root instanceof ShadowRoot) {
            parts.unshift("::shadow");
            current = root.host;
          } else current = null;
        }
        return parts.join(" > ");
      };
      const composedParent = (element) =>
        element.parentElement ||
        (element.getRootNode() instanceof ShadowRoot ? element.getRootNode().host : null);
      const composedContains = (ancestor, descendant) => {
        let current = descendant;
        while (current) {
          if (current === ancestor) return true;
          current = composedParent(current);
        }
        return false;
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
      const roots = [document.body];
      const seenRoots = new Set([document]);
      for (const element of locatedElements) {
        if (element.shadowRoot && !seenRoots.has(element.shadowRoot)) {
          seenRoots.add(element.shadowRoot);
          roots.push(element.shadowRoot);
        }
      }
      for (const root of roots) {
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
          const targetRef = `dom-text:${elementPath(owner)}/text[${textIndex}]`;
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
            ancestor = composedParent(ancestor);
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
            return !hit || (!composedContains(owner, hit) && !composedContains(hit, owner));
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
      }

      const controls = [];
      for (const root of roots) {
        const rootNode = root === document.body ? document : root;
        const elements = locatedElements.filter((element) => element.getRootNode() === rootNode);
        for (const element of elements) {
          if (!rendered(element)) continue;
          const path = elementPath(element);
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
          const isInteractive = element.matches(
            "a[href],button,input,select,textarea,[role='button'],[role='link'],[role='slider']",
          );
          if (isInteractive)
            controls.push({
              target_ref: `dom-control:${path}`,
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
      const unsupportedVisibleCanvas = locatedElements.some(
        (element) => element.matches("canvas") && rendered(element),
      );
      const visibleFrame = locatedElements.some(
        (element) => element.matches("iframe,frame") && rendered(element),
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
    const resizeControlSelector =
      "a[href],button,input,select,textarea,[role='button'],[role='link'],[role='slider']";
    const controlLocator = page.locator(resizeControlSelector);
    const controlPaths = await controlLocator.evaluateAll(pathsForLocatorElements);
    const controlPathsByRef = new Map(
      controlPaths.map((path, index) => [`dom-control:${path}`, index]),
    );
    const controlsByRef = new Map(state.interactive_controls.map((row) => [row.target_ref, row]));
    const confirmedControls = [];
    const unmeasurableControls = [];
    for (const [targetRef, row] of controlsByRef) {
      const index = controlPathsByRef.get(targetRef);
      const snapshot =
        index === undefined
          ? null
          : await controlLocator.nth(index).ariaSnapshotJSON({ depth: 0, timeout: 1000 });
      if (!Array.isArray(snapshot) || snapshot.length !== 1 || typeof snapshot[0]?.role !== "string") {
        unmeasurableControls.push(targetRef);
        continue;
      }
      confirmedControls.push({ ...row, role: snapshot[0].role });
      controlsByRef.delete(targetRef);
    }
    unmeasurableControls.push(...controlsByRef.keys());
    const currentControlPaths = await controlLocator.evaluateAll(pathsForLocatorElements);
    if (
      currentControlPaths.length !== controlPaths.length ||
      currentControlPaths.some((path, index) => path !== controlPaths[index])
    ) {
      unmeasurableControls.push("dom-control:population-changed-during-observation");
    }
    state.interactive_controls = confirmedControls.sort((left, right) =>
      left.target_ref < right.target_ref ? -1 : left.target_ref > right.target_ref ? 1 : 0,
    );
    state.unmeasurable_target_refs = [
      ...new Set([...state.unmeasurable_target_refs, ...unmeasurableControls]),
    ].sort();
    state.population_complete = state.population_complete && unmeasurableControls.length === 0;
    return state;
  };

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
