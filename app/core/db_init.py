import logging
import asyncio
import asyncpg
import os
from alembic.config import Config
from alembic.config import Config

from alembic import command

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from app.core.config import settings
from app.models.user import User
from app.core.security import get_password_hash
from app.core.database import AsyncSessionLocal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def ensure_db_exists():
    """Checks if the target database exists and creates it if it doesn't."""
    # Connect to the default 'postgres' database to check for our database
    db_name = settings.POSTGRES_DB
    user = settings.POSTGRES_USER
    password = settings.POSTGRES_PASSWORD
    host = settings.POSTGRES_SERVER
    port = settings.POSTGRES_PORT
    
    logger.info(f"Checking if database '{db_name}' exists...")
    
    try:
        # Connect to 'postgres' DB
        conn = await asyncpg.connect(
            user=user, 
            password=password, 
            host=host, 
            port=port, 
            database='postgres'
        )
        
        databases = await conn.fetch("SELECT datname FROM pg_database WHERE datname = $1", db_name)
        
        if not databases:
            logger.info(f"Database '{db_name}' not found. Creating it...")
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database '{db_name}' created successfully.")
        else:
            logger.info(f"Database '{db_name}' already exists.")
            
        await conn.close()
    except Exception as e:
        logger.error(f"Error ensuring database exists: {e}")
        raise

async def initialize_db():
    """Complete database initialization sequence."""
    logger.info("Starting database initialization...")
    await ensure_db_exists()
    
    # Small delay to ensure DB is ready for migrations
    await asyncio.sleep(2)
    
    logger.info("Proceeding to migrations...")
    if os.environ.get("VERCEL") == "1":
        logger.info("Skipping migrations and seeding in Vercel environment.")
        return
    # Migrations are sync, so we run them in a thread
    await asyncio.to_thread(run_migrations)
    
    logger.info("Proceeding to seeding...")
    await seed_initial_data()
    logger.info("Database initialization complete.")

async def seed_initial_data():
    """Seeds initial data like the first admin user."""
    logger.info("Seeding initial data...")
    try:
        async with AsyncSessionLocal() as session:
            # Check if any user exists
            stmt = select(User)
            result = await session.execute(stmt)
            first_user = result.scalars().first()
            if not first_user:
                logger.info("No users found. Creating initial admin user...")
                admin_user = User(
                    full_name="System Admin",
                    phone=settings.INITIAL_ADMIN_PHONE,
                    hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                    role="admin",
                    is_active=True,
                    is_verified=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(admin_user)
                await session.commit()
                logger.info(f"Initial admin user created with phone: {settings.INITIAL_ADMIN_PHONE}")
            else:
                logger.info(f"Users already exist (Found: {first_user.phone}). Skipping seeding.")
    except Exception as e:
        logger.error(f"Error during seeding: {str(e)}", exc_info=True)
        raise

import subprocess

def run_migrations():
    """Runs Alembic migrations to current head using a subprocess."""
    logger.info("Running database migrations via subprocess...")
    try:
        # We use subprocess to avoid event loop conflicts between 
        # the main app and alembic's async env.py
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Alembic output: {result.stdout}")
        logger.info("Migrations completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed with exit code {e.returncode}")
        logger.error(f"Alembic Error Output: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}", exc_info=True)
        raise
