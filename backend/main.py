"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router

app = FastAPI(title="Concise IR Report System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173", 
        "https://crs-2y4ydwa4w-like365hondais-projects.vercel.app/api/upload",
        "https://crs-mmj4-npntdyja7-like365hondais-projects.vercel.app"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)