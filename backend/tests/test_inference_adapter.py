from inference.adapter import StubAdapter, hash_photo_reference
import pytest


@pytest.mark.asyncio
async def test_stub_adapter_items() -> None:
    adapter = StubAdapter()
    items = await adapter.analyze_async(
        user_id="u1",
        photo_id="p1",
        photo_url="url1",
        now_iso="2025-09-27T12:00:00Z",
    )
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0].label == "mixed salad"
    assert items[0].display_name == "Insalata mista"
    assert items[1].label == "chicken breast"
    assert items[1].display_name == "Petto di pollo"
    assert 0.0 < items[0].confidence <= 1.0
    assert 0.0 < items[1].confidence <= 1.0


@pytest.mark.asyncio
async def test_stub_adapter_sync_wrapper_equivalence() -> None:
    """Verifica equivalenza output analyze (sync) vs analyze_async.

    Garantisce che il wrapper non introduca side-effect finché resta per
    compatibilità temporanea.
    """
    adapter = StubAdapter()
    async_items = await adapter.analyze_async(
        user_id="u1",
        photo_id="p1",
        photo_url="url1",
        now_iso="2025-09-27T12:05:00Z",
    )
    # Usa wrapper sync fuori dal loop (creiamo un thread loop artificialmente?)
    # Qui essendo il test async, evitare asyncio.run -> eseguiamo sync wrapper
    # in un executor per non annidare loop.
    import asyncio

    loop = asyncio.get_running_loop()
    sync_items = await loop.run_in_executor(
        None,
        lambda: adapter.analyze(
            user_id="u1",
            photo_id="p1",
            photo_url="url1",
            now_iso="2025-09-27T12:05:00Z",
        ),
    )
    assert len(async_items) == len(sync_items)
    for a, b in zip(async_items, sync_items):
        assert a.label == b.label
        assert a.quantity_g == b.quantity_g
        assert a.calories == b.calories


def test_hash_photo_reference_deterministic() -> None:
    h1 = hash_photo_reference("p1", "url1")
    h2 = hash_photo_reference("p1", "url1")
    h3 = hash_photo_reference("p2", "url1")
    h4 = hash_photo_reference("p1", "url2")
    assert h1 == h2
    assert h1 != h3
    assert h1 != h4
    assert len(h1) == 16
