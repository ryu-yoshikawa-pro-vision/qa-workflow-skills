async (page) => {
  const requestSlot = "__usabilityInspectionFixedProbeRequest";
  const currentDocumentIdentity = await page.evaluate(async () => {
    try {
      if (!globalThis.crypto?.subtle || typeof TextEncoder === "undefined") return null;
      const identityKeySlot = Symbol.for("qa-workflow-skills.document-identity-key.v1");
      let keyPromise = window[identityKeySlot];
      if (!keyPromise) {
        keyPromise = crypto.subtle.generateKey({ name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
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
  const request = await page.evaluate((slot) => {
    const value = window[slot];
    delete window[slot];
    return value ?? null;
  }, requestSlot);

  const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
  const nonEmpty = (value) => typeof value === "string" && value.trim().length > 0;
  const evidenceRefs = (value) =>
    Array.isArray(value) && value.length > 0 && value.every(nonEmpty)
      ? [...new Set(value)].sort()
      : null;
  const identityPattern = /^hmac-sha256:[0-9a-f]{64}$/u;
  const identity =
    object(request) && identityPattern.test(request.document_identity || "")
      ? request.document_identity
      : null;
  const refs = object(request) ? evidenceRefs(request.evidence_refs) : null;
  const failure = (probeKey, status, limitation, value = null) => ({
    probe_key: probeKey,
    document_identity: currentDocumentIdentity || identity,
    status,
    ...(value === null ? {} : { value }),
    limitation,
    evidence_refs: refs || [],
  });

  if (!object(request)) {
    return currentDocumentIdentity
      ? { probe_key: "document-identity", document_identity: currentDocumentIdentity, status: "ok" }
      : {
          probe_key: "document-identity",
          document_identity: null,
          status: "unavailable",
          limitation: "browser cannot create an in-memory keyed current-document identity",
        };
  }
  if (!currentDocumentIdentity) {
    return failure(
      nonEmpty(request.probe_key) ? request.probe_key : "unknown",
      "unavailable",
      "browser cannot create an in-memory keyed current-document identity",
    );
  }
  if (!identity || !refs || !nonEmpty(request.probe_key)) {
    return failure(
      object(request) ? request.probe_key : "unknown",
      "blocked",
      "fixed probe request identity or evidence refs are invalid",
    );
  }
  if (identity !== currentDocumentIdentity) {
    return failure(
      request.probe_key,
      "blocked",
      "fixed probe request is stale for the current document",
    );
  }

  const collectResponsiveConditions = async () =>
    page.evaluate(() => {
      const roots = [document];
      for (let index = 0; index < roots.length; index++) {
        const root = roots[index];
        for (const element of Array.from(root.querySelectorAll("*"))) {
          if (element.shadowRoot) roots.push(element.shadowRoot);
        }
      }

      const conditions = [];
      const issues = [];
      let sourceNumber = 0;
      const pathFor = (element) => {
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
      const queryKind = (rule) => {
        const query = rule.containerQuery || rule.conditionText || "";
        if (/\bstyle\s*\(/i.test(query)) return "container-style";
        if (/\bscroll-state\s*\(/i.test(query)) return "container-scroll-state";
        return "container-size";
      };
      const nestedStyleRules = (rules) => {
        const found = [];
        for (const rule of Array.from(rules || [])) {
          if (typeof rule.selectorText === "string" && rule.style) found.push(rule);
          if (rule.cssRules) {
            try {
              found.push(...nestedStyleRules(rule.cssRules));
            } catch {
              /* The owning source is recorded as incomplete by the caller. */
            }
          }
        }
        return found;
      };
      const findQueryContainers = (root, rule) => {
        const queryName = (rule.containerName || "").trim().split(/\s+/).filter(Boolean);
        const targets = [];
        for (const styleRule of nestedStyleRules(rule.cssRules)) {
          try {
            targets.push(...Array.from(root.querySelectorAll(styleRule.selectorText)));
          } catch {
            /* Invalid or unsupported source selectors cannot be resolved. */
          }
        }
        const containers = new Map();
        for (const target of targets) {
          for (let current = target.parentElement; current; current = current.parentElement) {
            const style = getComputedStyle(current);
            const type = style.containerType || "normal";
            const names = (style.containerName || "").trim().split(/\s+/).filter(Boolean);
            const eligible =
              type !== "normal" &&
              (queryName.length === 0 || queryName.some((name) => names.includes(name)));
            if (eligible) {
              const identity = pathFor(current);
              containers.set(identity, {
                element: current,
                identity,
                name: names.join(" ") || null,
                type,
              });
              break;
            }
          }
        }
        return { targets: [...new Set(targets)], containers: [...containers.values()] };
      };
      const describe = (rule, rootIndex, sheetIndex, rulePath, sourceRef) => {
        const constructorName = rule?.constructor?.name || "";
        if (constructorName !== "CSSMediaRule" && constructorName !== "CSSContainerRule")
          return null;
        const raw =
          constructorName === "CSSMediaRule"
            ? rule.conditionText || rule.media?.mediaText || ""
            : rule.conditionText || rule.containerQuery || "";
        const kind = constructorName === "CSSMediaRule" ? "media" : queryKind(rule);
        const matchName = raw.match(
          /(?:min|max)-(?:width|height)|\b(?:width|height|inline-size|block-size)\b/i,
        );
        const feature = matchName ? matchName[0].toLowerCase() : null;
        let currentMatch = null;
        let method = "";
        let queryContainers = [];
        let executionStatus = "executable";
        let executionReason = null;
        if (kind === "media") {
          try {
            currentMatch = window.matchMedia(raw).matches;
            method = "browser matchMedia evaluation of the complete CSSOM condition";
          } catch {
            executionStatus = "unsupported";
            executionReason = "browser rejected the CSSOM media condition";
          }
        } else {
          const resolved = findQueryContainers(roots[rootIndex], rule);
          queryContainers = resolved.containers;
          currentMatch = null;
          executionStatus = "not-executable";
          method =
            "CSSOM condition inventory only; no standard current container-query match-state API";
          executionReason =
            queryContainers.length === 1
              ? "the browser exposes the @container condition but no standard API reports whether it currently matches"
              : "the query container is not unique and no standard API reports the current @container match state";
        }
        return {
          source_ref: sourceRef,
          root_index: rootIndex,
          sheet_index: sheetIndex,
          rule_path: rulePath,
          query_kind: kind,
          raw_condition: raw,
          query_container_name: kind === "media" ? null : rule.containerName || null,
          query_container_type: queryContainers[0]?.type || null,
          query_container_identity:
            queryContainers
              .map((item) => item.identity)
              .sort()
              .join(" | ") || null,
          axis:
            kind === "media"
              ? feature?.includes("width")
                ? "width"
                : feature?.includes("height")
                  ? "height"
                  : null
              : feature?.includes("width") || feature === "inline-size"
                ? "inline-size"
                : feature?.includes("height") || feature === "block-size"
                  ? "block-size"
                  : null,
          feature,
          browser_capability:
            kind === "media"
              ? typeof window.matchMedia === "function"
                ? "available"
                : "unavailable"
              : "unavailable",
          evaluation_method: method,
          current_match_state: currentMatch,
          execution_status: executionStatus,
          execution_reason: executionReason,
          evidence_refs: [],
        };
      };
      const visit = (rules, rootIndex, sheetIndex, sourceRef, parentPath = []) => {
        for (let index = 0; index < rules.length; index++) {
          const rule = rules[index];
          const rulePath = [...parentPath, index];
          const row = describe(rule, rootIndex, sheetIndex, rulePath, sourceRef);
          if (row) conditions.push(row);
          if (rule.cssRules) {
            try {
              visit(rule.cssRules, rootIndex, sheetIndex, sourceRef, rulePath);
            } catch {
              issues.push({
                source_ref: sourceRef,
                rule_path: rulePath,
                reason: "nested_css_rules_unreadable",
              });
            }
          }
        }
      };
      for (let rootIndex = 0; rootIndex < roots.length; rootIndex++) {
        const sheets = Array.from(roots[rootIndex].styleSheets || []);
        for (let sheetIndex = 0; sheetIndex < sheets.length; sheetIndex++) {
          const sheet = sheets[sheetIndex];
          sourceNumber++;
          const sourceRef = `CSS-SOURCE-${String(sourceNumber).padStart(3, "0")}`;
          try {
            visit(sheet.cssRules, rootIndex, sheetIndex, sourceRef);
          } catch {
            issues.push({ source_ref: sourceRef, reason: "stylesheet_css_rules_unreadable" });
          }
        }
      }
      conditions.forEach((row, index) => {
        row.condition_ref = `COND-${String(index + 1).padStart(3, "0")}`;
      });
      return {
        conditions,
        issues,
        viewport: { width_css_px: innerWidth, height_css_px: innerHeight },
      };
    });

  if (request.probe_key === "document-location") {
    try {
      const safeLocation = await page.evaluate(() => {
        let protocol;
        try {
          protocol = new URL(location.href).protocol;
        } catch {
          return {
            safe_url: null,
            status: "unavailable",
            limitation: "current page URL could not be safely parsed",
          };
        }
        if (!/^https?:$/.test(protocol)) {
          return {
            safe_url: null,
            status: "unavailable",
            limitation: "current page URL scheme cannot be safely retained",
          };
        }
        return { safe_url: `${protocol}//[redacted]`, status: "ok", limitation: null };
      });
      if (safeLocation.status !== "ok")
        return failure(request.probe_key, safeLocation.status, safeLocation.limitation);
      return {
        probe_key: request.probe_key,
        document_identity: identity,
        status: "ok",
        value: {
          safe_url: safeLocation.safe_url,
          status: safeLocation.status,
          limitation: safeLocation.limitation,
        },
        evidence_refs: refs,
      };
    } catch (error) {
      return failure(
        request.probe_key,
        "unavailable",
        "current page location could not be safely observed",
      );
    }
  }

  if (request.probe_key === "document-title") {
    try {
      const value = await page.evaluate(() => {
        const htmlNamespace = "http://www.w3.org/1999/xhtml";
        const root = document.documentElement;
        const isHtmlDocument = root?.namespaceURI === htmlNamespace && root?.localName === "html";
        if (!isHtmlDocument) {
          return {
            is_html_document: false,
            has_html_title_descendant: false,
            first_title_children_are_text: false,
            has_non_whitespace_text: false,
            status: "ok",
            limitation: null,
          };
        }
        const titles = Array.from(document.getElementsByTagNameNS(htmlNamespace, "title"));
        const first = titles[0] || null;
        const childNodes = first ? Array.from(first.childNodes) : [];
        const childrenAreText =
          childNodes.length > 0 && childNodes.every((node) => node.nodeType === Node.TEXT_NODE);
        const hasNonWhitespaceText = childNodes.some(
          (node) => node.nodeType === Node.TEXT_NODE && /\P{White_Space}/u.test(node.data),
        );
        return {
          is_html_document: true,
          has_html_title_descendant: first !== null,
          first_title_children_are_text: childrenAreText,
          has_non_whitespace_text: hasNonWhitespaceText,
          status: "ok",
          limitation: null,
        };
      });
      return {
        probe_key: request.probe_key,
        document_identity: identity,
        status: "ok",
        value,
        evidence_refs: refs,
      };
    } catch (error) {
      return failure(
        request.probe_key,
        "incomplete",
        "document title could not be safely evaluated",
      );
    }
  }

  if (request.probe_key === "navigation-timing" || request.probe_key === "paint-timing") {
    try {
      const observation = await page.evaluate((probeKey) => {
        if (probeKey === "navigation-timing") {
          const entries = performance.getEntriesByType("navigation");
          const entry = entries.length === 1 ? entries[0] : null;
          if (!entry) return { status: "unavailable", entries: [] };
          const fields = [
            "startTime",
            "duration",
            "unloadEventStart",
            "unloadEventEnd",
            "redirectStart",
            "redirectEnd",
            "fetchStart",
            "domainLookupStart",
            "domainLookupEnd",
            "connectStart",
            "connectEnd",
            "secureConnectionStart",
            "requestStart",
            "responseStart",
            "responseEnd",
            "domInteractive",
            "domContentLoadedEventStart",
            "domContentLoadedEventEnd",
            "domComplete",
            "loadEventStart",
            "loadEventEnd",
          ];
          const value = { entry_type: "navigation" };
          for (const field of fields) {
            const candidate = entry[field];
            value[field.replace(/[A-Z]/g, (match) => `_${match.toLowerCase()}`)] =
              typeof candidate === "number" && Number.isFinite(candidate) ? candidate : null;
          }
          return { status: "ok", entries: [value] };
        }

        const entries = performance
          .getEntriesByType("paint")
          .filter((entry) => entry.name === "first-contentful-paint");
        const value = entries
          .filter((entry) => Number.isFinite(entry.startTime) && Number.isFinite(entry.duration))
          .map((entry) => ({
            entry_type: "paint",
            name: "first-contentful-paint",
            start_time: entry.startTime,
            duration: entry.duration,
          }));
        return { status: value.length === 1 ? "ok" : "unavailable", entries: value };
      }, request.probe_key);
      const value = { entries: observation.entries, status: observation.status };
      if (observation.status !== "ok") {
        return failure(
          request.probe_key,
          "unavailable",
          request.probe_key === "paint-timing"
            ? "First Contentful Paint entry is unavailable in the current page session"
            : "one unique Navigation Timing entry is unavailable",
          value,
        );
      }
      return {
        probe_key: request.probe_key,
        document_identity: identity,
        status: "ok",
        value,
        evidence_refs: refs,
      };
    } catch (error) {
      return failure(request.probe_key, "unavailable", "fixed performance timing probe failed");
    }
  }

  if (request.probe_key === "responsive-conditions") {
    try {
      const observed = await collectResponsiveConditions();
      const conditions = observed.conditions.map((row) => ({
        condition_ref: row.condition_ref,
        source_ref: row.source_ref,
        query_kind: row.query_kind,
        raw_condition: row.raw_condition,
        query_container_name: row.query_container_name,
        query_container_type: row.query_container_type,
        query_container_identity: row.query_container_identity,
        axis: row.axis,
        feature: row.feature,
        browser_capability: row.browser_capability,
        evaluation_method: row.evaluation_method,
        current_match_state: row.current_match_state,
        execution_status: row.execution_status,
        execution_reason: row.execution_reason,
        evidence_refs: refs,
      }));
      const complete = observed.issues.length === 0;
      return {
        probe_key: request.probe_key,
        document_identity: identity,
        status: complete ? "ok" : "incomplete",
        value: {
          conditions,
          complete,
          status: complete ? "ok" : "incomplete",
          issues: observed.issues,
          viewport: observed.viewport,
        },
        ...(complete
          ? {}
          : {
              limitation:
                "responsive condition inventory contains an unreadable or unexecutable source",
            }),
        evidence_refs: refs,
      };
    } catch (error) {
      return failure(request.probe_key, "unavailable", "responsive condition probe failed");
    }
  }

  if (request.probe_key === "responsive-boundaries") {
    const viewport = page.viewportSize();
    if (!viewport || !Number.isInteger(viewport.width) || !Number.isInteger(viewport.height)) {
      return failure(
        request.probe_key,
        "unavailable",
        "current viewport dimensions are unavailable",
      );
    }
    const original = { width: viewport.width, height: viewport.height };
    try {
      const inventory = await collectResponsiveConditions();
      const boundaries = [];
      const closures = [];
      let incomplete = inventory.issues.length > 0;
      for (const row of inventory.conditions) {
        if (row.execution_status !== "executable") {
          closures.push({
            condition_ref: row.condition_ref,
            status: "not-executable",
            reason: row.execution_reason || "condition is not executable",
          });
          continue;
        }
        if (
          row.query_kind === "container-style" ||
          row.query_kind === "container-scroll-state" ||
          !row.axis
        ) {
          closures.push({
            condition_ref: row.condition_ref,
            status: "non-numeric-presentation-variation",
            reason: "condition does not represent a one-axis numeric size transition",
          });
          continue;
        }
        const featureCount = (
          row.raw_condition.match(
            /(?:min|max)-(?:width|height)|\b(?:width|height|inline-size|block-size)\s*(?:<=|>=|<|>|:)/gi,
          ) || []
        ).length;
        if (featureCount !== 1 || /,|\bor\b/i.test(row.raw_condition)) {
          closures.push({
            condition_ref: row.condition_ref,
            status: "incomplete",
            reason: "condition branches cannot be separated as one monotonic axis",
          });
          incomplete = true;
          continue;
        }
        const axis = row.axis;
        const axisDimension = axis === "width" || axis === "inline-size" ? "width" : "height";
        const observeAt = async (value) => {
          await page.setViewportSize({
            width: axisDimension === "width" ? value : original.width,
            height: axisDimension === "height" ? value : original.height,
          });
          await page.evaluate(
            () => new Promise((resolve) => requestAnimationFrame(() => resolve(true))),
          );
          return page.evaluate((target) => {
            const roots = [document];
            for (let index = 0; index < roots.length; index++) {
              for (const element of Array.from(roots[index].querySelectorAll("*"))) {
                if (element.shadowRoot) roots.push(element.shadowRoot);
              }
            }
            const root = roots[target.root_index];
            const sheet = Array.from(root?.styleSheets || [])[target.sheet_index];
            if (!sheet) return { match: null, limitation: "stylesheet is no longer current" };
            let rule;
            try {
              rule = sheet.cssRules;
              for (let index = 0; index < target.rule_path.length; index++) {
                rule = rule[target.rule_path[index]];
                if (index < target.rule_path.length - 1) rule = rule.cssRules;
              }
            } catch {
              return { match: null, limitation: "CSSOM rule is unreadable" };
            }
            if (target.query_kind === "media") {
              try {
                return { match: window.matchMedia(rule.conditionText).matches };
              } catch {
                return { match: null, limitation: "browser rejected the media condition" };
              }
            }
            return {
              match: null,
              limitation: "standard browser APIs do not expose the current @container match state",
            };
          }, row);
        };

        let left = 1;
        let right = 8192;
        let leftResult = await observeAt(left);
        let rightResult = await observeAt(right);
        if (leftResult.match === null || rightResult.match === null) {
          closures.push({
            condition_ref: row.condition_ref,
            status: "incomplete",
            reason:
              leftResult.limitation || rightResult.limitation || "browser evaluation unavailable",
          });
          incomplete = true;
          continue;
        }
        if (leftResult.match === rightResult.match) {
          const middle = Math.floor((left + right) / 2);
          const middleResult = await observeAt(middle);
          if (middleResult.match === null || middleResult.match !== leftResult.match) {
            closures.push({
              condition_ref: row.condition_ref,
              status: "incomplete",
              reason:
                "condition is non-monotonic or has multiple transitions in the supported range",
            });
            incomplete = true;
          } else {
            closures.push({
              condition_ref: row.condition_ref,
              status: "no-numeric-transition",
              reason: `browser evaluation found no transition from 1 through 8192 CSS px on ${axis}`,
            });
          }
          continue;
        }
        const initialState = leftResult.match;
        while (right - left > 1) {
          const middle = Math.floor((left + right) / 2);
          const result = await observeAt(middle);
          if (result.match === null) break;
          if (result.match === initialState) left = middle;
          else right = middle;
        }
        const before = right - 1;
        const transition = right;
        const after = right + 1;
        const beforeResult = await observeAt(before);
        const transitionResult = await observeAt(transition);
        const afterResult = await observeAt(after);
        if (
          [beforeResult, transitionResult, afterResult].some((result) => result.match === null) ||
          beforeResult.match === transitionResult.match ||
          transitionResult.match !== afterResult.match
        ) {
          closures.push({
            condition_ref: row.condition_ref,
            status: "incomplete",
            reason: "neighboring browser observations did not verify a single transition",
          });
          incomplete = true;
          continue;
        }
        const boundary = {
          condition_ref: row.condition_ref,
          axis,
          before_viewport_css_px: before,
          transition_viewport_css_px: transition,
          after_viewport_css_px: after,
          match_states: [beforeResult.match, transitionResult.match, afterResult.match],
          raw_condition: row.raw_condition,
          derivation_method:
            "browser-evaluated fixed binary search with neighboring CSS px verification",
          execution_status: "executable",
          evidence_refs: refs,
        };
        boundaries.push(boundary);
      }
      return {
        probe_key: request.probe_key,
        document_identity: identity,
        status: incomplete ? "incomplete" : "ok",
        value: {
          boundaries,
          closures,
          complete: !incomplete,
          status: incomplete ? "incomplete" : "ok",
        },
        ...(incomplete
          ? { limitation: "one or more responsive size conditions could not be closed" }
          : {}),
        evidence_refs: refs,
      };
    } catch (error) {
      return failure(request.probe_key, "unavailable", "responsive boundary probe failed");
    } finally {
      try {
        await page.setViewportSize(original);
        const restored = page.viewportSize();
        if (!restored || restored.width !== original.width || restored.height !== original.height)
          return failure(
            request.probe_key,
            "incomplete",
            "original viewport restoration could not be verified",
          );
      } catch {
        return failure(
          request.probe_key,
          "incomplete",
          "original viewport restoration could not be verified",
        );
      }
    }
  }

  if (request.probe_key === "interaction-timing") {
    const allowedActions = new Set(["click", "fill", "press", "check", "uncheck", "select-option"]);
    const allowedStartEvents = new Set(["click", "input", "change", "keydown", "pointerdown"]);
    const allowedAttributes = new Set([
      "aria-current",
      "aria-label",
      "aria-live",
      "href",
      "name",
      "role",
      "title",
      "value",
    ]);
    const allowedAriaStates = new Set([
      "aria-checked",
      "aria-current",
      "aria-disabled",
      "aria-expanded",
      "aria-invalid",
      "aria-pressed",
      "aria-selected",
    ]);
    if (
      !object(request.target_resolver) ||
      !object(request.target_resolver.payload) ||
      !object(request.action) ||
      !allowedActions.has(request.action.kind) ||
      !allowedStartEvents.has(request.start_event) ||
      !object(request.predicate) ||
      !Number.isInteger(request.timeout_ms) ||
      request.timeout_ms < 1 ||
      request.timeout_ms > 120000
    ) {
      return failure(
        request.probe_key,
        "blocked",
        "fixed interaction timing request is outside the finite schema",
      );
    }
    const makeLocator = (scope, descriptor) => {
      if (!object(descriptor) || !object(descriptor.payload))
        throw new Error("target resolver is invalid");
      const { kind, payload } = descriptor;
      if (kind === "role-name" && nonEmpty(payload.role) && nonEmpty(payload.name))
        return scope.getByRole(payload.role, { name: payload.name, exact: true });
      if (kind === "label" && nonEmpty(payload.label_text))
        return scope.getByLabel(payload.label_text, { exact: true });
      if (kind === "visible-text" && nonEmpty(payload.text))
        return scope.getByText(payload.text, { exact: true });
      throw new Error(
        "fixed interaction probe supports only exact role/name, label, and visible-text resolvers",
      );
    };
    const targetRef = request.target_ref;
    if (!nonEmpty(targetRef))
      return failure(request.probe_key, "blocked", "interaction timing target ref is missing");
    let target;
    try {
      target = makeLocator(page, request.target_resolver);
    } catch {
      return failure(request.probe_key, "unsupported", "the fixed target resolver is unsupported");
    }
    if ((await target.count()) !== 1 || !(await target.isVisible()) || !(await target.isEnabled()))
      return failure(
        request.probe_key,
        "unavailable",
        "interaction target is not unique, visible, and enabled",
      );

    let textScopeLocator = page;
    const getPredicateLocator = (predicate) => {
      const key = predicate.predicate_key;
      if (key === "text-present" && typeof predicate.expected_text === "string") {
        if (predicate.within_target_ref) {
          const descriptor = request.resolved_targets?.[predicate.within_target_ref];
          if (!descriptor) throw new Error("text predicate scope ref has no current resolver");
          textScopeLocator = makeLocator(page, descriptor);
        }
        return textScopeLocator.getByText(predicate.expected_text, { exact: true });
      }
      if (
        [
          "element-visible",
          "element-hidden",
          "element-enabled",
          "element-disabled",
          "attribute-equals",
          "aria-state-equals",
        ].includes(key)
      ) {
        const descriptor =
          request.resolved_targets?.[predicate.target_ref] ||
          (predicate.target_ref === targetRef ? request.target_resolver : null);
        if (!descriptor) throw new Error("predicate target ref has no current resolver");
        if (
          (key === "attribute-equals" && !allowedAttributes.has(predicate.attribute_name)) ||
          (key === "aria-state-equals" && !allowedAriaStates.has(predicate.state_name))
        )
          throw new Error("predicate property is outside the fixed allowlist");
        return makeLocator(page, descriptor);
      }
      if (key === "url-changed" && predicate.baseline_url === "capture-at-arm") return null;
      throw new Error("unknown fixed interaction predicate");
    };
    const predicateSatisfied = async (predicate, locator, baselineUrl) => {
      const key = predicate.predicate_key;
      if (key === "text-present")
        return (await locator.count()) > 0 && (await locator.first().isVisible());
      if (key === "element-visible")
        return (await locator.count()) === 1 && (await locator.isVisible());
      if (key === "element-hidden")
        return (await locator.count()) === 0 || (await locator.isHidden());
      if (key === "element-enabled")
        return (await locator.count()) === 1 && (await locator.isEnabled());
      if (key === "element-disabled")
        return (await locator.count()) === 1 && (await locator.isDisabled());
      if (key === "attribute-equals")
        return (
          (await locator.count()) === 1 &&
          (await locator.getAttribute(predicate.attribute_name)) === predicate.expected_value
        );
      if (key === "aria-state-equals")
        return (
          (await locator.count()) === 1 &&
          (await locator.getAttribute(predicate.state_name)) === predicate.expected_value
        );
      if (key === "url-changed") return page.url() !== baselineUrl;
      return false;
    };
    const predicate = request.predicate;
    let predicateLocator;
    try {
      predicateLocator = getPredicateLocator(predicate);
    } catch {
      return failure(request.probe_key, "blocked", "the fixed end-state predicate is invalid");
    }
    const baselineUrl = page.url();
    if (await predicateSatisfied(predicate, predicateLocator, baselineUrl))
      return failure(request.probe_key, "blocked", "preexisting-end-state");

    let predicateElement = null;
    let textScopeElement = null;
    if (predicateLocator !== null && predicate.predicate_key !== "text-present") {
      if ((await predicateLocator.count()) !== 1)
        return failure(
          request.probe_key,
          "unavailable",
          "fixed predicate target is not uniquely resolvable before action",
        );
      predicateElement = await predicateLocator.elementHandle();
    }
    if (predicate.predicate_key === "text-present" && predicate.within_target_ref) {
      if ((await textScopeLocator.count()) !== 1)
        return failure(
          request.probe_key,
          "unavailable",
          "fixed text predicate scope is not uniquely resolvable before action",
        );
      textScopeElement = await textScopeLocator.elementHandle();
    }

    const startObserver = await page.evaluateHandle(
      ({
        inputTarget,
        endTarget,
        textScope,
        eventName,
        predicate: endPredicate,
        baselineUrl: initialUrl,
        timeoutMs,
      }) => {
        const state = {
          start_ms: null,
          end_ms: null,
          event_name: null,
          done: false,
          limitation: null,
        };
        const slot = "__usabilityInspectionInteractionTiming";
        const listener = (event) => {
          if (
            event.type !== eventName ||
            !event.composedPath().includes(inputTarget) ||
            state.start_ms !== null
          )
            return;
          state.start_ms = performance.now();
          state.event_name = event.type;
        };
        const visible = (element) => {
          if (!element || !element.isConnected) return false;
          const style = getComputedStyle(element);
          return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            element.getClientRects().length > 0
          );
        };
        const disabled = (element) =>
          !element ||
          !element.isConnected ||
          element.matches(":disabled") ||
          element.getAttribute("aria-disabled") === "true";
        const normalizeText = (value) =>
          String(value || "")
            .replace(/\s+/g, " ")
            .trim();
        const matches = () => {
          const key = endPredicate.predicate_key;
          if (key === "text-present") {
            const root = textScope || document.body;
            if (!root || !root.isConnected) return false;
            const expected = normalizeText(endPredicate.expected_text);
            return Array.from(root.querySelectorAll("*")).some(
              (element) =>
                visible(element) &&
                normalizeText(element.innerText || element.textContent) === expected,
            );
          }
          if (key === "url-changed") return location.href !== initialUrl;
          const element = endTarget;
          if (!element || !element.isConnected) return key === "element-hidden";
          if (key === "element-visible") return visible(element);
          if (key === "element-hidden") return !visible(element);
          if (key === "element-enabled") return !disabled(element);
          if (key === "element-disabled") return disabled(element);
          if (key === "attribute-equals")
            return (
              element.getAttribute(endPredicate.attribute_name) === endPredicate.expected_value
            );
          if (key === "aria-state-equals")
            return element.getAttribute(endPredicate.state_name) === endPredicate.expected_value;
          return false;
        };
        let observer;
        let animationFrame = null;
        let timeout = null;
        const cleanup = () => {
          observer?.disconnect();
          if (animationFrame !== null) cancelAnimationFrame(animationFrame);
          if (timeout !== null) clearTimeout(timeout);
          document.removeEventListener(eventName, listener, true);
          window.removeEventListener("popstate", check, true);
          window.removeEventListener("hashchange", check, true);
        };
        const finish = (matched, limitation = null) => {
          if (state.done) return;
          state.done = true;
          state.limitation = limitation;
          if (matched) state.end_ms = performance.now();
          cleanup();
        };
        const check = () => {
          if (!state.done && state.start_ms !== null && matches()) finish(true);
        };
        const frame = () => {
          if (state.done) return;
          check();
          if (!state.done) animationFrame = requestAnimationFrame(frame);
        };
        document.addEventListener(eventName, listener, true);
        window.addEventListener("popstate", check, true);
        window.addEventListener("hashchange", check, true);
        observer = new MutationObserver(check);
        observer.observe(document, {
          subtree: true,
          childList: true,
          attributes: true,
          characterData: true,
        });
        window[slot] = { state, listener, eventName, observer, cleanup };
        timeout = window.setTimeout(
          () => finish(false, "timeout: fixed end predicate was not observed"),
          timeoutMs,
        );
        animationFrame = requestAnimationFrame(frame);
        return true;
      },
      {
        inputTarget: await target.elementHandle(),
        endTarget: predicateElement,
        textScope: textScopeElement,
        eventName: request.start_event,
        predicate,
        baselineUrl,
        timeoutMs: request.timeout_ms,
      },
    );
    await startObserver.dispose();

    const startEventPromise = page
      .waitForFunction(
        (eventName) => {
          const state = window.__usabilityInspectionInteractionTiming?.state;
          return state?.start_ms !== null && state?.event_name === eventName;
        },
        request.start_event,
        { timeout: request.timeout_ms },
      )
      .catch(() => null);
    let actionError = null;
    try {
      if (request.action.kind === "click") await target.click();
      else if (request.action.kind === "fill" && typeof request.action.value === "string")
        await target.fill(request.action.value);
      else if (request.action.kind === "press" && nonEmpty(request.action.key))
        await target.press(request.action.key);
      else if (request.action.kind === "check") await target.check();
      else if (request.action.kind === "uncheck") await target.uncheck();
      else if (request.action.kind === "select-option" && typeof request.action.value === "string")
        await target.selectOption(request.action.value);
      else throw new Error("action payload does not match the fixed action kind");
    } catch {
      actionError = "the fixed browser action failed";
    }
    const startEvent = await startEventPromise;
    if (!startEvent) {
      await page.evaluate(() => {
        const record = window.__usabilityInspectionInteractionTiming;
        if (!record) return;
        record.cleanup();
        delete window.__usabilityInspectionInteractionTiming;
      });
      return failure(
        request.probe_key,
        "unavailable",
        actionError || "measurement-unavailable: required input event was not observed",
      );
    }

    const endState = await page
      .waitForFunction(
        () => {
          const state = window.__usabilityInspectionInteractionTiming?.state;
          return state?.done
            ? { start_ms: state.start_ms, end_ms: state.end_ms, limitation: state.limitation }
            : false;
        },
        null,
        { timeout: request.timeout_ms + 1000 },
      )
      .then((handle) => handle.jsonValue())
      .catch(() => null);
    if (!endState)
      return failure(
        request.probe_key,
        "unavailable",
        "measurement-unavailable: browser clock watcher did not close",
      );
    await page.evaluate(() => {
      const record = window.__usabilityInspectionInteractionTiming;
      if (!record) return;
      record.cleanup();
      delete window.__usabilityInspectionInteractionTiming;
    });
    if (endState.end_ms === null)
      return failure(
        request.probe_key,
        "unavailable",
        endState.limitation || "timeout: fixed end predicate was not observed",
      );
    const startMs = endState.start_ms;
    const endMs = endState.end_ms;
    if (
      startMs === null ||
      typeof endMs !== "number" ||
      !Number.isFinite(startMs) ||
      !Number.isFinite(endMs) ||
      endMs < startMs
    )
      return failure(
        request.probe_key,
        "unavailable",
        "same-page clock timestamps could not be verified",
      );
    return {
      probe_key: request.probe_key,
      document_identity: identity,
      status: "ok",
      value: {
        start_ms: startMs,
        end_ms: endMs,
        elapsed_ms: endMs - startMs,
        predicate_result: { predicate_key: predicate.predicate_key, matched: true },
        clock_domain: "same-page-performance-now",
        status: "ok",
      },
      evidence_refs: refs,
    };
  }

  return failure(
    request.probe_key,
    "unsupported",
    "probe key is outside this Skill's fixed browser dispatch",
  );
};
