"""Chooses the LLM provider. Only the fake provider exists for now.

A real LLM API provider will be added later as another class with the same
``generate`` method, selected here by the LLM_PROVIDER setting.
"""

import os

from .base import LLMProvider, ProviderError
from .fake import FakeProvider


def get_provider() -> LLMProvider:
    choice = os.environ.get("LLM_PROVIDER", "fake").lower()
    if choice != "fake":
        raise ProviderError(f"Provider {choice!r} is not available yet. Only the fake provider exists in this prototype.")
    return FakeProvider()


__all__ = ["LLMProvider", "ProviderError", "FakeProvider", "get_provider"]
