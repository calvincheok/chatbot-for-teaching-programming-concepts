"""Chat with the teaching engine in the terminal, before the web page exists.

Run:  python try_in_terminal.py
Type your replies. Type 'quit' to stop. Uses the fake tutor, so it costs nothing.
"""

import os
import re
import tempfile

from teaching.engine import EngineError, TeachingEngine
from teaching.providers import FakeProvider


def show(message: dict) -> None:
    who = {"tutor": "Tutor", "app": "App", "learner": "You"}[message["role"]]
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", message["content"])
    print(f"\n[{who}] {text}")


def main() -> None:
    db = os.path.join(tempfile.gettempdir(), "fyp_terminal_try.db")
    engine = TeachingEngine(db, FakeProvider())
    learner = "terminal-learner".ljust(32, "x")
    state = engine.start(learner, "variables")
    for m in state["messages"]:
        show(m)
    seen = len(state["messages"])
    while True:
        try:
            text = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"quit", "exit"}:
            break
        try:
            state = engine.send(state["session"]["id"], learner, text)
        except EngineError as exc:
            print(f"\n[Error] {exc.message}")
            continue
        for m in state["messages"][seen:]:
            if m["role"] != "learner":
                show(m)
        seen = len(state["messages"])
        s = state["session"]
        print(f"\n  (stage: {s['stage']}, level: {s['level'] or 'not decided yet'}, re-explanations: {s['reexplains']})")


if __name__ == "__main__":
    main()
