"""
Asynchronous database session management for FastAPI
Using SQLite with aiosqlite backend and WAL mode enabled
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from config import DATABASE_URL


# --- Create async database engine ---
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    future=True
)

# --- Enable performance PRAGMAs for SQLite ---
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL, foreign keys, and reasonable performance options"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")     # Enables write-ahead logging (better concurrency)
    cursor.execute("PRAGMA synchronous = NORMAL;")  # Faster commits, still durable
    cursor.execute("PRAGMA foreign_keys = ON;")     # Enforce FK constraints
    cursor.close()

# --- Create async session factory ---
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

# --- Dependency for FastAPI endpoints ---
async def get_db():
    """
    Provides a new async database session per request.
    Closes it automatically when the request is done.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
            
# Example usage in FastAPI endpoints:
'''
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.sessions import get_db
async def some_endpoint(db: AsyncSession = Depends(get_db)):
    result = await db.execute(some_query)
    ...
'''
