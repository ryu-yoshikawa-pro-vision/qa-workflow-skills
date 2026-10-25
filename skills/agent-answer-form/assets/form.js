(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const form = JSON.parse(byId("questions-json").textContent);
  const questions = form.questions;
  // v1/v2の保存領域を残し、fingerprintのない回答を誤って復元しない。
  const STORAGE_KEY = "answer-form:" + form.formId + ":v3";
  const LEGACY_STORAGE_KEY = "answer-form:" + form.formId;
  const initial = (q) => ({ multiple: q.defaultMultiple === true, choices: [], note: "", held: false });
  const state = Object.fromEntries(questions.map((q) => [q.id, initial(q)]));
  let canPersist = true;
  let toastTimer;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function notify(message) {
    const node = byId("toast");
    node.textContent = message;
    node.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      node.hidden = true;
    }, 2700);
  }
  function load() {
    let raw;
    try {
      raw = localStorage.getItem(STORAGE_KEY);
    } catch (_) {
      canPersist = false;
      byId("storage-note").textContent = "ブラウザ内の保存を利用できません。回答をコピーまたは保存してください。";
      return;
    }
    if (!raw) {
      try {
        if (localStorage.getItem(LEGACY_STORAGE_KEY)) {
          byId("storage-note").textContent =
            "旧形式の回答は定義を確認できないため自動復元しません。必要な回答は以前のHTMLからコピーしてください。";
        }
      } catch (_) { /* 保存領域が利用できなくても、フォームの入力は続行する。 */ }
      return;
    }
    try {
      const stored = JSON.parse(raw);
      if (!stored || stored.version !== 3 || !stored.answers || typeof stored.answers !== "object") {
        byId("storage-note").textContent = "保存形式を確認できないため、以前の回答を復元しません。";
        return;
      }
      let skipped = 0;
      for (const q of questions) {
        const answer = stored.answers[q.id];
        if (!answer || typeof answer !== "object") continue;
        if (answer.definitionHash !== q._definitionHash) {
          skipped++;
          continue;
        }
        const ids = new Set(q.choices.map((c) => c.id));
        const picked = Array.isArray(answer.choices) ? answer.choices.filter((id) => ids.has(id)) : [];
        const multiple = answer.multiple === true;
        state[q.id] = {
          multiple,
          choices: multiple ? [...new Set(picked)] : picked.slice(0, 1),
          note: typeof answer.note === "string" ? answer.note.slice(0, 10000) : "",
          held: answer.held === true,
        };
      }
      if (skipped) {
        byId("storage-note").textContent =
          skipped + "問の質問定義が変更されたため、その回答を自動復元しませんでした。";
      }
    } catch (_) {
      byId("storage-note").textContent = "以前の回答を読み込めません。新しく入力した回答は保存を試みます。";
    }
  }
  function save() {
    if (!canPersist) return;
    try {
      const answers = Object.fromEntries(questions.map((q) => [
        q.id,
        { ...state[q.id], definitionHash: q._definitionHash },
      ]));
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 3, answers }));
      byId("storage-note").textContent = "このブラウザ内に自動保存しました。";
    } catch (_) {
      canPersist = false;
      byId("storage-note").textContent = "自動保存できません。回答をコピーまたはMarkdown保存してください。";
    }
  }
  function isFilled(q) {
    const answer = state[q.id];
    return answer.held || answer.choices.length > 0 || answer.note.trim().length > 0;
  }
  function answerStatus(q) {
    const answer = state[q.id];
    if (answer.held) return "保留";
    if (answer.choices.length || (!q.choices.length && answer.note.trim())) return "回答済み";
    return answer.note.trim() ? "一部回答" : "未回答";
  }
  function updateProgress() {
    const answered = questions.filter(isFilled).length;
    byId("progress-count").textContent = String(answered);
    byId("progress-bar").style.width = (100 * answered / questions.length) + "%";
    byId("progress-detail").textContent = "回答・保留 " + answered + "問／未記入 " + (questions.length - answered)
      + "問";
    for (const link of byId("group-nav").querySelectorAll("[data-nav-group]")) {
      const group = link.dataset.navGroup;
      const inGroup = questions.filter((q) => q.group === group);
      link.lastElementChild.textContent = inGroup.filter(isFilled).length + "/" + inGroup.length;
    }
  }
  function updateChoiceState(card, q) {
    const answer = state[q.id];
    card.querySelectorAll("label.choice").forEach((row) => {
      const active = answer.choices.includes(row.dataset.choiceId);
      row.querySelector("input").checked = active;
      row.classList.toggle("chosen", active);
    });
    const status = card.querySelector("[data-status]");
    const value = answerStatus(q);
    status.textContent = value;
    status.className = "pill " + (value === "回答済み" ? "done" : value === "未回答" ? "todo" : "partial");
    card.querySelector("[data-hold-toggle]").checked = answer.held;
    if (q.choices.length) {
      card.querySelector("[data-multi-toggle]").checked = answer.multiple;
      const indicator = card.querySelector("[data-multi-indicator]");
      indicator.textContent = answer.multiple ? "オン" : "オフ";
      indicator.classList.toggle("on", answer.multiple);
      card.querySelector("[data-multi-help]").textContent = answer.multiple
        ? "複数の選択肢を選べます"
        : "選択できるのは1つです";
    }
  }
  function buildChoiceRows(card, q, container) {
    const answer = state[q.id];
    container.replaceChildren();
    container.setAttribute("role", answer.multiple ? "group" : "radiogroup");
    container.setAttribute("aria-label", (q.number || q.id) + " の選択肢");
    for (const choice of q.choices) {
      const row = element("label", "choice");
      row.dataset.choiceId = choice.id;
      const input = element("input");
      input.type = answer.multiple ? "checkbox" : "radio";
      input.name = "option-" + q.id;
      input.value = choice.id;
      input.checked = answer.choices.includes(choice.id);
      row.classList.toggle("chosen", input.checked);
      row.append(input, element("b", "", choice.id), element("span", "", choice.label));
      input.addEventListener("change", () => {
        if (answer.multiple) {
          answer.choices = input.checked
            ? [...answer.choices.filter((id) => id !== choice.id), choice.id]
            : answer.choices.filter((id) => id !== choice.id);
        } else {
          answer.choices = [choice.id];
        }
        answer.choices = q.choices.filter((c) => answer.choices.includes(c.id)).map((c) => c.id);
        updateChoiceState(card, q);
        save();
        updateProgress();
      });
      container.append(row);
    }
  }
  function buildCard(q) {
    const answer = state[q.id];
    const card = element("section", "question-card");
    card.id = "q-" + q.id;
    const top = element("div", "card-top");
    top.append(element("span", "num", q.number || q.id));
    if (q.priority) top.append(element("span", "pill" + (q.priority === "最優先" ? " high" : ""), q.priority));
    top.append(element("span", "pill", q.group));
    const status = element("span", "pill", answerStatus(q));
    status.dataset.status = "";
    top.append(status);
    card.append(top, element("h3", "", q.title));
    if (q.context) card.append(element("p", "context", q.context));

    if (q.choices.length) {
      const choiceLine = element("div", "choice-row");
      const toggle = element("label", "multi-toggle");
      const check = element("input");
      check.type = "checkbox";
      check.dataset.multiToggle = "";
      check.checked = answer.multiple;
      check.setAttribute("aria-label", (q.number || q.id) + "：複数選択");
      const indicator = element("span", "switch-label", answer.multiple ? "オン" : "オフ");
      indicator.dataset.multiIndicator = "";
      toggle.append(check, element("span", "", "複数選択"), indicator);
      choiceLine.append(element("h4", "", "選択肢"), toggle);
      card.append(choiceLine);
      const choicesContainer = element("div", "choice-list");
      card.append(choicesContainer);
      const optionsActions = element("div", "meta-actions");
      const help = element("span", "badge-count");
      help.dataset.multiHelp = "";
      const clear = element("button", "text-btn", "選択を解除");
      clear.type = "button";
      optionsActions.append(help, clear);
      card.append(optionsActions);
      check.addEventListener("change", () => {
        if (!check.checked && answer.choices.length > 1) {
          if (!confirm("単一選択に戻すと、先頭の選択肢だけが残ります。切り替えますか？")) {
            check.checked = true;
            return;
          }
          answer.choices = answer.choices.slice(0, 1);
        }
        answer.multiple = check.checked;
        buildChoiceRows(card, q, choicesContainer);
        updateChoiceState(card, q);
        save();
        updateProgress();
      });
      clear.addEventListener("click", () => {
        answer.choices = [];
        updateChoiceState(card, q);
        save();
        updateProgress();
      });
      buildChoiceRows(card, q, choicesContainer);
    }
    if (q.recommendation) card.append(element("div", "recommendation", "推奨：" + q.recommendation));
    const grid = element("div", "input-grid");
    const left = element("div");
    const holdLabel = element("label", "hold-toggle");
    const holdToggle = element("input");
    holdToggle.type = "checkbox";
    holdToggle.dataset.holdToggle = "";
    holdToggle.checked = answer.held;
    holdLabel.append(holdToggle, element("span", "", "保留"));
    holdToggle.addEventListener("change", () => {
      answer.held = holdToggle.checked;
      updateChoiceState(card, q);
      save();
      updateProgress();
    });
    left.append(holdLabel);
    const right = element("div");
    const noteLabel = element("label", "field-label", "補足・自由記述");
    noteLabel.htmlFor = "note-" + q.id;
    const note = element("textarea", "memo");
    note.id = noteLabel.htmlFor;
    note.rows = 3;
    note.maxLength = 10000;
    note.placeholder = "必要な条件・時刻・例外などを記入してください";
    note.value = answer.note;
    note.addEventListener("input", () => {
      answer.note = note.value;
      updateChoiceState(card, q);
      save();
      updateProgress();
    });
    right.append(noteLabel, note);
    grid.append(left, right);
    card.append(grid);
    updateChoiceState(card, q);
    return card;
  }
  function matches(q, query, filter, priority) {
    if (filter === "filled" && !isFilled(q) || filter === "blank" && isFilled(q)) return false;
    if (priority !== "all" && q.priority !== priority) return false;
    const answer = state[q.id];
    return !query
      || [
        q.id,
        q.number || "",
        q.title,
        q.group,
        q.priority || "",
        q.context || "",
        q.recommendation || "",
        ...q.choices.map((c) => c.label),
        answer.note,
      ].join(" ").toLowerCase().includes(query);
  }
  function render() {
    const root = byId("questions");
    root.replaceChildren();
    const query = byId("search").value.trim().toLowerCase();
    const filter = byId("answer-filter").value;
    const priority = byId("priority-filter").value;
    let count = 0;
    const groups = [...new Set(questions.map((q) => q.group))];
    groups.forEach((group, i) => {
      const found = questions.filter((q) => q.group === group && matches(q, query, filter, priority));
      if (!found.length) return;
      count += found.length;
      const heading = element("div", "group-header");
      heading.id = "group-" + i;
      const left = element("div");
      left.append(element("h2", "", group), element("p", "", "該当 " + found.length + "問"));
      heading.append(left, element("span", "group-count", found.length + "件"));
      root.append(heading);
      found.forEach((q) => root.append(buildCard(q)));
    });
    byId("shown-count").textContent = count + "件表示 / 全" + questions.length + "件";
    byId("empty").hidden = count !== 0;
    updateProgress();
  }
  // JSONの改行が質問見出しや選択肢から別のMarkdownブロックを作らないようにする。
  function oneLine(value) {
    return String(value).replace(/[\r\n\u2028\u2029]+/g, " ").replace(/[\t ]+/g, " ").trim();
  }
  function exportMarkdown(all) {
    const selected = questions.filter((q) => all || isFilled(q));
    const output = [
      "# " + oneLine(form.output.heading),
      "",
      "- 対象：" + oneLine(form.output.context || form.title),
      "- 出力対象：" + (all ? "全" + questions.length + "問" : "回答または保留のある質問のみ"),
      "- 注記：推奨案は回答に含まれません。",
      "",
    ];
    for (const q of selected) {
      const answer = state[q.id];
      output.push(
        "## " + oneLine(q.number || q.id) + " 【" + [q.priority, q.group].filter(Boolean).map(oneLine).join("／") + "】 " + oneLine(q.title),
        "",
        "- 質問ID：" + q.id,
        "- 回答状況：" + answerStatus(q),
      );
      if (q.choices.length) {
        const chosen = q.choices.filter((c) => answer.choices.includes(c.id))
          .map((c) => c.id + ". " + oneLine(c.label));
        output.push("- 選択方式：" + (answer.multiple ? "複数選択" : "単一選択"));
        output.push("- 選択：" + (chosen.length ? chosen.join(" / ") : "未選択"));
      }
      if (answer.note.trim()) {
        output.push("- 補足：", "");
        // 8スペースのコードブロックに収め、回答本文の ## 等を別の質問見出しにしない。
        output.push(...answer.note.trim().split(/\r\n|\r|\n|\u2028|\u2029/).map((line) => "        " + line));
      }
      if (all && !isFilled(q)) output.push("- 回答：未記入");
      output.push("");
    }
    if (!selected.length) output.push("記入された回答はありません。", "");
    return output.join("\n");
  }
  function openDialog(all) {
    byId("export-text").value = exportMarkdown(all);
    byId("export-dialog").showModal();
  }
  async function copyAnswer(content) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(content);
        notify("回答をコピーしました");
        return;
      }
    } catch (_) { /* 権限や実行環境によってClipboard APIが使えない場合がある。 */ }
    // ダイアログを開かず、旧ブラウザやfile://でも直接コピーを試みる。
    const field = element("textarea");
    field.value = content;
    field.setAttribute("readonly", "");
    field.setAttribute("aria-hidden", "true");
    field.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
    const active = document.activeElement;
    document.body.append(field);
    field.focus();
    field.select();
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (_) { /* コピー不可の場合はプレビューから手動コピーできる。 */ }
    field.remove();
    if (active && typeof active.focus === "function") active.focus();
    notify(
      copied ? "回答をコピーしました" : "コピーできませんでした。「出力内容を確認」から手動でコピーしてください。",
    );
  }
  function setup() {
    document.title = form.title + "｜回答フォーム";
    byId("form-eyebrow").textContent = form.subtitle || "";
    byId("form-eyebrow").hidden = !form.subtitle;
    byId("form-title").textContent = form.title;
    byId("form-description").textContent = form.description || "";
    byId("progress-total").textContent = "／" + questions.length + "問";
    byId("copy-all").textContent = "全" + questions.length + "問をコピー";
    if (form.notice) {
      byId("form-notice").hidden = false;
      byId("form-notice").textContent = form.notice;
    }
    byId("form-footer").textContent = form.title + " ／ このファイルから外部サービスへの通信は行いません。";
    const priorityFilter = byId("priority-filter");
    const priorities = [...new Set(questions.map((q) => q.priority).filter(Boolean))];
    priorityFilter.hidden = priorities.length === 0;
    priorities.forEach((name) => {
      const option = element("option", "", name);
      option.value = name;
      priorityFilter.append(option);
    });
    const nav = byId("group-nav");
    [...new Set(questions.map((q) => q.group))].forEach((group, i) => {
      const button = element("button", "side-link");
      button.type = "button";
      button.dataset.navGroup = group;
      button.append(element("span", "", group), element("span", "", "0"));
      button.addEventListener("click", () => {
        byId("search").value = "";
        byId("answer-filter").value = "all";
        byId("priority-filter").value = "all";
        render();
        byId("group-" + i).scrollIntoView({ behavior: "smooth", block: "start" });
      });
      nav.append(button);
    });
    load();
    render();
    byId("copy-filled").addEventListener("click", () => copyAnswer(exportMarkdown(false)));
    byId("copy-all").addEventListener("click", () => copyAnswer(exportMarkdown(true)));
    byId("show-md").addEventListener("click", () => openDialog(false));
    byId("copy-dialog").addEventListener("click", () => copyAnswer(byId("export-text").value));
    byId("close-dialog").addEventListener("click", () => byId("export-dialog").close());
    byId("select-all").addEventListener("click", () => {
      byId("export-text").focus();
      byId("export-text").select();
    });
    byId("save-md").addEventListener("click", () => {
      const blob = new Blob(["\ufeff", exportMarkdown(true)], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = element("a");
      link.href = url;
      link.download = form.output.filename;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1200);
      notify("Markdownの保存を開始しました");
    });
    byId("reset").addEventListener("click", () => {
      if (!confirm(questions.length + "問の回答・補足・複数選択設定をすべて初期化しますか？")) return;
      for (const q of questions) state[q.id] = initial(q);
      save();
      render();
      notify("回答を初期化しました");
    });
    ["search", "answer-filter", "priority-filter"].forEach((id) => {
      byId(id).addEventListener(id === "search" ? "input" : "change", render);
    });
  }
  setup();
})();
