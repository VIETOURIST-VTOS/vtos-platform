"""Cấu hình từ biến môi trường (.env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    APP_NAME: str = "VTOS API"
    APP_VERSION: str = "0.2.0"
    ENV: str = "dev"                       # dev | prod
    DATABASE_URL: str = "sqlite:///./vtos.db"
    SECRET_KEY: str = "doi-khoa-nay-truoc-khi-chay-that"
    ACCESS_TOKEN_MINUTES: int = 12 * 60
    ROBOT_TOKEN: str = "doi-robot-token"
    SEED_DEMO: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    TZ: str = "Asia/Ho_Chi_Minh"


settings = Settings()
