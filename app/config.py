from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    SECRET_KEY: str = "change-me"
    DATABASE_URL: str = "sqlite:///./aicrawler.db"

    ANTHROPIC_API_KEY: str = ""
    PERPLEXITY_API_KEY: str = ""

    DISCOVERY_CRON_HOUR: int = 6
    ENRICHMENT_INTERVAL_HOURS: int = 6
    FETCHING_INTERVAL_HOURS: int = 2
    FETCH_BATCH_SIZE: int = 20

    # Digest scheduling
    DIGEST_CRON_DAY: str = "mon"
    DIGEST_CRON_HOUR: int = 7

    # API auth
    API_TOKEN: str = ""

    APP_TITLE: str = "AICrawler"
    DEBUG: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
