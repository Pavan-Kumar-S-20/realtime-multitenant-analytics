import asyncio
from app.db.session import engine, Base
# Import all models explicitly to make sure metadata registers them
from app.models.schemas import Organization, User, APIKey, Event

async def reset_database():
    print("🚀 Starting database schema sync...")
    async with engine.begin() as conn:
        # Safely drop existing mismatched schemas
        print("🧹 Dropping old out-of-sync tables...")
        await conn.run_sync(Base.metadata.drop_all)

        # Generate clean tables with all structural columns
        print("🏗️ Creating fresh database tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("✨ Database successfully synchronized!")

if __name__ == "__main__":
    asyncio.run(reset_database())