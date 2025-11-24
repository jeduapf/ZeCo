# ZeCo Testing Guide

Comprehensive testing documentation for the ZeCo application covering backend, frontend, and end-to-end tests.

---

## Test Structure

```
ZeCo/
├── backend/tests/          # Backend API integration tests
│   ├── conftest.py        # Shared pytest fixtures
│   ├── test_master_core.py   # MASTER TEST SUITE ⭐
│   ├── test_core_auth.py     # Authentication tests
│   ├── test_core_api.py      # API connectivity tests
│   └── test_core_protected_routes.py  # Access control tests
├── frontend/src/test/     # Frontend component tests
│   ├── setup.js           # Vitest configuration
│   ├── App.test.jsx       # App component tests
│   └── LandingPage.test.jsx  # Landing page tests
└── tests/e2e/             # End-to-end browser tests
    ├── guest-flow.spec.js    # Guest user journey
    ├── auth-flow.spec.js     # Authentication workflows
    └── staff-flow.spec.js    # Staff certificate flow
```

---

## Quick Start

### Install Dependencies

**Backend** (Python):
```bash
cd backend
pip install pytest pytest-asyncio httpx
```

**Frontend** (Node.js):
```bash
cd frontend
npm install
```

**E2E Tests** (Playwright):
```bash
npm install -D @playwright/test
npx playwright install
```

---

## Running Tests

### 1. Backend Tests (API Integration)

**Run all core tests** (RECOMMENDED):
```bash
cd backend
pytest tests/test_master_core.py -v
```

**Run specific  test category**:
```bash
pytest tests/test_core_auth.py -v          # Authentication only
pytest tests/test_core_api.py -v           # API connectivity only
pytest tests/test_core_protected_routes.py -v  # Access control only
```

**Run with coverage**:
```bash
pytest tests/ --cov=src --cov-report=html
```

**Expected Output**:
```
✅ Phase 1: API Connectivity
✅ Phase 2: Authentication
✅ Phase 3: Protected Routes
✅ Phase 4: Integration Workflows
✅ Phase 5: Error Handling

ALL CORE TESTS PASSED - Application is functional!
```

---

### 2. Frontend Tests (Component Unit Tests)

**Run all frontend tests**:
```bash
cd frontend
npm test
```

**Run with UI** (interactive):
```bash
npm run test:ui
```

**Run with coverage**:
```bash
npm run test:coverage
```

**Watch mode** (auto-rerun on changes):
```bash
npm test -- --watch
```

---

### 3. End-to-End Tests (Full Stack)

**Prerequisites**:
- Backend must be running on `http://localhost:8000`
- Frontend must be running on `http://localhost:5173`

**Run all E2E tests**:
```bash
npx playwright test
```

**Run specific test file**:
```bash
npx playwright test tests/e2e/guest-flow.spec.js
npx playwright test tests/e2e/auth-flow.spec.js
npx playwright test tests/e2e/staff-flow.spec.js
```

**Run with UI** (headed mode):
```bash
npx playwright test --ui
```

**Generate HTML report**:
```bash
npx playwright show-report
```

> **Note**: Playwright config automatically starts frontend/backend servers if not running.

---

## Test Coverage

### Backend Tests Cover:
- ✅ Health check endpoints
- ✅ CORS configuration
- ✅ Login/Logout workflows
- ✅ Multiple concurrent sessions
- ✅ Token validation & expiration
- ✅ Protected route access control
- ✅ Role-based permissions (admin, user)
- ✅ Error handling (404, 422, 401)
- ✅ API documentation availability

### Frontend Tests Cover:
- ✅ Component rendering
- ✅ Guest button navigation
- ✅ Staff button HTTP/HTTPS logic
- ✅ Certificate instructions modal
- ✅ License activation flow
- ✅ HTTP vs HTTPS routing
- ✅ Route protection

### E2E Tests Cover:
- ✅ Complete guest user journey
- ✅ Complete staff user journey
- ✅ Login/Logout workflows (browser)
- ✅ Certificate check on HTTP
- ✅ HTTPS redirect for staff
- ✅ Protected route access in browser
- ✅ Page rendering across all routes
- ✅ Multiple login/logout cycles

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && pytest tests/test_master_core.py -v

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm test

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install -D @playwright/test
      - run: npx playwright install --with-deps
      - run: npx playwright test
```

---

## Test Maintenance

### When to Run Tests

| Scenario | Tests to Run |
|----------|-------------|
| Before commit | Backend Master + Frontend |
| Before deployment | All tests (Backend + Frontend + E2E) |
| After API changes | Backend tests |
| After UI changes | Frontend + E2E tests |
| Weekly/Nightly | Full suite with coverage |

### Adding New Tests

**For new API endpoints** → Add to `backend/tests/test_core_api.py`

**For new authentication features** → Add to `backend/tests/test_core_auth.py`

**For new React components** → Create `frontend/src/test/ComponentName.test.jsx`

**For new user workflows** → Create `tests/e2e/workflow-name.spec.js`

**For core functionality** → Add to `backend/tests/test_master_core.py`

---

## Troubleshooting

### Backend Tests Failing

**Issue**: `Module not found` errors
```bash
# Solution: Ensure you're in backend directory
cd backend
pytest tests/
```

**Issue**: Database connection errors
```bash
# Solution: Initialize database
cd backend
python main.py  # Let it create tables, then stop
pytest tests/
```

**Issue**: `async_client` fixture not found
```bash
# Solution: Install dependencies
pip install pytest-asyncio httpx
```

### Frontend Tests Failing

**Issue**: `Cannot find module 'vitest'`
```bash
# Solution: Install dependencies
cd frontend
npm install
```

**Issue**: `ReferenceError: document is not defined`
```bash
# Solution: Ensure jsdom is configured in vitest.config.js
# Check that environment: 'jsdom' is set
```

### E2E Tests Failing

**Issue**: `page.goto: net::ERR_CONNECTION_REFUSED`
```bash
# Solution: Start frontend/backend manually
cd frontend && npm run dev  # Terminal 1
cd backend && python main.py  # Terminal 2
npx playwright test  # Terminal 3
```

**Issue**: `Timeout waiting for locator`
```bash
# Solution: Check selectors in test files
# Verify the text/element exists on the page
npx playwright test --ui  # Run in headed mode to debug
```

---

## Test Credentials

Default test user (ensure exists in database):
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: Admin

---

## Performance Benchmarks

| Test Suite | Expected Duration | Test Count |
|------------|------------------|------------|
| Backend Master | ~10-15 seconds | 20+ tests |
| Frontend Unit | ~5-10 seconds | 10+ tests |
| E2E Full Suite | ~30-60 seconds | 15+ tests |

---

## Next Steps

1. **Run backend tests first**: `cd backend && pytest tests/test_master_core.py -v`
2. **If backend passes, run frontend**: `cd frontend && npm test`
3. **If both pass, run E2E**: `npx playwright test`
4. **Review coverage reports** to identify gaps
5. **Add tests for new features** before merging PRs

---

**⚠️ CRITICAL**: The `test_master_core.py` suite represents minimum viable functionality. If it fails, the application is broken.
