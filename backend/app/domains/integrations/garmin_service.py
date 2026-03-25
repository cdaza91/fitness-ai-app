import os
import json
import logging
from garminconnect import Garmin
from datetime import date

from garminconnect.workout import (
    RunningWorkout,
    create_warmup_step,
    create_interval_step,
    create_cooldown_step, WorkoutSegment, TargetType,
)

from garth.exc import GarthHTTPError
from sqlalchemy.orm import Session

from app.domains.users.models import Activity, HealthMetric


def sync_garmin_data(email: str, password: str):
    """Autentica y extrae métricas de salud y actividades de Garmin."""
    safe_email = email.replace("@", "_").replace(".", "_")
    token_dir = f"./.garmin_tokens_{safe_email}"
    try:
        client = Garmin(email, password)
        if os.path.exists(token_dir):
            client.login(token_dir)
        else:
            client.login()
            client.garth.dump(token_dir)

        today = date.today().isoformat()
        return {
            "status": "success",
            "date": today,
            "daily_stats": client.get_stats(today),
            "body_composition": client.get_body_composition(today),
            "recent_activities": client.get_activities(0, 10),
            "client": client
        }
    except Exception as e:
        logging.error(f"Garmin Sync Error: {e}")
        raise Exception(f"Fallo de inicio de sesión en Garmin: {str(e)}")


def get_grouped_garmin_context(user_id: int, db: Session):
    """Genera un resumen de historial para que el Prompt de la IA sea más inteligente."""
    activities = db.query(Activity).filter(Activity.user_id == user_id).order_by(Activity.date.desc()).limit(15).all()

    history_summary = []
    for a in activities:
        dist = f"{a.distance_meters / 1000:.1f}km" if a.distance_meters else ""
        history_summary.append(f"{a.date.date()}: {a.activity_type} {dist}")

    latest_metric = db.query(HealthMetric).filter(HealthMetric.user_id == user_id).order_by(
        HealthMetric.date.desc()).first()

    return {
        "recent_history": history_summary,
        "current_weight": latest_metric.weight if latest_metric else "Unknown"
    }

def pace_to_mps(pace_str: str):
    """Converts MM:SS min/km string to meters per second."""
    try:
        if not pace_str or ":" not in pace_str:
            return None
        minutes, seconds = map(int, pace_str.split(":"))
        total_seconds = (minutes * 60) + seconds
        if total_seconds == 0:
            return None
        # Speed (mps) = Distance (1000m) / Time (seconds)
        return 1000 / total_seconds
    except Exception as e:
        logging.error(f"Error converting pace {pace_str}: {e}")
        return None


def push_specific_workout_day(client, workout_model, day_index: int):
    try:
        data = workout_model.json_data
        if isinstance(data, str):
            data = json.loads(data)

        routines = data.get("daily_routines", [])
        if day_index >= len(routines):
            return False

        routine = routines[day_index]
        today_date = date.today()

        garmin_steps = []
        total_duration = 0
        for i, ex in enumerate(routine.get("exercises", [])):
            duration = float(ex.get("duration_s", 60))
            total_duration += duration
            description = (ex.get("instructions", "") or "")[:50]

            low_speed = pace_to_mps(ex.get("target_min"))
            high_speed = pace_to_mps(ex.get("target_max"))

            ex_type = ex.get("type", "active").lower()
            if "warmup" in ex_type:
                step = create_warmup_step(duration, step_order=i, target_type={
        "targetTypeId": 1,
        "targetTypeKey": "no.target"
    })
            elif "cooldown" in ex_type:
                step = create_cooldown_step(duration, step_order=i,target_type={
        "targetTypeId": 4,
        "targetTypeKey": "pace.zone",
                    "targetValueOne": low_speed,
                    "targetValueTwo": high_speed

    },)
            else:
                step = create_interval_step(duration, step_order=i, target_type={
        "targetTypeId": 4,
        "targetTypeKey": "pace.zone",
                    "targetValueOne": low_speed,
                    "targetValueTwo": high_speed

    })

            garmin_steps.append(step)
        segment = WorkoutSegment(
            segmentOrder=1,
            sportType={"sportTypeKey": "running"},
            workoutSteps=garmin_steps
        )

        workout = RunningWorkout(
            workoutName=f"FitCheck_{day_index}"[:15],
            estimatedDurationInSecs=total_duration,
            workoutSegments=[segment]
        )

        upload_response = client.upload_running_workout(workout)
        new_workout_id = upload_response.get("workoutId")

        if new_workout_id:
            client.schedule_workout(new_workout_id, today_date.isoformat())
            return True

        return False
    except GarthHTTPError as e:
        if hasattr(e, 'error') and hasattr(e.error, 'response'):
            logging.error(f"Garmin API Detail: {e.error.response.text}")
        else:
            logging.error(f"Push Workout Error: {e}")
        return False
    except Exception as e:
        logging.error(f"Push Workout Error: {str(e)}")
        return False