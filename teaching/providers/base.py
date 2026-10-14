"""The interface between the teaching engine and any LLM provider.

The engine only ever calls ``generate``. Swapping the fake provider for a real
LLM API means writing another class with the same method and changing one
setting; the teaching engine does not change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    """The provider failed or returned something unusable."""


class LLMProvider(ABC):
    name = "base"
    is_fake = False

    @abstractmethod
    def generate(self, task: str, system_prompt: str, history: list[dict]) -> str:
        """Return the model's reply text.

        task           which step this is, e.g. "explain" (a real API only needs
                       the system prompt; the fake provider uses this name)
        system_prompt  the full structured prompt from prompts.py
        history        the conversation so far: [{"role": "user"|"assistant", "content": str}]
        """
