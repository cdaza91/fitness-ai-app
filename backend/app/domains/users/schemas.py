from pydantic import BaseModel
from typing import Optional, Dict, Any

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

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