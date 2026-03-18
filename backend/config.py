import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    TOP_K: int = 10
    VECTOR_WEIGHT: float = 0.9
    ORDER_WEIGHT: float = 0.1
    LOW_CONF_THRESHOLD: float = 0.45
    UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "uploads")
    OUTPUT_DIR: str = os.path.join(os.path.dirname(__file__), "outputs")


settings = Settings()
