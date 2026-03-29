import os
import json
import re
import logging
from typing import Dict, Any, List, Optional
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

def get_best_available_model():
    """Dynamically finds the best model available from the API and its capabilities."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment")
        raise ValueError("GEMINI_API_KEY not found in environment")
    
    genai.configure(api_key=api_key)
    
    try:
        available_models = list(genai.list_models())
        supported_models = [m for m in available_models if 'generateContent' in m.supported_generation_methods]
        logger.info(available_models)
        logger.info(supported_models)
        # Priority map for selection
        priority_keywords = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']
        logger.info(priority_keywords)
        selected_model = None
        for keyword in priority_keywords:
            selected_model = next((m for m in supported_models if keyword in m.name), None)
            if selected_model:
                break
        
        if not selected_model:
            selected_model = supported_models[0] if supported_models else None
            
        if not selected_model:
            raise ValueError("No suitable Gemini model found via API")
            
        logger.info(f"Dynamically selected model: {selected_model.name}")
        return selected_model
    except Exception as e:
        logger.error(f"Error listing AI models: {e}")
        # Return a dummy model object with at least a name for fallback
        class DummyModel:
            name = "models/gemini-pro"
        return DummyModel()

def get_ai_model():
    """Lazily initializes the Google Generative AI model with dynamic capability checking."""
    global _model
    if _model is None:
        try:
            model_info = get_best_available_model()
            model_name = model_info.name
            
            # Capability checking: Gemini 1.5+ usually supports JSON schema
            # We also check for 'flash' or 'pro' and version numbers
            supports_schema = any(v in model_name for v in ["1.5", "2.0"])
            
            generation_config = {"temperature": 0.7}
            
            if supports_schema:
                generation_config["response_mime_type"] = "application/json"
                generation_config["response_schema"] = WORKOUT_SCHEMA
                logger.info(f"Model {model_name} supports schema-based generation.")
            else:
                logger.info(f"Model {model_name} does not support schema-based generation, using prompt-based extraction.")

            _model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(**generation_config)
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize AI model: {e}")
            # Ultra-safe fallback
            _model = genai.GenerativeModel("models/gemini-pro")
            
    return _model


def _extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extracts JSON content from the AI response string."""
    try:
        # Try to find JSON block if AI wrapped it in markdown
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
            
        # Try generic curly brace match
        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
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


def generate_adaptive_workout_update(
    user: User, 
    training_type: str,
    original_plan_json: str,
    completed_sessions: List[Dict[str, Any]],
    missed_sessions: List[Dict[str, Any]],
    performance_metrics: Dict[str, Any],
    health_metrics: List[Dict[str, Any]],
    activities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generates an updated workout plan based on the user's performance and metrics."""
    logger.info(f"Generating adaptive workout update for user: {user.email}")
    
    prompt = prompts.ADAPTIVE_REPLANNING_PROMPT.format(
        training_type=training_type,
        primary_goal=user.primary_goal or "Fitness",
        original_plan=original_plan_json,
        completed_sessions=json.dumps(completed_sessions),
        missed_sessions=json.dumps(missed_sessions),
        performance_metrics=json.dumps(performance_metrics),
        health_metrics=json.dumps(health_metrics),
        activities=json.dumps(activities)
    )
    
    model = get_ai_model()
    response = model.generate_content(prompt)
    return _extract_json_from_response(response.text)
