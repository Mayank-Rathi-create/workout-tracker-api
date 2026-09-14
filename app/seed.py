"""
Populates the `exercises` table with a starter catalog spanning strength,
cardio, and flexibility work across the major muscle groups.

Usage:
    python -m app.seed
"""
from app.database import Base, engine, SessionLocal
from app.models import Exercise, ExerciseCategory, MuscleGroup

EXERCISES = [
    # name, description, category, muscle_group
    ("Barbell Bench Press", "Flat barbell press targeting the chest, shoulders, and triceps.", ExerciseCategory.STRENGTH, MuscleGroup.CHEST),
    ("Incline Dumbbell Press", "Dumbbell press on an incline bench emphasizing upper chest.", ExerciseCategory.STRENGTH, MuscleGroup.CHEST),
    ("Push-Up", "Bodyweight press targeting chest, shoulders, and core.", ExerciseCategory.STRENGTH, MuscleGroup.CHEST),
    ("Deadlift", "Compound hip-hinge lift targeting the posterior chain.", ExerciseCategory.STRENGTH, MuscleGroup.BACK),
    ("Pull-Up", "Bodyweight vertical pull targeting the lats and biceps.", ExerciseCategory.STRENGTH, MuscleGroup.BACK),
    ("Barbell Row", "Bent-over row targeting the mid-back and lats.", ExerciseCategory.STRENGTH, MuscleGroup.BACK),
    ("Lat Pulldown", "Cable pulldown targeting the lats.", ExerciseCategory.STRENGTH, MuscleGroup.BACK),
    ("Back Squat", "Compound barbell squat targeting quads, glutes, and hamstrings.", ExerciseCategory.STRENGTH, MuscleGroup.LEGS),
    ("Romanian Deadlift", "Hip-hinge movement emphasizing the hamstrings and glutes.", ExerciseCategory.STRENGTH, MuscleGroup.LEGS),
    ("Walking Lunge", "Alternating-leg lunge targeting quads and glutes.", ExerciseCategory.STRENGTH, MuscleGroup.LEGS),
    ("Leg Press", "Machine-based compound press targeting the lower body.", ExerciseCategory.STRENGTH, MuscleGroup.LEGS),
    ("Overhead Press", "Standing barbell press targeting the shoulders.", ExerciseCategory.STRENGTH, MuscleGroup.SHOULDERS),
    ("Lateral Raise", "Dumbbell raise isolating the lateral deltoid.", ExerciseCategory.STRENGTH, MuscleGroup.SHOULDERS),
    ("Barbell Curl", "Curl targeting the biceps.", ExerciseCategory.STRENGTH, MuscleGroup.ARMS),
    ("Triceps Pushdown", "Cable pushdown isolating the triceps.", ExerciseCategory.STRENGTH, MuscleGroup.ARMS),
    ("Plank", "Isometric hold targeting the core.", ExerciseCategory.STRENGTH, MuscleGroup.CORE),
    ("Hanging Leg Raise", "Core exercise targeting the lower abs and hip flexors.", ExerciseCategory.STRENGTH, MuscleGroup.CORE),
    ("Kettlebell Swing", "Ballistic hip-hinge movement, full-body with a cardio component.", ExerciseCategory.STRENGTH, MuscleGroup.FULL_BODY),
    ("Burpee", "Full-body bodyweight movement combining a squat, plank, and jump.", ExerciseCategory.CARDIO, MuscleGroup.FULL_BODY),
    ("Treadmill Running", "Steady-state or interval running on a treadmill.", ExerciseCategory.CARDIO, MuscleGroup.NONE),
    ("Cycling", "Steady-state or interval cycling, indoor or outdoor.", ExerciseCategory.CARDIO, MuscleGroup.NONE),
    ("Rowing Machine", "Full-body cardio on an ergometer.", ExerciseCategory.CARDIO, MuscleGroup.FULL_BODY),
    ("Jump Rope", "High-intensity cardio using a skipping rope.", ExerciseCategory.CARDIO, MuscleGroup.NONE),
    ("Stair Climber", "Steady-state cardio on a stair machine.", ExerciseCategory.CARDIO, MuscleGroup.LEGS),
    ("Static Hamstring Stretch", "Seated or standing stretch for the hamstrings.", ExerciseCategory.FLEXIBILITY, MuscleGroup.LEGS),
    ("Cat-Cow Stretch", "Spinal mobility flow for the back and core.", ExerciseCategory.FLEXIBILITY, MuscleGroup.BACK),
    ("Shoulder Dislocate (Band)", "Band mobility drill for shoulder flexibility.", ExerciseCategory.FLEXIBILITY, MuscleGroup.SHOULDERS),
    ("90/90 Hip Stretch", "Hip mobility drill for rotational flexibility.", ExerciseCategory.FLEXIBILITY, MuscleGroup.LEGS),
    ("Child's Pose", "Restorative stretch for the back and hips.", ExerciseCategory.FLEXIBILITY, MuscleGroup.BACK),
    ("Standing Quad Stretch", "Standing stretch targeting the quadriceps.", ExerciseCategory.FLEXIBILITY, MuscleGroup.LEGS),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        added = 0
        for name, description, category, muscle_group in EXERCISES:
            if db.query(Exercise).filter(Exercise.name == name).first():
                continue  # idempotent: safe to run multiple times
            db.add(Exercise(name=name, description=description, category=category, muscle_group=muscle_group))
            added += 1
        db.commit()
        print(f"Seed complete: {added} new exercise(s) added, {len(EXERCISES) - added} already present.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
