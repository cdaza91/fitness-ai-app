import os
import json
import logging
from typing import Dict, Any, List, Optional
from garminconnect import Garmin
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.core.db import SessionLocal

from garminconnect.workout import (
    RunningWorkout,
    create_warmup_step,
    create_interval_step,
    create_cooldown_step, 
    WorkoutSegment,
)

from garth.exc import GarthHTTPError
from app.domains.users.models import Activity, HealthMetric, WorkoutPlan, WorkoutDay, User

# Configure logging
logger = logging.getLogger(__name__)

# Constants for Garmin Target Types
TARGET_TYPE_NO_TARGET = {"targetTypeId": 1, "targetTypeKey": "no.target"}
TARGET_TYPE_PACE_ZONE = {"targetTypeId": 4, "targetTypeKey": "pace.zone"}

def get_garmin_client(email: str, password: str) -> Garmin:
    """Authenticates and returns a Garmin client with token persistence."""
    safe_email = email.replace("@", "_").replace(".", "_")
    token_dir = f"./.garmin_tokens_{safe_email}"
    
    try:
        client = Garmin(email, password)
        if os.path.exists(token_dir):
            client.login(token_dir)
        else:
            client.login()
            client.garth.dump(token_dir)
        return client
    except Exception as e:
        logger.error(f"Garmin Authentication Error: {e}")
        raise ValueError(f"Fallo de inicio de sesión en Garmin: {str(e)}")


def sync_garmin_data(email: str, password: str) -> Dict[str, Any]:
    """Syncs health metrics and recent activities from Garmin and saves to DB."""
    try:
        client = get_garmin_client(email, password)
        today = date.today()
        db = SessionLocal()
        user = db.query(User).filter(User.garmin_email == email).first()
        
        if not user:
            db.close()
            return {"status": "error", "message": "User not found"}

        # 1. Sync Health Metrics (Last 7 days to be safe)
        for i in range(7):
            curr_date = today - timedelta(days=i)
            curr_date_str = curr_date.isoformat()
            
            stats = client.get_stats(curr_date_str)
            body = client.get_body_composition(curr_date_str)
            sleep = client.get_sleep_data(curr_date_str)

            # Update or create HealthMetric
            metric = db.query(HealthMetric).filter(
                HealthMetric.user_id == user.id,
                HealthMetric.date == curr_date
            ).first()
            
            if not metric:
                metric = HealthMetric(user_id=user.id, date=curr_date, source="garmin")
                db.add(metric)
            
            # Extract data safely
            metric.resting_heart_rate = stats.get("restingHeartRate")
            metric.steps = stats.get("totalSteps")
            
            if body and "totalWeight" in body:
                metric.weight_kg = body["totalWeight"] / 1000.0 if body["totalWeight"] > 1000 else body["totalWeight"]
            
            if sleep and "dailySleepDTO" in sleep:
                sleep_dto = sleep["dailySleepDTO"]
                metric.sleep_hours = sleep_dto.get("sleepTimeSeconds", 0) / 3600.0
                metric.sleep_score = sleep_dto.get("sleepScore")

        # 2. Sync Activities
        activities = client.get_activities(0, 10)
        for act in activities:
            external_id = str(act["activityId"])
            existing = db.query(Activity).filter(Activity.external_id == external_id).first()
            if not existing:
                new_act = Activity(
                    user_id=user.id,
                    external_id=external_id,
                    source="garmin",
                    activity_type=act.get("activityType", {}).get("typeKey"),
                    name=act.get("activityName"),
                    date=datetime.fromisoformat(act["startTimeLocal"].replace(" ", "T")),
                    distance_meters=act.get("distance"),
                    duration_seconds=act.get("duration"),
                    average_heart_rate=act.get("averageHR"),
                    calories=act.get("calories"),
                    json_data=json.dumps(act)
                )
                db.add(new_act)

        db.commit()
        db.close()
        
        return {
            "status": "success",
            "message": "Data synced from Garmin"
        }
    except Exception as e:
        logger.error(f"Garmin Sync Error: {e}")
        raise


def pace_to_mps(pace_str: Optional[str]) -> Optional[float]:
    """Converts MM:SS min/km string to meters per second."""
    if not pace_str or ":" not in pace_str:
        return None
    try:
        minutes, seconds = map(int, pace_str.split(":"))
        total_seconds = (minutes * 60) + seconds
        if total_seconds == 0:
            return None
        return 1000 / total_seconds
    except (ValueError, ZeroDivisionError) as e:
        logger.warning(f"Error converting pace {pace_str}: {e}")
        return None


def _create_running_step(ex: Dict[str, Any], step_order: int) -> Any:
    """Creates a Garmin workout step for a running exercise."""
    duration = float(ex.get("duration_s", 60))
    ex_type = ex.get("type", "active").lower()
    
    low_speed = pace_to_mps(ex.get("target_min"))
    high_speed = pace_to_mps(ex.get("target_max"))
    
    target_type = TARGET_TYPE_NO_TARGET
    if low_speed and high_speed:
        target_type = {
            **TARGET_TYPE_PACE_ZONE,
            "targetValueOne": low_speed,
            "targetValueTwo": high_speed
        }

    if "warmup" in ex_type:
        return create_warmup_step(duration, step_order=step_order, target_type=target_type)
    elif "cooldown" in ex_type:
        return create_cooldown_step(duration, step_order=step_order, target_type=target_type)
    else:
        return create_interval_step(duration, step_order=step_order, target_type=target_type)


def push_specific_workout_day(client: Garmin, workout_model: WorkoutPlan, day_index: int) -> bool:
    """Pushes a specific day of a workout plan to the Garmin calendar."""
    try:
        data = workout_model.json_data
        if isinstance(data, str):
            data = json.loads(data)

        routines = data.get("daily_routines", [])
        routine = next((r for r in routines if r.get("day") == day_index), None)
        
        if not routine:
            logger.warning(f"Day {day_index} not found in workout plan {workout_model.id}")
            return False

        training_type = workout_model.training_type or "strength"
        
        garmin_steps = []
        total_duration = 0
        
        for i, ex in enumerate(routine.get("exercises", [])):
            if training_type == "running":
                step = _create_running_step(ex, i)
                total_duration += float(ex.get("duration_s", 60))
                garmin_steps.append(step)
            else:
                # Generic step for strength/others
                duration = float(ex.get("duration_s", 60)) if "duration_s" in ex else 60
                total_duration += duration
                step = create_interval_step(duration, step_order=i, target_type=TARGET_TYPE_NO_TARGET)
                garmin_steps.append(step)

        sport_key = "running" if training_type == "running" else "strength"
        workout_name = f"Fit_{training_type[:4]}_{day_index}"[:15]
        
        segment = WorkoutSegment(
            segmentOrder=1,
            sportType={"sportTypeKey": sport_key},
            workoutSteps=garmin_steps
        )

        if training_type == "running":
            garmin_workout = RunningWorkout(
                workoutName=workout_name,
                estimatedDurationInSecs=total_duration,
                workoutSegments=[segment]
            )
            upload_response = client.upload_workout(garmin_workout.as_dict())
        else:
            workout_dict = {
                "workoutName": workout_name,
                "sportType": {"sportTypeKey": sport_key},
                "workoutSegments": [segment.as_dict() if hasattr(segment, 'as_dict') else segment]
            }
            upload_response = client.upload_workout(workout_dict)

        new_workout_id = upload_response.get("workoutId")
        if new_workout_id:
            client.schedule_workout(new_workout_id, date.today().isoformat())
            logger.info(f"Successfully scheduled Garmin workout {new_workout_id} for today")
            return True

        return False

    except GarthHTTPError as e:
        msg = e.error.response.text if hasattr(e, 'error') and hasattr(e.error, 'response') else str(e)
        logger.error(f"Garmin API Error: {msg}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error pushing workout to Garmin: {e}")
        return False
