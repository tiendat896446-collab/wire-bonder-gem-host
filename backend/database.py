import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Use an async SQLite database
DB_PATH = "wire_bonder_data.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}, # Required for SQLite
    echo=False
)

# Create async sessionmaker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Declarative base for models
Base = declarative_base()

async def init_db():
    """
    Initializes the database, creating all tables if they do not exist.
    """
    # Import models here to register them with Base metadata
    from backend.models import TelemetryModel, AlarmModel, RecipeModel

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[Database] Database initialized and tables created successfully.")
