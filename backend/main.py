"""
FastAPI Application Entry Point

This is the main application file that initializes and configures the ZeCo backend.
It handles:
1. App initialization with metadata
2. CORS middleware configuration
3. License verification middleware
4. Database initialization on startup
5. Root and health check endpoints

All business logic endpoints are organized in routers under src/api/v1/endpoints/
"""
from fastapi import FastAPI, status, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src import Base, engine, api_router
from src.core.license_manager import LicenseManager
from config import API_VERSION
from datetime import timezone, datetime

# === Application Initialization ===

# Initialize FastAPI application with metadata
app = FastAPI(
    title="ZeCo Restaurant Management API",
    description="Backend API for ZeCo restaurant management system with license validation",
    version="1.0.0",
    contact={
        "name": "José ALVES",
        "email": "jeduapf@gmail.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Initialize License Manager (singleton for the application)
# This manager handles JWT license verification and tampering detection
license_manager = LicenseManager()

# === Middleware Configuration ===

# CORS Middleware: Allows cross-origin requests from the frontend
# In production, replace allow_origins=["*"] with specific frontend URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Specify actual origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# License Check Middleware
# This middleware runs BEFORE every request to verify the application license
# It short-circuits the request with a 402 response if the license is invalid
@app.middleware("http")
async def check_license_middleware(request: Request, call_next):
    """
    Verify application license before processing requests.
    
    Execution Order:
    1. Check if path is in allowed_paths (no license required)
    2. If not allowed, verify license via license_manager.is_active()
    3. If license check fails, return 402 Payment Required
    4. If license is valid, proceed to route handler
    
    Allowed Paths (no license check):
    - / (root)
    - /health (health check)
    - /docs, /redoc, /openapi.json (API documentation)
    - /api/v1/license/* (license management endpoints)
    
    Args:
        request: Incoming HTTP request
        call_next: Next middleware/handler in the chain
        
    Returns:
        Response from the route handler or 402 error
    """
    # Define paths that don't require a valid license
    # This allows users to activate their license even without one
    allowed_paths = [
        "/",  # Root endpoint
        "/health",  # Health check for monitoring
        "/docs",  # Swagger UI
        "/redoc",  # ReDoc UI
        "/openapi.json",  # OpenAPI schema
        f"/api/{API_VERSION}/license",  # License activation
        f"/api/{API_VERSION}/license/status"  # License status check
    ]
    
    # Check if the requested path is allowed without a license
    # Allow: license endpoints, auth endpoints (login/register), and public paths
    if (request.url.path in allowed_paths or 
        request.url.path.startswith(f"/api/{API_VERSION}/license") or
        request.url.path.startswith(f"/api/{API_VERSION}/auth")):
        return await call_next(request)
    
    # Verify license for all other paths
    try:
        license_manager.is_active()
    except HTTPException as e:
        # Return 402 Payment Required if license is invalid/expired
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        # Catch any unexpected errors during license verification
        # In production, log this error for debugging
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"License check failed: {str(e)}"}
        )
        
    # License is valid, proceed to the route handler
    return await call_next(request)

# === Router Registration ===

# Include all API v1 routes
# The api_router is defined in src/api/v1/router.py and combines all endpoint routers
# All routes will be prefixed with /api/v1 (e.g., /api/v1/auth/login)
app.include_router(api_router, prefix=f"/api/{API_VERSION}")

# === Database Initialization ===

async def init_db():
    """
    Initialize database tables on application startup.
    
    This function creates all tables defined in SQLAlchemy models.
    It runs synchronously within an async context using run_sync().
    """
    async with engine.begin() as conn:
        # Create all tables defined in Base.metadata
        # Base is imported from src/__init__.py and includes all models
        await conn.run_sync(Base.metadata.create_all)

# Register startup event handler
@app.on_event("startup")
async def on_startup():
    """
    Application startup handler.
    
    This runs once when the server starts, before accepting requests.
    Currently only initializes the database, but can be extended for:
    - Cache warming
    - External service connections
    - Background task initialization
    """
    await init_db()

# === Root Endpoints ===

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Root endpoint - API information.
    
    Returns basic API info and link to documentation.
    Useful for verifying the API is running.
    """
    return {
        "message": "ZeCo API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    This endpoint is exempt from license checks (see middleware above).
    Returns current status, version, and timestamp in UTC.
    
    Common uses:
    - Docker health checks
    - Load balancer health probes
    - Monitoring systems (Prometheus, Datadog, etc.)
    """
    return {
        "status": "healthy",
        "version": API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
