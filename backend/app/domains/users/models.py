from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Date, Text
from sqlalchemy.orm import relationship
from app.core.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    goal = Column(String, nullable=True)

    garmin_email = Column(String, nullable=True)
    garmin_password = Column(String, nullable=True)

    fitness_level = Column(String, nullable=True) # beginner, intermediate, advanced
    experience_desc = Column(String, nullable=True)
    primary_goal = Column(String, nullable=True)
    secondary_goals = Column(String, nullable=True)
    target_race_distance = Column(String, nullable=True) # 5k, 10k, 21k, 42k
    target_race_date = Column(String, nullable=True)
    timeline_weeks = Column(Integer, default=12)

    easy_pace = Column(String, nullable=True) # e.g. "6:30"
    max_run_distance = Column(Float, nullable=True)
    weekly_mileage = Column(Float, nullable=True)

    days_per_week = Column(Integer, default=3)
    session_duration = Column(Integer, default=60)
    preferred_terrain = Column(String, nullable=True)

    injuries_pain = Column(Text, nullable=True)
    equipment_access = Column(Text, nullable=True)

    intensity_method = Column(String, default="pace")
    rep_range_pref = Column(String, nullable=True)
    mileage_increase_limit = Column(Integer, default=10)
    cross_training_pref = Column(Boolean, default=True)

    workouts = relationship("Workout", back_populates="user")
    health_metrics = relationship("HealthMetric", back_populates="user")
    activities = relationship("Activity", back_populates="user")

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    json_data = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    training_type = Column(String, nullable=True)

    user = relationship("User", back_populates="workouts")

class HealthMetric(Base):
    __tablename__ = "health_metrics"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, default=lambda: datetime.now().date())
    weight_kg = Column(Float, nullable=True)
    resting_heart_rate = Column(Integer, nullable=True)
    steps = Column(Integer, nullable=True)
    source = Column(String, default="garmin")

    user = relationship("User", back_populates="health_metrics")

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    external_id = Column(String, unique=True, index=True)
    source = Column(String)
    activity_type = Column(String)
    name = Column(String)
    date = Column(DateTime)
    distance_meters = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    average_heart_rate = Column(Integer, nullable=True)

    user = relationship("User", back_populates="activities")

class SupportedExercise(Base):
    __tablename__ = "supported_exercises"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    aliases = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    rules_json = Column(Text)
    video_url = Column(String, nullable=True)