"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from src import Base, engine, api_router, SlidingTokenMiddleware
from config import TOKEN_REFRESH_THRESHOLD_MINUTES, API_VERSION


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

# CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add sliding token middleware
app.add_middleware(
    SlidingTokenMiddleware,
    threshold_minutes=TOKEN_REFRESH_THRESHOLD_MINUTES  # Refresh if less than configured minutes remain
)

# Include API v1 router
app.include_router(api_router, prefix=f"/api/{API_VERSION}")

# Create database tables
Base.metadata.create_all(bind=engine)

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint"""
    return {
        "message": "API is running",
        "version": "0.0.1",
        "docs": "/docs"
    }

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}