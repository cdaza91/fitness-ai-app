from pydantic import BaseModel, EmailStr, SecretStr, Field
from typing import Optional, Dict, Any, List

class UserCreate(BaseModel):
    email: EmailStr
    password: SecretStr

class UserLogin(BaseModel):
    email: EmailStr
    password: SecretStr

class UserProfile(BaseModel):
    email: str
    weight: Optional[float] = None
    height: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    goal: Optional[str] = None
    fitness_level: Optional[str] = None
    primary_goal: Optional[str] = None
    garmin_email: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile
    last_workout: Optional[Dict[str, Any]] = None

class UserMeResponse(BaseModel):
    profile: UserProfile
    last_workout: Optional[Dict[str, Any]] = None

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
