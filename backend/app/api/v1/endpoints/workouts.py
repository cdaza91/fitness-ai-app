import asyncio
import base64
from fastapi import APIRouter, HTTPException
from app.domains.workouts.service import generate_workout_from_ai
from app.domains.workouts.youtube_service import get_exercise_video_id
from app.domains.workouts.posture_service import analyze_posture

router = APIRouter()

@router.post("/generate")
async def create_workout(user_info: dict):
    try:
        plan = generate_workout_from_ai(user_info)
        workout_dict = plan.model_dump()
        for day in workout_dict.get("daily_routines", []):
            tasks = [get_exercise_video_id(ex["search_term"]) for ex in day["exercises"]]
            video_ids = await asyncio.gather(*tasks)
            for i, exercise in enumerate(day["exercises"]):
                exercise["youtube_id"] = video_ids[i] or "dQw4w9WgXcQ"
        return workout_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al generar rutina")

@router.post("/analyze-posture")
async def analyze_pose(data: dict):
    try:
        image_bytes = base64.b64decode(data['image'])
        result = analyze_posture(image_bytes, data.get('exercise', 'General'))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))