from pydantic import BaseModel
from typing import List, Optional

class Exercise(BaseModel):
    name: str
    muscle_group: str
    sets: int
    reps: str
    rest_seconds: int
    instructions: str
    search_term: str
    youtube_id: Optional[str] = None

class DailyWorkout(BaseModel):
    day: str
    focus: str
    exercises: List[Exercise]

class WorkoutPlan(BaseModel):
    title: str
    target_goal: str
    daily_routines: List[DailyWorkout]