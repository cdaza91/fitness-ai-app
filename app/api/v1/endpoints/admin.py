import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.domains.users.models import SupportedExercise
from app.domains.users.schemas import SupportedExerciseCreate, SupportedExerciseResponse

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

@router.post("/exercises", response_model=SupportedExerciseResponse)
def create_supported_exercise(exercise: SupportedExerciseCreate, db: Session = Depends(get_db)):
    """Creates a new exercise that the system can analyze for posture checking."""
    db_ex = db.query(SupportedExercise).filter(
        SupportedExercise.name == exercise.name.lower()
    ).first()
    
    if db_ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El ejercicio ya existe"
        )

    # Convert rules_json to string for database storage
    rules_str = json.dumps(exercise.rules_json) if exercise.rules_json else "{}"

    new_ex = SupportedExercise(
        name=exercise.name.lower(),
        aliases=exercise.aliases,
        rules_json=rules_str,
        is_active=exercise.is_active
    )

    db.add(new_ex)
    db.commit()
    db.refresh(new_ex)

    # For the response, we need a dict with rules_json as a dictionary
    return SupportedExerciseResponse(
        id=new_ex.id,
        name=new_ex.name,
        aliases=new_ex.aliases,
        rules_json=json.loads(new_ex.rules_json) if new_ex.rules_json else {},
        is_active=new_ex.is_active
    )


@router.get("/exercises", response_model=List[SupportedExerciseResponse])
def get_supported_exercises(db: Session = Depends(get_db)):
    """Lists all configured exercises with their respective rules."""
    exercises = db.query(SupportedExercise).all()

    result = []
    for ex in exercises:
        result.append(SupportedExerciseResponse(
            id=ex.id,
            name=ex.name,
            aliases=ex.aliases,
            rules_json=json.loads(ex.rules_json) if ex.rules_json else {},
            is_active=ex.is_active
        ))

    return result
