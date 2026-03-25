import asyncio
import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.domains.workouts.service import generate_workout_from_ai
from app.domains.workouts.youtube_service import get_exercise_video_id
from app.domains.users.models import SupportedExercise, Workout, User
from app.domains.users.routers import get_current_user

router = APIRouter()


@router.post("/generate")
async def create_workout(
        user_info: dict,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        for key, value in user_info.items():
            if hasattr(current_user, key):
                if isinstance(value, list):
                    setattr(current_user, key, json.dumps(value))
                else:
                    setattr(current_user, key, value)

        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        training_type = user_info.get("training_type", "strength")

        workout_dict = generate_workout_from_ai(current_user, training_type, db)

        supported_records = db.query(SupportedExercise).filter(SupportedExercise.is_active == True).all()
        supported_keywords = []
        for rec in supported_records:
            supported_keywords.append(rec.name.lower())
            if rec.aliases:
                supported_keywords.extend([alias.strip().lower() for alias in rec.aliases.split(',')])

        new_workout = Workout(
            user_id=current_user.id,
            title=workout_dict.get("title", "Plan Adaptativo"),
            json_data=json.dumps(workout_dict),
            training_type=training_type,
        )
        db.add(new_workout)
        db.commit()

        return workout_dict

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))