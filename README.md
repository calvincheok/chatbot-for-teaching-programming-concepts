# Python Tutor: Teaching Engine Prototype (FYP1)

Prototype for the FYP "Chatbot for Teaching Basic Programming Concepts".
It covers **Objective 1** of the proposal: a conversational teaching engine
that assesses what the learner already knows through dialogue, then explains
at a suitable level and depth. It matches the FYP1 Gantt task "Teaching
Engine Prototype (Prompt Engineering)".

It currently runs with a **fake tutor**: replies are pre-written test
content, not a real AI model. No API costs are involved.

## How to run

You need Python 3.10 or newer.

```
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in a browser on a computer or phone.

Other ways to use it:
- `python try_in_terminal.py` lets you chat with the engine in the terminal.
- `python -m unittest discover tests` runs the 19 automated tests.

The database is saved in `data/teaching.db`. Delete that file to start fresh.

## What happens in a session

1. **Getting to know you.** The tutor asks 3 diagnostic questions, one at a
   time: the learner's coding experience, what they think a variable is, and
   a small question about data types.
2. **Choosing a level.** The AI reads the answers and picks a level, either
   *beginner* or *some experience*. It records the reason and what the
   learner didn't know yet.
3. **Explanation.** The AI explains at that level. Beginners get everyday
   analogies (proposal Section 4.2). Learners with some experience get
   technical terms and common mistakes.
4. **Discussion.** Each reply from the learner is sorted into one of four
   types:
   - *Understood:* the tutor confirms the key point and the explanation is finished.
   - *Confused:* the tutor explains again with a different approach.
   - *Question:* the tutor answers it and the learner stays in the discussion.
   - *Unclear:* the tutor asks what the learner means.

   The learner can keep asking questions after finishing.

The app decides the order of these steps. The AI only writes the content for
the step the app asks for. This keeps it acting as a tutor rather than a
general question-answering chatbot, which is the problem the proposal
identifies.

## What each part does

| File | Purpose |
|---|---|
| `teaching/engine.py` | The teaching engine. It controls the steps above, sends each request to the AI, checks the reply, and saves the result. If the AI fails or replies in the wrong format, nothing is saved and the learner can send the message again. |
| `teaching/prompts.py` | The prompt engineering. Each turn, the AI receives a structured system prompt and the recent conversation (proposal Section 4.2). The system prompt holds the tutor's rules plus the instruction for the current step. The level strategies live here too. |
| `teaching/providers/base.py` | The single interface between the engine and any AI provider. |
| `teaching/providers/fake.py` | The fake tutor: pre-written replies and simple keyword rules. |
| `teaching/storage.py` | The SQLite database. It stores every message, every teaching decision (which level was chosen and why, each re-explanation) and every AI call. The call log lets real usage be measured once a paid API is connected. |
| `teaching/concepts.py` | The topics from proposal Table 3.1. Only Variables and Data Types is switched on. |
| `app.py` | The Flask web server and JSON API. It ignores requests from other websites. A double click or network retry of the same message is processed only once, so the AI is never called twice for one message. |
| `templates/index.html`, `static/chat.css`, `static/chat.js` | The chat page. It shows the topic list, the lesson progress track, the chosen level, quick-reply buttons and the conversation. Enter sends and Shift + Enter makes a new line. If sending fails, the message stays in the box with a "Send again" button. |
| `try_in_terminal.py` | A terminal chat for trying the engine without the web page. |
| `tests/test_engine.py` | 19 functional tests. |

## Real, fake and not built yet

**Working, and checked by the automated tests and in a browser:**
- the step-by-step flow and level choice
- re-explaining when the learner is confused
- answering questions
- prompts built per step
- checks on the AI's replies
- failure handling with resend
- duplicate-message protection
- saving sessions and reopening earlier ones
- desktop and mobile layout

**Fake:**
- Every tutor reply is pre-written.
- The fake tutor judges replies with keyword rules, knows answers to only a few common questions, and has two explanations per level, so a third "I don't get it" repeats the first.
- The prompts in `prompts.py` have **not been sent to a real model yet**.

**Not built yet:**
- A real LLM API provider. Before choosing one, check current pricing and agree a testing budget.
- The other topics.
- Practice exercises with feedback (FYP2 in the proposal timeline).
- Accounts. For now, each browser is identified by a cookie.

**Not evaluated yet.** The tests show the software follows its rules, not
that learners understand better. That needs the pre/post concept quizzes
and the satisfaction questionnaire planned in proposal Section 4.6.

## Adding a real LLM API later

1. Write a new class in `teaching/providers/` with the same `generate(task, system_prompt, history)` method as `fake.py`.
2. Select it in `teaching/providers/__init__.py` using the `LLM_PROVIDER` setting.
3. Keep the API key on the server, for example in an environment variable.

The engine and the page do not need to change.
