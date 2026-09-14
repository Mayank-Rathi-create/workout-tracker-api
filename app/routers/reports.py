from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import WorkoutPlan, WorkoutExercise, Exercise, WorkoutStatus, User
from app.schemas import SummaryReport, ExerciseProgressReport, ExerciseProgressPoint

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=SummaryReport)
def summary_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    High-level stats across the user's workout history: counts by status
    and total training volume (sets x reps x weight) lifted, optionally
    scoped to a date range via ?start_date=&end_date= (ISO 8601).
    """
    query = db.query(WorkoutPlan).options(
        joinedload(WorkoutPlan.exercises)
    ).filter(WorkoutPlan.user_id == current_user.id)

    if start_date:
        query = query.filter(WorkoutPlan.created_at >= start_date)
    if end_date:
        query = query.filter(WorkoutPlan.created_at <= end_date)

    workouts = query.all()

    total_volume = 0.0
    counts = {WorkoutStatus.COMPLETED: 0, WorkoutStatus.PENDING: 0, WorkoutStatus.CANCELLED: 0}
    for w in workouts:
        counts[w.status] = counts.get(w.status, 0) + 1
        for we in w.exercises:
            if we.actual_sets and we.actual_reps and we.actual_weight_kg:
                total_volume += we.actual_sets * we.actual_reps * we.actual_weight_kg

    return SummaryReport(
        total_workouts_completed=counts[WorkoutStatus.COMPLETED],
        total_workouts_pending=counts[WorkoutStatus.PENDING],
        total_workouts_cancelled=counts[WorkoutStatus.CANCELLED],
        total_volume_kg=round(total_volume, 2),
        date_range_start=start_date,
        date_range_end=end_date,
    )


@router.get("/exercises/{exercise_id}/progress", response_model=ExerciseProgressReport)
def exercise_progress_report(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chronological history of the current user's performance on one exercise
    across all their completed workouts — the data a "progress over time"
    chart (e.g. weight lifted per session) would be built from.
    """
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    rows = (
        db.query(WorkoutExercise, WorkoutPlan)
        .join(WorkoutPlan, WorkoutExercise.workout_plan_id == WorkoutPlan.id)
        .filter(
            WorkoutPlan.user_id == current_user.id,
            WorkoutExercise.exercise_id == exercise_id,
            WorkoutPlan.status == WorkoutStatus.COMPLETED,
        )
        .order_by(WorkoutPlan.completed_at.asc())
        .all()
    )

    history = []
    for we, wp in rows:
        volume = None
        if we.actual_sets and we.actual_reps and we.actual_weight_kg:
            volume = round(we.actual_sets * we.actual_reps * we.actual_weight_kg, 2)
        history.append(
            ExerciseProgressPoint(
                workout_plan_id=wp.id,
                date=wp.completed_at or wp.updated_at,
                actual_sets=we.actual_sets,
                actual_reps=we.actual_reps,
                actual_weight_kg=we.actual_weight_kg,
                estimated_volume_kg=volume,
            )
        )

    return ExerciseProgressReport(exercise_id=exercise.id, exercise_name=exercise.name, history=history)
