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

from typing import Optional

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
    raise NotImplementedError("Real vision call non ancora implementata")
