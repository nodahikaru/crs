from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from main import router  # import your APIRouter from your main code

app = FastAPI()

# If you need CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your router
app.include_router(router)