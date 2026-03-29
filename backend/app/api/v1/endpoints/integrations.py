import logging
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.domains.integrations.garmin_service import sync_garmin_data, push_specific_workout_day, get_garmin_client
from app.domains.users.models import User, Workout
from app.domains.users.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

class GarminCredentials(BaseModel):
    """Schema for Garmin authentication credentials."""
    email: EmailStr
    password: str

class PushWorkoutRequest(BaseModel):
    """Schema for pushing a specific day's workout to Garmin."""
    day_index: int


@router.post("/integrations/garmin/sync", status_code=status.HTTP_200_OK)
async def trigger_garmin_sync(
    creds: GarminCredentials,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the user's Garmin credentials and performs an initial data synchronization.
    """
    try:
        # 1. Update and persist credentials
        current_user.garmin_email = creds.email
        current_user.garmin_password = creds.password
        db.add(current_user)
        db.commit()

        # 2. Perform the initial sync
        logger.info(f"Triggering initial Garmin sync for user: {current_user.email}")
        sync_garmin_data(creds.email, creds.password)

        return {"status": "success", "message": "Credenciales guardadas y sincronización iniciada."}
    
    except ValueError as e:
        logger.error(f"Sync failed due to invalid credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Error al autenticar con Garmin. Verifique sus credenciales."
        )
    except Exception as e:
        logger.exception(f"Unexpected error during Garmin sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno al sincronizar con Garmin."
        )


@router.post("/integrations/garmin/push-workout")
async def push_workout_to_garmin(
        req: PushWorkoutRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Pushes the current user's latest workout plan to their Garmin device.
    """
    # 1. Verify Garmin setup
    if not current_user.garmin_email or not current_user.garmin_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Su cuenta de Garmin no está vinculada. Ingrese sus credenciales primero."
        )

    # 2. Fetch latest workout
    workout = db.query(Workout).filter(
        Workout.user_id == current_user.id
    ).order_by(Workout.created_at.desc()).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No se encontró ningún plan de entrenamiento para subir a Garmin."
        )

    try:
        # 3. Authenticate and push
        logger.info(f"Pushing workout {workout.id} day {req.day_index} to Garmin for user {current_user.email}")
        client = get_garmin_client(current_user.garmin_email, current_user.garmin_password)
        
        success = push_specific_workout_day(client, workout, req.day_index)

        if success:
            return {
                "status": "success", 
                "message": f"Día {req.day_index} subido y programado en Garmin para hoy."
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail="No se pudo subir la rutina a Garmin. Verifique la compatibilidad del tipo de entrenamiento."
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error pushing workout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error inesperado al conectar con Garmin."
        )
