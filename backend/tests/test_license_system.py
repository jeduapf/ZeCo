import unittest
import os
import json
import time
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

import importlib.util
import sys
import os

# Add backend to path to import generate_license
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load LicenseManager directly to avoid triggering src/__init__.py which loads DB
spec = importlib.util.spec_from_file_location("license_manager", os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/license_manager.py')))
license_manager_module = importlib.util.module_from_spec(spec)
sys.modules["license_manager"] = license_manager_module
spec.loader.exec_module(license_manager_module)
LicenseManager = license_manager_module.LicenseManager
from generate_license import create_license, generate_keys

# Constants for testing
TEST_DATA_FILE = ".test_license_data"
TEST_PUB_KEY = "test_public_key.pem"
TEST_PRIV_KEY = "test_private_key.pem"

class TestLicenseSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate keys for testing
        # We need to temporarily override the key filenames in generate_license or just rename them after
        # Easier to just use the functions and move files
        print("Setting up test environment...")
        
        # Backup existing keys if they exist to avoid overwriting user's keys
        cls.backup_keys()
        
        # Generate new keys
        # We'll mock the filenames in generate_license module for the duration of generation
        with patch('generate_license.PRIVATE_KEY_FILE', TEST_PRIV_KEY), \
             patch('generate_license.PUBLIC_KEY_FILE', TEST_PUB_KEY):
            generate_keys()

    @classmethod
    def tearDownClass(cls):
        print("Cleaning up test environment...")
        # Remove test files
        if os.path.exists(TEST_DATA_FILE):
            os.remove(TEST_DATA_FILE)
        if os.path.exists(TEST_PUB_KEY):
            os.remove(TEST_PUB_KEY)
        if os.path.exists(TEST_PRIV_KEY):
            os.remove(TEST_PRIV_KEY)
            
        # Restore backed up keys
        cls.restore_keys()

    @classmethod
    def backup_keys(cls):
        cls.backups = {}
        for f in ["public_key.pem", "private_key.pem"]:
            if os.path.exists(f):
                shutil.move(f, f + ".bak")
                cls.backups[f] = True

    @classmethod
    def restore_keys(cls):
        for f, exists in getattr(cls, 'backups', {}).items():
            if exists and os.path.exists(f + ".bak"):
                shutil.move(f + ".bak", f)

    def setUp(self):
        # Reset data file before each test
        if os.path.exists(TEST_DATA_FILE):
            os.remove(TEST_DATA_FILE)
        
        self.manager = LicenseManager(public_key_path=TEST_PUB_KEY, data_file=TEST_DATA_FILE)

    def create_test_license(self, days=30):
        with patch('generate_license.PRIVATE_KEY_FILE', TEST_PRIV_KEY):
            return create_license("test_user", days)

    def test_01_valid_license(self):
        """Test that a valid license is accepted"""
        token = self.create_test_license(days=30)
        self.manager.set_license(token)
        self.assertTrue(self.manager.is_active())
        print("✅ Valid license test passed")

    def test_02_expired_license(self):
        """Test that an expired license is rejected"""
        # Create a license that expired yesterday
        token = self.create_test_license(days=-1)
        
        from fastapi import HTTPException
        # set_license verifies the token, so it should raise immediately
        with self.assertRaises(HTTPException) as cm:
            self.manager.set_license(token)
        self.assertEqual(cm.exception.status_code, 402)
        print("✅ Expired license test passed")

    def test_03_tamper_backward_jump(self):
        """Test detection of backward time jump"""
        token = self.create_test_license(days=30)
        self.manager.set_license(token)
        
        # 1. Run successfully at time T
        now = time.time()
        with patch('time.time', return_value=now):
            self.assertTrue(self.manager.is_active())
            
        # 2. User moves clock back 1 hour
        past = now - 3600
        with patch('time.time', return_value=past):
            from fastapi import HTTPException
            with self.assertRaises(HTTPException) as cm:
                self.manager.is_active()
            print(f"DEBUG: Exception detail: '{cm.exception.detail}'")
            self.assertIn("tampering", str(cm.exception.detail).lower())
            
        print("✅ Backward time jump detection passed")

    def test_04_tamper_forward_then_backward(self):
        """Test detection of forward jump followed by backward jump"""
        token = self.create_test_license(days=30)
        self.manager.set_license(token)
        
        # 1. Run at time T
        now = time.time()
        with patch('time.time', return_value=now):
            self.assertTrue(self.manager.is_active())
            
        # 2. User jumps to future (e.g. 1 year later) to try something? 
        # Actually, if they jump to future, the license might expire.
        # Let's say they jump 1 day forward (still valid license)
        future = now + 86400
        with patch('time.time', return_value=future):
            self.assertTrue(self.manager.is_active())
            
        # 3. Now they jump back to T (original time)
        # The last_seen should be T + 1 day. So T < last_seen.
        with patch('time.time', return_value=now):
            from fastapi import HTTPException
            with self.assertRaises(HTTPException) as cm:
                self.manager.is_active()
            print(f"DEBUG: Exception detail: '{cm.exception.detail}'")
            self.assertIn("tampering", str(cm.exception.detail).lower())
            
        print("✅ Forward-then-backward time jump detection passed")

if __name__ == '__main__':
    unittest.main()
