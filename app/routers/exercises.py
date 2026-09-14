from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Exercise, ExerciseCategory, MuscleGroup, User
from app.schemas import ExerciseOut

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseOut])
def list_exercises(
    category: Optional[ExerciseCategory] = None,
    muscle_group: Optional[MuscleGroup] = None,
    search: Optional[str] = Query(default=None, description="Case-insensitive substring match on name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Browse the exercise catalog (used to populate the exercise picker when
    building a workout plan). Filterable by category and/or muscle group.
    """
    query = db.query(Exercise)
    if category:
        query = query.filter(Exercise.category == category)
    if muscle_group:
        query = query.filter(Exercise.muscle_group == muscle_group)
    if search:
        query = query.filter(Exercise.name.ilike(f"%{search}%"))
    return query.order_by(Exercise.name).all()


@router.get("/{exercise_id}", response_model=ExerciseOut)
def get_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return exercise
