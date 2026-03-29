import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.domains.workouts.service import generate_workout, generate_adaptive_workout_update
from app.domains.workouts.schemas import WorkoutCreateRequest, WorkoutPlanResponse
from app.domains.users.models import User, WorkoutPlan, WorkoutDay, HealthMetric, Activity
from app.domains.users.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

def update_user_profile(user: User, data: WorkoutCreateRequest, db: Session):
    """Updates user profile attributes based on the request data."""
    update_data = data.model_dump(exclude_unset=True, exclude={"training_type"})
    for key, value in update_data.items():
        if hasattr(user, key):
            # Special handling for lists (e.g., equipment_access)
            if isinstance(value, list):
                # In models.py it's Text for equipment_access and secondary_goals.
                setattr(user, key, json.dumps(value))
            else:
                setattr(user, key, value)
    db.add(user)
    db.commit()
    db.refresh(user)

def save_workout_plan(db: Session, user_id: int, workout_dict: dict, training_type: str) -> WorkoutPlan:
    """Helper to save a generated workout plan and its individual days."""
    new_plan = WorkoutPlan(
        user_id=user_id,
        title=workout_dict.get("title", f"Plan {training_type.capitalize()}"),
        json_data=json.dumps(workout_dict),
        training_type=training_type,
    )
    db.add(new_plan)
    db.flush() # Get plan ID

    routines = workout_dict.get("daily_routines", [])
    for routine in routines:
        day_obj = WorkoutDay(
            workout_plan_id=new_plan.id,
            day_index=routine.get("day"),
            workout_data=json.dumps(routine),
            is_completed=False
        )
        db.add(day_obj)
    
    db.commit()
    db.refresh(new_plan)
    return new_plan


@router.post("/generate", response_model=WorkoutPlanResponse)
async def create_workout(
        request: WorkoutCreateRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Updates the user profile and generates a personalized workout plan using AI.
    Separates the plan into individual WorkoutDay entries.
    """
    try:
        # 1. Update user profile with any new information provided in the request
        update_user_profile(current_user, request, db)
        
        # 2. Orchestrate workout generation based on training type
        workout_dict = generate_workout(current_user, request.training_type)
        
        # 3. Store the generated workout plan
        new_plan = save_workout_plan(db, current_user.id, workout_dict, request.training_type)

        return new_plan

    except ValueError as e:
        logger.error(f"Validation or format error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error en los datos o formato: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error during workout generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al generar el entrenamiento. Por favor, intente de nuevo."
        )


@router.post("/replan", response_model=WorkoutPlanResponse)
async def update_workout_plan_adaptively(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyzes the user's performance and health metrics from the last week
    and generates an updated/improved plan for the next week.
    """
    # 1. Fetch the current/latest workout plan
    latest_plan = db.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == current_user.id
    ).order_by(WorkoutPlan.created_at.desc()).first()

    if not latest_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró un plan previo para replanificar."
        )

    # 2. Gather performance data from the last 7 days
    last_week_start = datetime.utcnow() - timedelta(days=7)
    
    completed_days = db.query(WorkoutDay).filter(
        WorkoutDay.workout_plan_id == latest_plan.id,
        WorkoutDay.is_completed == True
    ).all()

    missed_days = db.query(WorkoutDay).filter(
        WorkoutDay.workout_plan_id == latest_plan.id,
        WorkoutDay.is_completed == False,
        # Potentially filter by date if we tracked it per day
    ).all()

    # Aggregate performance metrics (e.g. weights used in strength)
    performance_metrics = {}
    for day in completed_days:
        if day.performance_data:
            try:
                metrics = json.loads(day.performance_data)
                performance_metrics.update(metrics)
            except json.JSONDecodeError:
                pass

    # 3. Gather health metrics (Weight, HR, Sleep, etc.)
    health_metrics_objs = db.query(HealthMetric).filter(
        HealthMetric.user_id == current_user.id,
        HealthMetric.date >= last_week_start.date()
    ).all()

    # 4. Gather activities from last week (Garmin data)
    activities_objs = db.query(Activity).filter(
        Activity.user_id == current_user.id,
        Activity.date >= last_week_start
    ).all()

    # Format data for AI
    formatted_health = [
        {
            "date": h.date.isoformat(), 
            "weight": h.weight_kg, 
            "body_fat": h.body_fat_pct,
            "muscle_mass": h.muscle_mass_kg,
            "rhr": h.resting_heart_rate,
            "sleep_hours": h.sleep_hours,
            "sleep_score": h.sleep_score,
            "source": h.source
        } for h in health_metrics_objs
    ]
    
    formatted_activities = [
        {
            "name": a.name,
            "type": a.activity_type,
            "date": a.date.isoformat(),
            "duration": a.duration_seconds,
            "distance": a.distance_meters,
            "avg_hr": a.average_heart_rate,
            "calories": a.calories
        } for a in activities_objs
    ]

    # 5. Invoke the AI to generate the adaptive update
    try:
        updated_workout_dict = generate_adaptive_workout_update(
            user=current_user,
            training_type=latest_plan.training_type,
            original_plan_json=latest_plan.json_data,
            completed_sessions=[{"day": d.day_index} for d in completed_days],
            missed_sessions=[{"day": d.day_index} for d in missed_days],
            performance_metrics=performance_metrics,
            health_metrics=formatted_health,
            # Activities are added to performance metrics context
            activities=formatted_activities 
        )
        print(updated_workout_dict)
        # 6. Save the new plan
        new_plan = save_workout_plan(db, current_user.id, updated_workout_dict, latest_plan.training_type)
        return new_plan

    except Exception as e:
        logger.exception(f"Adaptive replanning failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el plan adaptativo."
        )
