"""API X1000 PMU COURSES V65."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="X1000 PMU COURSES",
    version="65.0"
)

origines = [
    x.strip()
    for x in os.getenv(
        "X1000_CORS_ORIGINS", ""
    ).split(",")
    if x.strip()
]

if origines:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origines,
        allow_methods=["GET"],
        allow_headers=["Accept"],
    )

@app.get("/api/status")
def status():
    return {
        "projet": "X1000 PMU COURSES",
        "version": "V65",
        "mode": "LECTURE_SEULE",
        "moteurs": {
            f"M{i}": "NON_VALIDÉ"
            for i in range(1, 6)
        },
        "production_port_preserve": 8765,
        "collecte_active": False,
    }

@app.get("/api/courses")
def courses():
    return {
        "courses": [],
        "statut": "SOURCE_NON_CONNECTEE"
    }

@app.get("/api/selections")
def selections():
    return {"selections": []}

@app.get("/api/figes")
def figes():
    return {"figes": []}

@app.get("/api/audits")
def audits():
    return {"audits": []}
