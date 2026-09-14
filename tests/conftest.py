import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db

# In-memory SQLite shared across connections within a test, wiped between tests.
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seeded_exercise():
    """Inserts one exercise directly and returns its id, bypassing the API."""
    from app.models import Exercise, ExerciseCategory, MuscleGroup

    db = TestingSessionLocal()
    ex = Exercise(
        name="Barbell Bench Press",
        description="Chest press",
        category=ExerciseCategory.STRENGTH,
        muscle_group=MuscleGroup.CHEST,
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    ex_id = ex.id
    db.close()
    return ex_id


@pytest.fixture
def auth_headers(client):
    """Signs up and logs in a fresh user, returning Authorization headers."""
    client.post(
        "/auth/signup",
        json={"email": "test@example.com", "password": "supersecret123", "full_name": "Test User"},
    )
    resp = client.post("/auth/login", json={"email": "test@example.com", "password": "supersecret123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
