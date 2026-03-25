import json
import logging
import requests
import google.generativeai as genai
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.db import SessionLocal
from app.domains.integrations.garmin_service import sync_garmin_data
from app.domains.users.models import Workout, SupportedExercise, User
from app.domains.workouts.utils import generate_exercise_assets_with_ai
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_missing_exercises():
    db = SessionLocal()
    try:
        logger.info("--- 🕒 Iniciando tarea periódica: populate_missing_exercises ---")
        workouts = db.query(Workout).all()
        all_exercise_names = set()
        for w in workouts:
            for day in json.loads(w.json_data).get("daily_routines",{}):
                for ex in day.get("exercises",{}):
                    all_exercise_names.add(ex["name"])

        existing_names = [e.name for e in db.query(SupportedExercise).all()]
        missing_names = [name for name in all_exercise_names if name not in existing_names ]

        if not missing_names:
            return

        for name in missing_names:
            rules_json, video_url = generate_exercise_assets_with_ai(name)
            new_ex = SupportedExercise(
                name=name,
                rules_json=rules_json,
                video_url=video_url,
                is_active=True
            )
            db.add(new_ex)
        db.commit()

    finally:
        db.close()

def daily_garmin_sync():
    db = SessionLocal()
    users = db.query(User).filter(User.garmin_email != None).all()
    for user in users:
        try:
            data = sync_garmin_data(user.garmin_email, user.garmin_password)
        except Exception as e:
            print(f"Auto-sync failed for {user.email}: {e}")
    db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(populate_missing_exercises, 'interval', minutes=600)
scheduler.add_job(daily_garmin_sync, 'interval', minutes=1200)