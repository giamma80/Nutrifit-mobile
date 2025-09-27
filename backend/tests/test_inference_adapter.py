from inference.adapter import StubAdapter, hash_photo_reference




def test_stub_adapter_items():
    adapter = StubAdapter()
    items = adapter.analyze(
        user_id="u1",
        photo_id="p1",
        photo_url="url1",
        now_iso="2025-09-27T12:00:00Z",
    )
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0].label == "Insalata mista"
    assert items[1].label == "Petto di pollo"
    assert 0.0 < items[0].confidence <= 1.0
    assert 0.0 < items[1].confidence <= 1.0



def test_hash_photo_reference_deterministic():
    h1 = hash_photo_reference("p1", "url1")
    h2 = hash_photo_reference("p1", "url1")
    h3 = hash_photo_reference("p2", "url1")
    h4 = hash_photo_reference("p1", "url2")
    assert h1 == h2
    assert h1 != h3
    assert h1 != h4
    assert len(h1) == 16
