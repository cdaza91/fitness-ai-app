from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.db import get_db
import json
from app.core.security import SECRET_KEY, ALGORITHM, verify_password, create_access_token, get_password_hash
from app.domains.users.routers import get_current_user
from app.domains.users.schemas import UserCreate, Token
from app.domains.users.models import User, Workout
from app.domains.workouts.utils import enrich_workout_with_posture_check

router = APIRouter()



@router.post("/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    hashed_pwd = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login")
async def login(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    password = payload.get("password")

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")

    access_token = create_access_token(data={"sub": user.email})

    # Buscamos su última rutina
    last_workout_obj = db.query(Workout).filter(Workout.user_id == user.id).order_by(Workout.id.desc()).first()

    workout_data = None
    if last_workout_obj:
        # Asumiendo que guardas el JSON en una columna llamada json_data o similar\
        raw_data = json.loads(last_workout_obj.json_data)
        workout_data = enrich_workout_with_posture_check(raw_data, db)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "weight": user.weight,
            "height": user.height,
            "goal": user.goal,
            "last_workout": workout_data
        }
    }


@router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    last_workout_obj = db.query(Workout).filter(Workout.user_id == current_user.id).order_by(Workout.id.desc()).first()

    workout_data = None
    if last_workout_obj:
        raw_data = json.loads(last_workout_obj.json_data)
        workout_data = enrich_workout_with_posture_check(raw_data, db)

    return {
        "profile": {
            "email": current_user.email,
            "weight": current_user.weight,
            "height": current_user.height,
            "goal": current_user.goal,
        },
        "last_workout": workout_data
    }