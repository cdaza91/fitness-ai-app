import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from .schemas import WorkoutPlan

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_best_available_model() -> str:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    for model_name in available_models:
        if 'flash' in model_name: return model_name
    return available_models[0]

def generate_workout_from_ai(user_data: dict) -> WorkoutPlan:
    model = genai.GenerativeModel(get_best_available_model())
    exercise_list = "Push-up, Squat, Deadlift, Bench Press, Pull-up, Overhead Press, Bicep Curl, Tricep Dip, Plank, Lunge, Burpee, Mountain Climber, Leg Press, Lateral Raise, Hammer Curl, Skull Crusher, Leg Extension, Leg Curl, Calf Raise, Russian Twist, Sit-up, Crunch, Hanging Leg Raise, Lat Pulldown, Bent Over Row"
    prompt = f"""
    Eres un entrenador personal. Genera una rutina basada en:
    - Objetivo: {user_data.get('goal')}
    - Músculos: {', '.join(user_data.get('muscles', []))}
    - Equipo: {user_data.get('location')}
    REGLA ESTRICTA: Para el campo "name", usa SOLO nombres de esta lista: [{exercise_list}].
    Devuelve un JSON con esta estructura:
    {{
      "workout_plan": {{
        "title": "...",
        "target_goal": "...",
        "daily_routines": [
          {{
            "day": "Día 1",
            "focus": "...",
            "exercises": [
              {{ "name": "NombreDeLista", "muscle_group": "...", "sets": 4, "reps": "12", "rest_seconds": 60, "instructions": "...", "search_term": "..." }}
            ]
          }}
        ]
      }}
    }}
    Responde SOLO el JSON.
    """
    response = model.generate_content(prompt)
    raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        parsed_data = json.loads(raw_text)
        workout_data = parsed_data.get("workout_plan", parsed_data)
        return WorkoutPlan.model_validate(workout_data)
    except Exception as e:
        raise Exception(f"Error parseando rutina: {e}")