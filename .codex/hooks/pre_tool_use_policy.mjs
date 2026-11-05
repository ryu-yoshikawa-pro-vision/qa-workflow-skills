#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import path from "node:path";

const EVENT = "PreToolUse";
const GIT_PROMPT = new Set([
  "merge",
  "rebase",
  "push",
  "reset",
  "am",
  "cherry-pick",
  "revert",
  "restore",
  "checkout",
  "switch",
]);
const GIT_DYNAMIC_ARGUMENTS = new Set([...GIT_PROMPT, "commit", "pull", "fetch"]);
const GIT_PROMPT_FAMILIES = new Set(["branch", "tag", "config", "remote", "worktree", "stash"]);
const GIT_FORBIDDEN = new Set(["clean", "rm", "update-ref"]);
const GH_PROMPT_FAMILIES = new Set([
  "auth",
  "codespace",
  "gist",
  "org",
  "project",
  "ssh-key",
  "gpg-key",
  "extension",
  "alias",
  "config",
  "attestation",
  "at",
  "transfer",
  "move",
]);
const GH_ACTIONS = new Map([
  [
    "pr",
    new Set([
      "create",
      "new",
      "checkout",
      "co",
      "close",
      "comment",
      "edit",
      "lock",
      "merge",
      "ready",
      "reopen",
      "revert",
      "review",
      "unlock",
      "update-branch",
    ]),
  ],
  [
    "issue",
    new Set([
      "create",
      "new",
      "close",
      "comment",
      "delete",
      "develop",
      "edit",
      "lock",
      "pin",
      "reopen",
      "transfer",
      "unlock",
      "unpin",
    ]),
  ],
  [
    "repo",
    new Set([
      "archive",
      "clone",
      "create",
      "new",
      "delete",
      "edit",
      "fork",
      "read-file",
      "rename",
      "set-default",
      "unarchive",
    ]),
  ],
  ["workflow", new Set(["disable", "enable", "run"])],
  ["run", new Set(["cancel", "delete", "download", "rerun"])],
  ["release", new Set(["create", "new", "delete", "delete-asset", "download", "edit", "upload"])],
  ["secret", new Set(["delete", "remove", "set"])],
  ["variable", new Set(["delete", "remove", "set"])],
  ["cache", new Set(["delete"])],
  ["label", new Set(["clone", "create", "delete", "edit"])],
  ["discussion", new Set(["create", "comment", "edit"])],
  ["skill", new Set(["publish", "install", "add", "update"])],
  ["skills", new Set(["publish", "install", "add", "update"])],
  ["agent-task", new Set(["create"])],
  ["agent-tasks", new Set(["create"])],
  ["agent", new Set(["create"])],
  ["agents", new Set(["create"])],
]);
const GH_SUBCOMMAND_OPTIONS = new Set([
  "pr",
  "issue",
  "repo",
  "workflow",
  "run",
  "release",
  "secret",
  "variable",
  "cache",
  "label",
  "discussion",
  "skill",
  "skills",
  "agent-task",
  "agent-tasks",
  "agent",
  "agents",
]);
const GH_SUBFAMILIES = new Set(["autolink", "deploy-key"]);
const DELETE_COMMANDS = new Set(["rm", "del", "erase", "rd", "ri", "remove-item", "rmdir", "unlink"]);
const SAFE_PUSH_OPTIONS = new Set(["-u", "--set-upstream"]);
const SAFE_FALSE_CONFIG_VALUES = new Set(["false", "no", "off", "0"]);
const FETCH_SAFE_OPTIONS = new Set([
  "--atomic",
  "--dry-run",
  "--no-auto-maintenance",
  "--no-progress",
  "--no-recurse-submodules",
  "--no-tags",
  "--progress",
  "--quiet",
  "--verbose",
  "-q",
  "-v",
]);

function deny(reason) {
  return { hookSpecificOutput: { hookEventName: EVENT, permissionDecision: "deny", permissionDecisionReason: reason } };
}
function gitOutput(cwd, args) {
  try {
    return execFileSync("git", ["-C", cwd, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      windowsHide: true,
    }).trim();
  } catch {
    return null;
  }
}
function gitOutputLines(cwd, args) {
  try {
    const output = execFileSync("git", ["-C", cwd, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      windowsHide: true,
    }).replace(/\r?\n$/, "");
    return output ? output.split(/\r?\n/) : [];
  } catch (error) {
    return error?.status === 1 ? [] : null;
  }
}
const gitConfigCache = new Map();
function configKeyParts(key) {
  const firstDot = key.indexOf(".");
  if (firstDot < 0) return [key, "", ""];
  const lastDot = key.lastIndexOf(".");
  return [
    key.slice(0, firstDot),
    firstDot === lastDot ? "" : key.slice(firstDot + 1, lastDot),
    key.slice(lastDot + 1),
  ];
}
function sameConfigKey(left, right) {
  const [leftSection, leftSubsection, leftName] = configKeyParts(left);
  const [rightSection, rightSubsection, rightName] = configKeyParts(right);
  return leftSection.toLowerCase() === rightSection.toLowerCase()
    && leftSubsection === rightSubsection
    && leftName.toLowerCase() === rightName.toLowerCase();
}
function gitConfigEntries(root) {
  const cacheKey = path.resolve(root);
  if (gitConfigCache.has(cacheKey)) return gitConfigCache.get(cacheKey);
  try {
    const output = execFileSync("git", ["-C", root, "config", "--null", "--list"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      windowsHide: true,
    });
    const entries = [];
    for (const record of output.split("\0")) {
      if (!record) continue;
      const separator = record.indexOf("\n");
      if (separator <= 0) throw new Error("Git config entry has an invalid format.");
      entries.push([record.slice(0, separator), record.slice(separator + 1)]);
    }
    gitConfigCache.set(cacheKey, entries);
    return entries;
  } catch {
    gitConfigCache.set(cacheKey, null);
    return null;
  }
}
function gitConfigValues(root, key, boolean = false) {
  const entries = gitConfigEntries(root);
  if (entries === null) return null;
  const values = entries.filter(([entryKey]) => sameConfigKey(entryKey, key)).map(([, value]) => value);
  if (!boolean) return values;
  const trueValues = new Set(["true", "yes", "on", "1"]);
  const falseValues = new Set(["false", "no", "off", "0"]);
  const normalized = [];
  for (const value of values) {
    const lowerValue = value.trim().toLowerCase();
    if (trueValues.has(lowerValue)) normalized.push("true");
    else if (falseValues.has(lowerValue)) normalized.push("false");
    else return null;
  }
  return normalized;
}
function remoteDefaultBranch(root, remote) {
  const ref = `refs/remotes/${remote}/HEAD`;
  const head = gitOutputLines(root, [
    "symbolic-ref",
    "--quiet",
    ref,
  ]);
  if (head === null) return { status: "read_error" };
  if (head.length === 0) {
    const refs = gitOutputLines(root, ["show-ref", "--head"]);
    if (refs === null) return { status: "read_error" };
    if (refs.some(line => line.endsWith(` ${ref}`))) return { status: "invalid" };
    return { status: "missing" };
  }
  if (head.length !== 1) return { status: "invalid" };

  const prefix = `refs/remotes/${remote}/`;
  if (!head[0].startsWith(prefix)) {
    return { status: "invalid" };
  }
  const branch = head[0].slice(prefix.length);
  if (!validBranch(root, branch)) {
    return { status: "invalid" };
  }
  return { status: "ok", branch };
}
function remoteDefaultBranchError(status) {
  if (status === "missing") return "The remote default branch is not configured locally.";
  if (status === "read_error") return "Could not read the remote default branch.";
  return "The remote default branch metadata is invalid or does not match the remote.";
}
function repoRoot(cwd) {
  const root = gitOutput(cwd, ["rev-parse", "--show-toplevel"]);
  return root ? path.resolve(root) : null;
}
function samePath(a, b) {
  const left = path.resolve(a), right = path.resolve(b);
  if (a !== left) return false;
  return process.platform === "win32" ? a.toLowerCase() === right.toLowerCase() : a === right;
}
function gitContext(root) {
  const current = gitOutput(root, ["symbolic-ref", "--quiet", "--short", "HEAD"]);
  const originDefault = remoteDefaultBranch(root, "origin");
  const protectedBranches = new Set(["main", "master"]);
  if (originDefault.status === "ok") {
    protectedBranches.add(originDefault.branch);
  }
  const error = ["read_error", "invalid"].includes(originDefault.status)
    ? remoteDefaultBranchError(originDefault.status)
    : null;
  return { current, protectedBranches, error };
}
function branchExists(root, name) {
  try {
    execFileSync("git", ["-C", root, "show-ref", "--verify", "--quiet", "refs/heads/" + name], {
      stdio: "ignore",
      windowsHide: true,
    });
    return true;
  } catch {
    return false;
  }
}
function remoteTrackingBranchExists(root, remote, name) {
  try {
    execFileSync(
      "git",
      ["-C", root, "show-ref", "--verify", "--quiet", `refs/remotes/${remote}/${name}`],
      { stdio: "ignore", windowsHide: true },
    );
    return true;
  } catch {
    return false;
  }
}
function validBranch(root, name) {
  if (!name || ["-", "HEAD", "@{-1}"].includes(name) || name.startsWith("refs/")) return false;
  try {
    execFileSync("git", ["-C", root, "check-ref-format", "--branch", name], { stdio: "ignore", windowsHide: true });
    return true;
  } catch {
    return false;
  }
}
function canonicalCommand(command, root) {
  const posix = /^\s*cd\s+'([^']+)'\s*&&\s*([\s\S]+)$/.exec(command);
  if (posix) return { command: posix[2], valid: Boolean(root) && samePath(posix[1], root), shell: "posix" };
  const ps = /^\s*Set-Location\s+-LiteralPath\s+'([^']+)'\s+-ErrorAction\s+Stop\s*;\s*([\s\S]+)$/i.exec(command);
  if (ps) return { command: ps[2], valid: Boolean(root) && samePath(ps[1], root), shell: "powershell" };
  return null;
}
function splitCommands(input, shell) {
  const segments = [];
  let words = [];
  let value = "";
  let dynamic = false;
  let started = false;
  let quote = null;
  let parseError = null;
  const flushWord = () => {
    if (started) words.push({ value, dynamic });
    value = "";
    dynamic = false;
    started = false;
  };
  const flushSegment = () => {
    flushWord();
    if (words.length) segments.push(words);
    words = [];
  };
  for (let i = 0; i < input.length; i += 1) {
    const c = input[i], n = input[i + 1];
    if (quote !== null) {
      if (c === quote) {
        quote = null;
        started = true;
        continue;
      }
      if (shell === "posix" && c === "\\" && n !== undefined) {
        value += n;
        started = true;
        i += 1;
        continue;
      }
      if (shell === "powershell" && c.charCodeAt(0) === 96 && quote !== "'") {
        dynamic = true;
        if (n !== undefined) {
          value += n;
          i += 1;
        }
        started = true;
        continue;
      }
      if (quote !== "'" && (c === "$" || c === "~" || "*?[]".includes(c))) dynamic = true;
      value += c;
      started = true;
      continue;
    }
    if (c === "'" || c === "\"") {
      quote = c;
      started = true;
      continue;
    }
    if (shell === "posix" && c === "\\" && n !== undefined) {
      value += n;
      started = true;
      i += 1;
      continue;
    }
    if (shell === "powershell" && c.charCodeAt(0) === 96) {
      dynamic = true;
      if (n !== undefined) {
        value += n;
        i += 1;
      }
      started = true;
      continue;
    }
    if (c === "$" || c === "~" || "*?[]".includes(c)) dynamic = true;
    if (/\s/.test(c)) {
      flushWord();
      continue;
    }
    if (c === ";" || c === "|" || c === "&" || c === "\r" || c === "\n") {
      flushSegment();
      if ((c === "&" || c === "|") && n === c) i += 1;
      continue;
    }
    value += c;
    started = true;
  }
  if (quote !== null) parseError = "unterminated shell quote";
  flushSegment();
  return { segments, parseError };
}
function readOnlyGit(name, args) {
  const op = name.toLowerCase(), a = args.map(x => x.value.toLowerCase());
  if (
    [
      "status",
      "rev-parse",
      "ls-files",
      "check-ignore",
      "cat-file",
      "blame",
      "show-ref",
      "version",
      "help",
    ].includes(op)
  ) {
    return true;
  }
  if (["diff", "log", "show"].includes(op)) {
    return !a.some(x => x === "--output" || x.startsWith("--output=") || x === "--ext-diff" || x === "--textconv");
  }
  if (op === "branch") return readOnlyBranch(args);
  if (op === "tag") return a.length === 0 || a.includes("--list") || a.includes("-l");
  if (op === "config") {
    return a.some(x =>
      ["--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l"].includes(x) || x.startsWith("--get=")
    );
  }
  if (op === "remote") {
    const isVerboseOption = x => x === "-v" || x === "--verbose";
    const command = a.find(x => !isVerboseOption(x));
    return command === undefined || ["show", "get-url"].includes(command);
  }
  if (op === "worktree") return a[0] === "list";
  if (op === "stash") return ["list", "show"].includes(a[0]);
  return false;
}
function readOnlyBranch(args) {
  if (args.length === 0) return true;
  // Unknown options and branch names are mutations unless --list makes them patterns.
  let listOnly = false, endOfOptions = false;
  const listingOptions = new Set([
    "-a",
    "--all",
    "-r",
    "--remotes",
    "-v",
    "-vv",
    "--verbose",
    "--show-current",
    "--merged",
    "--no-merged",
    "--contains",
    "--no-contains",
    "--points-at",
    "--forked",
    "--format",
    "--sort",
    "--color",
    "--no-color",
    "--column",
    "--no-column",
    "--ignore-case",
    "-i",
    "--omit-empty",
    "--no-abbrev",
    "-l",
    "--list",
  ]);
  const optionalCommitOptions = new Set(["--merged", "--no-merged", "--contains", "--no-contains"]);
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i], value = arg.value, option = value.toLowerCase();
    if (arg.dynamic) return false;
    if (endOfOptions) continue;
    if (option === "--") {
      if (!listOnly) return false;
      endOfOptions = true;
      continue;
    }
    if (option === "-l" || option === "--list") {
      listOnly = true;
      continue;
    }
    if (listingOptions.has(option)) {
      if (option === "--format" || option === "--points-at" || option === "--forked") {
        const valueArg = args[i + 1];
        if (!valueArg || valueArg.dynamic || valueArg.value.startsWith("-")) return false;
        i += 1;
      } else if (optionalCommitOptions.has(option)) {
        const valueArg = args[i + 1];
        if (valueArg && !valueArg.value.startsWith("-")) {
          if (valueArg.dynamic) return false;
          i += 1;
        }
      }
      continue;
    }
    if (
      /^--(?:format|sort|abbrev|color|column|merged|no-merged|contains|no-contains|points-at|forked)=/i.test(value)
    ) continue;
    if (option.startsWith("-")) return false;
    if (!listOnly) return false;
  }
  return true;
}
function pushConfigurationError(root, remote) {
  const pushUrls = gitOutputLines(root, ["remote", "get-url", "--push", "--all", remote]);
  if (!pushUrls || pushUrls.length !== 1 || !pushUrls[0] || pushUrls[0].trim() !== pushUrls[0]) {
    return "Push requires exactly one configured URL for the named remote.";
  }

  const followTags = gitConfigValues(root, "push.followTags", true);
  if (!followTags || followTags.some(value => value !== "false")) {
    return "Push configuration may add tag refs implicitly.";
  }

  const recurseSubmodules = gitConfigValues(root, "push.recurseSubmodules");
  if (
    !recurseSubmodules
    || recurseSubmodules.some(value => !SAFE_FALSE_CONFIG_VALUES.has(value.trim().toLowerCase()))
  ) {
    return "Recursive submodule push configuration is unsupported.";
  }

  const mirror = gitConfigValues(root, `remote.${remote}.mirror`, true);
  if (!mirror || mirror.some(value => value !== "false")) {
    return "Mirror push configuration is unsupported.";
  }

  const configuredPushRefspecs = gitConfigValues(root, `remote.${remote}.push`);
  if (!configuredPushRefspecs || configuredPushRefspecs.length > 0) {
    return "Configured remote push refspecs are unsupported.";
  }
  return null;
}
function pushSafetyError(args, root, context) {
  let remote = null;
  let refspec = null;
  for (let i = 0; i < args.length; i += 1) {
    const value = args[i].value;
    if (args[i].dynamic) return "Shell-expanded push arguments are unsupported.";
    if (SAFE_PUSH_OPTIONS.has(value)) {
      if (refspec !== null) return "Push options after a refspec are unsupported.";
      continue;
    }
    if (value === "--" || value.startsWith("-")) {
      return "Unsupported or destructive push options are blocked.";
    }
    if (remote === null) remote = value;
    else if (refspec === null) refspec = value;
    else return "Push must contain exactly one refspec.";
  }

  if (remote === null || refspec === null || !/^[A-Za-z0-9_-]+$/.test(remote)) {
    return "Push requires a configured named remote and one explicit branch refspec.";
  }
  const remotes = gitOutputLines(root, ["remote"]);
  if (!remotes || !remotes.includes(remote)) {
    return "Push requires a configured named remote.";
  }

  const parts = refspec.split(":");
  if (parts.length > 2) return "Push refspec syntax is unsupported.";
  const source = parts[0];
  const destination = parts.length === 1 ? parts[0] : parts[1];
  if (!source || !destination || source.startsWith("+")) {
    return "Deletion and force refspecs are blocked.";
  }
  if (isProtectedRef(destination, context.protectedBranches)) {
    return "An explicit push to a protected branch is blocked.";
  }
  const defaultBranch = remoteDefaultBranch(root, remote);
  if (defaultBranch.status !== "ok") {
    return remoteDefaultBranchError(defaultBranch.status);
  }
  if (isProtectedRef(destination, new Set([defaultBranch.branch]))) {
    return "An explicit push to a protected branch is blocked.";
  }
  if (source !== "HEAD" && source !== context.current) {
    return "Push source must be the current branch or HEAD.";
  }
  if (parts.length === 1 && source !== context.current) {
    return "A single-name refspec must name the current branch.";
  }
  if (!validBranch(root, destination)) {
    return "Push destination must be one explicit branch name.";
  }
  if (!branchExists(root, destination) && !remoteTrackingBranchExists(root, remote, destination)) {
    return "Push destination must name a known local or remote-tracking branch.";
  }

  return pushConfigurationError(root, remote);
}
function configBooleanState(root, key) {
  const values = gitConfigValues(root, key, true);
  if (values === null) return { error: `Could not read Git setting ${key}.` };
  return {
    enabled: values.some(value => !SAFE_FALSE_CONFIG_VALUES.has(value.trim().toLowerCase())),
  };
}
function parseFetchLikeArguments(args, operation) {
  const positional = [];
  const options = { prune: null, pruneTags: false, ffOnly: false, noRebase: false, noRecurseSubmodules: false };
  for (const token of args) {
    if (token.dynamic) return { error: `${operation} arguments cannot contain shell expansions.` };
    const value = token.value;
    const option = value.toLowerCase();
    if (value === "--") return { error: `${operation} end-of-options form is unsupported.` };
    if (operation === "pull" && option === "--ff-only") {
      options.ffOnly = true;
      continue;
    }
    if (operation === "pull" && option === "--no-rebase") {
      options.noRebase = true;
      continue;
    }
    if (option === "--prune" || value === "-p") {
      options.prune = true;
      continue;
    }
    if (option === "--no-prune") {
      options.prune = false;
      continue;
    }
    if (option === "--prune-tags" || value === "-P" || option.startsWith("--prune-tags=")) {
      options.pruneTags = true;
      return { error: "Pruning local tags is unsupported." };
    }
    if (option === "--refmap" || option.startsWith("--refmap=")) {
      return { error: "Refmap can change local fetch destinations." };
    }
    if (option === "--stdin") {
      return { error: "Refspecs supplied through stdin cannot be evaluated safely." };
    }
    if (option === "--force" || option.startsWith("--force-") || /^-[^-]*f[^-]*$/i.test(value)) {
      return { error: "Forced fetch ref updates are unsupported." };
    }
    if (option === "--no-recurse-submodules") {
      options.noRecurseSubmodules = true;
      continue;
    }
    if (FETCH_SAFE_OPTIONS.has(option)) continue;
    if (value.startsWith("-")) return { error: `Unsupported ${operation} option ${value}.` };
    positional.push(value);
  }
  return { positional, options };
}
function validFetchRefspec(root, remote, refspec, configured = false) {
  if (!refspec || refspec.startsWith("^") || refspec.includes("+")) return false;
  const pieces = refspec.split(":");
  if (pieces.length > 2 || !pieces[0]) return false;
  const source = configured && pieces[0].startsWith("+") ? pieces[0].slice(1) : pieces[0];
  if (!source || source.includes("*") && !configured) return false;
  if (configured && source.startsWith("^")) return false;
  const sourceStars = (source.match(/\*/g) ?? []).length;
  if (sourceStars > 1) return false;
  if (pieces.length === 1) return !configured && !source.includes("*");
  const destination = pieces[1];
  if (!destination) return false;
  if (!configured && destination.includes("*")) return false;
  const destinationStars = (destination.match(/\*/g) ?? []).length;
  if (destinationStars > 1 || sourceStars !== destinationStars) return false;
  const expectedPrefix = `refs/remotes/${remote}/`;
  if (!destination.startsWith(expectedPrefix) || destination.length === expectedPrefix.length) return false;
  const checkableDestination = destination.replace("*", "codex-fetch-target");
  if (gitOutput(root, ["check-ref-format", checkableDestination]) === null) return false;
  return true;
}
function fetchConfiguration(root, remote, options) {
  const fetchRefspecs = gitConfigValues(root, `remote.${remote}.fetch`);
  if (!fetchRefspecs || fetchRefspecs.length === 0) {
    return { error: "The remote fetch refspec mapping is missing or could not be read." };
  }
  const destinations = [];
  for (const configuredRefspec of fetchRefspecs) {
    const value = configuredRefspec.startsWith("+") ? configuredRefspec.slice(1) : configuredRefspec;
    if (!validFetchRefspec(root, remote, value, true)) {
      return { error: "The remote fetch refspec does not map exclusively to its remote-tracking namespace." };
    }
    destinations.push(value.split(":")[1]);
  }

  const mirror = configBooleanState(root, `remote.${remote}.mirror`);
  if (mirror.error || mirror.enabled) {
    return { error: mirror.error ?? "Mirror fetch configuration is unsupported." };
  }
  const pruneStates = [
    configBooleanState(root, "fetch.prune"),
    configBooleanState(root, `remote.${remote}.prune`),
    configBooleanState(root, "fetch.pruneTags"),
    configBooleanState(root, `remote.${remote}.pruneTags`),
  ];
  const failedPruneState = pruneStates.find(state => state.error);
  if (failedPruneState) return { error: failedPruneState.error };
  const submoduleRecurse = configBooleanState(root, "submodule.recurse");
  if (submoduleRecurse.error) return { error: submoduleRecurse.error };
  if (!options.noRecurseSubmodules) {
    const recurse = gitConfigValues(root, "fetch.recurseSubmodules");
    if (recurse === null) return { error: "Could not read fetch.recurseSubmodules." };
    if (recurse.some(value => !SAFE_FALSE_CONFIG_VALUES.has(value.trim().toLowerCase()))) {
      return { error: "Recursive submodule fetch configuration is unsupported." };
    }
  }
  if (submoduleRecurse.enabled) return { error: "Recursive submodule fetch configuration is unsupported." };
  return {
    destinations,
    pruneEnabled: pruneStates.slice(0, 2).some(state => state.enabled),
    pruneTagsEnabled: pruneStates.slice(2).some(state => state.enabled),
  };
}
function resolveFetchRemote(root, context, positional, operation, options) {
  const remotes = gitOutputLines(root, ["remote"]);
  if (remotes === null) return { error: "Could not read configured Git remotes." };
  const explicitRemote = positional.length > 0;
  let remote = explicitRemote ? positional[0] : null;
  if (remote !== null) {
    if (!/^[A-Za-z0-9_-]+$/.test(remote) || !remotes.includes(remote)) {
      return { error: `${operation} requires one configured named remote.` };
    }
  } else {
    if (operation === "fetch") {
      const fetchAll = configBooleanState(root, "fetch.all");
      if (fetchAll.error || fetchAll.enabled) {
        return { error: fetchAll.error ?? "Fetching all remotes is unsupported without an explicit remote." };
      }
    }
    const branchRemote = gitConfigValues(root, `branch.${context.current}.remote`);
    if (branchRemote === null || branchRemote.length > 1) {
      return { error: "The current branch remote cannot be determined safely." };
    }
    remote = branchRemote[0] ?? (operation === "fetch" ? "origin" : null);
    if (!remote || remote === "." || !/^[A-Za-z0-9_-]+$/.test(remote) || !remotes.includes(remote)) {
      return { error: "A single configured named remote could not be resolved." };
    }
  }

  const refspecs = explicitRemote ? positional.slice(1) : [];
  if (refspecs.some(refspec => !validFetchRefspec(root, remote, refspec))) {
    return { error: "Fetch refspecs must be explicit, single-source updates to the named remote-tracking namespace." };
  }
  const configuration = fetchConfiguration(root, remote, options);
  if (configuration.error) return { error: configuration.error };
  const pruneEnabled = options.prune === null ? configuration.pruneEnabled : options.prune;
  if (pruneEnabled && configuration.pruneTagsEnabled) {
    return { error: "Pruning local tags through effective Git configuration is unsupported." };
  }
  const pruneDestinations = [...configuration.destinations];
  for (const refspec of refspecs) {
    if (refspec.includes(":")) pruneDestinations.push(refspec.split(":")[1]);
  }
  if (pruneEnabled && pruneDestinations.some(destination => !destination.startsWith(`refs/remotes/${remote}/`))) {
    return { error: "Prune destinations cannot be limited to the named remote-tracking namespace." };
  }
  return { remote, refspecs, configuration, options };
}
function fetchLikeSafetyError(args, root, context, operation) {
  const parsed = parseFetchLikeArguments(args, operation);
  if (parsed.error) return parsed.error;
  const { positional, options } = parsed;
  if (operation === "pull" && positional.length > 2) {
    return "Pull must contain at most one remote and one refspec.";
  }
  const resolved = resolveFetchRemote(root, context, positional, operation, options);
  if (resolved.error) return resolved.error;
  if (operation === "pull") {
    if (resolved.refspecs.length > 1) return "Pull with multiple refspecs could create an unintended merge.";
    if (resolved.refspecs.length === 0) {
      const upstreamRemote = gitConfigValues(root, `branch.${context.current}.remote`);
      const upstreamMerge = gitConfigValues(root, `branch.${context.current}.merge`);
      if (upstreamRemote === null || upstreamMerge === null) {
        return "The current branch upstream could not be read safely.";
      }
      if (
        upstreamRemote.length !== 1 || upstreamRemote[0] !== resolved.remote
        || upstreamMerge.length !== 1 || !upstreamMerge[0].startsWith("refs/heads/")
        || !validBranch(root, upstreamMerge[0].slice("refs/heads/".length))
      ) {
        return "Pull requires one configured branch upstream matching its named remote.";
      }
    }
    const mergeOptions = gitConfigValues(root, `branch.${context.current}.mergeOptions`);
    if (mergeOptions === null || mergeOptions.length > 0) {
      return "Branch merge options cannot be evaluated safely for pull.";
    }
    const pullSquash = configBooleanState(root, "pull.squash");
    if (pullSquash.error || pullSquash.enabled) {
      return pullSquash.error ?? "Pull squash configuration is unsupported.";
    }
    const pullRebase = gitConfigValues(root, "pull.rebase");
    const branchRebase = gitConfigValues(root, `branch.${context.current}.rebase`);
    const pullFf = gitConfigValues(root, "pull.ff");
    const mergeFf = gitConfigValues(root, "merge.ff");
    if (pullRebase === null || branchRebase === null || pullFf === null || mergeFf === null) {
      return "Effective pull integration settings could not be read safely.";
    }
    const rebaseTrueValues = new Set(["true", "yes", "on", "1", "merges", "m", "interactive", "i"]);
    if ([...pullRebase, ...branchRebase].some(value => rebaseTrueValues.has(value.trim().toLowerCase()))) {
      return "Pull rebase configuration can rewrite local history.";
    }
    const ffOnlyConfigured = pullFf.length > 0 && pullFf.every(value => value.trim().toLowerCase() === "only");
    const mergeFfOnlyConfigured = pullFf.length === 0 && mergeFf.length > 0
      && mergeFf.every(value => value.trim().toLowerCase() === "only");
    const explicitFfOnly = options.ffOnly;
    const ffOnlyEnforced = explicitFfOnly || ffOnlyConfigured || mergeFfOnlyConfigured;
    if (!ffOnlyEnforced) {
      return "Pull requires explicit fast-forward-only behavior through --ff-only or effective Git configuration.";
    }
    if (
      [...pullRebase, ...branchRebase].some(value =>
        !rebaseTrueValues.has(value.trim().toLowerCase())
        && !SAFE_FALSE_CONFIG_VALUES.has(value.trim().toLowerCase())
      )
    ) {
      return "Pull rebase configuration contains an unsupported value.";
    }
    if (
      [...pullFf, ...mergeFf].some(value =>
        !["only", "true", "false", "yes", "no", "on", "off", "1", "0"].includes(value.trim().toLowerCase())
      )
    ) {
      return "Pull fast-forward configuration contains an unsupported value.";
    }
  }
  return null;
}
function commitSafetyError(args) {
  let hasMessage = false;
  for (let index = 0; index < args.length; index += 1) {
    const value = args[index].value;
    const option = value.toLowerCase();
    if (
      option === "--amend" || option.startsWith("--amend=")
      || (option.startsWith("--") && option.length > 2 && "--amend".startsWith(option))
    ) {
      return "Commit amend rewrites local history and is blocked.";
    }
    if (option === "-m" || option === "--message") {
      if (args[index + 1] === undefined) return "Commit requires a literal explicit message.";
      hasMessage = true;
      index += 1;
      continue;
    }
    if (option.startsWith("--message=")) {
      hasMessage = true;
      continue;
    }
    if (["-a", "--all", "-q", "--quiet", "-v", "--verbose"].includes(option)) continue;
    return "Unsupported commit option or path form.";
  }
  if (!hasMessage) return "Commit requires an explicit -m or --message value.";
  return null;
}
function isProtectedRef(value, branches) {
  const ref = value.replace(/^\+/, "");
  for (const branch of branches) if (ref === branch || ref === "refs/heads/" + branch) return true;
  return false;
}
function safeProtectedSwitch(args, root, context) {
  if (!root || !context.current || !context.protectedBranches.has(context.current)) return false;
  let name = null, create = false;
  if (args.length === 2 && args[0].value === "-c" && !args[0].dynamic) {
    create = true;
    name = args[1];
  } else if (args.length === 1) name = args[0];
  if (!name || name.dynamic || !validBranch(root, name.value) || context.protectedBranches.has(name.value)) {
    return false;
  }
  return create ? !branchExists(root, name.value) : branchExists(root, name.value);
}
function branchTargetMutation(args, context) {
  const values = args.map(x => x.value.toLowerCase());
  const refMutation = values.some(x =>
    ["-d", "-D", "-m", "-M", "-c", "-C", "--delete", "--move", "--copy"].includes(x)
  );
  if (refMutation) {
    return args.some(x => !x.dynamic && context.protectedBranches.has(x.value.replace(/^refs\/heads\//, "")));
  }
  if (!values.some(x => x === "-f" || x === "--force")) return false;
  const branch = args.find(x => !x.dynamic && !x.value.startsWith("-"));
  return Boolean(branch && context.protectedBranches.has(branch.value.replace(/^refs\/heads\//, "")));
}
function evaluateGit(tokens, canonical, root) {
  if (tokens.length < 2) return { decision: null, mutation: false };
  const exe = tokens[0].value.toLowerCase();
  if (exe !== "git" && exe !== "git.exe") return { decision: null, mutation: false };
  const subToken = tokens[1];
  if (subToken.value.startsWith("-")) {
    return { decision: deny("Git global options before the subcommand are unsupported."), mutation: true };
  }
  if (subToken.dynamic) {
    return { decision: deny("Shell-expanded Git subcommands are unsupported."), mutation: true };
  }
  const sub = subToken.value.toLowerCase(), args = tokens.slice(2);
  if (readOnlyGit(sub, args)) return { decision: null, mutation: false };
  if (!canonical || !canonical.valid || !root) {
    return {
      decision: deny("State-changing Git requires the literal canonical repository root and one direct Git command."),
      mutation: true,
    };
  }
  if (
    args.some(x =>
      x.dynamic && (GIT_DYNAMIC_ARGUMENTS.has(sub) || GIT_PROMPT_FAMILIES.has(sub) || GIT_FORBIDDEN.has(sub))
    )
  ) {
    return {
      decision: deny("Shell-expanded arguments for a prompt or forbidden Git command are unsupported."),
      mutation: true,
    };
  }
  if (
    sub === "rebase" && args.some(x =>
      ["-x", "--exec", "-i", "--interactive"].includes(x.value.toLowerCase())
      || x.value.toLowerCase().startsWith("--exec=")
    )
  ) return { decision: deny("Interactive and exec-script rebase forms are unsupported."), mutation: true };
  const context = gitContext(root);
  if (!context.current) return { decision: deny("The current local branch could not be resolved."), mutation: true };
  if (context.error) return { decision: deny(context.error), mutation: true };
  if (sub === "commit") {
    const commitError = commitSafetyError(args);
    if (commitError) return { decision: deny(commitError), mutation: true };
    if (context.protectedBranches.has(context.current)) {
      return { decision: deny("State-changing Git on a protected branch is blocked."), mutation: true };
    }
    return { decision: null, mutation: true };
  }
  if (sub === "fetch") {
    const fetchError = fetchLikeSafetyError(args, root, context, "fetch");
    return fetchError
      ? { decision: deny(fetchError), mutation: true }
      : { decision: null, mutation: true };
  }
  if (sub === "pull") {
    if (context.protectedBranches.has(context.current)) {
      return { decision: deny("State-changing Git on a protected branch is blocked."), mutation: true };
    }
    const pullError = fetchLikeSafetyError(args, root, context, "pull");
    return pullError
      ? { decision: deny(pullError), mutation: true }
      : { decision: null, mutation: true };
  }
  if (sub === "push" && context.protectedBranches.has(context.current)) {
    return { decision: deny("State-changing Git on a protected branch is blocked."), mutation: true };
  }
  if (sub === "push") {
    const pushError = pushSafetyError(args, root, context);
    if (pushError) return { decision: deny(pushError), mutation: true };
  }
  if (sub === "branch" && branchTargetMutation(args, context)) {
    return { decision: deny("Changing a protected branch ref is blocked."), mutation: true };
  }
  if (context.protectedBranches.has(context.current)) {
    if (sub === "switch" && safeProtectedSwitch(args, root, context)) return { decision: null, mutation: true };
    return { decision: deny("State-changing Git on a protected branch is blocked."), mutation: true };
  }
  return { decision: null, mutation: true };
}
function ghAction(tokens) {
  if (tokens.length < 2) return { family: "", action: "", subfamily: "", invalid: false };
  const f = tokens[1];
  if (f.dynamic || f.value.startsWith("-")) return { family: "", action: "", subfamily: "", invalid: true };
  const family = f.value.toLowerCase();
  if (tokens.length < 3) return { family, action: "", subfamily: "", invalid: false };
  const second = tokens[2];
  if (second.value.startsWith("-") && GH_SUBCOMMAND_OPTIONS.has(family)) {
    return { family, action: "", subfamily: "", invalid: true };
  }
  if (family === "repo" && ["autolink", "deploy-key"].includes(second.value.toLowerCase())) {
    if (tokens.length < 4) return { family, action: "", subfamily: second.value.toLowerCase(), invalid: false };
    const third = tokens[3];
    if (third.value.startsWith("-") || third.dynamic) return { family, action: "", subfamily: "", invalid: true };
    return { family, action: third.value.toLowerCase(), subfamily: second.value.toLowerCase(), invalid: false };
  }
  if (second.dynamic) return { family, action: "", subfamily: "", invalid: true };
  return { family, action: second.value.toLowerCase(), subfamily: "", invalid: false };
}
function evaluateGh(tokens) {
  if (!tokens.length || !["gh", "gh.exe"].includes(tokens[0].value.toLowerCase())) return null;
  const p = ghAction(tokens);
  if (p.invalid) return deny("GitHub CLI options before a supported family or subcommand are unsupported.");
  const values = tokens.map(x => x.value.toLowerCase());
  if (
    p.family === "auth" && values.includes("status")
    && tokens.some(x =>
      x.value.toLowerCase() === "--show-token" || x.value.toLowerCase() === "-t"
      || x.value.toLowerCase().startsWith("--show-token=")
    )
  ) return deny("gh auth status token-display flags are blocked.");
  if (p.family === "api" || (p.family === "repo" && p.action === "sync")) {
    return tokens.some(x => x.dynamic)
      ? deny("Shell-expanded arguments for a forbidden GitHub CLI command are unsupported.")
      : null;
  }
  const isSubfamilyAction = (p.subfamily === "autolink" && ["create", "new", "delete"].includes(p.action))
    || (p.subfamily === "deploy-key" && ["add", "delete"].includes(p.action));
  const prompt = GH_PROMPT_FAMILIES.has(p.family) || Boolean(GH_ACTIONS.get(p.family)?.has(p.action))
    || isSubfamilyAction;
  if (prompt && tokens.some(x => x.dynamic)) {
    return deny("Shell-expanded arguments for an approval-required GitHub CLI command are unsupported.");
  }
  return null;
}
function hasUnsupportedGitWrapper(tokens) {
  const values = tokens.map(x => x.value.toLowerCase());
  const gitIndex = values.findIndex(x => x === "git" || x === "git.exe");
  if (gitIndex < 0) return false;
  if (values[0] === "env" || values[0] === "command") return true;
  for (let i = 0; i < gitIndex; i += 1) if (/^[a-z_][a-z0-9_]*=/.test(values[i])) return true;
  return false;
}
function isDelete(tokens) {
  return tokens.length > 0 && DELETE_COMMANDS.has(tokens[0].value.toLowerCase());
}
function opaqueShell(tokens) {
  if (!tokens.length) return false;
  const values = tokens.map(x => x.value.toLowerCase());
  const executable = values[0].split(/[\\/]/).pop();
  const args = values.slice(1);
  if (["bash", "bash.exe", "sh", "sh.exe", "zsh", "zsh.exe"].includes(executable)) {
    return args[0] === "-c";
  }
  if (["pwsh", "pwsh.exe", "powershell", "powershell.exe"].includes(executable)) {
    return ["-command", "-encodedcommand"].includes(args[0]);
  }
  if (["cmd", "cmd.exe"].includes(executable)) {
    const commandOption = args.findIndex(x => /^\/[ck]$/i.test(x));
    return commandOption >= 0 && args.slice(0, commandOption).every(x => /^\/[^\s;&|]+$/.test(x));
  }
  return executable === "invoke-expression";
}
function evaluateCommand(command, cwd) {
  const root = repoRoot(cwd), canonical = canonicalCommand(command, root);
  const parsed = splitCommands(canonical ? canonical.command : command, canonical ? canonical.shell : "posix");
  if (parsed.segments.some(opaqueShell)) return deny("Nested shell wrappers are unsupported.");
  if (parsed.parseError) {
    return /(?:^|[\s;&|])(?:git(?:\.exe)?|gh(?:\.exe)?)(?=\s|$)/i.test(command)
      ? deny("Shell quoting could not be parsed safely.")
      : null;
  }
  const git = [];
  let mutationCount = 0;
  for (const tokens of parsed.segments) {
    if (!tokens.length) continue;
    const first = tokens[0].value.toLowerCase();
    if (hasUnsupportedGitWrapper(tokens)) {
      return deny("Git command wrappers and command-local environment overrides are unsupported.");
    }
    if (first === "gh" || first === "gh.exe") {
      const decision = evaluateGh(tokens);
      if (decision) return decision;
    }
    if (first === "git" || first === "git.exe") {
      git.push(tokens);
      const result = evaluateGit(tokens, canonical, root);
      if (result.decision) return result.decision;
      if (result.mutation) mutationCount += 1;
    }
    if (isDelete(tokens)) return deny("Direct command-based deletion is forbidden.");
  }
  if (mutationCount && (!canonical || !canonical.valid || git.length !== 1 || parsed.segments.length !== 1)) {
    return deny("State-changing Git requires one direct command after the literal canonical repository root.");
  }
  if (canonical && git.length === 0) return deny("Canonical Git form must end in one direct Git command.");
  return null;
}
function validate(raw) {
  let p;
  try {
    p = JSON.parse(raw.replace(/^\uFEFF/, ""));
  } catch {
    throw new Error("invalid JSON input");
  }
  if (!p || typeof p !== "object" || Array.isArray(p)) throw new Error("payload must be an object");
  if (p.tool_name !== "Bash") throw new Error("tool_name must be Bash");
  if (!p.tool_input || typeof p.tool_input !== "object" || Array.isArray(p.tool_input)) {
    throw new Error("tool_input must be an object");
  }
  if (typeof p.tool_input.command !== "string") throw new Error("tool_input.command must be a string");
  return p;
}
async function main() {
  try {
    let raw = "";
    process.stdin.setEncoding("utf8");
    for await (const chunk of process.stdin) raw += chunk;
    const p = validate(raw), decision = evaluateCommand(p.tool_input.command, process.cwd());
    if (decision) process.stdout.write(JSON.stringify(decision));
  } catch (error) {
    process.stderr.write(
      "PreToolUse policy hook: " + (error instanceof Error ? error.message : "invalid input") + "\n",
    );
    process.exitCode = 2;
  }
}
await main();
