import logging
import asyncio
import asyncpg
import os
import subprocess
from urllib.parse import urlparse

from sqlalchemy.future import select
from app.models.user import User
from app.core.security import get_password_hash
from app.core.database import AsyncSessionLocal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def ensure_db_exists():
    """
    Production (Render + Supabase) me database create/check nahi karte.
    Sirf connection test karte hain.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    logger.info("Checking database connection...")

    try:
        host = (urlparse(db_url).hostname or "").lower() if db_url else ""
        connect_args = {"statement_cache_size": 0} if any(token in host for token in ["pgbouncer", "pooler"]) else {}
        conn = await asyncpg.connect(db_url, **connect_args)
        await conn.close()
        logger.info("Database connection successful.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


async def initialize_db():
    """Complete database initialization sequence."""
    logger.info("Starting database initialization...")

    await ensure_db_exists()

    await asyncio.sleep(2)

    logger.info("Proceeding to migrations...")

    # Vercel environment me migrations skip
    if os.environ.get("VERCEL") == "1":
        logger.info("Skipping migrations in Vercel environment.")
        return

    await asyncio.to_thread(run_migrations)

    logger.info("Proceeding to seeding...")

    await seed_initial_data()

    logger.info("Database initialization complete.")


async def seed_initial_data():
    """Create first admin user if database empty."""
    logger.info("Seeding initial data...")

    try:
        async with AsyncSessionLocal() as session:

            stmt = select(User)
            result = await session.execute(stmt)

            first_user = result.scalars().first()

            if not first_user:
                logger.info("No users found. Creating initial admin user...")

                admin_user = User(
                    full_name="System Admin",
                    phone=os.getenv("INITIAL_ADMIN_PHONE", "9999999999"),
                    hashed_password=get_password_hash(
                        os.getenv("INITIAL_ADMIN_PASSWORD", "admin123")
                    ),
                    role="admin",
                    is_active=True,
                    is_verified=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                session.add(admin_user)
                await session.commit()

                logger.info("Initial admin user created.")

            else:
                logger.info("Users already exist. Skipping seeding.")

    except Exception as e:
        logger.error(f"Error during seeding: {str(e)}", exc_info=True)
        raise


def run_migrations():
    """Run Alembic migrations."""
    logger.info("Running database migrations...")

    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )

        logger.info(result.stdout)
        logger.info("Migrations completed successfully.")

    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e.stderr}")
        raise
