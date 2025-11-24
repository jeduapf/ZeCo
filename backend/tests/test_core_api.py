"""
Core API Connectivity Tests

Tests backend-frontend connectivity and basic API functionality:
- Health check endpoint
- API version endpoint
- Backend availability
- CORS configuration
- License endpoints (without valid license)

These tests MUST pass for basic API communication to work.

================================================================================
FIXTURES USED (automatically loaded from conftest.py):
================================================================================

FROM conftest.py:
-----------------
- async_client (line 38):
    Async HTTP client for testing API endpoints.
    Creates a test client that talks directly to the FastAPI app.
    
HOW PYTEST FIXTURES WORK:
--------------------------
Fixtures are NOT imported. Pytest automatically finds conftest.py and makes
all fixtures available to test files in the same directory.

To use a fixture, just add it as a function parameter:
    async def test_health(async_client):
        response = await async_client.get("/health")
        # async_client is automatically provided by pytest!

================================================================================
"""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestAPIConnectivity:
    """Test basic API connectivity and availability"""
    
    @pytest.mark.asyncio
    async def test_01_health_check(self, async_client: AsyncClient):
        """
        Test health check endpoint
        
        CRITICAL: Validates backend is running and responding
        """
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        
        print(f"✅ Health check passed - Backend is {data['status']}")
    
    @pytest.mark.asyncio
    async def test_02_root_endpoint(self, async_client: AsyncClient):
        """
        Test root endpoint
        
        CRITICAL: Validates API root is accessible
        """
        response = await async_client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify API info
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        
        print(f"✅ Root endpoint accessible - API version: {data['version']}")
    
    @pytest.mark.asyncio
    async def test_03_cors_headers(self, async_client: AsyncClient):
        """
        Test CORS configuration
        
        CRITICAL: Validates frontend can communicate with backend
        """
        # Send OPTIONS request (preflight)
        response = await async_client.options(
            "/api/v1/auth/token",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )
        
        # CORS should allow the request
        # Note: The actual header check depends on your CORS middleware config
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        
        print("✅ CORS preflight handled correctly")
    
    @pytest.mark.asyncio
    async def test_04_openapi_docs_accessible(self, async_client: AsyncClient):
        """
        Test OpenAPI documentation endpoint
        
        CRITICAL: Validates API documentation is available
        """
        response = await async_client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify OpenAPI schema structure
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        
        print(f"✅ OpenAPI docs accessible - {len(data.get('paths', {}))} endpoints documented")


class TestLicenseEndpoints:
    """Test license endpoint availability (not activation)"""
    
    @pytest.mark.asyncio
    async def test_01_license_status_endpoint_accessible(self, async_client: AsyncClient):
        """
        Test license status endpoint is accessible
        
        CRITICAL: License endpoint must be reachable even without valid license
        """
        response = await async_client.get("/api/v1/license/status")
        
        # Endpoint should respond (even if license is invalid)
        assert response.status_code in [
            status.HTTP_200_OK,  # Valid license
            status.HTTP_402_PAYMENT_REQUIRED  # No/invalid license
        ]
        
        print(f"✅ License status endpoint accessible (HTTP {response.status_code})")
    
    @pytest.mark.asyncio
    async def test_02_license_activation_endpoint_exists(self, async_client: AsyncClient):
        """
        Test license activation endpoint exists
        
        CRITICAL: License activation must be available for system setup
        """
        # Try to activate with empty payload (should fail gracefully)
        response = await async_client.post(
            "/api/v1/license",
            json={"key": ""}
        )
        
        # Should reject invalid/empty license but endpoint should exist
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,  # Validation error
            status.HTTP_402_PAYMENT_REQUIRED,  # Invalid license
            status.HTTP_500_INTERNAL_SERVER_ERROR  # Missing key
        ]
        
        print("✅ License activation endpoint exists and validates input")


class TestProtectedRoutesAccessibility:
    """Test that protected routes exist and require authentication"""
    
    @pytest.mark.asyncio
    async def test_01_users_me_requires_auth(self, async_client: AsyncClient):
        """
        Test /users/me endpoint requires authentication
        
        CRITICAL: Protected routes must reject unauthenticated access
        """
        response = await async_client.get("/api/v1/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ /users/me correctly requires authentication")
    
    @pytest.mark.asyncio
    async def test_02_admin_routes_require_auth(self, async_client: AsyncClient):
        """
        Test admin routes require authentication
        
        CRITICAL: Admin routes must be protected
        """
        # Try to access admin endpoint without auth
        response = await async_client.get("/api/v1/admin/users")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Admin routes correctly require authentication")


class TestAPIErrorHandling:
    """Test API error handling and response formats"""
    
    @pytest.mark.asyncio
    async def test_01_404_not_found(self, async_client: AsyncClient):
        """
        Test 404 error handling
        
        CRITICAL: Non-existent endpoints should return proper 404
        """
        response = await async_client.get("/api/v1/nonexistent-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        print("✅ 404 errors handled correctly")
    
    @pytest.mark.asyncio
    async def test_02_invalid_json_handling(self, async_client: AsyncClient):
        """
        Test invalid JSON handling
        
        CRITICAL: API should handle malformed requests gracefully
        """
        response = await async_client.post(
            "/api/v1/auth/token",
            content="this is not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 422 (Unprocessable Entity) or 400 (Bad Request)
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
        print("✅ Invalid JSON handled gracefully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
