from fastapi import APIRouter
from app.api.v1.endpoints import workouts

api_router = APIRouter()
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])