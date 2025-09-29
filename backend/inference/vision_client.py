"""Skeleton client per GPT-4 Vision (fase di hardening test).

Questo modulo astrae la chiamata al modello vision così da poter:
* Mockare facilmente nei test (success / parse error / timeout / transient)
* Introdurre retry / backoff in futuro senza toccare l'adapter
* Separare responsabilità: adapter orchestration vs raw model call

Per ora non effettua la chiamata reale: restituisce NotImplementedError se
invocato in modalità reale. I test useranno monkeypatch per sostituire
`call_openai_vision` con versioni controllate.
"""

from __future__ import annotations

from typing import Optional, Iterable, cast, List, Any
import asyncio
import time
import os
import logging

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from httpx import ReadTimeout, ConnectTimeout

__all__ = [
    "VisionTimeoutError",
    "VisionTransientError",
    "VisionCallError",
    "call_openai_vision",
]


class VisionCallError(Exception):
    """Errore generico nella chiamata vision (non parse)."""


class VisionTimeoutError(VisionCallError):
    """Timeout raggiunto durante la chiamata al modello vision."""


class VisionTransientError(VisionCallError):
    """Errore transiente (es. 5xx, connessione, ratelimit) recuperabile."""


async def call_openai_vision(
    *,
    image_url: Optional[str],
    prompt: str,
    timeout_s: float = 12.0,
) -> str:
    """Esegue la chiamata al modello GPT-4 Vision restituendo testo grezzo.

    Fase attuale: skeleton → i test monkeypatcheranno questa funzione.

    In una futura implementazione reale:
    - Costruzione payload messages (prompt + image_url)
    - Gestione timeout (asyncio.wait_for)
    - Mapping errori openai verso VisionTimeoutError / VisionTransientError
    - Logging strutturato con timing
    """
    start = time.perf_counter()
    logger = logging.getLogger("ai.vision")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise VisionCallError("OPENAI_API_KEY missing")
    # Se nessuna image_url viene fornita, trasformiamo in errore prevedibile
    if not image_url:
        raise VisionCallError("IMAGE_URL_MISSING")

    client = OpenAI(api_key=api_key)

    # Costruiamo i messages e li castiamo ad Iterable generico per mypy.
    # Per compat con SDK openai>=1.x usiamo struttura minimale e cast a Any.
    # L'SDK accetta dict conformi ai parametri ChatCompletion*; qui non
    # vogliamo replicare tutti i TypedDict generati.
    raw_messages: List[dict[str, Any]] = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]
    messages_any: Iterable[Any] = cast(Iterable[Any], raw_messages)

    async def _do_call() -> str:
        # L'SDK openai è sync: usiamo executor per non bloccare l'event loop.
        loop = asyncio.get_running_loop()

        def _sync_call() -> str:
            # model name configurabile? per ora fisso
            try:
                resp = client.chat.completions.create(
                    model=os.getenv(
                        "OPENAI_VISION_MODEL", "gpt-4o-mini"
                    ),
                    messages=messages_any,
                    temperature=0.0,
                )
            except (
                ConnectTimeout,
                ReadTimeout,
                APITimeoutError,
            ) as exc:  # network timeouts
                raise VisionTimeoutError(str(exc)) from exc
            except RateLimitError as exc:
                raise VisionTransientError(f"ratelimit:{exc}") from exc
            except APIError as exc:  # generico errore API
                code = getattr(exc, "status_code", None)
                # 5xx come transient
                if code and 500 <= int(code) < 600:
                    raise VisionTransientError(f"{code}:{exc}") from exc
                raise VisionCallError(str(exc)) from exc
            # Struttura attesa: choices[0].message.content
            try:
                content = resp.choices[0].message.content
            except Exception as exc:  # pragma: no cover (difesa extra)
                raise VisionCallError(f"invalid_response:{exc}") from exc
            if not content:
                raise VisionCallError("empty_content")
            return content

        return await loop.run_in_executor(None, _sync_call)

    try:
        raw = await asyncio.wait_for(_do_call(), timeout=timeout_s)
        return raw
    except asyncio.TimeoutError as exc:
        raise VisionTimeoutError("client_timeout") from exc
    finally:
        elapsed = (time.perf_counter() - start) * 1000.0
        logger.info(
            "vision.call",
            extra={
                "elapsed_ms": int(elapsed),
                "has_image": bool(image_url),
                "timeout_s": timeout_s,
            },
        )
