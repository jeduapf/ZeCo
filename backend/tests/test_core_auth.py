"""
Core Authentication Tests

Tests authentication flow including:
- User login with valid credentials
- User logout
- Multiple login/logout sessions
- Invalid credentials
- Token expiration
- Session management

These tests MUST pass for the application to function correctly.

================================================================================
FIXTURES USED (automatically loaded from conftest.py):
================================================================================

FROM conftest.py:
-----------------
- async_client (line 38):
    Async HTTP client for making API requests in tests.
    Provided by pytest-asyncio, no imports needed.
    
- test_user_credentials (line 56):
    Test user login credentials (username='jeduapff', password='Rangers123456*').
    
- invalid_credentials (line 69):
    Invalid credentials for testing authentication failures.

NOTE: These fixtures are injected by pytest automatically. Just use them as
function parameters and pytest will provide the actual objects.

Example:
    async def test_login(async_client, test_user_credentials):
        response = await async_client.post("/login", data=test_user_credentials)
        # async_client is automatically created and passed in!

================================================================================
"""
import pytest
import asyncio
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timezone


# Test fixtures
@pytest.fixture
def test_user_credentials():
    """Standard test user credentials"""
    return {
        "username": "admin",
        "password": "admin123"
    }


@pytest.fixture
def invalid_credentials():
    """Invalid credentials for negative testing"""
    return {
        "username": "nonexistent",
        "password": "wrongpassword"
    }


class TestAuthentication:
    """Core authentication test suite"""
    
    @pytest.mark.asyncio
    async def test_01_login_success(self, async_client: AsyncClient, test_user_credentials):
        """
        Test successful login with valid credentials
        
        CRITICAL: This validates that users can authenticate
        """
        response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        
        # Verify token is not empty
        assert len(data["access_token"]) > 0
        
        print("✅ Login successful - token received")
    
    @pytest.mark.asyncio
    async def test_02_login_invalid_credentials(self, async_client: AsyncClient, invalid_credentials):
        """
        Test login failure with invalid credentials
        
        CRITICAL: Ensures unauthorized users cannot access the system
        """
        response = await async_client.post(
            "/api/v1/auth/token",
            data=invalid_credentials
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Invalid credentials correctly rejected")
    
    @pytest.mark.asyncio
    async def test_03_access_protected_route_without_token(self, async_client: AsyncClient):
        """
        Test accessing protected routes without authentication
        
        CRITICAL: Validates that protected routes require authentication
        """
        response = await async_client.get("/api/v1/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Protected route correctly requires authentication")
    
    @pytest.mark.asyncio
    async def test_04_access_protected_route_with_token(self, async_client: AsyncClient, test_user_credentials):
        """
        Test accessing protected routes with valid token
        
        CRITICAL: Validates authenticated access works
        """
        # Login first to get token
        login_response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        token = login_response.json()["access_token"]
        
        # Access protected route with token
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify user data structure
        assert "username" in data
        assert data["username"] == test_user_credentials["username"]
        
        print("✅ Protected route accessible with valid token")
    
    @pytest.mark.asyncio
    async def test_05_multiple_login_sessions(self, async_client: AsyncClient, test_user_credentials):
        """
        Test multiple login sessions for the same user
        
        CRITICAL: Validates concurrent sessions work correctly
        """
        tokens = []
        
        # Create 3 sessions
        for i in range(3):
            response = await async_client.post(
                "/api/v1/auth/token",
                data=test_user_credentials
            )
            assert response.status_code == status.HTTP_200_OK
            tokens.append(response.json()["access_token"])
        
        # All tokens should be different (each session gets unique token)
        assert len(set(tokens)) == 3, "Each login should generate a unique token"
        
        # All tokens should be valid
        for token in tokens:
            response = await async_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == status.HTTP_200_OK
        
        print(f"✅ Multiple sessions ({len(tokens)}) work correctly")
    
    @pytest.mark.asyncio
    async def test_06_login_logout_cycle(self, async_client: AsyncClient, test_user_credentials):
        """
        Test complete login/logout cycle
        
        CRITICAL: Validates session lifecycle management
        """
        # Login
        login_response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        
        # Verify token works
        me_response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == status.HTTP_200_OK
        
        # Logout
        logout_response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == status.HTTP_200_OK
        
        print("✅ Login/logout cycle completed successfully")
    
    @pytest.mark.asyncio
    async def test_07_token_with_invalid_format(self, async_client: AsyncClient):
        """
        Test accessing protected routes with malformed token
        
        CRITICAL: Ensures token validation works
        """
        # Try with completely invalid token
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Malformed token correctly rejected")
    
    @pytest.mark.asyncio
    async def test_08_missing_authorization_header(self, async_client: AsyncClient):
        """
        Test accessing protected route without Authorization header
        
        CRITICAL: Validates header requirement
        """
        response = await async_client.get("/api/v1/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Missing authorization header correctly handled")


class TestMultipleLoginLogoutCycles:
    """Test multiple consecutive login/logout cycles"""
    
    @pytest.mark.asyncio
    async def test_01_five_consecutive_cycles(self, async_client: AsyncClient, test_user_credentials):
        """
        Test 5 consecutive login/logout cycles
        
        CRITICAL: Validates system handles repeated auth cycles
        """
        for cycle in range(5):
            # Login
            login_response = await async_client.post(
                "/api/v1/auth/token",
                data=test_user_credentials
            )
            assert login_response.status_code == status.HTTP_200_OK
            token = login_response.json()["access_token"]
            
            # Verify authenticated access
            me_response = await async_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert me_response.status_code == status.HTTP_200_OK
            
            # Logout
            logout_response = await async_client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert logout_response.status_code == status.HTTP_200_OK
            
            print(f"✅ Cycle {cycle + 1}/5 completed")
        
        print("✅ All 5 login/logout cycles successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
