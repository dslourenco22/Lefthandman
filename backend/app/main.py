"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import hash_password
from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth, export, jobs, ranking, resumes


def _bootstrap_admin() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(
                email=settings.BOOTSTRAP_ADMIN_EMAIL,
                full_name="System Administrator",
                role="admin",
                hashed_password=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
            ))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _bootstrap_admin()
    yield


app = FastAPI(
    title="Omni Control Resume Ranking API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(ranking.router)
app.include_router(export.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
