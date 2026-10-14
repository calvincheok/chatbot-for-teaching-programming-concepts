/* Tests for the GitHub Pages version (docs/js), the same checks as test_engine.py.
   Run: node tests/test_static_site.js   (Node 18 or newer, no packages needed) */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert/strict");

const DOCS = path.join(__dirname, "..", "docs", "js");
const FILES = ["concepts.js", "prompts.js", "fake-provider.js", "storage.js", "engine.js"];

// A fresh "browser" for each test: its own window and localStorage.
function browser() {
  const store = new Map();
  const ctx = {
    console, setTimeout, crypto: globalThis.crypto, performance: globalThis.performance,
    localStorage: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, String(v)),
    },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  for (const f of FILES) vm.runInContext(fs.readFileSync(path.join(DOCS, f), "utf8"), ctx, { filename: f });
  const provider = new ctx.PyTutor.FakeProvider({ delayMs: 0 });
  const engine = ctx.PyTutor.createEngine(provider, ctx.PyTutor.storage);
  return { P: ctx.PyTutor, provider, engine, store };
}

async function session() {
  const b = browser();
  const first = await b.engine.start("variables");
  b.sid = first.session.id;
  b.say = (text) => b.engine.send(b.sid, text);
  b.first = first;
  return b;
}
async function beginner() {
  const b = await session();
  await b.say("No, never");
  await b.say("I don't know");
  b.last = await b.say("not sure");
  return b;
}
const lastMsg = (state) => state.messages[state.messages.length - 1];

const tests = {
  async "starts with welcome and first diagnostic question"() {
    const { first } = await session();
    assert.equal(first.messages.map((m) => m.task).join(","), "welcome,diagnostic_question");
    assert.equal(first.session.stage, "assess");
  },
  async "asks three questions one at a time before teaching"() {
    const b = await session();
    let s = await b.say("No, never");
    assert.equal(lastMsg(s).task, "diagnostic_question");
    s = await b.say("a box?");
    assert.equal(s.session.questions_asked, 3);
    assert.equal(s.session.stage, "assess");
    assert.ok(!s.messages.some((m) => m.task === "explain"));
  },
  async "beginner gets analogy explanation"() {
    const { last } = await beginner();
    assert.equal(last.session.level, "beginner");
    assert.equal(last.session.stage, "discuss");
    assert.match(lastMsg(last).content, /labelled box/);
  },
  async "experienced learner gets technical explanation"() {
    const b = await session();
    await b.say("Yes, I did a Java course");
    await b.say("A name that stores a value");
    const s = await b.say("3.5 is a float and hello is a string");
    assert.equal(s.session.level, "some_experience");
    assert.match(lastMsg(s).content, /binds a name to a value/);
  },
  async "confused learner gets a different explanation"() {
    const b = await beginner();
    const s = await b.say("I don't understand");
    assert.equal(lastMsg(s).task, "reexplain");
    assert.notEqual(lastMsg(s).content, lastMsg(b.last).content);
    assert.equal(s.session.reexplains, 1);
  },
  async "confusion phrasings are recognised"() {
    for (const text of ["I don't really get it", "it doesn't make sense", "I'm confused", "不懂"]) {
      const b = await beginner();
      assert.equal(lastMsg(await b.say(text)).task, "reexplain", text);
    }
  },
  async "question is answered without changing stage"() {
    const b = await beginner();
    const s = await b.say("What is a float?");
    assert.equal(lastMsg(s).task, "respond:question");
    assert.match(lastMsg(s).content, /decimal point/);
    assert.equal(s.session.stage, "discuss");
  },
  async "unclear reply asks for clarification"() {
    const b = await beginner();
    assert.equal(lastMsg(await b.say("hmm the box thing")).task, "respond:unclear");
  },
  async "understood completes the explanation"() {
    const b = await beginner();
    let s = await b.say("Yes, that makes sense");
    assert.equal(s.session.stage, "complete");
    assert.equal(lastMsg(s).task, "complete");
    s = await b.say("What is a bool?");
    assert.equal(lastMsg(s).task, "respond:question");
  },
  async "disabled topic refused"() {
    const b = browser();
    await assert.rejects(b.engine.start("oop"), (e) => e instanceof b.P.EngineError && !e.retryable);
  },
  async "provider failure saves nothing and resend works"() {
    const b = await session();
    await b.say("No, never");
    const before = b.engine.state(b.sid).messages.length;
    b.provider.failTasks = new Set(["diagnostic_question"]);
    await assert.rejects(b.say("I don't know"), (e) => e.retryable === true);
    assert.equal(b.engine.state(b.sid).messages.length, before);
    b.provider.failTasks = new Set();
    const s = await b.say("I don't know");
    assert.equal(s.messages.length, before + 2);
  },
  async "broken JSON from the model is rejected"() {
    const b = await session();
    await b.say("No");
    await b.say("no idea");
    b.provider.brokenJsonTasks = new Set(["classify_level"]);
    await assert.rejects(b.say("not sure"), (e) => /format/.test(e.message) && e.retryable);
    assert.equal(b.engine.state(b.sid).session.stage, "assess");
  },
  async "empty and too long messages are refused"() {
    const b = await session();
    await assert.rejects(b.say("   "), /Type a message/);
    await assert.rejects(b.say("x".repeat(1001)), /under 1000/);
  },
  async "sessions are saved in the browser and listed"() {
    const b = await beginner();
    const saved = JSON.parse(b.store.get("pytutor.sessions.v1"));
    assert.ok(saved[b.sid]);
    assert.equal(b.engine.sessions()[0].id, b.sid);
    assert.ok(saved[b.sid].llm_calls.length >= 5);   // every tutor call is logged
  },
  async "sessions from another browser are not visible"() {
    const b = await session();
    const other = browser();
    assert.throws(() => other.engine.state(b.sid), /not found/);
  },
  async "level decision is recorded"() {
    const { last } = await beginner();
    assert.ok(last.session.level_reason);
    assert.ok(last.session.gaps.includes("what a variable is"));
  },
  async "every task prompt includes the tutor rules"() {
    const { P } = browser();
    const fields = { number: 1, total: 3, focus: "x", level_description: "y", strategy: "z", gaps: "g", attempt: 1 };
    for (const task of Object.keys(P.prompts.TASKS)) {
      const text = P.prompts.systemPrompt(task, P.CONCEPTS.variables, fields);
      assert.match(text, /Act as a teacher/);
      assert.match(text, /Variables and Data Types/);
      assert.doesNotMatch(text, /\{(number|total|focus|level_description|strategy|gaps|attempt)\}/);
    }
  },
  async "explain prompt uses level strategy"() {
    const { P } = browser();
    const text = P.prompts.systemPrompt("explain", P.CONCEPTS.variables, {
      level_description: P.prompts.LEVELS.beginner, strategy: P.prompts.STRATEGIES.beginner, gaps: "what a variable is",
    });
    assert.match(text, /everyday analogy/);
    assert.match(text, /what a variable is/);
  },
  async "JSON parser"() {
    const { P, engine } = browser();
    assert.equal(engine.parseJsonReply('```json\n{"level": "beginner", "reason": "r"}\n```', { level: ["beginner"], reason: "string" }).level, "beginner");
    assert.throws(() => engine.parseJsonReply('{"level": "expert", "reason": "r"}', { level: ["beginner"], reason: "string" }), P.ProviderError);
    assert.throws(() => engine.parseJsonReply("not json", { level: ["beginner"] }), P.ProviderError);
  },
};

(async () => {
  let failed = 0;
  for (const [name, fn] of Object.entries(tests)) {
    try { await fn(); console.log(`ok    ${name}`); }
    catch (err) { failed++; console.log(`FAIL  ${name}\n      ${err.message}`); }
  }
  const total = Object.keys(tests).length;
  console.log(`\n${total - failed}/${total} passed`);
  process.exit(failed ? 1 : 0);
})();
