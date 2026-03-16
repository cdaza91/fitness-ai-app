from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router

app = FastAPI(title="FitCheck AI API")

# CONFIGURACIÓN DE CORS - ESTO ES VITAL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción pondrás tu dominio, en desarrollo "*" está bien
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")