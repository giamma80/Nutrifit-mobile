import pytest
import pytest_asyncio
from typing import Generator, AsyncIterator
from metrics.ai_meal_photo import reset_all
from httpx import AsyncClient, ASGITransport

# Import esplicito per prevenire PendingDeprecationWarning (best effort)
try:  # pragma: no cover
    import python_multipart  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover
    # Non bloccare i test se il pacchetto non è installato
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
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        yield ac
