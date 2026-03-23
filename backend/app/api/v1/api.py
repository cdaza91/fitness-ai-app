from fastapi import APIRouter
from app.api.v1.endpoints import workouts
from app.api.v1.endpoints import users

api_router = APIRouter()
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(users.router, tags=["users"])