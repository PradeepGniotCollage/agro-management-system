import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.farmer import Farmer
from app.core.config import settings
import sys
import os

# Add the current directory to sys.path to allow importing from 'app'
sys.path.append(os.getcwd())

async def add_manual_farmers():
    # Use the database URL from settings
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        farmers_data = [
            {"farmer_name": "Rajesh Kumar", "whatsapp_number": "9876543210", "address": "Village A, District B"},
            {"farmer_name": "Suresh Singh", "whatsapp_number": "9123456780", "address": "Village C, District D"},
            {"farmer_name": "Mahesh Patel", "whatsapp_number": "8888888888", "address": "Village E, District F"},
        ]

        for data in farmers_data:
            # Check if farmer already exists
            from sqlalchemy.future import select
            stmt = select(Farmer).where(Farmer.whatsapp_number == data["whatsapp_number"])
            result = await session.execute(stmt)
            existing_farmer = result.scalars().first()

            if not existing_farmer:
                new_farmer = Farmer(**data)
                session.add(new_farmer)
                print(f"Adding farmer: {data['farmer_name']} ({data['whatsapp_number']})")
            else:
                print(f"Farmer with WhatsApp {data['whatsapp_number']} already exists.")

        try:
            await session.commit()
            print("Successfully added manual farmer data.")
        except Exception as e:
            await session.rollback()
            print(f"Error adding manual farmer data: {e}")
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_manual_farmers())
