/* Python Tutor chat page (GitHub Pages version).
   The page shows what the teaching engine returns and passes learner messages
   on. All teaching decisions are made by the engine in js/engine.js, which runs
   in the browser because GitHub Pages cannot run a Python server. */
"use strict";

const engine = PyTutor.createEngine(new PyTutor.FakeProvider(), PyTutor.storage);
const BASE_PATH = location.pathname;
const LEVEL_TEXT = { beginner: "a complete beginner", some_experience: "someone with some programming experience" };
const QUICK = {
  assess: ["I don't know"],
  discuss: ["That makes sense", "I don't get it"],
  complete: [],
};

const $ = (id) => document.getElementById(id);
const state = { session: null, pending: null, busy: false };

function el(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) node.append(kid instanceof Node ? kid : document.createTextNode(kid));
  return node;
}
const requestId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}${Math.random()}`).replace(/[^a-z0-9]/gi, "").slice(0, 32);
const time = (iso) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const day = (iso) => new Date(iso).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

/* ---- safe Markdown: paragraphs, lists, **bold**, *italic*, `code`, ```code blocks``` ---- */
function inline(text) {
  const frag = document.createDocumentFragment();
  for (const part of text.split(/(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*)/g)) {
    if (!part) continue;
    if (/^`.+`$/.test(part)) frag.append(el("code", { text: part.slice(1, -1) }));
    else if (/^\*\*.+\*\*$/.test(part)) frag.append(el("strong", {}, inline(part.slice(2, -2))));
    else if (/^\*.+\*$/.test(part)) frag.append(el("em", {}, inline(part.slice(1, -1))));
    else frag.append(part);
  }
  return frag;
}
function markdown(text) {
  const frag = document.createDocumentFragment();
  for (const chunk of text.split(/(```[a-zA-Z]*\n[\s\S]*?```)/g)) {
    if (!chunk) continue;
    const code = chunk.match(/^```[a-zA-Z]*\n([\s\S]*?)```$/);
    if (code) { frag.append(el("pre", {}, el("code", { text: code[1].replace(/\n$/, "") }))); continue; }
    for (const block of chunk.split(/\n{2,}/)) {
      const lines = block.trim().split("\n").filter(Boolean);
      if (!lines.length) continue;
      if (lines.every((l) => /^\s*[-*]\s+/.test(l))) {
        frag.append(el("ul", {}, lines.map((l) => el("li", {}, inline(l.replace(/^\s*[-*]\s+/, ""))))));
      } else {
        const p = el("p");
        lines.forEach((l, i) => { if (i) p.append(el("br")); p.append(inline(l)); });
        frag.append(p);
      }
    }
  }
  return frag;
}

/* ---- engine calls: errors become { message, retryable } like the Flask version ---- */
async function call(fn) {
  try { return await fn(); }
  catch (err) {
    throw { message: err && err.message ? err.message : "Something went wrong.", retryable: !!(err && err.retryable) };
  }
}

/* ---- start view ---- */
async function showStart() {
  state.session = null;
  $("chatView").hidden = true;
  $("startView").hidden = false;
  window.scrollTo(0, 0);
  history.replaceState(null, "", BASE_PATH);
  $("storageNote").hidden = PyTutor.storage.isPersistent();
  try {
    const concepts = engine.concepts();
    const sessions = engine.sessions();
    $("topicList").replaceChildren(...concepts.map((c) => el("li", { class: c.enabled ? "" : "off" },
      el("span", { class: "topic-title", text: c.title }),
      el("span", { class: "topic-sub", text: c.enabled ? "Available now" : "Planned for a later phase" }),
      c.enabled ? el("button", { type: "button", onclick: (e) => startTopic(c.id, e.currentTarget) }, "Start")
                : el("span", { class: "later", text: "Later" }))));
    $("pastSection").hidden = !sessions.length;
    $("pastList").replaceChildren(...sessions.slice(0, 8).map((s) => el("li", {},
      el("button", { type: "button", onclick: () => openSession(s.id) },
        el("span", { text: s.concept_title }),
        el("span", { class: "meta", text: `${s.stage === "complete" ? "Finished" : "In progress"}, ${day(s.updated_at)}` })))));
  } catch (err) {
    $("topicList").replaceChildren(el("li", {}, el("span", { text: err.message })));
  }
}

async function startTopic(concept, button) {
  button.disabled = true;
  try {
    render(await call(() => engine.start(concept)));
  } catch (err) {
    button.disabled = false;
    button.textContent = "Try again";
    button.title = err.message;
  }
}

async function openSession(id) {
  try { render(await call(() => engine.state(id))); }
  catch (err) { showStart(); }
}

/* ---- chat view ---- */
function render(data) {
  state.session = data.session;
  $("startView").hidden = true;
  $("chatView").hidden = false;
  $("fakeChip").hidden = !data.fake_tutor;
  history.replaceState(null, "", `${BASE_PATH}?session=${data.session.id}`);
  renderTrack(data.session);
  renderLevel(data.session);
  $("messages").replaceChildren(...data.messages.map(renderMessage));
  renderQuick(data.session);
  $("input").placeholder = data.session.stage === "assess" ? "Type your answer..." : "Reply or ask a question...";
  scrollDown();
}

function renderTrack(s) {
  const answered = s.stage === "assess" ? s.questions_asked - 1 : s.questions_total;
  const dots = Array.from({ length: s.questions_total }, (_, i) => el("span", { class: i < answered ? "filled" : "" }));
  const phase = (label, cls, line) => el("div", { class: `phase ${cls}` }, el("div", { class: "bar-line" }, line || []), el("span", { text: label }));
  const assessCls = s.stage === "assess" ? "now dots" : "done";
  const explainCls = s.stage === "discuss" ? "now" : s.stage === "complete" ? "done" : "";
  const doneCls = s.stage === "complete" ? "done" : "";
  $("track").replaceChildren(
    phase(s.stage === "assess" ? `Getting to know you (${Math.min(answered + 1, s.questions_total)} of ${s.questions_total})` : "Getting to know you", assessCls, dots),
    phase("Explanation", explainCls),
    phase("Understood", doneCls),
  );
}

function renderLevel(s) {
  const note = $("levelNote");
  note.hidden = !s.level;
  if (s.level) {
    note.replaceChildren(el("strong", { text: `Explaining for ${LEVEL_TEXT[s.level]}. ` }), s.level_reason || "");
    note.title = `Why: ${s.level_reason || ""}`;
  }
}

function renderMessage(m) {
  const body = el("div", { class: "body" });
  if (m.role === "learner") body.textContent = m.content;
  else body.append(markdown(m.content));
  return el("div", { class: `msg ${m.role}` }, body, m.role === "app" ? null : el("span", { class: "stamp", text: time(m.created_at) }));
}

function renderQuick(s) {
  $("quick").replaceChildren(...(QUICK[s.stage] || []).map((text) =>
    el("button", { type: "button", onclick: () => send(text) }, text)));
}

function scrollDown() {
  requestAnimationFrame(() => window.scrollTo({ top: document.body.scrollHeight, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }));
}

/* ---- sending: the text stays in the box until the server confirms ---- */
function setBusy(busy) {
  state.busy = busy;
  $("sendBtn").disabled = busy;
  document.querySelectorAll("#quick button").forEach((b) => { b.disabled = busy; });
}

async function send(text, retry) {
  text = (text || "").trim();
  if (!text || state.busy || !state.session) return;
  const request = retry || { text, id: requestId(), session: state.session.id };
  state.pending = request;
  $("failed").hidden = true;
  setBusy(true);
  const bubble = el("div", { class: "msg learner" }, el("div", { class: "body", text: request.text }));
  const typing = el("div", { class: "msg tutor" }, el("div", { class: "typing", "aria-label": "Tutor is typing" }, el("span"), el("span"), el("span")));
  $("messages").append(bubble, typing);
  scrollDown();
  try {
    const data = await call(() => engine.send(request.session, request.text));
    if ($("input").value.trim() === request.text) { $("input").value = ""; autosize(); }
    state.pending = null;
    render(data);
  } catch (err) {
    bubble.remove();
    typing.remove();
    if (!$("input").value.trim()) { $("input").value = request.text; autosize(); }
    alertFailed(err.message, err.retryable ? () => send(request.text, request) : null);
  } finally {
    setBusy(false);
  }
}

function alertFailed(message, retry) {
  $("failedText").textContent = message;
  $("retryBtn").hidden = !retry;
  $("retryBtn").onclick = retry;
  $("failed").hidden = false;
}

function autosize() {
  const box = $("input");
  box.style.height = "auto";
  box.style.height = Math.min(box.scrollHeight, 160) + "px";
}

/* ---- wiring ---- */
$("input").addEventListener("input", autosize);
$("input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("composer").requestSubmit(); }
});
$("composer").addEventListener("submit", (e) => { e.preventDefault(); send($("input").value); });
$("homeBtn").addEventListener("click", () => {
  if (state.busy) return;
  if ($("input").value.trim() && !confirm("You have an unsent message. Leave it and go back to topics?")) return;
  $("input").value = "";
  showStart();
});

const resume = new URLSearchParams(location.search).get("session");
if (resume) openSession(resume); else showStart();
