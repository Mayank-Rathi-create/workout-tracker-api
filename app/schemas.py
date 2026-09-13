from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models import ExerciseCategory, MuscleGroup, WorkoutStatus


# ---------- Auth / Users ----------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- Exercises ----------

class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None
    category: ExerciseCategory
    muscle_group: MuscleGroup


# ---------- Workout exercises (nested inside a workout plan) ----------

class WorkoutExerciseCreate(BaseModel):
    exercise_id: int
    planned_sets: int = Field(gt=0, le=50)
    planned_reps: int = Field(gt=0, le=1000)
    planned_weight_kg: Optional[float] = Field(default=None, ge=0)
    position: int = 0


class WorkoutExerciseUpdate(BaseModel):
    """Used both to edit planned values and to record actuals on completion."""
    planned_sets: Optional[int] = Field(default=None, gt=0, le=50)
    planned_reps: Optional[int] = Field(default=None, gt=0, le=1000)
    planned_weight_kg: Optional[float] = Field(default=None, ge=0)
    actual_sets: Optional[int] = Field(default=None, ge=0, le=50)
    actual_reps: Optional[int] = Field(default=None, ge=0, le=1000)
    actual_weight_kg: Optional[float] = Field(default=None, ge=0)


class WorkoutExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise: ExerciseOut
    position: int
    planned_sets: int
    planned_reps: int
    planned_weight_kg: Optional[float] = None
    actual_sets: Optional[int] = None
    actual_reps: Optional[int] = None
    actual_weight_kg: Optional[float] = None


# ---------- Workout plans ----------

class WorkoutPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    comments: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    exercises: list[WorkoutExerciseCreate] = Field(min_length=1)


class WorkoutPlanUpdate(BaseModel):
    """Partial update: only fields supplied are changed."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    comments: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[WorkoutStatus] = None


class WorkoutPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    comments: Optional[str] = None
    status: WorkoutStatus
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    exercises: list[WorkoutExerciseOut] = []


# ---------- Reports ----------

class ExerciseProgressPoint(BaseModel):
    workout_plan_id: int
    date: datetime
    actual_sets: Optional[int] = None
    actual_reps: Optional[int] = None
    actual_weight_kg: Optional[float] = None
    estimated_volume_kg: Optional[float] = None  # sets * reps * weight


class ExerciseProgressReport(BaseModel):
    exercise_id: int
    exercise_name: str
    history: list[ExerciseProgressPoint]


class SummaryReport(BaseModel):
    total_workouts_completed: int
    total_workouts_pending: int
    total_workouts_cancelled: int
    total_volume_kg: float
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
