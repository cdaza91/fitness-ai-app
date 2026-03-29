from fastapi import APIRouter
from app.api.v1.endpoints import workouts, admin, users, integrations


api_router = APIRouter()

api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(users.router)
api_router.include_router(admin.router)

api_router.include_router(integrations.router)