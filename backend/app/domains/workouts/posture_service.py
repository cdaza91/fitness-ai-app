import cv2
import mediapipe as mp
import numpy as np
import os
import json
import logging
from typing import Dict, Any, Tuple
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from sqlalchemy.orm import Session
from app.domains.users.models import SupportedExercise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_detector = None

def get_detector():
    """Lazily initializes and returns the MediaPipe Pose Landmarker."""
    global _detector
    if _detector is None:
        model_path = os.path.join(os.path.dirname(__file__), 'pose_landmarker_heavy.task')
        if not os.path.exists(model_path):
            logger.error(f"Model file not found at {model_path}")
            raise FileNotFoundError(f"Model file not found at {model_path}")
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE
        )
        _detector = vision.PoseLandmarker.create_from_options(options)
    return _detector


def calculate_angle(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    """
    Calculates the angle between three points (a, b, c) where b is the vertex.
    Returns the angle in degrees (0-180).
    """
    a_arr, b_arr, c_arr = np.array(a), np.array(b), np.array(c)
    
    # Vector BA and BC
    ba = a_arr - b_arr
    bc = c_arr - b_arr
    
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    
    return float(np.degrees(angle))


def get_coords(landmarks, index: int, w: int, h: int) -> Tuple[float, float]:
    """Converts normalized landmark coordinates to pixel coordinates."""
    if index < 0 or index >= len(landmarks):
        raise IndexError(f"Landmark index {index} out of range")
    return float(landmarks[index].x * w), float(landmarks[index].y * h)


def analyze_posture(db: Session, image_bytes: bytes, ex_name: str) -> Dict[str, Any]:
    """
    Analyzes the posture for a given exercise using an image.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return {"status": "error", "feedback": "Error de imagen: no se pudo decodificar"}
        
    h, w, _ = img.shape

    # Query exercise rules
    exercise_rec = db.query(SupportedExercise).filter(
        (SupportedExercise.name == ex_name.lower()) |
        (SupportedExercise.aliases.contains(ex_name.lower()))
    ).first()

    if not exercise_rec:
        return {"status": "error", "feedback": f"Ejercicio '{ex_name}' no encontrado"}
    
    if not exercise_rec.rules_json:
        return {"status": "error", "feedback": f"Ejercicio '{ex_name}' no tiene reglas configuradas"}

    try:
        rules = json.loads(exercise_rec.rules_json)
    except json.JSONDecodeError:
        return {"status": "error", "feedback": "Error en el formato de reglas (JSON inválido)"}

    # Prepare MediaPipe image
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_img)
    
    try:
        detector = get_detector()
        res = detector.detect(mp_image)
    except Exception as e:
        logger.error(f"Error during posture detection: {e}")
        return {"status": "error", "feedback": f"Error en la detección: {str(e)}"}
    
    if not res.pose_landmarks:
        return {"status": "error", "feedback": "No se detecta ninguna persona en la imagen"}

    landmarks = res.pose_landmarks[0]
    joints = rules.get("target_joints", [])
    
    if len(joints) < 3:
        return {"status": "error", "feedback": "Reglas insuficientes: se requieren al menos 3 puntos de interés"}

    try:
        p1 = get_coords(landmarks, joints[0], w, h)
        p2 = get_coords(landmarks, joints[1], w, h)
        p3 = get_coords(landmarks, joints[2], w, h)
    except (IndexError, AttributeError) as e:
        return {"status": "error", "feedback": f"Error al obtener coordenadas de landmarks: {str(e)}"}

    angle = calculate_angle(p1, p2, p3)

    down_cfg = rules.get("down_stage", {})
    up_cfg = rules.get("up_stage", {})

    stage = None
    # Determine stage based on angle
    if down_cfg.get("condition") == "<" and angle < down_cfg.get("angle", 0):
        stage = "down"
    elif down_cfg.get("condition") == ">" and angle > down_cfg.get("angle", 0):
        stage = "down"

    if up_cfg.get("condition") == ">" and angle > up_cfg.get("angle", 0):
        stage = "up"
    elif up_cfg.get("condition") == "<" and angle < up_cfg.get("angle", 0):
        stage = "up"

    feedback = "¡Buen movimiento!"
    if stage == "up" and angle > down_cfg.get("angle", 0):
        feedback = rules.get("feedback_push", "Baja más")
    elif stage is None:
        feedback = "Mantén la posición o completa el rango de movimiento"

    return {
        "status": "success",
        "angle": angle,
        "stage": stage,
        "feedback": feedback,
        "exercise": ex_name
    }
