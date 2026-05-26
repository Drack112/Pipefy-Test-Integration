import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from strawberry.fastapi import GraphQLRouter

from app.config import settings
from app.db import get_db
from app.graphql.schema import schema
from app.shared import get_logger, setup_logging
from app.webhooks.router import router as webhooks_router

logger = get_logger(__name__)


async def get_context(db: Session = Depends(get_db)):
    return {"db": db}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging(debug=settings.debug, env=settings.app_env)
    logger.info(
        "starting app env=%s version=%s", settings.app_env, settings.app_version
    )
    try:
        Path("schema.graphql").write_text(schema.as_str())
        logger.info("schema.graphql generated")
    except OSError as exc:
        logger.warning("could not write schema.graphql: %s", exc)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_headers=settings.cors_allowed_headers,
        allow_methods=["*"],
    )

    graphql_app = GraphQLRouter(schema, context_getter=get_context)
    app.include_router(graphql_app, prefix="/graphql")
    app.include_router(webhooks_router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
