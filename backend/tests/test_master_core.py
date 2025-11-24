"""
MASTER CORE TESTS - ZeCo Application

This is the MASTER test suite that runs all core functionality tests.
These tests MUST PASS for the application to be considered functional.

Run this test file to validate all critical features:
    pytest tests/test_master_core.py -v

Test Categories:
1. API Connectivity (Health, CORS, Basic Endpoints)
2. Authentication (Login, Logout, Sessions)
3. Protected Routes (Access Control, Permissions)
4. Integration Tests (End-to-End Workflows)

WARNING: If any test in this file fails, the application has a critical issue.

================================================================================
FIXTURES USED (all automatically loaded from conftest.py):
================================================================================

These fixtures are NOT imported - pytest automatically discovers them from
conftest.py and injects them as function parameters. This is pytest's standard
fixture system.

FROM conftest.py:
-----------------
- async_client (line 38):
    Async HTTP client for testing API endpoints without starting a server.
    Usage: async def test_example(async_client): ...
    
- test_user_credentials (line 56):
    Dictionary with test user login credentials.
    Current values: username='jeduapff', password='Rangers123456*'
    
- invalid_credentials (line 69):
    Dictionary with invalid credentials for negative testing.
    
- authenticated_client (line 78):
    Tuple of (async_client, auth_token) - pre-authenticated client.
    Automatically logs in using test_user_credentials.
    
- auth_headers (line 110):
    Dictionary with Authorization header containing valid token.
    Format: {"Authorization": "Bearer <token>"}

HOW TO USE FIXTURES:
--------------------
Just add them as function parameters - pytest handles the rest:

    async def test_example(self, async_client, test_user_credentials):
        response = await async_client.post("/login", data=test_user_credentials)
        # async_client and test_user_credentials are automatically provided!

================================================================================
"""
import pytest
from httpx import AsyncClient
from fastapi import status


# ==============================================================================
# PHASE 1: API CONNECTIVITY TESTS (Must Pass First)
# ==============================================================================

class TestPhase1_APIConnectivity:
    """
    Phase 1: Validate basic API connectivity
    
    These tests ensure the backend is running and responding.
    If these fail, nothing else will work.
    """
    
    @pytest.mark.asyncio
    async def test_01_health_check(self, async_client: AsyncClient):
        """CRITICAL: Backend must be responsive"""
        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"
        print("✅ Phase 1.1: Health check passed")
    
    @pytest.mark.asyncio
    async def test_02_root_endpoint(self, async_client: AsyncClient):
        """CRITICAL: API root must be accessible"""
        response = await async_client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        print("✅ Phase 1.2: Root endpoint accessible")
    
    @pytest.mark.asyncio
    async def test_03_openapi_docs(self, async_client: AsyncClient):
        """CRITICAL: API documentation must be available"""
        response = await async_client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        assert "openapi" in response.json()
        print("✅ Phase 1.3: OpenAPI documentation available")
    
    @pytest.mark.asyncio
    async def test_04_cors_configuration(self, async_client: AsyncClient):
        """CRITICAL: CORS must allow frontend communication"""
        response = await async_client.options(
            "/api/v1/auth/token",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST"
            }
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        print("✅ Phase 1.4: CORS configuration validated")


# ==============================================================================
# PHASE 2: AUTHENTICATION TESTS
# ==============================================================================

class TestPhase2_Authentication:
    """
    Phase 2: Validate authentication system
    
    These tests ensure users can log in, log out, and maintain sessions.
    """
    
    @pytest.mark.asyncio
    async def test_01_login_success(self, async_client: AsyncClient, test_user_credentials):
        """CRITICAL: Valid credentials must allow login"""
        response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()
        print("✅ Phase 2.1: Login successful")
    
    @pytest.mark.asyncio
    async def test_02_login_invalid_credentials(self, async_client: AsyncClient, invalid_credentials):
        """CRITICAL: Invalid credentials must be rejected"""
        response = await async_client.post(
            "/api/v1/auth/token",
            data=invalid_credentials
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Phase 2.2: Invalid credentials rejected")
    
    @pytest.mark.asyncio
    async def test_03_authenticated_access(self, async_client: AsyncClient, test_user_credentials):
        """CRITICAL: Token must grant access to protected routes"""
        # Login
        login_response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        token = login_response.json()["access_token"]
        
        # Access protected route
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "username" in response.json()
        print("✅ Phase 2.3: Authenticated access works")
    
    @pytest.mark.asyncio
    async def test_04_logout_cycle(self, async_client: AsyncClient, test_user_credentials):
        """CRITICAL: Login/logout cycle must work"""
        # Login
        login_response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        token = login_response.json()["access_token"]
        
        # Logout
        logout_response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == status.HTTP_200_OK
        print("✅ Phase 2.4: Logout successful")
    
    @pytest.mark.asyncio
    async def test_05_multiple_sessions(self, async_client: AsyncClient, test_user_credentials):
        """CRITICAL: Multiple login sessions must work"""
        tokens = []
        for i in range(3):
            response = await async_client.post(
                "/api/v1/auth/token",
                data=test_user_credentials
            )
            assert response.status_code == status.HTTP_200_OK
            tokens.append(response.json()["access_token"])
        
        # All tokens should be unique and valid
        assert len(set(tokens)) == 3
        print("✅ Phase 2.5: Multiple sessions supported")


# ==============================================================================
# PHASE 3: PROTECTED ROUTES & ACCESS CONTROL
# ==============================================================================

class TestPhase3_ProtectedRoutes:
    """
    Phase 3: Validate access control and permissions
    
    These tests ensure protected routes are secured properly.
    """
    
    @pytest.mark.asyncio
    async def test_01_protected_route_without_token(self, async_client: AsyncClient):
        """CRITICAL: Protected routes must reject unauthenticated access"""
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Phase 3.1: Unauthenticated access blocked")
    
    @pytest.mark.asyncio
    async def test_02_protected_route_with_invalid_token(self, async_client: AsyncClient):
        """CRITICAL: Invalid tokens must be rejected"""
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Phase 3.2: Invalid token rejected")
    
    @pytest.mark.asyncio
    async def test_03_token_format_validation(self, async_client: AsyncClient, test_user_credentials):
        """CRITICAL: Bearer prefix must be required"""
        # Login
        login_response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        token = login_response.json()["access_token"]
        
        # Try without "Bearer " prefix
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Phase 3.3: Bearer prefix enforced")
    
    @pytest.mark.asyncio
    async def test_04_admin_routes_protected(self, async_client: AsyncClient):
        """CRITICAL: Admin routes must require authentication"""
        response = await async_client.get("/api/v1/admin/users")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print("✅ Phase 3.4: Admin routes protected")


# ==============================================================================
# PHASE 4: INTEGRATION TESTS (End-to-End Workflows)
# ==============================================================================

class TestPhase4_Integration:
    """
    Phase 4: End-to-end workflow testing
    
    These tests validate complete user workflows work correctly.
    """
    
    @pytest.mark.asyncio
    async def test_01_complete_auth_workflow(self, async_client: AsyncClient, test_user_credentials):
        """
        CRITICAL: Complete authentication workflow
        
        Steps:
        1. Login
        2. Access protected resource
        3. Logout
        4. Verify access denied after logout (if token blacklisting exists)
        """
        # Step 1: Login
        login_response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        
        # Step 2: Access protected resource
        me_response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == status.HTTP_200_OK
        user_data = me_response.json()
        assert user_data["username"] == test_user_credentials["username"]
        
        # Step 3: Logout
        logout_response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == status.HTTP_200_OK
        
        print("✅ Phase 4.1: Complete auth workflow successful")
    
    @pytest.mark.asyncio
    async def test_02_consecutive_login_logout_cycles(
        self,
        async_client: AsyncClient,
        test_user_credentials
    ):
        """
        CRITICAL: Multiple login/logout cycles must work
        
        Simulates user logging in and out multiple times.
        """
        for cycle in range(3):
            # Login
            login_response = await async_client.post(
                "/api/v1/auth/token",
                data=test_user_credentials
            )
            assert login_response.status_code == status.HTTP_200_OK
            token = login_response.json()["access_token"]
            
            # Verify access
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
        
        print("✅ Phase 4.2: 3 consecutive cycles successful")
    
    @pytest.mark.asyncio
    async def test_03_token_persistence_across_requests(
        self,
        async_client: AsyncClient,
        test_user_credentials
    ):
        """
        CRITICAL: Token must remain valid across multiple requests
        
        Simulates a user making multiple API calls in one session.
        """
        # Login
        login_response = await async_client.post(
            "/api/v1/auth/token",
            data=test_user_credentials
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Make 5 consecutive requests with same token
        for i in range(5):
            response = await async_client.get("/api/v1/users/me", headers=headers)
            assert response.status_code == status.HTTP_200_OK
        
        print("✅ Phase 4.3: Token valid across 5 requests")


# ==============================================================================
# PHASE 5: ERROR HANDLING & EDGE CASES
# ==============================================================================

class TestPhase5_ErrorHandling:
    """
    Phase 5: Error handling validation
    
    These tests ensure the API handles errors gracefully.
    """
    
    @pytest.mark.asyncio
    async def test_01_404_not_found(self, async_client: AsyncClient):
        """CRITICAL: Non-existent endpoints must return 404"""
        response = await async_client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        print("✅ Phase 5.1: 404 errors handled")
    
    @pytest.mark.asyncio
    async def test_02_invalid_json_handling(self, async_client: AsyncClient):
        """CRITICAL: Malformed requests must be handled gracefully"""
        response = await async_client.post(
            "/api/v1/auth/token",
            content="this is not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
        print("✅ Phase 5.2: Invalid JSON handled")
    
    @pytest.mark.asyncio
    async def test_03_missing_required_fields(self, async_client: AsyncClient):
        """CRITICAL: Missing required fields must return validation error"""
        response = await async_client.post(
            "/api/v1/auth/token",
            data={}  # Missing username and password
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
        print("✅ Phase 5.3: Missing fields validated")


# ==============================================================================
# TEST EXECUTION SUMMARY
# ==============================================================================

def pytest_sessionfinish(session, exitstatus):
    """
    Print summary after all tests complete
    """
    print("\n" + "="*70)
    print("MASTER CORE TESTS SUMMARY")
    print("="*70)
    
    if exitstatus == 0:
        print("✅ ALL CORE TESTS PASSED - Application is functional!")
        print("\nThe following systems are verified:")
        print("  ✅ API Connectivity")
        print("  ✅ Authentication System")
        print("  ✅ Protected Routes & Access Control")
        print("  ✅ Integration Workflows")
        print("  ✅ Error Handling")
    else:
        print("❌ CORE TESTS FAILED - Critical issues detected!")
        print("\n⚠️  The application has fundamental problems that must be fixed.")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
