type FenceState = {
  marker: "`" | "~";
  length: number;
};

type FenceMarker = FenceState & {
  suffix: string;
};

function parseFenceMarker(line: string): FenceMarker | null {
  const match = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line);
  if (match === null) return null;

  const markerSequence = match[1];
  if (markerSequence === undefined) return null;
  const marker = markerSequence[0];
  if (marker !== "`" && marker !== "~") return null;

  return {
    marker,
    length: markerSequence.length,
    suffix: match[2] ?? "",
  };
}

function normalizeH2(line: string): string | null {
  const match = /^ {0,3}(## )(.*)$/.exec(line);
  if (match === null) return null;

  const headingText = (match[2] ?? "").replace(/[ \t]+$/, "");
  return `## ${headingText}`;
}

function extractH2Headings(markdown: string): string[] {
  const headings: string[] = [];
  let fence: FenceState | null = null;

  for (const line of markdown.split(/\r?\n/)) {
    const marker = parseFenceMarker(line);
    if (fence !== null) {
      if (
        marker !== null &&
        marker.marker === fence.marker &&
        marker.length >= fence.length &&
        /^[ \t]*$/.test(marker.suffix)
      ) {
        fence = null;
      }
      continue;
    }

    if (marker !== null) {
      fence = marker;
      continue;
    }

    const heading = normalizeH2(line);
    if (heading !== null && !headings.includes(heading)) headings.push(heading);
  }

  return headings;
}

export function validatePlanOutput(
  templateMarkdown: string,
  outputMarkdown: string,
): {
  valid: boolean;
  missingHeadings: string[];
} {
  const requiredHeadings = extractH2Headings(templateMarkdown);
  if (requiredHeadings.length === 0)
    throw new Error("canonical plan template has no required level-2 headings");

  const outputHeadings = new Set(extractH2Headings(outputMarkdown));
  const missingHeadings = requiredHeadings.filter((heading) => !outputHeadings.has(heading));

  return {
    valid: missingHeadings.length === 0,
    missingHeadings,
  };
}
