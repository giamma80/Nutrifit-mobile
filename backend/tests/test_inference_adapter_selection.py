from inference.adapter import get_active_adapter, HeuristicAdapter, StubAdapter


def test_adapter_selection_stub(monkeypatch) -> None:
    monkeypatch.delenv("AI_HEURISTIC_ENABLED", raising=False)
    adapter = get_active_adapter()
    assert isinstance(adapter, StubAdapter)


def test_adapter_selection_heuristic(monkeypatch) -> None:
    monkeypatch.setenv("AI_HEURISTIC_ENABLED", "1")
    adapter = get_active_adapter()
    assert isinstance(adapter, HeuristicAdapter)
