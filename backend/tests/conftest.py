"""
Shared Test Fixtures and Configuration

This file provides pytest fixtures used across all test files.
Includes:
- Async client setup
- Database session management
- Common test data
- Authentication helpers
"""
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session

# Import the FastAPI app
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app
# from src import Base, engine  # These may not be directly available
# If needed for DB tests, import from actual module locations


# Configure pytest to use asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for testing API endpoints
    
    This fixture provides an async HTTP client that can make requests
    to the FastAPI application without needing to start a server.
    
    Usage:
        async def test_example(async_client):
            response = await async_client.get("/endpoint")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user_credentials():
    """
    Standard test user credentials
    
    Returns valid credentials for a test user account.
    Password meets requirements: uppercase, lowercase, digit, special char
    """
    return {
        "username": "jeduapf",  # ADMIN user from database
        "password": "Rangers123456*"
    }


@pytest.fixture
def invalid_credentials():
    """Invalid credentials for negative testing"""
    return {
        "username": "nonexistent_user",
        "password": "wrong_password_123"
    }


@pytest_asyncio.fixture
async def authenticated_client(
    async_client: AsyncClient,
    test_user_credentials: dict
) -> tuple[AsyncClient, str]:
    """
    Async client with authentication token
    
    Returns:
        tuple: (async_client, auth_token)
    
    Usage:
        async def test_protected(authenticated_client):
            client, token = authenticated_client
            response = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
    """
    # Login to get token
    response = await async_client.post(
        "/api/v1/auth/token",
        data=test_user_credentials
    )
    
    if response.status_code != 200:
        pytest.fail(f"Authentication failed: {response.json()}")
    
    token = response.json()["access_token"]
    return async_client, token


@pytest_asyncio.fixture
async def auth_headers(authenticated_client) -> dict:
    """
    Returns authorization headers with valid token
    
    Usage:
        async def test_example(async_client, auth_headers):
            response = await async_client.get(
                "/api/v1/protected",
                headers=auth_headers
            )
    """
    _, token = authenticated_client
    return {"Authorization": f"Bearer {token}"}


# Test data fixtures
@pytest.fixture
def sample_menu_item():
    """Sample menu item data for testing"""
    return {
        "name": "Test Burger",
        "description": "A delicious test burger",
        "price": 9.99,
        "category": "main",
        "available": True
    }


@pytest.fixture
def sample_order():
    """Sample order data for testing"""
    return {
        "table_number": 5,
        "items": [
            {"menu_item_id": 1, "quantity": 2},
            {"menu_item_id": 2, "quantity": 1}
        ],
        "notes": "Test order"
    }


# Database fixtures (if needed for integration tests)
# NOTE: Commented out because Base/engine imports may not be available
# Uncomment and fix imports if you need direct DB access in tests
#
# @pytest.fixture(scope="function")
# async def db_session() -> AsyncGenerator[AsyncSession, None]:
#     """
#     Database session for tests that need direct DB access
#     
#     This creates a test database session that is cleaned up after each test.
#     """
#     async with engine.begin() as conn:
#         # Create tables
#         await conn.run_sync(Base.metadata.create_all)
#     
#     # Create session
#     async_session = async_sessionmaker(
#         engine,
#         class_=AsyncSession,
#         expire_on_commit=False
#     )
#     
#     async with async_session() as session:
#         yield session
#     
#     # Cleanup (if needed)
#     # Note: Be careful with this in production-like environments
#     # async with engine.begin() as conn:
#     #     await conn.run_sync(Base.metadata.drop_all)


# Pytest configuration
def pytest_configure(config):
    """
    Pytest configuration hook
    
    Add custom markers and configuration here.
    """
    config.addinivalue_line(
        "markers", "critical: mark test as critical (must pass)"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication-related"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API connectivity test"
    )


# Custom pytest options (if needed)
def pytest_addoption(parser):
    """Add custom command-line options"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run slow tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers"""
    # Skip slow tests unless explicitly requested
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
