import pytest
import pytest_asyncio
from typing import Generator, AsyncIterator
from metrics.ai_meal_photo import reset_all
from httpx import AsyncClient, ASGITransport
from typing import cast, Any

# Import esplicito per prevenire PendingDeprecationWarning (best effort)
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    # Placeholder: import opzionale rimosso per evitare errori mypy se assente
    pass

from app import app  # FastAPI app con schema GraphQL


@pytest.fixture(autouse=True)
def _clear_ai_env() -> Generator[None, None, None]:
    """Pulisce variabili AI_* e OPENAI_* prima di ogni test.

    Evita che valori presenti in .env (es. AI_MEAL_PHOTO_MODE=gpt4v)
    influenzino test che si aspettano adapter default. I test che
    necessitano di un valore specifico lo impostano con monkeypatch.setenv.
    """
    import os

    to_clear = [
        "AI_MEAL_PHOTO_MODE",
        "AI_GPT4V_REAL_ENABLED",
        "OPENAI_API_KEY",
        "OPENAI_VISION_MODEL",
    ]
    for k in to_clear:
        if k in os.environ:
            del os.environ[k]
    try:
        yield
    finally:
        # Non ripristiniamo i valori (ambiente test isolato); la suite intera
        # resta con stato pulito, ma manteniamo la struttura se servisse.
        pass


@pytest.fixture(autouse=True)
def _reset_metrics() -> Generator[None, None, None]:
    """Reset metriche prima e dopo ogni test per isolamento."""
    reset_all()
    yield
    reset_all()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Client HTTP asincrono per test GraphQL/REST.

    Usa httpx.AsyncClient con ASGITransport esplicito (scorciatoia app=
    deprecata) e base_url fittizia per coerenza nelle richieste relative.
    """
    # Cast a Any per soddisfare la firma attesa (FastAPI è compatibile ASGI)
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac
