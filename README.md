# FitCheck AI - Personalized Fitness Assistant

FitCheck AI is a modern fitness application that leverages artificial intelligence to generate personalized workout plans, track exercise posture in real-time using computer vision, and sync health metrics with Garmin.

## 🚀 Key Features

*   **AI-Powered Workout Generation**: Personalized plans for running and strength training using Google Gemini AI, tailored to your goals, fitness level, and available equipment.
*   **Posture Analysis**: Real-time feedback on exercise execution using MediaPipe computer vision to ensure safety and efficiency.
*   **Garmin Integration**: Automated synchronization of health metrics (weight, heart rate, steps) and seamless uploading of generated workouts to Garmin devices.
*   **Admin Dashboard**: Manage supported exercises, configure posture analysis rules, and monitor user progress.

## 🛠 Tech Stack

*   **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
*   **Database**: [SQLAlchemy](https://www.sqlalchemy.org/) with SQLite (can be easily swapped for PostgreSQL)
*   **AI Engine**: [Google Gemini Pro](https://deepmind.google/technologies/gemini/)
*   **Computer Vision**: [MediaPipe](https://mediapipe.dev/) & [OpenCV](https://opencv.org/)
*   **Integrations**: [garminconnect](https://github.com/cyberjunky/python-garminconnect)
*   **Admin**: [SQLAdmin](https://aminalaee.dev/sqladmin/)

## 📋 Prerequisites

*   Python 3.12+
*   Google Gemini API Key
*   YouTube Data API v3 Key (for exercise tutorials)
*   Garmin Connect Account

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/fitness-ai-app.git
cd fitness-ai-app
```

### 2. Set Up the Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the `backend/` directory:
```env
PROJECT_NAME="FitCheck AI API"
SECRET_KEY="your_super_secret_key"
GEMINI_API_KEY="your_google_gemini_api_key"
YOUTUBE_API_KEY="your_youtube_api_key"
DATABASE_URL="sqlite:///./fitcheck.db"
```

### 4. Run the Application
```bash
# Must be inside the backend directory
uvicorn app.main:app --reload
```
The API documentation will be available at `http://127.0.0.1:8000/docs`.
The Admin dashboard will be available at `http://127.0.0.1:8000/admin`.

## 🧪 Running Tests

Tests must be executed from the **backend** directory to ensure proper module discovery.

### Pytest (Unit & Integration)
```bash
cd backend
pytest app/tests
```

### Behave (BDD)
```bash
cd backend
behave app/tests/features
```

## 📂 Project Structure
```
fitness-ai-app/
├── backend/
│   ├── app/
│   │   ├── api/             # API Endpoints (v1)
│   │   ├── core/            # Centralized Config, Security, Tasks
│   │   ├── domains/         # Domain-driven logic (Users, Workouts, Integrations)
│   │   ├── tests/           # Unit, Integration, and Behave tests
│   │   └── main.py          # Application entry point
│   ├── requirements.txt
│   └── .env
└── README.md
```

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
