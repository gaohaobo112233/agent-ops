import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "自动化运维Agent"
    APP_VERSION: str = "1.0.0"

    # DeepSeek API
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "agent_ops"

    # JWT
    JWT_SECRET_KEY: str = "change-this-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # Default admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
