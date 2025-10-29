"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from database.base import Base
from database.session import engine
from api.v1.router import api_router

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

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")

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