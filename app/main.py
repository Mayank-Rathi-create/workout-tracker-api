from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, exercises, workouts, reports

# For a real deployment, replace this with Alembic migrations (see README).
# create_all is convenient for local dev / tests but won't handle schema
# changes to existing tables.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Workout Tracker API",
    description=(
        "API for signing up, logging in, building workout plans from a "
        "shared exercise catalog, scheduling sessions, and generating "
        "progress reports."
    ),
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(exercises.router)
app.include_router(workouts.router)
app.include_router(reports.router)


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok"}
