from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, gt=0)
    GITHUB_TOKEN: str | None = None
    GITHUB_REPOSITORY: str = "EXBO-Studio/stalzone-database"
    GITHUB_BRANCH: str = "main"
    GITHUB_ITEMS_PATH: str = "global/items"
    GITHUB_HIDEOUT_RECIPES_PATH: str = "global/hideout_recipes.json"
    SYNC_RUN_ON_STARTUP: bool = True
    SYNC_INTERVAL_HOURS: int = Field(default=24, gt=0)
    SYNC_DOWNLOAD_CONCURRENCY: int = Field(default=10, gt=0, le=50)
    STALZONE_API_BASE_URL: str = "https://eapi.stalcraft.net"
    AUCTION_REGIONS: str = "EU"
    AUCTION_REQUESTS_PER_MINUTE: int = Field(default=180, gt=0, le=200)
    AUCTION_LOTS_REFRESH_MINUTES: int = Field(default=10, gt=0)
    AUCTION_HISTORY_REFRESH_HOURS: int = Field(default=6, gt=0)
    AUCTION_SYNC_INTERVAL_MINUTES: int = Field(default=1, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
