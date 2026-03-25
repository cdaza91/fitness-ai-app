from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.db import engine, Base
from sqladmin import Admin, ModelView
from app.domains.users.models import SupportedExercise, User, Workout, HealthMetric, Activity
from app.core.tasks import scheduler

app = FastAPI(title="FitCheck AI API")
# 1. Initialize Tables
Base.metadata.create_all(bind=engine)

# 2. Background Task

@app.on_event("startup")
async def startup_event():
    if not scheduler.running:
        scheduler.start()


# 3. FastAPI App Setup


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# 4. Correct Admin Views (Fixed Syntax)
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

# Register the views correctly
admin.add_view(UserAdmin)
admin.add_view(WorkoutAdmin)
admin.add_view(ActivityAdmin)
admin.add_view(HealthMetricAdmin)
admin.add_view(SupportedExerciseAdmin)