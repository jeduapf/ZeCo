import os
import json
import time
from datetime import datetime, timezone
import jwt
from fastapi import HTTPException, status

# Import from config
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LICENSE_DATA_FILE, PUBLIC_KEY_FILE

class LicenseManager:
    def __init__(self, public_key_path: str = PUBLIC_KEY_FILE, data_file: str = LICENSE_DATA_FILE):
        # Handle None values by creating default paths in backend directory
        if data_file is None:
            # Create .license_data in backend directory if it doesn't exist
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_file = os.path.join(backend_dir, ".license_data")
        
        if public_key_path is None:
            # Set to None to indicate no public key available
            self.public_key_path = None
        else:
            self.public_key_path = public_key_path
            
        self.data_file = data_file
        self.public_key = self._load_public_key()
        self._ensure_data_file()

    def _load_public_key(self):
        if self.public_key_path is None or not os.path.exists(self.public_key_path):
            # If no public key exists, we can't verify anything. 
            # In production, this should probably raise an error or default to secure fail.
            # For now, we'll return None and handle it in verify.
            return None
        with open(self.public_key_path, "rb") as f:
            return f.read()

    def _ensure_data_file(self):
        if not os.path.exists(self.data_file):
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            self._save_state({"last_seen": 0, "license_key": None})

    def _load_state(self):
        try:
            with open(self.data_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"last_seen": 0, "license_key": None}

    def _save_state(self, state):
        with open(self.data_file, "w") as f:
            json.dump(state, f)

    def get_stored_license(self):
        state = self._load_state()
        return state.get("license_key")

    def set_license(self, token: str):
        # Verify before saving
        self.verify_license(token)
        state = self._load_state()
        state["license_key"] = token
        self._save_state(state)

    def verify_license(self, token: str):
        if not self.public_key:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="License verification key missing on server."
            )
        
        try:
            # Decode and verify signature
            # PyJWT automatically verifies 'exp' and 'iat' by default.
            payload = jwt.decode(token, self.public_key, algorithms=["RS256"])
            
            # Extra check: verify 'iat' is not in the future (basic sanity)
            # PyJWT checks iat, but we can add tolerance if needed.
            # For now, we rely on PyJWT's standard validation.

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="License expired. Please renew your subscription."
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Invalid license key: {str(e)}"
            )

    def check_tampering(self):
        """
        Checks if the system time has been tampered with (moved backwards).
        """
        current_time = time.time()
        state = self._load_state()
        last_seen = state.get("last_seen", 0)

        # Tolerance for minor clock sync adjustments (e.g., 60 seconds)
        if current_time < last_seen - 60:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="System time tampering detected. Clock moved backwards."
            )
        
        # Also check if last_seen is way in the future (e.g. user moved forward then back)
        # If last_seen is > current_time (handled above), but what if they set it to 2050?
        # We can't know if 2050 is wrong unless we have a reference.
        # But if they set it to 2050, ran the app, and then set it back to 2024,
        # last_seen will be 2050, and current_time 2024, so the check above (current < last) catches it.
        
        # Update state with new time
        state["last_seen"] = current_time
        self._save_state(state)

    def is_active(self):
        """
        Main check function to be called by middleware/dependency.
        """
        # 1. Check Tampering
        self.check_tampering()

        # 2. Get License
        token = self.get_stored_license()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="No license key found. Please activate your application."
            )

        # 3. Verify License
        self.verify_license(token)
        
        return True
