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
import json

from ai_models.meal_photo_models import MealPhotoItemPredictionRecord
from ai_models.meal_photo_prompt import (
    parse_and_validate,  # noqa: F401
    ParseError as MealPhotoParseError,  # noqa: F401
)
from .vision_client import (
    call_openai_vision,
    VisionTimeoutError,
    VisionTransientError,
    VisionCallError,
)
from metrics.ai_meal_photo import record_fallback, record_error, time_analysis


class InferenceAdapter(Protocol):
    """Protocol aggiornato: supporta metodo asincrono principale.

    analyze_async è la fonte di verità; analyze sync è wrapper
    temporaneo per compat (può bloccare l'event loop se usato dentro
    coroutine; verrà rimosso in una fase successiva).
    """

    def name(self) -> str:  # identificatore adapter per logging/metrics
        ...

    async def analyze_async(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        ...

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:  # pragma: no cover wrapper
        import asyncio
        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
        )


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

    async def analyze_async(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        with time_analysis(phase=self.name(), source=self.name()):
            return list(self._ITEMS)

    # Manteniamo analyze sync per compat
    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        """Wrapper sync temporaneo (deprecando in futuro)."""
        import asyncio
        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
        )


class HeuristicAdapter:
    """Adapter semplice heuristic (fase 1 minimale).

    Regole:
    - Se photo_id termina con numero pari → aumenta porzione del secondo item
    - Aggiunge un terzo item "Acqua" se url contiene 'water'
    Confidence calcolata in base a semplici pesi.
    """

    def name(self) -> str:  # pragma: no cover (semplice)
        return "heuristic"

    async def analyze_async(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        with time_analysis(phase=self.name(), source=self.name()):
            base = await StubAdapter().analyze_async(
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
                items[1].quantity_g = items[1].quantity_g * 1.15
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

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        import asyncio
        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
        )


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

    async def analyze_async(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        with time_analysis(phase=self.name(), source=self.name()):
            ok = self._simulate_remote()
            if not ok:
                if _flag_enabled(os.getenv("AI_HEURISTIC_ENABLED")):
                    return await HeuristicAdapter().analyze_async(
                        user_id=user_id,
                        photo_id=photo_id,
                        photo_url=photo_url,
                        now_iso=now_iso,
                    )
                return await StubAdapter().analyze_async(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                )
            base_items = (
                await HeuristicAdapter().analyze_async(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                )
                if _flag_enabled(os.getenv("AI_HEURISTIC_ENABLED"))
                else await StubAdapter().analyze_async(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                )
            )
            for it in base_items:
                q = it.quantity_g
                if q is not None and q > 0:
                    it.quantity_g = q * 1.05
                    it.confidence = min(1.0, it.confidence + 0.04)
            return base_items

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        import asyncio
        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
        )


class Gpt4vAdapter:
    """Adapter GPT-4 Vision (fase 1) con doppia modalità: reale o simulata.

    Modalità reale se:
      - AI_GPT4V_REAL_ENABLED abilitato
      - OPENAI_API_KEY presente
    Altrimenti simulazione deterministica basata sullo stub.
    Qualsiasi errore nella parte reale → fallback immediato a simulazione.
    Se parsing JSON fallisce → fallback a StubAdapter (coerenza UX).
    """

    def name(self) -> str:  # pragma: no cover semplice
        return "gpt4v"

    def _simulate_model_output(self) -> str:
        # Usa direttamente gli item statici dello StubAdapter per evitare
        # chiamata sync analyze() (che userebbe asyncio.run dentro event loop).
        items: List[MealPhotoItemPredictionRecord] = list(StubAdapter._ITEMS)
        parts = []
        for it in items:
            q = it.quantity_g or 100.0
            parts.append(
                {
                    "label": it.label,
                    "quantity": {"value": q, "unit": "g"},
                    "confidence": it.confidence,
                }
            )
        return json.dumps({"items": parts})

    async def _real_model_output(self, photo_url: Optional[str]) -> str:
        if not _flag_enabled(os.getenv("AI_GPT4V_REAL_ENABLED")):
            raise MealPhotoParseError("REAL_DISABLED")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise MealPhotoParseError("MISSING_API_KEY")
        prompt = (
            "Analizza la foto del pasto e "
            "restituisci SOLO JSON valido con schema "
            '{"items":[{"label":"string","quantity":'
            '{"value":<num>,"unit":"g|piece"},"confidence":<0-1>}]}'
        )
        try:
            return await call_openai_vision(
                image_url=photo_url,
                prompt=prompt,
                timeout_s=12.0,
            )
        except VisionTimeoutError as exc:
            raise MealPhotoParseError(f"TIMEOUT:{exc}") from exc
        except VisionTransientError as exc:
            raise MealPhotoParseError(f"TRANSIENT:{exc}") from exc
        except VisionCallError as exc:
            raise MealPhotoParseError(f"CALL_ERR:{exc}") from exc

    def __init__(self) -> None:
        self.last_fallback_reason: Optional[str] = None

    async def analyze_async(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        with time_analysis(phase=self.name(), source=self.name()):
            try:
                raw_text = await self._real_model_output(photo_url)
            except MealPhotoParseError as exc:
                self.last_fallback_reason = str(exc)
                record_fallback(self.last_fallback_reason, source=self.name())
                raw_text = self._simulate_model_output()
            try:
                parsed = parse_and_validate(raw_text)
            except MealPhotoParseError as exc:
                reason = f"PARSE_{str(exc)}"
                self.last_fallback_reason = reason
                record_fallback(reason, source=self.name())
                record_error(reason, source=self.name())
                return await StubAdapter().analyze_async(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                )
            out: List[MealPhotoItemPredictionRecord] = []
            for p in parsed:
                out.append(
                    MealPhotoItemPredictionRecord(
                        label=p.label,
                        confidence=p.confidence,
                        quantity_g=p.quantity_g,
                        calories=p.calories,
                    )
                )
            return out

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        import asyncio
        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
            )
        )


def _flag_enabled(value: Optional[str]) -> bool:
    if not value:
        return False
    return value in {"1", "true", "TRUE", "on", "yes", "Y"}


def get_active_adapter() -> InferenceAdapter:
    # Priorità nuova variabile unificata
    mode = os.getenv("AI_MEAL_PHOTO_MODE")
    if mode:
        m = mode.strip().lower()
        if m == "gpt4v":
            return Gpt4vAdapter()
        if m == "model":
            return RemoteModelAdapter()
        if m == "heuristic":
            return HeuristicAdapter()
        return StubAdapter()
    # Backward compatibility
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
