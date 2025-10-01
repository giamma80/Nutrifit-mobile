"""In-memory repository per analisi foto pasto (stub Fase 0).

Responsabilità (Fase 0):
* Registrare un'analisi generata in modo deterministico (no vera AI)
* Supportare idempotenza tramite idempotency_key
    (auto-derivata da photoId|photoUrl|user)
* Restituire sempre stato COMPLETED con predictions statiche
* Fornire conferma che genera MealRecord a partire dagli indici accettati

Fasi future potranno introdurre stati PENDING/FAILED e aggiornamenti asincroni.
"""

from __future__ import annotations

from typing import Optional, Dict, Tuple
import hashlib
import uuid
import logging
from contextlib import contextmanager
from ai_models.meal_photo_models import MealPhotoAnalysisRecord
from inference.adapter import get_active_adapter


@contextmanager
def time_analysis(*args, **kwargs):  # type: ignore
    """No-op metrics context.

    Il modulo `metrics` è escluso dall'immagine Docker per ridurre superfice
    e dipendenze: questo contextmanager sostituisce la raccolta di metriche
    senza introdurre branch logici nell'app.
    """
    yield


class InMemoryMealPhotoAnalysisRepository:
    def __init__(self) -> None:
        self._analyses: Dict[Tuple[str, str], MealPhotoAnalysisRecord] = {}
        self._idemp: Dict[Tuple[str, str], str] = {}

    def _auto_key(
        self,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
    ) -> str:
        basis = f"{user_id}|{photo_id or ''}|{photo_url or ''}".encode("utf-8")
        return "auto-" + hashlib.sha256(basis).hexdigest()[:16]

    async def create_or_get_async(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        idempotency_key: Optional[str],
        now_iso: str,
    ) -> MealPhotoAnalysisRecord:
        if idempotency_key is None:
            idempotency_key = self._auto_key(user_id, photo_id, photo_url)
            # In futuro potremmo sostituire _auto_key con
            # hash_photo_reference(photo_id, photo_url) per rendere evidente
            # la derivazione e riusare la funzione comune.
        key = (user_id, idempotency_key)
        existing_id = self._idemp.get(key)
        if existing_id:
            return self._analyses[(user_id, existing_id)]
        adapter = get_active_adapter()
        with time_analysis(phase=adapter.name(), source=adapter.name()):
            # Chiamata async primaria
            items = await adapter.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
        analysis_id = uuid.uuid4().hex
        rec = MealPhotoAnalysisRecord(
            id=analysis_id,
            user_id=user_id,
            status="COMPLETED",
            created_at=now_iso,
            source=adapter.name(),
            items=items,
            raw_json=None,
            idempotency_key_used=idempotency_key,
        )
        self._analyses[(user_id, analysis_id)] = rec
        self._idemp[key] = analysis_id
        logging.getLogger("ai.meal_photo").info(
            "analysis.created",
            extra={
                "user_id": user_id,
                "analysis_id": analysis_id,
                "items_count": len(items),
                "adapter": adapter.name(),
            },
        )
        return rec

    # Wrapper sync per compat (verrà rimosso in futuro)
    def create_or_get(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        idempotency_key: Optional[str],
        now_iso: str,
    ) -> MealPhotoAnalysisRecord:  # pragma: no cover semplice wrapper
        import asyncio

        return asyncio.run(
            self.create_or_get_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                idempotency_key=idempotency_key,
                now_iso=now_iso,
            )
        )

    def get(
        self,
        user_id: str,
        analysis_id: str,
    ) -> Optional[MealPhotoAnalysisRecord]:
        return self._analyses.get((user_id, analysis_id))


meal_photo_repo = InMemoryMealPhotoAnalysisRepository()
