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
    """
    Base.metadata.create_all(bind=engine)
