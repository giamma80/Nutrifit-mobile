from typing import Any  # noqa: F401 (reserved for potential future assertions)
from pytest import MonkeyPatch  # type: ignore
from inference.adapter import get_active_adapter, HeuristicAdapter, StubAdapter


def test_adapter_selection_stub(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("AI_HEURISTIC_ENABLED", raising=False)
    adapter = get_active_adapter()
    assert isinstance(adapter, StubAdapter)


def test_adapter_selection_heuristic(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AI_HEURISTIC_ENABLED", "1")
    adapter = get_active_adapter()
    assert isinstance(adapter, HeuristicAdapter)
