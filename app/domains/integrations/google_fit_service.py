import logging
import requests
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.core.config import settings
from app.domains.users.models import HealthMetric, User

# Configure logging
logger = logging.getLogger(__name__)

# Google OAuth/Fit URLs
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_FIT_URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"

def refresh_google_token(user: User, db: Session) -> Optional[str]:
    """Refreshes the Google OAuth2 access token."""
    if not user.google_fit_refresh_token:
        return None
    
    payload = {
        "grant_type": "refresh_token",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": user.google_fit_refresh_token
    }
    
    try:
        response = requests.post(GOOGLE_TOKEN_URL, data=payload)
        response.raise_for_status()
        data = response.json()
        
        user.google_fit_access_token = data.get("access_token")
        db.add(user)
        db.commit()
        return user.google_fit_access_token
    except Exception as e:
        logger.error(f"Google Token Refresh Error: {e}")
        return None

def sync_google_fit_data(user_id: int):
    """Syncs health data (steps, weight, sleep) from Google Fit."""
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.google_fit_access_token:
        db.close()
        return
    
    access_token = user.google_fit_access_token
    
    # Time range: Last 7 days
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Aggregate daily steps, weight, and heart rate
    request_body = {
        "aggregateBy": [
            {"dataTypeName": "com.google.step_count.delta"},
            {"dataTypeName": "com.google.weight.summary"},
            {"dataTypeName": "com.google.heart_rate.summary"}
        ],
        "bucketByTime": {"durationMillis": 86400000}, # 1 day
        "startTimeMillis": int(start_time.timestamp() * 1000),
        "endTimeMillis": int(end_time.timestamp() * 1000)
    }
    
    try:
        response = requests.post(GOOGLE_FIT_URL, headers=headers, json=request_body)
        if response.status_code == 401:
            access_token = refresh_google_token(user, db)
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                response = requests.post(GOOGLE_FIT_URL, headers=headers, json=request_body)
            else:
                db.close()
                return

        response.raise_for_status()
        data = response.json()
        
        for bucket in data.get("bucket", []):
            start_ms = int(bucket.get("startTimeMillis"))
            curr_date = date.fromtimestamp(start_ms / 1000)
            
            metric = db.query(HealthMetric).filter(
                HealthMetric.user_id == user.id,
                HealthMetric.date == curr_date
            ).first()
            
            if not metric:
                metric = HealthMetric(user_id=user.id, date=curr_date, source="google_fit")
                db.add(metric)
            
            for dataset in bucket.get("dataset", []):
                for point in dataset.get("point", []):
                    data_type = point.get("dataTypeName", "")
                    
                    # Step count
                    if "step_count" in data_type:
                        for value in point.get("value", []):
                            metric.steps = (metric.steps or 0) + value.get("intVal", 0)
                    
                    # Weight
                    elif "weight" in data_type:
                        for value in point.get("value", []):
                            metric.weight_kg = value.get("fpVal")
                    
                    # Heart Rate (Resting HR estimation)
                    elif "heart_rate" in data_type:
                        for value in point.get("value", []):
                            # Usually summary has min, max, average. Use min as a proxy for resting if needed
                            min_hr = value.get("mapVal", [])
                            # mapVal contains entries for "min", "max", "average"
                            for entry in value.get("mapVal", []):
                                if entry.get("key") == "min":
                                    metric.resting_heart_rate = int(entry.get("value", {}).get("fpVal", 0))

        db.commit()
    except Exception as e:
        logger.error(f"Google Fit Sync Error: {e}")
    finally:
        db.close()
