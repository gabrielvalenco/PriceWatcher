"""
Database connection handling for PriceWatcher
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from .models import Base

def get_database_url():
    """Get database URL from environment variables or return default SQLite URL"""
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    if db_type.lower() == "postgresql":
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "pricewatcher")
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    else:
        # Default to SQLite
        db_path = os.getenv("DB_PATH", "pricewatcher.db")
        return f"sqlite:///{db_path}"

# Create engine
engine = create_engine(get_database_url(), echo=False)

# Create session
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_db():
    """Initialize the database by creating all tables"""
    Base.metadata.create_all(engine)

def get_session():
    """Get a new database session"""
    return Session()

def close_session(session):
    """Close a database session"""
    session.close()
