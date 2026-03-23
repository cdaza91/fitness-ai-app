import os
import json
import re
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from .schemas import WorkoutPlan

def find_dotenv():
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Busca hasta 5 niveles hacia arriba
        check_path = current / '.env'
        if check_path.exists():
            return check_path
        current = current.parent
    return None

ruta_env = find_dotenv()
load_dotenv(dotenv_path=ruta_env)
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    raise FileNotFoundError(f"No se encontró el .env o la variable en: {ruta_env}")


def get_best_available_model() -> str:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    for model_name in available_models:
        if 'flash' in model_name: return model_name
    return available_models[0]


def generate_workout_from_ai(user_data: dict) -> WorkoutPlan:
    model = genai.GenerativeModel(get_best_available_model())

    # Lista estricta para que el mapeo de postura funcione
    exercise_list = "Push-up, Squat, Deadlift, Bench Press, Pull-up, Overhead Press, Bicep Curl, Tricep Dip, Plank, Lunge, Burpee"

    prompt = f"""
    Eres un entrenador personal. Genera una rutina en JSON para un usuario de {user_data.get('weight')}kg.
    Objetivo: {user_data.get('goal')}
    Lugar: {user_data.get('location')}

    REGLA: Usa solo estos nombres de ejercicios: [{exercise_list}].

    Responde ÚNICAMENTE el JSON con esta estructura exacta:
    {{
      "title": "Nombre de la rutina",
      "target_goal": "Objetivo",
      "daily_routines": [
        {{
          "day": "Día 1",
          "focus": "Pecho y Brazo",
          "exercises": [
            {{
              "name": "Push-up",
              "muscle_group": "Pecho",
              "sets": 4,
              "reps": "12",
              "rest_seconds": 60,
              "instructions": "Baja despacio",
              "search_term": "push up form"
            }}
          ]
        }}
      ]
    }}
    """

    response = model.generate_content(prompt)
    text = response.text

    # Limpieza extrema de Markdown y basura
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if not json_match:
        raise Exception(f"La IA no devolvió un JSON válido: {text}")

    raw_json = json_match.group(0)

    try:
        data = json.loads(raw_json)
        # Si la IA envolvió todo en un objeto "workout_plan", lo extraemos
        if "workout_plan" in data:
            data = data["workout_plan"]

        return WorkoutPlan.model_validate(data)
    except Exception as e:
        print(f"DEBUG - Error de validación: {e}")
        print(f"DEBUG - JSON recibido: {raw_json}")
        raise e