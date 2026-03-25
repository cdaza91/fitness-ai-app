import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.domains.users.models import SupportedExercise
from app.domains.users.schemas import SupportedExerciseCreate, SupportedExerciseResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/exercises", response_model=SupportedExerciseResponse)
def create_supported_exercise(exercise: SupportedExerciseCreate, db: Session = Depends(get_db)):
    db_ex = db.query(SupportedExercise).filter(SupportedExercise.name == exercise.name).first()
    if db_ex:
        raise HTTPException(status_code=400, detail="El ejercicio ya existe")

    rules_str = json.dumps(exercise.rules_json) if exercise.rules_json else "{}"

    new_ex = SupportedExercise(
        name=exercise.name,
        aliases=exercise.aliases,
        rules_json=rules_str,
        is_active=exercise.is_active
    )

    db.add(new_ex)
    db.commit()
    db.refresh(new_ex)

    response_data = new_ex.__dict__.copy()
    response_data["rules_json"] = json.loads(new_ex.rules_json)

    return response_data


@router.get("/exercises", response_model=list[SupportedExerciseResponse])
def get_supported_exercises(db: Session = Depends(get_db)):
    exercises = db.query(SupportedExercise).all()

    result = []
    for ex in exercises:
        ex_dict = ex.__dict__.copy()
        ex_dict["rules_json"] = json.loads(ex.rules_json) if ex.rules_json else {}
        result.append(ex_dict)

    return result