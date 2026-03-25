import os
import json
import re
from datetime import date, timedelta
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.domains.users.models import User
from app.domains.integrations.garmin_service import get_grouped_garmin_context

workout_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "daily_routines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer"},
                    "focus": {"type": "string"},
                    "exercises": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "duration_s": {"type": "integer"},
                                "target_min": {"type": "string"},
                                "target_max": {"type": "string"},
                                "instructions": {"type": "string"}
                            },
                            "required": ["name", "type", "instructions", "duration_s", "target_min", "target_max"]
                        }
                    }
                },
                "required": ["day", "focus", "exercises"]
            }
        }
    },
    "required": ["title", "daily_routines"]
}


# Environment setup
def find_dotenv():
    current = Path(__file__).resolve().parent
    for _ in range(5):
        check_path = current / '.env'
        if check_path.exists(): return check_path
        current = current.parent
    return None


load_dotenv(dotenv_path=find_dotenv())
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)


def get_best_available_model() -> str:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    for model_name in available_models:
        if 'flash' in model_name: return model_name
    return available_models[0]


def generate_workout_from_ai(user: User, training_type: str, db: Session):
    config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=workout_schema,
        temperature=0.7  # Optional: keep it creative but focused
    )
    model = genai.GenerativeModel(get_best_available_model(), generation_config=config)

    if training_type == "running":
        prompt = f"""
            ROLE: You are an elite Running Coach. 
            
            CONTEXT: 
            - User Goal: {user.target_race_distance}
            - Competition Date: {user.target_race_date}
            - Current Base Pace (Easy/LSD): {user.easy_pace} min/km
            - Fitness Level: {user.fitness_level}
            
            COACHING LOGIC & PACE RULES:
            You must generate a workout based on the training phase (Base, Build, Peak, Taper). 
            Paces must be calculated relative to the Base Pace ({user.easy_pace}min/Km):
            
            1. LONG RUNS (LSD): 'type' is 'active'. Pace = Base Pace or 5% slower. Focus on volume.
            2. TEMPO RUNS: 'type' is 'active'. Pace = 5-10% faster than Base Pace (e.g., if 9:00, Tempo is ~8:15-8:30).
            3. INTERVALS: 'type' is 'active'. Pace = 15-20% faster than Base Pace (e.g., if 9:00, Interval is ~7:15-7:45).
            4. RECOVERY: 'type' is 'recovery'. Pace = 10% slower than Base Pace.
    
            STRICT OUTPUT RULES:
            - Use MM:SS format for all target_min and target_max values.
            - target_max is the FASTER pace (lower number), target_min is the SLOWER pace (higher number).
            - Descriptions must be under 50 characters to comply with Garmin watch limits.
            - If the workout is a Long Run, do not use short intervals; use one or two long 'active' blocks.
            """
    else:
        equipment = ", ".join(user.equipment_access) if user.equipment_access else "Full Gym"
        prompt = f"""
        ROLE: Expert Hypertrophy & Strength Coach (Garmin Workout Specialist).
        USER PROFILE: {user.age}yo, {user.weight}kg. Level: {user.fitness_level}.
        GOAL: {user.primary_goal}. Equipment: {equipment}.
        SCHEDULE: {user.days_per_week} days/week.

        STRICT RULES:
        1. "day" MUST BE NUMERIC: 0 for Monday, 1 for Tuesday, 2 for Wednesday, 3 for Thursday, 4 for Friday, 5 for Saturday, 6 for Sunday.
        2. Combine Warmup, Main Exercises, and Cooldown in ONE day routine.
        3. Use "reps" or "duration_s" for end_condition.

        JSON OUTPUT FORMAT:
        {{
          "title": "Garmin Strength Plan",
          "target_goal": "{user.primary_goal}",
          "daily_routines": [
            {{
              "day": 0,
              "focus": "Upper Body",
              "exercises": [
                {{ "name": "Pushups", "type": "warmup", "reps": 15, "instructions": "Warmup sets" }},
                {{ "name": "Bench Press", "type": "active", "end_condition": "reps", "end_condition_value": 10, "sets": 3 }}
              ]
            }}
          ]
        }}
        """

    response = model.generate_content(prompt)

    # Extract JSON logic
    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return json.loads(response.text)