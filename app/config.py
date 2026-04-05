from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/locomotive"
    cors_origins: str = "http://localhost:3000"
    simulator_interval_ms: int = 1000
    db_batch_interval_s: int = 5
    history_retention_hours: int = 72
    log_level: str = "INFO"
    simulator_scenario: str = "normal"  # normal | overheat | brake_failure | low_fuel | highload | demo
    api_key: str = "dev-api-key"
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    class Config:
        env_file = ".env"


settings = Settings()
