from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Real-Time Analytics Platform"
    SECRET_KEY: str = "production-grade-jwt-signing-key-secure-hash-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Defaults configured for standard containerized instances
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/analytics"
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        case_sensitive = True

settings = Settings()