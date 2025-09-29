import pytest
from typing import Generator, AsyncIterator
from metrics.ai_meal_photo import reset_all
from httpx import AsyncClient

from app import app  # FastAPI app con schema GraphQL


@pytest.fixture(autouse=True)
def _reset_metrics() -> Generator[None, None, None]:
    """Reset metriche prima e dopo ogni test per isolamento."""
    reset_all()
    yield
    reset_all()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Client HTTP asincrono per test GraphQL/REST.

    Usa httpx.AsyncClient con montato l'app FastAPI in-process per evitare
    dipendenze da server esterno. base_url fittizia necessaria per httpx.
    """
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
