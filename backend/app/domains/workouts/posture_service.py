import cv2
import mediapipe as mp
import numpy as np
import os
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

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
    return {"x": landmarks[index].x * w, "y": landmarks[index].y * h}


def get_norm(landmarks, index):
    return {"x": landmarks[index].x, "y": landmarks[index].y, "v": landmarks[index].visibility}


def check_squat_proportional(l, w, h):
    lk = get_coords(l, 25, w, h)
    lh = get_coords(l, 23, w, h)
    la = get_coords(l, 27, w, h)
    rk = get_coords(l, 26, w, h)
    rh = get_coords(l, 24, w, h)

    angle = calculate_angle([lh['x'], lh['y']], [lk['x'], lk['y']], [la['x'], la['y']])
    knee_dist = np.abs(lk['x'] - rk['x'])
    hip_dist = np.abs(lh['x'] - rh['x'])

    error_joints = []
    if knee_dist < hip_dist * 0.8:
        error_joints = ["lk", "rk"]

    stage = "down" if angle < 110 else "up" if angle > 160 else None
    feedback = "Baja más" if angle > 110 else "Excelente"
    if "lk" in error_joints: feedback = "Abre las rodillas"

    return {"angle": angle, "stage": stage, "feedback": feedback, "errors": error_joints}


def analyze_posture(image_bytes, ex_name):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return {"status": "error"}
    h, w, _ = img.shape
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    res = detector.detect(mp_image)

    if not res.pose_landmarks: return {"status": "error"}

    l = res.pose_landmarks[0]
    analysis = check_squat_proportional(l, w, h)

    skeleton = {
        "ls": get_norm(l, 11), "rs": get_norm(l, 12),
        "lh": get_norm(l, 23), "rh": get_norm(l, 24),
        "lk": get_norm(l, 25), "rk": get_norm(l, 26),
        "la": get_norm(l, 27), "ra": get_norm(l, 28)
    }

    return {
        "status": "success",
        "stage": analysis["stage"],
        "feedback": analysis["feedback"],
        "errors": analysis["errors"],
        "skeleton": skeleton
    }