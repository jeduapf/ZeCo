from dotenv import load_dotenv
import os
from typing import Final, Optional
from pathlib import Path

def find_file_recursive(filename: str, start_dir: Optional[str] = None, max_levels_up: int = 5) -> Optional[str]:
    """
    Find a file by searching recursively upwards from the start directory.
    
    Args:
        filename: Name of the file to find
        start_dir: Starting directory (defaults to current file's directory)
        max_levels_up: Maximum number of parent directories to search
        
    Returns:
        Absolute path to the file if found, None otherwise
    """
    if start_dir is None:
        # Start from the directory containing this config.py file
        start_dir = Path(__file__).parent.absolute()
    else:
        start_dir = Path(start_dir).absolute()
    
    current_dir = start_dir
    
    # Search upwards through parent directories
    for _ in range(max_levels_up + 1):
        # Check if file exists in current directory
        file_path = current_dir / filename
        if file_path.exists():
            return str(file_path.absolute())
        
        # Check if file exists in any subdirectory (one level deep)
        for item in current_dir.rglob(filename):
            if item.is_file():
                return str(item.absolute())
        
        # Move up one directory
        parent = current_dir.parent
        if parent == current_dir:  # Reached root
            break
        current_dir = parent
    
    return None

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
LANG: Final[str] = os.getenv("LANG", "en")  # Default language for logging
MIN_STOCK: Final[int] = int(os.getenv("MIN_STOCK", "5"))  # Minimum stock level for menu items
API_VERSION: Final[str] = os.getenv("API_VERSION", "v1")  # API version
if DEBUG:
    LOGLEVEL: Final[str] = "DEBUG"
else:
    LOGLEVEL: Final[str] = os.getenv("LOGLEVEL", "INFO")  # Log base levels to be printed       


    

# Search for the files recursively from the highest level and set the paths
# Returns None if file doesn't exist (will be created by license_manager if needed)
LICENSE_DATA_FILE: Final[Optional[str]] = os.getenv("LICENSE_DATA_FILE") or find_file_recursive(".license_data")
PUBLIC_KEY_FILE: Final[Optional[str]] = os.getenv("PUBLIC_KEY_FILE") or find_file_recursive("public_key.pem")


if __name__ == "__main__":
    print("=== Variables loaded successfully ===")
    print("LICENSE_DATA_FILE:", LICENSE_DATA_FILE)
    print("PUBLIC_KEY_FILE:", PUBLIC_KEY_FILE)
    print("DATABASE_URL:", DATABASE_URL)
    print("SECRET_KEY:", SECRET_KEY)
    print("ALGORITHM:", ALGORITHM)
    print("ACCESS_TOKEN_EXPIRE_MINUTES:", ACCESS_TOKEN_EXPIRE_MINUTES)
    print("TOKEN_REFRESH_THRESHOLD_MINUTES:", TOKEN_REFRESH_THRESHOLD_MINUTES)
    print("DEBUG:", DEBUG)
    print("LANG:", LANG)
    print("MIN_STOCK:", MIN_STOCK)
    print("API_VERSION:", API_VERSION)
    print("LOGLEVEL:", LOGLEVEL)