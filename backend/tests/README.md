# ZeCo Core Test Suite

This directory contains comprehensive integration tests for the ZeCo application.

## Test Structure

### Master Test Suite
**`test_master_core.py`** - The primary test file that MUST always pass. Run this first to validate all core functionality.

```bash
pytest tests/test_master_core.py -v
```

This master suite runs tests in 5 phases:
1. **API Connectivity** - Health checks, CORS, basic endpoints
2. **Authentication** - Login/logout, sessions, token validation
3. **Protected Routes** - Access control, permissions
4. **Integration** - End-to-end workflows
5. **Error Handling** - 404s, invalid data, edge cases

### Individual Test Files

These can be run separately for targeted testing:

- **`test_core_auth.py`** - Authentication system tests
  ```bash
  pytest tests/test_core_auth.py -v
  ```

- **`test_core_api.py`** - API connectivity and health checks
  ```bash
  pytest tests/test_core_api.py -v
  ```

- **`test_core_protected_routes.py`** - Access control tests
  ```bash
  pytest tests/test_core_protected_routes.py -v
  ```

### Shared Fixtures

**`conftest.py`** - Contains shared test fixtures:
- `async_client` - Async HTTP client for API testing
- `test_user_credentials` - Default test credentials
- `authenticated_client` - Pre-authenticated client
- `auth_headers` - Authorization headers helper

## Running Tests

### Run All Core Tests
```bash
pytest tests/test_master_core.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_master_core.py::TestPhase2_Authentication -v
```

### Run Single Test
```bash
pytest tests/test_master_core.py::TestPhase1_APIConnectivity::test_01_health_check -v
```

### Run with Detailed Output
```bash
pytest tests/test_master_core.py -v -s
```

### Run with Coverage
```bash
pytest tests/test_master_core.py --cov=src --cov-report=html
```

## Test Requirements

Tests require the following to be running:
1. ✅ Backend server must be operational
2. ✅ Database must be initialized
3. ✅ Default admin user must exist (username: admin, password: admin123)

## Adding New Tests

### For New Features
Create a new test file for specific features:
```python
# tests/test_feature_orders.py
import pytest
from httpx import AsyncClient

class TestOrderSystem:
    @pytest.mark.asyncio
    async def test_create_order(self, async_client, auth_headers):
        response = await async_client.post(
            "/api/v1/orders",
            json={"table": 5, "items": [...]},
            headers=auth_headers
        )
        assert response.status_code == 201
```

### For Core Functionality
Add tests to the appropriate phase in `test_master_core.py`:
```python
class TestPhase2_Authentication:
    @pytest.mark.asyncio
    async def test_06_new_auth_feature(self, async_client):
        # Your test here
        pass
```

## Test Markers

Use pytest markers for test organization:
```python
@pytest.mark.critical  # Must-pass tests
@pytest.mark.auth      # Authentication tests
@pytest.mark.api       # API tests
@pytest.mark.slow      # Long-running tests
```

## Continuous Integration

Add to your CI pipeline:
```yaml
# .github/workflows/tests.yml
- name: Run Core Tests
  run: pytest tests/test_master_core.py -v --tb=short
```

## Debugging Failed Tests

If a test fails:
1. Check the detailed error output
2. Run the specific test with `-s` for print statements
3. Use `--tb=long` for full tracebacks
4. Check the backend logs

```bash
pytest tests/test_master_core.py::TestPhase2_Authentication::test_01_login_success -v -s --tb=long
```

## Expected Test Output

When all tests pass:
```
======================================================================
MASTER CORE TESTS SUMMARY
======================================================================
✅ ALL CORE TESTS PASSED - Application is functional!

The following systems are verified:
  ✅ API Connectivity
  ✅ Authentication System
  ✅ Protected Routes & Access Control
  ✅ Integration Workflows
  ✅ Error Handling
======================================================================
```

## Maintenance

- **Weekly**: Run full test suite
- **Before Deployment**: MUST pass all core tests
- **After Changes**: Run related test category
- **License Tests**: Run separately with valid license

---

**⚠️ CRITICAL**: The master test suite (`test_master_core.py`) represents the minimum viable functionality. If these tests fail, the application is broken.
