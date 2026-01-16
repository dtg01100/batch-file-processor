"""
Database connection and initialization using SQLAlchemy ORM
"""

import os
from typing import Optional
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session


# Get database path from environment variable
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/folders.db")

# Database connection URL
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# SQLAlchemy setup
Base = declarative_base()
_engine = None
_session_maker = None


# ============================================================================
# Database Models
# ============================================================================

class Folder(Base):
    """Folder configuration"""
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True)
    folder_name = Column(String(255), nullable=False)
    alias = Column(String(255))
    folder_is_active = Column(Boolean, default=False)
    connection_type = Column(String(50), default="local")
    connection_params = Column(String(1000), default="{}")
    schedule = Column(String(100))
    enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class OutputProfile(Base):
    """Output format profile"""
    __tablename__ = "output_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    alias = Column(String(100), unique=True)
    description = Column(String(500))
    output_format = Column(String(50))
    edi_tweaks = Column(String(1000), default="{}")
    custom_settings = Column(String(2000), default="{}")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Settings(Base):
    """Application settings"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    enable_email = Column(Boolean, default=False)
    email_address = Column(String(255))
    email_username = Column(String(255))
    email_password = Column(String(255))
    email_smtp_server = Column(String(255), default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    backup_counter = Column(Integer, default=0)
    backup_counter_maximum = Column(Integer, default=200)
    enable_interval_backups = Column(Boolean, default=True)
    jdbc_url = Column(String(500))
    jdbc_driver_class = Column(String(255))
    jdbc_jar_path = Column(String(500))
    jdbc_username = Column(String(255))
    jdbc_password = Column(String(255))
    encryption_key = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ProcessedFile(Base):
    """Processed file record"""
    __tablename__ = "processed_files"

    id = Column(Integer, primary_key=True)
    file_name = Column(String(500))
    file_checksum = Column(String(100))
    copy_destination = Column(String(500))
    ftp_destination = Column(String(500))
    email_destination = Column(String(500))
    resend_flag = Column(Boolean, default=False)
    folder_id = Column(Integer)
    sent_date_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


class Run(Base):
    """Job execution record"""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    folder_id = Column(Integer)
    folder_alias = Column(String(200))
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    status = Column(String(50))  # running, completed, failed
    files_processed = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    error_message = Column(Text)


class Pipeline(Base):
    """Pipeline definition"""
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    description = Column(Text)
    nodes = Column(Text)  # JSON
    edges = Column(Text)  # JSON
    is_template = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class GlobalTrigger(Base):
    """Global cron trigger"""
    __tablename__ = "global_triggers"

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    cron = Column(String(100))
    enabled = Column(Boolean, default=False)
    pipeline_ids = Column(Text)  # JSON array
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============================================================================
# Database Functions
# ============================================================================

def get_engine():
    """Get or create SQLAlchemy engine"""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    return _engine


def get_session_maker():
    """Get or create session maker"""
    global _session_maker
    if _session_maker is None:
        _session_maker = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _session_maker


def get_database() -> Session:
    """Get database session"""
    SessionLocal = get_session_maker()
    return SessionLocal()


def initialize_database():
    """Initialize database tables"""
    engine = get_engine()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create default records if they don't exist
    SessionLocal = get_session_maker()
    session = SessionLocal()
    
    try:
        # Create default output profile if none exists
        if session.query(OutputProfile).count() == 0:
            default_profile = OutputProfile(
                name="Standard CSV Output",
                alias="standard-csv",
                description="Default CSV output format",
                output_format="csv",
                edi_tweaks="{}",
                custom_settings="{}",
                is_default=True,
            )
            session.add(default_profile)
        
        # Create default settings if none exist
        if session.query(Settings).count() == 0:
            default_settings = Settings()
            session.add(default_settings)
        
        session.commit()
        print(f"Database initialized: {DATABASE_PATH}")
    except Exception as e:
        session.rollback()
        print(f"Error initializing database: {e}")
    finally:
        session.close()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations"""
    session = get_database()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
