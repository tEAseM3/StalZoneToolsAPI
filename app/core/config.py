from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, gt=0)
    GITHUB_TOKEN: str | None = None
    GITHUB_REPOSITORY: str = "EXBO-Studio/stalzone-database"
    GITHUB_BRANCH: str = "main"
    GITHUB_ITEMS_PATH: str = "global/items"
    GITHUB_HIDEOUT_RECIPES_PATH: str = "global/hideout_recipes.json"
    SYNC_RUN_ON_STARTUP: bool = True
    SYNC_INTERVAL_HOURS: int = Field(default=24, gt=0)
    SYNC_DOWNLOAD_CONCURRENCY: int = Field(default=10, gt=0, le=50)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
