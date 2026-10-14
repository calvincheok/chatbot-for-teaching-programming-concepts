/* Fake tutor for building and testing without API costs.

   It returns pre-written replies and uses simple keyword rules where a real
   model would use judgement. It reads the same system prompt a real model
   would get (for example to see the learner's level). It says nothing about
   how good a real model's teaching will be.

   The texts below are the same as teaching/providers/fake.py in the Flask version. */
"use strict";
var PyTutor = window.PyTutor || (window.PyTutor = {});

PyTutor.FakeProvider = (function () {
  const CONTENT = {
  "DIAGNOSTIC": [
    "Before we start, have you written any code before, in Python or any other language? Tell me a little about it.",
    "In your own words, what do you think a **variable** is in programming?",
    "Quick one: what kind of value do you think `3.5` is? And what about `\"hello\"`?"
  ],
  "EXPLAIN": {
    "beginner": [
      "Think of a **variable** as a labelled box. The label is the variable's name, and whatever you put inside is its value. In Python, `=` means \"put this into the box\":\n\n```python\nage = 19\nname = \"Aina\"\n```\n\nValues come in different **types**, like how a kitchen has liquids, fruit and spices:\n\n- `int` is a whole number, like counting apples: `19`\n- `float` is a number with a decimal point, like a height: `1.62`\n- `str` (string) is text inside quotes, like a name tag: `\"Aina\"`\n- `bool` is a yes-or-no switch: `True` or `False`\n\nDoes that make sense so far, or is there a part you'd like me to go over?",
      "Let me try another way. Imagine your phone's contacts list. Each contact has a **name** (\"Mum\") and a **number** stored under it. A variable works the same way: the name points to a value.\n\n```python\nscore = 10\n```\n\nHere `score` is the contact name and `10` is what's saved under it. If you later write `score = 15`, it's like editing the contact: the old number is replaced.\n\nThe type tells Python what kind of value it is: `10` is an `int` (whole number), `10.5` is a `float` (decimal), and `\"10\"` in quotes is a `str` (text), even though it looks like a number.\n\nIs this clearer?"
    ],
    "some_experience": [
      "Since you've coded before, let's be precise. In Python, `=` **binds a name to a value**. Names have no fixed type; values do. So the same name can later point to a different type:\n\n```python\ncount = 3        # int\ncount = \"three\"  # now a str\n```\n\nThe four basic types are `int`, `float`, `str` and `bool`. Two common mistakes:\n\n- `\"19\"` and `19` are different: the first is a `str`. Anything from `input()` is a `str`.\n- `/` always gives a `float`, so `10 / 2` is `5.0`.\n\nUse `type()` to check a value and `int()`, `float()`, `str()` to convert:\n\n```python\nage = int(\"19\")\nprint(type(age))   # <class 'int'>\n```\n\nDoes that all make sense, or do you have a question?",
      "Another angle: think about what Python actually stores. Every value is an object with a type; a variable is just a reference to it.\n\n```python\nx = 5\ny = x      # y refers to the same value 5\nx = 6      # x now refers to 6; y is still 5\nprint(x, y)  # 6 5\n```\n\nTypes matter when you combine values: `\"5\" + \"5\"` gives `\"55\"` (joining text), while `5 + 5` gives `10`. That's why converting with `int()` before doing maths on user input is important.\n\nDoes this way of looking at it help?"
    ]
  },
  "FAQ": [
    [
      [
        "float",
        "decimal"
      ],
      "A `float` is a number with a decimal point, like `2.5` or even `3.0`. Dividing with `/` always gives a float, so `10 / 2` is `5.0`."
    ],
    [
      [
        "string",
        "str",
        "quote",
        "text"
      ],
      "A string (`str`) is text inside quotes. `'hi'` and `\"hi\"` are the same. Without quotes, Python reads the word as a variable name instead."
    ],
    [
      [
        "bool",
        "true",
        "false"
      ],
      "A `bool` is either `True` or `False`, with a capital first letter and no quotes. You'll use them a lot with `if` statements later."
    ],
    [
      [
        "name",
        "naming",
        "call"
      ],
      "Variable names can use letters, digits and underscores, but can't start with a digit or contain spaces. Python style is lowercase with underscores, like `student_name`."
    ],
    [
      [
        "convert",
        "int(",
        "change"
      ],
      "Use `int()`, `float()` or `str()` to convert. For example, `int(\"19\")` gives the number `19`. Converting text that isn't a number, like `int(\"abc\")`, causes an error."
    ],
    [
      [
        "type(",
        "type",
        "check"
      ],
      "`type()` tells you a value's type. For example, `print(type(3.5))` shows `<class 'float'>`."
    ]
  ]
};

  const UNDERSTOOD = /\b(yes|yep|yeah|ok|okay|got it|makes sense|i understand|understood|clear|sure)\b/;
  const CONFUSED = /\b(no|not really|confus\w*|(don'?t|do not|didn'?t|doesn'?t)\s+(really\s+|quite\s+)?(get|understand|make sense)|lost|huh)\b|不懂|不明白/;
  const EXPERIENCE = /\b(yes|python|java|javascript|c\+\+|html|scratch|coded|coding|course|project|programm\w*)\b/;
  const NO_EXPERIENCE = /\b(no|never|none|nope|not really|first time)\b/;
  const VARIABLE_IDEA = /\b(store|stores|hold|holds|value|name|label|box|container|memory|data)\b/;
  const TYPE_IDEA = /\b(float|decimal|str|string|text)\b/;

  function lastUser(history) {
    for (let i = history.length - 1; i >= 0; i--) if (history[i].role === "user") return history[i].content.toLowerCase();
    return "";
  }

  function reply(task, systemPrompt, history) {
    if (task === "diagnostic_question") {
      const number = Number(systemPrompt.match(/question number (\d+)/)[1]);
      return CONTENT.DIAGNOSTIC[(number - 1) % CONTENT.DIAGNOSTIC.length];
    }
    if (task === "classify_level") {
      const answers = history.filter((m) => m.role === "user").map((m) => m.content.toLowerCase());
      let score = 0;
      const gaps = [];
      if (answers[0] && EXPERIENCE.test(answers[0]) && !NO_EXPERIENCE.test(answers[0])) score += 1;
      if (answers[1] && VARIABLE_IDEA.test(answers[1])) score += 1; else gaps.push("what a variable is");
      if (answers[2] && TYPE_IDEA.test(answers[2])) score += 1; else gaps.push("the basic data types");
      const level = score >= 2 ? "some_experience" : "beginner";
      const reason = level === "some_experience" ? "They showed some experience and understanding." : "They are new to these ideas.";
      return JSON.stringify({ level, reason, gaps });
    }
    const level = systemPrompt.includes("some programming experience") ? "some_experience" : "beginner";
    if (task === "explain") return CONTENT.EXPLAIN[level][0];
    if (task === "reexplain") {
      const attempt = Number(systemPrompt.match(/attempt (\d+)/)[1]);
      return CONTENT.EXPLAIN[level][attempt % CONTENT.EXPLAIN[level].length];
    }
    if (task === "respond") {
      const text = lastUser(history);
      if (text.includes("?")) {
        for (const [keywords, answer] of CONTENT.FAQ) {
          if (keywords.some((k) => text.includes(k))) return JSON.stringify({ intent: "question", reply: answer + "\n\nAnything else you'd like to ask?" });
        }
        return JSON.stringify({ intent: "question", reply: "*(Fake tutor: the real model will answer this question. The fake one only knows a few common questions about variables and types.)*" });
      }
      if (CONFUSED.test(text)) return JSON.stringify({ intent: "confused", reply: "No problem, let me explain it another way." });
      if (UNDERSTOOD.test(text)) return JSON.stringify({ intent: "understood", reply: "Great. The key idea: a variable is a name that holds a value, and every value has a type such as `int`, `float`, `str` or `bool`." });
      return JSON.stringify({ intent: "unclear", reply: "I'm not sure what you mean. Does the explanation make sense, or is there a part you'd like me to explain again?" });
    }
    throw new PyTutor.ProviderError(`The fake provider has no reply for task "${task}".`);
  }

  // Same interface a real LLM provider would have: generate(task, systemPrompt, history) -> Promise<string>.
  return class FakeProvider {
    constructor(options) {
      this.name = "fake";
      this.isFake = true;
      this.delayMs = options && options.delayMs != null ? options.delayMs : 500;   // feels like a real reply
      this.failTasks = new Set((options && options.failTasks) || []);
      this.brokenJsonTasks = new Set((options && options.brokenJsonTasks) || []);   // for testing reply checks
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
