import { appendFileSync, mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TEXT_PREVIEW_MAX_CHARS = 2000;
const EVENTS_WITH_EMPTY_OBJECT_OUTPUT = new Set(["SubagentStop", "Stop"]);
const EXPECTED_EVENTS = new Set([
  "UserPromptSubmit",
  "PostToolUse",
  "SubagentStart",
  "SubagentStop",
  "Stop",
]);

const loggerDirectory = path.dirname(fileURLToPath(import.meta.url));
const logsDirectory = path.resolve(loggerDirectory, "..", "logs");
const fallbackLogsDirectory = path.resolve(loggerDirectory, "..", "..", ".artifacts", "codex-hooks");

const FALLBACK_LOG_PATH_ERRORS = new Set(["EACCES", "EEXIST", "ENOTDIR", "EPERM", "EROFS"]);

function redactSecrets(value) {
  return value
    .replace(
      /\b(authorization|api[-_ ]?key|token|secret|password)\b\s*["']?\s*[:=]\s*["']?(?:bearer\s+|basic\s+)?([^\s,;"'}]+)/gi,
      "$1: [REDACTED]",
    )
    .replace(/\b(bearer|basic)\s+([^\s,;"'}]+)/gi, "$1 [REDACTED]")
    .replace(/\b(?:sk|pk|rk|ghp|github_pat|xox[baprs]-|AKIA)[A-Za-z0-9_-]{8,}\b/g, "[REDACTED]");
}

function boundedText(value) {
  if (value === null || value === undefined) {
    return { value: undefined, truncated: false };
  }

  const text = typeof value === "string" ? value : JSON.stringify(value);
  if (typeof text !== "string") {
    return { value: undefined, truncated: false };
  }

  const sanitized = redactSecrets(text);
  if (sanitized.length <= TEXT_PREVIEW_MAX_CHARS) {
    return { value: sanitized, truncated: false };
  }

  return {
    value: `${sanitized.slice(0, TEXT_PREVIEW_MAX_CHARS - 1)}…`,
    truncated: true,
  };
}

function safeSessionId(sessionId) {
  const sanitized = String(sessionId).replace(/[^A-Za-z0-9._-]/g, "_");
  const bounded = sanitized.slice(0, 128);
  return bounded && !/^\.+$/.test(bounded) ? bounded : "unknown";
}

function addIfPresent(record, field, value, acceptedTypes) {
  if (acceptedTypes.includes(typeof value)) {
    record[field] = value;
  }
}

function buildRecord(expectedEvent, payload) {
  if (typeof payload.session_id !== "string" || payload.session_id.length === 0) {
    throw new Error("session_id is required");
  }

  const record = {
    event: expectedEvent,
    timestamp: new Date().toISOString(),
    session_id: payload.session_id,
  };
  addIfPresent(record, "turn_id", payload.turn_id, ["string", "number"]);

  let truncated = false;
  if (expectedEvent === "UserPromptSubmit") {
    const preview = boundedText(payload.prompt);
    if (preview.value !== undefined) {
      record.prompt = preview.value;
      truncated = preview.truncated;
    }
  } else if (expectedEvent === "PostToolUse") {
    addIfPresent(record, "tool_name", payload.tool_name, ["string"]);
    addIfPresent(record, "tool_use_id", payload.tool_use_id, ["string"]);
    if (Object.prototype.hasOwnProperty.call(payload, "tool_input")) {
      const preview = boundedText(JSON.stringify(payload.tool_input));
      if (preview.value !== undefined) {
        record.tool_input_preview = preview.value;
        truncated = preview.truncated;
      }
    }
  } else if (expectedEvent === "SubagentStart") {
    addIfPresent(record, "agent_id", payload.agent_id, ["string"]);
    addIfPresent(record, "agent_type", payload.agent_type, ["string"]);
  } else if (expectedEvent === "SubagentStop") {
    addIfPresent(record, "agent_id", payload.agent_id, ["string"]);
    addIfPresent(record, "agent_type", payload.agent_type, ["string"]);
    const preview = boundedText(payload.last_assistant_message);
    if (preview.value !== undefined) {
      record.last_assistant_message = preview.value;
      truncated = preview.truncated;
    }
    if (typeof payload.stop_hook_active === "boolean") {
      record.stop_hook_active = payload.stop_hook_active;
    }
  } else if (expectedEvent === "Stop") {
    const preview = boundedText(payload.last_assistant_message);
    if (preview.value !== undefined) {
      record.last_assistant_message = preview.value;
      truncated = preview.truncated;
    }
    if (typeof payload.stop_hook_active === "boolean") {
      record.stop_hook_active = payload.stop_hook_active;
    }
  }

  record.truncated = truncated;
  return record;
}

function appendRecordToDirectory(directory, record) {
  mkdirSync(directory, { recursive: true });
  const logPath = path.join(directory, `hooks-${safeSessionId(record.session_id)}.jsonl`);
  appendFileSync(logPath, `${JSON.stringify(record)}\n`, { encoding: "utf8", flag: "a" });
}

function isFallbackLogPathError(error) {
  return (
    error &&
    typeof error === "object" &&
    "code" in error &&
    FALLBACK_LOG_PATH_ERRORS.has(error.code)
  );
}

function appendRecord(record) {
  try {
    appendRecordToDirectory(logsDirectory, record);
  } catch (error) {
    if (!isFallbackLogPathError(error)) {
      throw error;
    }

    appendRecordToDirectory(fallbackLogsDirectory, record);
  }
}

function readPayload() {
  return JSON.parse(readFileSync(0, { encoding: "utf8" }));
}

function writeExpectedOutput(expectedEvent) {
  if (EVENTS_WITH_EMPTY_OBJECT_OUTPUT.has(expectedEvent)) {
    process.stdout.write("{}");
  }
}

const expectedEvent = process.argv[2];

try {
  if (!EXPECTED_EVENTS.has(expectedEvent)) {
    throw new Error("unknown expected event");
  }

  const payload = readPayload();
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("payload must be a JSON object");
  }
  if (payload.hook_event_name !== expectedEvent) {
    throw new Error("hook event does not match expected event");
  }

  const record = buildRecord(expectedEvent, payload);
  appendRecord(record);
} catch (error) {
  const detail = error instanceof Error ? error.message : "logging failed";
  process.stderr.write(`Codex logging hook: ${detail}\n`);
} finally {
  writeExpectedOutput(expectedEvent);
}
