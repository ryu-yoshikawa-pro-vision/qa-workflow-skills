"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const vm = require("node:vm");
const { spawnSync } = require("node:child_process");
const { test } = require("node:test");

const ROOT = path.resolve(__dirname, "..");
const JS = fs.readFileSync(path.join(ROOT, "assets", "form.js"), "utf8");
const end = "  setup();\n})();";
assert.ok(JS.endsWith(end + "\n"), "production code shape changed");
const INSTRUMENTED = JS.replace(
  end,
  "  globalThis.formTest = { state, load, save, answerStatus, exportMarkdown, copyAnswer };\n})();",
);

function makeForm() {
  return {
    schemaVersion: 1,
    formId: "qa-review",
    title: "QA確認",
    output: { heading: "QA回答", filename: "qa-answers.md" },
    questions: [
      {
        id: "Q-017", number: "No.1", group: "環境",
        title: "検証環境を指定してください",
        context: "未確定の実行条件",
        choices: [{ id: "A", label: "試験環境" }, { id: "B", label: "本番相当" }],
      },
      {
        id: "Q-018", number: "No.2", group: "環境",
        title: "補足事項はありますか？", choices: [],
      },
    ],
  };
}

function generatedForm(source) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agent-answer-form-"));
  try {
    const input = path.join(dir, "questions.json");
    const output = path.join(dir, "questions.html");
    fs.writeFileSync(input, JSON.stringify(source), "utf8");
    const run = spawnSync("python", [
      path.join(ROOT, "scripts", "build_form.py"),
      "--input", input, "--output", output,
    ], { encoding: "utf8" });
    assert.equal(run.status, 0, run.stderr);
    const html = fs.readFileSync(output, "utf8");
    const match = html.match(/<script id="questions-json" type="application\/json">([\s\S]*?)<\/script>/);
    assert.ok(match, "embedded JSON missing");
    return JSON.parse(match[1]);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function harness(form, storage = new Map(), opts = {}) {
  const nodes = new Map();
  let modalOpened = false;
  let copiedText = null;
  const el = (id) => {
    if (!nodes.has(id)) nodes.set(id, { textContent: "", hidden: true });
    return nodes.get(id);
  };
  const document = {
    getElementById(id) {
      if (id === "questions-json") return { textContent: JSON.stringify(form) };
      return el(id);
    },
    createElement() {
      return {
        value: "", style: {}, setAttribute() {}, focus() {}, select() {}, remove() {},
      };
    },
    body: { append() {} },
    activeElement: { focus() {} },
    execCommand() { return opts.execCopy ?? false; },
  };
  el("export-dialog").showModal = () => { modalOpened = true; };
  const localStorage = {
    getItem(key) {
      if (opts.storageBlocked) throw Error("storage disabled");
      return storage.get(key) ?? null;
    },
    setItem(key, value) {
      if (opts.storageBlocked) throw Error("storage disabled");
      storage.set(key, value);
    },
  };
  const sandbox = {
    document, localStorage, setTimeout() { return 1; }, clearTimeout() {},
    navigator: {
      clipboard: opts.clipboard
        ? { async writeText(text) { copiedText = text; } }
        : undefined,
    },
    window: { isSecureContext: Boolean(opts.clipboard) },
  };
  vm.runInNewContext(INSTRUMENTED, sandbox, { filename: "form.js" });
  return {
    api: sandbox.formTest,
    storage,
    node: el,
    modalOpened: () => modalOpened,
    copiedText: () => copiedText,
  };
}

test("回答Markdownは表示番号とQ IDを保持し、改行で別見出しを作らない", () => {
  const input = makeForm();
  input.questions[0].title += "\n## Q-999 偽の質問";
  input.questions[0].choices[0].label = "試験環境\n## Q-888 偽の選択肢";
  const form = generatedForm(input);
  const h = harness(form);
  h.api.state["Q-017"].choices = ["A"];
  h.api.state["Q-017"].note = "補足\n## Q-777 偽の回答";
  const markdown = h.api.exportMarkdown(true);
  assert.match(markdown, /^## No\.1 .*検証環境を指定してください/m);
  assert.match(markdown, /^- 質問ID：Q-017$/m);
  assert.match(markdown, /^- 質問ID：Q-018$/m);
  assert.doesNotMatch(markdown, /^## Q-(999|888|777) /m);
  assert.match(markdown, /^        ## Q-777/m);
  assert.match(markdown, /A\. 試験環境 ## Q-888/);
});

test("記入済みと全問を区別し、保留と自由記述を判定する", () => {
  const form = generatedForm(makeForm());
  const h = harness(form);
  assert.equal(h.api.answerStatus(form.questions[0]), "未回答");
  assert.doesNotMatch(h.api.exportMarkdown(false), /Q-017/);
  assert.match(h.api.exportMarkdown(true), /- 質問ID：Q-017/);
  h.api.state["Q-017"].note = "検証環境は調整中";
  assert.equal(h.api.answerStatus(form.questions[0]), "一部回答");
  h.api.state["Q-017"].held = true;
  assert.equal(h.api.answerStatus(form.questions[0]), "保留");
  h.api.state["Q-017"].held = false;
  h.api.state["Q-017"].choices = ["B"];
  assert.equal(h.api.answerStatus(form.questions[0]), "回答済み");
  h.api.state["Q-018"].note = "補足";
  assert.equal(h.api.answerStatus(form.questions[1]), "回答済み");
  assert.match(h.api.exportMarkdown(false), /- 質問ID：Q-018/);
});

test("質問の意味が変わった回答だけを除外し、無関係な回答を維持する", () => {
  const first = generatedForm(makeForm());
  const storage = new Map();
  const h1 = harness(first, storage);
  h1.api.state["Q-017"].choices = ["A"];
  h1.api.state["Q-018"].note = "変更不要の回答";
  h1.api.save();
  const saved = JSON.parse(storage.get("answer-form:qa-review:v3"));
  assert.equal(saved.version, 3);
  assert.equal(saved.answers["Q-017"].definitionHash, first.questions[0]._definitionHash);
  const input = makeForm();
  input.questions[0].choices[0].label = "選択肢の意味を変更";
  const second = generatedForm(input);
  const h2 = harness(second, storage);
  h2.api.load();
  assert.equal(h2.api.state["Q-017"].choices.length, 0);
  assert.equal(h2.api.state["Q-018"].note, "変更不要の回答");
  assert.match(h2.node("storage-note").textContent, /1問の質問定義が変更/);
});

test("表示番号のみ変更時は復元でき、旧形式は保持して自動適用しない", () => {
  const input = makeForm();
  const original = generatedForm(input);
  const storage = new Map();
  const h1 = harness(original, storage);
  h1.api.state["Q-017"].choices = ["B"];
  h1.api.save();
  input.questions[0].number = "No.9";
  const revised = generatedForm(input);
  assert.equal(original.questions[0]._definitionHash, revised.questions[0]._definitionHash);
  const h2 = harness(revised, storage);
  h2.api.load();
  assert.equal(h2.api.state["Q-017"].choices[0], "B");
  const legacy = new Map([[
    "answer-form:qa-review",
    JSON.stringify({ version: 2, answers: { "Q-017": { choices: ["A"] } } }),
  ]]);
  const h3 = harness(revised, legacy);
  h3.api.load();
  assert.equal(h3.api.state["Q-017"].choices.length, 0);
  assert.match(h3.node("storage-note").textContent, /以前のHTMLからコピー/);
  h3.api.save();
  assert.ok(legacy.has("answer-form:qa-review"), "旧形式を上書きしない");
});

test("安全なクリップボードでは直接コピーし、失敗時もダイアログを開かない", async () => {
  const form = generatedForm(makeForm());
  const h = harness(form, new Map(), { clipboard: true });
  await h.api.copyAnswer("コピー本文");
  assert.equal(h.copiedText(), "コピー本文");
  assert.equal(h.modalOpened(), false);
  const fallback = harness(form, new Map(), { execCopy: false });
  await fallback.api.copyAnswer("コピー不可本文");
  assert.equal(fallback.modalOpened(), false);
  assert.match(fallback.node("toast").textContent, /手動でコピー/);
});

test("保存領域が利用できない場合は回答を受け付けられる", () => {
  const form = generatedForm(makeForm());
  const h = harness(form, new Map(), { storageBlocked: true });
  h.api.load();
  h.api.state["Q-017"].choices = ["B"];
  h.api.save();
  assert.match(h.api.exportMarkdown(false), /- 質問ID：Q-017/);
  assert.match(h.node("storage-note").textContent, /保存を利用できません/);
});
