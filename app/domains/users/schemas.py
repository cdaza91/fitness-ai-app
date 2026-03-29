from pydantic import BaseModel, EmailStr, SecretStr, Field
from typing import Optional, Dict, Any, List
from datetime import date
from app.domains.workouts.schemas import WorkoutPlanResponse

class UserCreate(BaseModel):
    email: EmailStr
    password: SecretStr

class UserLogin(BaseModel):
    email: EmailStr
    password: SecretStr

class UserProfile(BaseModel):
    id: int
    email: str
    weight: Optional[float] = None
    height: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    goal: Optional[str] = None
    fitness_level: Optional[str] = None
    primary_goal: Optional[str] = None
    garmin_email: Optional[str] = None
    current_day: Optional[int] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile
    last_workout: Optional[WorkoutPlanResponse] = None

class UserMeResponse(BaseModel):
    profile: UserProfile
    last_workout: Optional[WorkoutPlanResponse] = None

class SupportedExerciseBase(BaseModel):
    name: str
    aliases: Optional[str] = None
    rules_json: Optional[Dict[str, Any]] = None
    is_active: bool = True

class SupportedExerciseCreate(SupportedExerciseBase):
    pass

class SupportedExerciseResponse(SupportedExerciseBase):
    id: int

    class Config:
        from_attributes = True

class WeightHistoryEntry(BaseModel):
    date: date
    weight: float

class CompletionStats(BaseModel):
    total_planned: int
    total_completed: int
    completion_rate: float

class PerformanceTrend(BaseModel):
    exercise_name: str
    improvement_percentage: float
    last_weight: Optional[float] = None
    best_weight: Optional[float] = None

class UserStatisticsResponse(BaseModel):
    weight_history: List[WeightHistoryEntry]
    workout_completion: CompletionStats
    strength_trends: List[PerformanceTrend]
    total_activities_count: int
    total_calories_burned: float
