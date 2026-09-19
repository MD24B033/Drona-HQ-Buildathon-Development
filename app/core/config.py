from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Autonomous SDR"
    VERSION: str = "1.0.0"
    
    # The database URL (Your teammate will likely provide this)
    # Example: postgresql+asyncpg://user:password@localhost:5432/sdr_db
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db" 
    
    # API Keys for Agents
    OPENAI_API_KEY: str = ""
    DRONAHQ_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
