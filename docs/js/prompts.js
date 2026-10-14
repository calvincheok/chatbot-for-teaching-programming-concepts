/* Builds the system prompt for each task, like teaching/prompts.py.
   The prompt texts themselves come from content.js, which build_pages.py
   generates from the Python file, so both versions send identical prompts. */
"use strict";
var PyTutor = window.PyTutor || (window.PyTutor = {});

PyTutor.prompts = (function () {
  const P = PyTutor.PROMPTS;

  // Fills {name} placeholders. Placeholders not in `fields` (like the JSON shapes) are left alone.
  function fill(template, fields) {
    return template.replace(/\{(\w+)\}/g, (match, key) => (key in fields ? String(fields[key]) : match));
  }

  function systemPrompt(task, concept, fields) {
    const rules = fill(P.BASE_RULES, { concept_title: concept.title, subtopics: concept.subtopics });
    return rules + "\n\n" + fill(P.TASKS[task], fields || {});
  }

  // What diagnostic question `number` (1-based) should ask about.
  function diagnosticFocus(concept, number) {
    const focus = [P.EXPERIENCE_FOCUS].concat(concept.focus || []);
    return focus[(number - 1) % focus.length];
  }

  return { LEVELS: P.LEVELS, STRATEGIES: P.STRATEGIES, TASKS: P.TASKS, systemPrompt, diagnosticFocus };
})();
