"""Fake LLM provider for building and testing without API costs.

It returns pre-written replies (fake_content.py) and uses simple keyword
rules where a real model would use judgement. It reads the same system
prompt a real model would get (to see the topic, the learner's level and
which question to ask), so it also checks that the prompts carry the right
information. It says nothing about how good the real model's teaching will be.

docs/js/fake-provider.js is the same logic for the GitHub Pages version.
"""

from __future__ import annotations

import json
import re

from ..concepts import CONCEPTS
from .base import LLMProvider, ProviderError
from .fake_content import PATTERNS, TOPICS, UNKNOWN_QUESTION

RX = {name: re.compile(p) for name, p in PATTERNS.items()}


def _last(history: list[dict], role: str) -> str:
    for message in reversed(history):
        if message["role"] == role:
            return message["content"]
    return ""


def _number(pattern: str, text: str) -> int:
    match = re.search(pattern, text)
    if not match:
        raise ProviderError("The fake tutor could not read the prompt.")
    return int(match.group(1))


def _topic(system_prompt: str) -> dict:
    for concept_id, concept in CONCEPTS.items():
        if f"one concept: {concept['title']} (" in system_prompt and concept_id in TOPICS:
            return TOPICS[concept_id]
    raise ProviderError("The fake tutor has no content for this topic.")


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

        topic = _topic(system_prompt)
        text = _last(history, "user").lower()

        if task == "diagnostic_question":
            number = _number(r"question number (\d+)", system_prompt)
            return topic["diagnostic"][(number - 1) % len(topic["diagnostic"])]

        if task == "classify_level":
            answers = [m["content"].lower() for m in history if m["role"] == "user"][-3:]
            score, gaps = 0, []
            if answers and RX["experience"].search(answers[0]) and not RX["no_experience"].search(answers[0]):
                score += 1
            for i, rule in enumerate(topic["classify"], start=1):
                if len(answers) > i and re.search(rule["pattern"], answers[i]):
                    score += 1
                else:
                    gaps.append(rule["gap"])
            level = "some_experience" if score >= 2 else "beginner"
            reason = "They showed some experience and understanding." if level == "some_experience" else "They are new to these ideas."
            return json.dumps({"level": level, "reason": reason, "gaps": gaps})

        level = "some_experience" if "some programming experience" in system_prompt else "beginner"
        explanations = topic["explain"][level]
        if task == "explain":
            return explanations[0]
        if task == "reexplain":
            attempt = _number(r"attempt (\d+)", system_prompt)
            return explanations[attempt % len(explanations)]

        if task == "respond":
            if "?" in text:
                for keywords, answer in topic["faq"]:
                    if any(k in text for k in keywords):
                        return json.dumps({"intent": "question", "reply": answer + "\n\nAnything else you'd like to ask?"})
                return json.dumps({"intent": "question", "reply": UNKNOWN_QUESTION})
            if RX["confused"].search(text):
                return json.dumps({"intent": "confused", "reply": "No problem, let me explain it another way."})
            if RX["understood"].search(text):
                return json.dumps({"intent": "understood", "reply": topic["summary"]})
            return json.dumps({"intent": "unclear", "reply": "I'm not sure what you mean. Does the explanation make sense, or is there a part you'd like me to explain again?"})

        if task == "check_question":
            number = _number(r"check question (\d+)", system_prompt)
            return topic["checks"][(number - 1) % len(topic["checks"])]["question"]

        if task == "grade_check":
            asked = _last(history, "assistant")
            for check in topic["checks"]:
                if check["question"] in asked:
                    correct = bool(re.search(check["answer"], text))
                    return json.dumps({"correct": correct, "reply": check["right" if correct else "wrong"]})
            raise ProviderError("The fake tutor could not find the check question it asked.")

        raise ProviderError(f"The fake provider has no reply for task {task!r}.")
