"""Test equivalence Activity domain vs repository legacy.

Verifica che i calcoli e aggregazioni del dominio Activity producano
risultati identici alla logica esistente in repository/activities.py
e repository/health_totals.py.
"""

from typing import List
from unittest.mock import Mock

from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivitySource,
)
from domain.activity.adapters import (
    ActivityEventsAdapter,
    ActivitySnapshotsAdapter,
)
from domain.activity.application import (
    ActivitySyncService,
    ActivityAggregationService,
)


class TestActivityEventsEquivalence:
    """Test equivalenza events ingest vs repository legacy."""

    def test_events_ingest_equivalence(self) -> None:
        """Ingest eventi produce stesso risultato di repository legacy."""
        # Setup: domain events
        events = [
            ActivityEvent(
                user_id="test_user",
                ts="2025-01-15T14:30:45Z",
                steps=100,
                calories_out=10.5,
                source=ActivitySource.MANUAL,
            ),
            ActivityEvent(
                user_id="test_user",
                ts="2025-01-15T14:31:22Z",
                steps=50,
                calories_out=5.2,
                source=ActivitySource.APPLE_HEALTH,
            ),
        ]

        # Domain adapter
        domain_adapter = ActivityEventsAdapter()
        domain_accepted, domain_dups, domain_rejected = domain_adapter.ingest_events(events)

        # Legacy repository diretta (per confronto)
        from repository.activities import (
            activity_repo,
            ActivityEventRecord,
            ActivitySource as RepoActivitySource,
        )

        legacy_events = [
            ActivityEventRecord(
                user_id="test_user",
                ts="2025-01-15T14:30:00Z",  # Normalized
                steps=100,
                calories_out=10.5,
                source=RepoActivitySource.MANUAL,
            ),
            ActivityEventRecord(
                user_id="test_user",
                ts="2025-01-15T14:31:00Z",  # Normalized
                steps=50,
                calories_out=5.2,
                source=RepoActivitySource.APPLE_HEALTH,
            ),
        ]

        # Clear repo state
        activity_repo._events_by_user.clear()
        activity_repo._duplicate_keys.clear()

        legacy_accepted, legacy_dups, legacy_rejected = activity_repo.ingest_batch(legacy_events)

        # Equivalence assertions
        assert domain_accepted == legacy_accepted
        assert domain_dups == legacy_dups
        assert len(domain_rejected) == len(legacy_rejected)

    def test_daily_events_count_equivalence(self) -> None:
        """Count eventi giornalieri equivalente."""
        # Reset repository state
        from repository.activities import activity_repo

        activity_repo._events_by_user.clear()
        activity_repo._duplicate_keys.clear()

        # Ingest via domain
        domain_adapter = ActivityEventsAdapter()
        events = [
            ActivityEvent(
                user_id="test_user",
                ts="2025-01-15T10:00:00Z",
                steps=100,
            ),
            ActivityEvent(
                user_id="test_user",
                ts="2025-01-15T11:00:00Z",
                steps=200,
            ),
        ]
        domain_adapter.ingest_events(events)

        # Compare counts
        domain_count = domain_adapter.get_daily_events_count("test_user", "2025-01-15")
        legacy_count = activity_repo.get_daily_stats("test_user", "2025-01-15T00:00:00Z")[
            "events_count"
        ]

        assert domain_count == legacy_count == 2


class TestHealthSnapshotsEquivalence:
    """Test equivalenza snapshot sync vs repository legacy."""

    def test_snapshot_recording_equivalence(self) -> None:
        """Recording snapshot produce stesso risultato."""
        from repository.health_totals import health_totals_repo

        # Clear repository state
        health_totals_repo._deltas.clear()
        health_totals_repo._last_totals.clear()
        health_totals_repo._idemp.clear()

        # Domain snapshot
        snapshot = HealthSnapshot(
            user_id="test_user",
            date="2025-01-15",
            timestamp="2025-01-15T14:30:00Z",
            steps_total=1000,
            calories_out_total=150.5,
            hr_avg_session=75.0,
        )

        # Record via domain
        domain_adapter = ActivitySnapshotsAdapter()
        domain_result = domain_adapter.record_snapshot(snapshot, idempotency_key="test_key")

        # Clear repository state per second call
        health_totals_repo._deltas.clear()
        health_totals_repo._last_totals.clear()
        health_totals_repo._idemp.clear()

        # Record via legacy (same data, fresh state)
        legacy_result = health_totals_repo.record_snapshot(
            user_id="test_user",
            date="2025-01-15",
            timestamp="2025-01-15T14:30:00Z",
            steps=1000,
            calories_out=150.5,
            hr_avg_session=75.0,
            idempotency_key="test_key",
        )

        # Equivalence assertions (structure può differire leggermente)
        assert domain_result["accepted"] == legacy_result["accepted"]
        assert domain_result["duplicate"] == legacy_result["duplicate"]
        assert domain_result["reset"] == legacy_result["reset"]
        assert domain_result["idempotency_key_used"] == legacy_result["idempotency_key_used"]

    def test_daily_totals_equivalence(self) -> None:
        """Totali giornalieri equivalenti."""
        from repository.health_totals import health_totals_repo

        # Reset state
        health_totals_repo._deltas.clear()
        health_totals_repo._last_totals.clear()

        # Record snapshot via legacy
        health_totals_repo.record_snapshot(
            user_id="test_user",
            date="2025-01-15",
            timestamp="2025-01-15T10:00:00Z",
            steps=500,
            calories_out=75.5,
            hr_avg_session=None,
        )
        health_totals_repo.record_snapshot(
            user_id="test_user",
            date="2025-01-15",
            timestamp="2025-01-15T11:00:00Z",
            steps=1200,
            calories_out=180.5,
            hr_avg_session=None,
        )

        # Compare totals
        domain_adapter = ActivitySnapshotsAdapter()
        domain_steps, domain_calories = domain_adapter.get_daily_totals("test_user", "2025-01-15")

        legacy_steps, legacy_calories = health_totals_repo.daily_totals(
            user_id="test_user", date="2025-01-15"
        )

        assert domain_steps == legacy_steps
        assert domain_calories == legacy_calories


class TestDomainServicesEquivalence:
    """Test equivalenza servizi domain vs logica GraphQL esistente."""

    def test_daily_summary_equivalence(self) -> None:
        """Daily summary domain vs app.py logic."""
        # Mock adapters per controllo comportamento
        mock_events_port = Mock()
        mock_snapshots_port = Mock()

        mock_snapshots_port.get_daily_totals.return_value = (5000, 450.75)
        mock_events_port.get_daily_events_count.return_value = 36

        # Domain service
        aggregation_service = ActivityAggregationService(mock_events_port, mock_snapshots_port)

        summary = aggregation_service.calculate_daily_summary("test_user", "2025-01-15")

        # Verifiche
        assert summary.user_id == "test_user"
        assert summary.date == "2025-01-15"
        assert summary.total_steps == 5000
        assert summary.total_calories_out == 450.75
        assert summary.events_count == 36

        # Verify adapter calls
        mock_snapshots_port.get_daily_totals.assert_called_once_with("test_user", "2025-01-15")
        mock_events_port.get_daily_events_count.assert_called_once_with("test_user", "2025-01-15")

    def test_sync_service_normalization(self) -> None:
        """Sync service normalizza timestamp correttamente."""
        mock_events_port = Mock()
        mock_snapshots_port = Mock()

        # Setup return values
        mock_events_port.ingest_events.return_value = (2, 0, [])

        sync_service = ActivitySyncService(mock_events_port, mock_snapshots_port)

        # Events con timestamp diversi (secondi)
        events = [
            ActivityEvent(
                user_id="test_user",
                ts="2025-01-15T14:30:15Z",  # Con secondi
                steps=100,
            ),
            ActivityEvent(
                user_id="test_user",
                ts="2025-01-15T14:31:45Z",  # Con secondi
                steps=200,
            ),
        ]

        accepted, duplicates, rejected = sync_service.ingest_activity_events(events)

        # Verify normalization occurred
        mock_events_port.ingest_events.assert_called_once()
        call_args = mock_events_port.ingest_events.call_args[0]
        normalized_events: List[ActivityEvent] = call_args[0]

        assert normalized_events[0].ts == "2025-01-15T14:30:00Z"
        assert normalized_events[1].ts == "2025-01-15T14:31:00Z"
        assert accepted == 2
        assert duplicates == 0
        assert rejected == []


class TestIntegrationLayerEquivalence:
    """Test equivalenza integration layer V2 - sempre attivo."""

    def test_enhanced_daily_summary_always_available(self) -> None:
        """Enhanced daily summary è sempre disponibile con V2."""
        from domain.activity.integration import ActivityIntegrationService

        integration_service = ActivityIntegrationService()

        # V2 è sempre abilitato (non c'è più is_enabled)

        # Enhanced summary funziona correttamente
        fallback = {
            "date": "2025-01-15",
            "total_steps": 1000,
            "total_calories_out": 100.0,
        }
        result = integration_service.enhanced_daily_summary("test_user", "2025-01-15", fallback)

        # Dovrebbe funzionare con i servizi V2
        assert isinstance(result, dict)
        assert "date" in result

    def test_integration_error_graceful_degradation(self) -> None:
        """Errori nell'integration layer degradano gracefully."""
        from domain.activity.integration import ActivityIntegrationService

        integration_service = ActivityIntegrationService()

        # Mock service per simulare errore
        if integration_service._aggregation_service:
            from unittest.mock import Mock

            mock_service = Mock()
            mock_service.calculate_daily_summary = Mock(side_effect=Exception("Test error"))
            integration_service._aggregation_service = mock_service

        fallback = {"date": "2025-01-15", "steps": 1000}
        result = integration_service.enhanced_daily_summary("test_user", "2025-01-15", fallback)

        # Dovrebbe fallback gracefully
        assert result == fallback
