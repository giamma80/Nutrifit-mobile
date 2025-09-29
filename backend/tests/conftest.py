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
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
