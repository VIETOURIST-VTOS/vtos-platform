"""VTOS API – điểm vào FastAPI."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import SessionLocal, engine, Base
from app.api.v1.routes import router
from app.api.v1.payments import router as payments_router
from app.api.v1.accounting import router as accounting_router
from app.api.v1.hr import router as hr_router
from app.api.v1.ops import router as ops_router
from app.services import rules as R
from app.services import accounting as ACC
from app.services.seed import seed_all


async def robot_loop():
    while True:
        await asyncio.sleep(600)
        try:
            db = SessionLocal(); R.run_robots(db); db.close()
        except Exception as e:  # noqa
            print("robot error", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENV == "dev":
        Base.metadata.create_all(engine)          # prod dùng alembic upgrade head
    db = SessionLocal()
    try:
        R.seed_params(db)
        ACC.seed_accounts(db)
        if settings.SEED_DEMO:
            seed_all(db)
    finally:
        db.close()
    task = asyncio.create_task(robot_loop())
    yield
    task.cancel()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan,
              docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(payments_router)
app.include_router(accounting_router)
app.include_router(hr_router)
app.include_router(ops_router)


@app.get("/", include_in_schema=False)
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/api/docs"}
