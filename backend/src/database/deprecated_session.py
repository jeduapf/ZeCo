# """
# Database session management
# However all this is syncronous and deprecated because it won't support several users 
# using the database at the same time and will lead to database locks and slowdowns.
# """
# from sqlalchemy import create_engine, event
# from sqlalchemy.orm import sessionmaker
# from config import DATABASE_URL

# # Create database engine
# engine = create_engine(
#     DATABASE_URL,
#     connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
# )

# # Enable WAL and other performance PRAGMAs automatically for SQLite so that they help with concurrency and speed
# @event.listens_for(engine, "connect")
# def set_sqlite_pragma(dbapi_connection, connection_record):
#     cursor = dbapi_connection.cursor()
#     cursor.execute("PRAGMA journal_mode=WAL;")       # Enables write-ahead logging
#     cursor.execute("PRAGMA synchronous = NORMAL;")    # Faster commits, still safe
#     cursor.execute("PRAGMA foreign_keys = ON;")       # Enforce FK constraints
#     cursor.close()

# # Create session factory
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# def get_db():
#     """Dependency to get database session"""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()