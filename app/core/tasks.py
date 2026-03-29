import json
import logging
from contextlib import contextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.db import SessionLocal
from app.core.config import settings
from app.domains.integrations.garmin_service import sync_garmin_data
from app.domains.users.models import WorkoutPlan, SupportedExercise, User
from app.domains.workouts.utils import generate_exercise_assets_with_ai

# Configure logging
logger = logging.getLogger(__name__)

@contextmanager
def db_session():
    """Context manager for database sessions, especially for background tasks."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error during background task database session: {e}")
        raise
    finally:
        db.close()


def populate_missing_exercises():
    """Identifies and adds rules for exercises found in workouts but missing in configuration."""
    logger.info("--- 🕒 Starting background task: populate_missing_exercises ---")
    
    with db_session() as db:
        try:
            # 1. Gather all exercise names used in current workouts
            workouts = db.query(WorkoutPlan).all()
            all_exercise_names = set()
            for w in workouts:
                try:
                    routine_data = json.loads(w.json_data)
                    for day in routine_data.get("daily_routines", []):
                        for ex in day.get("exercises", []):
                            all_exercise_names.add(ex["name"].lower())
                except (json.JSONDecodeError, AttributeError, KeyError) as e:
                    logger.warning(f"Malformed workout data (ID: {w.id}): {e}")

            # 2. Filter out already supported exercises
            existing_names = [e.name for e in db.query(SupportedExercise).all()]
            missing_names = [name for name in all_exercise_names if name not in existing_names]

            if not missing_names:
                logger.info("No missing exercises to populate.")
                return

            # 3. Use AI to generate assets/rules for missing ones
            for name in missing_names:
                logger.info(f"Populating rules for missing exercise: {name}")
                rules_json, video_url = generate_exercise_assets_with_ai(name)
                new_ex = SupportedExercise(
                    name=name,
                    rules_json=rules_json,
                    video_url=video_url,
                    is_active=True
                )
                db.add(new_ex)
                
            logger.info(f"Successfully populated {len(missing_names)} exercises.")
            
        except Exception as e:
            logger.error(f"Failed to populate missing exercises: {e}")


def daily_garmin_sync():
    """Triggers automated daily sync for all users with linked Garmin accounts."""
    logger.info("--- 🕒 Starting background task: daily_garmin_sync ---")
    
    with db_session() as db:
        users = db.query(User).filter(User.garmin_email != None).all()
        for user in users:
            try:
                logger.info(f"Auto-syncing data for user: {user.email}")
                sync_garmin_data(user.garmin_email, user.garmin_password)
            except Exception as e:
                logger.error(f"Automated Garmin sync failed for {user.email}: {e}")

# Scheduler initialization
scheduler = BackgroundScheduler()

# Add jobs with configurable intervals
scheduler.add_job(
    populate_missing_exercises, 
    'interval', 
    minutes=settings.POPULATE_EXERCISES_INTERVAL_MINUTES
)
scheduler.add_job(
    daily_garmin_sync, 
    'interval', 
    minutes=settings.GARMIN_SYNC_INTERVAL_MINUTES
)
