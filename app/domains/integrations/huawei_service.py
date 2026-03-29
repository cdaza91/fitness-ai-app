import logging
import requests
from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.domains.users.models import HealthMetric, User

# Configure logging
logger = logging.getLogger(__name__)

# Huawei API configuration (should be in settings)
HUAWEI_OAUTH_TOKEN_URL = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
HUAWEI_HEALTH_URL = "https://health-api.cloud.huawei.com/healthkit/v1"

def refresh_huawei_token(user: User, db: Session) -> Optional[str]:
    """Refreshes the Huawei access token using the refresh token."""
    if not user.huawei_refresh_token:
        return None
    
    payload = {
        "grant_type": "refresh_token",
        "client_id": "YOUR_HUAWEI_CLIENT_ID", # Should be in settings
        "client_secret": "YOUR_HUAWEI_CLIENT_SECRET", # Should be in settings
        "refresh_token": user.huawei_refresh_token
    }
    
    try:
        response = requests.post(HUAWEI_OAUTH_TOKEN_URL, data=payload)
        response.raise_for_status()
        data = response.json()
        
        user.huawei_access_token = data.get("access_token")
        if data.get("refresh_token"):
            user.huawei_refresh_token = data.get("refresh_token")
        
        db.add(user)
        db.commit()
        return user.huawei_access_token
    except Exception as e:
        logger.error(f"Huawei Token Refresh Error: {e}")
        return None

def sync_huawei_scale_data(user_id: int):
    """Syncs body composition data from Huawei Health Kit (Scale data)."""
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.huawei_access_token:
        db.close()
        return
    
    # We might need to refresh token before starting
    access_token = user.huawei_access_token
    
    # Define time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    # Convert to milliseconds for Huawei API
    start_time_ms = int(start_time.timestamp() * 1000)
    end_time_ms = int(end_time.timestamp() * 1000)
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Data type for body composition (scale data)
    # Ref: https://developer.huawei.com/consumer/en/doc/development/HMSCore-References/health-data-type-weight-0000001050071477
    data_type = "com.huawei.continuous.weight"
    
    url = f"{HUAWEI_HEALTH_URL}/dataCollectors/derived:{data_type}:com.huawei.health:weight_data/dataSets/{start_time_ms}-{end_time_ms}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 401: # Unauthorized, try refreshing
            access_token = refresh_huawei_token(user, db)
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                response = requests.get(url, headers=headers)
            else:
                db.close()
                return

        response.raise_for_status()
        data = response.json()
        
        # Process weight points
        for point in data.get("point", []):
            timestamp_ms = int(point.get("startTimeNanos", 0)) // 1000000
            data_date = date.fromtimestamp(timestamp_ms / 1000)
            
            # Find or create metric
            metric = db.query(HealthMetric).filter(
                HealthMetric.user_id == user.id,
                HealthMetric.date == data_date
            ).first()
            
            if not metric:
                metric = HealthMetric(user_id=user.id, date=data_date, source="huawei")
                db.add(metric)
            
            # Process values
            for value in point.get("value", []):
                val_float = value.get("floatVal")
                # Map based on field index in weight data type
                # 0: weight, 1: BMI, 2: Body fat rate, 3: Muscle mass, etc.
                # Note: This mapping is simplified, check Huawei docs for exact indices
                pass # Logic to map fields to metric.weight_kg, metric.body_fat_pct, metric.muscle_mass_kg

        db.commit()
    except Exception as e:
        logger.error(f"Huawei Scale Sync Error: {e}")
    finally:
        db.close()
