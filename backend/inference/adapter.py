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

from typing import List, Optional, Protocol, Tuple
import os
import hashlib
import time
import random
import json

from ai_models.meal_photo_models import MealPhotoItemPredictionRecord
from ai_models.meal_photo_prompt import (
    parse_and_validate_with_stats,
    parse_and_validate_v3,
    ParseError as MealPhotoParseError,
    ParseStats,
    ParsedItem,
)
from ai_models.nutrient_enrichment import NutrientEnrichmentService
from rules.category_profiles import (
    NormalizedItem,
    normalize as normalize_items,
)
from .vision_client import (
    call_openai_vision,
    VisionTimeoutError,
    VisionTransientError,
    VisionCallError,
)

try:  # metrics opzionali (non presenti nell'immagine slim)
    from metrics.ai_meal_photo import (
        record_fallback,  # noqa: F401
        record_error,  # noqa: F401
        time_analysis,  # noqa: F401
        record_parse_success,  # noqa: F401
        record_parse_failed,  # noqa: F401
        record_parse_clamped,  # noqa: F401
        record_enrichment_success,  # noqa: F401
        record_enrichment_latency_ms,  # noqa: F401
        record_macro_fill_ratio,  # noqa: F401
    )
except ImportError:  # pragma: no cover - fallback leggero
    from contextlib import contextmanager
    from typing import Iterator, Any

    def record_enrichment_success(*args: Any, **kwargs: Any) -> None:  # type: ignore # noqa
        pass

    def record_enrichment_latency_ms(*args: Any, **kwargs: Any) -> None:  # type: ignore # noqa
        pass

    def record_macro_fill_ratio(*args: Any, **kwargs: Any) -> None:  # type: ignore # noqa
        pass

    @contextmanager
    def time_analysis(
        phase: str,
        *,
        source: Optional[str] = None,
        status_on_exit: Optional[str] = None,
    ) -> Iterator[None]:
        yield

    def record_fallback(reason: str, *, source: Optional[str] = None) -> None:
        return None

    def record_error(code: str, *, source: Optional[str] = None) -> None:
        return None

    # Metriche parse no-op
    def record_parse_success(*args, **kwargs):  # type: ignore
        return None

    def record_parse_failed(*args, **kwargs):  # type: ignore
        return None

    def record_parse_clamped(*args, **kwargs):  # type: ignore
        return None


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
        dish_hint: Optional[str] = None,
    ) -> List[MealPhotoItemPredictionRecord]: ...

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
        dish_hint: Optional[str] = None,
    ) -> List[MealPhotoItemPredictionRecord]:  # pragma: no cover wrapper
        import asyncio

        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
                dish_hint=dish_hint,
            )
        )


class StubAdapter:
    """Adapter deterministico che replica lo stub fisso attuale."""

    _ITEMS = [
        MealPhotoItemPredictionRecord(
            label="mixed salad",
            display_name="Insalata mista",
            confidence=0.92,
            quantity_g=150.0,
            calories=60,
            protein=2.0,
            carbs=8.0,
            fat=2.0,
            fiber=3.0,
        ),
        MealPhotoItemPredictionRecord(
            label="chicken breast",
            display_name="Petto di pollo",
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
        dish_hint: Optional[str] = None,
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
        dish_hint: Optional[str] = None,
    ) -> List[MealPhotoItemPredictionRecord]:
        """Wrapper sync temporaneo (deprecando in futuro)."""
        import asyncio

        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
                dish_hint=dish_hint,
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
        dish_hint: Optional[str] = None,
    ) -> List[MealPhotoItemPredictionRecord]:
        with time_analysis(phase=self.name(), source=self.name()):
            base = await StubAdapter().analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
                dish_hint=dish_hint,
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
                        label="water",
                        display_name="Acqua",
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
        dish_hint: Optional[str] = None,
    ) -> List[MealPhotoItemPredictionRecord]:
        import asyncio

        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
                dish_hint=dish_hint,
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

    Implementazione attuale: mock che attende fino a `REMOTE_LATENCY_MS`.
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
        dish_hint: Optional[str] = None,
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
                        dish_hint=dish_hint,
                    )
                return await StubAdapter().analyze_async(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                    dish_hint=dish_hint,
                )
            base_items = (
                await HeuristicAdapter().analyze_async(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                    dish_hint=dish_hint,
                )
                if _flag_enabled(os.getenv("AI_HEURISTIC_ENABLED"))
                else await StubAdapter().analyze_async(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                    dish_hint=dish_hint,
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
        dish_hint: Optional[str] = None,
    ) -> List[MealPhotoItemPredictionRecord]:
        import asyncio

        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
                dish_hint=dish_hint,
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

    async def _real_model_output(
        self, photo_url: Optional[str], dish_hint: Optional[str] = None
    ) -> str:
        if not _flag_enabled(os.getenv("AI_GPT4V_REAL_ENABLED")):
            raise MealPhotoParseError("REAL_DISABLED")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise MealPhotoParseError("MISSING_API_KEY")

        # Base prompt v3 (intelligente con etichette inglesi per USDA)
        from ai_models.meal_photo_prompt import generate_prompt_v3

        prompt = generate_prompt_v3()

        # Aggiungi suggerimento se presente
        if dish_hint and dish_hint.strip():
            prompt += f" Suggerimento: potrebbe essere {dish_hint.strip()}."

        # Log del prompt per debugging
        import logging

        logger = logging.getLogger("ai.meal_photo.gpt4v")

        # Log completo con dettagli visibili
        photo_short = photo_url[:50] + "..." if photo_url and len(photo_url) > 50 else photo_url
        hint_info = f" | dishHint: '{dish_hint}'" if dish_hint else " | dishHint: None"

        logger.info(f"GPT-4V prompt generated - Length: {len(prompt)} chars{hint_info}")
        logger.info(f"Photo URL: {photo_short}")
        logger.info(f"Full prompt: {prompt}")

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
        # Legge API key dall'ambiente per permettere disabilitazione nei test
        usda_key = os.getenv("AI_USDA_API_KEY")
        if usda_key == "":
            usda_key = None  # Disabilita esplicitamente USDA
        enrichment_service = NutrientEnrichmentService(usda_api_key=usda_key)
        self.enrichment_service = enrichment_service

    # Normalization feature flag:
    # AI_NORMALIZATION_MODE (off|dry_run|enforce)

    async def analyze_async(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
        dish_hint: Optional[str] = None,
    ) -> List[MealPhotoItemPredictionRecord]:
        with time_analysis(phase=self.name(), source=self.name()):
            try:
                raw_text = await self._real_model_output(photo_url, dish_hint)
            except MealPhotoParseError as exc:
                self.last_fallback_reason = str(exc)
                record_fallback(self.last_fallback_reason, source=self.name())
                raw_text = self._simulate_model_output()
            # Parsing V3 con fallback al legacy (fallback a stub se errore parsing)
            parsed: List[ParsedItem] = []
            stats: Optional[ParseStats] = None
            dish_title: Optional[str] = None

            # Prova prima il parsing V3 (con dish_title e etichette inglesi)
            try:
                dish_title, parsed = parse_and_validate_v3(raw_text)
                # Crea stats di successo per V3
                stats = ParseStats(
                    success=True,
                    items_count=len(parsed),
                    clamped_count=0,
                    prompt_version=3,  # V3
                )
            except MealPhotoParseError:
                # Fallback al parsing legacy
                parsed, stats = parse_and_validate_with_stats(raw_text)
            if not stats.success:
                reason = "PARSE_" + (stats.raw_error or "UNKNOWN")
                self.last_fallback_reason = reason
                record_fallback(reason, source=self.name())
                record_error(reason, source=self.name())
                record_parse_failed(
                    stats.raw_error or "UNKNOWN",
                    prompt_version=stats.prompt_version,
                    source=self.name(),
                )
                return await StubAdapter().analyze_async(
                    user_id=user_id,
                    photo_id=photo_id,
                    photo_url=photo_url,
                    now_iso=now_iso,
                    dish_hint=dish_hint,
                )
            # Metriche parse success
            record_parse_success(
                stats.items_count,
                prompt_version=stats.prompt_version,
                source=self.name(),
            )
            record_parse_clamped(
                stats.clamped_count,
                prompt_version=stats.prompt_version,
                source=self.name(),
            )

            # Enrichment nutrizionale (Phase 2)
            start_enrich = time.perf_counter()
            enr_svc = self.enrichment_service
            enrichment_results = await enr_svc.enrich_parsed_items(parsed)
            enrich_time_ms = (time.perf_counter() - start_enrich) * 1000.0

            # Metriche enrichment
            enrich_stats = enr_svc.get_stats()
            record_enrichment_success(
                items_count=len(parsed),
                hit_usda=enrich_stats["hit_usda"],
                hit_default=enrich_stats["hit_default"],
                source=self.name(),
            )
            record_enrichment_latency_ms(enrich_time_ms, source=self.name())

            out: List[MealPhotoItemPredictionRecord] = []
            filled_fields_total = 0
            total_fields_possible = 0

            for p, enrich in zip(parsed, enrichment_results):
                # Campi macro: protein, carbs, fat, fiber
                macro_fields = [
                    enrich.protein if enrich.success else None,
                    enrich.carbs if enrich.success else None,
                    enrich.fat if enrich.success else None,
                    getattr(enrich, "fiber", None) if enrich.success else None,
                ]
                filled_fields_total += sum(1 for f in macro_fields if f is not None)
                total_fields_possible += len(macro_fields)

                out.append(
                    MealPhotoItemPredictionRecord(
                        label=p.label,
                        display_name=p.display_name,
                        confidence=p.confidence,
                        quantity_g=p.quantity_g,
                        calories=p.calories,
                        protein=macro_fields[0],
                        carbs=macro_fields[1],
                        fat=macro_fields[2],
                        fiber=macro_fields[3],
                        sugar=enrich.sugar if enrich.success else None,
                        sodium=enrich.sodium if enrich.success else None,
                        enrichment_source=enrich.source if enrich.success else None,
                    )
                )

            # Macro fill ratio metric (Phase 1 pending)
            record_macro_fill_ratio(
                filled_fields=filled_fields_total,
                total_fields=total_fields_possible,
                source=self.name(),
            )
            # --- Normalization Phase 2.1 ---
            norm_mode = os.getenv("AI_NORMALIZATION_MODE", "off").strip().lower()
            try:
                norm_items = [
                    NormalizedItem(
                        label=o.label,
                        quantity_g=float(o.quantity_g or 0.0),
                        calories=(float(o.calories) if o.calories is not None else None),
                        protein=o.protein,
                        carbs=o.carbs,
                        fat=o.fat,
                        fiber=o.fiber,
                        sugar=o.sugar,
                        sodium=o.sodium,
                        enrichment_source=o.enrichment_source,
                    )
                    for o in out
                ]
                norm_result = normalize_items(items=norm_items, mode=norm_mode)
                if norm_mode == "enforce":
                    # Apply back normalized values
                    for o, n in zip(out, norm_result.items):
                        o.label = n.label
                        o.quantity_g = n.quantity_g
                        if n.calories is not None:
                            try:
                                o.calories = int(round(n.calories))
                            except Exception:
                                pass
                        o.protein = n.protein
                        o.carbs = n.carbs
                        o.fat = n.fat
                        o.fiber = n.fiber
                        o.sugar = n.sugar if n.sugar is not None else o.sugar
                        o.sodium = n.sodium if n.sodium is not None else o.sodium
                        o.enrichment_source = n.enrichment_source or o.enrichment_source
                        if n.calorie_corrected:
                            o.calorie_corrected = True
                else:
                    # In dry_run/off copia solo sugar/sodium se assenti
                    for o, n in zip(out, norm_result.items):
                        if o.sugar is None and n.sugar is not None:
                            o.sugar = n.sugar
                        if o.sodium is None and n.sodium is not None:
                            o.sodium = n.sodium
                # Metrics placeholder (future): corrections & clamps stats
                setattr(
                    self,
                    "_last_normalization_stats",
                    {
                        "mode": norm_result.mode,
                        "corrections": norm_result.corrections,
                        "garnish_clamped": norm_result.garnish_clamped,
                        "macro_recomputed": norm_result.macro_recomputed,
                    },
                )
            except Exception:
                # Fail-safe: never break analysis for normalization issues
                setattr(self, "_last_normalization_error", True)
            # Dish name: usa dish_title italiano se disponibile
            dish: Optional[str] = None
            try:
                # Priorità 1: dish_title dal GPT-4V (in italiano)
                if dish_title and dish_title.strip():
                    dish = dish_title.strip()
                else:
                    # Priorità 2: euristica basata su label inglesi
                    dish = self._generate_dish_name(parsed, out)
            except Exception:
                dish = None
            if not dish:
                # Fallback semplice: primi 3 label originali
                base_labels = [p.label.lower() for p in parsed[:3]]
                dish = " ".join(base_labels) if base_labels else None
            setattr(self, "_last_dish_name", dish)
            return out

    # --- Dish name generation heuristic ---
    def _generate_dish_name(
        self,
        parsed: List[ParsedItem],
        items: List[MealPhotoItemPredictionRecord],
    ) -> Optional[str]:
        if not parsed:
            return None
        garnish = {"parsley", "basil", "basilico", "limone", "lemon", "lime"}
        ranked: List[Tuple[str, float]] = []
        for p, it in zip(parsed, items):
            label = p.label.lower().strip()
            score = 0.0
            if it.calories is not None:
                score = float(it.calories)
            else:
                # Macro fallback
                if it.protein:
                    score += it.protein * 4
                if it.carbs:
                    score += it.carbs * 4
                if it.fat:
                    score += it.fat * 9
                if score == 0 and p.quantity_g:
                    score = p.quantity_g
            ranked.append((label, score))
        # Filtra garnish
        core = [r for r in ranked if r[0] not in garnish]
        if not core:
            core = ranked
        core.sort(key=lambda t: t[1], reverse=True)
        top = [c[0] for c in core[:3]]
        if not top:
            return None
        # De-pluralization naive
        norm: List[str] = []
        for t in top:
            w = t
            if w.endswith("es") and len(w) > 4:
                w = w[:-2]
            elif w.endswith("s") and len(w) > 3:
                w = w[:-1]
            if not norm or norm[-1] != w:
                norm.append(w)
        name = " ".join(norm)
        if len(norm) > 1:
            name = f"{name} bowl"
        return name or None

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
        dish_hint: Optional[str] = None,
    ) -> List[MealPhotoItemPredictionRecord]:
        import asyncio

        return asyncio.run(
            self.analyze_async(
                user_id=user_id,
                photo_id=photo_id,
                photo_url=photo_url,
                now_iso=now_iso,
                dish_hint=dish_hint,
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
