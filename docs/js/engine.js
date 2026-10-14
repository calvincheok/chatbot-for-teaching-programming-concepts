/* The conversational teaching engine (proposal Objective 1, Section 4.2).
   Browser version of teaching/engine.py, so it can run on GitHub Pages.

   The app, not the model, controls the order of teaching:
     assess    ask diagnostic questions one at a time (3)
               -> the model classifies the learner's level from the answers
     discuss   explain at that level, then read each learner reply:
                 understood -> confirm, explanation complete
                 confused   -> explain again with a different approach
                 question   -> answer it, stay here
                 unclear    -> ask what they mean, stay here
     complete  the learner said it makes sense; they can still ask questions

   Each turn builds a structured system prompt (prompts.js) and sends it with
   the recent conversation to the provider. JSON replies are checked before use.
   If anything fails, nothing is saved and the learner can send again. */
"use strict";
var PyTutor = window.PyTutor || (window.PyTutor = {});

PyTutor.ProviderError = class ProviderError extends Error {};
PyTutor.EngineError = class EngineError extends Error {
  constructor(message, retryable) { super(message); this.retryable = !!retryable; }
};

PyTutor.createEngine = function (provider, storage) {
  const { prompts, CONCEPTS, ProviderError, EngineError } = PyTutor;
  const DIAGNOSTIC_QUESTIONS = 3;
  const HISTORY_LIMIT = 12;
  const MAX_MESSAGE_LENGTH = 1000;
  const WELCOME = "Hi! I'm your Python tutor. Today we'll learn about **{title}**. " +
    "First I'll ask you a few quick questions, so I can explain things at the right level for you. " +
    "There are no wrong answers, and \"I don't know\" is fine.";

  const now = () => new Date().toISOString();
  const newId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}${Math.random()}`).replace(/[^a-z0-9]/gi, "").slice(0, 32);

  function parseJsonReply(text, required) {
    const cleaned = String(text).trim().replace(/^```(?:json)?\s*|\s*```$/g, "");
    let data;
    try { data = JSON.parse(cleaned); } catch { throw new ProviderError("The tutor's reply was not in the expected format."); }
    if (!data || typeof data !== "object" || Array.isArray(data)) throw new ProviderError("The tutor's reply was not in the expected format.");
    for (const [field, rule] of Object.entries(required)) {
      const value = data[field];
      if (Array.isArray(rule)) {
        if (!rule.includes(value)) throw new ProviderError(`The tutor's reply had an invalid '${field}'.`);
      } else if (typeof value !== rule || (rule === "string" && !value.trim())) {
        throw new ProviderError(`The tutor's reply was missing '${field}'.`);
      }
    }
    return data;
  }

  function checkText(text) {
    if (typeof text !== "string" || !text.trim()) throw new ProviderError("The tutor returned an empty reply.");
    if (text.length > 4000) throw new ProviderError("The tutor's reply was too long.");
    return text.trim();
  }

  // One provider call: build the prompt, call, log the call on the session.
  async function ask(session, task, concept, history, fields) {
    const system = prompts.systemPrompt(task, concept, fields);
    const started = performance.now();
    const log = { task, provider: provider.name, ok: true, error: null, created_at: now() };
    try {
      return await provider.generate(task, system, history);
    } catch (err) {
      log.ok = false;
      log.error = String(err && err.message || err);
      throw new EngineError(`The tutor couldn't reply (${log.error}). Your message is kept, so you can send it again.`, true);
    } finally {
      log.duration_ms = Math.round(performance.now() - started);
      if (session) session._pendingCalls.push(log);
    }
  }

  function checked(fn) {
    try { return fn(); }
    catch (err) {
      if (err instanceof ProviderError) throw new EngineError(`${err.message} Please send your message again.`, true);
      throw err;
    }
  }

  function historyOf(session) {
    return session.messages.filter((m) => m.role !== "app").slice(-HISTORY_LIMIT)
      .map((m) => ({ role: m.role === "learner" ? "user" : "assistant", content: m.content }));
  }

  // Work on a copy; only a fully successful turn is saved.
  function draft(session) {
    const copy = JSON.parse(JSON.stringify(session));
    copy._pendingCalls = [];
    return copy;
  }
  function add(s, role, content, task) { s.messages.push({ id: s.messages.length + 1, role, content, task: task || null, created_at: now() }); }
  function event(s, kind, detail) { s.events.push({ kind, detail: detail || {}, created_at: now() }); }
  function commit(s) {
    s.llm_calls.push(...s._pendingCalls);
    delete s._pendingCalls;
    s.updated_at = now();
    storage.save(s);
  }
  function logFailure(s) {
    // Failed calls are still recorded for usage measurement; the turn itself is not saved.
    const stored = storage.get(s.id);
    if (stored && s._pendingCalls.length) { stored.llm_calls.push(...s._pendingCalls); storage.save(stored); }
  }

  function load(id) {
    const s = storage.get(id);
    if (!s) throw new EngineError("That session was not found in this browser.", false);
    return s;
  }

  // ---- public actions -------------------------------------------------
  async function start(conceptId) {
    const concept = CONCEPTS[conceptId];
    if (!concept || !concept.enabled) throw new EngineError("That topic isn't available yet.", false);
    const ts = now();
    const s = draft({
      id: newId(), concept: conceptId, stage: "assess", level: null, level_reason: null, gaps: [],
      questions_asked: 1, reexplains: 0, created_at: ts, updated_at: ts, messages: [], events: [], llm_calls: [],
    });
    const welcome = WELCOME.replace("{title}", concept.title);
    const raw = await ask(s, "diagnostic_question", concept, [{ role: "assistant", content: welcome }],
      { number: 1, total: DIAGNOSTIC_QUESTIONS, focus: prompts.DIAGNOSTIC_FOCUS[0] });
    const first = checked(() => checkText(raw));
    add(s, "tutor", welcome, "welcome");
    add(s, "tutor", first, "diagnostic_question");
    event(s, "session_started", { concept: conceptId });
    commit(s);
    return state(s.id);
  }

  async function send(sessionId, text) {
    text = (text || "").trim();
    if (!text) throw new EngineError("Type a message first.", false);
    if (text.length > MAX_MESSAGE_LENGTH) throw new EngineError(`Please keep messages under ${MAX_MESSAGE_LENGTH} characters.`, false);
    const s = draft(load(sessionId));
    const concept = CONCEPTS[s.concept];
    const history = historyOf(s).concat([{ role: "user", content: text }]);
    try {
      if (s.stage === "assess") await assessTurn(s, concept, history, text);
      else await discussTurn(s, concept, history, text);
    } catch (err) {
      logFailure(s);
      throw err;
    }
    commit(s);
    return state(s.id);
  }

  // ---- assess: diagnostic questions, then level -------------------------
  async function assessTurn(s, concept, history, text) {
    const asked = s.questions_asked;
    if (asked < DIAGNOSTIC_QUESTIONS) {
      const raw = await ask(s, "diagnostic_question", concept, history, {
        number: asked + 1, total: DIAGNOSTIC_QUESTIONS, focus: prompts.DIAGNOSTIC_FOCUS[asked % prompts.DIAGNOSTIC_FOCUS.length],
      });
      const question = checked(() => checkText(raw));
      add(s, "learner", text);
      add(s, "tutor", question, "diagnostic_question");
      s.questions_asked = asked + 1;
      return;
    }
    // All diagnostic questions answered: classify, then explain at that level.
    const rawLevel = await ask(s, "classify_level", concept, history, {});
    const result = checked(() => parseJsonReply(rawLevel, { level: Object.keys(prompts.LEVELS), reason: "string" }));
    const gaps = Array.isArray(result.gaps) ? result.gaps.filter((g) => typeof g === "string").slice(0, 5) : [];
    const level = result.level;
    const rawExplain = await ask(s, "explain", concept, history, {
      level_description: prompts.LEVELS[level], strategy: prompts.STRATEGIES[level], gaps: gaps.join(", ") || "nothing specific",
    });
    const explanation = checked(() => checkText(rawExplain));
    add(s, "learner", text);
    add(s, "app", `Thanks! I'll explain this for ${prompts.LEVELS[level]}.`, "level_chosen");
    add(s, "tutor", explanation, "explain");
    Object.assign(s, { stage: "discuss", level, level_reason: result.reason, gaps });
    event(s, "level_chosen", { level, reason: result.reason, gaps });
  }

  // ---- discuss: respond, re-explain when confused ------------------------
  async function discussTurn(s, concept, history, text) {
    const level = s.level;
    const raw = await ask(s, "respond", concept, history, { level_description: prompts.LEVELS[level] });
    const result = checked(() => parseJsonReply(raw, { intent: ["understood", "confused", "question", "unclear"], reply: "string" }));
    const reply = checked(() => checkText(result.reply));
    let reexplanation = null;
    if (result.intent === "confused") {
      const attempt = s.reexplains + 1;
      const rawAgain = await ask(s, "reexplain", concept, history.concat([{ role: "assistant", content: reply }]), {
        level_description: prompts.LEVELS[level], strategy: prompts.STRATEGIES[level], attempt,
      });
      reexplanation = checked(() => checkText(rawAgain));
    }
    add(s, "learner", text);
    add(s, "tutor", reply, `respond:${result.intent}`);
    if (reexplanation) {
      add(s, "tutor", reexplanation, "reexplain");
      s.reexplains += 1;
      s.stage = "discuss";
      event(s, "reexplained", { attempt: s.reexplains });
    }
    if (result.intent === "understood" && s.stage !== "complete") {
      s.stage = "complete";
      add(s, "app", "You've finished this explanation. You can keep asking questions here. " +
        "(Practice exercises for this topic are planned for the next phase of the project.)", "complete");
      event(s, "understood", { reexplains: s.reexplains });
    }
  }

  // ---- reading (same shape as the Flask API) ------------------------------
  function state(sessionId) {
    const s = load(sessionId);
    return {
      session: {
        id: s.id, concept: s.concept, concept_title: CONCEPTS[s.concept].title, stage: s.stage, level: s.level,
        level_reason: s.level_reason, gaps: s.gaps, questions_asked: s.questions_asked, questions_total: DIAGNOSTIC_QUESTIONS,
        reexplains: s.reexplains, created_at: s.created_at, updated_at: s.updated_at,
      },
      messages: s.messages.map((m) => ({ ...m })),
      fake_tutor: !!provider.isFake,
    };
  }

  function sessions() {
    return storage.all()
      .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
      .map((s) => ({ id: s.id, concept: s.concept, concept_title: CONCEPTS[s.concept].title, stage: s.stage, level: s.level, created_at: s.created_at, updated_at: s.updated_at }));
  }

  function concepts() {
    return Object.entries(CONCEPTS).map(([id, c]) => ({ id, title: c.title, enabled: c.enabled }));
  }

  return { start, send, state, sessions, concepts, parseJsonReply };
};
