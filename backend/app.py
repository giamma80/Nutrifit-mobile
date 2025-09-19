from fastapi import FastAPI
import strawberry
from strawberry.fastapi import GraphQLRouter
import datetime
import os
from typing import Final, Any

# Versione letta da env (Docker build ARG -> ENV APP_VERSION)
APP_VERSION = os.getenv("APP_VERSION", "0.0.0-dev")


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "nutrifit-backend alive"

    @strawberry.field
    def server_time(self) -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

    @strawberry.field
    def health(self) -> str:
        # Placeholder per future verifiche (DB, servizi, ecc.)
        return "ok"


schema = strawberry.Schema(query=Query)

app = FastAPI(title="Nutrifit Backend Subgraph", version=APP_VERSION)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
async def version() -> dict[str, str]:
    return {"version": APP_VERSION}


graphql_app: Final[GraphQLRouter[Any, Any]] = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
