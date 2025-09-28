"""Pytest configuration & global fixtures for backend tests.

Fixture principali:

* metrics_reset (autouse, function scope): assicura isolamento metrico
  chiamando `metrics.ai_meal_photo.reset_all()` prima e dopo ogni test.

Razionale:
I test sulle metriche (e qualunque altro test che indirettamente
invoca l'analisi foto pasto) incrementano counter/histogram condivisi
in memoria. Senza reset potremmo avere dipendenze dall'ordine di
esecuzione (es. il primo test presume contatori a zero). La fixture
autouse garantisce un ambiente pulito, rendendo ogni test indipendente.

Design note:
- Usiamo try/finally per assicurare il reset anche se il test fallisce.
- Resettiamo sia prima che dopo per ulteriore sicurezza (evita leak
  da test eseguiti prima in una stessa sessione di raccolta).
- Evitiamo import pesanti a livello moduli: import locale dentro la
  fixture → tempi di startup invariati.
"""

from __future__ import annotations

from typing import Iterator, Callable, Any, TYPE_CHECKING, cast

if TYPE_CHECKING:  # import solo per typing
    from httpx import AsyncClient, ASGITransport  # pragma: no cover

try:  # pragma: no cover - mypy può non risolvere pytest
    import pytest
except Exception:  # pragma: no cover

    class _PytestStub:
        def fixture(
            self, *args: Any, **kwargs: Any
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn

            return deco

    pytest = _PytestStub()  # type: ignore


@pytest.fixture(autouse=True)
def metrics_reset() -> Iterator[None]:
    """Reset globale metriche AI meal photo per ogni test.

    Sequenza:
    1. reset iniziale (stato noto)
    2. esegue il test
    3. reset finale (pulisce eventuali side-effect)
    """
    from metrics.ai_meal_photo import reset_all  # import deferito

    reset_all()
    try:
        yield
    finally:
        reset_all()


@pytest.fixture(scope="session")
def asgi_transport() -> "ASGITransport":
    """ASGI transport riusabile per tutti i test HTTP.

    Nota: niente parametro lifespan per compatibilità con la versione httpx
    installata.
    """
    from httpx import ASGITransport
    from app import app
    # FastAPI è ASGI compatibile, cast esplicito per placare mypy
    return ASGITransport(app=cast(Any, app))


@pytest.fixture()
def client(asgi_transport: "ASGITransport") -> Iterator["AsyncClient"]:
    """Client HTTP sync fixture che fornisce un AsyncClient.

    In modalità pytest-asyncio strict un test async può usare una fixture
    sincrona che restituisce un oggetto async-safe. Gestiamo l'apertura
    e chiusura del client manualmente.
    """
    import anyio
    from httpx import AsyncClient

    async def _make():
        return AsyncClient(transport=asgi_transport, base_url="http://test")

    client_obj: AsyncClient = anyio.run(_make)

    try:
        yield client_obj
    finally:
        anyio.run(client_obj.aclose)
