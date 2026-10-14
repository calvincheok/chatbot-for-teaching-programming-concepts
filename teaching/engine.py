"""The conversational teaching engine (proposal Objective 1, Section 4.2).

The app, not the model, controls the order of teaching:

    assess   ask diagnostic questions one at a time (3 by default)
             -> the model classifies the learner's level from the answers
    discuss  explain at that level, then read each learner reply:
               understood -> confirm, then move on to check
               confused   -> explain again with a different approach
               question   -> answer it, stay here
               unclear    -> ask what they mean, stay here
    check    ask short check questions, one at a time, to confirm they really
             understood. A wrong answer is followed by a targeted re-explanation
             and another question. Beginners need 2 correct answers, learners
             with some experience need 1. After 4 questions the lesson ends
             anyway, marked as worth reviewing.
    complete the lesson is finished; they can still ask questions

For each turn the engine builds a structured system prompt (prompts.py) and
sends it with the recent conversation to the provider. Model replies that
must be JSON are checked before use. If the provider fails, nothing is
saved and the learner can send the same message again.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from contextlib import contextmanager

from . import prompts, storage
from .concepts import CONCEPTS
from .providers.base import LLMProvider, ProviderError

DIAGNOSTIC_QUESTIONS = 3
HISTORY_LIMIT = 12          # recent messages sent to the model each turn
MAX_MESSAGE_LENGTH = 1000
CHECKS_NEEDED = {"beginner": 2, "some_experience": 1}   # correct answers to finish
MAX_CHECKS = 4                                           # check questions before ending anyway

WELCOME = ("Hi! I'm your Python tutor. Today we'll learn about **{title}**. "
           "First I'll ask you a few quick questions, so I can explain things at the right level for you. "
           "There are no wrong answers, and \"I don't know\" is fine.")


COMPLETE_PASSED = "Lesson complete! You answered the check questions correctly. You can keep asking questions here."
COMPLETE_REVIEW = ("Lesson complete. Some points are still a bit shaky, so it's worth coming back to this topic later. "
                   "You can keep asking questions here.")


class EngineError(Exception):
    """A problem the learner should see. ``retryable`` means sending again may work."""

    def __init__(self, message: str, status: int = 400, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.status = status
        self.retryable = retryable


def parse_json_reply(text: str, required: dict[str, set | type]) -> dict:
    """Read a JSON reply from the model and check its fields.

    ``required`` maps each field to either a set of allowed values or a type.
    """
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProviderError("The tutor's reply was not in the expected format.") from exc
    if not isinstance(data, dict):
        raise ProviderError("The tutor's reply was not in the expected format.")
    for field, rule in required.items():
        value = data.get(field)
        if isinstance(rule, set):
            if value not in rule:
                raise ProviderError(f"The tutor's reply had an invalid '{field}'.")
        elif not isinstance(value, rule) or (isinstance(value, str) and not value.strip()):
            raise ProviderError(f"The tutor's reply was missing '{field}'.")
    return data


def check_text(text) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ProviderError("The tutor returned an empty reply.")
    if len(text) > 4000:
        raise ProviderError("The tutor's reply was too long.")
    return text.strip()


class TeachingEngine:
    def __init__(self, db_path: str, provider: LLMProvider):
        self.db_path = db_path
        self.provider = provider
        storage.init(db_path)
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    # ---- infrastructure ---------------------------------------------------
    @contextmanager
    def _db(self):
        conn = storage.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _transaction(self):
        with self._db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def _lock(self, session_id: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(session_id, threading.Lock())

    def _ask(self, session_id: str | None, task: str, concept: dict, history: list[dict], **fields) -> str:
        """One provider call: build the prompt, call, log, turn failures into EngineError."""
        system = prompts.system_prompt(task, concept, **fields)
        started = time.monotonic()
        ok, error = 1, None
        try:
            return self.provider.generate(task, system, history)
        except ProviderError as exc:
            ok, error = 0, str(exc)
            raise EngineError(f"The tutor couldn't reply ({exc}). Your message is kept, so you can send it again.", 502, True) from exc
        except Exception as exc:  # never report success when the provider breaks
            ok, error = 0, f"{type(exc).__name__}: {exc}"
            raise EngineError("The tutor couldn't reply. Your message is kept, so you can send it again.", 502, True) from exc
        finally:
            with self._db() as conn:
                conn.execute(
                    "INSERT INTO llm_calls (session_id, provider, task, ok, error, duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (session_id, self.provider.name, task, ok, error, int((time.monotonic() - started) * 1000), storage.now()),
                )

    def _checked(self, fn):
        """Run a validation step; a bad model reply becomes a retryable error."""
        try:
            return fn()
        except ProviderError as exc:
            raise EngineError(f"{exc} Please send your message again.", 502, True) from exc

    def _history(self, conn, session_id: str) -> list[dict]:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? AND role != 'app' ORDER BY id DESC LIMIT ?",
            (session_id, HISTORY_LIMIT),
        ).fetchall()
        return [{"role": "user" if r["role"] == "learner" else "assistant", "content": r["content"]} for r in reversed(rows)]

    def _add(self, conn, session_id, role, content, task=None) -> None:
        conn.execute("INSERT INTO messages (session_id, role, content, task, created_at) VALUES (?, ?, ?, ?, ?)",
                     (session_id, role, content, task, storage.now()))

    def _event(self, conn, session_id, kind, detail=None) -> None:
        conn.execute("INSERT INTO events (session_id, kind, detail, created_at) VALUES (?, ?, ?, ?)",
                     (session_id, kind, storage.dumps(detail or {}), storage.now()))

    def _session(self, conn, session_id: str, learner_id: str):
        row = conn.execute("SELECT * FROM sessions WHERE id = ? AND learner_id = ?", (session_id, learner_id)).fetchone()
        if not row:
            raise EngineError("That session was not found.", 404)
        return row

    # ---- public actions ------------------------------------------------------
    def start(self, learner_id: str, concept_id: str) -> dict:
        concept = CONCEPTS.get(concept_id)
        if not concept or not concept["enabled"]:
            raise EngineError("That topic isn't available yet.", 404)
        session_id = uuid.uuid4().hex
        welcome = WELCOME.format(title=concept["title"])
        first = self._checked(lambda: check_text(self._ask(
            None, "diagnostic_question", concept, [{"role": "assistant", "content": welcome}],
            number=1, total=DIAGNOSTIC_QUESTIONS, focus=prompts.diagnostic_focus(concept, 1))))
        with self._transaction() as conn:
            ts = storage.now()
            conn.execute(
                "INSERT INTO sessions (id, learner_id, concept, stage, questions_asked, created_at, updated_at) VALUES (?, ?, ?, 'assess', 1, ?, ?)",
                (session_id, learner_id, concept_id, ts, ts),
            )
            self._add(conn, session_id, "tutor", welcome, "welcome")
            self._add(conn, session_id, "tutor", first, "diagnostic_question")
            self._event(conn, session_id, "session_started", {"concept": concept_id})
        return self.state(session_id, learner_id)

    def send(self, session_id: str, learner_id: str, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            raise EngineError("Type a message first.")
        if len(text) > MAX_MESSAGE_LENGTH:
            raise EngineError(f"Please keep messages under {MAX_MESSAGE_LENGTH} characters.")
        with self._lock(session_id):
            with self._db() as conn:
                session = self._session(conn, session_id, learner_id)
                concept = CONCEPTS[session["concept"]]
                history = self._history(conn, session_id) + [{"role": "user", "content": text}]
            if session["stage"] == "assess":
                return self._assess_turn(session, concept, history, text, learner_id)
            if session["stage"] == "check":
                return self._check_turn(session, concept, history, text, learner_id)
            return self._discuss_turn(session, concept, history, text, learner_id)

    # ---- assess: diagnostic questions, then level -----------------------------
    def _assess_turn(self, session, concept, history, text, learner_id) -> dict:
        sid = session["id"]
        asked = session["questions_asked"]
        if asked < DIAGNOSTIC_QUESTIONS:
            question = self._checked(lambda: check_text(self._ask(
                sid, "diagnostic_question", concept, history,
                number=asked + 1, total=DIAGNOSTIC_QUESTIONS, focus=prompts.diagnostic_focus(concept, asked + 1))))
            with self._transaction() as conn:
                self._add(conn, sid, "learner", text)
                self._add(conn, sid, "tutor", question, "diagnostic_question")
                conn.execute("UPDATE sessions SET questions_asked = ?, updated_at = ? WHERE id = ?", (asked + 1, storage.now(), sid))
            return self.state(sid, learner_id)

        # All diagnostic questions answered: classify, then explain at that level.
        result = self._checked(lambda: parse_json_reply(
            self._ask(sid, "classify_level", concept, history),
            {"level": set(prompts.LEVELS), "reason": str}))
        gaps = [g for g in result.get("gaps", []) if isinstance(g, str)][:5] if isinstance(result.get("gaps"), list) else []
        level = result["level"]
        explanation = self._checked(lambda: check_text(self._ask(
            sid, "explain", concept, history,
            level_description=prompts.LEVELS[level], strategy=prompts.STRATEGIES[level],
            gaps=", ".join(gaps) or "nothing specific")))
        with self._transaction() as conn:
            self._add(conn, sid, "learner", text)
            self._add(conn, sid, "app", f"Thanks! I'll explain this for {prompts.LEVELS[level]}.", "level_chosen")
            self._add(conn, sid, "tutor", explanation, "explain")
            conn.execute("UPDATE sessions SET stage = 'discuss', level = ?, level_reason = ?, gaps = ?, updated_at = ? WHERE id = ?",
                         (level, result["reason"], storage.dumps(gaps), storage.now(), sid))
            self._event(conn, sid, "level_chosen", {"level": level, "reason": result["reason"], "gaps": gaps})
        return self.state(sid, learner_id)

    # ---- discuss: respond, re-explain when confused -------------------------
    def _discuss_turn(self, session, concept, history, text, learner_id) -> dict:
        sid = session["id"]
        level = session["level"]
        result = self._checked(lambda: parse_json_reply(
            self._ask(sid, "respond", concept, history, level_description=prompts.LEVELS[level]),
            {"intent": {"understood", "confused", "question", "unclear"}, "reply": str}))
        intent = result["intent"]
        reply = self._checked(lambda: check_text(result["reply"]))
        follow_up = history + [{"role": "assistant", "content": reply}]
        reexplanation = check_question = None
        if intent == "confused":
            reexplanation = self._checked(lambda: check_text(self._ask(
                sid, "reexplain", concept, follow_up,
                level_description=prompts.LEVELS[level], strategy=prompts.STRATEGIES[level], attempt=session["reexplains"] + 1)))
        elif intent == "understood" and session["stage"] == "discuss":
            check_question = self._checked(lambda: check_text(self._ask(
                sid, "check_question", concept, follow_up,
                level_description=prompts.LEVELS[level], number=session["checks_asked"] + 1)))
        with self._transaction() as conn:
            self._add(conn, sid, "learner", text)
            self._add(conn, sid, "tutor", reply, f"respond:{intent}")
            if reexplanation:
                self._add(conn, sid, "tutor", reexplanation, "reexplain")
                conn.execute("UPDATE sessions SET reexplains = reexplains + 1 WHERE id = ?", (sid,))
                self._event(conn, sid, "reexplained", {"attempt": session["reexplains"] + 1})
            if check_question:
                self._add(conn, sid, "app", "Quick check before we finish.", "check_start")
                self._add(conn, sid, "tutor", check_question, "check_question")
                conn.execute("UPDATE sessions SET stage = 'check', checks_asked = checks_asked + 1 WHERE id = ?", (sid,))
                self._event(conn, sid, "understood", {"reexplains": session["reexplains"]})
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (storage.now(), sid))
        return self.state(sid, learner_id)

    # ---- check: short questions to confirm understanding ----------------------
    def _check_turn(self, session, concept, history, text, learner_id) -> dict:
        sid = session["id"]
        level = session["level"]
        number = session["checks_asked"]
        result = self._checked(lambda: parse_json_reply(
            self._ask(sid, "grade_check", concept, history, level_description=prompts.LEVELS[level]),
            {"correct": bool, "reply": str}))
        correct = result["correct"]
        feedback = self._checked(lambda: check_text(result["reply"]))
        total_correct = session["checks_correct"] + (1 if correct else 0)
        passed = total_correct >= CHECKS_NEEDED[level]
        finished = passed or number >= MAX_CHECKS
        next_question = None
        if not finished:
            next_question = self._checked(lambda: check_text(self._ask(
                sid, "check_question", concept, history + [{"role": "assistant", "content": feedback}],
                level_description=prompts.LEVELS[level], number=number + 1)))
        with self._transaction() as conn:
            self._add(conn, sid, "learner", text)
            self._add(conn, sid, "tutor", feedback, "check_correct" if correct else "check_wrong")
            conn.execute("UPDATE sessions SET checks_correct = ? WHERE id = ?", (total_correct, sid))
            self._event(conn, sid, "check_answered", {"number": number, "correct": correct})
            if next_question:
                self._add(conn, sid, "tutor", next_question, "check_question")
                conn.execute("UPDATE sessions SET checks_asked = checks_asked + 1 WHERE id = ?", (sid,))
            else:
                conn.execute("UPDATE sessions SET stage = 'complete' WHERE id = ?", (sid,))
                self._add(conn, sid, "app", COMPLETE_PASSED if passed else COMPLETE_REVIEW, "complete")
                self._event(conn, sid, "completed", {"passed": passed, "checks_asked": number, "checks_correct": total_correct})
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (storage.now(), sid))
        return self.state(sid, learner_id)

    # ---- reading ---------------------------------------------------------------
    def state(self, session_id: str, learner_id: str) -> dict:
        with self._db() as conn:
            s = self._session(conn, session_id, learner_id)
            messages = [dict(m) for m in conn.execute(
                "SELECT id, role, content, task, created_at FROM messages WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()]
        return {
            "session": {
                "id": s["id"], "concept": s["concept"], "concept_title": CONCEPTS[s["concept"]]["title"],
                "stage": s["stage"], "level": s["level"], "level_reason": s["level_reason"],
                "gaps": storage.loads(s["gaps"], []),
                "questions_asked": s["questions_asked"], "questions_total": DIAGNOSTIC_QUESTIONS,
                "reexplains": s["reexplains"],
                "checks_asked": s["checks_asked"], "checks_correct": s["checks_correct"],
                "checks_needed": CHECKS_NEEDED.get(s["level"]), "checks_max": MAX_CHECKS,
                "created_at": s["created_at"], "updated_at": s["updated_at"],
            },
            "messages": messages,
            "fake_tutor": self.provider.is_fake,
        }

    def sessions(self, learner_id: str) -> list[dict]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT id, concept, stage, level, created_at, updated_at FROM sessions WHERE learner_id = ? ORDER BY updated_at DESC, rowid DESC",
                (learner_id,)).fetchall()
        return [{**dict(r), "concept_title": CONCEPTS[r["concept"]]["title"]} for r in rows]
