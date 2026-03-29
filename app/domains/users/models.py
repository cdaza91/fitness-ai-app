from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Date, Text, Index
from sqlalchemy.orm import relationship
from app.core.db import Base

class User(Base):
    """
    Represents a system user, including their physical profile, fitness goals,
    and preferences for training.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Physical Profile
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(50), nullable=True)
    goal = Column(String(255), nullable=True)

    # Garmin Integration
    garmin_email = Column(String(255), nullable=True)
    garmin_password = Column(String(255), nullable=True)

    # Google Fit Integration
    google_fit_access_token = Column(Text, nullable=True)
    google_fit_refresh_token = Column(Text, nullable=True)

    # Fitness Preferences & Goals
    fitness_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced
    experience_desc = Column(Text, nullable=True)
    primary_goal = Column(String(255), nullable=True)
    secondary_goals = Column(Text, nullable=True)
    target_race_distance = Column(String(50), nullable=True)  # 5k, 10k, 21k, 42k
    target_race_date = Column(String(50), nullable=True)
    timeline_weeks = Column(Integer, default=12)

    # Running Metrics
    easy_pace = Column(String(20), nullable=True)  # e.g. "6:30"
    max_run_distance = Column(Float, nullable=True)
    weekly_mileage = Column(Float, nullable=True)

    # Schedule & Preferences
    days_per_week = Column(Integer, default=7)
    session_duration = Column(Integer, default=60)
    preferred_terrain = Column(String(100), nullable=True)

    # Health & Equipment
    injuries_pain = Column(Text, nullable=True)
    equipment_access = Column(Text, nullable=True)

    # Training Methodology
    intensity_method = Column(String(50), default="pace")
    rep_range_pref = Column(String(50), nullable=True)
    mileage_increase_limit = Column(Integer, default=10)
    cross_training_pref = Column(Boolean, default=True)

    # Relationships
    workout_plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")
    health_metrics = relationship("HealthMetric", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email='{self.email}', goal='{self.primary_goal}')>"


class WorkoutPlan(Base):
    """
    Represents a specific workout plan generated for a user.
    """
    __tablename__ = "workout_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    json_data = Column(Text, nullable=False)  # Stores the full workout structure
    created_at = Column(DateTime, default=datetime.utcnow)
    training_type = Column(String(50), nullable=True)

    user = relationship("User", back_populates="workout_plans")
    days = relationship("WorkoutDay", back_populates="workout_plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkoutPlan(title='{self.title}', user_id={self.user_id})>"


class WorkoutDay(Base):
    """
    Represents a specific day/session within a workout plan.
    Includes status, completion info, and results like weights used.
    """
    __tablename__ = "workout_days"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_plan_id = Column(Integer, ForeignKey("workout_plans.id"), index=True, nullable=False)
    day_index = Column(Integer, nullable=False)  # 1-based index or day number in the plan
    date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False)
    
    # Link to external activity (e.g., from Garmin) if matched
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    
    # Full information of the workout for this specific day (snapshot of the routine)
    workout_data = Column(Text, nullable=True)  # JSON field
    
    # Performance metrics, specifically weights used in strength training
    performance_data = Column(Text, nullable=True)  # JSON field: e.g., {"exercise_id": {"weight": 20, "reps": 10}}

    workout_plan = relationship("WorkoutPlan", back_populates="days")
    activity = relationship("Activity")

    def __repr__(self):
        return f"<WorkoutDay(plan_id={self.workout_plan_id}, day={self.day_index}, completed={self.is_completed})>"


class HealthMetric(Base):
    """
    Daily health and biometric data for a user.
    """
    __tablename__ = "health_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    date = Column(Date, default=lambda: datetime.utcnow().date(), index=True)
    weight_kg = Column(Float, nullable=True)
    body_fat_pct = Column(Float, nullable=True)
    muscle_mass_kg = Column(Float, nullable=True)
    resting_heart_rate = Column(Integer, nullable=True)
    steps = Column(Integer, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    sleep_score = Column(Integer, nullable=True)
    source = Column(String(50), default="garmin")  # garmin, google_fit, manual

    user = relationship("User", back_populates="health_metrics")

    def __repr__(self):
        return f"<HealthMetric(user_id={self.user_id}, date='{self.date}')>"


class Activity(Base):
    """
    Imported fitness activities from external sources (e.g., Garmin).
    """
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    external_id = Column(String(255), unique=True, index=True)
    source = Column(String(50))
    activity_type = Column(String(50))
    name = Column(String(255))
    date = Column(DateTime, index=True)
    distance_meters = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    average_heart_rate = Column(Integer, nullable=True)
    calories = Column(Float, nullable=True)
    json_data = Column(Text, nullable=True) # Full detail from source

    user = relationship("User", back_populates="activities")

    def __repr__(self):
        return f"<Activity(name='{self.name}', type='{self.activity_type}', date='{self.date}')>"


class SupportedExercise(Base):
    """
    Configuration for exercises that the AI can analyze via posture checking.
    """
    __tablename__ = "supported_exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    aliases = Column(Text, nullable=True)  # Comma-separated or JSON list of aliases
    is_active = Column(Boolean, default=True)
    rules_json = Column(Text, nullable=True)  # Rules for MediaPipe analysis
    video_url = Column(String(512), nullable=True)

    def __repr__(self):
        return f"<SupportedExercise(name='{self.name}', is_active={self.is_active})>"
