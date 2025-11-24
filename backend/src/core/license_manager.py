"""
License Manager - JWT-based License Verification with Tampering Detection

This module handles all license-related operations for the ZeCo application:
- Loading and validating JWT license keys
- Detecting system time tampering attempts
- Persistent storage of license state

The license system uses RSA public/private key cryptography:
- Private key (kept secure by license issuer) signs the license
- Public key (in backend/public_key.pem) verifies the license signature
- JWT payload contains expiration time, customer info, etc.
"""
import os
import json
import time
from datetime import datetime, timezone
import jwt
from fastapi import HTTPException, status
from config import LICENSE_DATA_FILE, PUBLIC_KEY_FILE


class LicenseManager:
    """
    Manages application licensing with JWT verification and tampering detection.
    
    The license manager provides three key protection mechanisms:
    1. **JWT Signature Verification**: Ensures the license was issued by the authorized party
    2. **Expiration Checking**: Validates the license hasn't expired
    3. **Time Tampering Detection**: Prevents users from rolling back system time
    
    Attributes:
        public_key_path (str): Path to the RSA public key file
        data_file (str): Path to the persistent state file (.license_data)
        public_key (bytes): Loaded RSA public key for JWT verification
    """
    
    def __init__(self, public_key_path: str = PUBLIC_KEY_FILE, data_file: str = LICENSE_DATA_FILE):
        """
        Initialize the License Manager.
        
        Args:
            public_key_path: Path to public_key.pem (RSA public key)
            data_file: Path to .license_data (persistent state storage)
        """
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
        """
        Load the RSA public key from file.
        
        The public key is used to verify that license JWTs were signed
        by the corresponding private key (held by the license issuer).
        
        Returns:
            bytes: The public key content, or None if not found
        """
        if self.public_key_path is None or not os.path.exists(self.public_key_path):
            # If no public key exists, we can't verify anything. 
            # In production, this should probably raise an error or default to secure fail.
            # For now, we'll return None and handle it in verify.
            return None
        with open(self.public_key_path, "rb") as f:
            return f.read()

    def _ensure_data_file(self):
        """
        Ensure the license data file exists with default state.
        
        The data file stores:
        - last_seen: Unix timestamp of last app run (for tampering detection)
        - license_key: The activated JWT license key
        """
        if not os.path.exists(self.data_file):
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            self._save_state({"last_seen": 0, "license_key": None})

    def _load_state(self):
        """
        Load the persistent license state from disk.
        
        Returns:
            dict: State containing 'last_seen' and 'license_key'
        """
        try:
            with open(self.data_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"last_seen": 0, "license_key": None}

    def _save_state(self, state):
        """
        Save the license state to disk.
        
        Args:
            state (dict): State dictionary to persist
        """
        with open(self.data_file, "w") as f:
            json.dump(state, f)

    def get_stored_license(self):
        """
        Retrieve the currently activated license key from storage.
        
        Returns:
            str | None: The license key JWT, or None if not activated
        """
        state = self._load_state()
        return state.get("license_key")

    def set_license(self, token: str):
        """
        Activate a new license key after verification.
        
        This method first verifies the license is valid, then stores it.
        Only valid licenses are persisted.
        
        Args:
            token: JWT license key to activate
            
        Raises:
            HTTPException: If license verification fails
        """
        # Verify before saving
        self.verify_license(token)
        state = self._load_state()
        state["license_key"] = token
        self._save_state(state)

    def verify_license(self, token: str):
        """
        Verify a JWT license key's authenticity and validity.
        
        This method performs multiple checks:
        1. **Signature Verification**: Ensures the JWT was signed with the private key
        2. **Expiration Check**: Validates the 'exp' claim
        3. **Issued At Check**: Validates the 'iat' claim (PyJWT handles this)
        
        The verification uses RS256 (RSA Signature with SHA-256), which requires:
        - The license to be signed with the private key
        - This server to have the matching public key
        
        Args:
            token: JWT license string to verify
            
        Returns:
            dict: Decoded JWT payload if valid
            
        Raises:
            HTTPException 500: If public key is missing
            HTTPException 402: If license is expired or invalid
        """
        if not self.public_key:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="License verification key missing on server."
            )
        
        try:
            # Decode and verify signature
            # PyJWT automatically verifies 'exp' (expiration) and 'iat' (issued at) by default.
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
        Detect system time tampering (clock rollback attacks).
        
        How it works:
        1. Compare current system time to the last recorded time (last_seen)
        2. If current time is significantly earlier (> 60s), raise an error
        3. Update last_seen to current time for next check
        
        This prevents users from:
        - Rolling back system time to extend an expired license
        - Manipulating time to bypass expiration checks
        
        The 60-second tolerance allows for minor NTP clock adjustments.
        
        Raises:
            HTTPException 402: If time tampering is detected
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
        Main license validation method called by middleware.
        
        This is the primary entry point for license checking. It performs
        all necessary validations in the correct order:
        
        1. **Tampering Check**: Verify system time hasn't been rolled back
        2. **License Existence**: Ensure a license key is activated
        3. **License Validity**: Verify signature and expiration
        
        Returns:
            bool: True if license is active and valid
            
        Raises:
            HTTPException 402: If any validation fails
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
