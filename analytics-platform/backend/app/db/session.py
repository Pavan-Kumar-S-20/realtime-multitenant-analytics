from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# 1. Fallback directly to 'analytics_db' to ensure it connects flawlessly
DATABASE_URL = getattr(settings, "DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/analytics_db")

if "analytics_db" not in DATABASE_URL and "analytics" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("/analytics", "/analytics_db")

# 2. Instantiate the asynchronous engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# 3. Create the scoped session factory maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 4. Declarative Base mapping layout for SQLAlchemy models
Base = declarative_base()

# Dependency generator to inject async DB sessions cleanly into routes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()