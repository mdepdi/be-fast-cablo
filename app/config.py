"""
Configuration module for FastAPI LastMile application
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings"""

    # FastAPI Configuration
    API_TITLE: str = os.getenv("API_TITLE", "Fast LastMile API")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION: str = os.getenv("API_DESCRIPTION", "FastAPI service for processing lastmile routing requests")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Authentication
    API_KEY: str = os.getenv("API_KEY", "default-api-key")

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    BASE_URL: str = os.getenv("BASE_URL", f"http://localhost:{int(os.getenv('PORT', '8000'))}")

    # ORS Configuration
    ORS_BASE_URL: str = os.getenv("ORS_BASE_URL", "http://localhost:6080")

    # File Storage Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./outputs")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

    # Default Processing Parameters
    DEFAULT_PULAU: str = os.getenv("DEFAULT_PULAU", "Sulawesi")
    DEFAULT_GRAPH_PATH: str = os.getenv("DEFAULT_GRAPH_PATH", "./data/sulawesi_graph.graphml")
    DEFAULT_FO_PATH: str = os.getenv("DEFAULT_FO_PATH", "./data/fo_sulawesi/fo_sulawesi.shp")
    DEFAULT_POP_PATH: str = os.getenv("DEFAULT_POP_PATH", "./data/pop.csv")

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000"
    ]

    def __init__(self):
        """Initialize settings and create necessary directories"""
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs("./data", exist_ok=True)

# Create global settings instance
settings = Settings()