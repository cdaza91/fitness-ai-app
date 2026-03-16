from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./fitness_app.db"

# 1. El Engine es quien lleva los 'connect_args'
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Solo necesario para SQLite
)

# 2. La sesión se vincula al engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. El Base NO lleva argumentos de conexión
Base = declarative_base()

# Función para inicializar la base de datos (se llama desde main.py)
def init_db():
    Base.metadata.create_all(bind=engine)