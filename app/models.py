"""
Database schema.

Design notes
------------
- User <-1:N-> WorkoutPlan <-1:N-> WorkoutExercise <-N:1-> Exercise
  A WorkoutPlan is a scheduled/completed workout session belonging to one
  user. It's made up of WorkoutExercise rows, each pinning one Exercise to
  the plan with the planned sets/reps/weight AND (once done) the actual
  sets/reps/weight — this is what lets us generate progress reports later
  without a separate "log" table.
- Exercise is a shared, user-independent catalog seeded once (see app/seed.py).
- Cascade deletes are used so deleting a workout plan cleans up its
  exercise rows, and deleting a user cleans up their plans.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Float,
    ForeignKey,
    DateTime,
    Enum,
    Text,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ExerciseCategory(str, enum.Enum):
    CARDIO = "cardio"
    STRENGTH = "strength"
    FLEXIBILITY = "flexibility"
    BALANCE = "balance"


class MuscleGroup(str, enum.Enum):
    CHEST = "chest"
    BACK = "back"
    LEGS = "legs"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    CORE = "core"
    FULL_BODY = "full_body"
    NONE = "none"  # for pure cardio/flexibility work with no primary muscle group


class WorkoutStatus(str, enum.Enum):
    PENDING = "pending"      # scheduled, not yet done
    COMPLETED = "completed"  # actually performed
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workout_plans: Mapped[list["WorkoutPlan"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Exercise(Base):
    """Shared exercise catalog. Populated by app/seed.py."""

    __tablename__ = "exercises"
    __table_args__ = (UniqueConstraint("name", name="uq_exercise_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[ExerciseCategory] = mapped_column(Enum(ExerciseCategory), nullable=False)
    muscle_group: Mapped[MuscleGroup] = mapped_column(
        Enum(MuscleGroup), nullable=False, default=MuscleGroup.NONE
    )

    workout_exercises: Mapped[list["WorkoutExercise"]] = relationship(back_populates="exercise")


class WorkoutPlan(Base):
    """A single workout session: a named, schedulable collection of exercises."""

    __tablename__ = "workout_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[WorkoutStatus] = mapped_column(
        Enum(WorkoutStatus), nullable=False, default=WorkoutStatus.PENDING
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="workout_plans")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout_plan", cascade="all, delete-orphan", order_by="WorkoutExercise.position"
    )


class WorkoutExercise(Base):
    """
    One exercise entry inside a workout plan, holding both the *planned*
    sets/reps/weight (set at creation time) and the *actual* values
    (filled in when the user marks the workout complete). Reports are
    built by comparing these two across time.
    """

    __tablename__ = "workout_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workout_plan_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)  # order within the workout

    planned_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_weight_kg: Mapped[float] = mapped_column(Float, nullable=True)

    actual_sets: Mapped[int] = mapped_column(Integer, nullable=True)
    actual_reps: Mapped[int] = mapped_column(Integer, nullable=True)
    actual_weight_kg: Mapped[float] = mapped_column(Float, nullable=True)

    workout_plan: Mapped["WorkoutPlan"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship(back_populates="workout_exercises")


class RevokedToken(Base):
    """
    Denylist of JWT IDs (jti) that have been logged out before their natural
    expiry. JWTs are stateless by design, so a real "logout" endpoint needs
    somewhere to record that a specific token should no longer be honoured
    even though it hasn't technically expired yet.
    """

    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
