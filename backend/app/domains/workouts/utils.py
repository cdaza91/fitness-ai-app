import google.generativeai as genai
from sqlalchemy.orm import Session

import logging
from app.domains.users.models import SupportedExercise
from app.domains.workouts import youtube_service
from app.domains.workouts.service import get_best_available_model
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SILICON_FLOW_KEY = "sk-hcfcvllhwwcsckwjsllqeiwbhxofapcyonlgtbthpjpbqemv"


def generate_exercise_assets_with_ai(ex_name: str):
    """
    Usa IA para definir cómo se mide este ejercicio y genera un video demostrativo.
    """
    model = genai.GenerativeModel(get_best_available_model())

    pose_prompt = f"""
    ROLE: Biomechanics and MediaPipe Pose API Expert.
    EXERCISE: {ex_name}
    TASK: Identify the 3 key MediaPipe landmark indices (0-32) to measure the primary joint angle for this exercise. 
    Define the 'down' and 'up' angle thresholds to count a successful repetition.

    OUTPUT: Return ONLY a valid JSON object with this structure:
    {{
        "target_joints": [index1, index2, index3],
        "down_stage": {{"condition": "<", "angle": 90}},
        "up_stage": {{"condition": ">", "angle": 160}},
        "feedback_msgs": {{"down": "Lower your hips", "up": "Extend fully"}}
    }}
    """
    rules_json = None
    try:
        res = model.generate_content(pose_prompt)
        rules_json = res.text.strip()
    except Exception as e:
        logging.error(f"Error generating pose rules: {e}")


    video_url = None
    try:
        video_url = youtube_service.get_exercise_video_id(ex_name)
    except Exception as e:
        logger.error(f"Error Video ({ex_name}): {e}")

    return rules_json, video_url


def enrich_workout_with_posture_check(workout_data: dict, db: Session):
    if not workout_data:
        return None

    supported_records = db.query(SupportedExercise).filter(SupportedExercise.is_active == True).all()

    supported_map = {rec.name.lower(): rec for rec in supported_records}

    for day in workout_data.get("daily_routines", []):
        for ex in day.get("exercises", []):
            ex_name = ex["name"].lower()
            record = supported_map.get(ex_name)

            if record:
                ex["is_posture_supported"] = True if record.rules_json else False
                ex["video_url"] = record.video_url
            else:
                ex["is_posture_supported"] = False
                ex["video_url"] = None

    return workout_data