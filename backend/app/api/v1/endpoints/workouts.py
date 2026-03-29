import json
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.domains.workouts.service import generate_workout
from app.domains.workouts.schemas import WorkoutCreateRequest, WorkoutPlan
from app.domains.users.models import User, Workout
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
                # If the DB stores it as a list, keep it. If it stores it as a string, dump it.
                # In models.py it's Text for equipment_access and secondary_goals.
                setattr(user, key, json.dumps(value))
            else:
                setattr(user, key, value)
    db.add(user)
    db.commit()
    db.refresh(user)

@router.post("/generate", response_model=WorkoutPlan)
async def create_workout(
        request: WorkoutCreateRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Updates the user profile and generates a personalized workout plan using AI.
    """
    try:
        # 1. Update user profile with any new information provided in the request
        update_user_profile(current_user, request, db)
        
        # 2. Orchestrate workout generation based on training type
        workout_dict = generate_workout(current_user, request.training_type)
        
        # 3. Store the generated workout for history and retrieval
        new_workout = Workout(
            user_id=current_user.id,
            title=workout_dict.get("title", f"Plan {request.training_type.capitalize()}"),
            json_data=json.dumps(workout_dict),
            training_type=request.training_type,
        )
        db.add(new_workout)
        db.commit()

        # Returning the dictionary that matches the WorkoutPlan schema
        return workout_dict

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
