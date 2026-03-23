from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.core.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)                
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    goal = Column(String, nullable=True)

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)