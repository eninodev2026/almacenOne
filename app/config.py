# app\config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    cors_origins: str = "http://localhost:5500"
    cookie_secure: bool = False
    access_minutes: int = 480
    model_config = SettingsConfigDict(env_file=".env")

    @property
    def lista_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()