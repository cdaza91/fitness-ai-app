import cv2
import mediapipe as mp
import numpy as np
import os
import json
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from app.domains.users.models import SupportedExercise
from app.core.db import SessionLocal

model_path = os.path.join(os.path.dirname(__file__), 'pose_landmarker_heavy.task')
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE
)
detector = vision.PoseLandmarker.create_from_options(options)


def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180.0 else angle


def get_coords(landmarks, index, w, h):
    return [landmarks[index].x * w, landmarks[index].y * h]


def analyze_posture(image_bytes, ex_name):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return {"status": "error", "feedback": "Error de imagen"}
    h, w, _ = img.shape

    db = SessionLocal()
    exercise_rec = db.query(SupportedExercise).filter(
        (SupportedExercise.name == ex_name.lower()) |
        (SupportedExercise.aliases.contains(ex_name.lower()))
    ).first()
    db.close()

    if not exercise_rec or not exercise_rec.rules_json:
        return {"status": "error", "feedback": "Ejercicio no mapeado en Admin"}

    rules = json.loads(exercise_rec.rules_json)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    res = detector.detect(mp_image)
    if not res.pose_landmarks: return {"status": "error", "feedback": "No se detecta persona"}

    l = res.pose_landmarks[0]
    joints = rules.get("target_joints", [])
    if len(joints) < 3: return {"status": "error", "feedback": "Reglas incompletas"}

    p1 = get_coords(l, joints[0], w, h)
    p2 = get_coords(l, joints[1], w, h)
    p3 = get_coords(l, joints[2], w, h)

    angle = calculate_angle(p1, p2, p3)

    down_cfg = rules.get("down_stage", {})
    up_cfg = rules.get("up_stage", {})

    stage = None
    if down_cfg.get("condition") == "<" and angle < down_cfg.get("angle"):
        stage = "down"
    elif down_cfg.get("condition") == ">" and angle > down_cfg.get("angle"):
        stage = "down"

    if up_cfg.get("condition") == ">" and angle > up_cfg.get("angle"):
        stage = "up"
    elif up_cfg.get("condition") == "<" and angle < up_cfg.get("angle"):
        stage = "up"

    feedback = "¡Buen movimiento!"
    if stage == "up" and angle > down_cfg.get("angle"):
        feedback = rules.get("feedback_push", "Baja más")

    return {
        "status": "success",
        "angle": angle,
        "stage": stage,
        "feedback": feedback,
        "exercise": ex_name
    }