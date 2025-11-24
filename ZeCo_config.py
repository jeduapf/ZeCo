from dotenv import load_dotenv
import os
from typing import Final, Optional
from pathlib import Path

# Load environment variables from .env file
load_dotenv(dotenv_path=".ZeCo.env")

# Database configuration
CERTIFICATE_LIFETIME_DAYS: Final[int] = int(os.getenv("CERTIFICATE_LIFETIME_DAYS", "3650"))
CERTIFICATE_ORGANIZATION_NAME: Final[str] = os.getenv("CERTIFICATE_ORGANIZATION_NAME", "ZeCo Secure Access")
