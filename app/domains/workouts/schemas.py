import json
from pydantic import BaseModel, field_validator, computed_field
from typing import List, Optional, Dict, Any
from datetime import date

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

class WorkoutPlanBase(BaseModel):
    title: str
    target_goal: Optional[str] = None

class WorkoutDaySchema(BaseModel):
    id: int
    day_index: int
    date: Optional[date] = None
    is_completed: bool = False
    activity_id: Optional[int] = None
    workout_data: Optional[Dict[str, Any]] = None  # Contains DailyRoutine info
    performance_data: Optional[Dict[str, Any]] = None  # e.g., weight used per exercise

    @field_validator('workout_data', 'performance_data', mode='before')
    @classmethod
    def parse_json_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v

    class Config:
        from_attributes = True

class WorkoutPlanResponse(WorkoutPlanBase):
    id: int
    training_type: Optional[str] = None
    created_at: Any
    json_data: Optional[Dict[str, Any]] = None
    days: List[WorkoutDaySchema]

    @field_validator('json_data', mode='before')
    @classmethod
    def parse_json_data(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                data = json.loads(v)
                return data
            except json.JSONDecodeError:
                return v
        return v
    
    @computed_field
    @property
    def daily_routines(self) -> List[DailyRoutine]:
        if self.json_data and "daily_routines" in self.json_data:
            return self.json_data["daily_routines"]
        return []

    class Config:
        from_attributes = True
