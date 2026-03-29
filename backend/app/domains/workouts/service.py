import os
import json
import re
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from app.domains.users.models import User
from app.domains.workouts import prompts

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
def setup_environment():
    """Locates and loads the .env file."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        env_path = current / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            return
        current = current.parent

setup_environment()

# Unified schema for AI response
WORKOUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "target_goal": {"type": "string"},
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
                                "instructions": {"type": "string"},
                                "duration_s": {"type": "integer"},
                                "target_min": {"type": "string"},
                                "target_max": {"type": "string"},
                                "reps": {"type": "integer"},
                                "sets": {"type": "integer"},
                                "end_condition": {"type": "string"},
                                "end_condition_value": {"type": "integer"}
                            },
                            "required": ["name", "type", "instructions"]
                        }
                    }
                },
                "required": ["day", "focus", "exercises"]
            }
        }
    },
    "required": ["title", "daily_routines"]
}

_model = None

def get_best_available_model() -> str:
    """Returns the name of the best available generative model (prefers 'flash')."""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return next((m for m in available_models if 'flash' in m), available_models[0])
    except Exception as e:
        logger.error(f"Error listing AI models: {e}")
        return "models/gemini-1.5-flash"  # Fallback

def get_ai_model():
    """Lazily initializes the Google Generative AI model."""
    global _model
    if _model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment")
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        
        try:
            model_name = get_best_available_model()
            _model = genai.GenerativeModel(
                model_name,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=WORKOUT_SCHEMA,
                    temperature=0.7
                )
            )
            logger.info(f"Initialized AI model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize AI model: {e}")
            raise

    return _model


def _extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extracts JSON content from the AI response string."""
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode AI response as JSON: {e}. Raw text: {response_text}")
        raise ValueError("Invalid AI response format")


def generate_running_workout(user: User) -> Dict[str, Any]:
    """Generates a personalized running workout plan."""
    logger.info(f"Generating running workout for user: {user.email}")
    prompt = prompts.RUNNING_COACH_PROMPT.format(
        target_race_distance=user.target_race_distance or "Unknown",
        target_race_date=user.target_race_date or "Soon",
        easy_pace=user.easy_pace or "6:00",
        fitness_level=user.fitness_level or "Beginner",
        days_per_week=user.days_per_week or 3
    )
    model = get_ai_model()
    response = model.generate_content(prompt)
    return _extract_json_from_response(response.text)


def generate_strength_workout(user: User) -> Dict[str, Any]:
    """Generates a personalized strength and hypertrophy workout plan."""
    logger.info(f"Generating strength workout for user: {user.email}")
    equipment = user.equipment_access or "Full Gym"
    prompt = prompts.STRENGTH_COACH_PROMPT.format(
        age=user.age or 30,
        weight=user.weight or 70,
        fitness_level=user.fitness_level or "Beginner",
        primary_goal=user.primary_goal or "Fitness",
        equipment=equipment,
        days_per_week=user.days_per_week or 3
    )
    model = get_ai_model()
    response = model.generate_content(prompt)
    return _extract_json_from_response(response.text)


def generate_workout(user: User, training_type: str) -> Dict[str, Any]:
    """Orchestrates workout generation based on training type."""
    if training_type == "running":
        return generate_running_workout(user)
    else:
        # Default to strength for other types
        return generate_strength_workout(user)
