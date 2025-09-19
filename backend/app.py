from fastapi import FastAPI
from fastapi.responses import JSONResponse
import strawberry
from strawberry.fastapi import GraphQLRouter
import datetime

APP_VERSION = "0.1.2"

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "nutrifit-backend alive"

    @strawberry.field
    def server_time(self) -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

schema = strawberry.Schema(query=Query)

app = FastAPI(title="Nutrifit Backend Subgraph", version=APP_VERSION)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/version")
async def version():
    return {"version": APP_VERSION}

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
