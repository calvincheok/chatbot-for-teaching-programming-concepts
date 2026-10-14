# Python Tutor: Teaching Engine Prototype (FYP1)

Prototype for the FYP "Chatbot for Teaching Basic Programming Concepts".
It covers **Objective 1** of the proposal: a conversational teaching engine
that assesses what the learner already knows through dialogue, then explains
at a suitable level and depth. It matches the FYP1 Gantt task "Teaching
Engine Prototype (Prompt Engineering)".

Three topics work: **Variables and Data Types**, **Operators** and
**Control Flow**. The other three from proposal Table 3.1 are listed for a
later phase.

It currently runs with a **fake tutor**: replies are pre-written test
content, not a real AI model. No API costs are involved.

## Try it online (GitHub Pages)

**Live preview:** https://calvincheok.github.io/chatbot-for-teaching-programming-concepts/

GitHub Pages can only host static files, not a Python server, so the `docs/`
folder holds a version of the prototype that runs entirely in the browser.
It uses the same teaching flow, prompts and fake tutor as the Flask version.
Sessions are saved in each visitor's own browser (localStorage), so they
don't move between devices and nothing is sent to a server.

To publish it (one time):
1. Push the whole project, including the `docs/` folder, to the `main` branch.
2. On GitHub, open the repo, then **Settings > Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, then
   branch `main` and folder `/docs`, and click **Save**.
4. Wait a minute or two. The link above then works, and later pushes update it automatically.

## Run the Flask version on your computer

You need Python 3.10 or newer.

```
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5050 in a browser on a computer or phone. (Port 5050
is used so it doesn't clash with other local projects on 5000.)

Other ways to use it:
- `python try_in_terminal.py operators` lets you chat with the engine in the terminal (topic: `variables`, `operators` or `control_flow`).
- `python -m unittest discover tests` runs the 29 tests for the Flask version.
- `node tests/test_static_site.js` runs the 28 matching tests for the GitHub Pages version (Node 18 or newer).

The database is saved in `data/teaching.db`. Delete that file to start fresh.
An older database is upgraded automatically when the app starts.

### After changing the Python code

The GitHub Pages version gets its topics, prompts, fake content and page
from the Python project. After changing any of them, run:

```
python build_pages.py
```

One of the Python tests fails if you forget, so the two versions can't drift apart.

## What happens in a session

1. **Getting to know you.** The tutor asks 3 diagnostic questions, one at a
   time: the learner's coding experience, then two small questions about the
   topic (for Operators, for example, what `7 / 2` gives).
2. **Choosing a level.** The AI reads the answers and picks a level, either
   *beginner* or *some experience*. It records the reason and what the
   learner didn't know yet.
3. **Explanation.** The AI explains at that level. Beginners get everyday
   analogies (proposal Section 4.2). Learners with some experience get
   technical terms and common mistakes.
4. **Discussion.** Each reply from the learner is sorted into one of four
   types:
   - *Understood:* the tutor confirms the key point and moves on to the check.
   - *Confused:* the tutor explains again with a different approach.
   - *Question:* the tutor answers it and the learner stays in the discussion.
   - *Unclear:* the tutor asks what the learner means.
5. **Check.** Saying "it makes sense" isn't enough on its own. The tutor asks
   short check questions, one at a time, such as predicting what a few lines
   of code print.
   - A correct answer is confirmed with a short reason.
   - A wrong answer (or "I don't know") gets the right answer, a new
     explanation of that specific point, and another check question.
   - Beginners need 2 correct answers, learners with some experience need 1.
   - After 4 check questions the lesson ends anyway and is marked as worth
     reviewing, so the learner never gets stuck.

   These are quick comprehension checks that belong to the teaching
   (Objective 1). Graded practice exercises are still FYP2.
6. **Done.** A finish card offers the next topic or the topic list. The
   learner can still ask questions in the finished lesson.

The app decides the order of these steps. The AI only writes the content for
the step the app asks for. This keeps it acting as a tutor rather than a
general question-answering chatbot, which is the problem the proposal
identifies.

### Moving around

- **Topic list:** shows each topic as *Not started*, *In progress* or
  *Done*, with Start, Continue or Review, plus "Start over".
- **In a lesson:** the "All topics" button (and the Python Tutor title) goes
  back to the list. Progress is saved after every message, so leaving is always
  safe, and unsent text is kept for when you come back.
- **Browser Back button:** also works, because each lesson has its own address (`?session=...`).

## What each part does

| File | Purpose |
|---|---|
| `teaching/engine.py` | The teaching engine. It controls the steps above, sends each request to the AI, checks the reply, and saves the result. If the AI fails or replies in the wrong format, nothing is saved and the learner can send the message again. |
| `teaching/prompts.py` | The prompt engineering. Each turn, the AI receives a structured system prompt and the recent conversation (proposal Section 4.2). The system prompt holds the tutor's rules plus the instruction for the current step. The level strategies live here too. |
| `teaching/concepts.py` | The topics from proposal Table 3.1, with what the diagnostic questions should focus on. Three are switched on. |
| `teaching/providers/base.py` | The single interface between the engine and any AI provider. |
| `teaching/providers/fake.py` | The fake tutor: simple keyword rules standing in for a real model's judgement. |
| `teaching/providers/fake_content.py` | The fake tutor's pre-written questions, explanations, answers and check questions for each topic. |
| `teaching/storage.py` | The SQLite database. It stores every message, every teaching decision (which level was chosen and why, each re-explanation, each check answer) and every AI call. The call log lets real usage be measured once a paid API is connected. |
| `app.py` | The Flask web server and JSON API. It ignores requests from other websites. A double click or network retry of the same message is processed only once, so the AI is never called twice for one message. |
| `templates/index.html`, `static/chat.css`, `static/chat.js` | The chat page, shared by both versions. It shows the topic list with progress, the lesson progress track, the chosen level, quick-reply buttons, the conversation and the finish card. Enter sends and Shift + Enter makes a new line. If sending fails, the message stays in the box with a "Send again" button. |
| `static/backend-server.js` | Connects the page to the Flask API. |
| `try_in_terminal.py` | A terminal chat for trying the engine without the web page. |
| `build_pages.py` | Builds the GitHub Pages version in `docs/` from the files above. |
| `docs/` | The GitHub Pages version. `docs/js/engine.js`, `prompts.js` and `fake-provider.js` are the browser versions of the Python engine, prompts and fake tutor. `storage.js` saves sessions in the browser instead of SQLite, and `backend-local.js` connects the page to them. `index.html`, `chat.js`, `chat.css` and `js/content.js` are generated by `build_pages.py`. |
| `tests/test_engine.py` | 29 functional tests for the Flask version, including one that checks `docs/` is up to date. |
| `tests/test_static_site.js` | 28 matching tests for the GitHub Pages version. They also check that the browser builds exactly the same prompts as Python (`tests/prompt_samples.json`). |

## Real, fake and not built yet

**Working, and checked by the automated tests and in a browser:**
- the step-by-step flow and level choice, for all three topics
- re-explaining when the learner is confused
- check questions, with re-explanation after a wrong answer
- answering questions
- prompts built per step
- checks on the AI's replies
- failure handling with resend
- duplicate-message protection (Flask version)
- saving progress, continuing or starting a topic over
- moving between the topic list and lessons, including the browser Back button
- desktop and mobile layout

**Fake:**
- Every tutor reply is pre-written.
- The fake tutor judges replies with keyword rules, knows answers to only a few common questions per topic, and has two explanations per level, so a third "I don't get it" repeats the first.
- It marks check answers by pattern matching, so an answer worded in an unexpected way can be marked wrong. A real model would judge the meaning. Each topic has 4 pre-written check questions.
- If the learner asks a question during the check, the fake tutor treats it as an answer.
- The prompts in `prompts.py` have **not been sent to a real model yet**.

**Not built yet:**
- A real LLM API provider. Before choosing one, check current pricing and agree a testing budget.
- The other three topics (Functions and Scope, OOP Basics, Introductory Data Structures).
- Practice exercises with feedback (FYP2 in the proposal timeline).
- Accounts. For now, each browser is identified by a cookie (Flask) or keeps its own sessions (GitHub Pages).

**Not evaluated yet.** The tests show the software follows its rules, not
that learners understand better. That needs the pre/post concept quizzes
and the satisfaction questionnaire planned in proposal Section 4.6.

## Adding a real LLM API later

1. Write a new class in `teaching/providers/` with the same `generate(task, system_prompt, history)` method as `fake.py`.
2. Select it in `teaching/providers/__init__.py` using the `LLM_PROVIDER` setting.
3. Keep the API key on the server, for example in an environment variable.

The engine and the page do not need to change.

The GitHub Pages version can't call a real AI by itself, because an API key
placed in browser code can be read by anyone who opens the page. Once a real
model is connected, the site needs a backend (the Flask version hosted
somewhere) to hold the key.
