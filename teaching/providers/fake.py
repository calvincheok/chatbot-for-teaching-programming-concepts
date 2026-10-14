"""Fake LLM provider for building and testing without API costs.

It returns pre-written replies and uses simple keyword rules where a real
model would use judgement. It reads the same system prompt a real model
would get (for example to see the learner's level), so it also checks that
the prompts carry the right information. It says nothing about how good the
real model's teaching will be.
"""

from __future__ import annotations

import json
import re

from .base import LLMProvider, ProviderError

DIAGNOSTIC = [
    "Before we start, have you written any code before, in Python or any other language? Tell me a little about it.",
    "In your own words, what do you think a **variable** is in programming?",
    "Quick one: what kind of value do you think `3.5` is? And what about `\"hello\"`?",
]

EXPLAIN = {
    "beginner": [
        """Think of a **variable** as a labelled box. The label is the variable's name, and whatever you put inside is its value. In Python, `=` means "put this into the box":

```python
age = 19
name = "Aina"
```

Values come in different **types**, like how a kitchen has liquids, fruit and spices:

- `int` is a whole number, like counting apples: `19`
- `float` is a number with a decimal point, like a height: `1.62`
- `str` (string) is text inside quotes, like a name tag: `"Aina"`
- `bool` is a yes-or-no switch: `True` or `False`

Does that make sense so far, or is there a part you'd like me to go over?""",
        """Let me try another way. Imagine your phone's contacts list. Each contact has a **name** ("Mum") and a **number** stored under it. A variable works the same way: the name points to a value.

```python
score = 10
```

Here `score` is the contact name and `10` is what's saved under it. If you later write `score = 15`, it's like editing the contact: the old number is replaced.

The type tells Python what kind of value it is: `10` is an `int` (whole number), `10.5` is a `float` (decimal), and `"10"` in quotes is a `str` (text), even though it looks like a number.

Is this clearer?""",
    ],
    "some_experience": [
        """Since you've coded before, let's be precise. In Python, `=` **binds a name to a value**. Names have no fixed type; values do. So the same name can later point to a different type:

```python
count = 3        # int
count = "three"  # now a str
```

The four basic types are `int`, `float`, `str` and `bool`. Two common mistakes:

- `"19"` and `19` are different: the first is a `str`. Anything from `input()` is a `str`.
- `/` always gives a `float`, so `10 / 2` is `5.0`.

Use `type()` to check a value and `int()`, `float()`, `str()` to convert:

```python
age = int("19")
print(type(age))   # <class 'int'>
```

Does that all make sense, or do you have a question?""",
        """Another angle: think about what Python actually stores. Every value is an object with a type; a variable is just a reference to it.

```python
x = 5
y = x      # y refers to the same value 5
x = 6      # x now refers to 6; y is still 5
print(x, y)  # 6 5
```

Types matter when you combine values: `"5" + "5"` gives `"55"` (joining text), while `5 + 5` gives `10`. That's why converting with `int()` before doing maths on user input is important.

Does this way of looking at it help?""",
    ],
}

FAQ = [
    (("float", "decimal"), "A `float` is a number with a decimal point, like `2.5` or even `3.0`. Dividing with `/` always gives a float, so `10 / 2` is `5.0`."),
    (("string", "str", "quote", "text"), "A string (`str`) is text inside quotes. `'hi'` and `\"hi\"` are the same. Without quotes, Python reads the word as a variable name instead."),
    (("bool", "true", "false"), "A `bool` is either `True` or `False`, with a capital first letter and no quotes. You'll use them a lot with `if` statements later."),
    (("name", "naming", "call"), "Variable names can use letters, digits and underscores, but can't start with a digit or contain spaces. Python style is lowercase with underscores, like `student_name`."),
    (("convert", "int(", "change"), "Use `int()`, `float()` or `str()` to convert. For example, `int(\"19\")` gives the number `19`. Converting text that isn't a number, like `int(\"abc\")`, causes an error."),
    (("type(", "type", "check"), "`type()` tells you a value's type. For example, `print(type(3.5))` shows `<class 'float'>`."),
]

UNDERSTOOD = re.compile(r"\b(yes|yep|yeah|ok|okay|got it|makes sense|i understand|understood|clear|sure)\b")
CONFUSED = re.compile(r"\b(no|not really|confus\w*|(don'?t|do not|didn'?t|doesn'?t)\s+(really\s+|quite\s+)?(get|understand|make sense)|lost|huh)\b|不懂|不明白")
EXPERIENCE = re.compile(r"\b(yes|python|java|javascript|c\+\+|html|scratch|coded|coding|course|project|programm\w*)\b")
NO_EXPERIENCE = re.compile(r"\b(no|never|none|nope|not really|first time)\b")
VARIABLE_IDEA = re.compile(r"\b(store|stores|hold|holds|value|name|label|box|container|memory|data)\b")
TYPE_IDEA = re.compile(r"\b(float|decimal|str|string|text)\b")


def _last_user(history: list[dict]) -> str:
    for message in reversed(history):
        if message["role"] == "user":
            return message["content"].lower()
    return ""


class FakeProvider(LLMProvider):
    name = "fake"
    is_fake = True

    def __init__(self, fail_tasks: set[str] | None = None, broken_json_tasks: set[str] | None = None):
        # Tests use these to prove failures are handled, not hidden.
        self.fail_tasks = fail_tasks or set()
        self.broken_json_tasks = broken_json_tasks or set()

    def generate(self, task, system_prompt, history):
        if task in self.fail_tasks:
            raise ProviderError(f"Fake failure in {task}.")
        if task in self.broken_json_tasks:
            return "Sure! Here is my answer: level beginner"

        if task == "diagnostic_question":
            number = int(re.search(r"question number (\d+)", system_prompt).group(1))
            return DIAGNOSTIC[(number - 1) % len(DIAGNOSTIC)]

        if task == "classify_level":
            answers = [m["content"].lower() for m in history if m["role"] == "user"]
            score, gaps = 0, []
            if answers and EXPERIENCE.search(answers[0]) and not NO_EXPERIENCE.search(answers[0]):
                score += 1
            if len(answers) > 1 and VARIABLE_IDEA.search(answers[1]):
                score += 1
            else:
                gaps.append("what a variable is")
            if len(answers) > 2 and TYPE_IDEA.search(answers[2]):
                score += 1
            else:
                gaps.append("the basic data types")
            level = "some_experience" if score >= 2 else "beginner"
            reason = "They showed some experience and understanding." if level == "some_experience" else "They are new to these ideas."
            return json.dumps({"level": level, "reason": reason, "gaps": gaps})

        level = "some_experience" if "some programming experience" in system_prompt else "beginner"
        if task == "explain":
            return EXPLAIN[level][0]
        if task == "reexplain":
            attempt = int(re.search(r"attempt (\d+)", system_prompt).group(1))
            return EXPLAIN[level][attempt % len(EXPLAIN[level])]

        if task == "respond":
            text = _last_user(history)
            if "?" in text:
                for keywords, answer in FAQ:
                    if any(k in text for k in keywords):
                        return json.dumps({"intent": "question", "reply": answer + "\n\nAnything else you'd like to ask?"})
                return json.dumps({"intent": "question", "reply": "*(Fake tutor: the real model will answer this question. The fake one only knows a few common questions about variables and types.)*"})
            if CONFUSED.search(text):
                return json.dumps({"intent": "confused", "reply": "No problem, let me explain it another way."})
            if UNDERSTOOD.search(text):
                return json.dumps({"intent": "understood", "reply": "Great. The key idea: a variable is a name that holds a value, and every value has a type such as `int`, `float`, `str` or `bool`."})
            return json.dumps({"intent": "unclear", "reply": "I'm not sure what you mean. Does the explanation make sense, or is there a part you'd like me to explain again?"})

        raise ProviderError(f"The fake provider has no reply for task {task!r}.")
