from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI

from server.app.core.database import init_db
from server.app.api.v1 import enroll

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    yield

app = FastAPI(
    title="SensiWatch Enterprise",
    description="Headless screen-monitoring platform backend",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(enroll.router, prefix="/api/v1", tags=["Enrollment"])