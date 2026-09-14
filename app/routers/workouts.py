from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import WorkoutPlan, WorkoutExercise, Exercise, WorkoutStatus, User
from app.schemas import (
    WorkoutPlanCreate,
    WorkoutPlanUpdate,
    WorkoutPlanOut,
    WorkoutExerciseCreate,
    WorkoutExerciseUpdate,
    WorkoutExerciseOut,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])


def _get_owned_workout(workout_id: int, db: Session, user: User) -> WorkoutPlan:
    """
    Fetches a workout plan and enforces ownership in one place. Returns 404
    (not 403) when the plan belongs to someone else, so we don't leak the
    existence of other users' workout IDs.
    """
    workout = (
        db.query(WorkoutPlan)
        .options(joinedload(WorkoutPlan.exercises).joinedload(WorkoutExercise.exercise))
        .filter(WorkoutPlan.id == workout_id)
        .first()
    )
    if not workout or workout.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


def _validate_exercise_ids(exercise_ids: set[int], db: Session) -> None:
    found = {e.id for e in db.query(Exercise.id).filter(Exercise.id.in_(exercise_ids)).all()}
    missing = exercise_ids - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown exercise id(s): {sorted(missing)}",
        )


@router.post("", response_model=WorkoutPlanOut, status_code=status.HTTP_201_CREATED)
def create_workout(
    payload: WorkoutPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_exercise_ids({e.exercise_id for e in payload.exercises}, db)

    workout = WorkoutPlan(
        user_id=current_user.id,
        name=payload.name,
        comments=payload.comments,
        scheduled_at=payload.scheduled_at,
        status=WorkoutStatus.PENDING,
    )
    for item in payload.exercises:
        workout.exercises.append(
            WorkoutExercise(
                exercise_id=item.exercise_id,
                position=item.position,
                planned_sets=item.planned_sets,
                planned_reps=item.planned_reps,
                planned_weight_kg=item.planned_weight_kg,
            )
        )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return _get_owned_workout(workout.id, db, current_user)


@router.get("", response_model=list[WorkoutPlanOut])
def list_workouts(
    status_filter: Optional[WorkoutStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists the current user's workouts, sorted by scheduled date/time
    (soonest first; unscheduled workouts sort last). Filter with
    ?status_filter=pending to see only active/upcoming workouts.
    """
    query = db.query(WorkoutPlan).options(
        joinedload(WorkoutPlan.exercises).joinedload(WorkoutExercise.exercise)
    ).filter(WorkoutPlan.user_id == current_user.id)

    if status_filter:
        query = query.filter(WorkoutPlan.status == status_filter)

    # NULLS LAST equivalent that works identically on SQLite and Postgres:
    # SQLite doesn't reliably preserve tz-awareness, so we normalize each
    # scheduled_at to a plain epoch-seconds float before comparing.
    def sort_key(w: WorkoutPlan):
        if w.scheduled_at is None:
            return (1, 0.0)
        dt = w.scheduled_at if w.scheduled_at.tzinfo else w.scheduled_at.replace(tzinfo=timezone.utc)
        return (0, dt.timestamp())

    workouts = query.all()
    workouts.sort(key=sort_key)
    return workouts


@router.get("/{workout_id}", response_model=WorkoutPlanOut)
def get_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_workout(workout_id, db, current_user)


@router.patch("/{workout_id}", response_model=WorkoutPlanOut)
def update_workout(
    workout_id: int,
    payload: WorkoutPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = _get_owned_workout(workout_id, db, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workout, field, value)

    if update_data.get("status") == WorkoutStatus.COMPLETED and workout.completed_at is None:
        workout.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(workout)
    return _get_owned_workout(workout.id, db, current_user)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = _get_owned_workout(workout_id, db, current_user)
    db.delete(workout)
    db.commit()
    return None


# ---------- Managing exercises within a workout ----------

@router.post("/{workout_id}/exercises", response_model=WorkoutPlanOut, status_code=status.HTTP_201_CREATED)
def add_exercise_to_workout(
    workout_id: int,
    payload: WorkoutExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = _get_owned_workout(workout_id, db, current_user)
    _validate_exercise_ids({payload.exercise_id}, db)

    workout.exercises.append(
        WorkoutExercise(
            exercise_id=payload.exercise_id,
            position=payload.position,
            planned_sets=payload.planned_sets,
            planned_reps=payload.planned_reps,
            planned_weight_kg=payload.planned_weight_kg,
        )
    )
    db.commit()
    return _get_owned_workout(workout_id, db, current_user)


@router.patch("/{workout_id}/exercises/{workout_exercise_id}", response_model=WorkoutExerciseOut)
def update_workout_exercise(
    workout_id: int,
    workout_exercise_id: int,
    payload: WorkoutExerciseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Edit planned values, or record actual sets/reps/weight once the user has
    performed that exercise — this is the data the progress report reads from.
    """
    workout = _get_owned_workout(workout_id, db, current_user)
    entry = next((e for e in workout.exercises if e.id == workout_exercise_id), None)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise entry not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{workout_id}/exercises/{workout_exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_workout_exercise(
    workout_id: int,
    workout_exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = _get_owned_workout(workout_id, db, current_user)
    entry = next((e for e in workout.exercises if e.id == workout_exercise_id), None)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise entry not found")

    db.delete(entry)
    db.commit()
    return None
