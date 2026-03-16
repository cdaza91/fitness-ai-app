import cv2
import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180.0 else angle

def check_arm_flexion(l):
    s = [l[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, l[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
    e = [l[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, l[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
    w = [l[mp_pose.PoseLandmark.LEFT_WRIST.value].x, l[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
    angle = calculate_angle(s, e, w)
    return {"angle": angle, "feedback": "Rango incompleto" if angle > 150 else "Buen rango"}

def check_leg_flexion(l):
    h = [l[mp_pose.PoseLandmark.LEFT_HIP.value].x, l[mp_pose.PoseLandmark.LEFT_HIP.value].y]
    k = [l[mp_pose.PoseLandmark.LEFT_KNEE.value].x, l[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
    a = [l[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, l[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
    angle = calculate_angle(h, k, a)
    return {"angle": angle, "feedback": "Baja más" if angle > 100 else "Excelente profundidad"}

def check_core_alignment(l):
    s = [l[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, l[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
    h = [l[mp_pose.PoseLandmark.LEFT_HIP.value].x, l[mp_pose.PoseLandmark.LEFT_HIP.value].y]
    a = [l[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, l[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
    angle = calculate_angle(s, h, a)
    return {"angle": angle, "feedback": "No bajes la cadera" if angle < 160 else "Cuerpo alineado"}

EXERCISES_DB = {
    "Push-up": check_core_alignment, "Squat": check_leg_flexion, "Deadlift": check_core_alignment,
    "Bench Press": check_arm_flexion, "Pull-up": check_arm_flexion, "Overhead Press": check_arm_flexion,
    "Bicep Curl": check_arm_flexion, "Tricep Dip": check_arm_flexion, "Plank": check_core_alignment,
    "Lunge": check_leg_flexion, "Burpee": check_core_alignment, "Mountain Climber": check_core_alignment,
    "Leg Press": check_leg_flexion, "Lateral Raise": check_arm_flexion, "Hammer Curl": check_arm_flexion,
    "Skull Crusher": check_arm_flexion, "Leg Extension": check_leg_flexion, "Leg Curl": check_leg_flexion,
    "Calf Raise": check_leg_flexion, "Russian Twist": check_core_alignment, "Sit-up": check_core_alignment,
    "Crunch": check_core_alignment, "Hanging Leg Raise": check_core_alignment, "Face Pull": check_arm_flexion,
    "Lat Pulldown": check_arm_flexion, "Bent Over Row": check_core_alignment, "T-Bar Row": check_core_alignment,
    "Cable Fly": check_arm_flexion, "Incline Bench Press": check_arm_flexion, "Decline Bench Press": check_arm_flexion,
    "Dumbbell Fly": check_arm_flexion, "Arnold Press": check_arm_flexion, "Front Raise": check_arm_flexion,
    "Shrugs": check_core_alignment, "Reverse Fly": check_arm_flexion, "Preacher Curl": check_arm_flexion,
    "Concentration Curl": check_arm_flexion, "Close Grip Bench Press": check_arm_flexion, "Tricep Pushdown": check_arm_flexion,
    "Overhead Tricep Extension": check_arm_flexion, "Roman Chair Leg Raise": check_core_alignment, "Bicycle Crunch": check_core_alignment,
    "Plank Jack": check_core_alignment, "Side Plank": check_core_alignment, "Bird Dog": check_core_alignment,
    "Superman": check_core_alignment, "Glute Bridge": check_core_alignment, "Hip Thrust": check_core_alignment,
    "Sumo Squat": check_leg_flexion, "Goblet Squat": check_leg_flexion, "Bulgarian Split Squat": check_leg_flexion,
    "Box Jump": check_leg_flexion, "Step Up": check_leg_flexion, "Romanian Deadlift": check_core_alignment,
    "Stiff Leg Deadlift": check_core_alignment, "Good Morning": check_core_alignment, "Clean and Press": check_arm_flexion,
    "Snatch": check_arm_flexion, "Kettlebell Swing": check_core_alignment, "Goblet Lunge": check_leg_flexion,
    "Walking Lunge": check_leg_flexion, "Side Lunge": check_leg_flexion, "Curtsy Lunge": check_leg_flexion,
    "Pike Push-up": check_arm_flexion, "Diamond Push-up": check_arm_flexion, "Wide Push-up": check_arm_flexion,
    "Incline Push-up": check_arm_flexion, "Decline Push-up": check_arm_flexion, "Chin-up": check_arm_flexion,
    "Muscle-up": check_arm_flexion, "Dips": check_arm_flexion, "Upright Row": check_arm_flexion,
    "Barbell Row": check_core_alignment, "Seated Cable Row": check_arm_flexion, "Single Arm Row": check_arm_flexion,
    "Pec Deck": check_arm_flexion, "Hack Squat": check_leg_flexion, "Front Squat": check_leg_flexion,
    "Zercher Squat": check_leg_flexion, "Pistol Squat": check_leg_flexion, "Wall Sit": check_leg_flexion,
    "Donkey Kick": check_core_alignment, "Fire Hydrant": check_core_alignment, "In-and-Outs": check_core_alignment,
    "Flutter Kicks": check_core_alignment, "Scissor Kicks": check_core_alignment, "V-ups": check_core_alignment,
    "Toe Touches": check_core_alignment, "Dead Bug": check_core_alignment, "Hollow Body": check_core_alignment,
    "Farmer’s Walk": check_core_alignment, "Battle Ropes": check_arm_flexion, "Wall Ball": check_leg_flexion,
    "Thruster": check_leg_flexion, "Renegade Row": check_core_alignment, "Plank to Push-up": check_core_alignment,
    "Spiderman Plank": check_core_alignment, "Bear Crawl": check_core_alignment, "Turkish Get-up": check_core_alignment,
    "Jumping Jacks": check_arm_flexion
}

def normalize_exercise_name(name):
    name_clean = name.lower().strip()
    mapping = {
        "sentadilla": "Squat", "squat": "Squat", "pecho": "Bench Press", "flexion": "Push-up",
        "lagartija": "Push-up", "pushup": "Push-up", "peso muerto": "Deadlift", "deadlift": "Deadlift",
        "bicep": "Bicep Curl", "tricep": "Tricep Dip", "plancha": "Plank", "zancada": "Lunge",
        "estocada": "Lunge", "lunge": "Lunge", "burpee": "Burpee", "dominada": "Pull-up",
        "prensa": "Leg Press", "hombro": "Overhead Press", "remo": "Bent Over Row"
    }
    for key, formal in mapping.items():
        if key in name_clean:
            return formal
    return "General"

def analyze_posture(image_bytes, ex_name):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    res = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if not res.pose_landmarks: return {"status": "error", "message": "No detectado"}
    l = res.pose_landmarks.landmark
    formal_name = normalize_exercise_name(ex_name)
    logic_func = EXERCISES_DB.get(formal_name, check_core_alignment)
    analysis = logic_func(l)
    return {"status": "success", "feedback": analysis["feedback"], "angle": analysis["angle"]}