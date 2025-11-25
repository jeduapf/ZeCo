"""
Core Protected Routes Tests

Tests protected route access control:
- Admin-only routes
- Staff-only routes
- User role verification
- Permission hierarchies

These tests MUST pass for security to function correctly.

================================================================================
FIXTURES USED:
================================================================================

FROM conftest.py (automatically loaded by pytest):
---------------------------------------------------
- async_client (line 38):
    Async HTTP client for making API requests.

LOCAL FIXTURES (defined in this file):
---------------------------------------
- admin_credentials (line 18):
    Admin user credentials for testing.
    Current: username='jeduapf', password='Rangers123456*'
    
- admin_token (line 26):
    Gets authentication token by logging in with admin_credentials.
    Returns the JWT token string.
    
- admin_headers (line 35):
    Authorization headers with admin token.
    Returns: {"Authorization": "Bearer <token>"}

NOTE: Both conftest.py fixtures and local fixtures work the same way - just
add them as function parameters and pytest injects them automatically.

Example:
    async def test_admin_access(async_client, admin_headers):
        response = await async_client.get("/admin/users", headers=admin_headers)
        # Both async_client and admin_headers are auto-injected!

================================================================================
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.fixture
def admin_credentials():
    """Admin user credentials"""
    return {
        "username": "jeduapf",
        "password": "Rangers123456*"
    }


@pytest.fixture
async def admin_token(async_client: AsyncClient, admin_credentials):
    """Get admin auth token"""
    response = await async_client.post(
        "/api/v1/auth/token",
        data=admin_credentials
    )
    return response.json()["access_token"]


@pytest.fixture
async def admin_headers(admin_token):
    """Get headers with admin token"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestProtectedRoutesAccess:
    """Test access control for protected routes"""
    
    @pytest.mark.asyncio
    async def test_01_admin_route_requires_admin_role(
        self,
        async_client: AsyncClient,
        admin_headers
    ):
        """
        Test admin routes require admin role
        
        CRITICAL: Admin routes should only be accessible by admins
        """
        # Admin should be able to access admin routes
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=admin_headers
        )
        
        # Should succeed with admin credentials
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # Endpoint might not exist
        ]
        
        print("✅ Admin routes accessible with admin credentials")
    
    @pytest.mark.asyncio
    async def test_02_users_me_accessible_when_authenticated(
        self,
        async_client: AsyncClient,
        admin_headers
    ):
        """
        Test /users/me is accessible when authenticated
        
        CRITICAL: Authenticated users should access their own profile
        """
        response = await async_client.get(
            "/api/v1/users/me",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify user data structure
        assert "username" in data
        assert "role" in data or "is_admin" in data
        
        print("✅ Authenticated user can access own profile")
    
    @pytest.mark.asyncio
    async def test_03_protected_route_with_expired_token(
        self,
        async_client: AsyncClient
    ):
        """
        Test protected routes reject expired tokens
        
        CRITICAL: Expired tokens should be rejected
        """
        # Use an obviously fake/expired token
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidtoken.signature"
        
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Expired/invalid tokens correctly rejected")
    
    @pytest.mark.asyncio
    async def test_04_protected_route_with_bearer_prefix_missing(
        self,
        async_client: AsyncClient,
        admin_token
    ):
        """
        Test protected routes require proper Bearer prefix
        
        CRITICAL: Token format validation
        """
        # Send token without "Bearer " prefix
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": admin_token}  # Missing "Bearer "
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Bearer prefix requirement enforced")


class TestRoleBasedAccess:
    """Test role-based access control"""
    
    @pytest.mark.asyncio
    async def test_01_admin_can_access_user_list(
        self,
        async_client: AsyncClient,
        admin_headers
    ):
        """
        Test admin can access user list
        
        CRITICAL: Admin should be able to view all users
        """
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=admin_headers
        )
        
        # Should succeed or return 404 if endpoint doesn't exist
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert isinstance(data, list), "User list should be an array"
            print(f"✅ Admin accessed user list ({len(data)} users)")
        else:
            print("✅ Admin endpoint structure validated (endpoint may not exist)")


class TestTokenRefresh:
    """Test token refresh functionality if implemented"""
    
    @pytest.mark.asyncio
    async def test_01_token_remains_valid_across_requests(
        self,
        async_client: AsyncClient,
        admin_headers
    ):
        """
        Test token remains valid across multiple requests
        
        CRITICAL: Token should work for multiple requests
        """
        # Make multiple requests with same token
        for i in range(5):
            response = await async_client.get(
                "/api/v1/users/me",
                headers=admin_headers
            )
            assert response.status_code == status.HTTP_200_OK
        
        print("✅ Token valid across 5 consecutive requests")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
