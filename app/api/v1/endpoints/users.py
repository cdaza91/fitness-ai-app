import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.domains.users.dependencies import get_current_user
from app.domains.users.schemas import (
    UserCreate, UserLogin, Token, UserResponse, UserProfile, UserMeResponse,
    UserStatisticsResponse, WeightHistoryEntry, CompletionStats, PerformanceTrend
)
from app.domains.users.models import User, WorkoutPlan, WorkoutDay, HealthMetric, Activity
from app.domains.workouts.utils import enrich_workout_with_posture_check

router = APIRouter()
logger = logging.getLogger(__name__)

def get_latest_enriched_workout(user_id: int, db: Session) -> Optional[WorkoutPlan]:
    """Helper to fetch and enrich the user's latest workout plan."""
    last_workout_obj = db.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == user_id
    ).order_by(WorkoutPlan.id.desc()).first()

    return last_workout_obj

def get_current_day_index() -> int:
    """Returns the current day of the week as an index (0-6, where Monday is 0)."""
    return datetime.utcnow().weekday()

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
    workout_obj = get_latest_enriched_workout(user.id, db)
    
    # Inject current_day into the user object (it won't be saved to DB)
    user.current_day = get_current_day_index()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,  # Pydantic will use UserProfile schema and exclude sensitive fields
        "last_workout": workout_obj
    }

@router.get("/users/me", response_model=UserMeResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Returns the current authenticated user's profile and latest workout."""
    workout_obj = get_latest_enriched_workout(current_user.id, db)
    
    # Inject current_day into the user object
    current_user.current_day = get_current_day_index()

    return {
        "profile": current_user,  # Pydantic will use UserProfile schema and exclude sensitive fields
        "last_workout": workout_obj
    }

@router.get("/users/me/statistics", response_model=UserStatisticsResponse)
async def get_user_statistics(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Calculates and returns user performance and health statistics."""
    
    # 1. Weight History
    weight_history_objs = db.query(HealthMetric).filter(
        HealthMetric.user_id == current_user.id,
        HealthMetric.weight_kg != None
    ).order_by(HealthMetric.date.asc()).all()
    
    weight_history = [WeightHistoryEntry(date=h.date, weight=h.weight_kg) for h in weight_history_objs]
    
    # 2. Workout Completion
    # Find all days associated with plans for this user
    plans_subquery = db.query(WorkoutPlan.id).filter(WorkoutPlan.user_id == current_user.id).subquery()
    total_planned = db.query(WorkoutDay).filter(WorkoutDay.workout_plan_id.in_(plans_subquery)).count()
    total_completed = db.query(WorkoutDay).filter(
        WorkoutDay.workout_plan_id.in_(plans_subquery),
        WorkoutDay.is_completed == True
    ).count()
    
    completion_stats = CompletionStats(
        total_planned=total_planned,
        total_completed=total_completed,
        completion_rate=(total_completed / total_planned * 100) if total_planned > 0 else 0
    )
    
    # 3. Strength Trends
    # Extract weights used per exercise across all workout days
    exercise_performance = {} # name: [weight1, weight2, ...]
    
    completed_workout_days = db.query(WorkoutDay).filter(
        WorkoutDay.workout_plan_id.in_(plans_subquery),
        WorkoutDay.is_completed == True,
        WorkoutDay.performance_data != None
    ).all()
    
    for day in completed_workout_days:
        try:
            perf_data = json.loads(day.performance_data)
            for ex_name, metrics in perf_data.items():
                weight = metrics.get("weight")
                if weight is not None:
                    if ex_name not in exercise_performance:
                        exercise_performance[ex_name] = []
                    exercise_performance[ex_name].append(float(weight))
        except (json.JSONDecodeError, AttributeError):
            continue
            
    strength_trends = []
    for ex_name, weights in exercise_performance.items():
        if len(weights) >= 1:
            first_weight = weights[0]
            last_weight = weights[-1]
            best_weight = max(weights)
            improvement = ((last_weight - first_weight) / first_weight * 100) if first_weight > 0 else 0
            
            strength_trends.append(PerformanceTrend(
                exercise_name=ex_name,
                improvement_percentage=improvement,
                last_weight=last_weight,
                best_weight=best_weight
            ))
            
    # 4. Activity Totals
    activity_data = db.query(
        func.count(Activity.id).label("count"),
        func.sum(Activity.calories).label("calories")
    ).filter(Activity.user_id == current_user.id).first()
    
    return UserStatisticsResponse(
        weight_history=weight_history,
        workout_completion=completion_stats,
        strength_trends=strength_trends,
        total_activities_count=activity_data.count or 0,
        total_calories_burned=float(activity_data.calories or 0.0)
    )
