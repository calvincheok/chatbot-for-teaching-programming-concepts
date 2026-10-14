"""Pre-written content for the fake tutor, one entry per enabled topic.

This is test content standing in for a real model, not part of the teaching
design. It is plain data (strings, lists, dicts) so that build_pages.py can
copy it into the GitHub Pages version unchanged.

Patterns are regular expressions matched against the learner's message in
lower case. They only use syntax that works the same in Python and
JavaScript. Number answers use (^|[^\\d.])N(?!\\.?\\d) so that, for example,
"3" matches but "3.5" and "13" do not.
"""

EXPERIENCE_QUESTION = ("Before we start, have you written any code before, in Python or any other language? "
                       "Tell me a little about it.")

PATTERNS = {
    "understood": r"\b(yes|yep|yeah|ok|okay|got it|makes sense|i understand|understood|clear|sure)\b",
    "confused": r"\b(no|not really|confus\w*|(don'?t|do not|didn'?t|doesn'?t)\s+(really\s+|quite\s+)?(get|understand|make sense)|lost|huh)\b|不懂|不明白",
    "experience": r"\b(yes|python|java|javascript|c\+\+|html|scratch|coded|coding|course|project|programm\w*)\b",
    "no_experience": r"\b(no|never|none|nope|not really|first time)\b",
}

UNKNOWN_QUESTION = ("*(Fake tutor: the real model will answer this question. "
                    "The fake one only knows a few common questions about this topic.)*")

TOPICS = {
    # ------------------------------------------------------------------
    "variables": {
        "diagnostic": [
            EXPERIENCE_QUESTION,
            "In your own words, what do you think a **variable** is in programming?",
            "Quick one: what kind of value do you think `3.5` is? And what about `\"hello\"`?",
        ],
        # What a good answer to diagnostic questions 2 and 3 looks like, and the gap if it's missing.
        "classify": [
            {"pattern": r"\b(store|stores|hold|holds|value|name|label|box|container|memory|data)\b", "gap": "what a variable is"},
            {"pattern": r"\b(float|decimal|str|string|text)\b", "gap": "the basic data types"},
        ],
        "explain": {
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
        },
        "faq": [
            [["float", "decimal"], "A `float` is a number with a decimal point, like `2.5` or even `3.0`. Dividing with `/` always gives a float, so `10 / 2` is `5.0`."],
            [["string", "str", "quote", "text"], "A string (`str`) is text inside quotes. `'hi'` and `\"hi\"` are the same. Without quotes, Python reads the word as a variable name instead."],
            [["bool", "true", "false"], "A `bool` is either `True` or `False`, with a capital first letter and no quotes. You'll use them a lot with `if` statements later."],
            [["name", "naming", "call"], "Variable names can use letters, digits and underscores, but can't start with a digit or contain spaces. Python style is lowercase with underscores, like `student_name`."],
            [["convert", "int(", "change"], "Use `int()`, `float()` or `str()` to convert. For example, `int(\"19\")` gives the number `19`. Converting text that isn't a number, like `int(\"abc\")`, causes an error."],
            [["type(", "type", "check"], "`type()` tells you a value's type. For example, `print(type(3.5))` shows `<class 'float'>`."],
        ],
        "summary": "Great. The key idea: a variable is a name that holds a value, and every value has a type such as `int`, `float`, `str` or `bool`.",
        "checks": [
            {
                "question": "Quick check: what type is the value `\"42\"` (with the quotes)?",
                "answer": r"\b(str|string|text)\b",
                "right": "Correct. The quotes make it a `str`, even though it looks like a number. `int(\"42\")` would turn it into the number 42.",
                "wrong": "Not quite. Because of the quotes, `\"42\"` is a `str` (text), not a number. Think of the quotes as a name tag that says \"this is text\". Without the quotes, `42` would be an `int`.",
            },
            {
                "question": "Quick check: what does this print?\n\n```python\nx = 5\nx = 8\nprint(x)\n```",
                "answer": r"(^|[^\d.])8(?!\.?\d)",
                "right": "Yes, `8`. The second line replaces the value in `x`, so the 5 is gone.",
                "wrong": "It prints `8`. A variable holds one value at a time. `x = 8` replaces the old value 5, like taking the old item out of the box and putting a new one in.",
            },
            {
                "question": "Quick check: what type is `True`?",
                "answer": r"\b(bool|boolean)\b",
                "right": "Correct, it's a `bool`. A bool can only be `True` or `False`.",
                "wrong": "It's a `bool` (short for boolean). A bool is a yes-or-no value, and it can only be `True` or `False`. Note there are no quotes: `\"True\"` with quotes would be a `str`.",
            },
            {
                "question": "Quick check: what does `int(\"7\") + 3` give?",
                "answer": r"(^|[^\d.])10(?!\.?\d)",
                "right": "Correct, `10`. `int(\"7\")` turns the text into the number 7, then 7 + 3 is 10.",
                "wrong": "It gives `10`. `int(\"7\")` converts the text \"7\" into the number 7, and then normal maths happens: 7 + 3 = 10. Without `int()`, `\"7\" + 3` would cause an error, because Python won't add text and a number.",
            },
        ],
    },
    # ------------------------------------------------------------------
    "operators": {
        "diagnostic": [
            EXPERIENCE_QUESTION,
            "What do you think `7 / 2` gives in Python? And what about `7 % 2`?",
            "Quick one: is `5 > 3 and 2 > 4` True or False?",
        ],
        "classify": [
            {"pattern": r"3\.5|remainder|(^|[^\d.])1(?!\.?\d)", "gap": "arithmetic operators such as / and %"},
            {"pattern": r"^(?!.*\btrue\b).*\bfalse\b", "gap": "comparison and logical operators"},
        ],
        "explain": {
            "beginner": [
                """Think of **operators** as the buttons on a calculator. They take values and produce a new value.

**Arithmetic** (doing maths):

```python
print(7 + 2)   # 9
print(7 / 2)   # 3.5  normal division
print(7 // 2)  # 3    divide, then drop the decimals
print(7 % 2)   # 1    the remainder
```

**Comparison** asks a yes-or-no question and answers `True` or `False`, like checking "is my score above 50?":

```python
print(60 > 50)   # True
print(3 == 4)    # False  (== means "is equal to")
```

**Logical** operators join yes-or-no answers: `and` needs both to be true, `or` needs at least one, and `not` flips the answer.

Does that make sense so far, or is there a part you'd like me to go over?""",
                """Let me try another way, with sweets. You have 7 sweets and 2 friends:

- `7 // 2` is how many each friend gets: `3`
- `7 % 2` is how many are left over: `1`
- `7 / 2` is the exact share if you could cut sweets in half: `3.5`

For `and` and `or`, think of the rules for entering a cinema:

```python
has_ticket = True
is_adult = False
print(has_ticket and is_adult)  # False: you need both
print(has_ticket or is_adult)   # True: one is enough
```

And remember: one `=` puts a value into a variable, two `==` asks "are these equal?".

Is this clearer?""",
            ],
            "some_experience": [
                """Python's operators come in three groups. Watch these details:

- `/` is **true division** and always returns a `float`: `6 / 2` is `3.0`. Use `//` for floor division, `%` for the remainder and `**` for powers.
- Comparisons (`==`, `!=`, `<`, `>=` and so on) return a `bool` and can be chained: `0 < x < 10`.
- `and`, `or`, `not` are words, not `&&` or `||`. They **short-circuit**: in `a and b`, `b` isn't evaluated if `a` is false.

```python
x = 7
print(x // 2, x % 2, x ** 2)   # 3 1 49
print(x % 2 == 1 and x > 5)    # True
```

Precedence: arithmetic first, then comparisons, then `not`, `and`, `or`. Use brackets when in doubt.

Does that all make sense, or do you have a question?""",
                """Another angle: read an expression the way Python evaluates it, step by step.

```python
score = 72
passed = score >= 50 and not score > 100
```

1. Arithmetic goes first (there is none here).
2. Comparisons: `score >= 50` is `True`, `score > 100` is `False`.
3. `not False` is `True`.
4. `True and True` is `True`.

A classic mistake: `if x == 1 or 2:` is always true, because Python reads it as `(x == 1) or 2`, and `2` counts as true. Write `x == 1 or x == 2`, or `x in (1, 2)`.

Does this way of looking at it help?""",
            ],
        },
        "faq": [
            [["//", "floor"], "`//` divides and drops the decimal part: `7 // 2` is `3`. With negative numbers it rounds down, so `-7 // 2` is `-4`."],
            [["%", "modulo", "mod ", "remainder"], "`%` gives the remainder after dividing: `7 % 2` is `1`. A common use is checking for even numbers: `n % 2 == 0`."],
            [["==", "equal"], "`=` stores a value in a variable (`x = 5`). `==` compares two values and gives `True` or `False` (`x == 5`)."],
            [["**", "power", "square"], "`**` means power: `2 ** 3` is `8`, and `5 ** 2` is `25`."],
            [["/", "divide", "division"], "`/` always gives a `float`, even when it divides exactly: `6 / 2` is `3.0`. Use `//` if you want a whole number."],
            [["and", "or", "not"], "`and` is `True` only if both sides are true. `or` is `True` if at least one side is true. `not` flips `True` to `False` and back."],
        ],
        "summary": "Great. The key idea: arithmetic operators calculate (`/` always gives a float, `//` drops the decimals, `%` gives the remainder), comparisons give `True` or `False`, and `and`, `or`, `not` combine them.",
        "checks": [
            {
                "question": "Quick check: what does `10 // 3` give?",
                "answer": r"(^|[^\d.])3(?!\.?\d)",
                "right": "Correct, `3`. `//` divides and throws away the decimal part (10 / 3 is 3.33...).",
                "wrong": "It gives `3`. `//` is floor division: it divides, then drops everything after the decimal point. 10 / 3 is 3.33..., so `10 // 3` is `3`. If you wanted the leftover, `10 % 3` would give `1`.",
            },
            {
                "question": "Quick check: what does `17 % 5` give?",
                "answer": r"(^|[^\d.])2(?!\.?\d)",
                "right": "Yes, `2`. 5 goes into 17 three times (that's 15), and 2 is left over.",
                "wrong": "It's `2`. `%` gives the remainder: 5 fits into 17 three times, which uses 15, and 17 - 15 leaves `2`. Think of sharing 17 sweets between 5 friends: each gets 3 and 2 are left over.",
            },
            {
                "question": "Quick check: is `not (3 > 5)` True or False?",
                "answer": r"^(?!.*\bfalse\b).*\btrue\b",
                "right": "Correct, `True`. `3 > 5` is `False`, and `not` flips it to `True`.",
                "wrong": "It's `True`. Work from the inside out: `3 > 5` is `False`, and `not` flips `False` into `True`.",
            },
            {
                "question": "Quick check: what does this print?\n\n```python\nage = 20\nprint(age >= 18 and age < 21)\n```",
                "answer": r"^(?!.*\bfalse\b).*\btrue\b",
                "right": "Yes, `True`. Both comparisons are true (20 >= 18 and 20 < 21), and `and` needs both.",
                "wrong": "It prints `True`. Check each side on its own: `20 >= 18` is `True`, and `20 < 21` is `True`. `and` gives `True` only when both sides are true, which they are here.",
            },
        ],
    },
    # ------------------------------------------------------------------
    "control_flow": {
        "diagnostic": [
            EXPERIENCE_QUESTION,
            "In your own words, what do you think an **if** statement does in a program?",
            "Quick one: how many times do you think this prints \"hi\"?\n\n```python\nfor i in range(3):\n    print(\"hi\")\n```",
        ],
        "classify": [
            {"pattern": r"\b(condition\w*|check\w*|true|false|decid\w*|decision|choose|chooses|depend\w*|otherwise)\b", "gap": "how if statements make decisions"},
            {"pattern": r"(^|[^\d.])3(?!\.?\d)|\bthree\b", "gap": "how loops repeat code"},
        ],
        "explain": {
            "beginner": [
                """Control flow is how a program decides **what to do**, and **how many times** to do it.

An **if statement** is like a decision at a road junction: if it's raining, take an umbrella; otherwise, don't.

```python
raining = True
if raining:
    print("Take an umbrella")
else:
    print("Enjoy the sun")
```

The indented lines (4 spaces) belong to the `if` or the `else`. Only one of them runs.

A **loop** repeats steps, like doing push-ups:

```python
for i in range(3):
    print("push-up")   # runs 3 times
```

A `while` loop keeps going *as long as* something is true, like stirring until the sugar dissolves.

Does that make sense so far, or is there a part you'd like me to go over?""",
                """Let me try another way. Think of a recipe card.

- An **if** is a step like "If the sauce is too thick, add water." You only do it when the condition is true.
- A **for** loop is "Crack 3 eggs": you know exactly how many times.
- A **while** loop is "Keep stirring while it's lumpy": you don't know how many times, so you check each time.

```python
eggs = 0
while eggs < 3:
    eggs = eggs + 1
    print("cracked egg", eggs)
```

This prints 3 lines, then stops because `eggs < 3` becomes false. If you forgot `eggs = eggs + 1`, it would never stop.

Is this clearer?""",
            ],
            "some_experience": [
                """A quick tour of Python's control flow, with the parts that trip people up:

```python
score = 72
if score >= 80:
    grade = "A"
elif score >= 50:
    grade = "Pass"
else:
    grade = "Fail"
```

- Blocks are defined by **indentation**, not braces. A wrong indent is a real error.
- `elif` chains are checked top to bottom; only the first true branch runs.
- `for` loops over any sequence: `for ch in "abc"` or `for i in range(2, 10, 2)`. `range(n)` stops *before* `n`.
- `while` repeats as long as a condition holds, so make sure something changes or it loops forever.
- `break` leaves a loop early; `continue` skips to the next round.

Does that all make sense, or do you have a question?""",
                """Another angle: trace the code line by line, the way Python runs it.

```python
total = 0
for n in range(1, 5):
    if n % 2 == 0:
        continue
    total += n
print(total)
```

`range(1, 5)` gives 1, 2, 3, 4. For 2 and 4, `continue` skips the rest of the body, so only 1 and 3 are added, and it prints `4`.

Tracing like this, writing down each variable's value after each line, is the fastest way to debug loops and to spot off-by-one errors, such as expecting `range(1, 5)` to include 5.

Does this way of looking at it help?""",
            ],
        },
        "faq": [
            [["difference", "for and while", "while and for"], "Use `for` when you know what you're looping over (a list, a string, or `range(n)`). Use `while` when you repeat until something changes and you don't know how many rounds it will take."],
            [["elif"], "`elif` means \"else if\". Python checks each condition from top to bottom and runs only the first one that is true. `else` runs if none of them were."],
            [["indent", "space", "tab"], "Indentation (usually 4 spaces) shows which lines belong to the `if`, `for` or `while`. Lines indented by the same amount are in the same block."],
            [["range"], "`range(3)` gives 0, 1, 2. It starts at 0 and stops *before* the number you give. `range(1, 4)` gives 1, 2, 3."],
            [["break", "continue", "stop"], "`break` exits the loop straight away. `continue` skips the rest of this round and moves on to the next one."],
            [["while", "infinite", "forever"], "A `while` loop repeats as long as its condition is true. If nothing inside the loop changes the condition, it never stops. That's called an infinite loop."],
            [["else"], "`else` is the \"otherwise\" branch: it runs only when the `if` condition (and any `elif`) was false."],
        ],
        "summary": "Great. The key idea: `if`, `elif` and `else` choose which block runs, `for` repeats over a sequence such as `range(n)`, and `while` repeats as long as a condition stays true.",
        "checks": [
            {
                "question": "Quick check: what does this print?\n\n```python\nx = 4\nif x > 5:\n    print(\"big\")\nelse:\n    print(\"small\")\n```",
                "answer": r"^(?!.*\bbig\b).*\bsmall\b",
                "right": "Correct, `small`. `4 > 5` is `False`, so Python skips the `if` block and runs the `else` block.",
                "wrong": "It prints `small`. Python checks `x > 5` first. Since 4 is not bigger than 5, the condition is `False`, so the `if` block is skipped and the `else` block runs instead. Only one of the two blocks ever runs.",
            },
            {
                "question": "Quick check: how many times does this print \"hi\"?\n\n```python\nfor i in range(4):\n    print(\"hi\")\n```",
                "answer": r"(^|[^\d.])4(?!\.?\d)|\bfour\b",
                "right": "Yes, 4 times. `range(4)` gives 0, 1, 2, 3, which is four values.",
                "wrong": "It prints 4 times. `range(4)` gives the numbers 0, 1, 2, 3. It starts at 0 and stops before 4, so there are four values, and the loop body runs once for each.",
            },
            {
                "question": "Quick check: what is the last number this prints?\n\n```python\nn = 1\nwhile n < 4:\n    print(n)\n    n = n + 1\n```",
                "answer": r"(^|[^\d.])3(?!\.?\d)|\bthree\b",
                "right": "Correct, `3`. After printing 3, `n` becomes 4, and `4 < 4` is `False`, so the loop stops.",
                "wrong": "The last number is `3`. Trace it: it prints 1, 2, 3, adding 1 each time. When `n` becomes 4, the check `n < 4` is `False`, so the loop stops before printing 4.",
            },
            {
                "question": "Quick check: what does this print?\n\n```python\nfor i in range(1, 4):\n    if i == 2:\n        continue\n    print(i)\n```",
                "answer": r"^(?!.*\b2\b)(?=.*\b1\b)(?=.*\b3\b)",
                "right": "Yes, `1` and `3`. When `i` is 2, `continue` skips the `print`.",
                "wrong": "It prints `1` and `3`, on separate lines. `range(1, 4)` gives 1, 2, 3. When `i` is 2, `continue` jumps straight to the next round, so `print(i)` is skipped for 2 only.",
            },
        ],
    },
}
