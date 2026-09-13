# Workout Tracker API

A RESTful backend for a workout tracker: sign up, log in with JWTs, build
workout plans from a shared exercise catalog, schedule sessions, record
what you actually did, and pull progress reports.

**Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + JWT (python-jose) +
bcrypt (passlib). Relational DB: PostgreSQL in production, SQLite for local
dev/tests (swap by changing one env var — no code changes needed).

## 1. Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then edit SECRET_KEY at minimum
```

By default `DATABASE_URL` in `.env.example` points at Postgres. If you
don't have Postgres running locally, just delete that line (or leave the
whole `.env` file absent) — `app/config.py` falls back to a local SQLite
file (`workout_tracker.db`) so the app runs with zero external
dependencies.

To use Postgres:
```sql
CREATE DATABASE workout_tracker;
CREATE USER workout_user WITH PASSWORD 'workout_pass';
GRANT ALL PRIVILEGES ON DATABASE workout_tracker TO workout_user;
```

## 2. Seed the exercise catalog

```bash
python -m app.seed
```

Idempotent — safe to re-run; it skips exercises that already exist. Adds
30 exercises across strength, cardio, and flexibility, tagged by muscle
group.

## 3. Run the API

```bash
uvicorn app.main:app --reload
```

- Interactive docs (Swagger UI): http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Raw OpenAPI spec (also exported to `openapi.json` in this repo): http://127.0.0.1:8000/openapi.json

## 4. Run the tests

```bash
pytest -v
```

26 tests covering signup/login/logout/refresh, JWT enforcement, exercise
filtering, workout CRUD, scheduling order, cross-user access isolation,
and both report endpoints. Tests run against an isolated in-memory SQLite
DB, so they never touch your real database.

---

## Database schema

```
User
 ├─ id, email (unique), hashed_password, full_name, is_active, created_at
 └─ 1───N WorkoutPlan

WorkoutPlan                              Exercise (shared catalog, seeded)
 ├─ id, user_id (FK)                      ├─ id, name (unique)
 ├─ name, comments                        ├─ description
 ├─ status: pending|completed|cancelled   ├─ category: cardio|strength|flexibility|balance
 ├─ scheduled_at, completed_at            └─ muscle_group: chest|back|legs|shoulders|arms|core|full_body|none
 ├─ created_at, updated_at
 └─ 1───N WorkoutExercise ───N───1 Exercise
             ├─ position (order within the workout)
             ├─ planned_sets, planned_reps, planned_weight_kg
             └─ actual_sets, actual_reps, actual_weight_kg   (filled in once performed)

RevokedToken   (denylist for logout — see "Auth design" below)
 ├─ jti (unique), expires_at
```

**Why `planned_*` / `actual_*` live on the same row** instead of a
separate "workout log" table: a workout plan *is* the log once it's
marked `completed` — there's no meaningful difference between "what I
planned to lift" and "what I logged" other than whether the actual
columns are filled in yet. This keeps one table instead of two, and the
progress-report endpoint reads directly off `actual_*` for exercises
belonging to `completed` workouts.

## Auth design

- **Access token** (30 min default) — sent as `Authorization: Bearer <token>`
  on every protected request.
- **Refresh token** (7 days default) — exchanged at `POST /auth/refresh`
  for a new token pair, so the frontend isn't forced to re-prompt for a
  password every 30 minutes.
- **Logout** — JWTs are stateless, so "logging out" a token that hasn't
  expired yet needs somewhere to record that it's no longer valid. Each
  token carries a unique `jti`; `POST /auth/logout` writes that `jti` to
  a `revoked_tokens` table, and `get_current_user` rejects any token
  whose `jti` shows up there. Rows older than their own `exp` are safe to
  garbage-collect periodically (see `deps.cleanup_expired_revocations`).
- **Passwords** are hashed with bcrypt via passlib — never stored or
  logged in plaintext.
- **Ownership checks**: every workout-scoped endpoint filters by
  `WorkoutPlan.user_id == current_user.id` and returns `404` (not `403`)
  for another user's workout ID, so the API doesn't confirm or deny that
  an ID exists for someone else's account.

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | – | Create an account |
| POST | `/auth/login` | – | Get access + refresh tokens |
| POST | `/auth/refresh` | – | Exchange a refresh token for a new pair |
| POST | `/auth/logout` | ✓ | Revoke the current access token |
| GET | `/auth/me` | ✓ | Current user's profile |
| GET | `/exercises` | ✓ | Browse catalog (filter by `category`, `muscle_group`, `search`) |
| GET | `/exercises/{id}` | ✓ | Single exercise |
| POST | `/workouts` | ✓ | Create a workout plan with its exercises |
| GET | `/workouts` | ✓ | List your workouts, sorted by `scheduled_at` (soonest first, unscheduled last); filter with `?status_filter=pending` |
| GET | `/workouts/{id}` | ✓ | Fetch one workout |
| PATCH | `/workouts/{id}` | ✓ | Update name/comments/schedule/status |
| DELETE | `/workouts/{id}` | ✓ | Delete a workout |
| POST | `/workouts/{id}/exercises` | ✓ | Add an exercise to an existing workout |
| PATCH | `/workouts/{id}/exercises/{we_id}` | ✓ | Edit planned values or record actual sets/reps/weight |
| DELETE | `/workouts/{id}/exercises/{we_id}` | ✓ | Remove an exercise from a workout |
| GET | `/reports/summary` | ✓ | Counts by status + total training volume, optional `start_date`/`end_date` |
| GET | `/reports/exercises/{id}/progress` | ✓ | Chronological history of actual performance on one exercise |

Full request/response schemas with examples are in the live Swagger UI
(`/docs`) — every field is documented there via the Pydantic models in
`app/schemas.py`.

### Example: end-to-end curl walkthrough

```bash
# 1. Sign up
curl -X POST localhost:8000/auth/signup -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"strongpass123","full_name":"Alice"}'

# 2. Log in
TOKEN=$(curl -s -X POST localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"strongpass123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 3. Browse exercises
curl localhost:8000/exercises?category=strength -H "Authorization: Bearer $TOKEN"

# 4. Create a workout (exercise_id from step 3), scheduled for a future date
curl -X POST localhost:8000/workouts -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Push Day","scheduled_at":"2026-10-01T18:00:00Z","exercises":[{"exercise_id":1,"planned_sets":4,"planned_reps":8,"planned_weight_kg":60}]}'

# 5. After training, record what you actually did and mark it complete
curl -X PATCH localhost:8000/workouts/1/exercises/1 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"actual_sets":4,"actual_reps":8,"actual_weight_kg":62.5}'
curl -X PATCH localhost:8000/workouts/1 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"status":"completed"}'

# 6. Pull a report
curl localhost:8000/reports/summary -H "Authorization: Bearer $TOKEN"
```

## Production notes (not needed to run/grade this locally)

- Swap `Base.metadata.create_all()` for **Alembic** migrations once the
  schema needs to evolve without dropping data (`alembic` is already in
  `requirements.txt`; run `alembic init migrations` to wire it up).
- Put `SECRET_KEY` in a real secrets manager, not `.env`, before deploying.
- Add rate limiting on `/auth/login` and `/auth/signup` to blunt
  brute-force and enumeration attempts.
- Consider shortening access-token lifetime further and relying more on
  refresh rotation if this were handling sensitive data at scale.
