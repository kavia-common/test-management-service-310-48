"""
Database configuration and session management.
Provides SQLAlchemy engine, session maker, and base model.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from .config import settings


# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PUBLIC_INTERFACE
def init_db() -> None:
    """
    Initialize database by creating all tables.
    Should be called on application startup.
    
    This function:
    - Imports all model modules to ensure they're registered with Base
    - Creates all tables using SQLAlchemy metadata.create_all
    - Is idempotent (safe to call multiple times)
    - Logs errors gracefully without crashing the application
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Import all models to register them with Base.metadata
        # This must be done before create_all is called
        logger.info("Importing all models...")
        from models import test_file, testcase, run, run_config, input_variable  # noqa: F401
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully (or already exist)")
        
    except Exception as e:
        # Log the error but don't crash the application
        # This allows the server to start even if DB is temporarily unavailable
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Application will continue but database operations may fail")
