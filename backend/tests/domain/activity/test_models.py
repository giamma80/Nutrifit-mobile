"""Test suite per Activity domain models.

Verifica normalizzazione timestamp, immutabilità Value Objects,
e comportamento dei helper methods.
"""

import pytest
from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivityDelta,
    DailyActivitySummary,
    ActivitySource,
    _normalize_minute_iso,
)


class TestTimestampNormalization:
    """Test normalizzazione timestamp a minuto UTC."""

    def test_normalize_minute_iso_with_z_suffix(self) -> None:
        """Normalizza timestamp con Z suffix."""
        result = _normalize_minute_iso("2025-01-15T14:23:47Z")
        assert result == "2025-01-15T14:23:00Z"

    def test_normalize_minute_iso_with_offset(self) -> None:
        """Normalizza timestamp con offset timezone."""
        result = _normalize_minute_iso("2025-01-15T16:23:47+02:00")
        assert result == "2025-01-15T14:23:00Z"  # Converted to UTC

    def test_normalize_minute_iso_already_normalized(self) -> None:
        """Timestamp già normalizzato resta invariato."""
        normalized = "2025-01-15T14:23:00Z"
        result = _normalize_minute_iso(normalized)
        assert result == normalized

    def test_normalize_minute_iso_invalid_format(self) -> None:
        """Formato invalido ritorna stringa originale (fail-soft)."""
        invalid = "invalid-timestamp"
        result = _normalize_minute_iso(invalid)
        assert result == invalid

    def test_normalize_minute_iso_naive_datetime(self) -> None:
        """Datetime naive assume UTC."""
        result = _normalize_minute_iso("2025-01-15T14:23:47")
        assert result == "2025-01-15T14:23:00Z"


class TestActivityEvent:
    """Test ActivityEvent Value Object."""

    def test_activity_event_creation(self) -> None:
        """Creazione base ActivityEvent."""
        event = ActivityEvent(
            user_id="user1",
            ts="2025-01-15T14:23:47Z",
            steps=100,
            calories_out=5.5,
            hr_avg=75.0,
            source=ActivitySource.APPLE_HEALTH,
        )

        assert event.user_id == "user1"
        assert event.ts == "2025-01-15T14:23:47Z"
        assert event.steps == 100
        assert event.calories_out == 5.5
        assert event.hr_avg == 75.0
        assert event.source == ActivitySource.APPLE_HEALTH

    def test_activity_event_defaults(self) -> None:
        """Default values per campi opzionali."""
        event = ActivityEvent(user_id="user1", ts="2025-01-15T14:23:47Z")

        assert event.steps is None
        assert event.calories_out is None
        assert event.hr_avg is None
        assert event.source == ActivitySource.MANUAL

    def test_activity_event_normalized(self) -> None:
        """Normalizzazione timestamp."""
        event = ActivityEvent(
            user_id="user1",
            ts="2025-01-15T14:23:47Z",
            steps=100,
        )
        normalized = event.normalized()

        assert normalized.ts == "2025-01-15T14:23:00Z"
        assert normalized.user_id == event.user_id
        assert normalized.steps == event.steps

    def test_activity_event_normalized_idempotent(self) -> None:
        """Normalizzazione già normalizzato ritorna stesso oggetto."""
        event = ActivityEvent(
            user_id="user1",
            ts="2025-01-15T14:23:00Z",
            steps=100,
        )
        normalized = event.normalized()

        assert normalized is event  # Same object reference

    def test_activity_event_immutable(self) -> None:
        """ActivityEvent è immutabile (frozen)."""
        event = ActivityEvent(user_id="user1", ts="2025-01-15T14:23:00Z")

        with pytest.raises(AttributeError):
            event.user_id = "user2"  # type: ignore[misc]


class TestHealthSnapshot:
    """Test HealthSnapshot Value Object."""

    def test_health_snapshot_creation(self) -> None:
        """Creazione base HealthSnapshot."""
        snapshot = HealthSnapshot(
            user_id="user1",
            date="2025-01-15",
            timestamp="2025-01-15T14:23:47Z",
            steps_total=1500,
            calories_out_total=234.5,
            hr_avg_session=72.0,
        )

        assert snapshot.user_id == "user1"
        assert snapshot.date == "2025-01-15"
        assert snapshot.timestamp == "2025-01-15T14:23:47Z"
        assert snapshot.steps_total == 1500
        assert snapshot.calories_out_total == 234.5
        assert snapshot.hr_avg_session == 72.0

    def test_health_snapshot_key(self) -> None:
        """Key method per raggruppamento."""
        snapshot = HealthSnapshot(
            user_id="user1",
            date="2025-01-15",
            timestamp="2025-01-15T14:23:47Z",
            steps_total=1500,
            calories_out_total=234.5,
        )

        assert snapshot.key() == ("user1", "2025-01-15")

    def test_health_snapshot_immutable(self) -> None:
        """HealthSnapshot è immutabile."""
        snapshot = HealthSnapshot(
            user_id="user1",
            date="2025-01-15",
            timestamp="2025-01-15T14:23:47Z",
            steps_total=1500,
            calories_out_total=234.5,
        )

        with pytest.raises(AttributeError):
            snapshot.steps_total = 2000  # type: ignore[misc]


class TestActivityDelta:
    """Test ActivityDelta Value Object."""

    def test_activity_delta_creation(self) -> None:
        """Creazione base ActivityDelta."""
        delta = ActivityDelta(
            user_id="user1",
            date="2025-01-15",
            timestamp="2025-01-15T14:23:47Z",
            steps_delta=500,
            calories_out_delta=45.5,
            steps_total=1500,
            calories_out_total=234.5,
            hr_avg_session=72.0,
            reset=False,
            duplicate=False,
        )

        assert delta.user_id == "user1"
        assert delta.steps_delta == 500
        assert delta.calories_out_delta == 45.5
        assert delta.reset is False
        assert delta.duplicate is False

    def test_activity_delta_immutable(self) -> None:
        """ActivityDelta è immutabile."""
        delta = ActivityDelta(
            user_id="user1",
            date="2025-01-15",
            timestamp="2025-01-15T14:23:47Z",
            steps_delta=500,
            calories_out_delta=45.5,
            steps_total=1500,
            calories_out_total=234.5,
            hr_avg_session=72.0,
            reset=False,
            duplicate=False,
        )

        with pytest.raises(AttributeError):
            delta.reset = True  # type: ignore[misc]


class TestDailyActivitySummary:
    """Test DailyActivitySummary Value Object."""

    def test_daily_activity_summary_creation(self) -> None:
        """Creazione base DailyActivitySummary."""
        summary = DailyActivitySummary(
            user_id="user1",
            date="2025-01-15",
            total_steps=5000,
            total_calories_out=456.789,
            events_count=24,
        )

        assert summary.user_id == "user1"
        assert summary.date == "2025-01-15"
        assert summary.total_steps == 5000
        assert summary.total_calories_out == 456.789
        assert summary.events_count == 24

    def test_calories_out_rounded(self) -> None:
        """Metodo di arrotondamento calorie."""
        summary = DailyActivitySummary(
            user_id="user1",
            date="2025-01-15",
            total_steps=5000,
            total_calories_out=456.789,
            events_count=24,
        )

        assert summary.calories_out_rounded() == 456.79
        assert summary.calories_out_rounded(1) == 456.8
        assert summary.calories_out_rounded(0) == 457

    def test_daily_activity_summary_immutable(self) -> None:
        """DailyActivitySummary è immutabile."""
        summary = DailyActivitySummary(
            user_id="user1",
            date="2025-01-15",
            total_steps=5000,
            total_calories_out=456.789,
            events_count=24,
        )

        with pytest.raises(AttributeError):
            summary.total_steps = 6000  # type: ignore[misc]


class TestActivitySource:
    """Test ActivitySource enum."""

    def test_activity_source_values(self) -> None:
        """Valori enum ActivitySource."""
        assert ActivitySource.APPLE_HEALTH == "APPLE_HEALTH"
        assert ActivitySource.GOOGLE_FIT == "GOOGLE_FIT"
        assert ActivitySource.MANUAL == "MANUAL"

    def test_activity_source_construction_from_string(self) -> None:
        """Costruzione enum da stringa."""
        source = ActivitySource("APPLE_HEALTH")
        assert source == ActivitySource.APPLE_HEALTH

        source = ActivitySource("MANUAL")
        assert source == ActivitySource.MANUAL
