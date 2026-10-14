"""Functional tests for the teaching engine and API, using the fake tutor.

They check that the app follows its teaching rules. They do not measure
teaching quality; that needs a real model and the planned user study.
"""

import os
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from teaching import prompts
from teaching.concepts import CONCEPTS
from teaching import storage
from teaching.engine import COMPLETE_PASSED, COMPLETE_REVIEW, MAX_CHECKS, parse_json_reply
from teaching.providers.base import ProviderError
from teaching.providers.fake import FakeProvider

HEADERS = {"X-Requested-With": "fyp-chat"}


class EngineFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.provider = FakeProvider()
        self.client = create_app(os.path.join(self.tmp.name, "t.db"), self.provider).test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, url, rid=None, expect=200, **body):
        body["request_id"] = rid or uuid.uuid4().hex
        res = self.client.post(url, json=body, headers=HEADERS)
        self.assertEqual(res.status_code, expect, res.get_json())
        return res.get_json()

    def start(self, concept="variables"):
        state = self.post("/api/sessions", concept=concept)
        self.sid = state["session"]["id"]
        return state

    def say(self, text, **kw):
        return self.post(f"/api/sessions/{self.sid}/messages", text=text, **kw)

    def beginner(self):
        self.start()
        self.say("No, never")
        self.say("I don't know")
        return self.say("not sure")

    # ------------------------------------------------------------------
    def test_starts_with_welcome_and_first_diagnostic_question(self):
        state = self.start()
        tasks = [m["task"] for m in state["messages"]]
        self.assertEqual(tasks, ["welcome", "diagnostic_question"])
        self.assertEqual(state["session"]["stage"], "assess")

    def test_asks_three_questions_one_at_a_time_before_teaching(self):
        self.start()
        state = self.say("No, never")
        self.assertEqual(state["messages"][-1]["task"], "diagnostic_question")
        state = self.say("a box?")
        self.assertEqual(state["session"]["questions_asked"], 3)
        self.assertEqual(state["session"]["stage"], "assess")
        self.assertNotIn("explain", [m["task"] for m in state["messages"]])

    def test_beginner_gets_analogy_explanation(self):
        state = self.beginner()
        self.assertEqual(state["session"]["level"], "beginner")
        self.assertEqual(state["session"]["stage"], "discuss")
        self.assertIn("labelled box", state["messages"][-1]["content"])

    def test_experienced_learner_gets_technical_explanation(self):
        self.start()
        self.say("Yes, I did a Java course")
        self.say("A name that stores a value")
        state = self.say("3.5 is a float and hello is a string")
        self.assertEqual(state["session"]["level"], "some_experience")
        self.assertIn("binds a name to a value", state["messages"][-1]["content"])

    def test_confused_learner_gets_a_different_explanation(self):
        state = self.beginner()
        first = state["messages"][-1]["content"]
        state = self.say("I don't understand")
        self.assertEqual(state["messages"][-1]["task"], "reexplain")
        self.assertNotEqual(state["messages"][-1]["content"], first)
        self.assertEqual(state["session"]["reexplains"], 1)

    def test_confusion_phrasings_are_recognised(self):
        for text in ["I don't really get it", "it doesn't make sense", "I'm confused", "不懂"]:
            with self.subTest(text=text):
                self.beginner()
                self.assertEqual(self.say(text)["messages"][-1]["task"], "reexplain")

    def test_question_is_answered_without_changing_stage(self):
        self.beginner()
        state = self.say("What is a float?")
        self.assertEqual(state["messages"][-1]["task"], "respond:question")
        self.assertIn("decimal point", state["messages"][-1]["content"])
        self.assertEqual(state["session"]["stage"], "discuss")

    def test_unclear_reply_asks_for_clarification(self):
        self.beginner()
        state = self.say("hmm the box thing")
        self.assertEqual(state["messages"][-1]["task"], "respond:unclear")

    def test_understood_leads_to_a_check_question(self):
        self.beginner()
        state = self.say("Yes, that makes sense")
        self.assertEqual(state["session"]["stage"], "check")
        self.assertEqual(state["messages"][-1]["task"], "check_question")
        self.assertEqual(state["session"]["checks_asked"], 1)

    def test_beginner_needs_two_correct_checks(self):
        self.beginner()
        self.say("Yes, that makes sense")
        state = self.say("it's a string")
        self.assertEqual(state["session"]["stage"], "check")          # 1 of 2
        self.assertEqual([m["task"] for m in state["messages"][-2:]], ["check_correct", "check_question"])
        state = self.say("8")
        self.assertEqual(state["session"]["stage"], "complete")
        self.assertEqual(state["messages"][-1]["content"], COMPLETE_PASSED)
        state = self.say("What is a bool?")                                # questions still allowed
        self.assertEqual(state["messages"][-1]["task"], "respond:question")

    def test_experienced_learner_needs_one_correct_check(self):
        self.start()
        self.say("Yes, I did a Java course")
        self.say("A name that stores a value")
        self.say("3.5 is a float and hello is a string")
        self.say("ok got it")
        state = self.say("str")
        self.assertEqual(state["session"]["checks_needed"], 1)
        self.assertEqual(state["session"]["stage"], "complete")

    def test_wrong_check_answer_is_explained_then_asked_again(self):
        self.beginner()
        self.say("Yes, that makes sense")
        state = self.say("an int")
        self.assertEqual(state["session"]["stage"], "check")
        self.assertEqual(state["messages"][-2]["task"], "check_wrong")
        self.assertIn("quotes", state["messages"][-2]["content"])
        self.assertEqual(state["messages"][-1]["task"], "check_question")
        self.assertEqual(state["session"]["checks_correct"], 0)

    def test_lesson_ends_after_max_checks_marked_for_review(self):
        self.beginner()
        self.say("Yes, that makes sense")
        for _ in range(MAX_CHECKS):
            state = self.say("I don't know")
        self.assertEqual(state["session"]["stage"], "complete")
        self.assertEqual(state["session"]["checks_asked"], MAX_CHECKS)
        self.assertEqual(state["messages"][-1]["content"], COMPLETE_REVIEW)

    def test_operators_topic_full_lesson(self):
        self.start("operators")
        self.say("never coded")
        self.say("no idea")
        state = self.say("not sure")
        self.assertEqual(state["session"]["level"], "beginner")
        self.assertIn("calculator", state["messages"][-1]["content"])
        state = self.say("What is the difference between = and ==?")
        self.assertIn("compares", state["messages"][-1]["content"])
        self.say("ok, makes sense")
        self.say("3")
        state = self.say("2")
        self.assertEqual(state["session"]["stage"], "complete")

    def test_control_flow_topic_full_lesson(self):
        self.start("control_flow")
        self.say("Yes, Python at school")
        self.say("It checks a condition and decides what to run")
        state = self.say("3 times")
        self.assertEqual(state["session"]["level"], "some_experience")
        self.assertIn("indentation", state["messages"][-1]["content"])
        self.say("got it")
        state = self.say("big")
        self.assertEqual(state["messages"][-2]["task"], "check_wrong")
        state = self.say("4 times")
        self.assertEqual(state["session"]["stage"], "complete")

    def test_number_answers_are_matched_exactly(self):
        self.start("operators")
        for text in ["no", "no", "no", "yes ok"]:
            self.say(text)
        state = self.say("3.33")                                       # 10 // 3 is 3, not 3.33
        self.assertEqual(state["messages"][-2]["task"], "check_wrong")

    def test_disabled_topic_refused(self):
        self.post("/api/sessions", concept="oop", expect=404)

    def test_blocked_without_header(self):
        res = self.client.post("/api/sessions", json={"request_id": uuid.uuid4().hex})
        self.assertEqual(res.status_code, 403)

    def test_provider_failure_saves_nothing_and_retry_works(self):
        self.start()
        self.say("No, never")
        before = len(self.client.get(f"/api/sessions/{self.sid}").get_json()["messages"])
        self.provider.fail_tasks = {"diagnostic_question"}
        rid = uuid.uuid4().hex
        err = self.say("I don't know", rid=rid, expect=502)
        self.assertTrue(err["retryable"])
        after = len(self.client.get(f"/api/sessions/{self.sid}").get_json()["messages"])
        self.assertEqual(before, after)
        self.provider.fail_tasks = set()
        state = self.say("I don't know", rid=rid)
        self.assertEqual(len(state["messages"]), before + 2)

    def test_broken_json_from_model_is_rejected(self):
        self.start()
        self.say("No")
        self.say("no idea")
        self.provider.broken_json_tasks = {"classify_level"}
        err = self.say("not sure", expect=502)
        self.assertIn("format", err["error"])
        state = self.client.get(f"/api/sessions/{self.sid}").get_json()
        self.assertEqual(state["session"]["stage"], "assess")

    def test_duplicate_request_runs_once(self):
        self.start()
        rid = uuid.uuid4().hex
        a = self.say("No, never", rid=rid)
        b = self.say("No, never", rid=rid)
        self.assertEqual(a, b)
        self.assertEqual(sum(1 for m in b["messages"] if m["role"] == "learner"), 1)

    def test_sessions_are_private_to_each_learner(self):
        self.start()
        other = create_app(os.path.join(self.tmp.name, "t.db"), self.provider).test_client()
        self.assertEqual(other.get(f"/api/sessions/{self.sid}").status_code, 404)

    def test_level_decision_is_recorded(self):
        self.beginner()
        state = self.client.get(f"/api/sessions/{self.sid}").get_json()
        self.assertTrue(state["session"]["level_reason"])
        self.assertIn("what a variable is", state["session"]["gaps"])


class PromptTests(unittest.TestCase):
    def test_every_task_prompt_includes_the_tutor_rules(self):
        concept = CONCEPTS["variables"]
        fields = dict(number=1, total=3, focus="x", level_description="y", strategy="z", gaps="g", attempt=1)
        self.assertIn("check_question", prompts.TASKS)
        self.assertIn("grade_check", prompts.TASKS)
        for task in prompts.TASKS:
            text = prompts.system_prompt(task, concept, **fields)
            self.assertIn("Act as a teacher", text)
            self.assertIn("Variables and Data Types", text)

    def test_explain_prompt_uses_level_strategy(self):
        text = prompts.system_prompt("explain", CONCEPTS["variables"], level_description=prompts.LEVELS["beginner"],
                                     strategy=prompts.STRATEGIES["beginner"], gaps="what a variable is")
        self.assertIn("everyday analogy", text)
        self.assertIn("what a variable is", text)

    def test_diagnostic_focus_follows_the_topic(self):
        self.assertIn("experience", prompts.diagnostic_focus(CONCEPTS["operators"], 1))
        self.assertIn("7 / 2", prompts.diagnostic_focus(CONCEPTS["operators"], 2))
        self.assertIn("range(3)", prompts.diagnostic_focus(CONCEPTS["control_flow"], 3))

    def test_old_database_gets_new_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.db")
            conn = storage.connect(path)
            conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, learner_id TEXT, concept TEXT, stage TEXT)")
            conn.close()
            storage.init(path)
            conn = storage.connect(path)
            columns = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
            conn.close()
            self.assertTrue({"checks_asked", "checks_correct"} <= columns)

    def test_github_pages_files_are_up_to_date(self):
        import build_pages
        self.assertEqual(build_pages.stale(), [], "Run: python build_pages.py")

    def test_json_parser(self):
        self.assertEqual(parse_json_reply('```json\n{"level": "beginner", "reason": "r"}\n```',
                                          {"level": {"beginner"}, "reason": str})["level"], "beginner")
        with self.assertRaises(ProviderError):
            parse_json_reply('{"level": "expert", "reason": "r"}', {"level": {"beginner"}, "reason": str})
        with self.assertRaises(ProviderError):
            parse_json_reply("not json", {"level": {"beginner"}})
        with self.assertRaises(ProviderError):
            parse_json_reply('{"correct": "yes", "reply": "r"}', {"correct": bool, "reply": str})


if __name__ == "__main__":
    unittest.main()
