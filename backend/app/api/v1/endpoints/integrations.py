from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.domains.integrations.garmin_service import sync_garmin_data, push_specific_workout_day
from app.domains.users.models import User, Workout
from app.domains.users.routers import get_current_user

router = APIRouter()

class GarminCredentials(BaseModel):
    email: str
    password: str

@router.post("/integrations/garmin/sync")
async def trigger_garmin_sync(
    creds: GarminCredentials,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        current_user.garmin_email = creds.email
        current_user.garmin_password = creds.password
        db.add(current_user)
        db.commit()

        data = sync_garmin_data(creds.email, creds.password)

        return {"status": "success", "message": "Synced and uploaded to Garmin"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class PushWorkoutRequest(BaseModel):
    day_index: int


@router.post("/integrations/garmin/push-workout")
async def push_workout_to_garmin(
        req: PushWorkoutRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if not current_user.garmin_email or not current_user.garmin_password:
        raise HTTPException(status_code=400, detail="Garmin account not linked")

    workout = db.query(Workout).filter(Workout.user_id == current_user.id).order_by(Workout.created_at.desc()).first()
    if not workout:
        raise HTTPException(status_code=404, detail="No workout found to push")

    try:
        garmin_auth = sync_garmin_data(current_user.garmin_email, current_user.garmin_password)
        client = garmin_auth["client"]

        success = push_specific_workout_day(client, workout, req.day_index)

        if success:
            return {"status": "success", "message": f"Day {req.day_index} pushed to Garmin"}
        else:
            raise HTTPException(status_code=500, detail="Failed to upload workout steps")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))