"""Inference Adapter abstraction per Meal Photo Analysis (Fase 1 groundwork).

Obiettivo: isolare la generazione delle predictions (oggi stub) dal repository
e futura orchestrazione. Permette di:
* Inserire heuristic / remote model senza refactor repository
* Aggiungere metriche e timing attorno all'adapter
* Selezionare implementazione via feature flag ambientale

API minimale per Fase 0→1. Potrà estendersi (portion inference, nutrient
enrichment, fallback chain).
"""

from __future__ import annotations

from typing import List, Optional, Protocol
import os
import hashlib
import time
import random

from ai_models.meal_photo_models import MealPhotoItemPredictionRecord


class InferenceAdapter(Protocol):
    def name(self) -> str:  # identificatore adapter per logging/metrics
        ...

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        """Produce lista di predictions (stub/heuristic/model).
            Requisiti baseline:
        * Non sollevare eccezioni per input vuoti (fallback interno)
        * Restituire ≥1 item (se nessun rilevamento usare placeholder generico)
            * Confidence in range [0,1]
        """
        ...


class StubAdapter:
    """Adapter deterministico che replica lo stub fisso attuale."""

    _ITEMS = [
        MealPhotoItemPredictionRecord(
            label="Insalata mista",
            confidence=0.92,
            quantity_g=150.0,
            calories=60,
            protein=2.0,
            carbs=8.0,
            fat=2.0,
            fiber=3.0,
        ),
        MealPhotoItemPredictionRecord(
            label="Petto di pollo",
            confidence=0.88,
            quantity_g=120.0,
            calories=198,
            protein=35.0,
            carbs=0.0,
            fat=4.0,
        ),
    ]

    def name(self) -> str:
        return "stub"

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        return list(self._ITEMS)


class HeuristicAdapter:
    """Adapter semplice heuristic (fase 1 minimale).

    Regole:
    - Se photo_id termina con numero pari → aumenta porzione del secondo item
    - Aggiunge un terzo item "Acqua" se url contiene 'water'
    Confidence calcolata in base a semplici pesi.
    """

    def name(self) -> str:  # pragma: no cover (semplice)
        return "heuristic"

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        base = StubAdapter().analyze(
            user_id=user_id,
            photo_id=photo_id,
            photo_url=photo_url,
            now_iso=now_iso,
        )
        items = list(base)
        even = False
        if photo_id and photo_id[-1].isdigit():
            even = int(photo_id[-1]) % 2 == 0
        if even and len(items) > 1 and items[1].quantity_g:
            # aumenta porzione secondo item
            items[1].quantity_g = items[1].quantity_g * 1.15  # tipo euristica
            items[1].confidence = min(1.0, items[1].confidence + 0.03)
        if photo_url and "water" in photo_url.lower():
            items.append(
                MealPhotoItemPredictionRecord(
                    label="Acqua",
                    confidence=0.75,
                    quantity_g=200.0,
                    calories=0,
                )
            )
        return items


# NOTE: le variabili d'ambiente sono lette dinamicamente in
# get_active_adapter per consentire ai test di mutarle a runtime
# senza ri-importare il modulo.


class RemoteModelAdapter:
    """Scheletro adapter per inference remota (Fase 2).

    Obiettivi:
    * Simulare chiamata esterna con timeout.
    * Applicare fallback automatico (heuristic → stub) se timeout o errore.
    * Non sollevare eccezioni verso il repository (robustezza UX).

    Implementazione attuale: mock che attende fino a `REMOTE_LATENCY_MS` e
    genera piccola variazione sulle quantità. Se la latenza simulata supera
    `REMOTE_TIMEOUT_MS` viene attivato fallback.

    Variabili ambiente supportate:
    * REMOTE_TIMEOUT_MS (default 1200)
    * REMOTE_LATENCY_MS (default 600)
    * REMOTE_FAIL_RATE (default 0.0)  # probabilità di fallire la chiamata
    * REMOTE_JITTER_MS (default 150)
    """

    def __init__(self) -> None:
        self.timeout_ms = int(os.getenv("REMOTE_TIMEOUT_MS", "1200"))
        self.base_latency_ms = int(os.getenv("REMOTE_LATENCY_MS", "600"))
        self.jitter_ms = int(os.getenv("REMOTE_JITTER_MS", "150"))
        self.fail_rate = float(os.getenv("REMOTE_FAIL_RATE", "0.0"))

    def name(self) -> str:  # pragma: no cover semplice
        return "model"

    def _simulate_remote(self) -> bool:
        latency = self.base_latency_ms + random.randint(0, self.jitter_ms)
        time.sleep(latency / 1000.0)
        if latency > self.timeout_ms:
            return False
        if random.random() < self.fail_rate:
            return False
        return True

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        # Prima prova a simulare remote; se fallisce fallback
        ok = self._simulate_remote()
        if not ok:
            # fallback a heuristic se flag attivo, altrimenti stub
            if _flag_enabled(os.getenv("AI_HEURISTIC_ENABLED")):
                return HeuristicAdapter().analyze(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                )
            return StubAdapter().analyze(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
        # Simulazione risposta "più raffinata" partendo dalla
        # heuristic/stub base
        base_items = (
            HeuristicAdapter().analyze(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
            if _flag_enabled(os.getenv("AI_HEURISTIC_ENABLED"))
            else StubAdapter().analyze(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
        )
        # Piccola variazione: +5% quantity se presente
        for it in base_items:
            if it.quantity_g:  # type: ignore[truthy-bool]
                it.quantity_g = it.quantity_g * 1.05
                it.confidence = min(1.0, it.confidence + 0.04)
        return base_items


def _flag_enabled(value: Optional[str]) -> bool:
    if not value:
        return False
    return value in {"1", "true", "TRUE", "on", "yes", "Y"}


def get_active_adapter() -> InferenceAdapter:
    # Lettura runtime flags
    remote_flag = os.getenv("AI_REMOTE_ENABLED")
    heuristic_flag = os.getenv("AI_HEURISTIC_ENABLED")
    if _flag_enabled(remote_flag):
        return RemoteModelAdapter()
    if _flag_enabled(heuristic_flag):
        return HeuristicAdapter()
    return StubAdapter()


def hash_photo_reference(
    photo_id: Optional[str],
    photo_url: Optional[str],
) -> str:
    """Hash stabile (sha256 trunc) di riferimenti foto per caching/idempotenza.
    Non usato ancora per la chiave principale (compat mantenuta) ma pronto.
    """
    basis = f"{photo_id or ''}|{photo_url or ''}".encode("utf-8")
    return hashlib.sha256(basis).hexdigest()[:16]
