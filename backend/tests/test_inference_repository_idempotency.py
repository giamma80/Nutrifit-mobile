from repository.ai_meal_photo import meal_photo_repo
from typing import Any


def test_repository_idempotent_same_auto_key(monkeypatch: Any) -> None:
    # Stesso utente + stessi riferimenti -> stessa analysis
    user = "user1"
    photo_id = "ph1"
    photo_url = "http://x/y.jpg"
    first = meal_photo_repo.create_or_get(
        user_id=user,
        photo_id=photo_id,
        photo_url=photo_url,
        idempotency_key=None,
        now_iso="2025-09-27T10:00:00Z",
    )
    second = meal_photo_repo.create_or_get(
        user_id=user,
        photo_id=photo_id,
        photo_url=photo_url,
        idempotency_key=None,
        now_iso="2025-09-27T10:00:05Z",
    )
    assert first.id == second.id
    assert first.idempotency_key_used == second.idempotency_key_used


def test_repository_different_photo_changes_analysis() -> None:
    user = "user2"
    a = meal_photo_repo.create_or_get(
        user_id=user,
        photo_id="phA",
        photo_url="http://x/a.jpg",
        idempotency_key=None,
        now_iso="2025-09-27T10:01:00Z",
    )
    b = meal_photo_repo.create_or_get(
        user_id=user,
        photo_id="phB",
        photo_url="http://x/a.jpg",
        idempotency_key=None,
        now_iso="2025-09-27T10:01:05Z",
    )
    assert a.id != b.id
