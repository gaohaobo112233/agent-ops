from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import engine, Base
from app.models import server, task  # noqa: F401 — register models
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.servers import router as servers_router
from app.api.tasks import router as tasks_router
from app.api.monitor import router as monitor_router
from app.api.promql import router as promql_router
from app.api.rollback import router as rollback_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(servers_router)
app.include_router(tasks_router)
app.include_router(monitor_router)
app.include_router(promql_router)
app.include_router(rollback_router)


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok"}
