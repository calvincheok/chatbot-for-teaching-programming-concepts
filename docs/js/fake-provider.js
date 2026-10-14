/* Fake tutor for building and testing without API costs. Same logic as
   teaching/providers/fake.py; the pre-written content comes from content.js.

   It returns pre-written replies and uses simple keyword rules where a real
   model would use judgement. It reads the same system prompt a real model
   would get (the topic, the learner's level, which question to ask). It says
   nothing about how good a real model's teaching will be. */
"use strict";
var PyTutor = window.PyTutor || (window.PyTutor = {});

PyTutor.FakeProvider = (function () {
  const F = PyTutor.FAKE;
  const RX = {};
  for (const [name, source] of Object.entries(F.PATTERNS)) RX[name] = new RegExp(source);
  const fail = (message) => { throw new PyTutor.ProviderError(message); };

  function last(history, role) {
    for (let i = history.length - 1; i >= 0; i--) if (history[i].role === role) return history[i].content;
    return "";
  }
  function number(pattern, text) {
    const match = text.match(pattern);
    if (!match) fail("The fake tutor could not read the prompt.");
    return parseInt(match[1], 10);
  }
  function topicOf(systemPrompt) {
    for (const [id, concept] of Object.entries(PyTutor.CONCEPTS)) {
      if (systemPrompt.includes(`one concept: ${concept.title} (`) && F.TOPICS[id]) return F.TOPICS[id];
    }
    return fail("The fake tutor has no content for this topic.");
  }

  function reply(task, systemPrompt, history) {
    const topic = topicOf(systemPrompt);
    const text = last(history, "user").toLowerCase();

    if (task === "diagnostic_question") {
      const n = number(/question number (\d+)/, systemPrompt);
      return topic.diagnostic[(n - 1) % topic.diagnostic.length];
    }

    if (task === "classify_level") {
      const answers = history.filter((m) => m.role === "user").map((m) => m.content.toLowerCase()).slice(-3);
      let score = 0;
      const gaps = [];
      if (answers.length && RX.experience.test(answers[0]) && !RX.no_experience.test(answers[0])) score += 1;
      topic.classify.forEach((rule, i) => {
        if (answers.length > i + 1 && new RegExp(rule.pattern).test(answers[i + 1])) score += 1;
        else gaps.push(rule.gap);
      });
      const level = score >= 2 ? "some_experience" : "beginner";
      const reason = level === "some_experience" ? "They showed some experience and understanding." : "They are new to these ideas.";
      return JSON.stringify({ level, reason, gaps });
    }

    const level = systemPrompt.includes("some programming experience") ? "some_experience" : "beginner";
    const explanations = topic.explain[level];
    if (task === "explain") return explanations[0];
    if (task === "reexplain") return explanations[number(/attempt (\d+)/, systemPrompt) % explanations.length];

    if (task === "respond") {
      if (text.includes("?")) {
        for (const [keywords, answer] of topic.faq) {
          if (keywords.some((k) => text.includes(k))) return JSON.stringify({ intent: "question", reply: answer + "\n\nAnything else you'd like to ask?" });
        }
        return JSON.stringify({ intent: "question", reply: F.UNKNOWN_QUESTION });
      }
      if (RX.confused.test(text)) return JSON.stringify({ intent: "confused", reply: "No problem, let me explain it another way." });
      if (RX.understood.test(text)) return JSON.stringify({ intent: "understood", reply: topic.summary });
      return JSON.stringify({ intent: "unclear", reply: "I'm not sure what you mean. Does the explanation make sense, or is there a part you'd like me to explain again?" });
    }

    if (task === "check_question") {
      const n = number(/check question (\d+)/, systemPrompt);
      return topic.checks[(n - 1) % topic.checks.length].question;
    }

    if (task === "grade_check") {
      const asked = last(history, "assistant");
      for (const check of topic.checks) {
        if (asked.includes(check.question)) {
          const correct = new RegExp(check.answer).test(text);
          return JSON.stringify({ correct, reply: correct ? check.right : check.wrong });
        }
      }
      return fail("The fake tutor could not find the check question it asked.");
    }

    return fail(`The fake provider has no reply for task '${task}'.`);
  }

  return class FakeProvider {
    constructor(options) {
      options = options || {};
      this.name = "fake";
      this.isFake = true;
      this.delayMs = options.delayMs != null ? options.delayMs : 500;   // feels like a real reply
      // Tests use these to prove failures are handled, not hidden.
      this.failTasks = new Set(options.failTasks || []);
      this.brokenJsonTasks = new Set(options.brokenJsonTasks || []);
    }
    generate(task, systemPrompt, history) {
      return new Promise((resolve, reject) => {
        setTimeout(() => {
          try {
            if (this.failTasks.has(task)) throw new PyTutor.ProviderError(`Fake failure in ${task}.`);
            if (this.brokenJsonTasks.has(task)) return resolve("Sure! Here is my answer: level beginner");
            resolve(reply(task, systemPrompt, history));
          } catch (err) { reject(err); }
        }, this.delayMs);
      });
    }
  };
})();
