import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqladmin import Admin, ModelView

from app.api.v1.api import api_router
from app.core.db import engine, Base
from app.core.config import settings
from app.core.tasks import scheduler
from app.core.logging_config import setup_logging
from app.domains.users.models import SupportedExercise, User, Workout, HealthMetric, Activity

# 1. Setup Logging
setup_logging()
logger = logging.getLogger(__name__)

# 2. Database Initialization
Base.metadata.create_all(bind=engine)

# 3. Lifespan for background tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown life of the application."""
    logger.info("Starting up FitCheck AI API...")
    if not scheduler.running:
        scheduler.start()
    yield
    logger.info("Shutting down FitCheck AI API...")
    if scheduler.running:
        scheduler.shutdown()

# 4. FastAPI App Setup
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# 5. Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6. Include API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# 7. Admin Views configuration
admin = Admin(app, engine)

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.primary_goal]
    icon = "fa-solid fa-user"

class WorkoutAdmin(ModelView, model=Workout):
    column_list = [Workout.id, Workout.user_id, Workout.title, Workout.created_at, Workout.training_type]
    icon = "fa-solid fa-calendar-check"

class ActivityAdmin(ModelView, model=Activity):
    column_list = [Activity.id, Activity.user_id, Activity.name, Activity.activity_type, Activity.date]
    icon = "fa-solid fa-person-running"

class HealthMetricAdmin(ModelView, model=HealthMetric):
    column_list = [HealthMetric.id, HealthMetric.user_id, HealthMetric.date, HealthMetric.weight_kg]
    icon = "fa-solid fa-heart-pulse"

class SupportedExerciseAdmin(ModelView, model=SupportedExercise):
    column_list = [SupportedExercise.id, SupportedExercise.name, SupportedExercise.is_active]
    icon = "fa-solid fa-list-check"

# Register admin views
admin.add_view(UserAdmin)
admin.add_view(WorkoutAdmin)
admin.add_view(ActivityAdmin)
admin.add_view(HealthMetricAdmin)
admin.add_view(SupportedExerciseAdmin)
