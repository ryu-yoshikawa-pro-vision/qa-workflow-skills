#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import path from "node:path";

const EVENT = "PreToolUse";
const GIT_PROMPT = new Set([
  "commit",
  "merge",
  "rebase",
  "pull",
  "push",
  "fetch",
  "reset",
  "am",
  "cherry-pick",
  "revert",
  "restore",
  "checkout",
  "switch",
]);
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
function gitConfigValues(root, key, boolean = false) {
  return gitOutputLines(root, ["config", ...(boolean ? ["--bool"] : []), "--get-all", key]);
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
  const originHead = gitOutput(root, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"]);
  const protectedBranches = new Set(["main", "master"]);
  if (originHead && originHead.startsWith("refs/remotes/origin/")) {
    protectedBranches.add(originHead.slice("refs/remotes/origin/".length));
  }
  return { current, protectedBranches };
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
  if (["status", "rev-parse", "ls-files", "check-ignore", "cat-file", "blame", "version", "help"].includes(op)) {
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
    ||recurseSubmodules.some(value => !SAFE_FALSE_CONFIG_VALUES.has(value.trim().toLowerCase()))
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
  if (destination !== context.current) {
    return "Push destination must be the current branch.";
  }
  if (source !== "HEAD" && source !== context.current) {
    return "Push source must be the current branch or HEAD.";
  }
  if (!validBranch(root, destination)) {
    return "Push destination must be one explicit branch name.";
  }

  return pushConfigurationError(root, remote);
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
  if (args.some(x => x.dynamic && (GIT_PROMPT.has(sub) || GIT_PROMPT_FAMILIES.has(sub) || GIT_FORBIDDEN.has(sub)))) {
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
