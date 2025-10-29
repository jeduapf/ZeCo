from dotenv import load_dotenv
import os
from typing import Final # So that my variables are immutable

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")

# Database configuration
DATABASE_URL: Final[str] = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# JWT configuration
SECRET_KEY: Final[str] = os.getenv("SECRET_KEY", "your-secret-key-here")  # Change in production!
ALGORITHM: Final[str] = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
TOKEN_REFRESH_THRESHOLD_MINUTES: Final[int] = int(os.getenv("TOKEN_REFRESH_THRESHOLD_MINUTES", "15"))
DEBUG: Final[bool] = os.getenv("DEBUG", "False").lower() in ("true", "1", "t", "True", "TRUE")  # Convert to boolean
