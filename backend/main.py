# main.py -- FastAPI application entry point.
# Depends on: config.py, db/database.py, all api/ routers
# Depended on by: uvicorn (run via `uvicorn backend.main:app`)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import init_db

app = FastAPI(
    title="Falsification Engine",
    description="Global macro hypothesis generation, adversarial evaluation, and mechanical conviction scoring.",
    version="0.1.0",
)

# CORS -- allow the Vite dev server (typically localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    # Seed mock data on first run
    from backend.db.seed import seed_if_empty
    seeded = seed_if_empty()
    if seeded:
        print("First run detected -- mock data loaded.")


# Register routers
from backend.api.hypotheses import router as hypotheses_router  # noqa: E402
from backend.api.pipeline import router as pipeline_router  # noqa: E402
from backend.api.theories import router as theories_router  # noqa: E402
from backend.api.journal import router as journal_router  # noqa: E402
from backend.api.inbox import router as inbox_router  # noqa: E402
from backend.api.briefing import router as briefing_router  # noqa: E402
from backend.api.user_state import router as user_state_router  # noqa: E402

app.include_router(hypotheses_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")
app.include_router(theories_router, prefix="/api")
app.include_router(journal_router, prefix="/api")
app.include_router(inbox_router, prefix="/api")
app.include_router(briefing_router, prefix="/api")
app.include_router(user_state_router, prefix="/api")


@app.get("/api/health")
def health_check():
    from backend.db.database import SessionLocal
    from backend.db.models import UserState
    db = SessionLocal()
    try:
        is_mock = db.query(UserState).filter(
            UserState.key == "is_mock_data", UserState.value == "true"
        ).first()
        return {
            "status": "ok",
            "version": "0.1.0",
            "is_mock_data": is_mock is not None,
        }
    finally:
        db.close()
