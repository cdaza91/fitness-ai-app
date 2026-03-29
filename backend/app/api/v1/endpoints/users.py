import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.domains.users.dependencies import get_current_user
from app.domains.users.schemas import (
    UserCreate, UserLogin, Token, UserResponse, UserProfile, UserMeResponse
)
from app.domains.users.models import User, Workout
from app.domains.workouts.utils import enrich_workout_with_posture_check

router = APIRouter()
logger = logging.getLogger(__name__)

def get_latest_enriched_workout(user_id: int, db: Session) -> Optional[Dict[str, Any]]:
    """Helper to fetch and enrich the user's latest workout plan."""
    last_workout_obj = db.query(Workout).filter(
        Workout.user_id == user_id
    ).order_by(Workout.id.desc()).first()

    if last_workout_obj and last_workout_obj.json_data:
        try:
            raw_data = json.loads(last_workout_obj.json_data)
            return enrich_workout_with_posture_check(raw_data, db)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode workout JSON for user {user_id}")
    return None

@router.post("/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user and returns an access token."""
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El email ya está registrado"
        )

    # Use .get_secret_value() to access the actual password from SecretStr
    hashed_pwd = get_password_hash(user.password.get_secret_value())
    new_user = User(email=user.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login", response_model=UserResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticates a user and returns a token along with their profile and latest workout."""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    # Use .get_secret_value() to access the actual password from SecretStr
    if not user or not verify_password(credentials.password.get_secret_value(), user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Correo o contraseña incorrectos"
        )

    access_token = create_access_token(data={"sub": user.email})
    workout_data = get_latest_enriched_workout(user.id, db)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,  # Pydantic will use UserProfile schema and exclude sensitive fields
        "last_workout": workout_data
    }

@router.get("/users/me", response_model=UserMeResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Returns the current authenticated user's profile and latest workout."""
    workout_data = get_latest_enriched_workout(current_user.id, db)

    return {
        "profile": current_user,  # Pydantic will use UserProfile schema and exclude sensitive fields
        "last_workout": workout_data
    }
