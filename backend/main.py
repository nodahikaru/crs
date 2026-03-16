"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, Response
from mangum import Mangum
from routes import router

app = FastAPI(title="Concise IR Report System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/")
def root():
    return {"message": "Hello World"}

app.include_router(router)

handler = Mangum(app)