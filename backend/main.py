"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI, status, Request, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src import Base, engine, api_router
from src.license_manager import LicenseManager
from config import API_VERSION
from datetime import timezone, datetime
from pydantic import BaseModel

# Initialize FastAPI application
app = FastAPI(
    title="FastAPI JWT Auth Demo",
    description="A simple API demonstrating JWT authentication with FastAPI",
    version="0.0.1",
    contact={
        "name": "José ALVES",
        "email": "jeduapf@gmail.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Initialize License Manager
license_manager = LicenseManager()

# CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# License Check Middleware
@app.middleware("http")
async def check_license_middleware(request: Request, call_next):
    # Define allowed paths that don't require a license
    allowed_paths = [
        "/", 
        "/health", 
        "/docs", 
        "/redoc", 
        "/openapi.json",
        f"/api/{API_VERSION}/license",
        f"/api/{API_VERSION}/license/status"
    ]
    
    # Check if path is allowed
    if request.url.path in allowed_paths or request.url.path.startswith(f"/api/{API_VERSION}/license"):
        return await call_next(request)
    
    # Check License
    try:
        license_manager.is_active()
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        # Log error here in production
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"License check failed: {str(e)}"}
        )
        
    return await call_next(request)

# Include API v1 router
app.include_router(api_router, prefix=f"/api/{API_VERSION}")

async def init_db():
    async with engine.begin() as conn:
        # create tables
        await conn.run_sync(Base.metadata.create_all)

# Run DB init on startup
@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint"""
    return {
        "message": "API is running",
        "version": "0.0.1",
        "docs": "/docs"
    }

# === Health Check Endpoint ===
@app.get("/health")
async def health_check():
    """Health check endpoint for frontend monitoring"""
    return {
        "status": "healthy",
        "version": API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# === License Endpoints ===
class LicenseInput(BaseModel):
    key: str

@app.post(f"/api/{API_VERSION}/license", status_code=status.HTTP_200_OK)
async def activate_license(license_data: LicenseInput):
    """Activate or update the license key"""
    try:
        license_manager.set_license(license_data.key)
        return {"message": "License activated successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"/api/{API_VERSION}/license/status", status_code=status.HTTP_200_OK)
async def get_license_status():
    """Check current license status"""
    try:
        license_manager.is_active()
        return {"status": "active", "message": "License is valid"}
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"status": "inactive", "detail": e.detail}
        )
