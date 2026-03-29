from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class WorkoutCreateRequest(BaseModel):
    """Input schema for workout generation, allows optional profile updates."""
    training_type: str = "strength"
    age: Optional[int] = None
    weight: Optional[float] = None
    fitness_level: Optional[str] = None
    primary_goal: Optional[str] = None
    equipment_access: Optional[List[str]] = None
    days_per_week: Optional[int] = None
    target_race_distance: Optional[str] = None
    target_race_date: Optional[str] = None
    easy_pace: Optional[str] = None

class Exercise(BaseModel):
    name: str
    type: str
    instructions: str
    duration_s: Optional[int] = None
    target_min: Optional[str] = None
    target_max: Optional[str] = None
    reps: Optional[int] = None
    sets: Optional[int] = None
    end_condition: Optional[str] = None
    end_condition_value: Optional[int] = None
    
    # Posture support fields (enriched later)
    is_posture_supported: Optional[bool] = False
    video_url: Optional[str] = None

class DailyRoutine(BaseModel):
    day: int
    focus: str
    exercises: List[Exercise]

class WorkoutPlan(BaseModel):
    title: str
    target_goal: Optional[str] = None
    daily_routines: List[DailyRoutine]
